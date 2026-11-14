from __future__ import annotations

import pytest
from tests.scenarios.harness import Dialog, finish_profile

from src.handlers.text import COPY

pytestmark = pytest.mark.integration


async def test_empty_profile_gets_cold_start(dialog: Dialog) -> None:
    turn = await dialog.press("materials")

    assert "Азы финансовой грамотности" in turn.text
    assert "Как составить бизнес-план" in turn.text
    assert "Чек-лист первых шагов предпринимателя" in turn.text
    assert COPY["next_step"].split("{")[0] not in turn.text
    assert len(turn.messages) == 1


async def test_newbie_gets_learning_route(dialog: Dialog) -> None:
    await finish_profile(dialog, "только планирую", "profile_mode:unknown")

    turn = await dialog.press("materials")

    assert "Азы финансовой грамотности" in turn.text
    assert "Как составить бизнес-план" in turn.text
    assert "Чек-лист первых шагов предпринимателя" in turn.text
    assert "Начнём с первого?" in turn.text
    assert "через 3 дня" in turn.text


async def test_coffee_usn_route_and_paid_line_stay_short(dialog: Dialog) -> None:
    saved = await finish_profile(
        dialog,
        "Кофейня, полгода",
        "profile_mode:usn",
        question="Как вести учёт доходов на УСН?",
    )
    route = await dialog.press("materials")

    assert "Шаблон учёта доходов на УСН" in saved.text
    assert "у вас кофейня на УСН" in saved.text
    assert "Курс «УСН без ошибок»" in saved.text
    assert "разобрать типовые ошибки учёта и отчётности" in saved.text
    assert "utm_source=tg_bot" in saved.text
    assert "полный текст урока" not in saved.text
    assert "через 3 дня" in saved.text
    assert "Шаблон учёта доходов на УСН" in route.text
    assert "Юнит-экономика кофейни" in route.text
    assert "Курс «УСН без ошибок»" in route.text
    assert "Начнём с первого?" in route.text


async def test_marketing_profile_gets_its_route(dialog: Dialog) -> None:
    await finish_profile(dialog, "маркетинг, больше года", "profile_mode:other")

    turn = await dialog.press("materials")

    assert "Маркетинг для соло-предпринимателя" in turn.text
    assert "Контент-план на месяц" in turn.text
    assert "Курс «Продвижение на практике»" in turn.text
    assert "Начнём с первого?" in turn.text
