from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..history import add_history
from ..llm.deepseek import build_messages, extractive_answer, has_llm, stream_chat
from ..rag.store import get_store
from ..schemas import RouteRequest

router = APIRouter(prefix="/api/route", tags=["route"])


def cred_from(request: Request) -> dict:
    return {
        "key": request.headers.get("x-llm-key", ""),
        "base": request.headers.get("x-llm-base", ""),
        "model": request.headers.get("x-llm-model", ""),
    }


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _build_question(p: RouteRequest) -> str:
    parts = [f"请设计一条「{p.city or '本地'}」的 Citywalk 人文漫步路线。"]
    if p.theme:
        parts.append(f"主题偏好：{p.theme}。")
    parts.append(f"时长：{p.duration}；节奏：{p.pace}；交通：{p.transport}。")
    if p.extra:
        parts.append(f"其他要求：{p.extra}")
    parts.append("请给出按顺序排列的打卡点，每点附人文背景和打卡文案。")
    return "\n".join(parts)


async def _event_stream(payload: RouteRequest, cred: dict) -> AsyncIterator[str]:
    store = get_store()
    question = _build_question(payload)
    sources = store.retrieve(question, top_k=payload.top_k,
                             doc_ids=payload.doc_ids, category=payload.category)
    yield _sse("sources", {"sources": sources})

    if not has_llm(cred):
        text = "**游客模式**：未配置 API Key，先给你资料里与这条路线相关的原文，可据此自行串点。\n\n"
        text += extractive_answer(question, sources, limit=4)
        yield _sse("delta", {"text": text})
        title = f"{payload.city or 'Citywalk'}·{payload.theme or '人文漫步'} · {payload.duration}"
        item = add_history("route", title, text, sources)
        yield _sse("done", {"content": text, "history_id": item["id"], "guest": True})
        return

    messages = build_messages(question, sources, mode="route")
    full = ""
    try:
        async for delta in stream_chat(messages, temperature=0.85, cred=cred):
            full += delta
            yield _sse("delta", {"text": delta})
    except RuntimeError as exc:
        # Key 失效 / 余额不足时，不让用户卡住：退回原文摘录
        msg = str(exc)
        text = f"（模型调用未成功：{msg[:120]}）\n\n" + extractive_answer(question, sources)
        yield _sse("delta", {"text": text})
        title = f"{payload.city or 'Citywalk'}·{payload.theme or '人文漫步'} · {payload.duration}"
        item = add_history("route", title, text, sources)
        yield _sse("done", {"content": text, "history_id": item["id"], "guest": True})
        return
    except Exception as exc:  # noqa: BLE001
        yield _sse("error", {"message": f"生成失败：{exc}"})
        return

    title = f"{payload.city or 'Citywalk'}·{payload.theme or '人文漫步'} · {payload.duration}"
    item = add_history("route", title, full, sources)
    yield _sse("done", {"content": full, "history_id": item["id"]})


@router.post("/stream")
async def route_stream(payload: RouteRequest, request: Request):
    return StreamingResponse(
        _event_stream(payload, cred_from(request)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
