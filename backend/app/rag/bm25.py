"""轻量 BM25：中文按字 + 词切分，弥补纯向量检索对地名/人名等专有名词召回不足的问题。"""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

_TOKEN_RE = re.compile(r"[一-龥]|[A-Za-z]+|\d+")
K1 = 1.5
B = 0.75


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25:
    def __init__(self, corpus: list[str]):
        self.docs = [tokenize(t) for t in corpus]
        self.doc_len = np.array([len(d) for d in self.docs], dtype=np.float32)
        self.n = len(self.docs)
        self.avgdl = float(self.doc_len.mean()) if self.n else 0.0
        self.df: Counter = Counter()
        for d in self.docs:
            self.df.update(set(d))
        self.idf = {
            term: math.log(1 + (self.n - freq + 0.5) / (freq + 0.5))
            for term, freq in self.df.items()
        }

    def scores(self, query: str) -> np.ndarray:
        if self.n == 0:
            return np.zeros(0, dtype=np.float32)
        q_terms = tokenize(query)
        out = np.zeros(self.n, dtype=np.float32)
        for i, doc in enumerate(self.docs):
            if not doc:
                continue
            tf = Counter(doc)
            dl = self.doc_len[i] or 1.0
            acc = 0.0
            for term in q_terms:
                f = tf.get(term, 0)
                if not f:
                    continue
                idf = self.idf.get(term, 0.0)
                acc += idf * (f * (K1 + 1)) / (f + K1 * (1 - B + B * dl / (self.avgdl or 1.0)))
            out[i] = acc
        return out


def normalize(x: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return x
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-8:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)
