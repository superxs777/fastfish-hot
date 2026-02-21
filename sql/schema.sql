-- fastfish-hot 数据库 schema
-- SQLite

PRAGMA foreign_keys = OFF;

-- 1. 拉取配置（支持多条，预留扩展）
CREATE TABLE IF NOT EXISTS hot_fetch_config (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    api_base_url         TEXT NOT NULL DEFAULT 'https://api.pearktrue.cn',
    platforms           TEXT NOT NULL,
    schedule_type       TEXT NOT NULL DEFAULT 'fixed',
    fixed_times         TEXT,
    interval_minutes    INTEGER DEFAULT 0,
    clear_before_fetch  INTEGER DEFAULT 1,
    is_active           INTEGER DEFAULT 1,
    create_time         INTEGER,
    update_time         INTEGER
);

-- 2. 原始拉取数据
CREATE TABLE IF NOT EXISTS hot_items_raw (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    title           TEXT,
    link            TEXT,
    desc_text       TEXT,
    hot             TEXT,
    rank            INTEGER DEFAULT 0,
    fetched_at      INTEGER NOT NULL,
    create_time     INTEGER
);
CREATE INDEX IF NOT EXISTS idx_hot_items_raw_source_fetched
    ON hot_items_raw(source, fetched_at);

-- 3. 推送配置（关键词存 DB，不依赖 JSON 文件）
CREATE TABLE IF NOT EXISTS hot_push_config (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    category_code       TEXT NOT NULL,
    category_name       TEXT NOT NULL,
    sources             TEXT NOT NULL,
    include_keywords    TEXT,
    exclude_keywords    TEXT,
    push_time           TEXT NOT NULL,
    im_channel          TEXT NOT NULL,
    webhook_url         TEXT NOT NULL,
    max_items           INTEGER DEFAULT 10,
    output_format       TEXT DEFAULT 'text',
    is_active           INTEGER DEFAULT 1,
    create_time         INTEGER,
    update_time         INTEGER
);

-- 4. 推送历史
CREATE TABLE IF NOT EXISTS hot_push_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id       INTEGER NOT NULL,
    pushed_at       INTEGER NOT NULL,
    items_count     INTEGER DEFAULT 0,
    item_ids        TEXT,
    status          INTEGER NOT NULL DEFAULT 0,
    error_msg       TEXT,
    create_time     INTEGER,
    FOREIGN KEY (config_id) REFERENCES hot_push_config(id)
);
CREATE INDEX IF NOT EXISTS idx_hot_push_history_config_pushed
    ON hot_push_history(config_id, pushed_at);

PRAGMA foreign_keys = ON;
