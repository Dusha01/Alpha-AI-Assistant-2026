from __future__ import annotations

import uuid

from src.modules.knowledge.catalog import material_url
from src.modules.knowledge.chunking import split_text_windows
from src.modules.knowledge.text import normalize_whitespace, strip_html
from src.modules.knowledge.types import ChunkDraft


def article_chunk_drafts(
    *,
    article_id: uuid.UUID,
    title: str,
    slug: str | None,
    embed_html_parts: list[str],
    base_url: str,
    chunk_size: int,
) -> list[ChunkDraft]:
    text = normalize_whitespace(strip_html("\n".join(embed_html_parts)))
    if not text:
        return []
    url = material_url(base_url, slug)
    chunks = split_text_windows(text, window=chunk_size)
    return [
        ChunkDraft(
            material_type="article",
            material_id=article_id,
            chunk_index=index,
            title=title,
            url=url,
            is_paid=False,
            body=body,
            include_in_rag=True,
        )
        for index, body in enumerate(chunks)
    ]


def lesson_chunk_drafts(
    *,
    lesson_id: uuid.UUID,
    title: str,
    description: str | None,
    course_slug: str | None,
    is_paid_course: bool,
    embed_html_parts: list[str],
    base_url: str,
    chunk_size: int,
) -> list[ChunkDraft]:
    url = material_url(base_url, course_slug)
    if is_paid_course:
        card = normalize_whitespace(strip_html(f"{title}\n{description or ''}"))
        if not card:
            card = title.strip()
        return [
            ChunkDraft(
                material_type="lesson",
                material_id=lesson_id,
                chunk_index=0,
                title=title,
                url=url,
                is_paid=True,
                body=card,
                include_in_rag=True,
            )
        ]
    text = normalize_whitespace(strip_html("\n".join(embed_html_parts)))
    if not text:
        fallback = normalize_whitespace(strip_html(f"{title}\n{description or ''}"))
        if not fallback:
            return []
        text = fallback
    chunks = split_text_windows(text, window=chunk_size)
    return [
        ChunkDraft(
            material_type="lesson",
            material_id=lesson_id,
            chunk_index=index,
            title=title,
            url=url,
            is_paid=False,
            body=body,
            include_in_rag=True,
        )
        for index, body in enumerate(chunks)
    ]


def embed_material_chunk_drafts(
    *,
    material_type: str,
    material_id: uuid.UUID,
    title: str,
    slug: str | None,
    embed_html_parts: list[str],
    base_url: str,
    chunk_size: int,
) -> list[ChunkDraft]:
    text = normalize_whitespace(strip_html("\n".join(embed_html_parts)))
    if not text:
        return []
    url = material_url(base_url, slug)
    chunks = split_text_windows(text, window=chunk_size)
    return [
        ChunkDraft(
            material_type=material_type,
            material_id=material_id,
            chunk_index=index,
            title=title,
            url=url,
            is_paid=False,
            body=body,
            include_in_rag=True,
        )
        for index, body in enumerate(chunks)
    ]
