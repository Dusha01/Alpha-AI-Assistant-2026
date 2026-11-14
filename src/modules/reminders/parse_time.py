from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

_WEEKDAY = {
    "понедельник": 0,
    "пн": 0,
    "вторник": 1,
    "вт": 1,
    "сред": 2,
    "ср": 2,
    "четверг": 3,
    "чт": 3,
    "пятниц": 4,
    "пятница": 4,
    "пт": 4,
    "суббот": 5,
    "суббота": 5,
    "сб": 5,
    "воскресен": 6,
    "воскресенье": 6,
    "вс": 6,
}


@dataclass(frozen=True, slots=True)
class ParsedTime:
    value: datetime


@dataclass(frozen=True, slots=True)
class TimeParseError:
    kind: str


def _localize(now: datetime, tz: ZoneInfo) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC).astimezone(tz)
    return now.astimezone(tz)


def _combine(local_date, clock: time, tz: ZoneInfo) -> datetime:
    return datetime(
        local_date.year,
        local_date.month,
        local_date.day,
        clock.hour,
        clock.minute,
        tzinfo=tz,
    )


def _parse_clock(fragment: str) -> time | None:
    match = re.search(r"(\d{1,2})[:\.](\d{2})", fragment)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)
    return None


def _parse_hour_words(fragment: str) -> time | None:
    match = re.search(r"(\d{1,2})\s*(утра|вечера|дня|ночи)", fragment)
    if match is None:
        return None
    hour = int(match.group(1))
    part = match.group(2)
    if hour > 23:
        return None
    if part == "вечера" and 1 <= hour <= 11:
        hour += 12
    if part == "дня" and 1 <= hour <= 7:
        hour += 12
    if part == "утра" and hour == 12:
        hour = 0
    if part == "ночи" and hour == 12:
        hour = 0
    return time(hour, 0)


def _next_weekday(local_now: datetime, weekday: int, tz: ZoneInfo) -> datetime:
    today = local_now.weekday()
    delta = (weekday - today) % 7
    if delta == 0:
        delta = 7
    target_date = (local_now + timedelta(days=delta)).date()
    clock = _parse_clock("19:00") or time(19, 0)
    return _combine(target_date, clock, tz)


def parse_when(text: str, now: datetime, *, tz_name: str = "Asia/Vladivostok"):
    tz = ZoneInfo(tz_name)
    local_now = _localize(now, tz)
    lowered = text.lower().strip()
    if not lowered:
        return TimeParseError("bad")

    relative = re.match(
        r"через\s+(\d+)\s+"
        r"(минут[уы]?|мин|час[аов]?|день|дня|дней|недел[июи]?|месяц[аев]?)",
        lowered,
    )
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2)
        if unit.startswith("мин"):
            delta = timedelta(minutes=amount)
        elif unit.startswith("час"):
            delta = timedelta(hours=amount)
        elif unit.startswith("недел"):
            delta = timedelta(weeks=amount)
        elif unit.startswith("месяц"):
            delta = timedelta(days=30 * amount)
        else:
            delta = timedelta(days=amount)
        return ParsedTime(local_now + delta)

    clock = _parse_clock(lowered) or _parse_hour_words(lowered)
    if "вчера" in lowered:
        day = (local_now - timedelta(days=1)).date()
        when = _combine(day, clock or time(9, 0), tz)
        if when <= local_now:
            return TimeParseError("past")
        return ParsedTime(when)

    if "сегодня" in lowered and clock is not None:
        when = _combine(local_now.date(), clock, tz)
        if when <= local_now:
            return TimeParseError("past")
        return ParsedTime(when)

    if "завтра" in lowered:
        day = (local_now + timedelta(days=1)).date()
        when = _combine(day, clock or time(10, 0), tz)
        if when <= local_now:
            return TimeParseError("past")
        return ParsedTime(when)

    if "послезавтра" in lowered:
        day = (local_now + timedelta(days=2)).date()
        when = _combine(day, clock or time(10, 0), tz)
        return ParsedTime(when)

    if "вечером" in lowered or "вечер" in lowered:
        clock = clock or time(19, 0)

    for key, weekday in _WEEKDAY.items():
        if key in lowered:
            when = _next_weekday(local_now, weekday, tz)
            if clock is not None:
                when = _combine(when.date(), clock, tz)
            if when <= local_now:
                when = when + timedelta(days=7)
            return ParsedTime(when)

    if clock is not None:
        when = _combine(local_now.date(), clock, tz)
        if when <= local_now:
            when = when + timedelta(days=1)
        if when <= local_now:
            return TimeParseError("past")
        return ParsedTime(when)

    return TimeParseError("bad")
