from __future__ import annotations

import argparse
import asyncio
import uuid
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import setup_logging
from src.core.settings import Settings
from src.data.database import create_engine, create_session_factory
from src.data.migrate import run_migrations
from src.data.models.chunk import Chunk
from src.data.repositories.chunks import ChunkRepository
from src.modules.knowledge.catalog import PUBLISHED_STATUS_ID, is_paid_course_type
from src.modules.knowledge.embedder import (
    Embedder,
    FixedLengthEmbedder,
    SentenceTransformerEmbedder,
)
from src.modules.knowledge.sources import (
    article_chunk_drafts,
    embed_material_chunk_drafts,
    landing_chunk_drafts,
    lesson_chunk_drafts,
)
from src.modules.knowledge.types import ChunkDraft

_EMBED_BATCH = 64


async def _fetch_articles(session: AsyncSession) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            a."Id" AS material_id,
            a."Title" AS title,
            a."Url" AS slug,
            a."TitleTag" AS seo_title,
            a."DescriptionTag" AS seo_description,
            a."Description" AS description,
            e."HtmlContent" AS html,
            e."Order" AS item_order
        FROM public."Articles" AS a
        JOIN public."ArticleEmbedItems" AS e ON e."ArticleId" = a."Id"
        WHERE a."StatusId" = :status_id
          AND a."IsDeleted" = false
        ORDER BY a."Id", e."Order"
        """
    )
    result = await session.execute(query, {"status_id": str(PUBLISHED_STATUS_ID)})
    return [dict(row) for row in result.mappings()]


async def _fetch_documents(session: AsyncSession) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            d."Id" AS material_id,
            d."Title" AS title,
            d."Url" AS slug,
            d."TitleTag" AS seo_title,
            d."DescriptionTag" AS seo_description,
            d."Description" AS description,
            e."HtmlContent" AS html,
            e."Order" AS item_order
        FROM public."Documents" AS d
        JOIN public."DocumentEmbedItems" AS e ON e."DocumentId" = d."Id"
        WHERE d."StatusId" = :status_id
          AND d."IsDeleted" = false
        ORDER BY d."Id", e."Order"
        """
    )
    result = await session.execute(query, {"status_id": str(PUBLISHED_STATUS_ID)})
    return [dict(row) for row in result.mappings()]


async def _fetch_glossary(session: AsyncSession) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            g."Id" AS material_id,
            g."Title" AS title,
            g."Url" AS slug,
            g."TitleTag" AS seo_title,
            g."DescriptionTag" AS seo_description,
            g."Description" AS description,
            e."HtmlContent" AS html,
            e."Order" AS item_order
        FROM public."Glossary" AS g
        JOIN public."GlossaryEmbedItems" AS e ON e."GlossaryId" = g."Id"
        WHERE g."StatusId" = :status_id
          AND g."IsDeleted" = false
        ORDER BY g."Id", e."Order"
        """
    )
    result = await session.execute(query, {"status_id": str(PUBLISHED_STATUS_ID)})
    return [dict(row) for row in result.mappings()]


async def _fetch_lessons(session: AsyncSession) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            l."Id" AS material_id,
            l."Title" AS title,
            l."Description" AS description,
            c."Url" AS course_slug,
            c."TypeId" AS course_type_id,
            c."TitleTag" AS seo_title,
            c."DescriptionTag" AS seo_description,
            e."HtmlContent" AS html,
            e."Order" AS item_order
        FROM public."Lessons" AS l
        JOIN public."CourseLessonBindings" AS b ON b."LessonId" = l."Id"
        JOIN public."Courses" AS c ON c."Id" = b."CourseId"
        LEFT JOIN public."LessonEmbedItems" AS e ON e."LessonId" = l."Id"
        WHERE l."IsDeleted" = false
          AND c."IsDeleted" = false
          AND c."StatusId" = :status_id
        ORDER BY l."Id", e."Order" NULLS LAST
        """
    )
    result = await session.execute(query, {"status_id": str(PUBLISHED_STATUS_ID)})
    return [dict(row) for row in result.mappings()]


async def _fetch_landings(session: AsyncSession) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            l."Id" AS material_id,
            l."Title" AS title,
            l."Url" AS slug,
            l."TitleTag" AS seo_title,
            l."DescriptionTag" AS seo_description,
            l."Description" AS description,
            l."LandingDescription" AS landing_description
        FROM public."Landings" AS l
        WHERE l."StatusId" = :status_id
          AND l."IsDeleted" = false
        """
    )
    result = await session.execute(query, {"status_id": str(PUBLISHED_STATUS_ID)})
    return [dict(row) for row in result.mappings()]


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _group_html(
    rows: Sequence[dict[str, Any]],
    key: str = "material_id",
) -> dict[uuid.UUID, dict[str, Any]]:
    grouped: dict[uuid.UUID, dict[str, Any]] = {}
    html_parts: dict[uuid.UUID, list[str]] = defaultdict(list)
    for row in rows:
        material_id = row[key] if isinstance(row[key], uuid.UUID) else uuid.UUID(str(row[key]))
        if material_id not in grouped:
            grouped[material_id] = dict(row)
        html = row.get("html")
        if html:
            html_parts[material_id].append(str(html))
    for material_id, meta in grouped.items():
        meta["embed_html_parts"] = html_parts.get(material_id, [])
    return grouped


def build_drafts_from_catalog(
    *,
    articles: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    glossary: list[dict[str, Any]],
    lessons: list[dict[str, Any]],
    base_url: str,
    chunk_size: int,
    landings: list[dict[str, Any]] | None = None,
) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    for meta in _group_html(articles).values():
        drafts.extend(
            article_chunk_drafts(
                article_id=meta["material_id"],
                title=str(meta["title"]),
                slug=meta.get("slug"),
                embed_html_parts=meta["embed_html_parts"],
                base_url=base_url,
                chunk_size=chunk_size,
                seo_title=_text_or_none(meta.get("seo_title")),
                seo_description=_text_or_none(meta.get("seo_description")),
                description=_text_or_none(meta.get("description")),
            )
        )
    for meta in _group_html(documents).values():
        drafts.extend(
            embed_material_chunk_drafts(
                material_type="document",
                material_id=meta["material_id"],
                title=str(meta["title"]),
                slug=meta.get("slug"),
                embed_html_parts=meta["embed_html_parts"],
                base_url=base_url,
                chunk_size=chunk_size,
                seo_title=_text_or_none(meta.get("seo_title")),
                seo_description=_text_or_none(meta.get("seo_description")),
                description=_text_or_none(meta.get("description")),
            )
        )
    for meta in _group_html(glossary).values():
        drafts.extend(
            embed_material_chunk_drafts(
                material_type="glossary",
                material_id=meta["material_id"],
                title=str(meta["title"]),
                slug=meta.get("slug"),
                embed_html_parts=meta["embed_html_parts"],
                base_url=base_url,
                chunk_size=chunk_size,
                seo_title=_text_or_none(meta.get("seo_title")),
                seo_description=_text_or_none(meta.get("seo_description")),
                description=_text_or_none(meta.get("description")),
            )
        )
    for meta in _group_html(lessons).values():
        course_type = meta["course_type_id"]
        if isinstance(course_type, uuid.UUID):
            course_type_id = course_type
        else:
            course_type_id = uuid.UUID(str(course_type))
        drafts.extend(
            lesson_chunk_drafts(
                lesson_id=meta["material_id"],
                title=str(meta["title"]),
                description=_text_or_none(meta.get("description")),
                course_slug=meta.get("course_slug"),
                is_paid_course=is_paid_course_type(course_type_id),
                embed_html_parts=meta["embed_html_parts"],
                base_url=base_url,
                chunk_size=chunk_size,
                seo_title=_text_or_none(meta.get("seo_title")),
                seo_description=_text_or_none(meta.get("seo_description")),
            )
        )
    for meta in landings or []:
        material_id = meta["material_id"]
        if not isinstance(material_id, uuid.UUID):
            material_id = uuid.UUID(str(material_id))
        drafts.extend(
            landing_chunk_drafts(
                landing_id=material_id,
                title=str(meta["title"]),
                slug=meta.get("slug"),
                base_url=base_url,
                seo_title=_text_or_none(meta.get("seo_title")),
                seo_description=_text_or_none(meta.get("seo_description")),
                description=_text_or_none(meta.get("description")),
                landing_description=_text_or_none(meta.get("landing_description")),
            )
        )
    return drafts


def _drafts_by_material(
    drafts: Sequence[ChunkDraft],
) -> dict[tuple[str, uuid.UUID], list[ChunkDraft]]:
    grouped: dict[tuple[str, uuid.UUID], list[ChunkDraft]] = defaultdict(list)
    for draft in drafts:
        grouped[(draft.material_type, draft.material_id)].append(draft)
    return grouped


async def _persist_material_chunks(
    repository: ChunkRepository,
    material_type: str,
    material_id: uuid.UUID,
    drafts: list[ChunkDraft],
    embeddings: list[list[float]],
) -> int:
    chunks = [
        Chunk(
            material_type=material_type,
            material_id=material_id,
            chunk_index=draft.chunk_index,
            title=draft.title,
            url=draft.url,
            is_paid=draft.is_paid,
            body=draft.body,
            include_in_rag=draft.include_in_rag,
            embedding=vector,
        )
        for draft, vector in zip(drafts, embeddings, strict=True)
    ]
    return await repository.replace_for_material(material_type, material_id, chunks)


async def ingest_catalog(
    session: AsyncSession,
    *,
    settings: Settings,
    embedder: Embedder,
    limit: int | None = None,
) -> dict[str, int]:
    articles = await _fetch_articles(session)
    documents = await _fetch_documents(session)
    glossary = await _fetch_glossary(session)
    lessons = await _fetch_lessons(session)
    landings = await _fetch_landings(session)
    drafts = build_drafts_from_catalog(
        articles=articles,
        documents=documents,
        glossary=glossary,
        lessons=lessons,
        landings=landings,
        base_url=settings.platform_base_url,
        chunk_size=settings.ingest_chunk_size,
    )
    if limit is not None:
        grouped = _drafts_by_material(drafts)
        limited_keys = list(grouped.keys())[:limit]
        drafts = [draft for key in limited_keys for draft in grouped[key]]

    grouped = _drafts_by_material(drafts)
    repository = ChunkRepository(session)
    counts = {"materials": 0, "chunks": 0}
    for (material_type, material_id), material_drafts in grouped.items():
        material_drafts.sort(key=lambda item: item.chunk_index)
        vectors: list[list[float]] = []
        for start in range(0, len(material_drafts), _EMBED_BATCH):
            batch = material_drafts[start : start + _EMBED_BATCH]
            vectors.extend(embedder.embed_passages([item.body for item in batch]))
        written = await _persist_material_chunks(
            repository,
            material_type,
            material_id,
            material_drafts,
            vectors,
        )
        counts["materials"] += 1
        counts["chunks"] += written
    return counts


def _build_embedder(settings: Settings, *, dry_run: bool) -> Embedder:
    if dry_run:
        return FixedLengthEmbedder()
    return SentenceTransformerEmbedder(settings.embedding_model)


async def _async_main(args: argparse.Namespace) -> int:
    settings = Settings()
    setup_logging(settings.log_level, debug=settings.debug)
    database_url = settings.database_url_resolved
    if not database_url.strip():
        raise SystemExit("DATABASE_URL не задан")

    await asyncio.to_thread(run_migrations, database_url)
    engine = create_engine(database_url)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            counts = await ingest_catalog(
                session,
                settings=settings,
                embedder=_build_embedder(settings, dry_run=args.dry_run),
                limit=args.limit,
            )
            await session.commit()
    finally:
        await engine.dispose()

    logger.info(
        "Ingest завершён: материалов={}, чанков={}, dry_run={}",
        counts["materials"],
        counts["chunks"],
        args.dry_run,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Нарезка каталога и эмбеддинги в content.chunks")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Не скачивать модель: записать фиктивные векторы",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Ограничить число материалов (для отладки)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
