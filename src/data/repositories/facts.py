from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select

from src.data.models.fact import Fact
from src.data.repositories.base import BaseRepository
from src.modules.knowledge.types import FactHit


class FactRepository(BaseRepository):
    async def delete_for_material(self, material_type: str, material_id: uuid.UUID) -> int:
        result = await self.session.execute(
            delete(Fact).where(
                Fact.material_type == material_type,
                Fact.material_id == material_id,
            )
        )
        return int(result.rowcount or 0)

    async def count_for_material(self, material_type: str, material_id: uuid.UUID) -> int:
        value = await self.session.scalar(
            select(func.count())
            .select_from(Fact)
            .where(
                Fact.material_type == material_type,
                Fact.material_id == material_id,
            )
        )
        return int(value or 0)

    async def replace_for_material(self, fact: Fact) -> None:
        await self.delete_for_material(fact.material_type, fact.material_id)
        self.session.add(fact)
        await self.session.flush()

    async def search_similar(self, query_vector: list[float], *, limit: int) -> list[FactHit]:
        distance = Fact.embedding.cosine_distance(query_vector)
        score = (1 - distance).label("score")
        stmt = (
            select(Fact, score).where(Fact.embedding.is_not(None)).order_by(distance).limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [FactHit(body=fact.body, score=float(row_score)) for fact, row_score in rows]
