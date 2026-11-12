from __future__ import annotations

import uuid
from datetime import date
from enum import EnumMeta

from sqlalchemy import Date, Enum, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import Base
from src.data.models.enums import TaxMode


def _enum_values(enum_cls: EnumMeta) -> list[str]:
    return [member.value for member in enum_cls]


class TaxDeadline(Base):
    __tablename__ = "tax_deadlines"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    mode: Mapped[TaxMode] = mapped_column(
        Enum(
            TaxMode,
            name="tax_mode",
            schema="app",
            values_callable=_enum_values,
            validate_strings=True,
            create_type=False,
        ),
        nullable=False,
    )
    what_to_pay: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    lead_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="14")
    source_note: Mapped[str] = mapped_column(Text, nullable=False)
    material_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    material_slug: Mapped[str | None] = mapped_column(Text, nullable=True)
