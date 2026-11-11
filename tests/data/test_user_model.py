import pytest

from src.data.models import User


@pytest.mark.parametrize("telegram_id", [None, "", "   ", 0])
def test_rejects_empty_telegram_id(telegram_id: object) -> None:
    with pytest.raises(ValueError):
        User(telegram_id=telegram_id)


def test_accepts_positive_integer() -> None:
    assert User(telegram_id=123).telegram_id == 123


def test_converts_numeric_string() -> None:
    assert User(telegram_id="123").telegram_id == 123
