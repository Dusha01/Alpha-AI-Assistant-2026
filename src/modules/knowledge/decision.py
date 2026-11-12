from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.modules.knowledge.relevance import (
    is_vague_question,
    material_covers_question,
    question_aligns_with_title,
    significant_terms,
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


def _titles_are_same_topic(title_a: str, title_b: str) -> bool:
    key_a = _title_key(title_a)
    key_b = _title_key(title_b)
    if key_a == key_b or key_a in key_b or key_b in key_a:
        return True
    terms_a = set(significant_terms(title_a))
    terms_b = set(significant_terms(title_b))
    if not terms_a or not terms_b:
        return False
    return terms_a <= terms_b or terms_b <= terms_a


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
            if first_key != second_key and not _titles_are_same_topic(best.title, second.title):
                return SearchOutcome(
                    kind="clarify",
                    hits=ranked,
                    variants=(best.title, second.title),
                )
            return SearchOutcome(kind="answer", hits=ranked)
    return SearchOutcome(kind="answer", hits=ranked)
