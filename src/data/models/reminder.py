from __future__ import annotations

import uuid
from datetime import datetime
from enum import EnumMeta

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base
from src.data.models.enums import ReminderRepeat, ReminderStatus


def _enum_values(enum_cls: EnumMeta) -> list[str]:
    return [member.value for member in enum_cls]


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    repeat: Mapped[ReminderRepeat] = mapped_column(
        Enum(
            ReminderRepeat,
            name="reminder_repeat",
            schema="app",
            values_callable=_enum_values,
            validate_strings=True,
            create_type=False,
        ),
        nullable=False,
    )
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(
            ReminderStatus,
            name="reminder_status",
            schema="app",
            values_callable=_enum_values,
            validate_strings=True,
            create_type=False,
        ),
        nullable=False,
        server_default=ReminderStatus.ACTIVE.value,
    )
    next_fire_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    material_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    material_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_tax: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
