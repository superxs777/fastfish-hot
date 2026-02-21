# fastfish-hot 热点推送

从 fastfish 抽取的独立热点拉取与推送项目。支持灵活配置拉取 URL、定时时间、推送渠道、过滤关键词等。

## 功能

- **拉取**：从 api.pearktrue.cn 拉取热点，支持固定时刻或时间间隔
- **推送**：推送到飞书 / 钉钉 / Telegram
- **过滤**：包含/排除关键词，由 hot_push_config 管理
- **管理界面**：纯 HTML 表单，配置拉取、推送、环境变量

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 复制环境变量
copy .env.example .env
# 编辑 .env，配置 HOT_PUSH_FEISHU_WEBHOOK 或钉钉/Telegram

# 3. 初始化数据库
python scripts/init_db.py
python scripts/init_default_config.py
python scripts/init_default_push_config.py

# 4. 启动管理服务
python run.py
# 访问 http://127.0.0.1:8900/config（本地免鉴权）

# 5. 手动测试
python scripts/fetch_hot_items.py
set HOT_PUSH_FORCE=1
python scripts/push_hot_to_im.py
```

## 定时任务

Windows 任务计划程序或 Linux crontab：

```
# 拉取：7:00、14:00、18:00
0 7,14,18 * * * python d:\Python312\fastfish-hot\scripts\fetch_hot_items.py >> data\logs\hot_fetch.log 2>&1

# 推送：7:10、14:10、18:10
10 7,14,18 * * * python d:\Python312\fastfish-hot\scripts\push_hot_to_im.py >> data\logs\hot_push.log 2>&1
```

拉取/推送时间可在管理界面「拉取配置」中修改，修改后需手动更新 crontab。

## 管理界面

| 页面 | 说明 |
|------|------|
| /config | 配置状态、crontab 建议 |
| /settings | 环境变量（Webhook、API Key 等） |
| /fetch | 拉取配置 CRUD |
| /push | 推送配置 CRUD |

鉴权：配置 `HOT_ADMIN_API_KEY` 后，访问需带 `?api_key=xxx`。本地 127.0.0.1 可免鉴权。

## 项目结构

```
fastfish-hot/
├── config.py          # 配置
├── db.py              # 数据库
├── core/              # 拉取、推送、过滤逻辑
├── api/               # 管理 API 与界面
├── scripts/           # 命令行脚本
├── sql/schema.sql     # 表结构
└── run.py             # 启动管理服务
```

## 数据库表

- `hot_fetch_config`：拉取配置（URL、平台、调度类型、固定时刻/间隔）
- `hot_items_raw`：原始拉取数据
- `hot_push_config`：推送配置（关键词、渠道、时间等）
- `hot_push_history`：推送历史

## 与 fastfish 关系

完全独立运行，不依赖 fastfish。数据源暂仅支持 api.pearktrue.cn。
