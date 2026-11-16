from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..rag.store import CATEGORIES, get_store
from ..schemas import DocOut, DocUpdate

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _out(d: dict) -> DocOut:
    return DocOut(
        id=d["id"], name=d["name"], category=d.get("category", "其他"),
        size=d.get("size", 0), ext=d.get("ext", ""), chunks=d.get("chunks", 0),
        created_at=d.get("created_at", ""), preview=d.get("preview", ""),
        origin=d.get("origin", "user"), city=d.get("city", ""),
        image=d.get("image", ""), source=d.get("source", ""),
    )


@router.get("/categories")
def list_categories():
    return {"categories": CATEGORIES}


@router.get("/stats")
def stats():
    return get_store().stats()


@router.get("/cities")
def list_cities():
    """内置人文库的城市档案（含对应 doc_id，供路线生成直接指定）。"""
    store = get_store()
    if not store.builtin_ready():
        store.sync_builtin()
    return {"cities": store.cities()}


@router.get("/cities/{city_id}")
def city_detail(city_id: str):
    """单座城的完整档案：城市档案 + 正文章节 + 看点坐标。"""
    from ..rag import builtin as builtin_mod

    profile = next((p for p in builtin_mod.CITY_PROFILES if p["id"] == city_id), None)
    if not profile:
        raise HTTPException(status_code=404, detail="没有这座城的档案")

    store = get_store()
    if not store.builtin_ready():
        store.sync_builtin()
    item = next((c for c in store.cities() if c["id"] == city_id), {})

    return {
        **profile,
        "doc_id": item.get("doc_id", ""),
        "chunks": item.get("chunks", 0),
        "ingested": item.get("ingested", False),
        "spots": item.get("spots", []),
        "center": item.get("center"),
        "sections": builtin_mod.city_sections(city_id),
    }


@router.post("/builtin/sync")
def sync_builtin(force: bool = False):
    """导入（或强制重建）内置人文库。"""
    try:
        return get_store().sync_builtin(force=force)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"内置库导入失败：{exc}")


@router.get("/docs", response_model=list[DocOut])
def list_docs(category: str | None = None, origin: str | None = None):
    docs = get_store().list_docs(category)
    if origin:
        docs = [d for d in docs if d.get("origin", "user") == origin]
    return [_out(d) for d in docs]


@router.post("/upload", response_model=DocOut)
async def upload(file: UploadFile = File(...), category: str = Form("其他")):
    store = get_store()
    try:
        raw = await file.read()
        doc = store.add_file(file.filename or "unnamed", raw, category)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"入库失败：{exc}")
    return _out(doc)


@router.patch("/docs/{doc_id}", response_model=DocOut)
def update_doc(doc_id: str, payload: DocUpdate):
    doc = get_store().update_doc(doc_id, name=payload.name, category=payload.category)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return _out(doc)


@router.delete("/docs/{doc_id}")
def delete_doc(doc_id: str):
    if not get_store().delete_doc(doc_id):
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"ok": True}


@router.delete("/clear")
def clear_all():
    get_store().clear()
    return {"ok": True}
