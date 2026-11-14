from __future__ import annotations

from datetime import timedelta

import pytest
from tests.scenarios.harness import Dialog, freeze_poller

from src.data.models.enums import BusinessStage, ReminderRepeat, TaxMode
from src.handlers.text import COPY
from src.modules.knowledge.service import BotReply

pytestmark = pytest.mark.integration

_QUESTION = "Как вести учёт доходов на УСН?"
_CREDIT = "Как получить кредит?"
_VISA = "Как оформить визу в Китай?"


async def test_jury_question_profile_and_recommendation(dialog: Dialog) -> None:
    source = COPY["answer_source"].format(
        material_name="Книга учёта",
        url="https://example.alfacourse.local/usn?utm_source=tg_bot",
    )
    dialog.knowledge.reply(
        _QUESTION,
        BotReply(
            f"Доходы на УСН записывают в книгу учёта.\n\n{source}",
            feedback=True,
            material_title="Книга учёта",
        ),
    )

    answer = await dialog.say(_QUESTION)
    business = await dialog.say("Кофейня, полгода")
    picked = await dialog.press("profile_mode:usn")
    profile = await dialog.profile_row()

    assert "Доходы на УСН записывают в книгу учёта." in answer.text
    assert "Книга учёта" in answer.text
    assert COPY["feedback"] in answer.text
    assert COPY["ask_business"] in answer.text
    assert profile is not None
    assert profile.sphere == "Кофейня"
    assert profile.stage == BusinessStage.LT_YEAR
    assert profile.mode == TaxMode.USN
    assert "Кофейня" in business.text
    assert COPY["ask_tax_regime"] in business.text
    assert "Шаблон учёта доходов на УСН" in picked.text
    assert "у вас кофейня на УСН" in picked.text
    assert "Курс «УСН без ошибок»" in picked.text
    assert "разобрать типовые ошибки учёта и отчётности" in picked.text
    assert "utm_source=tg_bot" in picked.text
    assert "через 3 дня" in picked.text
    assert "полный текст урока" not in picked.text


async def test_jury_tax_reminder(dialog: Dialog, monkeypatch: pytest.MonkeyPatch) -> None:
    await dialog.add_tax_deadline(what="авансовый платёж по УСН за тест", lead_days=14)

    asked = await dialog.say("Напомни про налог")
    offered = await dialog.press("profile_mode:usn")
    created = await dialog.press("tax_remind:quarterly")
    listed = await dialog.say("/reminders")
    edit = next(data for data in listed.callbacks() if data.startswith("remind_edit:"))
    choices = await dialog.press(edit)
    weekly = next(data for data in choices.callbacks() if data.endswith(":weekly"))
    changed = await dialog.press(weekly)
    row = (await dialog.reminder_rows())[0]
    freeze_poller(monkeypatch, row.next_fire_at + timedelta(minutes=1))
    fired = await dialog.tick()

    assert COPY["ask_tax_regime"] in asked.text
    assert "авансовый платёж по УСН за тест" in offered.text
    assert created.text == COPY["tax_created"].format(режим="usn", N=14)
    assert "авансовый платёж по УСН за тест" in listed.text
    assert changed.text == COPY["reminder_changed"].format(новая_частота="каждую неделю")
    assert row.repeat == ReminderRepeat.WEEKLY
    assert "Налоговый шаблон" in fired.text


async def test_jury_unclear_question_and_missing_answer(dialog: Dialog) -> None:
    dialog.knowledge.reply(
        _CREDIT,
        BotReply(
            COPY["clarify"].format(
                variant_1="кредит на открытие",
                variant_2="оборотные средства",
            )
        ),
    )
    dialog.knowledge.reply(_VISA, BotReply(COPY["not_found"]))

    clarify = await dialog.say(_CREDIT)
    missing = await dialog.say(_VISA)

    assert "кредит на открытие" in clarify.text
    assert "оборотные средства" in clarify.text
    assert COPY["feedback"] not in clarify.text
    assert missing.text == COPY["not_found"]
    assert COPY["ask_business"] not in missing.text
