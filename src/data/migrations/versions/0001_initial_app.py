"""initial app schema

Revision ID: 0001_initial_app
Revises:
Create Date: 2026-11-11

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_app"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("CREATE TYPE app.business_stage AS ENUM ('planning', 'lt_year', 'gt_year')")
    op.execute("CREATE TYPE app.tax_mode AS ENUM ('usn', 'patent', 'npd', 'other', 'unknown')")

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("telegram_id <> 0", name="ck_users_telegram_id_not_zero"),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        schema="app",
    )
    op.create_table(
        "profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sphere", sa.String(length=255), nullable=True),
        sa.Column(
            "stage",
            postgresql.ENUM(
                "planning",
                "lt_year",
                "gt_year",
                name="business_stage",
                schema="app",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "mode",
            postgresql.ENUM(
                "usn",
                "patent",
                "npd",
                "other",
                "unknown",
                name="tax_mode",
                schema="app",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name="fk_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_profiles"),
        schema="app",
    )
    op.create_table(
        "dialog_states",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "state",
            sa.String(length=64),
            server_default=sa.text("'idle'"),
            nullable=False,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["app.users.id"],
            name="fk_dialog_states_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_dialog_states"),
        schema="app",
    )


def downgrade() -> None:
    op.drop_table("dialog_states", schema="app")
    op.drop_table("profiles", schema="app")
    op.drop_table("users", schema="app")
    op.execute("DROP TYPE IF EXISTS app.tax_mode")
    op.execute("DROP TYPE IF EXISTS app.business_stage")
    op.execute("DROP SCHEMA IF EXISTS app")
