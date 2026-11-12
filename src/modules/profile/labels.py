from __future__ import annotations

from src.data.models import Profile
from src.data.models.enums import BusinessStage, TaxMode

_STAGE_LABELS = {
    BusinessStage.PLANNING: "Только планирую",
    BusinessStage.LT_YEAR: "Работаю меньше года",
    BusinessStage.GT_YEAR: "Работаю больше года",
}

_MODE_LABELS = {
    TaxMode.USN: "УСН",
    TaxMode.PATENT: "Патент",
    TaxMode.NPD: "Самозанятость (НПД)",
    TaxMode.OTHER: "Другой",
    TaxMode.UNKNOWN: "Не знаю",
}

STAGE_CALLBACK = {
    "planning": BusinessStage.PLANNING,
    "lt_year": BusinessStage.LT_YEAR,
    "gt_year": BusinessStage.GT_YEAR,
}

MODE_CALLBACK = {
    "usn": TaxMode.USN,
    "patent": TaxMode.PATENT,
    "npd": TaxMode.NPD,
    "other": TaxMode.OTHER,
    "unknown": TaxMode.UNKNOWN,
}


def stage_label(stage: BusinessStage | None) -> str:
    if stage is None:
        return "—"
    return _STAGE_LABELS[stage]


def mode_label(mode: TaxMode | None) -> str:
    if mode is None:
        return "—"
    return _MODE_LABELS[mode]


def is_profile_empty(profile: Profile | None) -> bool:
    if profile is None:
        return True
    return profile.sphere is None and profile.stage is None and profile.mode is None


def format_profile_show(profile: Profile) -> str:
    return (
        "Вот что я знаю о вашем бизнесе:\n"
        f"Сфера: {profile.sphere or '—'}\n"
        f"Стадия: {stage_label(profile.stage)}\n"
        f"Режим налогообложения: {mode_label(profile.mode)}\n"
        "Что изменить?"
    )
