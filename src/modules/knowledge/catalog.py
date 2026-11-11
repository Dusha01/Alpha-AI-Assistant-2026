from __future__ import annotations

from uuid import UUID

PUBLISHED_STATUS_ID = UUID("61f12dbc-3cd4-4c14-b64b-1709548b904e")

OPEN_COURSE_TYPE_ID = UUID("ed085df2-b9bf-43fc-9a29-e2140346e333")
SUBSCRIPTION_COURSE_TYPE_ID = UUID("1069fd62-8920-417b-b6c1-1bfb7c3f57fb")
PAID_COURSE_TYPE_ID = UUID("9cda1148-8db6-4d29-98fc-6d67ea538fff")
CLOSED_COURSE_TYPE_ID = UUID("50c186e6-14c2-4446-81c5-5263fd5b3362")

_PAID_COURSE_TYPE_IDS = frozenset(
    {
        SUBSCRIPTION_COURSE_TYPE_ID,
        PAID_COURSE_TYPE_ID,
        CLOSED_COURSE_TYPE_ID,
    }
)


def is_paid_course_type(type_id: UUID) -> bool:
    return type_id in _PAID_COURSE_TYPE_IDS


def material_url(base_url: str, slug: str | None) -> str | None:
    if not slug or not slug.strip():
        return None
    base = base_url.rstrip("/")
    if not base:
        return slug.strip()
    return f"{base}/{slug.strip().lstrip('/')}"
