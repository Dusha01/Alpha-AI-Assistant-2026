from src.modules.knowledge.decision import decide_outcome
from src.modules.knowledge.types import SearchHit


def _hit(title: str, score: float, body: str | None = None) -> SearchHit:
    return SearchHit(
        title=title,
        url=f"https://example/{title}",
        body=body or title,
        is_paid=False,
        score=score,
    )


def test_weak_neighbor_yields_not_found() -> None:
    outcome = decide_outcome(
        [_hit("далёкий", 0.21)],
        question="далёкая тема",
        answer_threshold=0.35,
        related_threshold=0.27,
        clarify_gap=0.06,
    )
    assert outcome.kind == "not_found"


def test_borderline_neighbor_yields_not_found_related() -> None:
    outcome = decide_outcome(
        [_hit("похожий материал", 0.30, "похожий материал по теме")],
        question="похожий материал",
        answer_threshold=0.35,
        related_threshold=0.27,
        clarify_gap=0.06,
    )
    assert outcome.kind == "not_found_related"


def test_competing_topics_yield_clarify() -> None:
    outcome = decide_outcome(
        [
            _hit("Кредит для ИП", 0.62, "как получить кредит для ИП"),
            _hit("Ипотека для бизнеса", 0.59, "ипотека для бизнеса"),
        ],
        question="как получить кредит",
        answer_threshold=0.35,
        related_threshold=0.27,
        clarify_gap=0.06,
    )
    assert outcome.kind == "clarify"
    assert outcome.variants == ("Кредит для ИП", "Ипотека для бизнеса")


def test_specific_question_skips_clarify_for_high_scores() -> None:
    outcome = decide_outcome(
        [
            _hit(
                "Переход на УСН: пошаговая инструкция для ИП",
                0.90,
                "Как вести учёт доходов на УСН для ИП",
            ),
            _hit(
                "Переход с УСН на ПСН в 2026",
                0.89,
                "Переход с УСН на ПСН",
            ),
        ],
        question="Как вести учёт доходов на УСН?",
        answer_threshold=0.35,
        related_threshold=0.27,
        clarify_gap=0.06,
    )
    assert outcome.kind == "answer"


def test_vague_credit_question_skips_redundant_clarify() -> None:
    outcome = decide_outcome(
        [
            _hit("Как выбрать кредит", 0.62, "как выбрать кредит для бизнеса"),
            _hit("Кредит", 0.61, "что такое кредит для бизнеса"),
        ],
        question="что такое кредит?",
        answer_threshold=0.35,
        related_threshold=0.27,
        clarify_gap=0.06,
    )
    assert outcome.kind == "answer"


def test_followup_after_clarify_goes_to_answer() -> None:
    outcome = decide_outcome(
        [
            _hit("Как выбрать кредит", 0.89, "как выбрать кредит для бизнеса"),
            _hit("Кредит", 0.88, "кредит для бизнеса"),
        ],
        question="Как выбрать кредит",
        answer_threshold=0.35,
        related_threshold=0.27,
        clarify_gap=0.06,
    )
    assert outcome.kind == "answer"


def test_high_score_without_shared_words_still_answers() -> None:
    outcome = decide_outcome(
        [_hit("Регистрация бизнеса", 0.8, "общие сведения о старте")],
        question="Как подать заявление в налоговую?",
        answer_threshold=0.35,
        related_threshold=0.27,
        clarify_gap=0.06,
    )
    assert outcome.kind == "answer"


def test_visa_against_china_article_is_not_found() -> None:
    outcome = decide_outcome(
        [_hit("Какие налоги платят в Китае", 0.9, "налоги и платежи в Китае")],
        question="Как оформить визу в Китай за запчастями?",
        answer_threshold=0.35,
        related_threshold=0.27,
        clarify_gap=0.06,
    )
    assert outcome.kind == "not_found"


def test_china_visa_scenario_not_found() -> None:
    outcome = decide_outcome(
        [],
        answer_threshold=0.35,
        related_threshold=0.27,
        clarify_gap=0.06,
    )
    assert outcome.kind == "not_found"
