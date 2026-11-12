from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from src.core.settings import Settings
from src.data.migrate import run_migrations


@pytest.fixture(autouse=True)
def _reset_loguru() -> Iterator[None]:
    logger.remove()
    yield
    logger.remove()


def _database_url() -> str:
    settings = Settings()
    return os.getenv("DATABASE_URL_TEST") or settings.database_url_resolved


@pytest_asyncio.fixture
async def database_engine() -> AsyncIterator[AsyncEngine]:
    url = _database_url()
    if not url.strip():
        pytest.skip("DATABASE_URL_TEST или DATABASE_URL_HOST не задан")
    await asyncio.to_thread(run_migrations, url)
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
def profile_session_factory(db_session: AsyncSession):
    """Одна тестовая сессия для ProfileService (интеграционные FSM-тесты)."""

    class _SessionCtx:
        async def __aenter__(self) -> AsyncSession:
            return db_session

        async def __aexit__(self, *args: object) -> None:
            await db_session.commit()

    class _Maker:
        def __call__(self) -> _SessionCtx:
            return _SessionCtx()

    return _Maker()


@pytest_asyncio.fixture
async def db_session(database_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with database_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
