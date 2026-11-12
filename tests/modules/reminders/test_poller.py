from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.enums import ReminderRepeat
from src.data.repositories.reminders import ReminderRepository
from src.data.repositories.users import UserRepository
from src.modules.reminders.poller import _tick
from src.modules.reminders.service import ReminderService


@pytest.mark.integration
async def test_poller_sends_once_and_advances(
    profile_session_factory,
    db_session: AsyncSession,
) -> None:
    user = await UserRepository(db_session).create(telegram_id=400000010)
    await ReminderRepository(db_session).create(
        user.id,
        text="через минуту",
        repeat=ReminderRepeat.ONCE,
        next_fire_at=datetime.now(UTC) - timedelta(seconds=5),
    )
    await db_session.commit()

    bot = AsyncMock()
    settings = __import__("src.core.settings", fromlist=["Settings"]).Settings()
    service = ReminderService(settings=settings, session_factory=profile_session_factory)  # type: ignore[arg-type]
    await _tick(bot, profile_session_factory, service)  # type: ignore[arg-type]

    bot.send_message.assert_awaited_once()
    due = await ReminderRepository(db_session).claim_due(datetime.now(UTC))
    assert due == []
