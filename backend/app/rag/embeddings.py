"""可插拔 Embedding。

三档策略，保证任何环境下项目都能跑起来：
1. api   —— 调用 OpenAI 兼容 /embeddings（如 bge-m3），语义效果最好
2. local —— 内置 hashing + 字符 n-gram 加权向量，零依赖离线可用
3. auto  —— 优先 sentence-transformers，其次 api，最后 local
"""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

import numpy as np

from .. import config

_TOKEN_RE = re.compile(r"[一-龥]|[A-Za-z]+|\d+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class EmbeddingProvider:
    """统一接口：embed(texts) -> np.ndarray [n, dim]，已做 L2 归一化。"""

    def __init__(self, dim: int):
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class LocalEmbedding(EmbeddingProvider):
    """轻量 hashing embedding：中文单字 + 词级 n-gram 混合加权，无外部依赖。"""

    def __init__(self, dim: int = config.LOCAL_EMBED_DIM):
        super().__init__(dim)

    def embed(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            tokens = _tokenize(text)
            if not tokens:
                continue
            feats: dict[int, float] = {}
            # 单字特征
            for tok in tokens:
                for ch in (tok if len(tok) == 1 else tok):
                    idx = int(hashlib.md5(f"c:{ch}".encode()).hexdigest(), 16) % self.dim
                    feats[idx] = feats.get(idx, 0.0) + 1.0
            # 二元组特征（保留一定的词序信息）
            for a, b in zip(tokens, tokens[1:]):
                idx = int(hashlib.md5(f"g:{a}{b}".encode()).hexdigest(), 16) % self.dim
                feats[idx] = feats.get(idx, 0.0) + 1.2
            for idx, val in feats.items():
                matrix[row, idx] = val
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (matrix / norms).astype(np.float32)


class ApiEmbedding(EmbeddingProvider):
    """OpenAI 兼容 embeddings 接口。"""

    def __init__(self, base_url: str, api_key: str, model: str, dim: int):
        super().__init__(dim)
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    def embed(self, texts: list[str]) -> np.ndarray:
        import httpx

        url = f"{self.base_url}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"model": self.model, "input": texts}
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()["data"]
        data.sort(key=lambda x: x.get("index", 0))
        vectors = np.array([d["embedding"] for d in data], dtype=np.float32)
        if self.dim and vectors.shape[1] != self.dim:
            self.dim = vectors.shape[1]
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (vectors / norms).astype(np.float32)


class SentenceTransformerEmbedding(EmbeddingProvider):
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        super().__init__(int(self.model.get_sentence_embedding_dimension()))

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
        return np.asarray(vectors, dtype=np.float32)


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    provider = config.EMBEDDING_PROVIDER
    if provider == "api":
        if not (config.EMBEDDING_BASE_URL and config.EMBEDDING_API_KEY):
            print("[embedding] 未配置 api 参数，回退 local")
            return LocalEmbedding()
        return ApiEmbedding(config.EMBEDDING_BASE_URL, config.EMBEDDING_API_KEY,
                            config.EMBEDDING_MODEL, config.EMBEDDING_DIM)
    if provider == "local":
        return LocalEmbedding()

    # auto
    try:
        return SentenceTransformerEmbedding()
    except Exception:
        pass
    if config.EMBEDDING_BASE_URL and config.EMBEDDING_API_KEY:
        try:
            return ApiEmbedding(config.EMBEDDING_BASE_URL, config.EMBEDDING_API_KEY,
                                config.EMBEDDING_MODEL, config.EMBEDDING_DIM)
        except Exception:
            pass
    print("[embedding] 使用内置 local hashing 向量（离线降级模式）")
    return LocalEmbedding()


def cosine_matrix(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return np.zeros(0, dtype=np.float32)
    return np.asarray(matrix @ query_vec, dtype=np.float32).reshape(-1)


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    norm = float(math.sqrt(float((vec * vec).sum())) or 1.0)
    return (vec / norm).astype(np.float32)
