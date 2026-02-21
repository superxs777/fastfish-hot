"""
热点拉取模块。

从 api.pearktrue.cn 拉取数据，支持从 hot_fetch_config 读取配置。
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import requests

from db import get_connection

logger = logging.getLogger(__name__)

_DEFAULT_API_BASE = "https://api.pearktrue.cn"
_REQUEST_TIMEOUT = 15


def _get_api_base(override: str | None = None) -> str:
    base = (override or os.getenv("HOT_API_BASE", _DEFAULT_API_BASE)).strip().rstrip("/")
    return base or _DEFAULT_API_BASE


def fetch_platforms(api_base: str | None = None) -> list[str]:
    """获取支持的平台列表（约 45 个）。"""
    base = _get_api_base(api_base)
    url = f"{base}/api/dailyhot/"
    try:
        r = requests.get(url, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        logger.warning("拉取平台列表失败: %s", e)
        return []
    except json.JSONDecodeError as e:
        logger.warning("解析平台列表 JSON 失败: %s", e)
        return []

    if data.get("code") not in (200, 0):
        return []

    data_obj = data.get("data")
    if isinstance(data_obj, dict) and "platforms" in data_obj:
        platforms = data_obj.get("platforms")
        return list(platforms) if isinstance(platforms, list) else []
    return []


def fetch_from_api(source: str, api_base: str | None = None) -> list[dict[str, Any]]:
    """拉取指定平台的热点数据。"""
    base = _get_api_base(api_base)
    url = f"{base}/api/dailyhot/"
    try:
        r = requests.get(url, params={"title": source}, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        logger.warning("拉取热点失败 source=%s: %s", source, e)
        return []
    except json.JSONDecodeError as e:
        logger.warning("解析热点 JSON 失败 source=%s: %s", source, e)
        return []

    code = data.get("code")
    if code not in (200, 0):
        logger.warning("热点 API 返回异常 source=%s code=%s", source, code)
        return []

    items = data.get("data")
    if not isinstance(items, list):
        return []

    result = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("name") or ""
        link = item.get("mobileUrl") or item.get("url") or item.get("link") or ""
        desc = item.get("desc") or ""
        hot = str(item.get("hot", "")) if item.get("hot") is not None else ""
        if title:
            result.append({
                "title": title,
                "link": link,
                "desc": desc,
                "hot": hot,
                "rank": i + 1,
            })
    return result


def get_fetch_configs() -> list[dict[str, Any]]:
    """获取所有启用的拉取配置。"""
    with get_connection() as conn:
        cur = conn.execute(
            """SELECT id, name, api_base_url, platforms, schedule_type,
                      fixed_times, interval_minutes, clear_before_fetch
               FROM hot_fetch_config WHERE is_active = 1"""
        )
        rows = cur.fetchall()
    configs = []
    for row in rows:
        configs.append({
            "id": row[0],
            "name": row[1],
            "api_base_url": (row[2] or "").strip() or _DEFAULT_API_BASE,
            "platforms": json.loads(row[3]) if row[3] else [],
            "schedule_type": row[4] or "fixed",
            "fixed_times": (row[5] or "").strip(),
            "interval_minutes": row[6] or 0,
            "clear_before_fetch": bool(row[7]),
        })
    return configs


def delete_all_raw_items() -> int:
    """清空 hot_items_raw 表。"""
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM hot_items_raw")
        return cur.rowcount


def save_raw_items(source: str, items: list[dict], fetched_at: int) -> int:
    """将拉取的热点写入 hot_items_raw 表。"""
    ts = int(time.time())
    count = 0
    with get_connection() as conn:
        for item in items:
            conn.execute(
                """INSERT INTO hot_items_raw
                   (source, title, link, desc_text, hot, rank, fetched_at, create_time)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    source,
                    item.get("title", ""),
                    item.get("link", ""),
                    item.get("desc", ""),
                    item.get("hot", ""),
                    item.get("rank", 0),
                    fetched_at,
                    ts,
                ),
            )
            count += 1
    return count
