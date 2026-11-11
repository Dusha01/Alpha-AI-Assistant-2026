from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.chunk import Chunk
from src.data.repositories.chunks import ChunkRepository

pytestmark = pytest.mark.integration


async def test_content_chunks_table_exists(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT count(*) FROM pg_tables WHERE schemaname = 'content' AND tablename = 'chunks'")
    )
    assert result.scalar_one() == 1


async def test_replace_for_material_is_idempotent(db_session: AsyncSession) -> None:
    repository = ChunkRepository(db_session)
    material_id = uuid.uuid4()

    first = Chunk(
        material_type="article",
        material_id=material_id,
        chunk_index=0,
        title="Тест",
        url=None,
        is_paid=False,
        body="тело",
        include_in_rag=True,
        embedding=[0.1] * 384,
    )
    await repository.replace_for_material("article", material_id, [first])
    assert await repository.count_for_material("article", material_id) == 1

    updated = Chunk(
        material_type="article",
        material_id=material_id,
        chunk_index=0,
        title="Тест 2",
        url=None,
        is_paid=False,
        body="новое тело",
        include_in_rag=True,
        embedding=[0.2] * 384,
    )
    await repository.replace_for_material("article", material_id, [updated])
    assert await repository.count_for_material("article", material_id) == 1
