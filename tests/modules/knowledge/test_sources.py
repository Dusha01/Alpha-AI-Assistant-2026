import uuid

from src.modules.knowledge.sources import (
    article_chunk_drafts,
    landing_chunk_drafts,
    lesson_chunk_drafts,
)

PAID_EMBED = "<p>" + ("секрет " * 400) + "</p>"


def test_paid_lesson_uses_card_only() -> None:
    lesson_id = uuid.uuid4()
    drafts = lesson_chunk_drafts(
        lesson_id=lesson_id,
        title="Платный урок",
        description="Краткая польза",
        course_slug="paid-course",
        is_paid_course=True,
        embed_html_parts=[PAID_EMBED],
        base_url="https://course.example",
        chunk_size=800,
    )

    assert len(drafts) == 1
    assert drafts[0].is_paid is True
    assert "секрет" not in drafts[0].body
    assert "Краткая польза" in drafts[0].body
    assert drafts[0].url == "https://course.example/paid-course"


def test_free_lesson_chunks_embed_body() -> None:
    lesson_id = uuid.uuid4()
    embed = "<p>" + ("текст " * 300) + "</p>"
    drafts = lesson_chunk_drafts(
        lesson_id=lesson_id,
        title="Открытый урок",
        description=None,
        course_slug="open-course",
        is_paid_course=False,
        embed_html_parts=[embed],
        base_url="https://course.example",
        chunk_size=800,
    )

    assert len(drafts) >= 2
    assert all(not draft.is_paid for draft in drafts)


def test_article_splits_by_window() -> None:
    article_id = uuid.uuid4()
    embed = "<p>" + ("статья " * 500) + "</p>"
    drafts = article_chunk_drafts(
        article_id=article_id,
        title="Статья",
        slug="statya",
        embed_html_parts=[embed],
        base_url="https://course.example",
        chunk_size=800,
    )

    assert len(drafts) >= 2
    assert drafts[0].material_type == "article"


def test_article_prefixes_public_seo_fields() -> None:
    article_id = uuid.uuid4()
    drafts = article_chunk_drafts(
        article_id=article_id,
        title="Статья",
        slug="statya",
        embed_html_parts=["<p>Основной текст статьи</p>"],
        base_url="https://course.example",
        chunk_size=800,
        seo_title="Как вести учёт",
        seo_description="Короткое SEO-описание",
        description="Анонс для карточки",
    )

    body = drafts[0].body
    assert "Как вести учёт" in body
    assert "Короткое SEO-описание" in body
    assert "Анонс для карточки" in body
    assert "Основной текст статьи" in body


def test_paid_lesson_card_keeps_seo_and_drops_body() -> None:
    drafts = lesson_chunk_drafts(
        lesson_id=uuid.uuid4(),
        title="Платный урок",
        description="Краткая польза",
        course_slug="paid-course",
        is_paid_course=True,
        embed_html_parts=[PAID_EMBED],
        base_url="https://course.example",
        chunk_size=800,
        seo_title="Курс по учёту",
        seo_description="Публичная польза курса",
    )

    assert "секрет" not in drafts[0].body
    assert "Краткая польза" in drafts[0].body
    assert "Курс по учёту" in drafts[0].body
    assert "Публичная польза курса" in drafts[0].body


def test_landing_chunk_uses_public_copy_only() -> None:
    drafts = landing_chunk_drafts(
        landing_id=uuid.uuid4(),
        title="Лендинг УСН",
        slug="usn-landing",
        base_url="https://course.example",
        seo_title="УСН для кофейни",
        seo_description="Что сдавать на УСН",
        description="Описание страницы",
        landing_description="Кому подойдёт страница",
    )

    assert len(drafts) == 1
    assert drafts[0].material_type == "landing"
    assert drafts[0].is_paid is False
    assert "УСН для кофейни" in drafts[0].body
    assert "Кому подойдёт страница" in drafts[0].body
    assert drafts[0].url == "https://course.example/usn-landing"
