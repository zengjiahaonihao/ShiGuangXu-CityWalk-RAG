"""文本切片：优先 LangChain RecursiveCharacterTextSplitter，缺失时回退同策略自研实现。

中文文史资料段落普遍偏短，这里用较小的 chunk_size + 一定重叠，
保证一条典故/一座建筑的记载不会被切断。
"""
from __future__ import annotations

import re

CHUNK_SIZE = 420
CHUNK_OVERLAP = 80
SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]


def _split_recursive(text: str, chunk_size: int, chunk_overlap: int, separators: list[str]) -> list[str]:
    final_sep = separators[-1]
    sep = separators[0]
    for candidate in separators:
        if candidate == "":
            sep = candidate
            break
        if candidate in text:
            sep = candidate
            break

    if sep == final_sep:
        raw = list(text)
    else:
        raw = text.split(sep)

    chunks: list[str] = []
    buffer = ""
    for piece in raw:
        piece = piece if sep == final_sep else piece
        candidate = (buffer + sep + piece) if buffer else piece
        if len(candidate) <= chunk_size:
            buffer = candidate
            continue
        if buffer:
            chunks.append(buffer)
        if len(piece) <= chunk_size:
            buffer = piece
            continue
        # 单块仍然超长：递归下一级分隔符
        chunks.extend(_split_recursive(piece, chunk_size, chunk_overlap, separators[separators.index(sep) + 1:]))
        buffer = ""
    if buffer:
        chunks.append(buffer)

    # 叠加重叠片段
    if chunk_overlap <= 0 or len(chunks) <= 1:
        return [c.strip() for c in chunks if c.strip()]

    merged: list[str] = []
    for idx, chunk in enumerate(chunks):
        if idx == 0:
            merged.append(chunk)
            continue
        prev = chunks[idx - 1]
        overlap = prev[-chunk_overlap:]
        merged.append(overlap + chunk)
    return [c.strip() for c in merged if c.strip()]


def split_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        )
        return [c.strip() for c in splitter.split_text(text) if c.strip()]
    except Exception:
        return _split_recursive(text, chunk_size, chunk_overlap, SEPARATORS)
