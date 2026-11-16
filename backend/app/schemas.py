from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DocOut(BaseModel):
    id: str
    name: str
    category: str
    size: int
    ext: str
    chunks: int
    created_at: str
    preview: str = ""
    origin: str = "user"  # user | builtin
    city: str = ""
    image: str = ""
    source: str = ""


class DocUpdate(BaseModel):
    category: str | None = None
    name: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    doc_ids: list[str] = Field(default_factory=list)
    category: str | None = None
    top_k: int = 5
    session_id: str | None = None


class SourceItem(BaseModel):
    doc_id: str
    doc_name: str
    chunk_id: int
    score: float
    text: str


class RouteRequest(BaseModel):
    doc_ids: list[str] = Field(default_factory=list)
    category: str | None = None
    city: str = ""
    theme: str = ""
    duration: str = "半日"
    pace: str = "悠闲"
    transport: str = "步行为主"
    extra: str = ""
    top_k: int = 8


class HistoryItem(BaseModel):
    id: str
    type: str  # chat | route
    title: str
    content: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
