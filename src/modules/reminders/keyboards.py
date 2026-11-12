from __future__ import annotations

import uuid

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

REPEAT_BUTTONS: tuple[tuple[str, str], ...] = (
    ("Один раз", "reminder_repeat:once"),
    ("Каждую неделю", "reminder_repeat:weekly"),
    ("Каждый месяц", "reminder_repeat:monthly"),
    ("Каждый квартал", "reminder_repeat:quarterly"),
)

CONFIRM_BUTTONS: tuple[tuple[str, str], ...] = (
    ("Да", "reminder_confirm:yes"),
    ("Изменить", "reminder_confirm:edit"),
)

TAX_REPEAT_BUTTONS: tuple[tuple[str, str], ...] = (
    ("Да", "tax_remind:quarterly"),
    ("Только один раз", "tax_remind:once"),
)


def _rows(buttons: tuple[tuple[str, str], ...]) -> list[list[InlineKeyboardButton]]:
    return [[InlineKeyboardButton(text=label, callback_data=data)] for label, data in buttons]


def repeat_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=_rows(REPEAT_BUTTONS))


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=_rows(CONFIRM_BUTTONS))


def tax_repeat_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=_rows(TAX_REPEAT_BUTTONS))


def fire_keyboard(reminder_id: uuid.UUID) -> InlineKeyboardMarkup:
    rid = str(reminder_id)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Готово", callback_data=f"remind_done:{rid}"),
                InlineKeyboardButton(text="Напомнить позже", callback_data=f"remind_later:{rid}"),
                InlineKeyboardButton(text="Отключить", callback_data=f"remind_off:{rid}"),
            ]
        ]
    )


def reminders_list_keyboard(reminder_ids: list[uuid.UUID]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"Изменить #{index + 1}", callback_data=f"remind_edit:{rid}")]
        for index, rid in enumerate(reminder_ids)
    ]
    fallback = [[InlineKeyboardButton(text="—", callback_data="noop")]]
    return InlineKeyboardMarkup(inline_keyboard=rows or fallback)
