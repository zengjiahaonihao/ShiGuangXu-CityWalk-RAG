"""DeepSeek Chat 调用封装（原生 httpx，支持 SSE 流式）。"""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from .. import config

SYSTEM_QA = """你是「拾光叙」的城市人文漫步向导，为大学生 Citywalk、城市研学提供讲解。
规则：
1. 只依据【参考资料】回答。资料里没有的内容，必须明确说明"资料中未记载"，禁止编造年代、人物、典故。
2. 回答用中文，语气温润有画面感，但信息要准确；适当分点，避免空话。
3. 涉及来源时，在句末用 [1] [2] 标注对应资料编号。
4. 若资料与问题无关，先说明"当前知识库未收录相关资料"，再给出通用的研学建议。"""

SYSTEM_ROUTE = """你是「拾光叙」的 Citywalk 路线策划师，服务大学生人文研学。
规则：
1. 严格基于【参考资料】中真实出现的地点、建筑、典故设计路线，不得虚构地名。
2. 输出 Markdown，包含：路线主题与一句话引言、按顺序列出的打卡点（每点含：地点 / 看点 / 人文背景 / 建议停留 / 打卡文案）、漫步贴士、研学思考题。
3. 每个打卡点后标注引用编号 [1] [2]，引用必须来自资料。
4. 若资料不足，如实说明并给出补充调研建议。"""


def resolve_cred(cred: dict | None = None) -> dict[str, str]:
    """合并调用方传入的 Key 与服务端 .env 配置；请求优先。"""
    cred = cred or {}
    return {
        "key": (cred.get("key") or config.DEEPSEEK_API_KEY or "").strip(),
        "base": (cred.get("base") or config.DEEPSEEK_BASE_URL or "https://api.deepseek.com").rstrip("/"),
        "model": (cred.get("model") or config.DEEPSEEK_MODEL or "deepseek-chat").strip(),
    }


def has_llm(cred: dict | None = None) -> bool:
    return bool(resolve_cred(cred)["key"])


def _headers(cred: dict | None = None) -> dict[str, str]:
    c = resolve_cred(cred)
    if not c["key"]:
        raise RuntimeError("未配置 API Key：请在页面右下角「接入大模型」里填写，或在 backend/.env 配置后重启")
    return {
        "Authorization": f"Bearer {c['key']}",
        "Content-Type": "application/json",
    }


def extractive_answer(question: str, sources: list[dict], limit: int = 3) -> str:
    """游客模式：不调用大模型，直接把最相关的资料原文交给用户。"""
    if not sources:
        return ("当前知识库没有检索到与这个问题相关的资料。\n\n"
                "可以换一个更具体的地名或构件再问；也可以到「知识库」上传自己的史料。")
    lines = ["**游客模式**（未配置 API Key，先按资料原文作答）", ""]
    for i, src in enumerate(sources[:limit], 1):
        text = " ".join(str(src.get("text", "")).split())
        lines.append(f"**[{i}] 《{src.get('doc_name', '未知文档')}》**")
        lines.append(text[:260] + ("…" if len(text) > 260 else ""))
        lines.append("")
    lines.append("—— 想要连贯成文的回答，可在「接入大模型」中填写自己的 API Key。")
    return "\n".join(lines)


def build_context(sources: list[dict]) -> str:
    if not sources:
        return "（本次检索无可用资料）"
    blocks = []
    for i, src in enumerate(sources, 1):
        blocks.append(f"[{i}] 来源：《{src.get('doc_name', '未知文档')}》片段{src.get('chunk_id', 0)}\n{src.get('text', '')}")
    return "\n\n".join(blocks)


def build_messages(question: str, sources: list[dict], mode: str = "qa", extra: str = "") -> list[dict]:
    system = SYSTEM_ROUTE if mode == "route" else SYSTEM_QA
    context = build_context(sources)
    user = f"【参考资料】\n{context}\n\n【用户问题】\n{question}"
    if extra:
        user += f"\n\n【附加要求】\n{extra}"
    if not sources:
        user += "\n\n（注意：知识库暂无命中资料，请如实说明并避免编造。）"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


async def stream_chat(messages: list[dict], temperature: float = 0.7,
                      cred: dict | None = None) -> AsyncIterator[str]:
    """逐块产出 DeepSeek 返回的增量文本。"""
    c = resolve_cred(cred)
    url = f"{c['base']}/chat/completions"
    payload = {
        "model": c["model"],
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "max_tokens": 2048,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", url, json=payload, headers=_headers(cred)) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(f"DeepSeek 返回 {resp.status_code}: {body.decode('utf-8', 'ignore')[:400]}")
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                if delta:
                    yield delta


async def chat_once(messages: list[dict], temperature: float = 0.7,
                    cred: dict | None = None) -> str:
    c = resolve_cred(cred)
    url = f"{c['base']}/chat/completions"
    payload = {
        "model": c["model"],
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": 2048,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=_headers(cred))
    if resp.status_code != 200:
        raise RuntimeError(f"DeepSeek 返回 {resp.status_code}: {resp.text[:400]}")
    return resp.json()["choices"][0]["message"]["content"]
