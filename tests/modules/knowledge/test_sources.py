import uuid

from src.modules.knowledge.sources import article_chunk_drafts, lesson_chunk_drafts

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
