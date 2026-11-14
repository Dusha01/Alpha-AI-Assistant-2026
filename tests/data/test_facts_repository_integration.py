from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.fact import Fact
from src.data.repositories.facts import FactRepository

pytestmark = pytest.mark.integration


async def test_content_facts_table_exists(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT count(*) FROM pg_tables WHERE schemaname = 'content' AND tablename = 'facts'")
    )
    assert result.scalar_one() == 1


async def test_search_similar_returns_the_nearest_fact(db_session: AsyncSession) -> None:
    repository = FactRepository(db_session)
    near = Fact(
        material_type="article",
        material_id=uuid.uuid4(),
        source_title="Близкий",
        source_url=None,
        body="близкий факт",
        embedding=[1.0] + [0.0] * 383,
    )
    far = Fact(
        material_type="article",
        material_id=uuid.uuid4(),
        source_title="Дальний",
        source_url=None,
        body="дальний факт",
        embedding=[0.0, 1.0] + [0.0] * 382,
    )
    await repository.replace_for_material(near)
    await repository.replace_for_material(far)

    found = await repository.search_similar([1.0] + [0.0] * 383, limit=1)
    assert [item.body for item in found] == ["близкий факт"]
    assert found[0].score > 0.99


async def test_replace_for_material_does_not_duplicate(db_session: AsyncSession) -> None:
    repository = FactRepository(db_session)
    material_id = uuid.uuid4()
    first = Fact(
        material_type="article",
        material_id=material_id,
        source_title="УСН",
        source_url=None,
        body="первая формулировка",
        embedding=[0.2] * 384,
    )
    await repository.replace_for_material(first)
    assert await repository.count_for_material("article", material_id) == 1

    updated = Fact(
        material_type="article",
        material_id=material_id,
        source_title="УСН",
        source_url=None,
        body="вторая формулировка",
        embedding=[0.3] * 384,
    )
    await repository.replace_for_material(updated)
    assert await repository.count_for_material("article", material_id) == 1
    found = await repository.search_similar([0.3] * 384, limit=1)
    assert found[0].body == "вторая формулировка"
