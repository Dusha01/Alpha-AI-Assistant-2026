from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.settings import Settings
from src.data.repositories.chunks import ChunkRepository
from src.data.repositories.facts import FactRepository
from src.handlers.text import COPY, interesting_fact_message
from src.modules.knowledge.clarify_rules import ProfileSnapshot, clarify_reply
from src.modules.knowledge.decision import SearchOutcome, decide_outcome
from src.modules.knowledge.embedder import Embedder
from src.modules.knowledge.facts import chosen_fact
from src.modules.knowledge.llm import LlmClient
from src.modules.knowledge.outside import outside_reply
from src.modules.knowledge.prompt import build_llm_messages
from src.modules.knowledge.relevance import collapse_by_url, expand_query, prefer_lexical_hit
from src.modules.knowledge.text import benefit_one_liner
from src.modules.knowledge.types import SearchHit
from src.modules.recommend.utm import slug_from_url, with_utm

_CANDIDATE_LIMIT = 80
_LLM_HITS = 3
SourceProgress = Callable[[int], Awaitable[None]]
FactProgress = Callable[[str], Awaitable[None]]


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

    async def answer_question(
        self,
        question: str,
        *,
        search_query: str | None = None,
        profile: ProfileSnapshot | None = None,
        on_sources: SourceProgress | None = None,
        on_fact: FactProgress | None = None,
    ) -> BotReply:
        early = outside_reply(question) or clarify_reply(question, profile)
        if early is not None:
            return BotReply(early)
        hits, fact = await self.retrieve(search_query or question)
        return await self.answer_from_hits(
            question,
            hits,
            profile=profile,
            on_sources=on_sources,
            on_fact=on_fact,
            fact=fact,
        )

    async def search(self, question: str) -> list[SearchHit]:
        hits, _fact = await self.retrieve(question)
        return hits

    async def retrieve(self, question: str) -> tuple[list[SearchHit], str | None]:
        vector = await asyncio.to_thread(self.embedder.embed_query, expand_query(question))
        async with self.session_factory() as session:
            hits = await ChunkRepository(session).search_similar(
                vector,
                limit=max(self.settings.rag_top_k, _CANDIDATE_LIMIT),
            )
            nearest = await FactRepository(session).search_similar(vector, limit=1)
        fact = None
        if nearest:
            fact = chosen_fact(
                nearest[0].body,
                nearest[0].score,
                threshold=self.settings.fact_score_threshold,
            )
        hits = prefer_lexical_hit(collapse_by_url(hits, question), question)
        hits = hits[: self.settings.rag_top_k]
        if hits and self.settings.debug:
            logger.debug(
                "rag_search question={} top_score={:.4f} title={}",
                question[:120],
                hits[0].score,
                hits[0].title[:80],
            )
        return hits, fact

    async def answer_from_hits(
        self,
        question: str,
        hits: list[SearchHit],
        *,
        profile: ProfileSnapshot | None = None,
        on_sources: SourceProgress | None = None,
        on_fact: FactProgress | None = None,
        fact: str | None = None,
    ) -> BotReply:
        early = outside_reply(question) or clarify_reply(question, profile)
        if early is not None:
            logger.info("rag_outcome kind=early question={}", question[:120])
            return BotReply(early)
        hits = prefer_lexical_hit(hits, question)
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
        return await self._render_outcome(
            question,
            outcome,
            on_sources=on_sources,
            on_fact=on_fact,
            fact=fact,
        )

    async def _render_outcome(
        self,
        question: str,
        outcome: SearchOutcome,
        *,
        on_sources: SourceProgress | None = None,
        on_fact: FactProgress | None = None,
        fact: str | None = None,
    ) -> BotReply:
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
        found = _distinct_articles(outcome.hits)
        if on_sources is not None and found:
            await on_sources(found)
        if on_fact is not None and fact:
            await on_fact(interesting_fact_message(fact))
        return await self._answer_with_llm(question, outcome.hits)

    async def _answer_with_llm(self, question: str, hits: tuple[SearchHit, ...]) -> BotReply:
        if not self.settings.llm_api_key.strip():
            return BotReply(COPY["error_llm"])
        try:
            messages = build_llm_messages(question, hits[:_LLM_HITS])
            llm_text = await self.llm.complete(messages)
            primary = hits[0]
            url = _public_url(primary.url)
            if _should_append_source(llm_text, primary.title, url):
                source = COPY["answer_source"].format(material_name=primary.title, url=url)
                text = f"{llm_text}\n\n{source}"
            else:
                text = llm_text
            return BotReply(text, feedback=True, material_title=primary.title)
        except Exception as exc:
            logger.warning("LLM недоступен: {}", exc)
            return BotReply(COPY["error_llm"])


def _distinct_articles(hits: tuple[SearchHit, ...]) -> int:
    seen: set[str] = set()
    for hit in hits:
        key = (hit.url or "").strip() or hit.title.strip()
        if key:
            seen.add(key)
    return len(seen)


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
