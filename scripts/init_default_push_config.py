#!/usr/bin/env python
"""
初始化默认推送配置。

若 hot_push_config 为空，插入一条情感类配置。
支持 --channel feishu|dingtalk|telegram 指定推送渠道，默认 feishu。
Webhook/Token 从 .env 读取，不存数据库；webhook_url 留空即可。
"""

import argparse
import json
import os
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

INC = ["情感", "恋爱", "婚姻", "家庭", "爱情", "分手", "相亲", "婆媳", "亲子", "女性", "男女", "两性", "结婚", "离婚", "单身", "亲密关系", "恋爱观", "婚姻观", "恋爱脑", "原生家庭", "治愈", "情绪", "心情", "共鸣"]
EXC = ["政治", "时政", "军事"]


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化默认推送配置")
    parser.add_argument(
        "--channel",
        choices=["feishu", "dingtalk", "telegram"],
        default="feishu",
        help="推送渠道，默认 feishu",
    )
    args = parser.parse_args()
    im_channel = args.channel

    with get_connection() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM hot_push_config")
        if cur.fetchone()[0] > 0:
            print("hot_push_config 已有数据，跳过")
            return 0

        ts = int(time.time())
        conn.execute(
            """INSERT INTO hot_push_config
               (category_code, category_name, sources, include_keywords, exclude_keywords,
                push_time, im_channel, webhook_url, max_items, output_format, is_active, create_time, update_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "emotion",
                "情感类",
                "[]",
                json.dumps(INC, ensure_ascii=False),
                json.dumps(EXC, ensure_ascii=False),
                "07:10,14:10,18:10",
                im_channel,
                "",
                30,
                "text",
                1,
                ts,
                ts,
            ),
        )
    ch_hint = {
        "feishu": "HOT_PUSH_FEISHU_WEBHOOK",
        "dingtalk": "HOT_PUSH_DINGTALK_WEBHOOK（加签需 HOT_PUSH_DINGTALK_SECRET）",
        "telegram": "HOT_PUSH_TELEGRAM_BOT_TOKEN + HOT_PUSH_TELEGRAM_CHAT_ID",
    }
    print(f"已插入默认推送配置（情感类，渠道 {im_channel}）。请在 .env 配置 {ch_hint[im_channel]}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
