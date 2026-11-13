from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from tests.scenarios.harness import (
    Dialog,
    begin_profile,
    complete_custom,
    finish_profile,
    freeze_poller,
)

from src.data.models import User
from src.data.models.enums import BusinessStage, ReminderRepeat, ReminderStatus
from src.data.repositories.reminders import ReminderRepository
from src.handlers.text import COPY
from src.modules.knowledge.service import BotReply

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("command", ["/start", "/help", "/cancel"])
async def test_reset_commands_leave_reminder_text_step(dialog: Dialog, command: str) -> None:
    await dialog.press("remind")

    left = await dialog.say(command)
    await dialog.say("завтра в 10:00")

    assert await dialog.dialog_state() == "idle"
    assert COPY["reminder_ask_when"] not in left.text
    assert dialog.knowledge.calls[-1][0] == "завтра в 10:00"
    assert await dialog.reminder_rows(include_done=True) == []


async def test_profile_and_reminders_commands_drop_the_when_step(dialog: Dialog) -> None:
    await dialog.press("remind")
    await dialog.say("молоко")

    profile = await dialog.say("/profile")
    assert profile.text == COPY["profile_empty"]
    assert await dialog.dialog_state() == "idle"

    await dialog.press("remind")
    await dialog.say("молоко")
    listed = await dialog.say("/reminders")
    await dialog.say("завтра в 10:00")

    assert listed.text == COPY["reminders_empty"]
    assert await dialog.dialog_state() == "idle"
    assert dialog.knowledge.calls[-1][0] == "завтра в 10:00"


async def test_help_on_when_step_is_help_not_a_time_error(dialog: Dialog) -> None:
    await dialog.press("remind")
    await dialog.say("отчёт")

    turn = await dialog.say("/help")

    assert turn.text == COPY["help"]
    assert COPY["reminder_bad_time"] not in turn.text
    assert await dialog.dialog_state() == "idle"


async def test_question_on_confirm_stays_in_reminder_until_reset(dialog: Dialog) -> None:
    dialog.knowledge.reply("Как оформить визу в Китай?", BotReply(COPY["not_found"]))
    await dialog.press("remind")
    await dialog.say("отчёт")
    await dialog.say("завтра в 10:00")
    await dialog.press("reminder_repeat:once")

    question = await dialog.say("Как оформить визу в Китай?")
    assert question.text == COPY["not_found"]
    assert await dialog.dialog_state() == "reminder_confirm"

    help_turn = await dialog.say("/help")
    assert help_turn.text == COPY["help"]
    assert await dialog.dialog_state() == "idle"


async def test_start_and_help_reset_business_prompt(dialog: Dialog) -> None:
    await begin_profile(dialog)

    started = await dialog.say("/start")
    assert started.text == COPY["start"]
    assert COPY["ask_business"] not in started.text
    assert await dialog.dialog_state() == "idle"

    await begin_profile(dialog)
    helped = await dialog.say("/help")
    assert helped.text == COPY["help"]
    assert await dialog.dialog_state() == "idle"


async def test_command_shapes_and_polite_reminder_phrase(dialog: Dialog) -> None:
    start = await dialog.say("/start хочу кредит")
    folded = await dialog.say("/StArT")
    help_at = await dialog.say("/help@OtherBot")
    polite = await dialog.say("пожалуйста напомни про налог")

    assert start.text == COPY["start"]
    assert folded.text == COPY["start"]
    assert help_at.text == COPY["help"]
    assert dialog.knowledge.calls[-1][0] == "пожалуйста напомни про налог"
    assert COPY["ask_tax_regime"] not in polite.text


@pytest.mark.parametrize("phrase", ["НАПОМНИ ПРО НАЛОГ", "НапомниПроНалог"])
async def test_tax_intent_ignores_case_and_spaces(dialog: Dialog, phrase: str) -> None:
    turn = await dialog.say(phrase)

    assert COPY["ask_tax_regime"] in turn.text
    assert "profile_mode:usn" in turn.callbacks()


async def test_bare_remind_asks_what_to_remember(dialog: Dialog) -> None:
    turn = await dialog.say("напомни")

    assert turn.text == "О чём напомнить?"
    assert await dialog.reminder_rows(include_done=True) == []


async def test_odd_time_phrases(dialog: Dialog) -> None:
    await dialog.press("remind")
    await dialog.say("срок")

    yesterday = await dialog.say("вчера")
    bad_clock = await dialog.say("в 25:00")
    zero = await dialog.say("через 0 минут")
    assert yesterday.text == COPY["reminder_bad_time"]
    assert bad_clock.text == COPY["reminder_bad_time"]
    assert zero.text == COPY["reminder_ask_repeat"]

    await dialog.press("remind")
    await dialog.say("ещё срок")
    tomorrow = await dialog.say("завтра")
    assert tomorrow.text == COPY["reminder_ask_repeat"]


async def test_business_line_does_not_read_tax_mode_from_the_tail(dialog: Dialog) -> None:
    await begin_profile(dialog)

    turn = await dialog.say("кофейня, полгода, УСН")
    profile = await dialog.profile_row()

    assert profile is not None
    assert profile.sphere == "кофейня"
    assert profile.stage == BusinessStage.LT_YEAR
    assert profile.mode is None
    assert COPY["ask_tax_regime"] in turn.text


async def test_emoji_sphere_is_stored(dialog: Dialog) -> None:
    await begin_profile(dialog)

    await dialog.say("🍰")
    profile = await dialog.profile_row()

    assert profile is not None
    assert profile.sphere == "🍰"
    assert await dialog.dialog_state() == "ask_stage"


async def test_blank_sphere_edit_offers_profile_again(dialog: Dialog) -> None:
    await finish_profile(dialog, "Пекарня, полгода", "profile_mode:other")
    await dialog.press("profile_edit:sphere")
    await dialog.say("   ")
    dialog.knowledge.reply(
        "Что дальше?",
        BotReply("Дальше.", feedback=True, material_title="Дальше"),
    )

    turn = await dialog.say("Что дальше?")
    profile = await dialog.profile_row()

    assert profile is not None
    assert profile.sphere == ""
    assert COPY["ask_business"] in turn.text


async def test_markup_question_is_passed_through(dialog: Dialog) -> None:
    question = ('<b>учёт</b> "доходов" ' + ("и ещё " * 40)).strip()
    dialog.knowledge.reply(question, BotReply("Принял как есть."))

    turn = await dialog.say(question)

    assert dialog.knowledge.calls[-1] == (question, question)
    assert turn.text == "Принял как есть."


async def test_feedback_buttons_work_without_a_prior_answer(dialog: Dialog) -> None:
    yes = await dialog.press("feedback_yes")
    no = await dialog.press("feedback_no")

    assert yes.alerts == ["Спасибо за отзыв!"]
    assert yes.messages == []
    assert no.text == COPY["feedback_no"]
    assert await dialog.dialog_state() is None


async def test_unknown_callback_sends_no_message(dialog: Dialog) -> None:
    unknown = await dialog.press("noop")

    assert unknown.messages == []
    assert unknown.alerts == [None]


async def test_stale_stage_and_mode_buttons_overwrite_profile(dialog: Dialog) -> None:
    await dialog.say("/start")

    stage = await dialog.press("profile_stage:gt_year")
    mode = await dialog.press("profile_mode:patent")
    profile = await dialog.profile_row()

    assert "Работаю больше года" in stage.text
    assert COPY["ask_tax_regime"] in stage.text
    assert "Патент" in mode.text
    assert profile is not None
    assert profile.stage == BusinessStage.GT_YEAR
    assert profile.mode is not None
    assert profile.mode.value == "patent"


async def test_skip_while_idle_answers_smalltalk(dialog: Dialog) -> None:
    await dialog.say("/start")

    turn = await dialog.press("profile_skip")

    assert COPY["smalltalk"] in turn.text
    assert "Азы финансовой грамотности" in turn.text
    assert await dialog.dialog_state() == "idle"


async def test_confirm_and_repeat_without_payload_do_not_create(dialog: Dialog) -> None:
    await dialog.say("/start")

    repeat = await dialog.press("reminder_repeat:once")
    confirm = await dialog.press("reminder_confirm:yes")

    assert repeat.text == COPY["error_general"]
    assert confirm.text == COPY["error_general"]
    assert await dialog.reminder_rows(include_done=True) == []


async def test_tax_button_without_draft_is_an_error(dialog: Dialog) -> None:
    await dialog.say("/start")

    turn = await dialog.press("tax_remind:quarterly")

    assert turn.text == COPY["error_general"]
    assert await dialog.reminder_rows(include_done=True) == []


async def test_missing_reminder_buttons_do_not_crash(dialog: Dialog) -> None:
    missing = uuid4()

    off = await dialog.press(f"remind_off:{missing}")
    later = await dialog.press(f"remind_later:{missing}")
    done = await dialog.press(f"remind_done:{missing}")
    broken = await dialog.press("remind_edit:not-a-uuid")

    assert off.text == COPY["reminder_off"]
    assert later.text == "Хорошо, напомню чуть позже."
    assert done.text == "Спасибо! Рад, что вы в курсе."
    assert broken.text == COPY["error_general"]


async def test_second_tax_yes_does_not_duplicate(dialog: Dialog) -> None:
    await dialog.add_tax_deadline()
    await dialog.say("Напомни про налог")
    await dialog.press("profile_mode:usn")

    first = await dialog.press("tax_remind:quarterly")
    second = await dialog.press("tax_remind:quarterly")

    assert "usn" in first.text
    assert second.text == COPY["error_general"]
    assert len(await dialog.reminder_rows(include_done=True)) == 1


async def test_second_confirm_does_not_duplicate(dialog: Dialog) -> None:
    await complete_custom(dialog, "один раз", "завтра в 10:00")

    again = await dialog.press("reminder_confirm:yes")

    assert again.text == COPY["error_general"]
    assert len(await dialog.reminder_rows(include_done=True)) == 1


async def test_callback_without_message_or_user_is_silent(dialog: Dialog) -> None:
    no_message = await dialog.press("ask", with_message=False)
    no_user = await dialog.press("profile_skip", with_user=False)

    assert no_message.messages == []
    assert no_user.messages == []
    assert no_message.alerts == [None]
    assert no_user.alerts == [None]


async def test_dialogs_of_two_users_stay_apart(make_dialog) -> None:
    first = make_dialog()
    second = make_dialog()
    await first.press("remind")
    await first.say("молоко для первого")

    profile = await second.say("/profile")
    continued = await first.say("завтра в 10:00")

    assert profile.text == COPY["profile_empty"]
    assert continued.text == COPY["reminder_ask_repeat"]
    assert await second.profile_row() is None
    assert await first.dialog_state() == "reminder_repeat"
    assert await second.dialog_state() == "idle"


async def test_foreign_reminder_id_can_pause_it(make_dialog) -> None:
    owner = make_dialog()
    other = make_dialog()
    await complete_custom(owner, "чужое", "завтра в 10:00")
    reminder_id = (await owner.reminder_rows())[0].id

    turn = await other.press(f"remind_off:{reminder_id}")
    row = (await owner.reminder_rows())[0]

    assert turn.text == COPY["reminder_off"]
    assert row.status == ReminderStatus.PAUSED


async def test_failed_send_is_retried_on_the_next_tick(
    dialog: Dialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await complete_custom(dialog, "повтор", "через 1 минуту")
    due = (await dialog.reminder_rows())[0].next_fire_at
    freeze_poller(monkeypatch, due + timedelta(minutes=1))
    dialog.recording.fail_sends = 1

    failed = await dialog.tick()
    sent = await dialog.tick()
    extra = await dialog.tick()

    assert failed.messages == []
    assert "повтор" in sent.text
    assert extra.messages == []


async def test_missing_user_is_not_sent_and_stays_active(
    dialog: Dialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await dialog.say("/start")
    owner = await dialog.require_user()
    await ReminderRepository(dialog.db).create(
        owner.id,
        text="сирота",
        repeat=ReminderRepeat.ONCE,
        next_fire_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    await dialog.db.commit()
    original = dialog.db.get

    async def hide_user(entity, ident, **kwargs):
        if entity is User:
            return None
        return await original(entity, ident, **kwargs)

    monkeypatch.setattr(dialog.db, "get", hide_user)
    freeze_poller(monkeypatch, datetime.now(UTC))
    try:
        fired = await dialog.tick()
    finally:
        monkeypatch.undo()
    row = (await dialog.reminder_rows(include_done=True))[0]

    assert fired.messages == []
    assert row.status == ReminderStatus.ACTIVE
    assert row.text == "сирота"


async def test_quarterly_fire_moves_the_next_date(
    dialog: Dialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await dialog.say("/start")
    user = await dialog.require_user()
    when = datetime(2026, 11, 1, tzinfo=UTC)
    await ReminderRepository(dialog.db).create(
        user.id,
        text="квартал",
        repeat=ReminderRepeat.QUARTERLY,
        next_fire_at=when,
    )
    await dialog.db.commit()
    freeze_poller(monkeypatch, when + timedelta(hours=1))

    fired = await dialog.tick()
    quiet = await dialog.tick()
    row = (await dialog.reminder_rows())[0]

    assert "квартал" in fired.text
    assert quiet.messages == []
    assert row.status == ReminderStatus.ACTIVE
    assert row.next_fire_at == when + timedelta(days=91)


async def test_partial_profiles_pick_different_routes(make_dialog) -> None:
    coffee = make_dialog()
    marketing = make_dialog()
    await finish_profile(coffee, "кофейня, только планирую", "profile_skip")
    await finish_profile(marketing, "маркетинг, только планирую", "profile_skip")

    coffee_route = await coffee.press("materials")
    marketing_route = await marketing.press("materials")

    assert "Азы финансовой грамотности" in coffee_route.text
    assert "Маркетинг для соло-предпринимателя" not in coffee_route.text
    assert "Маркетинг для соло-предпринимателя" in marketing_route.text
    assert "Азы финансовой грамотности" not in marketing_route.text


async def test_tax_and_marketing_in_one_question_keep_usn_topic(dialog: Dialog) -> None:
    await finish_profile(dialog, "Пекарня, полгода", "profile_mode:other")
    question = "налог и маркетинг"
    dialog.knowledge.reply(
        question,
        BotReply("Смотрю налог.", feedback=True, material_title="Налог"),
    )

    await dialog.say(question)
    picked = await dialog.press("materials")

    assert (await dialog.payload())["last_topic"] == "usn"
    assert "Шаблон учёта доходов на УСН" in picked.text
    assert "Маркетинг для соло-предпринимателя" not in picked.text
