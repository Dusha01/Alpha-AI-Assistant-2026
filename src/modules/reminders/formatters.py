from __future__ import annotations

from datetime import datetime

from src.data.models import Reminder
from src.data.models.enums import ReminderRepeat, TaxMode
from src.handlers.text import COPY
from src.modules.profile.labels import mode_label

_REPEAT_LABEL = {
    ReminderRepeat.ONCE: "один раз",
    ReminderRepeat.WEEKLY: "каждую неделю",
    ReminderRepeat.MONTHLY: "каждый месяц",
    ReminderRepeat.QUARTERLY: "каждый квартал",
}


def format_when(dt: datetime) -> str:
    return dt.astimezone().strftime("%d.%m.%Y в %H:%M")


def format_confirm(text: str, when: datetime, repeat: ReminderRepeat) -> str:
    repeat_text = _REPEAT_LABEL[repeat]
    when_text = format_when(when)
    suffix = f", повтор: {repeat_text}" if repeat != ReminderRepeat.ONCE else ""
    return COPY["reminder_confirm"].format(
        текст_напоминания=text,
        когда=f" {when_text}",
        повтор=suffix,
    )


def format_reminders_list(rows: list[Reminder]) -> str:
    if not rows:
        return COPY["reminders_empty"]
    lines = ["Ваши напоминания:"]
    for index, row in enumerate(rows, start=1):
        status = "активно" if row.status.value == "active" else "на паузе"
        lines.append(
            f"{index}. «{row.text}» — {format_when(row.next_fire_at)} "
            f"({_REPEAT_LABEL[row.repeat]}, {status})"
        )
    lines.append("Выберите напоминание, чтобы изменить частоту или отключить.")
    return "\n".join(lines)


def format_tax_offer(mode: TaxMode, what: str, due: str, lead: int) -> str:
    return COPY["tax_offer"].format(
        режим=mode_label(mode),
        что_платить=what,
        дата=due,
        N=lead,
    )
