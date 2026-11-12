from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.enums import BusinessStage, TaxMode
from src.data.repositories.users import UserRepository
from src.handlers.text import COPY
from src.modules.profile import states
from src.modules.profile.service import ProfileService

pytestmark = pytest.mark.integration


async def test_empty_profile_offers_business_after_prompt(
    profile_session_factory,
    db_session: AsyncSession,
) -> None:
    service = ProfileService(profile_session_factory)  # type: ignore[arg-type]
    user = await UserRepository(db_session).create(telegram_id=300000001)

    assert await service.should_offer_business_prompt(user.id) is True
    reply = await service.start_business_prompt(user.id)
    assert reply.text == COPY["ask_business"]
    assert await service.is_in_dialog(user.id) is True


async def test_coffee_half_year_saves_sphere_and_stage(
    profile_session_factory,
    db_session: AsyncSession,
) -> None:
    from src.data.repositories.dialog_states import DialogStateRepository
    from src.data.repositories.profiles import ProfileRepository

    service = ProfileService(profile_session_factory)  # type: ignore[arg-type]
    users = UserRepository(db_session)
    dialogs = DialogStateRepository(db_session)
    user = await users.create(telegram_id=300000002)
    await dialogs.set_state(user.id, states.ASK_BUSINESS)
    await db_session.commit()

    reply = await service.handle_text(user, "Кофейня, полгода")
    assert reply is not None
    assert "Кофейня" in reply.text

    profile = await ProfileRepository(db_session).get_by_user_id(user.id)
    assert profile is not None
    assert profile.sphere == "Кофейня"
    assert profile.stage == BusinessStage.LT_YEAR


async def test_show_profile_empty_when_no_data(
    profile_session_factory,
    db_session: AsyncSession,
) -> None:
    service = ProfileService(profile_session_factory)  # type: ignore[arg-type]
    user = await UserRepository(db_session).create(telegram_id=300000003)

    reply = await service.show_profile(user.id)
    assert reply.text == COPY["profile_empty"]


async def test_skip_on_ask_tax_preserves_existing_mode(
    profile_session_factory,
    db_session: AsyncSession,
) -> None:
    from src.data.repositories.dialog_states import DialogStateRepository
    from src.data.repositories.profiles import ProfileRepository

    service = ProfileService(profile_session_factory)  # type: ignore[arg-type]
    users = UserRepository(db_session)
    profiles = ProfileRepository(db_session)
    dialogs = DialogStateRepository(db_session)
    user = await users.create(telegram_id=300000004)
    await profiles.upsert(user.id, mode=TaxMode.USN)
    await dialogs.set_state(user.id, states.ASK_TAX)
    await db_session.commit()

    reply = await service.handle_callback(user, "profile_skip")
    assert reply is not None

    profile = await profiles.get_by_user_id(user.id)
    assert profile is not None
    assert profile.mode == TaxMode.USN
