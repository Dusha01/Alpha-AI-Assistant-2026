from src.modules.knowledge.relevance import (
    is_vague_question,
    material_covers_question,
    question_aligns_with_title,
)
from src.modules.knowledge.types import SearchHit


def test_usn_short_question_matches_seller_article() -> None:
    hit = SearchHit(
        title="УСН. Налоговый учёт у селлера",
        url="https://example/usn",
        body="Налоговый учёт на УСН для селлеров",
        is_paid=False,
        score=0.9,
    )
    assert material_covers_question("Учёт доходов на УСН", hit) is True


def test_visa_question_misses_china_finance_material() -> None:
    hit = SearchHit(
        title="Финансы и платежи в Китае",
        url="https://example/cn",
        body="Про бизнес и платежи в Китае без виз",
        is_paid=False,
        score=0.86,
    )
    assert material_covers_question("Виза в Китай", hit) is False


def test_short_credit_question_is_vague() -> None:
    assert is_vague_question("как получить кредит?") is True


def test_long_usn_question_is_specific() -> None:
    assert is_vague_question("Как вести учёт доходов на УСН?") is False


def test_short_followup_aligns_with_title() -> None:
    assert question_aligns_with_title("Кредит", "Как выбрать кредит") is True
    assert question_aligns_with_title("Как выбрать кредит", "Как выбрать кредит") is True
