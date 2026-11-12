from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

STAGE_BUTTONS: tuple[tuple[str, str], ...] = (
    ("Только планирую", "profile_stage:planning"),
    ("Работаю меньше года", "profile_stage:lt_year"),
    ("Работаю больше года", "profile_stage:gt_year"),
)

TAX_BUTTONS: tuple[tuple[str, str], ...] = (
    ("УСН", "profile_mode:usn"),
    ("Патент", "profile_mode:patent"),
    ("Самозанятость (НПД)", "profile_mode:npd"),
    ("Другой", "profile_mode:other"),
    ("Не знаю", "profile_mode:unknown"),
)

EDIT_BUTTONS: tuple[tuple[str, str], ...] = (
    ("Сфера", "profile_edit:sphere"),
    ("Стадия", "profile_edit:stage"),
    ("Режим", "profile_edit:mode"),
)


def skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="profile_skip")],
        ]
    )


def _rows(buttons: tuple[tuple[str, str], ...]) -> list[list[InlineKeyboardButton]]:
    return [[InlineKeyboardButton(text=label, callback_data=data)] for label, data in buttons]


def stage_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=_rows(STAGE_BUTTONS))


def tax_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=_rows(TAX_BUTTONS))


def profile_edit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=_rows(EDIT_BUTTONS))
