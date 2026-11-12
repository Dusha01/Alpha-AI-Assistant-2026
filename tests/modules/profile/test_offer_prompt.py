from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import Profile
from src.data.models.enums import BusinessStage, TaxMode
from src.data.repositories.profiles import ProfileRepository
from src.data.repositories.users import UserRepository
from src.modules.profile.labels import profile_needs_sphere
from src.modules.profile.service import ProfileService

pytestmark = pytest.mark.integration


def test_profile_needs_sphere_when_stage_filled() -> None:
    profile = Profile(
        user_id=uuid.uuid4(),
        stage=BusinessStage.PLANNING,
        mode=TaxMode.USN,
    )
    assert profile_needs_sphere(profile) is True


async def test_should_offer_when_sphere_missing(
    profile_session_factory,
    db_session: AsyncSession,
) -> None:
    users = UserRepository(db_session)
    profiles = ProfileRepository(db_session)
    user = await users.create(telegram_id=300000099)
    await profiles.upsert(
        user.id,
        stage=BusinessStage.PLANNING,
        mode=TaxMode.PATENT,
    )
    await db_session.commit()
    service = ProfileService(profile_session_factory)  # type: ignore[arg-type]
    assert await service.should_offer_business_prompt(user.id) is True
