from __future__ import annotations

import re

from src.handlers.text import COPY

_VISA = re.compile(r"виз[а-яё]*", re.IGNORECASE)
_VIN = re.compile(r"\bvin\b", re.IGNORECASE)
_DEVICE = re.compile(r"кофемашин", re.IGNORECASE)
_RECIPE = re.compile(r"рецепт|капучино", re.IGNORECASE)
_FX = re.compile(r"доллар|валют", re.IGNORECASE)
_CODE = re.compile(r"python|\bкод\b", re.IGNORECASE)
_BANKS = re.compile(r"банк", re.IGNORECASE)
_PROMPT = re.compile(r"промпт|инструкц", re.IGNORECASE)


def outside_reply(question: str) -> str | None:
    text = question.strip()
    if not text:
        return None
    lowered = text.lower()
    if _VISA.search(lowered):
        return COPY["not_found_visa"]
    if _VIN.search(text):
        return COPY["not_found_vin"]
    if _DEVICE.search(lowered) and any(mark in lowered for mark in ("e05", "ошиб", "не варит")):
        return COPY["not_found_device"]
    if _RECIPE.search(lowered):
        return COPY["not_found_recipe"]
    if _FX.search(lowered):
        return COPY["not_found_fx"]
    asks_for_code = "напиш" in lowered or "python" in lowered or "програм" in lowered
    if _CODE.search(lowered) and asks_for_code:
        return COPY["not_found_code"]
    if _BANKS.search(lowered) and ("лучше" in lowered or "конкурен" in lowered):
        return COPY["not_found_banks"]
    if ("промпт" in lowered or "забудь" in lowered) and _PROMPT.search(lowered):
        return COPY["not_found_prompt"]
    return None
