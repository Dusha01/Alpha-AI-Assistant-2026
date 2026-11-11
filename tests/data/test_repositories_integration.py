from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import BusinessStage, TaxMode
from src.data.repositories import ProfileRepository, UserRepository

pytestmark = pytest.mark.integration


async def test_create_and_get_user(db_session: AsyncSession) -> None:
    repository = UserRepository(db_session)

    user = await repository.create(telegram_id=100000001, username="alice")

    assert user.id is not None
    assert user.created_at is not None
    found = await repository.get_by_telegram_id(100000001)
    assert found is not None
    assert found.id == user.id
    assert found.username == "alice"


async def test_get_or_create_is_idempotent(db_session: AsyncSession) -> None:
    repository = UserRepository(db_session)

    first = await repository.get_or_create(telegram_id=100000002, username="first")
    second = await repository.get_or_create(telegram_id=100000002, username="second")

    assert second.id == first.id
    assert second.username == "first"


async def test_profile_upsert_creates_and_updates_partially(db_session: AsyncSession) -> None:
    users = UserRepository(db_session)
    profiles = ProfileRepository(db_session)
    user = await users.create(telegram_id=100000003)

    profile = await profiles.upsert(
        user.id,
        sphere="Кофейня",
        stage=BusinessStage.LT_YEAR,
        mode=TaxMode.USN,
    )
    assert profile.sphere == "Кофейня"
    assert profile.stage == BusinessStage.LT_YEAR
    assert profile.mode == TaxMode.USN

    updated = await profiles.upsert(user.id, sphere="Ретейл")
    await db_session.refresh(updated)

    assert updated.sphere == "Ретейл"
    assert updated.stage == BusinessStage.LT_YEAR
    assert updated.mode == TaxMode.USN


async def test_profile_all_fields_nullable(db_session: AsyncSession) -> None:
    users = UserRepository(db_session)
    profiles = ProfileRepository(db_session)
    user = await users.create(telegram_id=100000004)

    profile = await profiles.upsert(user.id)

    assert profile.sphere is None
    assert profile.stage is None
    assert profile.mode is None


async def test_migrations_created_app_tables(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT count(*) FROM pg_tables "
            "WHERE schemaname = 'app' "
            "AND tablename IN ('users', 'profiles', 'dialog_states')"
        )
    )

    assert result.scalar_one() == 3
