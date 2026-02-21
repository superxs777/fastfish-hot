"""
fastfish-hot 独立配置模块。

从 .env 和环境变量读取，不依赖 fastfish。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_project_root = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(_project_root / ".env")
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    """热点推送相关配置。"""

    db_path: Path
    log_dir: Path
    api_host: str = "0.0.0.0"
    api_port: int = 8900
    api_key: str | None = None
    allow_local_no_auth: bool = True


def _int_from_env(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """读取配置并缓存。"""
    db_env = os.getenv("HOT_DB_PATH")
    if db_env:
        db_path = Path(db_env).expanduser().resolve()
    else:
        db_path = (_project_root / "data" / "fastfish_hot.db").resolve()

    log_env = os.getenv("HOT_LOG_DIR")
    if log_env:
        log_dir = Path(log_env).expanduser().resolve()
    else:
        log_dir = (db_path.parent / "logs").resolve()

    api_host = os.getenv("HOT_API_HOST", "0.0.0.0")
    api_port = _int_from_env("HOT_API_PORT", 8900)
    api_key = (os.getenv("HOT_ADMIN_API_KEY") or "").strip() or None
    allow_local = os.getenv("HOT_ALLOW_LOCAL_NO_AUTH", "true").strip().lower() in ("1", "true", "yes")

    return Settings(
        db_path=db_path,
        log_dir=log_dir,
        api_host=api_host,
        api_port=api_port,
        api_key=api_key,
        allow_local_no_auth=allow_local,
    )


__all__ = ["Settings", "get_settings"]
