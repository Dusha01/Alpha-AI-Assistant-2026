from __future__ import annotations

from sqlalchemy import select

from src.data.models import User
from src.data.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.session.scalar(select(User).where(User.telegram_id == telegram_id))

    async def create(self, telegram_id: int, username: str | None = None) -> User:
        user = User(telegram_id=telegram_id, username=username)
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_or_create(self, telegram_id: int, username: str | None = None) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user is not None:
            return user
        return await self.create(telegram_id, username)
