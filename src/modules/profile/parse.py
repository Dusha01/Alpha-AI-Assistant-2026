from __future__ import annotations

from dataclasses import dataclass

from src.data.models.enums import BusinessStage


@dataclass(frozen=True, slots=True)
class ParsedBusiness:
    sphere: str | None
    stage: BusinessStage | None


def _detect_stage(text: str) -> BusinessStage | None:
    lowered = text.lower()
    if "планир" in lowered or "только план" in lowered:
        return BusinessStage.PLANNING
    if "полгода" in lowered or "меньше года" in lowered:
        return BusinessStage.LT_YEAR
    if "больше года" in lowered or "уже год" in lowered:
        return BusinessStage.GT_YEAR
    if " год" in f" {lowered}" and "полгода" not in lowered:
        return BusinessStage.GT_YEAR
    return None


def parse_business_line(text: str) -> ParsedBusiness:
    raw = text.strip()
    if not raw:
        return ParsedBusiness(sphere=None, stage=None)
    if "," in raw:
        sphere_part, tail = (item.strip() for item in raw.split(",", 1))
        return ParsedBusiness(sphere=sphere_part or None, stage=_detect_stage(tail))
    stage = _detect_stage(raw)
    return ParsedBusiness(sphere=raw, stage=stage)
