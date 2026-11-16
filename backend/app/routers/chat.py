from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..history import add_history
from ..llm.deepseek import build_messages, extractive_answer, has_llm, stream_chat
from ..rag.store import get_store
from ..schemas import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


def cred_from(request: Request) -> dict:
    """从请求头读取用户自带的 Key；缺省时回落到服务端 .env。"""
    return {
        "key": request.headers.get("x-llm-key", ""),
        "base": request.headers.get("x-llm-base", ""),
        "model": request.headers.get("x-llm-model", ""),
    }


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _event_stream(payload: ChatRequest, cred: dict) -> AsyncIterator[str]:
    store = get_store()
    sources = store.retrieve(
        payload.question, top_k=payload.top_k, doc_ids=payload.doc_ids, category=payload.category
    )
    yield _sse("sources", {"sources": sources})

    # 游客模式：没有 Key 时不调用大模型，直接把资料原文交给用户
    if not has_llm(cred):
        text = extractive_answer(payload.question, sources)
        yield _sse("delta", {"text": text})
        item = add_history("chat", payload.question[:60], text, sources)
        yield _sse("done", {"content": text, "history_id": item["id"], "guest": True})
        return

    messages = build_messages(payload.question, sources, mode="qa")
    full = ""
    try:
        async for delta in stream_chat(messages, cred=cred):
            full += delta
            yield _sse("delta", {"text": delta})
    except RuntimeError as exc:
        # Key 失效 / 余额不足时，不让用户卡住：退回原文摘录
        msg = str(exc)
        text = f"（模型调用未成功：{msg[:120]}）\n\n" + extractive_answer(payload.question if hasattr(payload, 'question') else question, sources)
        yield _sse("delta", {"text": text})
        item = add_history("chat", (payload.question if hasattr(payload, 'question') else '路线生成')[:60], text, sources)
        yield _sse("done", {"content": text, "history_id": item["id"], "guest": True})
        return
    except Exception as exc:  # noqa: BLE001
        yield _sse("error", {"message": f"生成失败：{exc}"})
        return

    item = add_history("chat", payload.question[:60], full, sources)
    yield _sse("done", {"content": full, "history_id": item["id"]})


@router.post("/stream")
async def chat_stream(payload: ChatRequest, request: Request):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    return StreamingResponse(
        _event_stream(payload, cred_from(request)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/retrieve")
def retrieve(payload: ChatRequest):
    """仅检索，不调用大模型，便于调试切片效果。"""
    return {"sources": get_store().retrieve(payload.question, top_k=payload.top_k,
                                            doc_ids=payload.doc_ids, category=payload.category)}
