"""fastfish-hot 核心模块。"""

from core.fetcher import (
    delete_all_raw_items,
    fetch_from_api,
    fetch_platforms,
    get_fetch_configs,
    save_raw_items,
)
from core.filter import _dedupe_by_link, filter_items
from core.pusher import (
    already_pushed_in_window,
    already_pushed_today,
    format_push_message,
    get_push_configs,
    get_today_raw_items,
    push_to_im,
    record_push_history,
)

__all__ = [
    "delete_all_raw_items",
    "fetch_from_api",
    "fetch_platforms",
    "get_fetch_configs",
    "save_raw_items",
    "filter_items",
    "_dedupe_by_link",
    "get_push_configs",
    "get_today_raw_items",
    "format_push_message",
    "push_to_im",
    "already_pushed_today",
    "already_pushed_in_window",
    "record_push_history",
]
