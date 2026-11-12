from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.enums import ReminderRepeat, ReminderStatus
from src.data.repositories.reminders import ReminderRepository
from src.data.repositories.users import UserRepository
from src.modules.reminders.service import ReminderService

pytestmark = pytest.mark.integration


async def test_create_active_reminder(
    profile_session_factory,
    db_session: AsyncSession,
) -> None:
    user = await UserRepository(db_session).create(telegram_id=400000001)
    when = datetime.now(UTC) + timedelta(days=1)
    row = await ReminderRepository(db_session).create(
        user.id,
        text="Продолжить курс",
        repeat=ReminderRepeat.WEEKLY,
        next_fire_at=when,
    )
    await db_session.commit()
    assert row.status == ReminderStatus.ACTIVE
    assert row.text == "Продолжить курс"


async def test_pause_excluded_from_due(
    profile_session_factory,
    db_session: AsyncSession,
) -> None:
    user = await UserRepository(db_session).create(telegram_id=400000002)
    repo = ReminderRepository(db_session)
    when = datetime.now(UTC) - timedelta(minutes=1)
    row = await repo.create(
        user.id,
        text="Тест",
        repeat=ReminderRepeat.ONCE,
        next_fire_at=when,
    )
    await repo.set_status(row.id, ReminderStatus.PAUSED)
    await db_session.commit()
    due = await repo.claim_due(datetime.now(UTC))
    assert all(item.id != row.id for item in due)


async def test_confirm_flow_creates_active(
    profile_session_factory,
    db_session: AsyncSession,
) -> None:
    from src.data.repositories.dialog_states import DialogStateRepository
    from src.modules.reminders import states

    user = await UserRepository(db_session).create(telegram_id=400000003)
    dialogs = DialogStateRepository(db_session)
    when = datetime.now(UTC) + timedelta(hours=2)
    await dialogs.set_state(
        user.id,
        states.REMINDER_CONFIRM,
        payload={
            "reminder_text": "Демо",
            "reminder_when": when.isoformat(),
            "reminder_repeat": ReminderRepeat.MONTHLY.value,
        },
    )
    await db_session.commit()
    service = ReminderService(
        settings=__import__("src.core.settings", fromlist=["Settings"]).Settings(),
        session_factory=profile_session_factory,  # type: ignore[arg-type]
    )
    reply = await service.handle_callback(user.id, "reminder_confirm:yes")
    assert reply is not None
    rows = await ReminderRepository(db_session).list_for_user(user.id)
    assert len(rows) == 1
    assert rows[0].status == ReminderStatus.ACTIVE
    assert rows[0].repeat == ReminderRepeat.MONTHLY
