from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from tests.scenarios.harness import Dialog, complete_custom, freeze_poller, local_when

from src.data.models.enums import ReminderRepeat, ReminderStatus
from src.data.repositories.reminders import ReminderRepository
from src.handlers.text import COPY
from src.modules.reminders.keyboards import REPEAT_BUTTONS

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("repeat", "label"),
    [
        ("once", None),
        ("weekly", "каждую неделю"),
        ("monthly", "каждый месяц"),
        ("quarterly", "каждый квартал"),
    ],
)
async def test_custom_reminder_confirms_before_create(
    dialog: Dialog,
    repeat: str,
    label: str | None,
) -> None:
    await dialog.press("remind")
    asked_when = await dialog.say("купить молоко")
    asked_repeat = await dialog.say("завтра в 10:00")
    confirmed = await dialog.press(f"reminder_repeat:{repeat}")
    created = await dialog.press("reminder_confirm:yes")
    row = (await dialog.reminder_rows())[0]
    local = local_when(row.next_fire_at)

    assert asked_when.text == COPY["reminder_ask_when"]
    assert asked_repeat.text == COPY["reminder_ask_repeat"]
    assert list(asked_repeat.callbacks()) == [data for _, data in REPEAT_BUTTONS]
    assert "купить молоко" in confirmed.text
    assert "Всё верно?" in confirmed.text
    if label is None:
        assert "повтор:" not in confirmed.text
    else:
        assert label in confirmed.text
    assert created.text == COPY["reminder_created"]
    assert row.repeat == ReminderRepeat(repeat)
    assert row.text == "купить молоко"
    assert local.hour == 10 and local.minute == 0
    assert local.date() == datetime.now(ZoneInfo("Asia/Vladivostok")).date() + timedelta(days=1)


async def test_edit_restarts_the_flow(dialog: Dialog) -> None:
    await dialog.press("remind")
    await dialog.say("черновик")
    await dialog.say("завтра в 10:00")
    await dialog.press("reminder_repeat:once")

    restarted = await dialog.press("reminder_confirm:edit")

    assert restarted.text == "О чём напомнить?"
    assert await dialog.reminder_rows(include_done=True) == []
    assert await dialog.dialog_state() == "reminder_text"


async def test_quick_phrase_keeps_text_and_asks_when(dialog: Dialog) -> None:
    asked = await dialog.say("Напомни в пятницу продолжить курс")
    await dialog.say("в пятницу вечером")
    confirmed = await dialog.press("reminder_repeat:once")

    assert asked.text == COPY["reminder_ask_when"]
    assert "продолжить курс" in confirmed.text
    assert not confirmed.text.startswith("Напомни")
    assert "напомни" not in confirmed.text.lower().split("«")[-1].split("»")[0]
    local = local_when(datetime.fromisoformat(str((await dialog.payload())["reminder_when"])))
    assert local.weekday() == 4
    assert local.hour == 19


async def test_time_phrases_land_on_different_instants(make_dialog) -> None:
    tomorrow = make_dialog()
    friday = make_dialog()
    soon = make_dialog()
    before = datetime.now(UTC)

    await complete_custom(tomorrow, "завтра", "завтра в 10:00")
    await friday.say("Напомни про пятницу")
    await friday.say("в пятницу вечером")
    await friday.press("reminder_repeat:once")
    await friday.press("reminder_confirm:yes")
    await complete_custom(soon, "скоро", "через 1 минуту")

    tomorrow_at = (await tomorrow.reminder_rows())[0].next_fire_at
    friday_at = (await friday.reminder_rows())[0].next_fire_at
    soon_at = (await soon.reminder_rows())[0].next_fire_at

    assert len({tomorrow_at, friday_at, soon_at}) == 3
    assert local_when(tomorrow_at).hour == 10
    assert local_when(friday_at).hour == 19
    assert before + timedelta(seconds=50) <= soon_at <= before + timedelta(seconds=80)


async def test_bad_and_past_time_stay_on_the_when_step(dialog: Dialog) -> None:
    await dialog.press("remind")
    await dialog.say("отчёт")

    garbage = await dialog.say("никогда")
    past = await dialog.say("сегодня в 00:00")
    moved = await dialog.say("завтра в 10:00")

    assert garbage.text == COPY["reminder_bad_time"]
    assert past.text == COPY["reminder_past"]
    assert moved.text == COPY["reminder_ask_repeat"]
    assert await dialog.dialog_state() == "reminder_repeat"


async def test_list_empty_then_change_frequency(dialog: Dialog) -> None:
    empty = await dialog.say("/reminders")
    await complete_custom(dialog, "позвонить", "завтра в 10:00")

    listed = await dialog.say("/reminders")
    edit = next(data for data in listed.callbacks() if data.startswith("remind_edit:"))
    choices = await dialog.press(edit)
    weekly = next(data for data in choices.callbacks() if data.endswith(":weekly"))
    changed = await dialog.press(weekly)
    row = (await dialog.reminder_rows())[0]

    assert empty.text == COPY["reminders_empty"]
    assert "позвонить" in listed.text
    assert choices.text == COPY["reminder_ask_repeat"]
    assert changed.text == COPY["reminder_changed"].format(новая_частота="каждую неделю")
    assert row.repeat == ReminderRepeat.WEEKLY


async def test_fire_custom_course_and_buttons(
    dialog: Dialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await complete_custom(dialog, "купить молоко", "завтра в 10:00")
    user = await dialog.require_user()
    course = await ReminderRepository(dialog.db).create(
        user.id,
        text="курс",
        repeat=ReminderRepeat.ONCE,
        next_fire_at=datetime.now(UTC) - timedelta(minutes=5),
        material_title="Курс по учёту",
        material_url="https://example.alfacourse.local/course",
    )
    weekly = await ReminderRepository(dialog.db).create(
        user.id,
        text="еженедельно",
        repeat=ReminderRepeat.WEEKLY,
        next_fire_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    custom = next(row for row in await dialog.reminder_rows() if row.text == "купить молоко")
    custom.next_fire_at = datetime.now(UTC) - timedelta(minutes=5)
    await dialog.db.commit()
    freeze_poller(monkeypatch, datetime.now(UTC) + timedelta(minutes=1))

    fired = await dialog.tick()
    texts = [item.text for item in fired.messages]
    custom_text = next(item for item in texts if "купить молоко" in item)
    course_text = next(item for item in texts if "Курс по учёту" in item)
    done = next(
        data
        for item in fired.messages
        if "купить молоко" in item.text
        for _, data in item.buttons
        if data.startswith("remind_done:")
    )
    later = next(
        data
        for item in fired.messages
        if "еженедельно" in item.text
        for _, data in item.buttons
        if data.startswith("remind_later:")
    )
    off = next(
        data
        for item in fired.messages
        if "еженедельно" in item.text
        for _, data in item.buttons
        if data.startswith("remind_off:")
    )

    assert custom_text == COPY["reminder_fire_custom"].format(текст_напоминания="купить молоко")
    assert "Курс по учёту" in course_text
    assert "utm_source=tg_bot" in course_text
    thanks = await dialog.press(done)
    before_later = next(
        row.next_fire_at
        for row in await dialog.reminder_rows(include_done=True)
        if row.id == weekly.id
    )
    postponed = await dialog.press(later)
    after_later = await dialog.reminder(weekly.id)
    disabled = await dialog.press(off)
    again = await dialog.tick()

    assert thanks.text == "Спасибо! Рад, что вы в курсе."
    assert postponed.text == "Хорошо, напомню чуть позже."
    assert after_later.next_fire_at - before_later == timedelta(minutes=60)
    assert disabled.text == COPY["reminder_off"]
    assert again.messages == []
    done_row = await dialog.reminder(custom.id)
    paused = await dialog.reminder(weekly.id)
    course_row = await dialog.reminder(course.id)
    assert done_row.status == ReminderStatus.DONE
    assert paused.status == ReminderStatus.PAUSED
    assert course_row.status == ReminderStatus.DONE


async def test_one_minute_reminder_is_sent_without_sleep(
    dialog: Dialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await complete_custom(dialog, "демо", "через 1 минуту")
    due = (await dialog.reminder_rows())[0].next_fire_at
    freeze_poller(monkeypatch, due + timedelta(minutes=1))

    first = await dialog.tick()
    second = await dialog.tick()

    assert "демо" in first.text
    assert second.messages == []
