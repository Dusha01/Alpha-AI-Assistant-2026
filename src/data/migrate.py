from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def run_migrations(database_url: str) -> None:
    if not database_url.strip():
        raise ValueError("DATABASE_URL не задан")

    config = Config()
    config.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parent / "migrations"),
    )
    config.attributes["sqlalchemy_url"] = database_url
    command.upgrade(config, "head")
