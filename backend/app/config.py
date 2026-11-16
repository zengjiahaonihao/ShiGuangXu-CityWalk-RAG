from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
# backend/app -> backend -> 项目根
PROJECT_DIR = BASE_DIR.parent.parent
BUILTIN_DIR = PROJECT_DIR / "内置人文库"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
INDEX_DIR = DATA_DIR / "index"
META_FILE = DATA_DIR / "documents.json"
HISTORY_FILE = DATA_DIR / "history.json"

for d in (DATA_DIR, UPLOAD_DIR, INDEX_DIR):
    d.mkdir(parents=True, exist_ok=True)

load_dotenv(DATA_DIR.parent.parent / ".env")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL", "deepseek-chat")

EMBEDDING_PROVIDER = _env("EMBEDDING_PROVIDER", "auto").lower()
EMBEDDING_BASE_URL = _env("EMBEDDING_BASE_URL").rstrip("/")
EMBEDDING_API_KEY = _env("EMBEDDING_API_KEY")
EMBEDDING_MODEL = _env("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = int(_env("EMBEDDING_DIM", "1024") or 1024)

# 无外部 embedding 时的内置降级维度
LOCAL_EMBED_DIM = 1024

ALLOWED_EXT = {".txt", ".md", ".markdown", ".pdf", ".docx"}
MAX_FILE_MB = 20

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
