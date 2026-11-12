import pytest

from src.handlers.incoming import reply_key
from src.handlers.text import COPY


@pytest.mark.parametrize(
    ("text", "is_text", "expected"),
    [
        ("/start", True, "start"),
        ("/start@AlfaCourseBot", True, "start"),
        ("/help", True, "help"),
        ("/profile", True, "profile"),
        ("/reminders", True, "reminders"),
        ("/cancel", True, "cancel"),
        ("/cancel@AlfaCourseBot", True, "cancel"),
        ("/unknown", True, "unknown_command"),
        ("привет", True, "smalltalk"),
        (None, False, "non_text"),
        ("x" * 20, True, "too_long"),
    ],
)
def test_reply_key(text: str | None, is_text: bool, expected: str) -> None:
    assert reply_key(text, is_text=is_text, max_length=10) == expected
    if expected not in ("profile", "reminders"):
        assert COPY[expected]
