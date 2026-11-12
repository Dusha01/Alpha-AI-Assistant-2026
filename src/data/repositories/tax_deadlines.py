from __future__ import annotations

from datetime import date

from sqlalchemy import select

from src.data.models import TaxDeadline
from src.data.models.enums import TaxMode
from src.data.repositories.base import BaseRepository


class TaxDeadlineRepository(BaseRepository):
    async def next_for_mode(self, mode: TaxMode, *, on_or_after: date) -> TaxDeadline | None:
        result = await self.session.execute(
            select(TaxDeadline)
            .where(TaxDeadline.mode == mode, TaxDeadline.due_date >= on_or_after)
            .order_by(TaxDeadline.due_date.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()
