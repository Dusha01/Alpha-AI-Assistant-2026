from __future__ import annotations

import pytest
from tests.scenarios.harness import Dialog, begin_profile, finish_profile

from src.data.models.enums import BusinessStage, TaxMode
from src.handlers.text import COPY
from src.modules.profile.keyboards import STAGE_BUTTONS

pytestmark = pytest.mark.integration


async def test_coffee_half_year_saves_sphere_and_stage(dialog: Dialog) -> None:
    await begin_profile(dialog)

    turn = await dialog.say("Кофейня, полгода")
    profile = await dialog.profile_row()

    assert profile is not None
    assert profile.sphere == "Кофейня"
    assert profile.stage == BusinessStage.LT_YEAR
    assert "сфера — Кофейня" in turn.text
    assert "Работаю меньше года" in turn.text
    assert COPY["ask_tax_regime"] in turn.text
    assert await dialog.dialog_state() == "ask_tax"


async def test_sphere_without_stage_asks_for_buttons(dialog: Dialog) -> None:
    await begin_profile(dialog)

    turn = await dialog.say("Пекарня")

    assert "Выберите стадию бизнеса:" in turn.text
    assert list(turn.callbacks()) == [data for _, data in STAGE_BUTTONS]
    assert await dialog.dialog_state() == "ask_stage"


async def test_blank_business_line_repeats_the_question(dialog: Dialog) -> None:
    await begin_profile(dialog)

    turn = await dialog.say("   ")
    profile = await dialog.profile_row()

    assert turn.text == COPY["ask_business"]
    assert profile is None or profile.sphere is None
    assert await dialog.dialog_state() == "ask_business"


async def test_skip_on_business_then_stage_without_a_saved_profile(dialog: Dialog) -> None:
    await begin_profile(dialog)

    skipped_business = await dialog.press("profile_skip")
    skipped_stage = await dialog.press("profile_skip")

    assert "Выберите стадию бизнеса:" in skipped_business.text
    assert COPY["smalltalk"] in skipped_stage.text
    assert "Азы финансовой грамотности" in skipped_stage.text
    assert await dialog.dialog_state() == "idle"


async def test_skip_on_stage_without_mode_asks_tax_then_stops(dialog: Dialog) -> None:
    await begin_profile(dialog)
    await dialog.say("Пекарня")

    skipped_stage = await dialog.press("profile_skip")
    skipped_tax = await dialog.press("profile_skip")

    assert COPY["ask_tax_regime"] in skipped_stage.text
    assert COPY["smalltalk"] in skipped_tax.text
    assert await dialog.dialog_state() == "idle"


async def test_skip_on_tax_keeps_existing_mode(dialog: Dialog) -> None:
    await begin_profile(dialog)
    await dialog.say("Пекарня")
    await dialog.press("profile_stage:lt_year")
    user = await dialog.require_user()
    from src.data.repositories.profiles import ProfileRepository

    await ProfileRepository(dialog.db).upsert(user.id, mode=TaxMode.USN)
    await dialog.db.commit()

    turn = await dialog.press("profile_skip")
    profile = await dialog.profile_row()

    assert COPY["smalltalk"] in turn.text
    assert profile is not None
    assert profile.mode == TaxMode.USN
    assert await dialog.dialog_state() == "idle"


@pytest.mark.parametrize(
    ("callback", "stage", "label"),
    [
        ("profile_stage:planning", BusinessStage.PLANNING, "Только планирую"),
        ("profile_stage:lt_year", BusinessStage.LT_YEAR, "Работаю меньше года"),
        ("profile_stage:gt_year", BusinessStage.GT_YEAR, "Работаю больше года"),
    ],
)
async def test_stage_buttons(
    dialog: Dialog,
    callback: str,
    stage: BusinessStage,
    label: str,
) -> None:
    await begin_profile(dialog)
    await dialog.say("Пекарня")

    turn = await dialog.press(callback)
    profile = await dialog.profile_row()

    assert profile is not None
    assert profile.stage == stage
    assert label in turn.text
    assert COPY["ask_tax_regime"] in turn.text


@pytest.mark.parametrize(
    ("callback", "mode", "label"),
    [
        ("profile_mode:usn", TaxMode.USN, "УСН"),
        ("profile_mode:patent", TaxMode.PATENT, "Патент"),
        ("profile_mode:npd", TaxMode.NPD, "Самозанятость (НПД)"),
        ("profile_mode:other", TaxMode.OTHER, "Другой"),
        ("profile_mode:unknown", TaxMode.UNKNOWN, "Не знаю"),
    ],
)
async def test_tax_mode_buttons(dialog: Dialog, callback: str, mode: TaxMode, label: str) -> None:
    await begin_profile(dialog)
    await dialog.say("Кофейня, полгода")

    turn = await dialog.press(callback)
    profile = await dialog.profile_row()

    assert profile is not None
    assert profile.mode == mode
    assert label in turn.text
    assert "Советую" in turn.text
    if mode == TaxMode.UNKNOWN:
        assert COPY["tax_regime_unknown"] in turn.text
    assert await dialog.dialog_state() == "idle"


async def test_profile_card_and_edits(dialog: Dialog) -> None:
    empty = await dialog.say("/profile")
    await finish_profile(dialog, "Кофейня, полгода", "profile_mode:usn")

    shown = await dialog.say("/profile")
    await dialog.press("profile_edit:sphere")
    sphere = await dialog.say("Пекарня")
    await dialog.press("profile_edit:stage")
    stage = await dialog.press("profile_stage:gt_year")
    await dialog.press("profile_edit:mode")
    mode = await dialog.press("profile_mode:patent")
    profile = await dialog.profile_row()

    assert empty.text == COPY["profile_empty"]
    assert "Сфера: Кофейня" in shown.text
    assert "Работаю меньше года" in shown.text
    assert "УСН" in shown.text
    assert list(shown.callbacks()) == [
        "profile_edit:sphere",
        "profile_edit:stage",
        "profile_edit:mode",
    ]
    assert "сфера — Пекарня" in sphere.text
    assert "Работаю больше года" in stage.text
    assert "Патент" in mode.text
    assert profile is not None
    assert profile.sphere == "Пекарня"
    assert profile.stage == BusinessStage.GT_YEAR
    assert profile.mode == TaxMode.PATENT


async def test_profile_and_reminders_commands_leave_the_questionnaire(dialog: Dialog) -> None:
    await begin_profile(dialog)

    profile = await dialog.say("/profile")
    assert profile.text == COPY["profile_empty"]
    assert await dialog.dialog_state() == "idle"

    await begin_profile(dialog)
    reminders = await dialog.say("/reminders")
    await dialog.say("Кофейня, полгода")

    assert reminders.text == COPY["reminders_empty"]
    assert await dialog.profile_row() is None or (await dialog.profile_row()).sphere is None
    assert dialog.knowledge.calls[-1][0] == "Кофейня, полгода"


async def test_remind_phrase_inside_profile_does_not_start_reminder(dialog: Dialog) -> None:
    await begin_profile(dialog)

    turn = await dialog.say("напомни про налог")

    assert "О чём напомнить?" not in turn.text
    assert "ближайший срок" not in turn.text
    assert await dialog.reminder_rows(include_done=True) == []
    assert await dialog.dialog_state() == "ask_stage"
    profile = await dialog.profile_row()
    assert profile is not None
    assert profile.sphere == "напомни про налог"


async def test_reminder_text_is_not_saved_as_business(dialog: Dialog) -> None:
    await dialog.press("remind")

    turn = await dialog.say("Кофейня, полгода")
    shown = await dialog.say("/profile")

    assert COPY["reminder_ask_when"] in turn.text
    assert shown.text == COPY["profile_empty"]
