"""Извлечение одного факта на материал и запись вектора в content.facts.

Команда отдельно от ingest: загрузка чанков не зависит от LLM.
"""

from __future__ import annotations

import argparse
import asyncio
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import setup_logging
from src.core.settings import Settings
from src.data.database import create_engine, create_session_factory
from src.data.migrate import run_migrations
from src.data.models.chunk import Chunk
from src.data.models.fact import Fact
from src.data.repositories.facts import FactRepository
from src.modules.knowledge.embedder import Embedder, SentenceTransformerEmbedder
from src.modules.knowledge.llm import LlmClient, OpenAICompatibleLlm

_BODY_LIMIT = 4000
_NO_FACT = frozenset({"нет", "нет.", "none", "none.", "no", "no.", "—", "-", "пусто"})
_FACT_SYSTEM = (
    "Вы выделяете один интересный факт из материала «Альфа-Курса». "
    "Ответьте одним предложением и только тем, что прямо сказано в тексте. "
    "Не добавляйте числа, советы и призывы, которых нет в тексте. "
    "Если отдельного факта нет, ответьте ровно: нет"
)


@dataclass(frozen=True, slots=True)
class MaterialText:
    material_type: str
    material_id: uuid.UUID
    title: str
    url: str | None
    body: str


class FactStore(Protocol):
    async def delete_for_material(self, material_type: str, material_id: uuid.UUID) -> int: ...

    async def replace_for_material(self, fact: Fact) -> None: ...


def fact_from_llm(raw: str) -> str | None:
    text = " ".join(raw.strip().split())
    if len(text) >= 2 and text[0] in '«"' and text[-1] in '»"':
        text = text[1:-1].strip()
    if not text or text.casefold() in _NO_FACT:
        return None
    if len(text) > 300:
        for index, char in enumerate(text):
            if char in ".!?" and index > 20:
                text = text[: index + 1]
                break
    if len(text) > 300:
        return None
    return text


def build_fact_messages(title: str, body: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _FACT_SYSTEM},
        {"role": "user", "content": f"Материал: {title}\n\nТекст:\n{body}"},
    ]


def chosen_fact(body: str | None, score: float | None, *, threshold: float) -> str | None:
    if body is None or score is None or score < threshold:
        return None
    text = body.strip()
    return text or None


async def extract_fact(llm: LlmClient, title: str, body: str) -> str | None:
    if not body.strip():
        return None
    raw = await llm.complete(build_fact_messages(title, body[:_BODY_LIMIT]))
    return fact_from_llm(raw)


async def fill_facts_from_materials(
    materials: Sequence[MaterialText],
    *,
    llm: LlmClient,
    embedder: Embedder,
    repository: FactStore,
) -> dict[str, int]:
    counts = {"written": 0, "skipped": 0, "failed": 0}
    for material in materials:
        try:
            phrase = await extract_fact(llm, material.title, material.body)
        except Exception:
            logger.exception(
                "Не удалось извлечь факт material_type={} material_id={}",
                material.material_type,
                material.material_id,
            )
            counts["failed"] += 1
            continue
        if phrase is None:
            await repository.delete_for_material(material.material_type, material.material_id)
            counts["skipped"] += 1
            continue
        vector = embedder.embed_passages([phrase])[0]
        await repository.replace_for_material(
            Fact(
                material_type=material.material_type,
                material_id=material.material_id,
                source_title=material.title,
                source_url=material.url,
                body=phrase,
                embedding=vector,
            )
        )
        counts["written"] += 1
    return counts


def materials_from_chunks(rows: Sequence[Chunk]) -> list[MaterialText]:
    grouped: dict[tuple[str, uuid.UUID], list[Chunk]] = {}
    for row in rows:
        grouped.setdefault((row.material_type, row.material_id), []).append(row)
    materials: list[MaterialText] = []
    for (material_type, material_id), chunks in grouped.items():
        chunks.sort(key=lambda item: item.chunk_index)
        body = "\n".join(chunk.body.strip() for chunk in chunks if chunk.body.strip())
        url = next((chunk.url for chunk in chunks if chunk.url), None)
        materials.append(
            MaterialText(
                material_type=material_type,
                material_id=material_id,
                title=chunks[0].title,
                url=url,
                body=body[:_BODY_LIMIT],
            )
        )
    return materials


async def load_materials(session: AsyncSession, *, limit: int | None) -> list[MaterialText]:
    stmt = (
        select(Chunk)
        .where(Chunk.include_in_rag.is_(True))
        .order_by(Chunk.material_type, Chunk.material_id, Chunk.chunk_index)
    )
    rows = list((await session.scalars(stmt)).all())
    materials = materials_from_chunks(rows)
    if limit is not None:
        return materials[:limit]
    return materials


async def fill_facts(
    session: AsyncSession,
    *,
    llm: LlmClient,
    embedder: Embedder,
    limit: int | None = None,
) -> dict[str, int]:
    materials = await load_materials(session, limit=limit)
    return await fill_facts_from_materials(
        materials,
        llm=llm,
        embedder=embedder,
        repository=FactRepository(session),
    )


def _build_llm(settings: Settings) -> OpenAICompatibleLlm:
    return OpenAICompatibleLlm(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        fallback_model=settings.llm_fallback_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )


async def _async_main(args: argparse.Namespace) -> int:
    settings = Settings()
    setup_logging(settings.log_level, debug=settings.debug)
    database_url = settings.database_url_resolved
    if not database_url.strip():
        raise SystemExit("DATABASE_URL не задан")
    if not settings.llm_api_key.strip():
        raise SystemExit("LLM_API_KEY не задан")

    await asyncio.to_thread(run_migrations, database_url)
    engine = create_engine(database_url)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            counts = await fill_facts(
                session,
                llm=_build_llm(settings),
                embedder=SentenceTransformerEmbedder(settings.embedding_model),
                limit=args.limit,
            )
            await session.commit()
    finally:
        await engine.dispose()

    logger.info(
        "Факты записаны: written={}, skipped={}, failed={}",
        counts["written"],
        counts["skipped"],
        counts["failed"],
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Один факт на материал в content.facts")
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
