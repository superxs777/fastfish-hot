#!/usr/bin/env python
"""
初始化数据库。

创建热点相关表，若表已存在则跳过。
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

from db import init_database


def main() -> int:
    init_database()
    print("数据库初始化完成")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
