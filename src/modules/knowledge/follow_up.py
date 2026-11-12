from __future__ import annotations

import re

_FOLLOW_UP = re.compile(
    r"^(?:а\s+для|а\s+как|а\s+этот|подробнее|этот\s+материал|этот\s+курс)\b",
    re.IGNORECASE,
)
_MAX_FOLLOW_UP_LENGTH = 80


def is_follow_up(text: str) -> bool:
    stripped = text.strip()
    if not stripped or len(stripped) > _MAX_FOLLOW_UP_LENGTH:
        return False
    return _FOLLOW_UP.search(stripped) is not None


def expand_follow_up(
    text: str,
    *,
    previous_question: str | None,
    previous_material: str | None,
) -> str:
    stripped = text.strip()
    if not is_follow_up(stripped):
        return stripped
    extra = [
        part.strip() for part in (previous_question, previous_material) if part and part.strip()
    ]
    if not extra:
        return stripped
    return f"{stripped} {' '.join(extra)}"


def queries_for_turn(
    text: str,
    *,
    previous_question: str | None,
    previous_material: str | None,
) -> tuple[str, str]:
    question = text.strip()
    return question, expand_follow_up(
        question,
        previous_question=previous_question,
        previous_material=previous_material,
    )
