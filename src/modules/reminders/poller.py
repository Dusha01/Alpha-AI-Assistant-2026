from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from aiogram import Bot
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.data.repositories.reminders import ReminderRepository
from src.modules.reminders.service import ReminderService


async def run_reminder_poller(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    reminder_service: ReminderService,
    interval_seconds: float,
) -> None:
    while True:
        try:
            await _tick(bot, session_factory, reminder_service)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("reminder_poller_tick_failed")
        await asyncio.sleep(interval_seconds)


async def _tick(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    reminder_service: ReminderService,
) -> None:
    now = datetime.now(UTC)
    async with session_factory() as session:
        repo = ReminderRepository(session)
        due = await repo.claim_due(now)
        await session.commit()

    for row in due:
        from src.data.models import User

        async with session_factory() as session:
            user = await session.get(User, row.user_id)
            if user is None:
                continue
            telegram_id = user.telegram_id
        text, markup = reminder_service.fire_message(row)
        try:
            await bot.send_message(telegram_id, text, reply_markup=markup)
        except Exception:
            logger.exception("reminder_send_failed user_id={}", row.user_id)
            continue
        async with session_factory() as session:
            repo = ReminderRepository(session)
            current = await repo.get_by_id(row.id)
            if current is not None:
                await repo.advance_after_fire(current, now)
            await session.commit()
