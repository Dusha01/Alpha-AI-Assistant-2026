from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.settings import Settings
from src.data.models import TaxDeadline, User
from src.data.models.enums import ReminderRepeat, ReminderStatus
from src.data.repositories.dialog_states import DialogStateRepository
from src.data.repositories.profiles import ProfileRepository
from src.data.repositories.reminders import ReminderRepository
from src.data.repositories.tax_deadlines import TaxDeadlineRepository
from src.data.repositories.users import UserRepository
from src.handlers.text import COPY
from src.modules.knowledge.catalog import material_url
from src.modules.profile import states as profile_states
from src.modules.profile.dialog_memory import payload_after_reset
from src.modules.recommend.utm import slug_from_url, with_utm
from src.modules.reminders import states
from src.modules.reminders.formatters import format_confirm, format_reminders_list, format_tax_offer
from src.modules.reminders.keyboards import (
    confirm_keyboard,
    fire_keyboard,
    reminders_list_keyboard,
    repeat_keyboard,
    tax_repeat_keyboard,
)
from src.modules.reminders.parse_time import TimeParseError, parse_when

_PAYLOAD_TEXT = "reminder_text"
_PAYLOAD_WHEN = "reminder_when"
_PAYLOAD_REPEAT = "reminder_repeat"
_PAYLOAD_TAX = "tax_deadline_id"

_TAX_INTENT = re.compile(r"^напомни.*налог", re.IGNORECASE | re.DOTALL)


def _reminder_link(reminder: object) -> str | None:
    raw = getattr(reminder, "material_url", None)
    if not isinstance(raw, str) or not raw.strip():
        return None
    campaign = "tax" if getattr(reminder, "is_tax", False) else "reminder"
    return with_utm(raw, campaign=campaign, content=slug_from_url(raw))


@dataclass(frozen=True, slots=True)
class ReminderReply:
    text: str
    markup: InlineKeyboardMarkup | None = None


class ReminderService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory

    async def ensure_user(self, telegram_id: int, username: str | None) -> User:
        async with self.session_factory() as session:
            user = await UserRepository(session).get_or_create(telegram_id, username)
            await session.commit()
            return user

    async def is_in_dialog(self, user_id: uuid.UUID) -> bool:
        async with self.session_factory() as session:
            dialog = await DialogStateRepository(session).get_by_user_id(user_id)
            return dialog is not None and dialog.state in states.ACTIVE_STATES

    def is_reminder_intent(self, text: str) -> bool:
        return text.lower().startswith("напомни")

    def is_tax_intent(self, text: str) -> bool:
        return _TAX_INTENT.search(text.strip()) is not None

    async def list_reminders(self, user_id: uuid.UUID) -> ReminderReply:
        async with self.session_factory() as session:
            rows = await ReminderRepository(session).list_for_user(user_id)
        return ReminderReply(
            format_reminders_list(rows),
            reminders_list_keyboard([row.id for row in rows]) if rows else None,
        )

    async def start_custom_flow(
        self, user_id: uuid.UUID, initial_text: str | None = None
    ) -> ReminderReply:
        async with self.session_factory() as session:
            dialog_repo = DialogStateRepository(session)
            existing = await dialog_repo.get_or_create(user_id)
            payload = payload_after_reset(dict(existing.payload))
            if initial_text:
                payload[_PAYLOAD_TEXT] = initial_text
                await dialog_repo.set_state(user_id, states.REMINDER_WHEN, payload=payload)
                await session.commit()
                return ReminderReply(COPY["reminder_ask_when"])
            await dialog_repo.set_state(user_id, states.REMINDER_TEXT, payload=payload)
            await session.commit()
        return ReminderReply("О чём напомнить?")

    async def start_quick(self, user_id: uuid.UUID, raw_text: str) -> ReminderReply:
        body = raw_text.strip()
        if body.lower().startswith("напомни"):
            body = body[7:].strip(" ,")
        if self.is_tax_intent(raw_text):
            return await self.start_tax_flow(user_id)
        return await self.start_custom_flow(user_id, initial_text=body or None)

    async def handle_text(self, user_id: uuid.UUID, text: str) -> ReminderReply | None:
        async with self.session_factory() as session:
            dialog_repo = DialogStateRepository(session)
            dialog = await dialog_repo.get_by_user_id(user_id)
            if dialog is None or dialog.state not in states.ACTIVE_STATES:
                return None
            payload = dict(dialog.payload)
            if dialog.state == states.REMINDER_TEXT:
                payload[_PAYLOAD_TEXT] = text.strip()
                await dialog_repo.set_state(user_id, states.REMINDER_WHEN, payload=payload)
                await session.commit()
                return ReminderReply(COPY["reminder_ask_when"])
            if dialog.state == states.REMINDER_WHEN:
                parsed = parse_when(
                    text,
                    datetime.now(UTC),
                    tz_name=self.settings.reminder_timezone,
                )
                if isinstance(parsed, TimeParseError):
                    key = "reminder_past" if parsed.kind == "past" else "reminder_bad_time"
                    return ReminderReply(COPY[key])
                payload[_PAYLOAD_WHEN] = parsed.value.isoformat()
                await dialog_repo.set_state(user_id, states.REMINDER_REPEAT, payload=payload)
                await session.commit()
                return ReminderReply(COPY["reminder_ask_repeat"], repeat_keyboard())
            return None

    async def handle_callback(self, user_id: uuid.UUID, data: str) -> ReminderReply | None:
        if data.startswith("reminder_repeat:"):
            return await self._pick_repeat(user_id, data.removeprefix("reminder_repeat:"))
        if data.startswith("reminder_confirm:"):
            action = data.removeprefix("reminder_confirm:")
            if action == "yes":
                return await self._confirm_create(user_id)
            if action == "edit":
                return await self.start_custom_flow(user_id)
        if data.startswith("tax_remind:"):
            return await self._create_tax_reminder(
                user_id, data.removeprefix("tax_remind:") == "quarterly"
            )
        if data.startswith("remind_off:"):
            return await self._pause_reminder(uuid.UUID(data.removeprefix("remind_off:")))
        if data.startswith("remind_later:"):
            return await self._postpone_reminder(uuid.UUID(data.removeprefix("remind_later:")))
        if data.startswith("remind_done:"):
            return ReminderReply("Спасибо! Рад, что вы в курсе.")
        if data.startswith("reminder_repeat_set:"):
            body = data.removeprefix("reminder_repeat_set:")
            rid_text, _, repeat_key = body.partition(":")
            if rid_text and repeat_key:
                return await self._change_repeat(uuid.UUID(rid_text), repeat_key)
        return None

    async def _pick_repeat(self, user_id: uuid.UUID, key: str) -> ReminderReply:
        repeat = ReminderRepeat(key)
        async with self.session_factory() as session:
            dialog_repo = DialogStateRepository(session)
            dialog = await dialog_repo.get_by_user_id(user_id)
            if dialog is None:
                return ReminderReply(COPY["error_general"])
            payload = dict(dialog.payload)
            payload[_PAYLOAD_REPEAT] = repeat.value
            await dialog_repo.set_state(user_id, states.REMINDER_CONFIRM, payload=payload)
            await session.commit()
        text = str(payload.get(_PAYLOAD_TEXT, ""))
        when = datetime.fromisoformat(str(payload[_PAYLOAD_WHEN]))
        return ReminderReply(format_confirm(text, when, repeat), confirm_keyboard())

    async def _confirm_create(self, user_id: uuid.UUID) -> ReminderReply:
        async with self.session_factory() as session:
            dialog = await DialogStateRepository(session).get_by_user_id(user_id)
            if dialog is None:
                return ReminderReply(COPY["error_general"])
            payload = dialog.payload
            text = str(payload.get(_PAYLOAD_TEXT, "Напоминание"))
            when = datetime.fromisoformat(str(payload[_PAYLOAD_WHEN]))
            repeat = ReminderRepeat(str(payload.get(_PAYLOAD_REPEAT, ReminderRepeat.ONCE.value)))
            await ReminderRepository(session).create(
                user_id,
                text=text,
                repeat=repeat,
                next_fire_at=when,
            )
            await DialogStateRepository(session).set_state(
                user_id,
                profile_states.IDLE,
                payload=payload_after_reset(dict(payload)),
            )
            await session.commit()
        return ReminderReply(COPY["reminder_created"])

    async def continue_tax_offer(self, user_id: uuid.UUID) -> ReminderReply | None:
        async with self.session_factory() as session:
            dialog = await DialogStateRepository(session).get_by_user_id(user_id)
            profile = await ProfileRepository(session).get_by_user_id(user_id)
            if (
                dialog is None
                or not dialog.payload.get("tax_reminder_pending")
                or profile is None
                or profile.mode is None
            ):
                return None
            mode = profile.mode
            deadline = await TaxDeadlineRepository(session).next_for_mode(
                mode, on_or_after=date.today()
            )
            if deadline is None:
                kept = payload_after_reset(dict(dialog.payload))
                await DialogStateRepository(session).set_state(
                    user_id, profile_states.IDLE, payload=kept
                )
                await session.commit()
                return ReminderReply(COPY["tax_no_data"].format(режим=mode.value))
            payload = payload_after_reset(dict(dialog.payload))
            payload[_PAYLOAD_TAX] = str(deadline.id)
            await DialogStateRepository(session).set_state(
                user_id, states.REMINDER_CONFIRM, payload=payload
            )
            await session.commit()
        due = deadline.due_date.strftime("%d.%m.%Y")
        return ReminderReply(
            format_tax_offer(mode, deadline.what_to_pay, due, deadline.lead_days),
            tax_repeat_keyboard(),
        )

    async def start_tax_flow(self, user_id: uuid.UUID) -> ReminderReply:
        async with self.session_factory() as session:
            profile = await ProfileRepository(session).get_by_user_id(user_id)
            dialog_repo = DialogStateRepository(session)
            if profile is None or profile.mode is None:
                existing = await dialog_repo.get_or_create(user_id)
                pending = payload_after_reset(dict(existing.payload))
                pending["tax_reminder_pending"] = True
                await dialog_repo.set_state(
                    user_id,
                    profile_states.ASK_TAX,
                    payload=pending,
                )
                await session.commit()
                from src.modules.profile.keyboards import tax_keyboard

                return ReminderReply(COPY["ask_tax_regime"], tax_keyboard())
            mode = profile.mode
            deadline = await TaxDeadlineRepository(session).next_for_mode(
                mode, on_or_after=date.today()
            )
            if deadline is None:
                await session.commit()
                return ReminderReply(COPY["tax_no_data"].format(режим=mode.value))
            existing = await dialog_repo.get_or_create(user_id)
            payload = payload_after_reset(dict(existing.payload))
            payload[_PAYLOAD_TAX] = str(deadline.id)
            await dialog_repo.set_state(user_id, states.REMINDER_CONFIRM, payload=payload)
            await session.commit()
        due = deadline.due_date.strftime("%d.%m.%Y")
        return ReminderReply(
            format_tax_offer(mode, deadline.what_to_pay, due, deadline.lead_days),
            tax_repeat_keyboard(),
        )

    async def _create_tax_reminder(self, user_id: uuid.UUID, quarterly: bool) -> ReminderReply:
        async with self.session_factory() as session:
            dialog = await DialogStateRepository(session).get_by_user_id(user_id)
            profile = await ProfileRepository(session).get_by_user_id(user_id)
            if dialog is None or profile is None or profile.mode is None:
                return ReminderReply(COPY["error_general"])
            deadline_id = uuid.UUID(str(dialog.payload.get(_PAYLOAD_TAX)))
            deadline = await session.get(TaxDeadline, deadline_id)
            if deadline is None:
                return ReminderReply(COPY["tax_no_data"].format(режим=profile.mode.value))
            repeat = ReminderRepeat.QUARTERLY if quarterly else ReminderRepeat.ONCE
            fire_at = datetime.combine(
                deadline.due_date - timedelta(days=deadline.lead_days),
                datetime.min.time(),
                tzinfo=UTC,
            )
            base = self.settings.platform_base_url or "https://example.alfacourse.local"
            raw_url = material_url(base, deadline.material_slug) or base
            url = with_utm(raw_url, campaign="tax", content=deadline.material_slug)
            await ReminderRepository(session).create(
                user_id,
                text=deadline.what_to_pay,
                repeat=repeat,
                next_fire_at=fire_at,
                material_title=deadline.material_title,
                material_url=url,
                is_tax=True,
            )
            await DialogStateRepository(session).set_state(
                user_id,
                profile_states.IDLE,
                payload=payload_after_reset(dict(dialog.payload)),
            )
            await session.commit()
        return ReminderReply(
            COPY["tax_created"].format(режим=profile.mode.value, N=deadline.lead_days)
        )

    async def _pause_reminder(self, reminder_id: uuid.UUID) -> ReminderReply:
        async with self.session_factory() as session:
            await ReminderRepository(session).set_status(reminder_id, ReminderStatus.PAUSED)
            await session.commit()
        return ReminderReply(COPY["reminder_off"])

    async def _postpone_reminder(self, reminder_id: uuid.UUID) -> ReminderReply:
        async with self.session_factory() as session:
            await ReminderRepository(session).postpone(reminder_id, minutes=60)
            await session.commit()
        return ReminderReply("Хорошо, напомню чуть позже.")

    async def _change_repeat(self, reminder_id: uuid.UUID, repeat_key: str) -> ReminderReply:
        repeat = ReminderRepeat(repeat_key)
        async with self.session_factory() as session:
            row = await ReminderRepository(session).set_repeat(reminder_id, repeat)
            await session.commit()
        if row is None:
            return ReminderReply(COPY["error_general"])
        labels = {
            ReminderRepeat.ONCE: "один раз",
            ReminderRepeat.WEEKLY: "каждую неделю",
            ReminderRepeat.MONTHLY: "каждый месяц",
            ReminderRepeat.QUARTERLY: "каждый квартал",
        }
        return ReminderReply(COPY["reminder_changed"].format(новая_частота=labels[repeat]))

    def fire_message(self, reminder) -> tuple[str, InlineKeyboardMarkup]:
        link = _reminder_link(reminder)
        if reminder.material_title and link:
            text = COPY["reminder_fire_course"].format(
                имя_материала=reminder.material_title,
                ссылка=link,
            )
        elif reminder.is_tax:
            text = COPY["reminder_fire_custom"].format(текст_напоминания=reminder.text)
            text += "\n" + COPY["tax_disclaimer"].format(источник="справочнику MVP")
        else:
            text = COPY["reminder_fire_custom"].format(текст_напоминания=reminder.text)
        return text, fire_keyboard(reminder.id)
