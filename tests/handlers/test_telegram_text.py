from src.handlers.telegram_text import split_telegram_text


def test_short_text_stays_one_message() -> None:
    assert split_telegram_text("Короткий ответ.") == ["Короткий ответ."]


def test_long_text_is_split_before_telegram_limit() -> None:
    text = "а" * 4001
    parts = split_telegram_text(text)

    assert parts == ["а" * 4000, "а"]
    assert all(len(part) <= 4000 for part in parts)
