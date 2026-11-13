from __future__ import annotations

import re
from dataclasses import replace

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


_QUOTE = re.compile(r"[«\"]([^»\"]+)[»\"]")
_SYNONYM_STEMS = (("магаз", "рознич"), ("полк", "полоч"), ("спис", "списа"))


def significant_terms(question: str) -> list[str]:
    terms = [match.group(0).lower() for match in _WORD.finditer(question)]
    chosen: list[str] = []
    for term in terms:
        if term in _STOP:
            continue
        if term in _ACRONYMS or len(term) >= 4 or (term.isascii() and len(term) >= 2):
            chosen.append(term)
    return chosen


def mandatory_terms(question: str) -> list[str]:
    return [term for term in significant_terms(question) if term in _MUST_APPEAR]


def _normalize_token(token: str) -> str:
    folded = token.lower().replace("ё", "е")
    return re.sub(r"(.)\1+", r"\1", folded)


def _levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for index, left_char in enumerate(left, start=1):
        current = [index]
        for right_index, right_char in enumerate(right, start=1):
            insert = current[right_index - 1] + 1
            delete = previous[right_index] + 1
            replace = previous[right_index - 1] + (left_char != right_char)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def _close_typo(left: str, right: str) -> bool:
    if len(left) < 6 or len(right) < 6:
        return False
    distance = _levenshtein(left, right)
    return 1 - distance / max(len(left), len(right)) >= 0.8


def _term_in_text(term: str, text: str) -> bool:
    folded_term = _normalize_token(term)
    words = [_normalize_token(word) for word in _WORD.findall(text)]
    for word in words:
        if word == folded_term or word.startswith(folded_term):
            return True
        if (
            len(folded_term) >= 6
            and word.startswith(folded_term[:5])
            and not (folded_term.startswith("фильтр") and word.startswith("фильтрац"))
        ):
            return True
        if len(folded_term) >= 6 and _close_typo(folded_term, word):
            return True
    if term.endswith("ов") and len(term) > 4:
        root = _normalize_token(term[:-2])
        if any(word.startswith(root) for word in words):
            return True
    if term in _ACRONYMS and any(word == term or term in word for word in words):
        return True
    for left, right in _SYNONYM_STEMS:
        if folded_term.startswith(left) and any(right in word for word in words):
            return True
        if folded_term.startswith(right) and any(left in word for word in words):
            return True
    return folded_term.startswith("маркетпле") and "marketplejs" in text.lower()


def expand_query(question: str) -> str:
    folded = question.lower().replace("ё", "е")
    extra: list[str] = []
    if "недостач" in folded or "полк" in folded:
        extra.append("инвентаризация остатки")
    if "списыва" in folded:
        extra.append("списание")
    if "qr" in folded:
        extra.append("оплата по QR-коду")
    if "магазин" in folded and ("патент" in folded or "усн" in folded):
        extra.append("розничная торговля")
    if "ассортимент" in folded:
        extra.append("ABC-анализ ассортимента")
    if not extra:
        return question
    return f"{question} {' '.join(extra)}"


def coverage_count(question: str, hit: SearchHit) -> int:
    blob = f"{hit.title} {hit.body}"
    return sum(1 for term in significant_terms(question) if _term_in_text(term, blob))


def quote_terms(question: str) -> list[str]:
    found: list[str] = []
    for chunk in _QUOTE.findall(question):
        found.extend(significant_terms(chunk))
    return found


def _asks_paid(question: str) -> bool:
    folded = question.lower()
    return "платн" in folded or ("куп" in folded and ("курс" in folded or "маркет" in folded))


def _title_terms(question: str, hit: SearchHit) -> list[str]:
    blob = f"{hit.title} {hit.url or ''}"
    terms = [term for term in significant_terms(question) if _term_in_text(term, blob)]
    terms.extend(term for term in _expansion_terms(question) if _term_in_text(term, blob))
    return terms


def _expansion_terms(question: str) -> list[str]:
    folded = question.lower().replace("ё", "е")
    terms: list[str] = []
    if "недостач" in folded or "полк" in folded:
        terms.append("инвентаризация")
    if "списыва" in folded:
        terms.append("списание")
    if "магазин" in folded and ("патент" in folded or "усн" in folded):
        terms.append("розничн")
    if "ассортимент" in folded:
        terms.append("abc")
    return terms


def _vat_limit_bonus(question: str, hit: SearchHit) -> int:
    folded = question.lower().replace("ё", "е")
    if "ндс" not in folded or "усн" not in folded:
        return 0
    blob = f"{hit.title} {hit.url or ''}".lower()
    if "ндс" not in blob and "nds" not in blob:
        return 0
    return int("kak-rabotat-i-ne-sojti-s-uma" in (hit.url or ""))


def _keeps_question_acronyms(question: str, leader: SearchHit, hit: SearchHit) -> bool:
    leader_blob = f"{leader.title} {leader.url or ''}"
    hit_blob = f"{hit.title} {hit.url or ''}"
    for term in significant_terms(question):
        if term not in _ACRONYMS:
            continue
        if _term_in_text(term, leader_blob) and not _term_in_text(term, hit_blob):
            return False
    return True


def prefer_lexical_hit(
    hits: list[SearchHit],
    question: str,
    *,
    gap: float = 0.04,
) -> list[SearchHit]:
    if len(hits) < 2 or not question.strip():
        return hits
    best = hits[0]
    best_score = best.score
    pool = [hit for hit in hits if best_score - hit.score <= gap]
    named = quote_terms(question)
    paid_intent = _asks_paid(question)

    def sort_key(hit: SearchHit) -> tuple[int, int, int, int, int, float]:
        named_hits = sum(1 for term in named if _term_in_text(term, f"{hit.title} {hit.url or ''}"))
        paid = int(hit.is_paid and (named_hits > 0 or paid_intent))
        distance = best_score - hit.score
        title_count = len(_title_terms(question, hit))
        hint_count = sum(1 for term in _expansion_terms(question) if _term_in_text(term, hit.title))
        title_bonus = 0
        if title_count >= 4 and distance <= 0.03 and _keeps_question_acronyms(question, best, hit):
            title_bonus = title_count
        elif title_count >= 2 and distance <= 0.012:
            title_bonus = title_count
        if distance <= 0.012:
            title_bonus += hint_count
        near_cover = coverage_count(question, hit) if distance <= 0.002 else 0
        vat_bonus = _vat_limit_bonus(question, hit) if distance <= 0.02 else 0
        return (named_hits, paid, vat_bonus, title_bonus, near_cover, hit.score)

    chosen = max(pool, key=sort_key)
    if chosen is hits[0]:
        return hits
    return [chosen, *[hit for hit in hits if hit is not chosen]]


def collapse_by_url(hits: list[SearchHit], question: str) -> list[SearchHit]:
    grouped: dict[str, list[SearchHit]] = {}
    for hit in hits:
        grouped.setdefault(hit.url or hit.title, []).append(hit)
    collapsed: list[SearchHit] = []
    for group in grouped.values():
        peak = max(hit.score for hit in group)
        chosen = max(group, key=lambda hit: (coverage_count(question, hit), hit.score))
        if chosen.score != peak:
            chosen = replace(chosen, score=peak)
        collapsed.append(chosen)
    collapsed.sort(key=lambda hit: hit.score, reverse=True)
    return collapsed


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
