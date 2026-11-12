from __future__ import annotations

TELEGRAM_TEXT_LIMIT = 4000


def split_telegram_text(text: str, size: int = TELEGRAM_TEXT_LIMIT) -> list[str]:
    if len(text) <= size:
        return [text]
    return [text[index : index + size] for index in range(0, len(text), size)]
