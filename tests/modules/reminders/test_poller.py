from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from loguru import logger
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
    reminder = await ReminderRepository(db_session).create(
        user.id,
        text="через минуту",
        repeat=ReminderRepeat.ONCE,
        next_fire_at=datetime.now(UTC) - timedelta(seconds=5),
    )
    await db_session.commit()

    bot = AsyncMock()
    settings = __import__("src.core.settings", fromlist=["Settings"]).Settings()
    service = ReminderService(settings=settings, session_factory=profile_session_factory)  # type: ignore[arg-type]
    logged: list[str] = []
    sink = logger.add(lambda message: logged.append(message.record["message"]))
    try:
        await _tick(bot, profile_session_factory, service)  # type: ignore[arg-type]
    finally:
        logger.remove(sink)

    bot.send_message.assert_awaited_once()
    sent = [line for line in logged if line.startswith("reminder_sent ")]
    assert sent == [f"reminder_sent user_id={user.id} id={reminder.id}"]
    due = await ReminderRepository(db_session).claim_due(datetime.now(UTC))
    assert due == []
