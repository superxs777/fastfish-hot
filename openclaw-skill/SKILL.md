---
name: fastfish-hot
description: "热点推送独立项目。从 api.pearktrue.cn 拉取热点，支持飞书/钉钉/Telegram 推送。可配置拉取时间、推送时间、过滤关键词。通过 system.run 直接调用脚本，无需 MCP。当用户需要拉取热点、知乎热搜、配置热点推送或设置定时推送时使用本技能。"
metadata:
  {
    "openclaw":
      {
        "requires": { "bins": ["python3"] }
      }
  }
---

# fastfish-hot 能力说明

**GitHub**：https://github.com/superxs777/fastfish-hot

本 Skill 需配合 fastfish-hot 项目使用。请先安装 fastfish-hot，再在 OpenClaw 中启用本 Skill。

## 安装 fastfish-hot（首次使用必读）

1. 克隆仓库：`git clone https://github.com/superxs777/fastfish-hot.git`
2. 进入目录：`cd fastfish-hot`
3. 安装依赖：`pip install -r requirements.txt`
4. 配置：`copy .env.example .env`，填写 Webhook 等
5. 初始化：`python scripts/init_db.py`，`python scripts/init_default_config.py`，`python scripts/init_default_push_config.py`
6. 可选：`python run.py` 启动管理界面（http://127.0.0.1:8900）

详细说明见 GitHub README。

## 前置要求

1. **fastfish-hot 已安装**：按上方步骤完成部署
2. **Python 3.10+**
3. **命令路径**：`{baseDir}` 为 fastfish-hot 的 openclaw-skill 目录，脚本路径为 `{baseDir}/../scripts/`
4. **若 baseDir 无法替换**：使用绝对路径，如 `python /opt/fastfish-hot/scripts/get_hot_now.py`

## 使用方式

**必须使用 `system.run` 执行脚本命令，不要使用 MCP 方式。**

## ⚠️ 定时任务：严禁擅改（阻断式规则）

**在未得到用户明确要求时，严禁修改、删除或编辑已有 OpenClaw 定时任务。**

- **禁止**：在定时任务出错、报错或用户未明确要求时，执行 `openclaw cron edit`、`openclaw cron rm`、`openclaw cron update`
- **允许**：用户明确说「修改」「删除」「调整」「取消」定时任务时，方可执行上述操作
- **允许**：用户要求「添加」「创建」定时任务时，执行 `openclaw cron add`
- **出错时**：仅报告问题并给出建议，不得主动修改配置

**违反此条属于严重错误。**

## 可用能力

### 1. 实时拉取热点

用户说「拉取热点」「实时热点」「知乎热搜」等时，执行：

```bash
# 列出支持的平台
python {baseDir}/../scripts/get_hot_now.py --list-platforms

# 按平台拉取（逗号分隔）
python {baseDir}/../scripts/get_hot_now.py --source 知乎
python {baseDir}/../scripts/get_hot_now.py --source 知乎,百度,今日头条

# 按类别拉取（使用 hot_push_config 的 sources 和关键词过滤）
python {baseDir}/../scripts/get_hot_now.py --category emotion

# 从数据库读取（需先执行 fetch_hot_items.py，秒级完成，适合 OpenClaw Cron）
python {baseDir}/../scripts/get_hot_now.py --category emotion --from-db

# 输出 JSON
python {baseDir}/../scripts/get_hot_now.py --source 知乎 --format json

# 拉取并写入数据库（补录）
python {baseDir}/../scripts/get_hot_now.py --source 知乎 --save
```

参数：`--source` 平台名逗号分隔；`--category` 类别 code 如 emotion；`--format` text/json；`--save` 写入 hot_items_raw；`--limit` 每平台条数默认 20；`--from-db` 从数据库读取。

### 2. 定时更新（拉取 + 推送）

**职责分工（重要）**：
- **拉取**：仅由**系统 crontab** 执行 `fetch_hot_items.py`，将数据写入数据库
- **推送**：OpenClaw Cron 仅执行 `get_hot_now.py --from-db` 或 `push_hot_to_im.py`
- **禁止**：不要在 OpenClaw 中创建或执行拉取任务（`fetch_hot_items.py`），拉取由系统 crontab 完成

**方式一：系统 crontab / Windows 计划任务**（飞书/钉钉/Telegram）

- 拉取：7:00、14:00、18:00 执行 `python scripts/fetch_hot_items.py`
- 推送：7:10、14:10、18:10 执行 `python scripts/push_hot_to_im.py`（.env 配置 Webhook）

**方式二：OpenClaw Cron**

飞书/钉钉/Telegram（通过脚本推送到 Webhook）：
```bash
openclaw cron add --name "每日热点" --cron "0 8 * * *" --tz "Asia/Shanghai" --session isolated --message "cd /opt/fastfish-hot && python scripts/push_hot_to_im.py，将热点推送到配置的渠道"
```

Telegram（OpenClaw 已配置 Telegram 渠道，announce 直接推送）：
```bash
# 拉取由系统 crontab 完成，OpenClaw 仅负责推送。该任务只执行 get_hot_now.py --from-db。
openclaw cron add --name "每日热点" --cron "10 7,14,18 * * *" --tz "Asia/Shanghai" --session isolated --message "cd /opt/fastfish-hot && python scripts/get_hot_now.py --category emotion --from-db，将输出作为今日热点简报发送" --channel telegram --to "你的ChatID"
```

立即测试：创建后执行 `openclaw cron run <job-id> --force` 可立即运行一次。

### 3. 配置管理

- **拉取/推送配置**：访问管理界面 http://127.0.0.1:8900（需先 `python run.py`）
- **环境变量**：在 .env 中配置 HOT_PUSH_FEISHU_WEBHOOK、HOT_PUSH_DINGTALK_WEBHOOK、HOT_PUSH_TELEGRAM_BOT_TOKEN、HOT_PUSH_TELEGRAM_CHAT_ID

## 使用示例

- "拉取热点" / "知乎热搜" / "实时热点"
  ```bash
  python {baseDir}/../scripts/get_hot_now.py --source 知乎
  # 或按类别：python {baseDir}/../scripts/get_hot_now.py --category emotion
  ```

- "如何设置每日热点推送"
  1. 执行 `python scripts/init_default_config.py` 和 `python scripts/init_default_push_config.py` 初始化配置
  2. 在 .env 中配置 Webhook 或 Telegram Token+ChatID
  3. 系统 crontab 配置 `fetch_hot_items.py` 拉取（7:00、14:00、18:00）
  4. 创建 OpenClaw Cron 推送任务（见上方示例）

**注意**：若 `{baseDir}` 无法正确替换，请使用绝对路径 `/opt/fastfish-hot/scripts/get_hot_now.py`。

## ClawHub 安装

计划支持 `clawhub install fastfish-hot`，届时可一键安装本 Skill。
