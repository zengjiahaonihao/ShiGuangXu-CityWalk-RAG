"""历史记录：JSON 落盘，保存对话与路线文案，支持复制导出。"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from . import config


def _read() -> list[dict[str, Any]]:
    if not config.HISTORY_FILE.exists():
        return []
    try:
        return json.loads(config.HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write(items: list[dict[str, Any]]) -> None:
    config.HISTORY_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_history(type_: str | None = None, keyword: str = "") -> list[dict[str, Any]]:
    items = _read()
    if type_:
        items = [i for i in items if i.get("type") == type_]
    if keyword:
        kw = keyword.lower()
        items = [i for i in items if kw in (i.get("title", "") + i.get("content", "")).lower()]
    return sorted(items, key=lambda i: i.get("created_at", ""), reverse=True)


def add_history(type_: str, title: str, content: str, sources: list[dict] | None = None) -> dict[str, Any]:
    items = _read()
    item = {
        "id": uuid.uuid4().hex[:12],
        "type": type_,
        "title": title[:80],
        "content": content,
        "sources": sources or [],
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    items.append(item)
    _write(items)
    return item


def delete_history(item_id: str) -> bool:
    items = _read()
    remain = [i for i in items if i["id"] != item_id]
    if len(remain) == len(items):
        return False
    _write(remain)
    return True


def clear_history() -> None:
    _write([])
