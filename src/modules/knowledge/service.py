from __future__ import annotations

import asyncio
from dataclasses import dataclass

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.settings import Settings
from src.data.repositories.chunks import ChunkRepository
from src.handlers.text import COPY
from src.modules.knowledge.decision import SearchOutcome, decide_outcome
from src.modules.knowledge.embedder import Embedder
from src.modules.knowledge.llm import LlmClient, LlmNotConfiguredError, LlmRequestError
from src.modules.knowledge.prompt import build_llm_messages
from src.modules.knowledge.text import benefit_one_liner
from src.modules.knowledge.types import SearchHit
from src.modules.recommend.utm import slug_from_url, with_utm


@dataclass(frozen=True, slots=True)
class BotReply:
    text: str
    feedback: bool = False
    material_title: str | None = None


class KnowledgeService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        embedder: Embedder,
        llm: LlmClient,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.embedder = embedder
        self.llm = llm

    async def answer_question(self, question: str, *, search_query: str | None = None) -> BotReply:
        hits = await self.search(search_query or question)
        return await self.answer_from_hits(question, hits)

    async def search(self, question: str) -> list[SearchHit]:
        vector = await asyncio.to_thread(self.embedder.embed_query, question)
        async with self.session_factory() as session:
            hits = await ChunkRepository(session).search_similar(
                vector,
                limit=self.settings.rag_top_k,
            )
        if hits and self.settings.debug:
            logger.debug(
                "rag_search question={} top_score={:.4f} title={}",
                question[:120],
                hits[0].score,
                hits[0].title[:80],
            )
        return hits

    async def answer_from_hits(self, question: str, hits: list[SearchHit]) -> BotReply:
        outcome = decide_outcome(
            hits,
            question=question,
            answer_threshold=self.settings.rag_score_threshold,
            related_threshold=self.settings.rag_related_score_threshold,
            clarify_gap=self.settings.rag_clarify_score_gap,
        )
        logger.info(
            "rag_outcome kind={} question={}",
            outcome.kind,
            question[:120],
        )
        return await self._render_outcome(question, outcome)

    async def _render_outcome(self, question: str, outcome: SearchOutcome) -> BotReply:
        if outcome.kind == "not_found":
            return BotReply(COPY["not_found"])
        if outcome.kind == "not_found_related":
            hit = outcome.hits[0]
            return BotReply(
                COPY["not_found_related"].format(
                    material_name=hit.title,
                    benefit=benefit_one_liner(hit.body),
                    url=_public_url(hit.url),
                ),
                material_title=hit.title,
            )
        if outcome.kind == "clarify" and outcome.variants is not None:
            variant_1, variant_2 = outcome.variants
            return BotReply(
                COPY["clarify"].format(variant_1=variant_1, variant_2=variant_2),
            )
        if outcome.kind == "clarify_free":
            return BotReply(COPY["clarify_free"])
        return await self._answer_with_llm(question, outcome.hits)

    async def _answer_with_llm(self, question: str, hits: tuple[SearchHit, ...]) -> BotReply:
        if not self.settings.llm_api_key.strip():
            return BotReply(COPY["error_llm"])
        messages = build_llm_messages(question, hits[:3])
        try:
            llm_text = await self.llm.complete(messages)
        except (LlmNotConfiguredError, LlmRequestError) as exc:
            logger.warning("LLM недоступен: {}", exc)
            return BotReply(COPY["error_llm"])
        primary = hits[0]
        url = _public_url(primary.url)
        if _should_append_source(llm_text, primary.title, url):
            source = COPY["answer_source"].format(material_name=primary.title, url=url)
            text = f"{llm_text}\n\n{source}"
        else:
            text = llm_text
        return BotReply(text, feedback=True, material_title=primary.title)


def _public_url(url: str | None) -> str:
    if not url:
        return "—"
    return with_utm(url, campaign="answer", content=slug_from_url(url))


def _should_append_source(llm_text: str, material_name: str, url: str) -> bool:
    lowered = llm_text.lower()
    if url != "—" and url in llm_text:
        return False
    if material_name in llm_text:
        return False
    if "подробнее" in lowered and "материал" in lowered:
        return False
    return True
