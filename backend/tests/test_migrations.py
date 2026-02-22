from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect


def _run_alembic_upgrade(sqlalchemy_url: str) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    script = (
        "from pathlib import Path\n"
        "from alembic import command\n"
        "from alembic.config import Config\n"
        "backend_dir = Path('.').resolve()\n"
        "cfg = Config(str(backend_dir / 'alembic.ini'))\n"
        "cfg.set_main_option('script_location', str(backend_dir / 'alembic'))\n"
        f"cfg.set_main_option('sqlalchemy.url', {sqlalchemy_url!r})\n"
        "command.upgrade(cfg, 'head')\n"
    )
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend_dir,
        check=True,
        timeout=20,
        env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
    )


def test_alembic_upgrade_applies_schema_to_clean_sqlite_db(tmp_path: Path) -> None:
    db_path = tmp_path / "alembic_test.db"
    _run_alembic_upgrade(f"sqlite:///{db_path}")

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)

    assert set(inspector.get_table_names()) >= {
        "alembic_version",
        "organizations",
        "users",
        "tasks",
    }

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    task_columns = {column["name"] for column in inspector.get_columns("tasks")}
    assert {"id", "org_id", "email", "status", "created_at"} <= user_columns
    assert {"id", "org_id", "status", "assignee_user_id", "created_at"} <= task_columns


def test_migration_creates_required_indexes_and_unique_constraints(tmp_path: Path) -> None:
    db_path = tmp_path / "alembic_indexes.db"
    _run_alembic_upgrade(f"sqlite:///{db_path}")

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)

    user_indexes = {index["name"] for index in inspector.get_indexes("users")}
    task_indexes = {index["name"] for index in inspector.get_indexes("tasks")}
    user_uniques = {constraint["name"] for constraint in inspector.get_unique_constraints("users")}

    assert "ix_users_org_id_created_at" in user_indexes
    assert "ix_users_status" in user_indexes
    assert "uq_users_org_id_email" in user_uniques
    assert "ix_tasks_org_id_created_at" in task_indexes
    assert "ix_tasks_status" in task_indexes
    assert "ix_tasks_assignee_user_id" in task_indexes
