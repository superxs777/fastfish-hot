"""
热点推送模块。

推送到飞书/钉钉/Telegram，Webhook/Token 从 .env 读取。
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

from db import get_connection


def get_push_configs() -> list[dict[str, Any]]:
    """获取所有启用的推送配置。"""
    with get_connection() as conn:
        cur = conn.execute(
            """SELECT id, category_code, category_name, sources, include_keywords,
                      exclude_keywords, push_time, im_channel, webhook_url, max_items, output_format
               FROM hot_push_config WHERE is_active = 1"""
        )
        rows = cur.fetchall()
    configs = []
    for row in rows:
        configs.append({
            "id": row[0],
            "category_code": row[1],
            "category_name": row[2],
            "sources": json.loads(row[3]) if row[3] else [],
            "include_keywords": json.loads(row[4]) if row[4] else [],
            "exclude_keywords": json.loads(row[5]) if row[5] else [],
            "push_time": row[6],
            "im_channel": row[7],
            "webhook_url": row[8],
            "max_items": row[9] or 10,
            "output_format": row[10] or "text",
        })
    return configs


def get_today_raw_items(sources: list[str]) -> list[dict]:
    """获取今日拉取的 raw 数据。sources 为空时取全部平台。"""
    ts = int(time.time())
    today_start = ts - (ts % 86400) - 8 * 3600
    today_end = today_start + 86400

    if sources:
        placeholders = ",".join("?" * len(sources))
        source_clause = f"source IN ({placeholders})"
        params = list(sources) + [today_start, today_end]
    else:
        source_clause = "1=1"
        params = [today_start, today_end]

    with get_connection() as conn:
        cur = conn.execute(
            f"""SELECT id, source, title, link, desc_text, hot, rank
                FROM hot_items_raw
                WHERE {source_clause}
                  AND fetched_at >= ? AND fetched_at < ?
                ORDER BY source, rank""",
            params,
        )
        rows = cur.fetchall()

    items = []
    for row in rows:
        items.append({
            "id": row[0],
            "source": row[1],
            "title": row[2],
            "link": row[3],
            "desc": row[4] or "",
            "hot": row[5] or "",
            "rank": row[6] or 0,
        })
    return items


def format_push_message(items: list[dict], category_name: str) -> str:
    """格式化推送消息文本。"""
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    lines = [f"【{category_name}】今日热点 {date_str}", ""]
    for i, item in enumerate(items[:20], 1):
        title = (item.get("title") or "").strip()
        link = (item.get("link") or "").strip()
        source = item.get("source", "")
        if title:
            lines.append(f"{i}. [{source}] {title}")
            if link:
                lines.append(f"   {link}")
            lines.append("")
    return "\n".join(lines).strip()


def push_to_feishu(webhook_url: str, content: str) -> tuple[bool, str]:
    """推送到飞书 Webhook。"""
    if not webhook_url or not webhook_url.strip():
        return False, "webhook_url 为空"
    try:
        r = requests.post(
            webhook_url.strip(),
            json={"msg_type": "text", "content": {"text": content}},
            timeout=10,
        )
        resp = r.json()
        if resp.get("code") != 0 and resp.get("StatusCode") != 0:
            return False, resp.get("msg", resp.get("message", str(resp)))
        return True, ""
    except requests.RequestException as e:
        return False, str(e)
    except json.JSONDecodeError:
        return False, "响应非 JSON"


def push_to_dingtalk(webhook_url: str, content: str) -> tuple[bool, str]:
    """推送到钉钉 Webhook。"""
    if not webhook_url or not webhook_url.strip():
        return False, "webhook_url 为空"
    try:
        r = requests.post(
            webhook_url.strip(),
            json={"msgtype": "text", "text": {"content": content}},
            timeout=10,
        )
        resp = r.json()
        if resp.get("errcode") != 0:
            return False, resp.get("errmsg", str(resp))
        return True, ""
    except requests.RequestException as e:
        return False, str(e)
    except json.JSONDecodeError:
        return False, "响应非 JSON"


def push_to_telegram(bot_token: str, chat_id: str, content: str) -> tuple[bool, str]:
    """推送到 Telegram Bot API。"""
    if not bot_token or not bot_token.strip():
        return False, "HOT_PUSH_TELEGRAM_BOT_TOKEN 未配置"
    if not chat_id or not chat_id.strip():
        return False, "chat_id 为空"
    url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
    try:
        r = requests.post(
            url,
            json={"chat_id": chat_id.strip(), "text": content},
            timeout=10,
        )
        resp = r.json()
        if not resp.get("ok"):
            return False, resp.get("description", str(resp))
        return True, ""
    except requests.RequestException as e:
        return False, str(e)
    except json.JSONDecodeError:
        return False, "响应非 JSON"


def push_to_im(im_channel: str, webhook_url: str, content: str) -> tuple[bool, str]:
    """根据 im_channel 选择推送方式。telegram 时 webhook_url 存 chat_id。"""
    ch = (im_channel or "").lower()
    if ch == "feishu":
        return push_to_feishu(webhook_url, content)
    if ch == "dingtalk":
        return push_to_dingtalk(webhook_url, content)
    if ch == "telegram":
        token = os.getenv("HOT_PUSH_TELEGRAM_BOT_TOKEN", "").strip()
        return push_to_telegram(token, webhook_url, content)
    return False, f"不支持的 im_channel: {im_channel}"


def already_pushed_today(config_id: int) -> bool:
    """检查该 config 今日是否已推送。"""
    ts = int(time.time())
    today_start = ts - (ts % 86400) - 8 * 3600
    today_end = today_start + 86400
    with get_connection() as conn:
        cur = conn.execute(
            """SELECT 1 FROM hot_push_history
               WHERE config_id = ? AND pushed_at >= ? AND pushed_at < ? AND status = 1
               LIMIT 1""",
            (config_id, today_start, today_end),
        )
        return cur.fetchone() is not None


def already_pushed_in_window(config_id: int, window_hours: int = 2) -> bool:
    """检查该 config 在本窗口内是否已推送。"""
    now = time.localtime()
    y, m, d, hour = now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour
    window_hour = (hour // window_hours) * window_hours
    window_start = int(time.mktime((y, m, d, window_hour, 0, 0, 0, 0, 0)))
    window_end = window_start + window_hours * 3600
    with get_connection() as conn:
        cur = conn.execute(
            """SELECT 1 FROM hot_push_history
               WHERE config_id = ? AND pushed_at >= ? AND pushed_at < ? AND status = 1
               LIMIT 1""",
            (config_id, window_start, window_end),
        )
        return cur.fetchone() is not None


def record_push_history(
    config_id: int,
    item_ids: list[int],
    status: int,
    error_msg: str | None = None,
) -> None:
    """记录推送历史。"""
    ts = int(time.time())
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO hot_push_history
               (config_id, pushed_at, items_count, item_ids, status, error_msg, create_time)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (config_id, ts, len(item_ids), json.dumps(item_ids), status, error_msg, ts),
        )
