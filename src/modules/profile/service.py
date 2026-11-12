from __future__ import annotations

import uuid
from dataclasses import dataclass

from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.data.models import User
from src.data.models.enums import BusinessStage, TaxMode
from src.data.repositories.dialog_states import DialogStateRepository
from src.data.repositories.profiles import ProfileRepository
from src.data.repositories.users import UserRepository
from src.handlers.text import COPY
from src.modules.profile import states
from src.modules.profile.dialog_memory import payload_after_reset, payload_with_follow_up
from src.modules.profile.keyboards import (
    profile_edit_keyboard,
    skip_keyboard,
    stage_keyboard,
    tax_keyboard,
)
from src.modules.profile.labels import (
    MODE_CALLBACK,
    STAGE_CALLBACK,
    format_profile_show,
    is_profile_empty,
    mode_label,
    profile_needs_sphere,
    stage_label,
)
from src.modules.profile.parse import parse_business_line


@dataclass(frozen=True, slots=True)
class ProfileReply:
    text: str
    markup: InlineKeyboardMarkup | None = None


class ProfileService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def ensure_user(self, telegram_id: int, username: str | None) -> User:
        async with self.session_factory() as session:
            user = await UserRepository(session).get_or_create(telegram_id, username)
            await session.commit()
            return user

    async def should_offer_business_prompt(self, user_id: uuid.UUID) -> bool:
        async with self.session_factory() as session:
            profile = await ProfileRepository(session).get_by_user_id(user_id)
            dialog = await DialogStateRepository(session).get_by_user_id(user_id)
            if dialog is not None and dialog.state in states.ACTIVE_STATES:
                return False
            if profile is None or is_profile_empty(profile):
                return True
            if profile_needs_sphere(profile):
                return True
            return False

    async def start_business_prompt(self, user_id: uuid.UUID) -> ProfileReply:
        async with self.session_factory() as session:
            await DialogStateRepository(session).set_state(user_id, states.ASK_BUSINESS)
            await session.commit()
        return ProfileReply(COPY["ask_business"], skip_keyboard())

    async def reset_dialog(self, user_id: uuid.UUID) -> None:
        async with self.session_factory() as session:
            repo = DialogStateRepository(session)
            row = await repo.get_or_create(user_id)
            await repo.set_state(
                user_id,
                states.IDLE,
                payload=payload_after_reset(dict(row.payload)),
            )
            await session.commit()

    async def remember_follow_up(
        self,
        user_id: uuid.UUID,
        question: str,
        material_title: str | None,
    ) -> None:
        async with self.session_factory() as session:
            repo = DialogStateRepository(session)
            row = await repo.get_or_create(user_id)
            await repo.set_state(
                user_id,
                row.state,
                payload=payload_with_follow_up(
                    dict(row.payload),
                    question=question,
                    material_title=material_title,
                ),
            )
            await session.commit()

    async def follow_up_context(self, user_id: uuid.UUID) -> tuple[str | None, str | None]:
        async with self.session_factory() as session:
            row = await DialogStateRepository(session).get_by_user_id(user_id)
        if row is None:
            return None, None
        question = row.payload.get("follow_question")
        material = row.payload.get("follow_material")
        return (
            question if isinstance(question, str) and question.strip() else None,
            material if isinstance(material, str) and material.strip() else None,
        )

    async def is_in_dialog(self, user_id: uuid.UUID) -> bool:
        async with self.session_factory() as session:
            dialog = await DialogStateRepository(session).get_by_user_id(user_id)
            return dialog is not None and dialog.state in states.ACTIVE_STATES

    async def show_profile(self, user_id: uuid.UUID) -> ProfileReply:
        async with self.session_factory() as session:
            profile = await ProfileRepository(session).get_by_user_id(user_id)
            if is_profile_empty(profile):
                return ProfileReply(COPY["profile_empty"])
            assert profile is not None
            return ProfileReply(format_profile_show(profile), profile_edit_keyboard())

    async def handle_text(self, user: User, text: str) -> ProfileReply | None:
        async with self.session_factory() as session:
            dialog_repo = DialogStateRepository(session)
            dialog = await dialog_repo.get_by_user_id(user.id)
            if dialog is None or dialog.state not in states.ACTIVE_STATES:
                return None
            profiles = ProfileRepository(session)
            reply: ProfileReply | None = None
            if dialog.state == states.ASK_BUSINESS:
                reply = await self._handle_business_text(profiles, dialog_repo, user.id, text)
            elif dialog.state == states.EDIT_SPHERE:
                await profiles.upsert(user.id, sphere=text.strip())
                await dialog_repo.set_state(user.id, states.IDLE)
                reply = ProfileReply(
                    COPY["profile_saved"].format(что_запомнил=f"сфера — {text.strip()}")
                )
            await session.commit()
            return reply

    async def handle_callback(self, user: User, data: str) -> ProfileReply | None:
        if not (
            data == "profile_skip"
            or data.startswith("profile_stage:")
            or data.startswith("profile_mode:")
            or data.startswith("profile_edit:")
        ):
            return None
        async with self.session_factory() as session:
            profiles = ProfileRepository(session)
            dialog_repo = DialogStateRepository(session)
            dialog = await dialog_repo.get_by_user_id(user.id)
            current = dialog.state if dialog else states.IDLE
            reply: ProfileReply | None = None
            if data == "profile_skip":
                reply = await self._handle_skip(profiles, dialog_repo, user.id, current)
            elif data.startswith("profile_stage:"):
                stage = STAGE_CALLBACK[data.removeprefix("profile_stage:")]
                reply = await self._save_stage(profiles, dialog_repo, user.id, stage)
            elif data.startswith("profile_mode:"):
                mode_key = data.removeprefix("profile_mode:")
                mode = MODE_CALLBACK[mode_key]
                unknown = mode_key == "unknown"
                reply = await self._save_mode(profiles, dialog_repo, user.id, mode, unknown)
            elif data.startswith("profile_edit:"):
                field = data.removeprefix("profile_edit:")
                reply = await self._start_edit(dialog_repo, user.id, field)
            await session.commit()
            return reply

    async def _handle_business_text(
        self,
        profiles: ProfileRepository,
        dialog_repo: DialogStateRepository,
        user_id: uuid.UUID,
        text: str,
    ) -> ProfileReply:
        parsed = parse_business_line(text)
        values: dict[str, object] = {}
        saved_parts: list[str] = []
        if parsed.sphere:
            values["sphere"] = parsed.sphere
            saved_parts.append(f"сфера — {parsed.sphere}")
        if parsed.stage is not None:
            values["stage"] = parsed.stage
            saved_parts.append(f"стадия — {stage_label(parsed.stage)}")
        if not values:
            return ProfileReply(COPY["ask_business"], skip_keyboard())
        await profiles.upsert(user_id, **values)
        profile = await profiles.get_by_user_id(user_id)
        prefix = ""
        if saved_parts:
            prefix = COPY["profile_saved"].format(что_запомнил=", ".join(saved_parts)) + "\n\n"
        assert profile is not None
        if profile.stage is None:
            await dialog_repo.set_state(user_id, states.ASK_STAGE)
            return ProfileReply(f"{prefix}Выберите стадию бизнеса:", stage_keyboard())
        if profile.mode is None:
            await dialog_repo.set_state(user_id, states.ASK_TAX)
            return ProfileReply(f"{prefix}{COPY['ask_tax_regime']}", tax_keyboard())
        await dialog_repo.set_state(user_id, states.IDLE)
        return ProfileReply(prefix.strip() or COPY["smalltalk"])

    async def _handle_skip(
        self,
        profiles: ProfileRepository,
        dialog_repo: DialogStateRepository,
        user_id: uuid.UUID,
        state: str,
    ) -> ProfileReply:
        profile = await profiles.get_by_user_id(user_id)
        if state == states.ASK_BUSINESS:
            await dialog_repo.set_state(user_id, states.ASK_STAGE)
            return ProfileReply("Выберите стадию бизнеса:", stage_keyboard())
        if state == states.ASK_STAGE:
            if profile is not None and profile.mode is None:
                await dialog_repo.set_state(user_id, states.ASK_TAX)
                return ProfileReply(COPY["ask_tax_regime"], tax_keyboard())
        await dialog_repo.set_state(user_id, states.IDLE)
        return ProfileReply(COPY["smalltalk"])

    async def _save_stage(
        self,
        profiles: ProfileRepository,
        dialog_repo: DialogStateRepository,
        user_id: uuid.UUID,
        stage: BusinessStage,
    ) -> ProfileReply:
        await profiles.upsert(user_id, stage=stage)
        profile = await profiles.get_by_user_id(user_id)
        saved = COPY["profile_saved"].format(что_запомнил=f"стадия — {stage_label(stage)}")
        assert profile is not None
        if profile.mode is None:
            await dialog_repo.set_state(user_id, states.ASK_TAX)
            return ProfileReply(f"{saved}\n\n{COPY['ask_tax_regime']}", tax_keyboard())
        await dialog_repo.set_state(user_id, states.IDLE)
        return ProfileReply(saved)

    async def _save_mode(
        self,
        profiles: ProfileRepository,
        dialog_repo: DialogStateRepository,
        user_id: uuid.UUID,
        mode: TaxMode,
        is_unknown: bool,
    ) -> ProfileReply:
        await profiles.upsert(user_id, mode=mode)
        await dialog_repo.set_state(user_id, states.IDLE)
        saved = COPY["profile_saved"].format(что_запомнил=f"режим — {mode_label(mode)}")
        if is_unknown:
            return ProfileReply(f"{saved}\n\n{COPY['tax_regime_unknown']}")
        return ProfileReply(saved)

    async def _start_edit(
        self,
        dialog_repo: DialogStateRepository,
        user_id: uuid.UUID,
        field: str,
    ) -> ProfileReply:
        if field == "sphere":
            await dialog_repo.set_state(user_id, states.EDIT_SPHERE)
            return ProfileReply("Напишите новую сферу бизнеса:")
        if field == "stage":
            await dialog_repo.set_state(user_id, states.EDIT_STAGE)
            return ProfileReply("Выберите стадию:", stage_keyboard())
        if field == "mode":
            await dialog_repo.set_state(user_id, states.EDIT_MODE)
            return ProfileReply(COPY["ask_tax_regime"], tax_keyboard())
        return ProfileReply(COPY["unknown_command"])
