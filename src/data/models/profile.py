from __future__ import annotations

import uuid
from datetime import datetime
from enum import EnumMeta

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base
from src.data.models.enums import BusinessStage, TaxMode


def _enum_values(enum_cls: EnumMeta) -> list[str]:
    return [member.value for member in enum_cls]


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("app.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    sphere: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stage: Mapped[BusinessStage | None] = mapped_column(
        Enum(
            BusinessStage,
            name="business_stage",
            schema="app",
            values_callable=_enum_values,
            validate_strings=True,
        ),
        nullable=True,
    )
    mode: Mapped[TaxMode | None] = mapped_column(
        Enum(
            TaxMode,
            name="tax_mode",
            schema="app",
            values_callable=_enum_values,
            validate_strings=True,
        ),
        nullable=True,
    )
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
