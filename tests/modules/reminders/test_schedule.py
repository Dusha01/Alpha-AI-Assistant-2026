from __future__ import annotations

from datetime import UTC, datetime

from src.data.models.enums import ReminderRepeat
from src.modules.reminders.schedule import next_fire_after, next_quarterly_usn_fire


def test_quarterly_interval() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    nxt = next_fire_after(start, ReminderRepeat.QUARTERLY)
    assert (nxt - start).days == 91


def test_next_quarterly_usn_fire_helper() -> None:
    start = datetime(2026, 4, 1, tzinfo=UTC)
    nxt = next_quarterly_usn_fire(start)
    assert nxt > start
