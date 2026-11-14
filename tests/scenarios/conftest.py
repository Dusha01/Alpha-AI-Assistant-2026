from __future__ import annotations

from collections.abc import Callable

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from tests.scenarios.harness import Dialog, ScriptedKnowledge, open_dialog
from tests.scenarios.progress import remember, report_status


@pytest.hookimpl(tryfirst=True)
def pytest_report_teststatus(
    report: pytest.TestReport,
    config: pytest.Config,
) -> tuple[str, str, str] | None:
    return report_status(report, config)


def pytest_runtest_setup(item: pytest.Item) -> None:
    remember(item)


@pytest_asyncio.fixture
async def make_dialog(profile_session_factory, db_session: AsyncSession) -> Callable[..., Dialog]:
    def _make(**kwargs: object) -> Dialog:
        return open_dialog(session_factory=profile_session_factory, db=db_session, **kwargs)  # type: ignore[arg-type]

    return _make


@pytest_asyncio.fixture
async def dialog(make_dialog: Callable[..., Dialog]) -> Dialog:
    return make_dialog()


@pytest_asyncio.fixture
async def knowledge() -> ScriptedKnowledge:
    return ScriptedKnowledge()
