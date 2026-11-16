from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..history import add_history, clear_history, delete_history, list_history
from ..schemas import HistoryItem

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[HistoryItem])
def get_history(type_: str | None = None, keyword: str = ""):
    return list_history(type_, keyword)


@router.post("", response_model=HistoryItem)
def create_history(item: HistoryItem):
    return add_history(item.type, item.title, item.content, item.sources)


@router.delete("/{item_id}")
def remove_history(item_id: str):
    if not delete_history(item_id):
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True}


@router.delete("")
def remove_all():
    clear_history()
    return {"ok": True}
