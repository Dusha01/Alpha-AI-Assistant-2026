from __future__ import annotations

MEMORY_KEYS = ("last_topic", "follow_question", "follow_material")


def payload_after_reset(payload: dict[str, object]) -> dict[str, object]:
    return {key: payload[key] for key in MEMORY_KEYS if key in payload}


def payload_with_follow_up(
    payload: dict[str, object],
    *,
    question: str,
    material_title: str | None,
) -> dict[str, object]:
    updated = dict(payload)
    updated["follow_question"] = question
    if material_title:
        updated["follow_material"] = material_title
    return updated
