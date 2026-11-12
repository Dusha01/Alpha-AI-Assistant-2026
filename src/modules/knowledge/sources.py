from __future__ import annotations

import uuid

from src.modules.knowledge.catalog import material_url
from src.modules.knowledge.chunking import split_text_windows
from src.modules.knowledge.text import normalize_whitespace, strip_html
from src.modules.knowledge.types import ChunkDraft


def public_card(*parts: str | None) -> str:
    seen: list[str] = []
    for part in parts:
        if not part:
            continue
        text = normalize_whitespace(strip_html(part))
        if text and text not in seen:
            seen.append(text)
    return "\n".join(seen)


def _with_lead(lead: str, chunks: list[str]) -> list[str]:
    if not lead:
        return chunks
    return [chunk if chunk.startswith(lead) else f"{lead}\n{chunk}" for chunk in chunks]


def _drafts(
    *,
    material_type: str,
    material_id: uuid.UUID,
    title: str,
    url: str | None,
    is_paid: bool,
    chunks: list[str],
) -> list[ChunkDraft]:
    return [
        ChunkDraft(
            material_type=material_type,
            material_id=material_id,
            chunk_index=index,
            title=title,
            url=url,
            is_paid=is_paid,
            body=body,
            include_in_rag=True,
        )
        for index, body in enumerate(chunks)
    ]


def article_chunk_drafts(
    *,
    article_id: uuid.UUID,
    title: str,
    slug: str | None,
    embed_html_parts: list[str],
    base_url: str,
    chunk_size: int,
    seo_title: str | None = None,
    seo_description: str | None = None,
    description: str | None = None,
) -> list[ChunkDraft]:
    lead = public_card(seo_title, seo_description, description)
    text = normalize_whitespace(strip_html("\n".join(embed_html_parts)))
    if not text and not lead:
        return []
    chunks = split_text_windows(text or lead, window=chunk_size)
    return _drafts(
        material_type="article",
        material_id=article_id,
        title=title,
        url=material_url(base_url, slug),
        is_paid=False,
        chunks=_with_lead(lead, chunks) if text else chunks,
    )


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
    seo_title: str | None = None,
    seo_description: str | None = None,
) -> list[ChunkDraft]:
    url = material_url(base_url, course_slug)
    lead = public_card(title, description, seo_title, seo_description)
    if is_paid_course:
        card = lead or title.strip()
        return _drafts(
            material_type="lesson",
            material_id=lesson_id,
            title=title,
            url=url,
            is_paid=True,
            chunks=[card],
        )
    text = normalize_whitespace(strip_html("\n".join(embed_html_parts)))
    if not text:
        if not lead:
            return []
        text = lead
        lead = ""
    chunks = split_text_windows(text, window=chunk_size)
    return _drafts(
        material_type="lesson",
        material_id=lesson_id,
        title=title,
        url=url,
        is_paid=False,
        chunks=_with_lead(lead, chunks),
    )


def embed_material_chunk_drafts(
    *,
    material_type: str,
    material_id: uuid.UUID,
    title: str,
    slug: str | None,
    embed_html_parts: list[str],
    base_url: str,
    chunk_size: int,
    seo_title: str | None = None,
    seo_description: str | None = None,
    description: str | None = None,
) -> list[ChunkDraft]:
    lead = public_card(seo_title, seo_description, description)
    text = normalize_whitespace(strip_html("\n".join(embed_html_parts)))
    if not text and not lead:
        return []
    chunks = split_text_windows(text or lead, window=chunk_size)
    return _drafts(
        material_type=material_type,
        material_id=material_id,
        title=title,
        url=material_url(base_url, slug),
        is_paid=False,
        chunks=_with_lead(lead, chunks) if text else chunks,
    )


def landing_chunk_drafts(
    *,
    landing_id: uuid.UUID,
    title: str,
    slug: str | None,
    base_url: str,
    seo_title: str | None = None,
    seo_description: str | None = None,
    description: str | None = None,
    landing_description: str | None = None,
) -> list[ChunkDraft]:
    text = public_card(title, seo_title, seo_description, description, landing_description)
    if not text:
        return []
    return _drafts(
        material_type="landing",
        material_id=landing_id,
        title=title,
        url=material_url(base_url, slug),
        is_paid=False,
        chunks=[text],
    )
