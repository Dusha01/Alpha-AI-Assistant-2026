from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tests.scenarios.harness import Dialog, finish_profile, freeze_poller

from src.data.models.enums import ReminderRepeat
from src.data.repositories.reminders import ReminderRepository
from src.handlers.text import COPY

pytestmark = pytest.mark.integration

_WHAT = "авансовый платёж по УСН за тест"


async def test_usn_tax_reminder_can_be_quarterly_or_once(make_dialog) -> None:
    quarterly = make_dialog()
    once = make_dialog()
    await quarterly.add_tax_deadline(what=_WHAT, lead_days=14)
    await once.add_tax_deadline(what=_WHAT, lead_days=14)

    asked = await quarterly.say("Напомни про налог")
    offered = await quarterly.press("profile_mode:usn")
    created = await quarterly.press("tax_remind:quarterly")
    once_offer = await once.say("Напомни про налог")
    await once.press("profile_mode:usn")
    once_created = await once.press("tax_remind:once")
    quarterly_row = (await quarterly.reminder_rows())[0]
    once_row = (await once.reminder_rows())[0]

    assert COPY["ask_tax_regime"] in asked.text
    assert "profile_mode:usn" in asked.callbacks()
    assert "УСН" in offered.text
    assert _WHAT in offered.text
    assert "20.12.2026" in offered.text
    assert "14" in offered.text
    assert ("Да", "tax_remind:quarterly") in offered.messages[-1].buttons
    assert ("Только один раз", "tax_remind:once") in offered.messages[-1].buttons
    assert created.text == COPY["tax_created"].format(режим="usn", N=14)
    assert "тестовый справочник" not in created.text
    assert quarterly_row.repeat == ReminderRepeat.QUARTERLY
    assert quarterly_row.is_tax is True
    assert COPY["ask_tax_regime"] in once_offer.text
    assert once_created.text == COPY["tax_created"].format(режим="usn", N=14)
    assert once_row.repeat == ReminderRepeat.ONCE


async def test_patent_offer_uses_seeded_deadline(dialog: Dialog) -> None:
    await dialog.say("Напомни про налог")

    turn = await dialog.press("profile_mode:patent")

    assert "Патент" in turn.text
    assert "оплата патента" in turn.text
    assert "31.12.2026" in turn.text
    assert "30" in turn.text


async def test_npd_has_no_deadline(dialog: Dialog) -> None:
    await dialog.say("Напомни про налог")

    turn = await dialog.press("profile_mode:npd")

    assert "npd" in turn.text
    assert "нет точных сроков" in turn.text
    assert await dialog.reminder_rows(include_done=True) == []


async def test_known_mode_skips_the_questionnaire(dialog: Dialog) -> None:
    await finish_profile(dialog, "Пекарня, больше года", "profile_mode:patent")

    turn = await dialog.say("Напомни про налог")

    assert COPY["ask_tax_regime"] not in turn.text
    assert "оплата патента" in turn.text
    assert "31.12.2026" in turn.text


async def test_saving_mode_without_tax_flag_does_not_offer_tax(dialog: Dialog) -> None:
    turn = await finish_profile(
        dialog,
        "Кофейня, полгода",
        "profile_mode:usn",
        question="Как вести учёт доходов на УСН?",
    )

    assert "ближайший срок" not in turn.text
    assert "Шаблон учёта доходов на УСН" in turn.text
    assert "через 3 дня" in turn.text


async def test_tax_fire_with_material_and_without(
    dialog: Dialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await dialog.add_tax_deadline(what=_WHAT, title="Налоговый шаблон", slug="tax-template")
    await dialog.say("Напомни про налог")
    await dialog.press("profile_mode:usn")
    await dialog.press("tax_remind:once")
    user = await dialog.require_user()
    await ReminderRepository(dialog.db).create(
        user.id,
        text="просто налог",
        repeat=ReminderRepeat.ONCE,
        next_fire_at=datetime.now(UTC) - timedelta(minutes=1),
        is_tax=True,
    )
    material = next(row for row in await dialog.reminder_rows() if row.material_title)
    material.next_fire_at = datetime.now(UTC) - timedelta(minutes=1)
    await dialog.db.commit()
    freeze_poller(monkeypatch, datetime.now(UTC))

    fired = await dialog.tick()
    with_material = next(item.text for item in fired.messages if "Налоговый шаблон" in item.text)
    without = next(item.text for item in fired.messages if "просто налог" in item.text)

    assert "Напоминаю:" in with_material
    assert "Налоговый шаблон" in with_material
    assert "utm_source=tg_bot" in with_material
    assert "utm_campaign=tax" in with_material
    assert "справочнику MVP" not in with_material
    assert without == (
        COPY["reminder_fire_custom"].format(текст_напоминания="просто налог")
        + "\n"
        + COPY["tax_disclaimer"].format(источник="справочнику MVP")
    )
