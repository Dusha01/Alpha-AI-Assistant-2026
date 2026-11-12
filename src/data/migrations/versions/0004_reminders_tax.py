"""app reminders and tax deadlines

Revision ID: 0004_reminders_tax
Revises: 0003_material_tags
Create Date: 2026-11-12

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_reminders_tax"
down_revision: str | Sequence[str] | None = "0003_material_tags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE app.reminder_repeat AS ENUM ('once', 'weekly', 'monthly', 'quarterly')")
    op.execute("CREATE TYPE app.reminder_status AS ENUM ('active', 'paused', 'done')")
    op.create_table(
        "reminders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "repeat",
            postgresql.ENUM(
                "once",
                "weekly",
                "monthly",
                "quarterly",
                name="reminder_repeat",
                schema="app",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active",
                "paused",
                "done",
                name="reminder_status",
                schema="app",
                create_type=False,
            ),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("next_fire_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("material_title", sa.Text(), nullable=True),
        sa.Column("material_url", sa.Text(), nullable=True),
        sa.Column("is_tax", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
            name="fk_reminders_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reminders"),
        schema="app",
    )
    op.create_index(
        "ix_reminders_due",
        "reminders",
        ["next_fire_at"],
        schema="app",
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "tax_deadlines",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
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
            nullable=False,
        ),
        sa.Column("what_to_pay", sa.Text(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("lead_days", sa.Integer(), server_default="14", nullable=False),
        sa.Column("source_note", sa.Text(), nullable=False),
        sa.Column("material_title", sa.Text(), nullable=True),
        sa.Column("material_slug", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_tax_deadlines"),
        schema="app",
    )
    op.execute(
        """
        INSERT INTO app.tax_deadlines
            (mode, what_to_pay, due_date, lead_days, source_note, material_title, material_slug)
        VALUES
            ('usn'::app.tax_mode, 'авансовый платёж по УСН за I квартал', '2026-04-28', 14,
             'сроки УСН (MVP-справочник для демо)',
             'Переход на УСН: пошаговая инструкция',
             'kak-perejti-na-uproshchyonnuyu-sistemu-nalogooblozheniya'),
            ('usn'::app.tax_mode, 'авансовый платёж по УСН за II квартал', '2026-07-28', 14,
             'сроки УСН (MVP-справочник для демо)',
             'Переход на УСН: пошаговая инструкция',
             'kak-perejti-na-uproshchyonnuyu-sistemu-nalogooblozheniya'),
            ('patent'::app.tax_mode, 'оплата патента', '2026-12-31', 30,
             'сроки ПСН (MVP-справочник для демо)',
             'Патентная система налогообложения', 'patent')
        """
    )


def downgrade() -> None:
    op.drop_index("ix_reminders_due", table_name="reminders", schema="app")
    op.drop_table("reminders", schema="app")
    op.drop_table("tax_deadlines", schema="app")
    op.execute("DROP TYPE IF EXISTS app.reminder_status")
    op.execute("DROP TYPE IF EXISTS app.reminder_repeat")
