from __future__ import annotations

from datetime import UTC, datetime

from src.modules.reminders.parse_time import ParsedTime, TimeParseError, parse_when


def _now() -> datetime:
    return datetime(2026, 11, 12, 8, 0, tzinfo=UTC)


def test_tomorrow_at_ten() -> None:
    parsed = parse_when("завтра в 10:00", _now(), tz_name="Asia/Vladivostok")
    assert isinstance(parsed, ParsedTime)
    assert parsed.value.hour == 10


def test_friday_evening() -> None:
    parsed = parse_when("в пятницу вечером", _now(), tz_name="Asia/Vladivostok")
    assert isinstance(parsed, ParsedTime)
    assert parsed.value.hour == 19


def test_in_one_minute() -> None:
    parsed = parse_when("через 1 минуту", _now(), tz_name="Asia/Vladivostok")
    assert isinstance(parsed, ParsedTime)
    assert parsed.value > _now()


def test_past_time() -> None:
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Asia/Vladivostok")
    noon = datetime(2026, 11, 12, 15, 0, tzinfo=tz)
    past = parse_when("сегодня в 08:00", noon, tz_name="Asia/Vladivostok")
    assert isinstance(past, TimeParseError)
    assert past.kind == "past"


def test_yesterday_morning_is_past() -> None:
    past = parse_when("вчера в 9 утра", _now(), tz_name="Asia/Vladivostok")
    assert isinstance(past, TimeParseError)
    assert past.kind == "past"


def test_garbage() -> None:
    bad = parse_when("когда-нибудь потом", _now(), tz_name="Asia/Vladivostok")
    assert isinstance(bad, TimeParseError)
    assert bad.kind == "bad"
