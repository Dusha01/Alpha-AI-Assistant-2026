from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select

from src.data.models import Reminder
from src.data.models.enums import ReminderRepeat, ReminderStatus
from src.data.repositories.base import BaseRepository
from src.modules.reminders.schedule import next_fire_after


class ReminderRepository(BaseRepository):
    async def create(
        self,
        user_id: uuid.UUID,
        *,
        text: str,
        repeat: ReminderRepeat,
        next_fire_at: datetime,
        material_title: str | None = None,
        material_url: str | None = None,
        is_tax: bool = False,
    ) -> Reminder:
        row = Reminder(
            user_id=user_id,
            text=text,
            repeat=repeat,
            status=ReminderStatus.ACTIVE,
            next_fire_at=next_fire_at,
            material_title=material_title,
            material_url=material_url,
            is_tax=is_tax,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_for_user(self, user_id: uuid.UUID) -> list[Reminder]:
        result = await self.session.execute(
            select(Reminder)
            .where(
                Reminder.user_id == user_id,
                Reminder.status.in_((ReminderStatus.ACTIVE, ReminderStatus.PAUSED)),
            )
            .order_by(Reminder.next_fire_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, reminder_id: uuid.UUID) -> Reminder | None:
        return await self.session.get(Reminder, reminder_id)

    async def set_status(self, reminder_id: uuid.UUID, status: ReminderStatus) -> Reminder | None:
        row = await self.get_by_id(reminder_id)
        if row is None:
            return None
        row.status = status
        await self.session.flush()
        return row

    async def set_repeat(self, reminder_id: uuid.UUID, repeat: ReminderRepeat) -> Reminder | None:
        row = await self.get_by_id(reminder_id)
        if row is None:
            return None
        row.repeat = repeat
        await self.session.flush()
        return row

    async def claim_due(self, now: datetime, *, limit: int = 20) -> list[Reminder]:
        stmt = (
            select(Reminder)
            .where(
                Reminder.status == ReminderStatus.ACTIVE,
                Reminder.next_fire_at <= now,
            )
            .order_by(Reminder.next_fire_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def advance_after_fire(self, reminder: Reminder, now: datetime) -> Reminder:
        if reminder.repeat == ReminderRepeat.ONCE:
            reminder.status = ReminderStatus.DONE
        else:
            reminder.next_fire_at = next_fire_after(reminder.next_fire_at, reminder.repeat)
        await self.session.flush()
        return reminder

    async def postpone(self, reminder_id: uuid.UUID, *, minutes: int = 60) -> Reminder | None:
        row = await self.get_by_id(reminder_id)
        if row is None:
            return None
        from datetime import timedelta

        row.next_fire_at = row.next_fire_at + timedelta(minutes=minutes)
        await self.session.flush()
        return row
