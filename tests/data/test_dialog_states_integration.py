from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.repositories.dialog_states import DialogStateRepository
from src.data.repositories.users import UserRepository

pytestmark = pytest.mark.integration


async def test_dialog_state_set_and_read(db_session: AsyncSession) -> None:
    users = UserRepository(db_session)
    dialogs = DialogStateRepository(db_session)
    user = await users.create(telegram_id=200000010)
    await dialogs.set_state(user.id, "ask_business")
    row = await dialogs.get_by_user_id(user.id)
    assert row is not None
    assert row.state == "ask_business"
