"""
fastfish-hot 数据库模块。

独立于 fastfish，仅管理热点相关表。
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config import get_settings


def _get_schema_path() -> Path:
    return Path(__file__).resolve().parent / "sql" / "schema.sql"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """获取数据库连接。"""
    settings = get_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_database() -> None:
    """初始化数据库，创建表。"""
    schema_path = _get_schema_path()
    if not schema_path.exists():
        raise FileNotFoundError(f"schema 不存在: {schema_path}")

    settings = get_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(settings.db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        with schema_path.open("r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()


__all__ = ["get_connection", "init_database"]
