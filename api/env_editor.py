""".env 可编辑配置，仅 HOT_* 变量。"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

EDITABLE_ENV_SPEC: list[dict[str, Any]] = [
    {"key": "HOT_ADMIN_API_KEY", "label": "管理界面 API Key", "type": "password", "placeholder": "鉴权用", "section": "管理"},
    {"key": "HOT_API_HOST", "label": "API 监听地址", "type": "text", "placeholder": "0.0.0.0", "section": "管理"},
    {"key": "HOT_API_PORT", "label": "API 端口", "type": "text", "placeholder": "8900", "section": "管理"},
    {"key": "HOT_DB_PATH", "label": "数据库路径", "type": "text", "placeholder": "默认 data/fastfish_hot.db", "section": "路径"},
    {"key": "HOT_LOG_DIR", "label": "日志目录", "type": "text", "placeholder": "默认 data/logs", "section": "路径"},
    {"key": "HOT_API_BASE", "label": "热点 API 基础地址", "type": "text", "placeholder": "https://api.pearktrue.cn", "section": "数据源"},
    {"key": "HOT_PUSH_FEISHU_WEBHOOK", "label": "飞书 Webhook", "type": "text", "placeholder": "https://open.feishu.cn/...", "section": "推送"},
    {"key": "HOT_PUSH_DINGTALK_WEBHOOK", "label": "钉钉 Webhook", "type": "text", "placeholder": "https://oapi.dingtalk.com/...", "section": "推送"},
    {"key": "HOT_PUSH_TELEGRAM_BOT_TOKEN", "label": "Telegram Bot Token", "type": "password", "placeholder": "可选", "section": "推送"},
    {"key": "HOT_PUSH_TELEGRAM_CHAT_ID", "label": "Telegram Chat ID", "type": "text", "placeholder": "可选", "section": "推送"},
]


def _parse_env_file(env_path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not env_path.exists():
        return result
    try:
        content = env_path.read_text(encoding="utf-8")
    except OSError:
        return result
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1].replace('\\"', '"')
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1].replace("\\'", "'")
            result[key] = val
    return result


def _escape_env_value(val: str) -> str:
    if not val:
        return ""
    if any(c in val for c in " \t\n\"'#="):
        return '"' + val.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return val


def load_env_editable(project_root: Path) -> dict[str, Any]:
    env_path = project_root / ".env"
    parsed = _parse_env_file(env_path)
    result: dict[str, Any] = {}
    for spec in EDITABLE_ENV_SPEC:
        key = spec["key"]
        env_val = os.getenv(key)
        file_val = parsed.get(key, "")
        if env_val is not None and str(env_val).strip():
            result[key] = str(env_val).strip()
        else:
            result[key] = file_val if isinstance(file_val, str) else ""
        if spec.get("type") == "bool":
            result[key] = str(result[key]).lower() in ("1", "true", "yes", "on")
    return result


def save_env_editable(project_root: Path, data: dict[str, Any]) -> tuple[bool, str]:
    env_path = project_root / ".env"
    parsed = _parse_env_file(env_path)
    keys_to_update = {s["key"] for s in EDITABLE_ENV_SPEC}

    for spec in EDITABLE_ENV_SPEC:
        key = spec["key"]
        val = data.get(key)
        if spec.get("type") == "bool":
            parsed[key] = "true" if val else "false"
        else:
            parsed[key] = str(val).strip() if val is not None else ""

    lines_out: list[str] = []
    seen_keys: set[str] = set()
    if env_path.exists():
        try:
            content = env_path.read_text(encoding="utf-8")
        except OSError as e:
            return False, str(e)
        for line in content.splitlines(keepends=True):
            if not line.strip() or line.strip().startswith("#"):
                lines_out.append(line)
                continue
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=.*$", line.strip())
            if m:
                k = m.group(1)
                seen_keys.add(k)
                if k in keys_to_update:
                    lines_out.append(f"{k}={_escape_env_value(parsed.get(k, ''))}\n")
                else:
                    lines_out.append(line)
                continue
            lines_out.append(line)

    for spec in EDITABLE_ENV_SPEC:
        key = spec["key"]
        if key not in seen_keys:
            lines_out.append(f"{key}={_escape_env_value(parsed.get(key, ''))}\n")

    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text("".join(lines_out), encoding="utf-8")
    except OSError as e:
        return False, str(e)
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)
    except ImportError:
        pass
    return True, ""
