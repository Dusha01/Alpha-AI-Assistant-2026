from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select

from src.data.models.chunk import Chunk
from src.data.repositories.base import BaseRepository


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
