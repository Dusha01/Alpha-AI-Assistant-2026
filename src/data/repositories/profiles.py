from __future__ import annotations

import uuid
from typing import Any

from src.data.models import Profile
from src.data.repositories.base import BaseRepository

_ALLOWED_FIELDS = frozenset({"sphere", "stage", "mode"})


class ProfileRepository(BaseRepository):
    async def get_by_user_id(self, user_id: uuid.UUID) -> Profile | None:
        return await self.session.get(Profile, user_id)

    async def upsert(self, user_id: uuid.UUID, **values: Any) -> Profile:
        unknown = set(values) - _ALLOWED_FIELDS
        if unknown:
            raise ValueError(f"Неизвестные поля профиля: {', '.join(sorted(unknown))}")

        profile = await self.get_by_user_id(user_id)
        if profile is None:
            profile = Profile(user_id=user_id, **values)
            self.session.add(profile)
        else:
            for field, value in values.items():
                setattr(profile, field, value)

        await self.session.flush()
        return profile
