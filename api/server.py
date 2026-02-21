"""
fastfish-hot 管理 API 与界面。

提供拉取配置、推送配置、环境变量的 CRUD 及 HTML 表单界面。
"""

from __future__ import annotations

import html
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from api.auth import require_auth
from api.env_editor import EDITABLE_ENV_SPEC, load_env_editable, save_env_editable
from config import get_settings
from db import get_connection

_project_root = Path(__file__).resolve().parent.parent
app = FastAPI(title="fastfish-hot")


def _auth_suffix(api_key: str | None) -> str:
    return f"?api_key={quote(api_key or '', safe='')}" if api_key else ""


def _cron_from_fetch_config(cfg: dict) -> str:
    """根据拉取配置生成 crontab 表达式。"""
    st = cfg.get("schedule_type") or "fixed"
    if st == "interval":
        mins = cfg.get("interval_minutes") or 60
        if mins >= 60 and mins % 60 == 0:
            h = mins // 60
            return f"0 */{h} * * *"
        return f"*/{mins} * * * *"
    times = (cfg.get("fixed_times") or "").strip()
    if not times:
        return "0 7,14,18 * * *"
    parts = []
    for t in times.split(","):
        t = t.strip()
        if ":" in t:
            h, m = t.split(":", 1)
            try:
                parts.append((int(h), int(m)))
            except ValueError:
                pass
    if not parts:
        return "0 7,14,18 * * *"
    minutes = sorted(set(p[1] for p in parts))
    hours = sorted(set(p[0] for p in parts))
    return f"{minutes[0] if len(minutes) == 1 else f'{minutes[0]}-{minutes[-1]}'} {','.join(str(h) for h in hours)} * * *"


# ---------- 配置状态 ----------
@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return HTMLResponse(f'<html><head><meta charset="utf-8"></head><body>'
        f'<p><a href="/config{_auth_suffix(request.query_params.get("api_key"))}">配置状态</a></p>'
        f'<p><a href="/settings{_auth_suffix(request.query_params.get("api_key"))}">设置</a></p>'
        f'<p><a href="/fetch{_auth_suffix(request.query_params.get("api_key"))}">拉取配置</a></p>'
        f'<p><a href="/push{_auth_suffix(request.query_params.get("api_key"))}">推送配置</a></p>'
        f'</body></html>')


@app.get("/config", response_class=HTMLResponse)
def config_page(request: Request, _: None = Depends(require_auth)) -> HTMLResponse:
    """配置状态页。"""
    api_key = request.query_params.get("api_key")
    auth = _auth_suffix(api_key)
    settings = get_settings()

    fetch_count = push_count = raw_count = 0
    try:
        with get_connection() as conn:
            fetch_count = conn.execute("SELECT COUNT(*) FROM hot_fetch_config WHERE is_active = 1").fetchone()[0]
            push_count = conn.execute("SELECT COUNT(*) FROM hot_push_config WHERE is_active = 1").fetchone()[0]
            ts = int(time.time())
            today_start = ts - (ts % 86400) - 8 * 3600
            today_end = today_start + 86400
            raw_count = conn.execute(
                "SELECT COUNT(*) FROM hot_items_raw WHERE fetched_at >= ? AND fetched_at < ?",
                (today_start, today_end),
            ).fetchone()[0]
    except Exception:
        pass

    cron_hint = ""
    try:
        configs = __import__("core.fetcher", fromlist=["get_fetch_configs"]).get_fetch_configs()
        if configs:
            cron_hint = _cron_from_fetch_config(configs[0])
        else:
            cron_hint = "0 7,14,18 * * *"
    except Exception:
        cron_hint = "0 7,14,18 * * *"

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>fastfish-hot 配置</title>
<style>body{{font-family:sans-serif;max-width:720px;margin:24px auto;padding:0 16px;}}
table{{border-collapse:collapse;width:100%;}} td{{padding:8px;border:1px solid #ddd;}}
a{{color:#06c;}}</style></head><body>
<h1>fastfish-hot 配置状态</h1>
<p><a href="/settings{auth}">设置</a> | <a href="/fetch{auth}">拉取配置</a> | <a href="/push{auth}">推送配置</a></p>
<table><tr><td>拉取配置(启用)</td><td>{fetch_count}</td></tr>
<tr><td>推送配置(启用)</td><td>{push_count}</td></tr>
<tr><td>今日拉取条数</td><td>{raw_count}</td></tr>
<tr><td>数据库</td><td>{settings.db_path}</td></tr>
<tr><td>拉取 crontab 建议</td><td><code>{html.escape(cron_hint)}</code> python scripts/fetch_hot_items.py</td></tr>
<tr><td>推送 crontab 建议</td><td><code>10 7,14,18 * * *</code> python scripts/push_hot_to_im.py</td></tr>
</table></body></html>"""
    return HTMLResponse(html_content)


# ---------- 设置页（环境变量）----------
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, _: None = Depends(require_auth)) -> HTMLResponse:
    api_key = request.query_params.get("api_key")
    auth = _auth_suffix(api_key)
    data = load_env_editable(_project_root)
    parts = []
    current_section = ""
    for spec in EDITABLE_ENV_SPEC:
        sec = spec.get("section", "")
        if sec != current_section:
            current_section = sec
            parts.append(f'<h2 style="font-size:1rem;margin-top:20px;">{html.escape(sec)}</h2>')
        key = spec["key"]
        label = spec.get("label", key)
        val = data.get(key, "")
        safe_val = html.escape(str(val))
        ph = html.escape(spec.get("placeholder", ""))
        if spec.get("type") == "password":
            parts.append(f'<label>{label}</label><input type="password" data-key="{html.escape(key)}" value="{safe_val}" placeholder="{ph}">')
        else:
            parts.append(f'<label>{label}</label><input type="text" data-key="{html.escape(key)}" value="{safe_val}" placeholder="{ph}">')
    form_html = "\n".join(parts)

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>设置</title>
<style>body{{font-family:sans-serif;max-width:720px;margin:24px auto;padding:0 16px;}}
label{{display:block;margin-top:12px;font-weight:500;}} input{{width:100%;padding:8px;box-sizing:border-box;}}
button{{margin-top:16px;padding:8px 16px;}} a{{color:#06c;}}</style></head><body>
<h1>设置</h1><p><a href="/config{auth}">返回配置</a></p>
<form id="f"><input type="hidden" name="api_key" value="{html.escape(api_key or '')}">
{form_html}
<button type="submit">保存</button></form>
<script>
document.getElementById("f").onsubmit=function(e){{e.preventDefault();
const d={{}}; this.querySelectorAll('[data-key]').forEach(function(el){{d[el.getAttribute("data-key")]=el.value;}});
fetch("/api/settings{auth}",{{method:"PUT",headers:{{"Content-Type":"application/json"}},body:JSON.stringify(d)}})
.then(r=>r.json()).then(d=>{{alert(d.ok?"保存成功":d.detail);if(d.ok)location.reload();}});
}};
</script></body></html>"""
    return HTMLResponse(html_content)


@app.put("/api/settings")
def api_settings_put(body: dict[str, Any], _: None = Depends(require_auth)) -> dict:
    ok, err = save_env_editable(_project_root, body)
    if not ok:
        raise HTTPException(status_code=500, detail=err)
    return {"ok": True}


# ---------- 拉取配置 CRUD ----------
@app.get("/fetch", response_class=HTMLResponse)
def fetch_config_page(request: Request, _: None = Depends(require_auth)) -> HTMLResponse:
    api_key = request.query_params.get("api_key")
    auth = _auth_suffix(api_key)
    rows = []
    with get_connection() as conn:
        for row in conn.execute("SELECT id,name,api_base_url,schedule_type,fixed_times,interval_minutes,platforms FROM hot_fetch_config ORDER BY id").fetchall():
            platforms = row[6] or "[]"
            try:
                pl = json.loads(platforms)
                pl_str = ",".join(pl[:5]) + ("..." if len(pl) > 5 else "")
            except Exception:
                pl_str = "全部"
            rows.append(f'<tr><td>{row[0]}</td><td>{html.escape(row[1])}</td><td>{html.escape(row[2] or "")}</td>'
                f'<td>{row[3]}</td><td>{html.escape(row[4] or "")}</td><td>{row[5] or 0}</td><td>{pl_str}</td>'
                f'<td><a href="/fetch/edit/{row[0]}{auth}">编辑</a> <a href="/api/fetch/{row[0]}" data-method="DELETE">删除</a></td></tr>')
    table = "\n".join(rows) if rows else "<tr><td colspan='7'>暂无配置，<a href='/fetch/add" + auth + "'>添加</a></td></tr>"
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>拉取配置</title>
<style>body{{font-family:sans-serif;max-width:900px;margin:24px auto;padding:0 16px;}}
table{{border-collapse:collapse;width:100%;}} th,td{{padding:8px;border:1px solid #ddd;}} a{{color:#06c;}}</style></head><body>
<h1>拉取配置</h1><p><a href="/config{auth}">返回</a> | <a href="/fetch/add{auth}">添加</a></p>
<table><tr><th>ID</th><th>名称</th><th>API URL</th><th>类型</th><th>固定时间</th><th>间隔(分)</th><th>平台</th><th>操作</th></tr>
{table}</table></body></html>"""
    return HTMLResponse(html_content)


def _render_fetch_form(cfg: dict | None, auth: str, action: str, form_action: str) -> str:
    c = cfg or {}
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>{action}拉取配置</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:24px auto;padding:0 16px;}}
label{{display:block;margin-top:12px;}} input,select,textarea{{width:100%;padding:8px;box-sizing:border-box;}}
button{{margin-top:16px;padding:8px 16px;}} a{{color:#06c;}}</style></head><body>
<h1>{action}拉取配置</h1><p><a href="/fetch{auth}">返回列表</a></p>
<form id="f" method="post" action="{html.escape(form_action)}">
<label>名称</label><input name="name" value="{html.escape(c.get("name",""))}" required>
<label>API 基础 URL</label><input name="api_base_url" value="{html.escape(c.get("api_base_url","https://api.pearktrue.cn"))}">
<label>调度类型</label><select name="schedule_type">
<option value="fixed" {"selected" if c.get("schedule_type")=="fixed" else ""}>固定时刻</option>
<option value="interval" {"selected" if c.get("schedule_type")=="interval" else ""}>时间间隔</option>
</select>
<label>固定时刻（如 07:00,14:00,18:00）</label><input name="fixed_times" value="{html.escape(c.get("fixed_times",""))}" placeholder="07:00,14:00,18:00">
<label>间隔分钟（间隔模式，如 120=每2小时）</label><input name="interval_minutes" type="number" value="{c.get("interval_minutes") or 0}" placeholder="120">
<label>平台（JSON 数组，空=全部）</label><textarea name="platforms" rows="3" placeholder='["知乎","微博"]'>{html.escape(c.get("platforms_str","[]"))}</textarea>
<label><input type="checkbox" name="clear_before_fetch" {"checked" if c.get("clear_before_fetch", True) else ""}> 拉取前清空</label>
<label><input type="checkbox" name="is_active" {"checked" if c.get("is_active", True) else ""}> 启用</label>
<button type="submit">保存</button></form></body></html>"""


@app.get("/fetch/add", response_class=HTMLResponse)
def fetch_add_page(request: Request, _: None = Depends(require_auth)) -> HTMLResponse:
    auth = _auth_suffix(request.query_params.get("api_key"))
    return HTMLResponse(_render_fetch_form(None, auth, "添加", f"/fetch/add{auth}"))


@app.get("/fetch/edit/{id}", response_class=HTMLResponse)
def fetch_edit_page(id: int, request: Request, _: None = Depends(require_auth)) -> HTMLResponse:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT name,api_base_url,schedule_type,fixed_times,interval_minutes,platforms,clear_before_fetch,is_active FROM hot_fetch_config WHERE id=?",
            (id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="配置不存在")
    cfg = {
        "name": row[0], "api_base_url": row[1], "schedule_type": row[2], "fixed_times": row[3],
        "interval_minutes": row[4], "platforms_str": row[5] or "[]", "clear_before_fetch": bool(row[6]), "is_active": bool(row[7]),
    }
    auth = _auth_suffix(request.query_params.get("api_key"))
    return HTMLResponse(_render_fetch_form(cfg, auth, "编辑", f"/fetch/edit/{id}{auth}"))


class FetchConfigBody(BaseModel):
    name: str = ""
    api_base_url: str = "https://api.pearktrue.cn"
    schedule_type: str = "fixed"
    fixed_times: str = ""
    interval_minutes: int = 0
    platforms: str = "[]"
    clear_before_fetch: bool = True
    is_active: bool = True


@app.post("/api/fetch")
def api_fetch_create(body: FetchConfigBody, _: None = Depends(require_auth)) -> dict:
    ts = int(time.time())
    platforms = body.platforms.strip()
    if not platforms:
        platforms = "[]"
    try:
        json.loads(platforms)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="platforms 须为 JSON 数组")
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO hot_fetch_config (name,api_base_url,platforms,schedule_type,fixed_times,interval_minutes,clear_before_fetch,is_active,create_time,update_time)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (body.name, body.api_base_url, platforms, body.schedule_type, body.fixed_times, body.interval_minutes,
             int(body.clear_before_fetch), int(body.is_active), ts, ts),
        )
        rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"ok": True, "id": rid}


@app.post("/api/fetch/{id}")
def api_fetch_update(id: int, body: FetchConfigBody, _: None = Depends(require_auth)) -> dict:
    platforms = body.platforms.strip() or "[]"
    try:
        json.loads(platforms)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="platforms 须为 JSON 数组")
    ts = int(time.time())
    with get_connection() as conn:
        conn.execute(
            """UPDATE hot_fetch_config SET name=?,api_base_url=?,platforms=?,schedule_type=?,fixed_times=?,interval_minutes=?,
               clear_before_fetch=?,is_active=?,update_time=? WHERE id=?""",
            (body.name, body.api_base_url, platforms, body.schedule_type, body.fixed_times, body.interval_minutes,
             int(body.clear_before_fetch), int(body.is_active), ts, id),
        )
    return {"ok": True}


@app.delete("/api/fetch/{id}")
def api_fetch_delete(id: int, _: None = Depends(require_auth)) -> dict:
    with get_connection() as conn:
        conn.execute("DELETE FROM hot_fetch_config WHERE id=?", (id,))
    return {"ok": True}


# ---------- 推送配置 CRUD ----------
@app.get("/push", response_class=HTMLResponse)
def push_config_page(request: Request, _: None = Depends(require_auth)) -> HTMLResponse:
    api_key = request.query_params.get("api_key")
    auth = _auth_suffix(api_key)
    rows = []
    with get_connection() as conn:
        for row in conn.execute(
            "SELECT id,category_code,category_name,im_channel,push_time,max_items,is_active FROM hot_push_config ORDER BY id"
        ).fetchall():
            rows.append(f'<tr><td>{row[0]}</td><td>{html.escape(row[1])}</td><td>{html.escape(row[2])}</td>'
                f'<td>{row[3]}</td><td>{html.escape(row[4] or "")}</td><td>{row[5]}</td><td>{row[6]}</td>'
                f'<td><a href="/push/edit/{row[0]}{auth}">编辑</a> <a href="/api/push/{row[0]}" data-method="DELETE">删除</a></td></tr>')
    table = "\n".join(rows) if rows else "<tr><td colspan='8'>暂无配置，<a href='/push/add" + auth + "'>添加</a></td></tr>"
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>推送配置</title>
<style>body{{font-family:sans-serif;max-width:900px;margin:24px auto;padding:0 16px;}}
table{{border-collapse:collapse;width:100%;}} th,td{{padding:8px;border:1px solid #ddd;}} a{{color:#06c;}}</style></head><body>
<h1>推送配置</h1><p><a href="/config{auth}">返回</a> | <a href="/push/add{auth}">添加</a></p>
<table><tr><th>ID</th><th>类别</th><th>名称</th><th>渠道</th><th>推送时间</th><th>条数</th><th>启用</th><th>操作</th></tr>
{table}</table>
<p>Webhook/Token 在 <a href="/settings{auth}">设置</a> 中配置，不存数据库。</p></body></html>"""
    return HTMLResponse(html_content)


def _render_push_form(cfg: dict | None, auth: str, action: str, form_action: str) -> str:
    c = cfg or {}
    inc = c.get("include_keywords") or []
    exc = c.get("exclude_keywords") or []
    inc_text = "\n".join(inc) if isinstance(inc, list) else ""
    exc_text = "\n".join(exc) if isinstance(exc, list) else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>{action}推送配置</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:24px auto;padding:0 16px;}}
label{{display:block;margin-top:12px;}} input,select,textarea{{width:100%;padding:8px;box-sizing:border-box;}}
button{{margin-top:16px;padding:8px 16px;}} a{{color:#06c;}}</style></head><body>
<h1>{action}推送配置</h1><p><a href="/push{auth}">返回列表</a></p>
<form id="f" method="post" action="{html.escape(form_action)}">
<label>类别 code</label><input name="category_code" value="{html.escape(c.get("category_code",""))}" required placeholder="emotion">
<label>类别名称</label><input name="category_name" value="{html.escape(c.get("category_name",""))}" required placeholder="情感类">
<label>平台（JSON 数组，空=全部）</label><textarea name="sources" rows="2" placeholder='["知乎","微博"]'>{html.escape(c.get("sources_str","[]"))}</textarea>
<label>包含关键词（每行一个）</label><textarea name="include_keywords" rows="4">{html.escape(inc_text)}</textarea>
<label>排除关键词（每行一个）</label><textarea name="exclude_keywords" rows="2">{html.escape(exc_text)}</textarea>
<label>推送时间（如 07:10,14:10,18:10）</label><input name="push_time" value="{html.escape(c.get("push_time",""))}" placeholder="07:10,14:10,18:10">
<label>IM 渠道</label><select name="im_channel">
<option value="feishu" {"selected" if c.get("im_channel")=="feishu" else ""}>飞书</option>
<option value="dingtalk" {"selected" if c.get("im_channel")=="dingtalk" else ""}>钉钉</option>
<option value="telegram" {"selected" if c.get("im_channel")=="telegram" else ""}>Telegram</option>
</select>
<label>Webhook/ChatID（留空则从设置页 .env 读取）</label><input name="webhook_url" value="{html.escape(c.get("webhook_url",""))}" placeholder="可选，默认从 .env 读取">
<label>最多条数</label><input name="max_items" type="number" value="{c.get("max_items",10)}">
<label>输出格式</label><select name="output_format">
<option value="text" {"selected" if c.get("output_format","text")=="text" else ""}>text</option>
<option value="json" {"selected" if c.get("output_format")=="json" else ""}>json</option>
</select>
<label><input type="checkbox" name="is_active" {"checked" if c.get("is_active", True) else ""}> 启用</label>
<button type="submit">保存</button></form></body></html>"""


@app.get("/push/add", response_class=HTMLResponse)
def push_add_page(request: Request, _: None = Depends(require_auth)) -> HTMLResponse:
    auth = _auth_suffix(request.query_params.get("api_key"))
    return HTMLResponse(_render_push_form(None, auth, "添加", f"/push/add{auth}"))


@app.get("/push/edit/{id}", response_class=HTMLResponse)
def push_edit_page(id: int, request: Request, _: None = Depends(require_auth)) -> HTMLResponse:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT category_code,category_name,sources,include_keywords,exclude_keywords,push_time,im_channel,webhook_url,max_items,output_format,is_active
               FROM hot_push_config WHERE id=?""",
            (id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="配置不存在")
    inc = json.loads(row[3]) if row[3] else []
    exc = json.loads(row[4]) if row[4] else []
    cfg = {
        "category_code": row[0], "category_name": row[1], "sources_str": row[2] or "[]",
        "include_keywords": inc, "exclude_keywords": exc, "push_time": row[5], "im_channel": row[6],
        "webhook_url": row[7], "max_items": row[8], "output_format": row[9] or "text", "is_active": bool(row[10]),
    }
    auth = _auth_suffix(request.query_params.get("api_key"))
    return HTMLResponse(_render_push_form(cfg, auth, "编辑", f"/push/edit/{id}{auth}"))


class PushConfigBody(BaseModel):
    category_code: str = ""
    category_name: str = ""
    sources: str = "[]"
    include_keywords: str = ""
    exclude_keywords: str = ""
    push_time: str = ""
    im_channel: str = "feishu"
    webhook_url: str = ""
    max_items: int = 10
    output_format: str = "text"
    is_active: bool = True


@app.post("/api/push")
def api_push_create(body: PushConfigBody, _: None = Depends(require_auth)) -> dict:
    ts = int(time.time())
    sources = body.sources.strip() or "[]"
    try:
        json.loads(sources)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="sources 须为 JSON 数组")
    inc = [s.strip() for s in body.include_keywords.split("\n") if s.strip()]
    exc = [s.strip() for s in body.exclude_keywords.split("\n") if s.strip()]
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO hot_push_config (category_code,category_name,sources,include_keywords,exclude_keywords,push_time,im_channel,webhook_url,max_items,output_format,is_active,create_time,update_time)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (body.category_code, body.category_name, sources, json.dumps(inc, ensure_ascii=False), json.dumps(exc, ensure_ascii=False),
             body.push_time, body.im_channel, "", body.max_items, body.output_format, int(body.is_active), ts, ts),
        )
    return {"ok": True}


@app.post("/api/push/{id}")
def api_push_update(id: int, body: PushConfigBody, _: None = Depends(require_auth)) -> dict:
    sources = body.sources.strip() or "[]"
    try:
        json.loads(sources)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="sources 须为 JSON 数组")
    inc = [s.strip() for s in body.include_keywords.split("\n") if s.strip()]
    exc = [s.strip() for s in body.exclude_keywords.split("\n") if s.strip()]
    ts = int(time.time())
    with get_connection() as conn:
        conn.execute(
            """UPDATE hot_push_config SET category_code=?,category_name=?,sources=?,include_keywords=?,exclude_keywords=?,
               push_time=?,im_channel=?,webhook_url=?,max_items=?,output_format=?,is_active=?,update_time=? WHERE id=?""",
            (body.category_code, body.category_name, sources, json.dumps(inc, ensure_ascii=False), json.dumps(exc, ensure_ascii=False),
             body.push_time, body.im_channel, "", body.max_items, body.output_format, int(body.is_active), ts, id),
        )
    return {"ok": True}


@app.delete("/api/push/{id}")
def api_push_delete(id: int, _: None = Depends(require_auth)) -> dict:
    with get_connection() as conn:
        conn.execute("DELETE FROM hot_push_config WHERE id=?", (id,))
    return {"ok": True}


# ---------- 表单 POST 处理（HTML form 提交）----------
@app.post("/fetch/add")
async def fetch_add_post(request: Request, _: None = Depends(require_auth)):
    from fastapi.responses import RedirectResponse
    form = await request.form()
    body = FetchConfigBody(
        name=form.get("name", ""),
        api_base_url=form.get("api_base_url", "https://api.pearktrue.cn"),
        schedule_type=form.get("schedule_type", "fixed"),
        fixed_times=form.get("fixed_times", ""),
        interval_minutes=int(form.get("interval_minutes", 0) or 0),
        platforms=form.get("platforms", "[]"),
        clear_before_fetch=form.get("clear_before_fetch") == "on",
        is_active=form.get("is_active") == "on",
    )
    api_fetch_create(body)
    return RedirectResponse(url=f"/fetch{_auth_suffix(request.query_params.get('api_key'))}", status_code=303)


@app.post("/fetch/edit/{id}")
async def fetch_edit_post(id: int, request: Request, _: None = Depends(require_auth)):
    from fastapi.responses import RedirectResponse
    form = await request.form()
    body = FetchConfigBody(
        name=form.get("name", ""),
        api_base_url=form.get("api_base_url", "https://api.pearktrue.cn"),
        schedule_type=form.get("schedule_type", "fixed"),
        fixed_times=form.get("fixed_times", ""),
        interval_minutes=int(form.get("interval_minutes", 0) or 0),
        platforms=form.get("platforms", "[]"),
        clear_before_fetch=form.get("clear_before_fetch") == "on",
        is_active=form.get("is_active") == "on",
    )
    api_fetch_update(id, body)
    return RedirectResponse(url=f"/fetch{_auth_suffix(request.query_params.get('api_key'))}", status_code=303)


@app.post("/push/add")
async def push_add_post(request: Request, _: None = Depends(require_auth)):
    from fastapi.responses import RedirectResponse
    form = await request.form()
    body = PushConfigBody(
        category_code=form.get("category_code", ""),
        category_name=form.get("category_name", ""),
        sources=form.get("sources", "[]"),
        include_keywords=form.get("include_keywords", ""),
        exclude_keywords=form.get("exclude_keywords", ""),
        push_time=form.get("push_time", ""),
        im_channel=form.get("im_channel", "feishu"),
        webhook_url=form.get("webhook_url", ""),
        max_items=int(form.get("max_items", 10) or 10),
        output_format=form.get("output_format", "text"),
        is_active=form.get("is_active") == "on",
    )
    api_push_create(body)
    return RedirectResponse(url=f"/push{_auth_suffix(request.query_params.get('api_key'))}", status_code=303)


@app.post("/push/edit/{id}")
async def push_edit_post(id: int, request: Request, _: None = Depends(require_auth)):
    from fastapi.responses import RedirectResponse
    form = await request.form()
    body = PushConfigBody(
        category_code=form.get("category_code", ""),
        category_name=form.get("category_name", ""),
        sources=form.get("sources", "[]"),
        include_keywords=form.get("include_keywords", ""),
        exclude_keywords=form.get("exclude_keywords", ""),
        push_time=form.get("push_time", ""),
        im_channel=form.get("im_channel", "feishu"),
        webhook_url=form.get("webhook_url", ""),
        max_items=int(form.get("max_items", 10) or 10),
        output_format=form.get("output_format", "text"),
        is_active=form.get("is_active") == "on",
    )
    api_push_update(id, body)
    return RedirectResponse(url=f"/push{_auth_suffix(request.query_params.get('api_key'))}", status_code=303)

