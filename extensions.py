"""
Conexión a SQLite compartida por toda la app.
Mismo comportamiento que el app.py original: la ubicación de la DB se lee
de la variable de entorno CONECTO_DB en cada request (importante para los
tests, que usan una DB temporal distinta por test).
"""
import os
import sqlite3
from pathlib import Path

from flask import g

import config


def _ensure_columns(db: sqlite3.Connection) -> None:
    """Migración liviana para bases creadas con una versión anterior del schema."""
    def existing_columns(table: str) -> set[str]:
        return {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}

    task_columns = existing_columns("tasks")
    if "steps" not in task_columns:
        db.execute("ALTER TABLE tasks ADD COLUMN steps TEXT NOT NULL DEFAULT ''")
    if "file_path" not in task_columns:
        db.execute("ALTER TABLE tasks ADD COLUMN file_path TEXT")
    if "file_name" not in task_columns:
        db.execute("ALTER TABLE tasks ADD COLUMN file_name TEXT")

    message_columns = existing_columns("messages")
    if "is_read" not in message_columns:
        db.execute("ALTER TABLE messages ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0")

    account_columns = existing_columns("accounts")
    if "last_login" not in account_columns:
        db.execute("ALTER TABLE accounts ADD COLUMN last_login TEXT")
    db.commit()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(os.environ.get("CONECTO_DB", config.DEFAULT_DB_PATH))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.executescript(config.SCHEMA)
        _ensure_columns(g.db)
    return g.db


def _close_db(_error: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    return get_db().execute(sql, params).fetchall()


def execute(sql: str, params: tuple = ()) -> int:
    db = get_db()
    cursor = db.execute(sql, params)
    db.commit()
    return int(cursor.lastrowid)


def init_app(app):
    app.teardown_appcontext(_close_db)
