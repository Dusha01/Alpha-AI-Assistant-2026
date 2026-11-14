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


def test_close_scores_prefer_the_article_that_covers_more_terms() -> None:
    from src.modules.knowledge.relevance import prefer_lexical_hit

    wrong = SearchHit(
        title="Как самозанятому стать ИП",
        url="https://example/stat-ip",
        body="Как самозанятому стать ИП",
        is_paid=False,
        score=0.876,
    )
    right = SearchHit(
        title="Чем ИП отличается от самозанятого",
        url="https://example/chem-ip",
        body="Чем ИП отличается от самозанятого",
        is_paid=False,
        score=0.869,
    )
    ranked = prefer_lexical_hit([wrong, right], "чем ип отличаеца от самозаннятого")
    assert ranked[0].title == right.title


def test_close_score_prefers_title_that_names_the_topic() -> None:
    from src.modules.knowledge.relevance import prefer_lexical_hit

    form = SearchHit(
        title="Заявление на получение патента по форме 26.5-1",
        url="https://example/form",
        body="ИП может работать на патенте",
        is_paid=False,
        score=0.886,
    )
    retail = SearchHit(
        title="Патент на розничную торговлю в 2026 году",
        url="https://example/retail",
        body="ИП может работать на патенте",
        is_paid=False,
        score=0.879,
    )
    question = "Можно ли мне, ИП с магазином, работать на патенте?"
    ranked = prefer_lexical_hit([form, retail], question)
    assert ranked[0].title == retail.title


def test_named_course_beats_a_nearby_article() -> None:
    from src.modules.knowledge.relevance import prefer_lexical_hit

    barista = SearchHit(
        title="День бариста",
        url="https://example/barista",
        body="Кофейня и бариста",
        is_paid=False,
        score=0.889,
    )
    course = SearchHit(
        title="Управление командой",
        url="https://example/kak-upravlyat-komandoi",
        body="Урок про роли",
        is_paid=True,
        score=0.871,
    )
    question = "Вижу курс «Как управлять командой». У меня небольшая кофейня и два бариста."
    ranked = prefer_lexical_hit([barista, course], question)
    assert ranked[0].title == course.title


def test_typo_with_changed_prefix_matches_article() -> None:
    hit = SearchHit(
        title="Чем ИП отличается от самозанятого",
        url="https://example/ip",
        body="Отличие ИП и самозанятого",
        is_paid=False,
        score=0.9,
    )
    assert material_covers_question("атличается", hit) is True
    assert material_covers_question("чем ип отличаеца от самозаннятого", hit) is True


def test_short_followup_aligns_with_title() -> None:
    assert question_aligns_with_title("Кредит", "Как выбрать кредит") is True
    assert question_aligns_with_title("Как выбрать кредит", "Как выбрать кредит") is True
