#!/usr/bin/env python
"""
热点拉取脚本。

从 hot_fetch_config 读取启用的配置，按配置拉取并写入 hot_items_raw。
若无拉取配置，则使用默认 api.pearktrue.cn 拉取全部平台。
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

from core.fetcher import (
    delete_all_raw_items,
    fetch_from_api,
    fetch_platforms,
    get_fetch_configs,
    save_raw_items,
)


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def main() -> int:
    log("=== 开始拉取热点 ===")
    configs = get_fetch_configs()

    if not configs:
        api_base = "https://api.pearktrue.cn"
        platforms = fetch_platforms(api_base)
        if not platforms:
            log("获取平台列表失败，跳过拉取")
            return 0
        cfg = {
            "name": "default",
            "api_base_url": api_base,
            "platforms": [],
            "clear_before_fetch": True,
        }
    else:
        cfg = configs[0]

    api_base = cfg.get("api_base_url", "https://api.pearktrue.cn")
    platforms = cfg.get("platforms") or []
    clear_before = cfg.get("clear_before_fetch", True)

    if not platforms:
        platforms = fetch_platforms(api_base)
    if not platforms:
        log("获取平台列表失败")
        return 0

    if clear_before:
        deleted = delete_all_raw_items()
        if deleted:
            log(f"清空旧数据 {deleted} 条")

    fetched_at = int(time.time())
    total = 0
    for source in sorted(platforms):
        items = fetch_from_api(source, api_base)
        if items:
            n = save_raw_items(source, items, fetched_at)
            total += n
            log(f"  {source}: 写入 {n} 条")
        else:
            log(f"  {source}: 无数据或拉取失败")

    log(f"=== 拉取完成，共 {total} 条（{len(platforms)} 个平台）===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
