from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from src.data.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("telegram_id <> 0", name="telegram_id_not_zero"),
        UniqueConstraint("telegram_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
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

    @validates("telegram_id")
    def validate_telegram_id(self, key: str, value: Any) -> int:
        if value is None:
            raise ValueError("telegram_id не может быть пустым")
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                raise ValueError("telegram_id не может быть пустым")
            if not raw.lstrip("-").isdigit():
                raise ValueError("telegram_id должен быть числом")
            value = int(raw)
        if not isinstance(value, int) or isinstance(value, bool) or value == 0:
            raise ValueError("telegram_id не может быть пустым")
        return value
