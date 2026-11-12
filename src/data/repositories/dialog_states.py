from __future__ import annotations

import uuid

from src.data.models import DialogState
from src.data.repositories.base import BaseRepository


class DialogStateRepository(BaseRepository):
    async def get_by_user_id(self, user_id: uuid.UUID) -> DialogState | None:
        return await self.session.get(DialogState, user_id)

    async def get_or_create(self, user_id: uuid.UUID) -> DialogState:
        row = await self.get_by_user_id(user_id)
        if row is not None:
            return row
        row = DialogState(user_id=user_id, state="idle", payload={})
        self.session.add(row)
        await self.session.flush()
        return row

    async def set_state(
        self,
        user_id: uuid.UUID,
        state: str,
        *,
        payload: dict[str, object] | None = None,
    ) -> DialogState:
        row = await self.get_or_create(user_id)
        row.state = state
        if payload is not None:
            row.payload = payload
        await self.session.flush()
        return row
