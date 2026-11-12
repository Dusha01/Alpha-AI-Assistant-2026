from __future__ import annotations

import pytest
from tests.scenarios.harness import Dialog

from src.handlers.text import COPY, START_BUTTONS

pytestmark = pytest.mark.integration


async def test_start_and_mention(dialog: Dialog) -> None:
    plain = await dialog.say("/start")
    mentioned = await dialog.say("/start@AlfaCourseBot")

    for turn in (plain, mentioned):
        assert turn.messages[0].text == COPY["start"]
        expected = tuple(zip(START_BUTTONS, ("ask", "materials", "remind"), strict=True))
        assert turn.messages[0].buttons == expected


async def test_help_unknown_sticker_and_too_long(make_dialog) -> None:
    dialog = make_dialog()
    help_turn = await dialog.say("/help")
    unknown = await dialog.say("/nope")
    sticker = await dialog.send_sticker()

    short = make_dialog(max_length=20)
    too_long = await short.say("я" * 21)

    assert help_turn.text == COPY["help"]
    assert unknown.text == COPY["unknown_command"]
    assert sticker.text == COPY["non_text"]
    assert too_long.text == COPY["too_long"]
    assert short.knowledge.calls == []


async def test_blank_and_greeting_go_to_knowledge(dialog: Dialog) -> None:
    blank = await dialog.say(" \n\t ")
    greeting = await dialog.say("привет")

    assert dialog.knowledge.calls[0] == ("", "")
    assert dialog.knowledge.calls[1] == ("привет", "привет")
    assert COPY["smalltalk"] not in blank.text
    assert COPY["smalltalk"] not in greeting.text
    assert blank.text == COPY["not_found"]
    assert greeting.text == COPY["not_found"]


async def test_start_buttons_ask_recommend_and_remind(dialog: Dialog) -> None:
    await dialog.say("/start")

    asked = await dialog.press("ask")
    answer = await dialog.say("Как платить налог?")
    materials = await dialog.press("materials")
    reminder = await dialog.press("remind")

    assert asked.text == COPY["smalltalk"]
    assert asked.alerts == [None]
    assert dialog.knowledge.calls[-1][0] == "Как платить налог?"
    assert answer.text == COPY["not_found"]
    assert "Азы финансовой грамотности" in materials.text
    assert reminder.text == "О чём напомнить?"
    assert await dialog.dialog_state() == "reminder_text"


async def test_handler_exception_returns_error_general(dialog: Dialog) -> None:
    dialog.knowledge.fail.add("сломайся")

    failed = await dialog.say("сломайся")
    recovered = await dialog.say("/help")

    assert failed.text == COPY["error_general"]
    assert recovered.text == COPY["help"]
