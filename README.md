# 拾光叙 · 城市人文漫步 RAG 助手

> 一个面向大学生 Citywalk 与城市研学的城市人文知识问答系统：把老街的砖、手艺人的手、老人的口述收进一座可以检索的记忆库，让每一次提问都有出处。

- **参赛赛道**：传智杯 · RAG 知识问答赛道
- **作品形态**：Web 应用（前后端分离）+ 单文件离线版
- **核心能力**：内置人文档案检索、带引用的问答、Citywalk 路线生成、城市档案页、本地上传建档

---

## 一、项目介绍

### 1.1 要解决的问题

Citywalk 与城市研学正在成为大学生认识城市的主要方式，但真实场景里普遍存在三个困难：

1. **资料散**。一条老街的历史可能分散在政府门户、景区官网、地方志摘录和新闻报道里，出发前检索成本极高。
2. **讲解浅**。现场看到的只是"红砖厝""骑楼""燕尾脊"这些名词，缺少"为什么这样做"的解释。
3. **AI 会编**。直接问通用大模型，年代、人物、典故经常张冠李戴，而人文研学最不能容忍事实错误。

### 1.2 我们的回答

「拾光叙」把公开的文史资料整理成结构化档案，用 **RAG（检索增强生成）** 把"资料原文"作为唯一事实来源：

- 先检索，再生成：模型只能基于命中的资料片段组织语言；
- 每句话可回溯：回答中的 `[1] [2]` 编号对应具体文档与片段；
- 没有就说没有：资料未收录时明确回"未记载"，不替城市编故事；
- 没有 Key 也能用：**游客模式**直接返回资料原文，零模型调用、零编造。

### 1.3 功能一览

| 模块 | 说明 |
|---|---|
| 首页 | 纵向长海报：主视觉 → 序 → 三十城人文档案 → 影像短片 → 能力 → 现场影像志 → 开始 |
| 知识库 | 37 篇内置档案（30 座名城古街 + 7 篇专题通识）、分类筛选、上传自有 txt/md/pdf/docx |
| 漫步对话 | 混合检索 + 流式生成 + 来源原文展开，支持指定文档范围与召回条数 |
| 路线生成 | 按城市 / 主题 / 时长 / 节奏生成路线，落脚点编号落图，可直接复制打卡文案 |
| 城市档案 | 大图页头、看点清单、档案正文（约 1.5–2 千字）、漫步建议、同区域推荐 |
| 历史记录 | 每次问答与每次生成自动归档，可展开、检索、导出、删除 |
| 随行向导 | 常驻底部胶囊，短句轮播，点击展开为对话面板 |
| 模型接入 | 支持绑定自己的 API Key（OpenAI 兼容），未绑定则进入游客模式 |
| 离线版 | `发布版/拾光叙-海报网页.html`，双击即开，图片、视频、地图库全部内联 |

### 1.4 目录结构

```
01-代码仓库/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── config.py         # 环境变量、路径、常量
│   │   ├── main.py           # 应用入口、生命周期、CORS
│   │   ├── schemas.py        # 请求/响应模型
│   │   ├── history.py        # 历史记录读写
│   │   ├── llm/deepseek.py   # 提示词、上下文拼装、SSE 流式调用
│   │   ├── rag/              # 切片、向量、BM25、混合检索、内置库
│   │   └── routers/          # knowledge / chat / route / history
│   ├── .env.example          # 环境变量模板（复制为 .env）
│   ├── requirements.txt      # Python 依赖清单
│   └── run.py
├── frontend/                 # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── views/            # 首页、知识库、对话、路线、历史、城市档案
│   │   ├── components/       # 导航、页脚、胶囊、来源列表、Key 弹窗等
│   │   ├── map/              # MapLibre 地图组件与坐标换算
│   │   ├── api/index.js      # 请求封装与本地 Key 管理
│   │   └── router/index.js
│   ├── public/               # 城市配图（WebP）、短片与五段景点视频
│   ├── package.json          # 前端依赖清单
│   └── vite.config.js
├── 内置人文库/                # 37 篇 Markdown 文史档案（检索语料）
├── 示例资料/                  # 可直接上传的示例文件
├── 网页导出/                  # 单文件网页导出脚本、坐标抓取脚本、模板
├── 发布版/                    # 构建产物：单文件网页（双击即开）
├── docs/全站文案总表.md        # 全站文字导出，便于评审对照
├── start.bat                 # Windows 一键启动
├── .gitignore
└── README.md
```

---

## 二、技术架构

### 2.1 总体架构

```
┌──────────────────────────── 浏览器 ────────────────────────────┐
│  Vue 3 单页应用（Vite 构建）                                     │
│  首页 / 知识库 / 漫步对话 / 路线生成 / 历史记录 / 城市档案         │
│  MapLibre GL 地图 · 灵动岛胶囊 · 本地 Key 管理（localStorage）      │
└───────────────┬──────────────────────────────┬─────────────────┘
                │ REST + SSE                    │ 直连（可选）
                ▼                               ▼
┌──────────────────────────────┐      ┌────────────────────────┐
│ FastAPI 服务（:8000）          │      │ OpenAI 兼容大模型接口    │
│  routers: knowledge/chat/      │      │ DeepSeek / Moonshot /  │
│           route/history        │      │ 通义 / 本地 vLLM        │
│  ┌──────────────────────────┐  │      └────────────────────────┘
│  │ RAG 管线                  │  │
│  │ 切片 → 向量 → BM25 → 融合  │  │
│  │ FAISS / NumPy + hashing   │  │
│  └──────────────────────────┘  │
│  数据：37 篇 Markdown + JSON   │
└──────────────────────────────┘
```

### 2.2 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| 前端框架 | Vue 3（Composition API） | 上手快、单文件组件适合海报式长页面；构建体积小 |
| 构建工具 | Vite 5 | 冷启动快，`base: './'` 便于静态托管 |
| 地图 | MapLibre GL JS | 开源无 Key，可整体内联进单文件版；高德瓦片做底图 |
| 后端框架 | FastAPI | 原生异步、自动生成 OpenAPI 文档，SSE 流式返回实现简单 |
| 向量检索 | FAISS（Linux/macOS）+ NumPy 回退（Windows） | FAISS 快；Windows 下 pip 安装受限，自动降级不阻塞部署 |
| 关键词检索 | 自研 BM25（k1=1.5，b=0.75） | 中文专有名词、地名命中稳定，弥补纯语义检索的偏差 |
| 切片 | LangChain `RecursiveCharacterTextSplitter` 或同策略自研 | 按段落/句号递归切分，保留上下文边界 |
| 生成模型 | DeepSeek Chat（OpenAI 兼容） | 中文人文表达自然、价格低；兼容层允许换任意同类模型 |
| 数据存储 | JSON 元数据 + `.npy` 向量 + 文件系统 | 单机演示零依赖，评审无需装数据库 |

### 2.3 关键数据流

**问答**：问题 → 混合检索（向量 + BM25）→ 归一化加权融合 → Top-K 片段 → 组装提示词（含来源编号）→ 流式生成 → SSE 推送 `delta` → 结束后写历史 → 前端渲染 Markdown 与来源列表。

**路线**：表单（城市/主题/时长/节奏）→ 检索相关史料 → 路线提示词（要求只使用资料中真实地点）→ 流式生成 → 按标题匹配城市看点坐标 → 地图编号落点。

### 2.4 接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/knowledge/categories` | 分类及计数 |
| GET | `/api/knowledge/stats` | 文档数、片段数、向量后端 |
| GET | `/api/knowledge/cities` | 30 座城市档案（含看点坐标） |
| GET | `/api/knowledge/cities/{id}` | 单城完整档案（含正文章节） |
| POST | `/api/knowledge/upload` | 上传 txt/md/pdf/docx 并建索引 |
| GET/PATCH/DELETE | `/api/knowledge/docs...` | 文档列表、重命名、删除、清空 |
| POST | `/api/chat/stream` | SSE 流式问答（`sources` / `delta` / `done` / `error`） |
| POST | `/api/chat/retrieve` | 仅检索，返回片段（调试用） |
| POST | `/api/route/stream` | SSE 流式生成路线 |
| GET/POST/DELETE | `/api/history` | 历史记录读写 |

服务启动后可在 `http://127.0.0.1:8000/docs` 查看自动生成的交互式接口文档。

---

## 三、安装运行指南

### 3.1 环境要求

| 项 | 版本 |
|---|---|
| Python | 3.10+（开发使用 3.11） |
| Node.js | 18+（开发使用 20/22） |
| 操作系统 | Windows 10/11、macOS、Linux |
| 浏览器 | Chrome / Edge 100+（需支持 SSE 与 WebGL） |

### 3.2 环境变量

后端所有配置通过环境变量注入，**仓库内不含任何真实密钥**：

```bash
cd backend
cp .env.example .env     # Windows: copy .env.example .env
```

`.env` 各项含义：

| 变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | 否 | 空 | 为空则进入游客模式，仅返回资料原文 |
| `DEEPSEEK_BASE_URL` | 否 | `https://api.deepseek.com` | OpenAI 兼容地址 |
| `DEEPSEEK_MODEL` | 否 | `deepseek-chat` | 模型名 |
| `EMBEDDING_PROVIDER` | 否 | `auto` | `auto` / `local` / `api` |
| `EMBEDDING_BASE_URL` | 否 | 空 | `api` 模式下的 `/embeddings` 地址 |
| `EMBEDDING_API_KEY` | 否 | 空 | 向量服务密钥 |
| `EMBEDDING_MODEL` | 否 | `BAAI/bge-m3` | 向量模型名 |
| `EMBEDDING_DIM` | 否 | `1024` | 向量维度 |

> 说明：`auto` 会优先尝试本地句向量模型，不可用时自动降级为内置 hashing 向量 + BM25，**不填任何 Key 也能完整跑通检索链路**。

### 3.3 依赖清单

- Python：见 `backend/requirements.txt`（fastapi、uvicorn、httpx、numpy、python-dotenv、pypdf、python-docx、langchain-text-splitters；FAISS 仅在非 Windows 平台安装）
- 前端：见 `frontend/package.json`（运行依赖 vue、vue-router、markdown-it、maplibre-gl；开发依赖 vite、@vitejs/plugin-vue）

### 3.4 启动

**方式一：一键启动（Windows）**

双击根目录 `start.bat`。脚本会检测前端依赖，缺失时自动 `npm install`，随后分别启动后端与前端。

**方式二：手动启动**

```bash
# 后端
cd backend
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run.py                                        # http://127.0.0.1:8000

# 前端（另开终端）
cd frontend
npm install
npm run dev                                          # http://localhost:5173
```

首次启动会自动把 `内置人文库/` 的 37 篇档案切片入库，并打印入库结果；索引与元数据写在 `backend/app/data/`（该目录为运行时产物，已被 `.gitignore` 排除）。

**方式三：离线演示**

直接双击 `发布版/拾光叙-海报网页.html`。该文件把 CSS、JS、30 张城市配图、6 段视频与 MapLibre 全部内联，不依赖服务；问答使用内置档案的本地检索。

### 3.5 常见问题

| 现象 | 处理 |
|---|---|
| 回答以「游客模式」开头 | 没有配置 `DEEPSEEK_API_KEY`，属预期行为；在页面「API」入口或 `.env` 配置即可 |
| Windows 下 FAISS 安装失败 | `requirements.txt` 已用环境标记跳过 Windows，自动使用 NumPy 向量检索 |
| 地图空白 | 底图瓦片需联网；断网时自动切换为路线示意图 |
| 上传 PDF 报错 | 确认文件小于 20MB 且为文本型 PDF（扫描件需先 OCR） |

---

## 四、代码规范

- **Python**：遵循 PEP 8，4 空格缩进，类型注解 + `from __future__ import annotations`；模块顶部写职责说明；关键算法（切分、融合权重、降级策略）均有中文注释说明"为什么这样做"。
- **前端**：Vue 3 单文件组件，`<script setup>` 与 Options API 按文件既有风格保持一致；组件命名 PascalCase，样式使用 scoped 与 CSS 变量统一色板。
- **命名**：Python 模块小写下划线，Vue 组件大驼峰，接口路径小写复数。
- **提交**：Conventional Commits 风格（`feat:` / `fix:` / `docs:` / `chore:`），一次提交只做一件事。
- **安全**：密钥只走环境变量或浏览器本地存储，仓库内仅保留 `.env.example` 模板。

---

## 五、团队信息

> 请队长在提交前补齐下表（评审核对用）。

| 项 | 内容 |
|---|---|
| 队伍名称 | （待填写） |
| 参赛学校 | （待填写） |
| 团队成员 | （待填写：姓名 / 年级专业 / 分工） |
| 指导教师 | （待填写） |
| 联系方式 | （待填写：手机 / 邮箱） |

**分工建议模板**

| 成员 | 负责内容 |
|---|---|
| 成员 A | RAG 管线、后端接口、提示词与评测 |
| 成员 B | 前端页面、地图与交互、单文件导出 |
| 成员 C | 文史资料整理、文案撰写、测试与文档 |

---

## 六、文档与素材说明

- **技术文档**：《拾光叙-技术文档.pdf》，26 页，含需求分析、架构、AI 方案、核心实现、测试部署、创新点；按大赛要求与技术文档分开提交，不存放在本仓库内。
- **全站文案**：`docs/全站文案总表.md`，与页面逐字一致，便于对照评审。
- **图片来源**：城市配图与视频来自 Pexels 免费商用素材库，为氛围示意，非对应街区实拍。
- **文史资料**：整理自各地政府门户、官方景区与主流媒体报道，各篇篇末标注出处；年代与数量存在不同口径时并列说明。
- **地图数据**：底图 © 高德地图，数据 © OpenStreetMap contributors；坐标经 Photon 地理编码，仅用于示意走线。
