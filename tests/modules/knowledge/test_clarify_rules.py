from src.data.models.enums import TaxMode
from src.handlers.text import COPY
from src.modules.knowledge.clarify_rules import ProfileSnapshot, clarify_reply


def test_credit_question_asks_for_the_purpose() -> None:
    text = clarify_reply("Как получить кредит?")
    assert text is not None
    assert "открытие бизнеса" in text
    assert "оборотные средства" in text


def test_tax_amount_without_mode_asks_for_regime() -> None:
    assert clarify_reply("Сколько мне платить налогов?") == COPY["clarify_tax_mode"]


def test_known_usn_does_not_ask_regime_again() -> None:
    profile = ProfileSnapshot(sphere="кофейня", mode=TaxMode.USN)
    assert clarify_reply("Сколько мне платить налогов?", profile) is None


def test_bare_close_asks_what_to_close() -> None:
    assert clarify_reply("Как закрыть?") == COPY["clarify_close"]


def test_cash_without_sphere_and_mode_asks_for_activity() -> None:
    text = clarify_reply(
        "Мне для начала кассу покупать надо или можно пока без неё?",
        ProfileSnapshot(),
    )
    assert text == COPY["clarify_cash"]
    assert "да" not in (text or "").split()


def test_usn_expenses_ask_for_the_object() -> None:
    profile = ProfileSnapshot(sphere="кофейня", mode=TaxMode.USN)
    text = clarify_reply(
        "За молоко и стаканчики плачу всё больше. Эти расходы могут уменьшить мой налог?",
        profile,
    )
    assert text == COPY["clarify_usn_object"]
    assert "кофейн" not in (text or "")
