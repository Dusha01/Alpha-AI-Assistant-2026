from __future__ import annotations

import re
from dataclasses import dataclass

from src.data.models.enums import BusinessStage, TaxMode
from src.handlers.text import COPY

_WORDS = re.compile(r"[а-яёa-z0-9]+", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ProfileSnapshot:
    sphere: str | None = None
    stage: BusinessStage | None = None
    mode: TaxMode | None = None


def clarify_reply(question: str, profile: ProfileSnapshot | None = None) -> str | None:
    lowered = question.lower()
    if "кредит" in lowered and "оборот" not in lowered and "открыт" not in lowered:
        return COPY["clarify"].format(
            variant_1="кредит на открытие бизнеса",
            variant_2="кредит на оборотные средства",
        )
    if "сколько" in lowered and "налог" in lowered and (profile is None or profile.mode is None):
        return COPY["clarify_tax_mode"]
    words = [match.group(0).lower() for match in _WORDS.finditer(question)]
    if words[:2] == ["как", "закрыть"] and len(words) <= 2:
        return COPY["clarify_close"]
    sphere = (profile.sphere or "").strip() if profile is not None else ""
    mode = profile.mode if profile is not None else None
    if "касс" in lowered and not sphere and mode is None:
        return COPY["clarify_cash"]
    if mode == TaxMode.USN and "расход" in lowered and "налог" in lowered:
        return COPY["clarify_usn_object"]
    return None
