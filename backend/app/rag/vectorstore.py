"""向量库：优先 FAISS（IndexFlatIP），不可用时自动降级为等价的 NumPy 实现。

对外接口保持一致，便于答辩时说明"向量库可替换"。
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

try:  # pragma: no cover - 环境相关
    import faiss

    _HAS_FAISS = True
except Exception:  # pragma: no cover
    faiss = None
    _HAS_FAISS = False


class VectorStore:
    """保存 (vector, chunk_meta) 并支持按 doc_id / category 过滤检索。"""

    def __init__(self, dim: int, index_path: Path):
        self.dim = dim
        self.index_path = index_path
        self.vectors = np.zeros((0, dim), dtype=np.float32)
        self.metas: list[dict] = []
        self.backend = "faiss" if _HAS_FAISS else "numpy"
        self._index = None
        self.load()

    # ---------- 持久化 ----------
    def load(self) -> None:
        vec_file = self.index_path.with_suffix(".npy")
        meta_file = self.index_path.with_suffix(".meta.pkl")
        if vec_file.exists():
            self.vectors = np.load(vec_file)
        if meta_file.exists():
            with open(meta_file, "rb") as f:
                self.metas = pickle.load(f)
        if _HAS_FAISS and self.vectors.shape[0] > 0:
            self._rebuild_faiss()

    def save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(self.index_path.with_suffix(".npy"), self.vectors)
        with open(self.index_path.with_suffix(".meta.pkl"), "wb") as f:
            pickle.dump(self.metas, f)

    def _rebuild_faiss(self) -> None:
        if _HAS_FAISS and self.vectors.shape[0] > 0:
            self._index = faiss.IndexFlatIP(self.dim)
            self._index.add(self.vectors)

    # ---------- 写入 ----------
    def add(self, vectors: np.ndarray, metas: list[dict]) -> None:
        if vectors.size == 0:
            return
        if self.vectors.shape[0] == 0:
            self.vectors = vectors.astype(np.float32)
        else:
            if self.vectors.shape[1] != vectors.shape[1]:
                raise ValueError(
                    f"向量维度不一致：已有 {self.vectors.shape[1]}，新增 {vectors.shape[1]}，"
                    "请清空知识库后统一 embedding 重新入库"
                )
            self.vectors = np.vstack([self.vectors, vectors]).astype(np.float32)
        self.metas.extend(metas)
        if _HAS_FAISS:
            if self._index is None:
                self._index = faiss.IndexFlatIP(self.dim)
            self._index.add(vectors.astype(np.float32))
        self.save()

    def remove_doc(self, doc_id: str) -> int:
        keep = [i for i, m in enumerate(self.metas) if m.get("doc_id") != doc_id]
        removed = len(self.metas) - len(keep)
        if removed:
            self.metas = [self.metas[i] for i in keep]
            self.vectors = self.vectors[keep] if self.vectors.shape[0] else self.vectors
            self._index = None
            self._rebuild_faiss()
            self.save()
        return removed

    def clear(self) -> None:
        self.vectors = np.zeros((0, self.dim), dtype=np.float32)
        self.metas = []
        self._index = None
        self.save()

    # ---------- 检索 ----------
    def candidate_indices(self, doc_ids: list[str] | None = None,
                          category: str | None = None) -> list[int]:
        idxs = list(range(len(self.metas)))
        if doc_ids:
            doc_set = set(doc_ids)
            idxs = [i for i in idxs if self.metas[i].get("doc_id") in doc_set]
        if category:
            idxs = [i for i in idxs if self.metas[i].get("category") == category]
        return idxs

    def vector_scores(self, idxs: list[int], query_vec: np.ndarray) -> np.ndarray:
        sub = self.vectors[idxs]
        return np.asarray(sub @ query_vec.reshape(-1), dtype=np.float32)

    def search(self, query_vec: np.ndarray, top_k: int = 5,
               doc_ids: list[str] | None = None, category: str | None = None) -> list[tuple[float, dict]]:
        idxs = self.candidate_indices(doc_ids, category)
        if not idxs:
            return []
        scores = self.vector_scores(idxs, query_vec)
        order = np.argsort(-scores)[: top_k * 2]
        results: list[tuple[float, dict]] = []
        seen: set[tuple[str, int]] = set()
        for rank in order:
            score = float(scores[rank])
            if score <= 0:
                continue
            meta = dict(self.metas[idxs[rank]])
            key = (meta.get("doc_id", ""), meta.get("chunk_id", -1))
            if key in seen:
                continue
            seen.add(key)
            results.append((score, meta))
            if len(results) >= top_k:
                break
        return results

    def count(self) -> int:
        return len(self.metas)

    def dim(self) -> int:
        return self.vectors.shape[1] if self.vectors.ndim == 2 else self.dim
