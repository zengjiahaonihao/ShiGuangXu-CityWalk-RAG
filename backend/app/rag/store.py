"""知识库仓库：文档元数据 + 向量索引 + 落盘。"""
from __future__ import annotations

import hashlib
import json
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from .. import config
from . import builtin as builtin_mod
from .bm25 import BM25, normalize
from .embeddings import LocalEmbedding, get_embedding_provider
from .loader import load_text
from .splitter import split_text
from .vectorstore import VectorStore

_LOCK = threading.Lock()
_INDEX_PATH = config.INDEX_DIR / "corpus.index"

CATEGORIES = ["老街史料", "古建筑", "地方传说", "非遗手记", "人物口述", "其他"]


class KnowledgeStore:
    def __init__(self):
        self.provider = get_embedding_provider()
        self.vectorstore = VectorStore(self.provider.dim, _INDEX_PATH)
        self.docs: dict[str, dict[str, Any]] = {}
        self._bm25: BM25 | None = None
        self._bm25_sig: tuple | None = None
        self._load_meta()

    # ---------- BM25 关键词索引（按语料变化惰性重建） ----------
    def _get_bm25(self) -> BM25:
        corpus = [m.get("text", "") for m in self.vectorstore.metas]
        sig = (len(corpus), sum(len(c) for c in corpus))
        if self._bm25 is None or self._bm25_sig != sig:
            self._bm25 = BM25(corpus)
            self._bm25_sig = sig
        return self._bm25

    # ---------- 元数据 ----------
    def _load_meta(self) -> None:
        if config.META_FILE.exists():
            try:
                self.docs = json.loads(config.META_FILE.read_text(encoding="utf-8"))
            except Exception:
                self.docs = {}

    def _save_meta(self) -> None:
        config.META_FILE.write_text(
            json.dumps(self.docs, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_docs(self, category: str | None = None) -> list[dict[str, Any]]:
        items = list(self.docs.values())
        if category:
            items = [d for d in items if d.get("category") == category]
        return sorted(items, key=lambda d: d.get("created_at", ""), reverse=True)

    def get_doc(self, doc_id: str) -> dict[str, Any] | None:
        return self.docs.get(doc_id)

    def update_doc(self, doc_id: str, name: str | None = None, category: str | None = None):
        doc = self.docs.get(doc_id)
        if not doc:
            return None
        if name:
            doc["name"] = name
        if category:
            doc["category"] = category
            for meta in self.vectorstore.metas:
                if meta.get("doc_id") == doc_id:
                    meta["category"] = category
            self.vectorstore.save()
        self._save_meta()
        return doc

    def delete_doc(self, doc_id: str) -> bool:
        doc = self.docs.pop(doc_id, None)
        if not doc:
            return False
        self.vectorstore.remove_doc(doc_id)
        file_path = Path(doc.get("path", ""))
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass
        self._save_meta()
        return True

    def clear(self) -> None:
        """清空用户上传的资料；内置人文库保留（可用 force 重建）。"""
        for doc_id in [k for k, v in self.docs.items() if v.get("origin") != "builtin"]:
            self.delete_doc(doc_id)
        if config.UPLOAD_DIR.exists():
            shutil.rmtree(config.UPLOAD_DIR, ignore_errors=True)
            config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self._save_meta()

    # ---------- 入库 ----------
    def add_file(self, filename: str, raw: bytes, category: str) -> dict[str, Any]:
        ext = Path(filename).suffix.lower()
        if ext not in config.ALLOWED_EXT:
            raise ValueError(f"不支持的文件类型：{ext or '未知'}，支持 {', '.join(sorted(config.ALLOWED_EXT))}")
        if len(raw) > config.MAX_FILE_MB * 1024 * 1024:
            raise ValueError(f"文件超过 {config.MAX_FILE_MB}MB 限制")

        doc_id = uuid.uuid4().hex[:12]
        safe_name = Path(filename).name
        save_path = config.UPLOAD_DIR / f"{doc_id}_{safe_name}"
        save_path.write_bytes(raw)

        text = load_text(save_path)
        if len(text.strip()) < 10:
            save_path.unlink(missing_ok=True)
            raise ValueError("文档内容为空或无法解析出文字（扫描版 PDF 请先 OCR）")

        chunks = split_text(text)
        if not chunks:
            save_path.unlink(missing_ok=True)
            raise ValueError("切片后无有效内容")

        vectors = self.provider.embed(chunks)
        metas = [
            {
                "doc_id": doc_id,
                "doc_name": safe_name,
                "category": category,
                "chunk_id": i,
                "text": chunk,
            }
            for i, chunk in enumerate(chunks)
        ]
        with _LOCK:
            self.vectorstore.add(np.asarray(vectors, dtype=np.float32), metas)

        doc = {
            "id": doc_id,
            "name": safe_name,
            "category": category,
            "size": len(raw),
            "ext": ext,
            "chunks": len(chunks),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "path": str(save_path),
            "preview": text[:160].replace("\n", " "),
        }
        self.docs[doc_id] = doc
        self._save_meta()
        return doc

    # ---------- 纯文本入库（内置人文库用） ----------
    def add_text_doc(self, name: str, text: str, category: str, *, origin: str = "user",
                     city: str = "", image: str = "", source: str = "",
                     doc_id: str | None = None, created_at: str | None = None) -> dict[str, Any]:
        chunks = split_text(text)
        if not chunks:
            raise ValueError("切片后无有效内容")
        doc_id = doc_id or uuid.uuid4().hex[:12]
        vectors = self.provider.embed(chunks)
        metas = [
            {
                "doc_id": doc_id,
                "doc_name": name,
                "category": category,
                "chunk_id": i,
                "text": chunk,
            }
            for i, chunk in enumerate(chunks)
        ]
        with _LOCK:
            self.vectorstore.add(np.asarray(vectors, dtype=np.float32), metas)
        doc = {
            "id": doc_id,
            "name": name,
            "category": category,
            "size": len(text.encode("utf-8")),
            "ext": Path(name).suffix.lower() or ".txt",
            "chunks": len(chunks),
            "created_at": created_at or time.strftime("%Y-%m-%d %H:%M:%S"),
            "path": "",
            "preview": text[:160].replace("\n", " "),
            "origin": origin,
            "city": city,
            "image": image,
            "source": source,
        }
        self.docs[doc_id] = doc
        self._save_meta()
        return doc

    # ---------- 内置人文库（幂等同步） ----------
    def sync_builtin(self, force: bool = False) -> dict[str, Any]:
        """扫描项目根的「内置人文库」目录，把未入库的篇目导入向量库。"""
        base = config.BUILTIN_DIR
        added: list[str] = []
        skipped: list[str] = []
        if not base.exists():
            return {"added": added, "skipped": skipped, "total": 0, "dir": str(base), "exists": False}

        for entry in builtin_mod.builtin_entries():
            fname = entry["doc"]
            fpath = base / fname
            if not fpath.exists():
                skipped.append(fname)
                continue
            stable_id = "bi_" + hashlib.md5(fname.encode("utf-8")).hexdigest()[:10]
            if not force and stable_id in self.docs:
                skipped.append(fname)
                continue
            if force and stable_id in self.docs:
                self.delete_doc(stable_id)
            text = fpath.read_text(encoding="utf-8")
            self.add_text_doc(
                name=fname,
                text=text,
                category=entry.get("category", "老街史料"),
                origin="builtin",
                city=entry.get("city", ""),
                image=entry.get("image", ""),
                source="内置人文库（公开资料整理）",
                doc_id=stable_id,
            )
            added.append(fname)
        return {
            "added": added,
            "skipped": skipped,
            "total": len(self.docs),
            "dir": str(base),
            "exists": True,
        }

    def builtin_ready(self) -> bool:
        return any(d.get("origin") == "builtin" for d in self.docs.values())

    def cities(self) -> list[dict[str, Any]]:
        """城市档案 + 是否已入库的 doc_id。"""
        out = []
        by_doc = {d.get("name"): d for d in self.docs.values() if d.get("origin") == "builtin"}
        for profile in builtin_mod.CITY_PROFILES:
            item = dict(profile)
            doc = by_doc.get(profile["doc"])
            item["doc_id"] = doc["id"] if doc else ""
            item["chunks"] = doc.get("chunks", 0) if doc else 0
            item["ingested"] = bool(doc)
            item["doc"] = ""
            item.update(builtin_mod.city_coords(profile["id"]))
            out.append(item)
        return out

    # ---------- 检索（向量 + BM25 融合） ----------
    def retrieve(self, question: str, top_k: int = 5,
                 doc_ids: list[str] | None = None, category: str | None = None):
        vs = self.vectorstore
        idxs = vs.candidate_indices(doc_ids, category)
        if not idxs:
            return []

        query_vec = np.asarray(self.provider.embed([question])[0], dtype=np.float32)
        vec_scores = normalize(vs.vector_scores(idxs, query_vec))

        bm_all = self._get_bm25().scores(question)
        bm_scores = normalize(np.asarray([bm_all[i] for i in idxs], dtype=np.float32))

        # 语义向量可靠时以向量为主；内置 hashing 向量则更倚重关键词匹配
        w_vec = 0.35 if isinstance(self.provider, LocalEmbedding) else 0.65
        final = w_vec * vec_scores + (1.0 - w_vec) * bm_scores

        order = np.argsort(-final)[:top_k]
        results = []
        for rank in order:
            meta = vs.metas[idxs[rank]]
            results.append(
                {
                    "doc_id": meta.get("doc_id"),
                    "doc_name": meta.get("doc_name"),
                    "category": meta.get("category", ""),
                    "chunk_id": meta.get("chunk_id"),
                    "score": round(float(final[rank]), 4),
                    "text": meta.get("text", ""),
                }
            )
        return results

    def stats(self) -> dict[str, Any]:
        cats: dict[str, int] = {}
        for d in self.docs.values():
            cats[d.get("category", "未分类")] = cats.get(d.get("category", "未分类"), 0) + 1
        return {
            "doc_count": len(self.docs),
            "chunk_count": self.vectorstore.count(),
            "embedding_backend": f"{type(self.provider).__name__}",
            "vector_backend": self.vectorstore.backend,
            "dim": self.vectorstore.vectors.shape[1] if self.vectorstore.vectors.ndim == 2 else self.provider.dim,
            "categories": cats,
        }


_STORE: KnowledgeStore | None = None


def get_store() -> KnowledgeStore:
    global _STORE
    if _STORE is None:
        _STORE = KnowledgeStore()
    return _STORE
