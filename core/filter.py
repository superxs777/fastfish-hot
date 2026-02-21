"""
热点过滤模块。

关键词过滤、去重。
"""

from __future__ import annotations


def _match_keywords(text: str, keywords: list[str]) -> bool:
    """检查文本是否包含任一关键词（不区分大小写）。"""
    if not keywords:
        return False
    lower = (text or "").lower()
    for kw in keywords:
        if kw and kw.lower() in lower:
            return True
    return False


def filter_items(
    items: list[dict],
    include_keywords: list[str],
    exclude_keywords: list[str],
) -> list[dict]:
    """按关键词过滤热点。先排除 exclude，再按 include 筛选（若 include 非空）。"""
    filtered = []
    for item in items:
        title = item.get("title", "") or ""
        desc = item.get("desc", "") or ""
        text = f"{title} {desc}"

        if exclude_keywords and _match_keywords(text, exclude_keywords):
            continue
        if include_keywords and not _match_keywords(text, include_keywords):
            continue
        filtered.append(item)
    return filtered


def _dedupe_by_link(items: list[dict]) -> list[dict]:
    """按 link 去重，保留 rank 最小的。"""
    seen = {}
    for item in items:
        link = (item.get("link") or "").strip()
        if not link:
            continue
        if link not in seen or (item.get("rank", 999) < seen[link].get("rank", 999)):
            seen[link] = item
    return list(seen.values())
