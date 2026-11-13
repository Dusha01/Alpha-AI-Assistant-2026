from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.questions.catalog import CASES
from tests.questions.harness import QuestionDialog, question_settings
from tests.questions.report import emit_lines

from src.core.settings import Settings
from src.data.models.chunk import Chunk

_config: pytest.Config | None = None
_announced = False


def pytest_configure(config: pytest.Config) -> None:
    global _config
    _config = config


def pytest_runtest_logstart(nodeid: str, location: tuple[str, int | None, str]) -> None:
    global _announced
    path = nodeid.replace("\\", "/")
    if _config is None or "tests/questions/test_questions.py" not in path:
        return
    number = path.rsplit("[", 1)[-1].rstrip("]")
    case = next((item for item in CASES if f"{item.number:02d}" == number), None)
    lines: list[str] = []
    if not _announced:
        _announced = True
        lines.append("Прогон вопросов. Ниже вход, поиск по базе и ответ.")
    if case is None:
        lines.append(f"старт {number}")
    else:
        question = next(
            (turn for turn in case.turns if turn != "sticker" and not turn.startswith("press:")),
            case.turns[0],
        )
        lines.append(f"  {case.number:02d}  {case.hero}  {question}")
    emit_lines(_config, lines)


@pytest.hookimpl(tryfirst=True)
def pytest_report_teststatus(
    report: pytest.TestReport,
    config: pytest.Config,
) -> tuple[str, str, str] | None:
    if report.when != "call" or config.getoption("verbose") > 0:
        return None
    nodeid = str(report.nodeid).replace("\\", "/")
    if "tests/questions/test_questions.py" not in nodeid:
        return None
    if report.outcome in {"passed", "failed", "skipped"}:
        return report.outcome, "", report.outcome.upper()
    return None


@pytest_asyncio.fixture
async def question_dialog(profile_session_factory, db_session: AsyncSession) -> QuestionDialog:
    count = await db_session.scalar(select(func.count()).select_from(Chunk))
    if not count:
        pytest.fail("В базе нет чанков знаний. Сначала загрузите материалы.")
    return QuestionDialog(
        session_factory=profile_session_factory,
        db=db_session,
        settings=question_settings(Settings()),
    )
