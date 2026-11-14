from __future__ import annotations

import pytest
from tests.questions.catalog import CASES, QuestionCase
from tests.questions.harness import QuestionDialog
from tests.questions.report import emit_lines

from src.handlers.text import COPY
from src.modules.knowledge.decision import decide_outcome

pytestmark = pytest.mark.questions

_section = ""


def _norm(text: str) -> str:
    return " ".join(text.lower().replace("ё", "е").split())


def _hit_matches(
    url: str | None,
    title: str,
    case: QuestionCase,
    *,
    is_paid: bool = False,
) -> bool:
    if case.accept_paid and is_paid:
        return True
    folded_url = (url or "").lower()
    folded_title = title.lower()
    if any(slug in folded_url for slug in case.slugs):
        return True
    return any(fragment.lower() in folded_title for fragment in case.titles)


def _write(config: pytest.Config, case: QuestionCase, rows: list[str]) -> None:
    global _section
    lines: list[str] = []
    if case.section != _section:
        _section = case.section
        lines.append("")
        lines.append(case.section)
    question = next(
        (turn for turn in case.turns if turn != "sticker" and not turn.startswith("press:")),
        case.turns[0],
    )
    lines.append(f"  {case.number:02d}  {case.hero}  {question}")
    lines.extend(f"      {row}" for row in rows)
    emit_lines(config, lines)


async def _play(dialog: QuestionDialog, case: QuestionCase) -> list[tuple[str, str]]:
    if case.seed_usn:
        await dialog.add_usn_deadline()
    await dialog.prepare(case.hero)
    transcript: list[tuple[str, str]] = []
    for turn in case.turns:
        if turn == "sticker":
            result = await dialog.send_sticker()
        elif turn.startswith("press:"):
            result = await dialog.press(turn.removeprefix("press:"))
        else:
            result = await dialog.say(turn)
        transcript.append((turn, result.text))
    return transcript


def _search_question(case: QuestionCase) -> str:
    for turn in reversed(case.turns):
        if turn != "sticker" and not turn.startswith("press:") and not turn.startswith("/"):
            return turn
    return case.turns[-1]


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case.number:02d}")
async def test_question(
    case: QuestionCase,
    question_dialog: QuestionDialog,
    request: pytest.FixtureRequest,
) -> None:
    calls_before = question_dialog.llm.calls
    transcript = await _play(question_dialog, case)
    reply = "\n".join(text for _, text in transcript if text)
    rows = [
        f"{'кнопка' if turn.startswith('press:') else 'вопрос'}  {turn}" for turn, _ in transcript
    ]
    rows.extend(f"ответ   {line}" for line in reply.splitlines() if line.strip())

    if case.kind in {"answer", "paid", "non_text"} and (case.slugs or case.titles):
        question = _search_question(case)
        hits = await question_dialog.knowledge.search(question)
        outcome = decide_outcome(
            hits,
            question=question,
            answer_threshold=question_dialog.settings.rag_score_threshold,
            related_threshold=question_dialog.settings.rag_related_score_threshold,
            clarify_gap=question_dialog.settings.rag_clarify_score_gap,
        )
        if hits:
            rows.insert(0, f"поиск   {outcome.kind}  {hits[0].score:.2f}  {hits[0].title}")
        else:
            rows.insert(0, "поиск   пусто")
        if case.kind == "paid":
            messages = question_dialog.llm.last_messages or []
            prompt = "\n".join(item["content"] for item in messages)
            for hit in hits[:3]:
                if hit.is_paid and len(hit.body) > 220 and hit.body[180:320] in prompt:
                    rows.append("промпт  в запрос попал текст урока")

    folded = _norm(reply)
    if case.kind in {"answer", "paid"} and (
        COPY["error_llm"] in reply or not question_dialog.llm_ready()
    ):
        rows.append("ответ   модель недоступна, проверка фактов пропущена")
    _write(request.config, case, rows)
    if case.kind in {"answer", "paid", "non_text"} and (case.slugs or case.titles):
        assert hits, f"{case.number}: поиск ничего не нашёл"
        assert _hit_matches(hits[0].url, hits[0].title, case, is_paid=hits[0].is_paid), hits[
            0
        ].title
        if case.kind == "paid":
            prompt = "\n".join(
                item["content"] for item in (question_dialog.llm.last_messages or [])
            )
            for hit in hits[:3]:
                if hit.is_paid and len(hit.body) > 220:
                    assert hit.body[180:320] not in prompt
    if case.kind == "outside":
        assert question_dialog.llm.calls == calls_before
        assert COPY[case.copy_key] in reply
    elif case.kind == "clarify":
        assert question_dialog.llm.calls == calls_before
        if case.copy_key:
            assert COPY[case.copy_key] in reply
        for piece in case.must:
            assert _norm(piece) in folded
    elif case.kind == "dialog":
        assert reply.strip()
        for piece in case.must:
            assert _norm(piece) in folded
    elif case.kind == "non_text":
        assert COPY["non_text"] in reply
    elif case.kind in {"answer", "paid"}:
        for piece in case.forbidden:
            assert _norm(piece) not in folded
        if COPY["error_llm"] in reply or not question_dialog.llm_ready():
            return
        else:
            assert COPY["error_general"] not in reply
            for fact in case.facts:
                assert _norm(fact) in folded
            if case.slugs:
                assert any(slug in reply for slug in case.slugs) or any(
                    _norm(title) in folded for title in case.titles
                )
    if case.kind == "non_text" and case.slugs and COPY["error_llm"] not in reply:
        if question_dialog.llm_ready():
            assert any(slug in reply for slug in case.slugs)
