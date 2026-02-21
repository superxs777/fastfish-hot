#!/bin/bash
# fastfish-hot 定时任务安装脚本
# 从 DB 读取拉取配置生成 crontab 建议，用户手动添加

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 确保使用项目 Python
if [ -x "$PROJECT_ROOT/venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/venv/bin/python"
else
    PYTHON="${PYTHON:-python}"
fi

LOGS_DIR="${PROJECT_ROOT}/data/logs"
mkdir -p "$LOGS_DIR"

echo "=== fastfish-hot 定时任务 ==="
echo "项目路径: $PROJECT_ROOT"
echo "Python: $PYTHON"
echo "日志: $LOGS_DIR"
echo ""
echo "请将以下行添加到 crontab (crontab -e)："
echo ""
echo "TZ=Asia/Shanghai"
echo "0 7,14,18 * * * $PYTHON $PROJECT_ROOT/scripts/fetch_hot_items.py >> $LOGS_DIR/hot_fetch.log 2>&1"
echo "10 7,14,18 * * * $PYTHON $PROJECT_ROOT/scripts/push_hot_to_im.py >> $LOGS_DIR/hot_push.log 2>&1"
echo ""
echo "拉取/推送时间可在管理界面修改，修改后需手动更新 crontab。"
