"""content.material_tags seed

Revision ID: 0003_material_tags
Revises: 0002_content_chunks
Create Date: 2026-11-12

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_material_tags"
down_revision: str | Sequence[str] | None = "0002_content_chunks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "material_tags",
        sa.Column("material_slug", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("topics", sa.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("stages", sa.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("audiences", sa.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("is_paid", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        schema="content",
    )
    op.create_primary_key(
        "pk_material_tags",
        "material_tags",
        ["material_slug"],
        schema="content",
    )
    material_tags = sa.table(
        "material_tags",
        sa.column("material_slug", sa.Text()),
        sa.column("title", sa.Text()),
        sa.column("topics", sa.ARRAY(sa.Text())),
        sa.column("stages", sa.ARRAY(sa.Text())),
        sa.column("audiences", sa.ARRAY(sa.Text())),
        sa.column("is_paid", sa.Boolean()),
        schema="content",
    )
    op.bulk_insert(
        material_tags,
        [
            {
                "material_slug": "azy-finansovoj-gramotnosti",
                "title": "Азы финансовой грамотности",
                "topics": ["startup", "finance", "general"],
                "stages": ["planning"],
                "audiences": ["newbie"],
                "is_paid": False,
            },
            {
                "material_slug": "usn-income-template",
                "title": "Шаблон учёта доходов на УСН",
                "topics": ["usn", "finance"],
                "stages": ["lt_year", "gt_year"],
                "audiences": ["coffee_usn"],
                "is_paid": False,
            },
            {
                "material_slug": "marketing-solo",
                "title": "Маркетинг для соло-предпринимателя",
                "topics": ["marketing"],
                "stages": ["planning", "lt_year", "gt_year"],
                "audiences": ["solo_marketing"],
                "is_paid": False,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("material_tags", schema="content")
