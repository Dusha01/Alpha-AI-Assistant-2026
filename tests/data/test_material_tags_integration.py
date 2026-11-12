from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


async def test_material_tags_seed_present(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT count(*) FROM content.material_tags "
            "WHERE material_slug IN ("
            "'azy-finansovoj-gramotnosti', "
            "'usn-income-template', "
            "'marketing-solo'"
            ")"
        )
    )
    assert result.scalar_one() == 3
