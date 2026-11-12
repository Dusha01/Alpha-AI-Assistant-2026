from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.data.models.enums import ReminderRepeat


def next_fire_after(previous: datetime, repeat: ReminderRepeat) -> datetime:
    if previous.tzinfo is None:
        previous = previous.replace(tzinfo=UTC)
    if repeat == ReminderRepeat.WEEKLY:
        return previous + timedelta(weeks=1)
    if repeat == ReminderRepeat.MONTHLY:
        return previous + timedelta(days=30)
    if repeat == ReminderRepeat.QUARTERLY:
        return previous + timedelta(days=91)
    return previous


def next_quarterly_usn_fire(from_when: datetime) -> datetime:
    """Следующее срабатывание для демо квартального налога."""
    if from_when.tzinfo is None:
        from_when = from_when.replace(tzinfo=UTC)
    return from_when + timedelta(days=91)
