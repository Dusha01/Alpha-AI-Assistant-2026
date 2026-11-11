from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.modules.knowledge.relevance import (
    is_vague_question,
    material_covers_question,
    question_aligns_with_title,
)
from src.modules.knowledge.types import SearchHit

OutcomeKind = Literal["answer", "not_found", "not_found_related", "clarify", "clarify_free"]


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    kind: OutcomeKind
    hits: tuple[SearchHit, ...] = ()
    variants: tuple[str, str] | None = None


def _title_key(title: str) -> str:
    return " ".join(title.lower().split())


def decide_outcome(
    hits: list[SearchHit],
    *,
    question: str = "",
    answer_threshold: float,
    related_threshold: float,
    clarify_gap: float,
) -> SearchOutcome:
    if not hits:
        return SearchOutcome(kind="not_found")
    ranked = tuple(hit for hit in hits if hit.include_in_rag)
    if not ranked:
        return SearchOutcome(kind="not_found")
    best = ranked[0]
    if best.score < related_threshold:
        return SearchOutcome(kind="not_found")
    if question and not material_covers_question(question, best):
        return SearchOutcome(kind="not_found")
    if best.score < answer_threshold:
        return SearchOutcome(kind="not_found_related", hits=(best,))
    if question and question_aligns_with_title(question, best.title):
        return SearchOutcome(kind="answer", hits=ranked)
    if len(ranked) >= 2 and is_vague_question(question):
        second = ranked[1]
        gap = best.score - second.score
        if second.score >= answer_threshold and gap <= clarify_gap:
            first_key = _title_key(best.title)
            second_key = _title_key(second.title)
            if first_key != second_key:
                return SearchOutcome(
                    kind="clarify",
                    hits=ranked,
                    variants=(best.title, second.title),
                )
            return SearchOutcome(kind="clarify_free", hits=ranked)
    return SearchOutcome(kind="answer", hits=ranked)
