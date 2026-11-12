from __future__ import annotations

import re

from src.modules.knowledge.types import SearchHit

_WORD = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+")
_ACRONYMS = frozenset({"усн", "псн", "ндс", "нпд", "ип", "ооо", "кудир"})
_MUST_APPEAR = frozenset({"виза", "визу", "визы", "визе", "визой"})
_STOP = frozenset(
    {
        "как",
        "что",
        "где",
        "когда",
        "можно",
        "нужно",
        "есть",
        "или",
        "для",
        "это",
        "если",
        "ли",
        "вы",
        "на",
        "по",
        "в",
        "и",
        "с",
        "у",
    }
)


def significant_terms(question: str) -> list[str]:
    terms = [match.group(0).lower() for match in _WORD.finditer(question)]
    return [term for term in terms if (len(term) >= 4 or term in _ACRONYMS) and term not in _STOP]


def mandatory_terms(question: str) -> list[str]:
    return [term for term in significant_terms(question) if term in _MUST_APPEAR]


def _term_in_text(term: str, text: str) -> bool:
    if term in text:
        return True
    stem = term[:4]
    if len(stem) == 4 and stem in text:
        return True
    if term.endswith("ов") and len(term) > 4:
        root = term[:-2]
        if root in text:
            return True
    if term in _ACRONYMS:
        return term in text
    return False


def material_covers_question(question: str, hit: SearchHit) -> bool:
    blob = f"{hit.title} {hit.body}".lower()
    for term in mandatory_terms(question):
        if not _term_in_text(term, blob):
            return False
    terms = significant_terms(question)
    if not terms:
        return True
    if len(terms) > 3:
        terms = sorted(terms, key=len, reverse=True)[:3]
    matched = sum(1 for term in terms if _term_in_text(term, blob))
    if matched == len(terms):
        return True
    if len(terms) == 1:
        return matched == 1
    return matched >= len(terms) - 1


def is_vague_question(question: str) -> bool:
    terms = significant_terms(question)
    return len(terms) <= 2


def _title_key(title: str) -> str:
    return " ".join(title.lower().split())


def question_aligns_with_title(question: str, title: str) -> bool:
    question_key = _title_key(question)
    title_key = _title_key(title)
    if not question_key or not title_key:
        return False
    if question_key == title_key or question_key in title_key or title_key in question_key:
        return True
    question_terms = set(significant_terms(question))
    title_terms = set(significant_terms(title))
    return bool(question_terms) and question_terms.issubset(title_terms)
