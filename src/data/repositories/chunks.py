from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select

from src.data.models.chunk import Chunk
from src.data.repositories.base import BaseRepository
from src.modules.knowledge.types import SearchHit


class ChunkRepository(BaseRepository):
    async def delete_for_material(self, material_type: str, material_id: uuid.UUID) -> int:
        result = await self.session.execute(
            delete(Chunk).where(
                Chunk.material_type == material_type,
                Chunk.material_id == material_id,
            )
        )
        return int(result.rowcount or 0)

    async def add(self, chunk: Chunk) -> Chunk:
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def count_for_material(self, material_type: str, material_id: uuid.UUID) -> int:
        value = await self.session.scalar(
            select(func.count())
            .select_from(Chunk)
            .where(
                Chunk.material_type == material_type,
                Chunk.material_id == material_id,
            )
        )
        return int(value or 0)

    async def replace_for_material(
        self,
        material_type: str,
        material_id: uuid.UUID,
        chunks: list[Chunk],
    ) -> int:
        await self.delete_for_material(material_type, material_id)
        for chunk in chunks:
            self.session.add(chunk)
        await self.session.flush()
        return len(chunks)

    async def search_similar(self, query_vector: list[float], *, limit: int) -> list[SearchHit]:
        distance = Chunk.embedding.cosine_distance(query_vector)
        score = (1 - distance).label("score")
        stmt = (
            select(Chunk, score)
            .where(
                Chunk.embedding.is_not(None),
                Chunk.include_in_rag.is_(True),
            )
            .order_by(distance)
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            SearchHit(
                title=chunk.title,
                url=chunk.url,
                body=chunk.body,
                is_paid=chunk.is_paid,
                score=float(row_score),
                include_in_rag=chunk.include_in_rag,
            )
            for chunk, row_score in rows
        ]
