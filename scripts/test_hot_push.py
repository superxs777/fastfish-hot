#!/usr/bin/env python
"""
热点推送功能测试脚本。
"""

import sys
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


def log(msg: str) -> None:
    print(f"  {msg}")


def main() -> int:
    print("=== 热点推送功能测试 ===\n")

    print("1. 测试 API 拉取")
    try:
        from core.fetcher import fetch_from_api, fetch_platforms
        platforms = fetch_platforms()
        if platforms:
            items = fetch_from_api("知乎")
            if items:
                log(f"[OK] 成功拉取 {len(items)} 条（知乎）")
                log(f"  示例: {items[0].get('title', '')[:40]}...")
            else:
                log("[FAIL] 拉取结果为空")
        else:
            log("[FAIL] 获取平台列表失败")
    except Exception as e:
        log(f"[FAIL] 异常: {e}")
        import traceback
        traceback.print_exc()

    print("\n2. 测试推送配置")
    try:
        from core.pusher import get_push_configs
        configs = get_push_configs()
        if configs:
            log(f"[OK] 找到 {len(configs)} 个启用配置")
        else:
            log("  提示: 无启用配置，请通过管理界面添加")
    except Exception as e:
        log(f"✗ 异常: {e}")
        import traceback
        traceback.print_exc()

    print("\n3. 测试 hot_items_raw 今日数据")
    try:
        from core.pusher import get_today_raw_items
        items = get_today_raw_items([])
        if items:
            log(f"[OK] 今日共 {len(items)} 条")
        else:
            log("  提示: 若为 0，请先执行 fetch_hot_items.py")
    except Exception as e:
        log(f"✗ 异常: {e}")
        import traceback
        traceback.print_exc()

    print("\n=== 测试完成 ===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
