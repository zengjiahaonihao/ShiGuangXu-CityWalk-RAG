from __future__ import annotations

import random
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .rag.store import get_store
from .routers import chat, history, knowledge, route


@asynccontextmanager
async def lifespan(_: FastAPI):
    store = get_store()  # 启动时加载索引与元数据
    try:
        res = store.sync_builtin()  # 首次启动自动导入内置人文库
        if res.get("added"):
            print(f"[拾光叙] 内置人文库入库 {len(res['added'])} 篇：{', '.join(res['added'])}")
    except Exception as exc:  # noqa: BLE001
        print(f"[拾光叙] 内置人文库导入失败：{exc}")
    yield


app = FastAPI(title="拾光叙 · 城市人文漫步 RAG 助手", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS + ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(knowledge.router)
app.include_router(chat.router)
app.include_router(route.router)
app.include_router(history.router)

QUOTES = [
    "一条老街，半城烟火。",
    "砖缝里藏着城市的年轮。",
    "走得慢一点，才听得见旧事。",
    "每座老建筑都是一封未寄的信。",
    "把脚步交给巷子，把故事交给时间。",
    "手艺人指尖的温度，是一座城的记忆。",
    "地名会变，传说不改。",
    "晨光爬上骑楼时，城市刚醒。",
    "生活不过是一半烟火，一半香火。",
    "泉州处处是文化，脚下皆是历史。",
    "谁知五柳孤松客，却住三坊七巷间。",
    "君到姑苏见，人家尽枕河。",
    "一条平江路，半座姑苏城。",
    "坊之多而知风化之美，巷之多而知民居之密。",
    "潮州厝，皇宫起。",
    "看到东西塔，就像看到家的方向。",
    "廊廊相接，一路走来，既避雨又遮阳。",
    "一砖一瓦承载千年文脉，一言一诺彰显信义力量。",
]


@app.get("/")
def root():
    return {"name": "拾光叙", "docs": "/docs", "status": "running"}


@app.get("/api/health")
def health():
    store = get_store()
    return {
        "status": "ok",
        "deepseek_configured": bool(config.DEEPSEEK_API_KEY),
        "model": config.DEEPSEEK_MODEL,
        **store.stats(),
    }


@app.get("/api/quotes")
def quotes(n: int = 8):
    return {"quotes": random.sample(QUOTES, k=min(n, len(QUOTES)))}
