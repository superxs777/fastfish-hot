#!/usr/bin/env python
"""
初始化默认拉取配置。

若 hot_fetch_config 为空，插入一条默认配置（固定时刻 7/14/18）。
"""

import sys
import time
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from dotenv import load_dotenv
    load_dotenv(_project_root / ".env")
except ImportError:
    pass

from db import get_connection


def main() -> int:
    ts = int(time.time())
    with get_connection() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM hot_fetch_config")
        if cur.fetchone()[0] > 0:
            print("hot_fetch_config 已有数据，跳过")
            return 0
        conn.execute(
            """INSERT INTO hot_fetch_config
               (name, api_base_url, platforms, schedule_type, fixed_times, interval_minutes, clear_before_fetch, is_active, create_time, update_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("default", "https://api.pearktrue.cn", "[]", "fixed", "07:00,14:00,18:00", 0, 1, 1, ts, ts),
        )
    print("已插入默认拉取配置")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
