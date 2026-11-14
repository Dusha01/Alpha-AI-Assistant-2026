from __future__ import annotations

import pytest
from tests.scenarios.harness import NEUTRAL_QUESTION, Dialog, finish_profile

from src.handlers.text import COPY
from src.modules.knowledge.service import BotReply

pytestmark = pytest.mark.integration

USN_QUESTION = "Как вести учёт доходов на УСН?"
VISA_QUESTION = "Как оформить визу в Китай?"
CREDIT_QUESTION = "Как получить кредит?"
FREE_CLARIFY = "Что делать с бизнесом?"


def _answer(title: str = "Книга учёта") -> BotReply:
    source = COPY["answer_source"].format(
        material_name=title,
        url="https://example.alfacourse.local/usn?utm_source=tg_bot",
    )
    return BotReply(
        f"Доходы фиксируют в книге учёта.\n\n{source}",
        feedback=True,
        material_title=title,
    )


async def test_answer_shows_source_feedback_and_business_prompt(dialog: Dialog) -> None:
    dialog.knowledge.reply(USN_QUESTION, _answer())

    turn = await dialog.say(USN_QUESTION)

    assert "Доходы фиксируют в книге учёта." in turn.text
    assert "Подробнее в материале «Книга учёта»" in turn.text
    assert "utm_source=tg_bot" in turn.text
    assert COPY["feedback"] in turn.text
    assert ("Да", "feedback_yes") in turn.messages[1].buttons
    assert ("Нет", "feedback_no") in turn.messages[1].buttons
    assert COPY["ask_business"] in turn.text
    assert (await dialog.payload())["follow_material"] == "Книга учёта"
    assert (await dialog.payload())["last_topic"] == "usn"


async def test_feedback_yes_and_no(dialog: Dialog) -> None:
    dialog.knowledge.reply(USN_QUESTION, _answer())
    await dialog.say(USN_QUESTION)

    yes = await dialog.press("feedback_yes")
    no = await dialog.press("feedback_no")

    assert yes.messages == []
    assert yes.alerts == ["Спасибо за отзыв!"]
    assert no.text == COPY["feedback_no"]
    assert await dialog.dialog_state() == "ask_business"


async def test_no_business_prompt_when_sphere_known(dialog: Dialog) -> None:
    await finish_profile(dialog, "Пекарня, полгода", "profile_mode:other")
    dialog.knowledge.reply(USN_QUESTION, _answer())

    turn = await dialog.say(USN_QUESTION)

    assert COPY["feedback"] in turn.text
    assert COPY["ask_business"] not in turn.text


async def test_visa_question_is_not_found(dialog: Dialog) -> None:
    dialog.knowledge.reply(VISA_QUESTION, BotReply(COPY["not_found"]))

    turn = await dialog.say(VISA_QUESTION)

    assert turn.text == COPY["not_found"]
    assert COPY["feedback"] not in turn.text
    assert COPY["ask_business"] not in turn.text
    assert len(turn.messages) == 1


async def test_related_material_when_answer_is_weak(dialog: Dialog) -> None:
    text = COPY["not_found_related"].format(
        material_name="Соседний материал",
        benefit="поможет с учётом",
        url="https://example.alfacourse.local/related?utm_source=tg_bot",
    )
    dialog.knowledge.reply("Почти про учёт", BotReply(text, material_title="Соседний материал"))

    turn = await dialog.say("Почти про учёт")

    assert "Соседний материал" in turn.text
    assert "поможет с учётом" in turn.text
    assert "utm_source=tg_bot" in turn.text
    assert COPY["feedback"] not in turn.text
    assert (await dialog.payload())["follow_material"] == "Соседний материал"


async def test_clarify_with_variants_and_free_form(dialog: Dialog) -> None:
    dialog.knowledge.reply(
        CREDIT_QUESTION,
        BotReply(
            COPY["clarify"].format(
                variant_1="кредит на открытие",
                variant_2="оборотные средства",
            )
        ),
    )
    dialog.knowledge.reply(FREE_CLARIFY, BotReply(COPY["clarify_free"]))

    clarify = await dialog.say(CREDIT_QUESTION)
    free = await dialog.say(FREE_CLARIFY)

    assert "кредит на открытие" in clarify.text
    assert "оборотные средства" in clarify.text
    assert COPY["feedback"] not in clarify.text
    assert free.text == COPY["clarify_free"]
    assert COPY["ask_business"] not in free.text


async def test_llm_error_has_no_feedback_and_no_profile_prompt(dialog: Dialog) -> None:
    dialog.knowledge.reply(USN_QUESTION, BotReply(COPY["error_llm"]))

    turn = await dialog.say(USN_QUESTION)

    assert turn.text == COPY["error_llm"]
    assert COPY["feedback"] not in turn.text
    assert COPY["ask_business"] not in turn.text


@pytest.mark.parametrize(
    ("question", "topic", "expected_title", "unexpected_title"),
    [
        (USN_QUESTION, "usn", "Шаблон учёта доходов на УСН", "Маркетинг для соло-предпринимателя"),
        (
            "Как выстроить маркетинг?",
            "marketing",
            "Маркетинг для соло-предпринимателя",
            "Шаблон учёта доходов на УСН",
        ),
        (
            "Как открыть своё дело?",
            "startup",
            "Юнит-экономика кофейни",
            "Маркетинг для соло-предпринимателя",
        ),
        (
            "Как собрать бюджет?",
            "finance",
            "Шаблон учёта доходов на УСН",
            "Курс «Продвижение на практике»",
        ),
    ],
)
async def test_answered_question_steers_next_recommendation(
    dialog: Dialog,
    question: str,
    topic: str,
    expected_title: str,
    unexpected_title: str,
) -> None:
    await finish_profile(dialog, "Пекарня, полгода", "profile_mode:other")
    dialog.knowledge.reply(question, _answer("Материал темы"))

    await dialog.say(question)
    picked = await dialog.press("materials")

    assert (await dialog.payload())["last_topic"] == topic
    assert expected_title in picked.text
    assert unexpected_title not in picked.text
    assert NEUTRAL_QUESTION not in dialog.knowledge.calls[-1][0]
