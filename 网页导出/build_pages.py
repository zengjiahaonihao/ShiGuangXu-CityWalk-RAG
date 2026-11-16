"""生成「拾光叙」多页面海报网页（单文件 HTML，双击即开）。

与旧版的区别：导航点击是**切换页面**，而不是滚动到首页的某个锚点。
五个页面各自有独立的内容介绍：首页 / 知识库 / 漫步对话 / 路线生成 / 历史记录。

城市档案数据直接来自 backend/app/rag/builtin.py，保证与后端一致；
所有配图（主视觉 + 六城 + 七区域）内联为 base64，无需外部资源。
"""
from __future__ import annotations

import ast
import base64
import os
import io
import json
import pathlib
import re

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "frontend" / "public"
CITY_DIR = PUBLIC / "cities"
TPL = ROOT / "网页导出" / "poster_template.html"
OUT = pathlib.Path(os.getenv("SGX_OUT") or (ROOT / "拾光叙-海报网页.html"))

# ---------------------------------------------------------------- 图片编码
_cache: dict[str, str] = {}


def encode(rel: str, max_w: int, quality: int) -> str:
    if rel in _cache:
        return _cache[rel]
    src = PUBLIC / rel.lstrip("/")
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if w > max_w:
        im = im.resize((max_w, int(h * max_w / w)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=quality, method=6)
    data = buf.getvalue()
    uri = "data:image/webp;base64," + base64.b64encode(data).decode("ascii")
    _cache[rel] = uri
    print(f"  {rel}: {w}x{h} -> {im.size[0]}x{im.size[1]}, {len(data) / 1024:.0f} KB")
    return uri


# ---------------------------------------------------------------- 读取城市档案
def load_profiles() -> list[dict]:
    src = (ROOT / "backend" / "app" / "rag" / "builtin.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in tree.body:
        target = None
        if isinstance(node, ast.AnnAssign):
            target = getattr(node.target, "id", None)
            value = node.value
        elif isinstance(node, ast.Assign) and node.targets:
            target = getattr(node.targets[0], "id", None)
            value = node.value
        else:
            continue
        if target == "CITY_PROFILES":
            return ast.literal_eval(value)
    raise RuntimeError("未能从 builtin.py 解析出 CITY_PROFILES")


def load_sections(doc_name: str) -> list[dict]:
    """把内置档案 Markdown 拆成 [{h, items}]，与后端 city_sections 保持一致。"""
    path = ROOT / "内置人文库" / doc_name
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    sections: list[dict] = []
    cur = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            cur = {"h": line[3:].strip(), "items": []}
            sections.append(cur)
        elif line.startswith("# ") or line.startswith(">") or line.strip() in ("", "---"):
            continue
        elif cur is not None:
            t = re.sub(r"^[-*]\s+", "", line.strip()).replace("**", "")
            t = re.sub(r"\[\d+\]", "", t)
            t = re.sub(r"\s{2,}", " ", t).strip()
            if len(t) >= 4 and (not cur["items"] or cur["items"][-1] != t):
                cur["items"].append(t)
    return [{"h": x["h"], "items": x["items"][:6]} for x in sections if x["items"]]


def main() -> None:
    tpl = TPL.read_text(encoding="utf-8")
    m = re.search(r"<style>(.*?)</style>", tpl, re.S)
    base_css = m.group(1) if m else ""

    print("读取城市档案：")
    profiles = load_profiles()
    print(f"  共 {len(profiles)} 座名城")

    print("内联图片：")
    poster = encode("/poster.jpg", 1500, 72)

    img_keys: dict[str, str] = {}
    for p in profiles:
        rel = p["image"]
        key = rel.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        if key not in img_keys:
            img_keys[key] = encode(rel, 760, 72)

    # 城市数据（图片用 key 引用）
    coords = {}
    coords_file = ROOT / "backend" / "app" / "data" / "spot_coords.json"
    if coords_file.exists():
        coords = json.loads(coords_file.read_text(encoding="utf-8"))
        print(f"  坐标：{sum(len(v.get('spots', [])) for v in coords.values())} 处看点")

    cities = []
    for p in profiles:
        key = p["image"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        c = coords.get(p["id"]) or {}
        cities.append(
            {
                "id": p["id"],
                "city": p["city"],
                "district": p["district"],
                "region": p["region"],
                "title": p["title"],
                "subtitle": p["subtitle"],
                "summary": p["summary"],
                "tags": p["tags"][:4],
                "highlights": p["highlights"],
                "walk": p["walk"],
                "img": key,
                "spots": c.get("spots") or [],
                "center": c.get("center"),
                "sections": load_sections(p["doc"]),
            }
        )

    regions = []
    for p in profiles:
        if p["region"] not in regions:
            regions.append(p["region"])

    payload = json.dumps({"cities": cities, "regions": regions}, ensure_ascii=False)
    imgs_json = json.dumps(img_keys, ensure_ascii=False)

    # 地图库：直接内联 maplibre-gl，保证双击打开、断网也能出图（瓦片仍需联网）
    map_css = ""
    map_js = ""
    dist = ROOT / "frontend" / "node_modules" / "maplibre-gl" / "dist"
    if (dist / "maplibre-gl.js").exists():
        map_css = (dist / "maplibre-gl.css").read_text(encoding="utf-8")
        map_js = (dist / "maplibre-gl.js").read_text(encoding="utf-8")
        map_js = map_js.replace("</script", "<\\/script")
        print(f"  地图库内联：{len(map_js) / 1024:.0f} KB")
    else:
        print("  ! 未找到 maplibre-gl，地图将退化为示意图")

    vid = ROOT / "frontend" / "public" / "story.mp4"
    video_uri = ""
    if vid.exists():
        b64 = base64.b64encode(vid.read_bytes()).decode("ascii")
        video_uri = "data:video/mp4;base64," + b64
        print(f"  短片内联：{len(video_uri) / 1024:.0f} KB")

    html = DOC.replace("__BASE_CSS__", base_css)
    html = html.replace("__VIDEO__", video_uri)

    vids_dir = ROOT / "frontend" / "public" / "videos"
    META = [
        ("dali.mp4", "大理 · 古城楼", "DALI · YUNNAN", True),
        ("zhujiajiao.mp4", "朱家角 · 水巷", "SHANGHAI · WATER TOWN", False),
        ("temple.mp4", "闽南 · 古寺门", "MINNAN · TEMPLE", False),
        ("hangzhou.mp4", "杭州 · 夜市灯影", "HANGZHOU · NIGHT MARKET", False),
        ("guangzhou.mp4", "广州 · 骑楼街", "GUANGZHOU · ARCADE", False),
    ]
    vids = []
    for name, title, city, big in META:
        f = vids_dir / name
        if not f.exists():
            print(f"  ! 缺少视频 {name}")
            continue
        b64 = base64.b64encode(f.read_bytes()).decode("ascii")
        vids.append({"src": "data:video/mp4;base64," + b64, "title": title, "city": city, "big": big})
    print(f"  影像志：{len(vids)} 段")
    html = html.replace('"__VIDS__"', json.dumps(vids, ensure_ascii=False))
    html = html.replace("__MAP_CSS__", map_css)
    html = html.replace("__MAP_JS__", map_js)
    html = html.replace("__POSTER__", poster)
    html = html.replace('"__IMGS__"', imgs_json)
    html = html.replace('"__DATA__"', payload)

    left = len(re.findall(r"__[A-Z_]+__", html))
    if left:
        print(f"  ! 仍有 {left} 个占位符未替换")

    OUT.write_text(html, encoding="utf-8")
    print(f"written: {OUT}  ({OUT.stat().st_size / 1024 / 1024:.2f} MB)")


# ---------------------------------------------------------------- 页面模板
DOC = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>拾光叙 · 城市人文漫步 RAG 助手</title>
<style>
__BASE_CSS__
__MAP_CSS__

/* ============ 多页面切换 ============ */
.page { display: none; }
.page.is-on { display: block; animation: pageIn .5s var(--ease-soft) both; }
@keyframes pageIn { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
a.link { cursor: pointer; }

/* ============ 页头 PageHero ============ */
.ph { position: relative; min-height: 46vh; display: flex; align-items: flex-end;
  overflow: hidden; background: #241a12; color: #f8f1e2; border-bottom: 1px solid var(--line); }
.ph-bg { position: absolute; inset: 0; }
.ph-bg img { width: 100%; height: 100%; object-fit: cover; display: block;
  filter: saturate(.82) contrast(1.05); transform: scale(1.04); }
.ph-scrim { position: absolute; inset: 0;
  background: linear-gradient(90deg, rgba(24,17,10,.86) 0%, rgba(24,17,10,.6) 40%, rgba(24,17,10,.28) 72%, rgba(24,17,10,.42) 100%),
              linear-gradient(180deg, rgba(24,17,10,.5) 0%, rgba(24,17,10,0) 34%),
              linear-gradient(0deg, rgba(22,16,9,.7) 0%, rgba(22,16,9,0) 56%); }
.ph-inner { position: relative; z-index: 2; width: 100%; max-width: 1180px;
  margin: 0 auto; padding: 150px 48px 56px; }
.ph-no { display: flex; align-items: baseline; gap: 16px; margin: 0 0 18px; }
.ph-num { font-family: var(--font-mono); font-size: 11px; letter-spacing: .26em; color: var(--seal-soft); }
.ph-en { font-family: var(--font-mono); font-size: 9.5px; letter-spacing: .4em; color: rgba(248,241,226,.5); }
.ph-cn { margin: 0; font-size: clamp(34px, 5.4vw, 66px); letter-spacing: .16em;
  font-weight: 500; color: #fdf8ec; text-shadow: 0 10px 40px rgba(18,12,7,.5); }
.ph-rule { width: 78px; margin: 22px 0; background: rgba(248,241,226,.45); }
.ph-lead { margin: 0; max-width: 640px; font-size: 13.5px; line-height: 2.1;
  letter-spacing: .12em; color: rgba(248,241,226,.82); }
.ph-meta { display: flex; flex-wrap: wrap; gap: 40px; margin: 34px 0 0; padding: 0; list-style: none; }
.ph-meta li { display: flex; flex-direction: column; gap: 4px; }
.ph-meta b { font-family: var(--font-serif); font-size: 22px; font-weight: 500; color: #fdf8ec; }
.ph-meta span { font-family: var(--font-mono); font-size: 9px; letter-spacing: .3em; color: rgba(248,241,226,.55); }
.ph-seal { position: absolute; right: 56px; bottom: 56px; z-index: 2; width: 54px; height: 54px;
  display: flex; align-items: center; justify-content: center; font-family: var(--font-serif);
  font-size: 24px; color: #fdf3e5; border: 1.5px solid rgba(178,46,38,.85);
  background: rgba(178,46,38,.28); transform: rotate(-3deg); }

/* ============ 内容块通用 ============ */
.blk { max-width: 1180px; margin: 0 auto; padding: 0 48px; }
.blk-head { display: flex; align-items: baseline; justify-content: space-between; gap: 16px;
  margin: 64px 0 28px; padding-bottom: 16px; border-bottom: 1px solid var(--line); }
.blk-head h2 { margin: 0; font-family: var(--font-serif); font-size: 26px;
  letter-spacing: .14em; font-weight: 500; }
.blk-head span { font-family: var(--font-mono); font-size: 10px; letter-spacing: .24em; color: var(--muted-2); }
.region-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 30px; }
.rtab { font-family: var(--font-mono); font-size: 10.5px; letter-spacing: .16em;
  padding: 7px 14px; border: 1px solid var(--line); background: transparent;
  color: var(--muted); cursor: pointer; transition: all .35s var(--ease-soft); }
.rtab:hover { border-color: var(--seal-soft); color: var(--seal); }
.rtab.on { background: var(--ink); border-color: var(--ink); color: var(--paper-light); }
.note { font-family: var(--font-mono); font-size: 10.5px; line-height: 2;
  letter-spacing: .06em; color: var(--muted-2); margin: 34px 0 0; }

/* ============ 对话演示 ============ */
.talk { border: 1px solid var(--line); background: var(--paper-light); }
.msg { display: flex; gap: 18px; padding: 26px 30px; border-bottom: 1px solid var(--line-soft); }
.msg:last-child { border-bottom: 0; }
.avatar { flex: none; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center;
  font-family: var(--font-serif); font-size: 14px; border: 1px solid var(--line); color: var(--muted); }
.msg.ai .avatar { background: var(--ink); color: var(--paper-light); border-color: var(--ink); }
.bubble { flex: 1; min-width: 0; }
.bubble p { margin: 0 0 10px; font-size: 13.5px; line-height: 2; color: var(--ink-soft); }
.bubble p:last-child { margin-bottom: 0; }
.bubble b { color: var(--ink); font-weight: 500; }
.cite { display: inline-block; font-family: var(--font-mono); font-size: 9.5px;
  color: var(--seal); margin: 0 2px; vertical-align: super; }
.srcs { margin-top: 16px; border-top: 1px dashed var(--line); padding-top: 14px; }
.srcs h4 { margin: 0 0 10px; font-family: var(--font-mono); font-size: 9.5px;
  letter-spacing: .26em; color: var(--muted-2); font-weight: 400; }
.src-item { display: flex; gap: 10px; font-size: 11.5px; line-height: 1.9; color: var(--muted); margin-bottom: 8px; }
.src-no { flex: none; font-family: var(--font-mono); color: var(--seal); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 26px; }
.chip { font-size: 12px; letter-spacing: .06em; padding: 8px 14px; border: 1px solid var(--line);
  color: var(--ink-soft); background: var(--paper-light); cursor: default; }

/* ============ 表单示意 / 路线 ============ */
.form-grid { display: grid; grid-template-columns: .8fr 1.2fr; gap: 40px; align-items: start; }
.field { border: 1px solid var(--line); padding: 22px 24px; background: var(--paper-light); }
.field + .field { margin-top: 0; }
.field label { display: block; font-family: var(--font-mono); font-size: 9.5px;
  letter-spacing: .24em; color: var(--muted-2); margin-bottom: 12px; }
.pills { display: flex; flex-wrap: wrap; gap: 7px; }
.pill { font-size: 11.5px; padding: 6px 12px; border: 1px solid var(--line); color: var(--muted); }
.pill.on { background: var(--seal); border-color: var(--seal); color: #fdf8ef; }
.route-out { border: 1px solid var(--line); background: var(--paper-light); padding: 30px 32px; }
.stops { list-style: none; margin: 0; padding: 0; }
.stops li { display: grid; grid-template-columns: 46px 1fr; gap: 18px; padding: 18px 0;
  border-bottom: 1px solid var(--line-soft); }
.stops li:last-child { border-bottom: 0; }
.stop-no { font-family: var(--font-mono); font-size: 11px; letter-spacing: .18em; color: var(--seal); padding-top: 3px; }
.stop-t { font-family: var(--font-serif); font-size: 16px; letter-spacing: .06em; margin: 0 0 6px; }
.stop-d { margin: 0; font-size: 12.5px; line-height: 1.95; color: var(--muted); }
.copy-box { margin-top: 22px; padding: 18px 20px; background: var(--paper);
  border-left: 2px solid var(--seal); font-size: 12.5px; line-height: 2; color: var(--ink-soft); }

/* ============ 记录 ============ */
.rec { border: 1px solid var(--line); background: var(--paper-light); margin-bottom: 18px; }
.rec-head { display: flex; align-items: center; gap: 16px; padding: 20px 26px; }
.rec-kind { flex: none; font-family: var(--font-mono); font-size: 9px; letter-spacing: .2em;
  padding: 3px 9px; border: 1px solid var(--seal-soft); color: var(--seal); }
.rec-t { flex: 1; font-family: var(--font-serif); font-size: 16px; letter-spacing: .06em; }
.rec-time { font-family: var(--font-mono); font-size: 10px; letter-spacing: .16em; color: var(--muted-2); }
.rec-body { padding: 0 26px 24px; font-size: 12.5px; line-height: 2; color: var(--muted);
  border-top: 1px dashed var(--line); padding-top: 18px; }

/* ============ 通识列表 ============ */
.gen-list { border-top: 1px solid var(--line); }
.gen-item { display: flex; align-items: baseline; gap: 18px; padding: 18px 0; border-bottom: 1px solid var(--line); }
.gen-no { flex: none; font-family: var(--font-mono); font-size: 10px; letter-spacing: .2em; color: var(--seal); }
.gen-t { font-family: var(--font-serif); font-size: 17px; letter-spacing: .06em; }
.gen-s { margin-left: auto; font-size: 11.5px; color: var(--muted-2); letter-spacing: .08em; }



/* 路线主题说明 */
.route-intro { margin: 0 0 18px; padding: 16px 18px; border-left: 2px solid var(--seal);
  background: var(--paper-light); }
.route-intro .ri-kicker { margin: 0 0 6px; font-family: var(--font-mono); font-size: 9.5px;
  letter-spacing: .18em; color: var(--seal); }
.route-intro .ri-text { margin: 0; font-size: 13px; line-height: 1.95; color: var(--ink-soft); }
.route-tips { margin: 16px 0 0; padding: 12px 16px; border: 1px dashed var(--line);
  font-size: 12px; line-height: 1.9; color: var(--muted); }
.route-tips b { font-family: var(--font-mono); font-size: 9.5px; letter-spacing: .16em;
  color: var(--ink); margin-right: 8px; }


/* ============ 视频弹层 ============ */
.vmodal { position: fixed; inset: 0; z-index: 1400; display: none; align-items: center;
  justify-content: center; padding: 24px; }
.vmodal.on { display: flex; }
.vmodal-bg { position: absolute; inset: 0; background: rgba(14,10,6,.86); backdrop-filter: blur(6px); }
.vmodal-box { position: relative; z-index: 2; width: min(1080px, 94vw); background: #14100b;
  border: 1px solid rgba(248,241,226,.18); box-shadow: 0 30px 80px rgba(0,0,0,.5); }
.vmodal-box video { display: block; width: 100%; max-height: 78vh; background: #000; }
.vmodal-cap { margin: 0; padding: 12px 18px; font-family: var(--font-mono); font-size: 10px;
  letter-spacing: .18em; color: rgba(248,241,226,.62); }
.vmodal-close { position: absolute; top: -44px; right: 0; width: 32px; height: 32px;
  border: 1px solid rgba(248,241,226,.4); background: transparent; color: #f8f1e2;
  font-size: 20px; line-height: 1; cursor: pointer; }
.vmodal-close:hover { background: var(--seal); border-color: var(--seal); }
.vid-card { cursor: zoom-in; }
.vid-card .vid-play { pointer-events: none; }


.auto-save { display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-mono);
  font-size: 9.5px; letter-spacing: .12em; color: var(--muted-2); }
.auto-save::before { content: ''; width: 5px; height: 5px; border-radius: 50%; background: var(--muted-2); }
.auto-save.on { color: var(--seal); }
.auto-save.on::before { background: var(--seal); }
.auto-save.flash { animation: saveFlash .9s var(--ease-soft); }
@keyframes saveFlash {
  0% { opacity: .2; transform: translateY(2px); }
  40% { opacity: 1; transform: translateY(0); }
  100% { opacity: 1; }
}

/* ============ 影像志 ============ */
.vid-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 34px; }
.vid-card { position: relative; margin: 0; overflow: hidden; border: 1px solid var(--line);
  background: #1b1510; min-height: 190px; cursor: pointer; }
.vid-card video { display: block; width: 100%; height: 100%; object-fit: cover;
  filter: saturate(.9) contrast(1.03); transition: transform .8s var(--ease-soft); }
.vid-card:hover video { transform: scale(1.04); }
.vid-card.big { grid-column: span 2; grid-row: span 2; min-height: 394px; }
.vid-cap { position: absolute; left: 0; right: 0; bottom: 0; padding: 30px 18px 14px;
  background: linear-gradient(0deg, rgba(18,13,8,.86) 0%, rgba(18,13,8,0) 100%);
  color: #f8f1e2; pointer-events: none; }
.vid-cap b { display: block; font-family: var(--font-serif); font-size: 16px;
  font-weight: 500; letter-spacing: .1em; }
.vid-cap span { display: block; margin-top: 3px; font-family: var(--font-mono); font-size: 9px;
  letter-spacing: .2em; color: rgba(248,241,226,.62); }
.vid-play { position: absolute; top: 14px; right: 14px; width: 34px; height: 34px;
  border-radius: 50%; border: 1px solid rgba(248,241,226,.5); background: rgba(18,13,8,.35);
  color: #f8f1e2; display: flex; align-items: center; justify-content: center;
  font-size: 11px; backdrop-filter: blur(6px); }
.vid-play::after { content: '▶'; }
.vid-card.playing .vid-play { background: var(--seal); border-color: var(--seal); }
.vid-card.playing .vid-play::after { content: 'Ⅱ'; }
@media (max-width: 900px) {
  .vid-grid { grid-template-columns: repeat(2, 1fr); }
  .vid-card.big { grid-column: span 2; grid-row: auto; min-height: 220px; }
}
@media (max-width: 560px) {
  .vid-grid { grid-template-columns: 1fr; }
  .vid-card.big { grid-column: auto; }
}

/* ============ 可交互控件 ============ */
.pill, .chip, .rtab, .rec-head, .city-card { cursor: pointer; }
.pill { transition: all .3s var(--ease-soft); }
.pill:hover { border-color: var(--seal-soft); color: var(--seal); }
.chip { transition: all .3s var(--ease-soft); }
.chip:hover { border-color: var(--seal-soft); color: var(--seal); }
.btn-ghost { font-family: var(--font-mono); font-size: 10.5px; letter-spacing: .16em;
  padding: 8px 16px; border: 1px solid var(--line); background: transparent; color: var(--ink);
  cursor: pointer; transition: all .3s var(--ease-soft); }
.btn-ghost:hover { background: var(--ink); border-color: var(--ink); color: var(--paper-light); }
.btn-ghost:disabled { opacity: .4; cursor: not-allowed; }
.btn-solid { font-family: var(--font-mono); font-size: 10.5px; letter-spacing: .18em;
  padding: 10px 20px; border: 1px solid var(--seal); background: var(--seal); color: #fdf8ef;
  cursor: pointer; transition: all .3s var(--ease-soft); }
.btn-solid:hover { background: #8f221c; border-color: #8f221c; }

/* 轻提示 */
.toast { position: fixed; left: 50%; bottom: 104px; transform: translateX(-50%) translateY(10px);
  z-index: 1200; padding: 10px 20px; background: rgba(23,20,15,.94); color: #f6f1e6;
  font-size: 12px; letter-spacing: .1em; opacity: 0; pointer-events: none;
  transition: all .35s var(--ease-soft); border: 1px solid rgba(246,241,230,.18); }
.toast.on { opacity: 1; transform: translateX(-50%) translateY(0); }

/* ============ 城市简介页 ============ */
.city-hero { position: relative; min-height: 58vh; display: flex; align-items: flex-end;
  overflow: hidden; background: #241a12; color: #f8f1e2; }
.city-hero img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;
  filter: saturate(.85) contrast(1.04); transform: scale(1.03); }
.city-hero .scrim { position: absolute; inset: 0;
  background: linear-gradient(90deg, rgba(24,17,10,.88) 0%, rgba(24,17,10,.55) 44%, rgba(24,17,10,.25) 76%, rgba(24,17,10,.45) 100%),
              linear-gradient(0deg, rgba(22,16,9,.72) 0%, rgba(22,16,9,0) 58%); }
.city-hero .inner { position: relative; z-index: 2; width: 100%; max-width: 1180px; margin: 0 auto;
  padding: 150px 48px 56px; }
.city-hero .back { display: inline-block; margin-bottom: 24px; font-family: var(--font-mono);
  font-size: 10px; letter-spacing: .2em; color: rgba(248,241,226,.66);
  border-bottom: 1px solid rgba(248,241,226,.24); padding-bottom: 4px; cursor: pointer; }
.city-hero .back:hover { color: #fdf8ec; }
.city-hero .kicker { font-family: var(--font-mono); font-size: 9.5px; letter-spacing: .3em;
  color: rgba(248,241,226,.6); margin: 0 0 14px; }
.city-hero h1 { margin: 0; font-family: var(--font-serif); font-size: clamp(38px, 5.6vw, 68px);
  letter-spacing: .12em; font-weight: 500; color: #fdf8ec; }
.city-hero h1 em { display: block; font-style: normal; font-size: .34em; letter-spacing: .28em;
  color: rgba(248,241,226,.74); margin-top: 14px; }
.city-hero .sub { margin: 16px 0 0; font-family: var(--font-serif); font-size: 15px;
  letter-spacing: .24em; color: rgba(248,241,226,.82); }
.city-hero .acts { display: flex; gap: 12px; margin-top: 32px; flex-wrap: wrap; }
.city-hero .acts button { font-family: var(--font-mono); font-size: 10.5px; letter-spacing: .16em;
  padding: 11px 20px; cursor: pointer; transition: all .3s var(--ease-soft); }
.city-hero .acts .primary { background: var(--seal); border: 1px solid var(--seal); color: #fdf6ee; }
.city-hero .acts .primary:hover { background: #8f221c; }
.city-hero .acts .plain { background: transparent; border: 1px solid rgba(248,241,226,.4); color: #f8f1e2; }
.city-hero .acts .plain:hover { border-color: #fdf8ec; }

.city-body { max-width: 1180px; margin: 0 auto; padding: 76px 48px 120px;
  display: grid; grid-template-columns: 1.5fr .85fr; gap: 64px; align-items: start; }
.city-lead { margin: 0; font-family: var(--font-serif); font-size: 20px; line-height: 2.05;
  letter-spacing: .04em; color: var(--ink); }
.city-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 24px; }
.city-tags span { font-size: 11.5px; letter-spacing: .1em; padding: 5px 12px;
  border: 1px solid var(--line); color: var(--muted); }
.city-h3 { margin: 52px 0 20px; padding-bottom: 14px; border-bottom: 1px solid var(--line);
  font-family: var(--font-serif); font-size: 20px; letter-spacing: .18em; font-weight: 500; }
.city-spots { list-style: none; margin: 0; padding: 0; }
.city-spots li { display: grid; grid-template-columns: 40px 1fr; gap: 14px; padding: 16px 0;
  border-bottom: 1px solid var(--line-soft); align-items: baseline; }
.city-spots .n { font-family: var(--font-mono); font-size: 11px; letter-spacing: .18em; color: var(--seal); }
.city-spots b { font-family: var(--font-serif); font-size: 16px; font-weight: 500; letter-spacing: .06em; }
.city-spots p { margin: 6px 0 0; font-size: 12.5px; line-height: 1.95; color: var(--muted); }
.city-facts { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--line);
  border: 1px solid var(--line); }
.city-facts div { background: var(--paper-light); padding: 18px 16px; display: flex; flex-direction: column; gap: 6px; }
.city-facts .k { font-family: var(--font-mono); font-size: 9px; letter-spacing: .2em; color: var(--muted-2); }
.city-facts b { font-family: var(--font-serif); font-size: 14px; font-weight: 500; }
.city-side { position: sticky; top: 110px; display: flex; flex-direction: column; gap: 18px; }
.city-side .card-s { border: 1px solid var(--line); background: var(--paper-light); padding: 20px 22px; }
.city-side .card-s h4 { margin: 0 0 14px; font-family: var(--font-mono); font-size: 9px;
  letter-spacing: .3em; color: var(--muted-2); font-weight: 400; }
.city-side .go-line { display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 10px 0; border: 0; border-bottom: 1px dashed var(--line);
  background: transparent; cursor: pointer; font-family: var(--font-serif); font-size: 13.5px;
  letter-spacing: .08em; color: var(--ink); text-align: left; }
.city-side .go-line:last-child { border-bottom: 0; }
.city-side .go-line span { color: var(--seal); }
.city-side .go-line:hover span { transform: translateX(4px); }
.city-side .poi { display: flex; align-items: center; gap: 8px; font-size: 12.5px;
  color: var(--ink-soft); padding: 5px 0; }
.city-side .poi i { width: 5px; height: 5px; border-radius: 50%; background: var(--seal); }


.city-read { border-top: 1px solid var(--line); }
.city-sec { padding: 24px 0 20px; border-bottom: 1px solid var(--line-soft); }
.city-sec h4 { display: flex; align-items: baseline; gap: 12px; margin: 0 0 12px;
  font-family: var(--font-serif); font-size: 17px; font-weight: 500; letter-spacing: .06em; color: var(--ink); }
.city-sec .sec-no { font-family: var(--font-mono); font-size: 10px; letter-spacing: .16em; color: var(--seal); }
.city-sec p { margin: 0 0 9px; font-size: 13.5px; line-height: 2.05; color: var(--ink-soft); text-align: justify; }
.city-sec p:last-child { margin-bottom: 0; }



/* ============ 接入模型 ============ */



/* ============ 接入模型 ============ */
.nav-api { display: inline-flex; align-items: center; gap: 7px; margin-left: 20px;
  padding: 6px 12px; border: 1px solid var(--line); background: transparent; cursor: pointer;
  transition: all .3s var(--ease-soft); }
.nav-api .na-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--muted-2); }
.nav-api.on .na-dot { background: var(--seal); box-shadow: 0 0 0 3px rgba(178,46,38,.16); }
.nav-api .na-txt { font-family: var(--font-mono); font-size: 9px; letter-spacing: .16em; color: var(--muted); }
.nav-api:hover { border-color: var(--seal-soft); }
.nav-api:hover .na-txt { color: var(--seal); }
.nav.on-top .nav-api { border-color: rgba(248,241,226,.32); }
.nav.on-top .nav-api .na-txt { color: rgba(248,241,226,.75); }
.nav.on-top .nav-api .na-dot { background: rgba(248,241,226,.45); }
.nav.on-top .nav-api.on .na-dot { background: #c2604f; }
.nav.on-top .nav-api:hover { border-color: rgba(248,241,226,.7); }

.llm-lead { margin: 0 0 18px; font-size: 13px; line-height: 2; color: var(--ink-soft); max-width: 760px; }
.llm-actions { display: flex; gap: 10px; }

.apim-box { position: relative; z-index: 2; width: min(560px, 94vw); max-height: 88vh; overflow-y: auto;
  background: var(--paper-light); border: 1px solid var(--line); padding: 26px 26px 22px;
  box-shadow: 0 30px 80px rgba(0,0,0,.35); }
.apim-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.apim-kicker { margin: 0 0 6px; font-family: var(--font-mono); font-size: 9px; letter-spacing: .3em; color: var(--seal); }
.apim-head h3 { margin: 0; font-family: var(--font-serif); font-size: 23px; font-weight: 500; letter-spacing: .06em; }
.apim-x { top: 0; right: 0; position: static; }
.apim-intro { margin: 16px 0 18px; font-size: 12.5px; line-height: 1.95; color: var(--muted); }
.apim-intro strong { color: var(--ink); font-weight: 500; }
.apim-field { display: flex; flex-direction: column; gap: 6px; flex: 1; }
.apim-field span { font-family: var(--font-mono); font-size: 9px; letter-spacing: .18em; color: var(--muted-2); }
.apim-field input { padding: 10px 12px; border: 1px solid var(--line); background: var(--paper);
  font-family: var(--font-mono); font-size: 12.5px; color: var(--ink); outline: none; }
.apim-field input:focus { border-color: var(--seal-soft); }
.apim-row { display: flex; gap: 12px; margin-top: 14px; }
.apim-hint { margin: 12px 0 0; font-size: 11.5px; line-height: 1.8; color: var(--muted-2); }
.apim-actions { display: flex; align-items: center; gap: 10px; margin-top: 18px; }
.apim-state { margin-left: auto; font-family: var(--font-mono); font-size: 9px; letter-spacing: .16em;
  padding: 4px 10px; border: 1px solid var(--line); color: var(--muted-2); }
.apim-state.on { color: var(--seal); border-color: var(--seal-soft); }
.apim-msg { margin: 12px 0 0; font-size: 12px; line-height: 1.9; color: var(--ink-soft); }
.apim-msg.err { color: #a33227; }
@media (max-width: 720px) { .apim-row { flex-direction: column; } .nav-api { margin-left: 8px; padding: 5px 8px; } }

/* ============ 上传档案 ============ */
.up-zone { display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 38px 24px; border: 1px dashed var(--line); background: var(--paper-light);
  cursor: pointer; transition: all .3s var(--ease-soft); text-align: center; }
.up-zone:hover, .up-zone.drag { border-color: var(--seal); background: rgba(178,46,38,.04); }
.up-zone .up-icon { font-family: var(--font-serif); font-size: 26px; color: var(--seal); line-height: 1; }
.up-zone b { font-family: var(--font-serif); font-size: 15px; letter-spacing: .08em; font-weight: 500; }
.up-zone span { font-size: 11.5px; color: var(--muted-2); letter-spacing: .04em; }
.up-list { display: flex; flex-direction: column; gap: 10px; margin-top: 18px; }
.up-item { display: flex; align-items: center; gap: 14px; padding: 14px 18px;
  border: 1px solid var(--line); background: var(--paper-light); }
.up-item .u-name { flex: 1; min-width: 0; font-family: var(--font-serif); font-size: 14px;
  letter-spacing: .04em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.up-item .u-meta { font-family: var(--font-mono); font-size: 9.5px; letter-spacing: .14em; color: var(--muted-2); }
.up-item .u-acts { display: flex; gap: 8px; }
.up-item .u-acts button { font-family: var(--font-mono); font-size: 9.5px; letter-spacing: .12em;
  padding: 5px 10px; border: 1px solid var(--line); background: transparent; color: var(--ink-soft);
  cursor: pointer; transition: all .25s; }
.up-item .u-acts button:hover { background: var(--ink); border-color: var(--ink); color: var(--paper-light); }
.up-empty { padding: 14px 2px; font-size: 12px; color: var(--muted-2); letter-spacing: .04em; }
.up-answer { margin-top: 16px; border-left: 2px solid var(--seal); padding: 12px 16px;
  background: var(--paper); font-size: 12.5px; line-height: 2; color: var(--ink-soft); display: none; }
.up-answer.on { display: block; }
.up-answer b { font-family: var(--font-mono); font-size: 9.5px; letter-spacing: .16em; color: var(--seal); display: block; margin-bottom: 6px; }

/* ============ 交互问答 ============ */
.ask-box { margin-top: 30px; border: 1px solid var(--line); background: var(--paper-light); }
.ask-row { display: flex; border-bottom: 1px solid var(--line-soft); }
.ask-row input { flex: 1; border: 0; background: transparent; padding: 16px 20px;
  font-family: var(--font-serif); font-size: 14px; letter-spacing: .06em; color: var(--ink); outline: none; }
.ask-row button { border: 0; border-left: 1px solid var(--line); background: var(--ink);
  color: var(--paper-light); padding: 0 26px; font-size: 12px; letter-spacing: .2em; cursor: pointer; }
.ask-row button:hover { background: var(--seal); }
.ask-hint { padding: 10px 20px; font-family: var(--font-mono); font-size: 9.5px;
  letter-spacing: .16em; color: var(--muted-2); }
.ask-thread { padding: 0 20px; }
.ask-thread .row { padding: 16px 0; border-bottom: 1px dashed var(--line-soft); }
.ask-thread .row:last-child { border-bottom: 0; }
.ask-thread .q { font-family: var(--font-serif); font-size: 14px; letter-spacing: .05em; color: var(--ink); }
.ask-thread .a { margin-top: 8px; font-size: 13px; line-height: 2; color: var(--ink-soft); }
.ask-thread .src { margin-top: 10px; font-family: var(--font-mono); font-size: 10px;
  letter-spacing: .1em; color: var(--seal); }

/* ============ 路线地图 ============ */
.map-box { position: relative; height: 460px; border: 1px solid var(--line);
  background: var(--paper-deep); overflow: hidden; margin-top: 26px; }
.map-box .map-fallback-svg { position: absolute; inset: 0; }
.map-box canvas { filter: saturate(.86) contrast(.98); }
.map-legend { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.map-legend button { display: flex; align-items: center; gap: 9px; padding: 8px 13px;
  border: 1px solid var(--line); background: var(--paper-light); cursor: pointer;
  font-size: 12px; color: var(--ink-soft); transition: all .3s var(--ease-soft); }
.map-legend button.on { border-color: var(--seal); background: rgba(178,46,38,.06); }
.map-legend .n { font-family: var(--font-mono); font-size: 10px; color: var(--seal); }
.map-credit { margin: 10px 0 0; font-family: var(--font-mono); font-size: 9px;
  letter-spacing: .12em; color: var(--muted-2); }
.map-badge { position: absolute; top: 12px; left: 12px; z-index: 3; padding: 6px 12px;
  background: rgba(246,241,230,.92); border: 1px solid var(--line); font-family: var(--font-mono);
  font-size: 9.5px; letter-spacing: .16em; color: var(--ink-soft); }
.route-generate { margin-top: 26px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.route-hint { font-size: 11.5px; color: var(--muted-2); }

/* ============ 记录交互 ============ */
.rec-head { cursor: pointer; }
.rec-arrow { font-family: var(--font-mono); font-size: 9.5px; letter-spacing: .16em; color: var(--muted-2); }
.rec-body { display: none; }
.rec.open .rec-body { display: block; }
.rec-tools { display: flex; gap: 8px; margin-top: 16px; }
.stats-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px;
  background: var(--line); border: 1px solid var(--line); margin-bottom: 26px; }
.stats-strip div { background: var(--paper-light); padding: 20px 22px; display: flex;
  flex-direction: column; gap: 6px; }
.stats-strip b { font-family: var(--font-serif); font-size: 26px; font-weight: 500; }
.stats-strip span { font-family: var(--font-mono); font-size: 9.5px; letter-spacing: .2em; color: var(--muted-2); }
.rec-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 22px; }
.rec-toolbar input { flex: 1; min-width: 200px; padding: 10px 14px; border: 1px solid var(--line);
  background: var(--paper-light); font-size: 12.5px; letter-spacing: .06em; color: var(--ink); outline: none; }
.rec-toolbar input:focus { border-color: var(--seal-soft); }

/* 地图标记与胶囊快捷问题 */
.exp-marker { width: 26px; height: 26px; border-radius: 50%; background: #b22e26;
  border: 2px solid #fdf8ec; box-shadow: 0 3px 10px rgba(0,0,0,.35); cursor: pointer;
  display: flex; align-items: center; justify-content: center; color: #fdf8ec;
  font-family: var(--font-mono); font-size: 11px; transition: transform .25s var(--ease-soft); }
.exp-marker:hover { transform: scale(1.18); }
.cap-chips { display: flex; flex-wrap: wrap; gap: 7px; padding: 4px 0 14px; }
.cap-chip { padding: 5px 11px; border: 1px solid rgba(23,20,15,.16); border-radius: 999px;
  background: transparent; font-size: 11px; color: var(--ink-soft); cursor: pointer; }
.cap-chip:hover { background: var(--ink); border-color: var(--ink); color: var(--paper-light); }
.btn-ghost.on { background: var(--ink); border-color: var(--ink); color: var(--paper-light); }

/* 胶囊内的消息气泡 */
.cap-msg { display: flex; gap: 10px; margin-bottom: 14px; font-size: 13px; line-height: 1.9; }
.cap-who { flex: none; width: 26px; height: 26px; display: flex; align-items: center;
  justify-content: center; font-family: var(--font-serif); font-size: 12px;
  background: var(--paper-deep); color: var(--muted); }
.cap-msg.ai .cap-who { background: var(--ink); color: var(--paper-light); }
.cap-text { flex: 1; min-width: 0; color: var(--ink-soft); white-space: pre-wrap; }
.cap-hint { flex: none; font-family: var(--font-mono); font-size: 8.5px; letter-spacing: .24em;
  color: rgba(246,241,230,.5); }

@media (max-width: 1024px) {
  .city-hero .inner { padding: 128px 28px 44px; }
  .city-body { grid-template-columns: 1fr; gap: 36px; padding: 52px 28px 90px; }
  .city-side { position: static; }
  .city-facts { grid-template-columns: repeat(2, 1fr); }
  .map-box { height: 360px; }
}

@media (max-width: 1024px) {
  .ph-inner { padding: 128px 28px 44px; }
  .ph-seal { right: 24px; bottom: 30px; width: 44px; height: 44px; font-size: 20px; }
  .blk { padding: 0 28px; }
  .form-grid { grid-template-columns: 1fr; gap: 26px; }
}
@media (max-width: 640px) {
  .ph-meta { gap: 24px; }
  .ph-meta b { font-size: 18px; }
  .msg { padding: 20px 18px; gap: 12px; }
  .gen-s { display: none; }
}
</style>
</head>
<body>

<!-- ======================= 导航 ======================= -->
<header class="nav" id="nav">
  <div class="nav-inner">
    <a class="brand" data-page="home">
      <span class="brand-cn">拾光叙</span>
      <span class="brand-en">SHIGUANGXU</span>
    </a>

    <nav class="links">
      <a class="link active" data-page="home"><span class="link-cn">首页</span><span class="link-en">Index</span></a>
      <a class="link" data-page="knowledge"><span class="link-cn">知识库</span><span class="link-en">Archive</span></a>
      <a class="link" data-page="chat"><span class="link-cn">漫步对话</span><span class="link-en">Dialogue</span></a>
      <a class="link" data-page="route"><span class="link-cn">路线生成</span><span class="link-en">Route</span></a>
      <a class="link" data-page="history"><span class="link-cn">历史记录</span><span class="link-en">Record</span></a>
    </nav>

    <button class="nav-api" id="apiOpen" title="绑定自己的 API Key">
      <span class="na-dot" id="apiDot"></span>
      <span class="na-txt" id="apiLabel">游客模式</span>
    </button>

    <button class="burger" id="burger" aria-label="打开菜单"><span></span><span></span></button>
  </div>

  <div class="mobile-menu" id="mobileMenu" style="display:none">
    <a class="mm-item" data-page="home"><span class="mm-no">01</span><span class="mm-cn">首页</span><span class="mm-en">Index</span></a>
    <a class="mm-item" data-page="knowledge"><span class="mm-no">02</span><span class="mm-cn">知识库</span><span class="mm-en">Archive</span></a>
    <a class="mm-item" data-page="chat"><span class="mm-no">03</span><span class="mm-cn">漫步对话</span><span class="mm-en">Dialogue</span></a>
    <a class="mm-item" data-page="route"><span class="mm-no">04</span><span class="mm-cn">路线生成</span><span class="mm-en">Route</span></a>
    <a class="mm-item" data-page="history"><span class="mm-no">05</span><span class="mm-cn">历史记录</span><span class="mm-en">Record</span></a>
    <a class="mm-item" id="apiOpenMobile"><span class="mm-no">06</span><span class="mm-cn">接入模型</span><span class="mm-en">Model Access</span></a>
  </div>
</header>

<main class="poster">

  <!-- ==================== 首页 ==================== -->
  <div class="page is-on" id="page-home">
    <section class="hero">
      <div class="hero-img"><img src="__POSTER__" alt="老街晨光" /></div>
      <div class="hero-scrim"></div>
      <div class="hero-content">
        <div class="hero-top">
          <p class="eyebrow">City Humanities Walk · RAG Assistant</p>
          <span class="tag seal">传智杯 · RAG 知识问答赛道</span>
        </div>
        <div class="hero-title">
          <h1 class="display hero-cn">拾光叙</h1>
          <div class="hero-sub"><hr class="rule" /><p>城市人文漫步 · 知识问答助手</p></div>
        </div>
        <div class="hero-bottom">
          <p class="hero-lead">把老街的砖、手艺人的手、老人的口述<br />收进一座可以检索的记忆库<span class="seal-dot">。</span></p>
          <div class="hero-meta">
            <span><b>RAG</b> 检索增强</span>
            <span><b>FAISS</b> 向量库</span>
            <span><b>DeepSeek</b> 生成</span>
          </div>
        </div>
      </div>
      <div class="hero-vertical">SHIGUANGXU — MEMORY OF STREETS</div>
      <div class="scroll-hint"><span>SCROLL</span><i></i></div>
    </section>

    <section class="section prelude">
      <div class="wrap">
        <p class="eyebrow reveal">02 — Prelude</p>
        <h2 class="display quote reveal">走得慢一点，<br />才听得见旧事<span class="seal-dot">。</span></h2>
        <div class="two-col reveal">
          <p>「拾光叙」为大学生的城市研学与 Citywalk 而生。你不只是路过一条街，而是带着问题走进它：这条巷子为什么叫这个名字，骑楼下的廊道为谁而建，那些还在营业的老铺子守着怎样的手艺。</p>
          <p>我们把答案的来源交还给你——所有解读都出自知识库里的文史资料，附原文可核对。资料里没有的，它会明说「未记载」，而不是替城市编一个漂亮的故事。</p>
        </div>
      </div>
    </section>

    <section class="section archive" id="archive">
      <div class="wrap">
        <header class="sec-head reveal">
          <p class="eyebrow">03 — Archive</p>
          <h2 class="display sec-title">全国人文档案，随项目自带</h2>
          <p class="sec-sub">不用先上传任何资料，也能立刻提问与生成路线：项目内置覆盖七大区域的名城古街文史档案，另有古建、非遗、运河、丝路等专题通识，全部整理自公开的政府门户、官方景区与主流媒体报道，并标注来源。</p>
        </header>
        <div class="region-tabs reveal" id="homeTabs"></div>
        <div class="city-gallery" id="homeGallery"></div>
        <p class="sec-note reveal">图片来自 Pexels 免费商用图库，仅作区域氛围示意，非对应街区实拍；文字资料均为公开来源整理，涉及年代与数量的不同口径已在各篇末并列说明。</p>
      </div>
    </section>

    <section class="section film">
      <div class="wrap">
        <header class="sec-head reveal">
          <p class="eyebrow">04 — Film</p>
          <h2 class="display sec-title">走一遍，才认得这座城</h2>
          <p class="sec-sub">四段街景，一镜到底。没有旁白，只有檐下的水声与灯笼的影子。</p>
        </header>
        <figure class="film-box reveal" id="film">
          <video src="__VIDEO__" autoplay muted loop playsinline controls preload="metadata"></video>
          <figcaption>短片由项目内城市影像剪成，仅作氛围示意 · 无声循环</figcaption>
        </figure>
      </div>
    </section>

    <section class="section caps">
      <div class="wrap">
        <header class="sec-head reveal">
          <p class="eyebrow">05 — Capabilities</p>
          <h2 class="display sec-title">它能做什么</h2>
        </header>
        <div class="cap-list">
          <article class="cap reveal">
            <span class="cap-no">01</span>
            <div class="cap-body">
              <h3 class="display cap-cn">人文档案库</h3>
              <p class="cap-en">ARCHIVE</p>
              <p class="cap-desc">内置三十座名城古街与七篇专题通识，开箱即可检索；也可以上传自己的老街史料、地方传说与非遗手记，自动切片建索引。</p>
            </div>
          </article>
          <article class="cap reveal">
            <span class="cap-no">02</span>
            <div class="cap-body">
              <h3 class="display cap-cn">有出处的回答</h3>
              <p class="cap-en">TRACEABLE ANSWERS</p>
              <p class="cap-desc">先检索命中资料片段，再交给 DeepSeek 组织语言；每条回答附来源与原文，可以逐句回溯核对，杜绝编造。</p>
            </div>
          </article>
          <article class="cap reveal">
            <span class="cap-no">03</span>
            <div class="cap-body">
              <h3 class="display cap-cn">Citywalk 路线</h3>
              <p class="cap-en">WALKING ROUTE</p>
              <p class="cap-desc">按城市、主题、时长与节奏生成人文漫步路线和打卡文案，路线里的每一个落脚点都出自资料本身。</p>
            </div>
          </article>
          <article class="cap reveal">
            <span class="cap-no">04</span>
            <div class="cap-body">
              <h3 class="display cap-cn">灵动岛随行向导</h3>
              <p class="cap-en">FLOATING GUIDE</p>
              <p class="cap-desc">页面常驻悬浮胶囊，常态一句人文短句，点击平滑舒展为对话面板，随时发问、流式作答。</p>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section class="section vids">
      <div class="wrap">
        <header class="sec-head reveal">
          <p class="eyebrow">06 — Moving Image</p>
          <h2 class="display sec-title">几段现场，替文字说话</h2>
          <p class="sec-sub">水乡的橹声、古寺檐下的光、夜市刚亮起的灯笼——有些东西写不出来，只能看一眼。</p>
        </header>
        <div class="vid-grid reveal" id="vidGrid"></div>
        <p class="note">影像来自 Pexels 免费商用视频，为氛围示意，非对应城市实拍；已压缩、无声循环播放。</p>
      </div>
    </section>

    <section class="section cta">
      <div class="wrap cta-inner reveal">
        <p class="eyebrow">07 — Begin</p>
        <h2 class="display cta-title">从第一份史料开始</h2>
        <div class="cta-actions">
          <a class="btn primary" data-page="knowledge">翻看人文档案</a>
          <a class="btn" data-page="chat">直接提问</a>
          <a class="btn" data-page="route">生成路线</a>
        </div>
      </div>
    </section>
  </div>

  <!-- ==================== 知识库 ==================== -->
  <div class="page" id="page-knowledge">
    <header class="ph">
      <div class="ph-bg"><img id="kHeroImg" src="" alt="" /></div>
      <div class="ph-scrim"></div>
      <div class="ph-inner">
        <p class="ph-no"><span class="ph-num">01</span><span class="ph-en">ARCHIVE</span></p>
        <h1 class="display ph-cn">知识库</h1>
        <hr class="rule ph-rule" />
        <p class="ph-lead">内置全国人文档案常驻可用：三十座名城古街、七篇专题通识，开箱即可提问。你也可以上传自己的老街史料、古建筑介绍、地方传说与非遗手记，与内置库一起参与检索。</p>
        <ul class="ph-meta">
          <li><b>39</b><span>DOCUMENTS</span></li>
          <li><b>324</b><span>CHUNKS</span></li>
          <li><b>FAISS</b><span>VECTOR</span></li>
        </ul>
      </div>
      <span class="ph-seal">拾</span>
    </header>

    <div class="section">
      <div class="blk">
        <div class="blk-head">
          <h2>内置人文档案</h2>
          <span>七大片区分组 · 公开资料整理</span>
        </div>
        <div class="region-tabs" id="kTabs"></div>
        <div class="city-gallery" id="kGallery"></div>
        <p class="note">文史档案整理自各地政府门户、官方景区与主流媒体报道，篇末均标注出处；配图取自 Pexels 免费商用图库，为区域氛围示意图，非对应街区的实拍。</p>
      </div>
    </div>

    <div class="section" id="upSec" style="padding-top: 0;">
      <div class="blk">
        <div class="blk-head">
          <h2>上传你的人文档案</h2>
          <span>本机保存 · 不会上传到服务器</span>
        </div>

        <div class="up-zone" id="upZone">
          <input type="file" id="upFile" accept=".txt,.md,.markdown,text/plain" multiple hidden />
          <div class="up-icon">＋</div>
          <b>拖入 txt / md，或点击选择</b>
          <span>支持多选；内容保存在这台电脑的浏览器里，刷新还在，可随时删除</span>
        </div>

        <div class="up-list" id="upList"></div>
        <div class="up-answer" id="upAnswer"></div>
        <p class="note" id="upNote">上传的档案会和内置三十城一起参与「我的档案」检索：在对话页或随行向导里提问时，会先搜你上传的内容。PDF / DOCX 请在完整版（FastAPI 后端）上传，会自动切片入库。</p>
      </div>
    </div>

    <div class="section" id="llmSec" style="padding-top: 0;">
      <div class="blk">
        <div class="blk-head">
          <h2>接入你自己的大模型</h2>
          <span id="llmState">游客模式</span>
        </div>

        <p class="llm-lead" id="llmLead">当前是游客模式：只用本站内置的 30 城档案检索作答，不调用任何模型，也不会编造。绑定自己的 API Key 后，回答由你的模型生成，Key 只存在这台电脑的浏览器里。</p>

        <div class="llm-actions">
          <button class="btn-solid" id="llmOpen">绑定我的 API Key</button>
          <button class="btn-ghost" id="llmClear">清除 Key</button>
        </div>

        <p class="note">支持 DeepSeek、Moonshot、通义、本地 vLLM 等任何 OpenAI 兼容接口；浏览器直连官方接口，不需要本地后端。若接口不允许跨域，会自动退回本站资料检索，不会中断对话。</p>
      </div>
    </div>

    <div class="section" style="background: var(--paper-light); padding-top: 0;">
      <div class="blk">
        <div class="blk-head">
          <h2>专题通识</h2>
          <span>不属任一城市 · 参与全局检索</span>
        </div>
        <div class="gen-list">
          <div class="gen-item"><span class="gen-no">G1</span><span class="gen-t">中国老街建筑语汇通识</span><span class="gen-s">骑楼 / 马鞍墙 / 燕尾脊 / 牌坊 / 双棋盘</span></div>
          <div class="gen-item"><span class="gen-no">G2</span><span class="gen-t">中国传统民居类型图谱</span><span class="gen-s">合院 / 窑洞 / 吊脚楼 / 土楼 / 碉房 / 一颗印</span></div>
          <div class="gen-item"><span class="gen-no">G3</span><span class="gen-t">中国古代都城营建</span><span class="gen-s">从里坊制到街巷制，中轴线与城墙体系</span></div>
          <div class="gen-item"><span class="gen-no">G4</span><span class="gen-t">中国非物质文化遗产概览</span><span class="gen-s">十大门类与 Citywalk 里的非遗</span></div>
          <div class="gen-item"><span class="gen-no">G5</span><span class="gen-t">线性文化遗产：运河、丝路与茶马古道</span><span class="gen-s">一条路如何串起一串城</span></div>
          <div class="gen-item"><span class="gen-no">G6</span><span class="gen-t">中国古桥与园林</span><span class="gen-s">梁桥拱桥索桥廊桥 · 叠山理水与借景框景</span></div>
          <div class="gen-item"><span class="gen-no">G7</span><span class="gen-t">历史文化名城与街区保护制度</span><span class="gen-s">三层体系、四条原则与四种更新模式</span></div>
        </div>
      </div>
    </div>
  </div>

  <!-- ==================== 漫步对话 ==================== -->
  <div class="page" id="page-chat">
    <header class="ph">
      <div class="ph-bg"><img id="cHeroImg" src="" alt="" /></div>
      <div class="ph-scrim"></div>
      <div class="ph-inner">
        <p class="ph-no"><span class="ph-num">02</span><span class="ph-en">DIALOGUE</span></p>
        <h1 class="display ph-cn">漫步对话</h1>
        <hr class="rule ph-rule" />
        <p class="ph-lead">带着问题走进一条街：先在资料里找到证据，再让模型把它讲成一段话。每条回答都附来源原文，可以逐句回溯核对；资料里没有的，它会明说「未记载」。</p>
      </div>
      <span class="ph-seal">拾</span>
    </header>

    <div class="section" style="padding-top: 70px;">
      <div class="blk">
        <div class="blk-head">
          <h2>一次真实的问答</h2>
          <span>检索 → 生成 → 附来源</span>
        </div>

        <div class="talk">
          <div class="msg">
            <span class="avatar">我</span>
            <div class="bubble"><p>日昇昌票号是哪一年创办的？它凭什么能「汇通天下」？</p></div>
          </div>
          <div class="msg ai">
            <span class="avatar">拾</span>
            <div class="bubble">
              <p>据资料记载，<b>清道光三年（1823 年）</b>，平遥商人<b>雷履泰</b>创办了中国第一家票号「<b>日昇昌</b>」<span class="cite">[1]</span>——也有文献记为道光四年（1824 年），两种说法在篇末并列。</p>
              <p>在票号出现之前，商人运银需要马车装载并雇保镖护送；票号发明了<b>汇票</b>：银子存进去，拿一张纸，走到全国任何一个分号都能取出来<span class="cite">[1]</span>。鼎盛时期平遥城内有二十多家票号，全国五百多个分号，业务在 19 世纪 40 年代扩展到日本、新加坡、俄罗斯等地，平遥因此被称为「<b>古代中国的华尔街</b>」<span class="cite">[2]</span>。</p>
              <div class="srcs">
                <h4>资料来源</h4>
                <div class="src-item"><span class="src-no">[1]</span><span>《平遥-明清古城.md》——四、日昇昌：中国第一家票号</span></div>
                <div class="src-item"><span class="src-no">[2]</span><span>《平遥-明清古城.md》——清代晚期总部设在平遥的票号就有二十多家，占全国一半以上</span></div>
              </div>
            </div>
          </div>
        </div>

        <div class="chips" id="chatChips">
          <span class="chip" data-q="平遥日昇昌票号是哪一年创办的？">日昇昌票号哪一年创办？</span>
          <span class="chip" data-q="骑楼为什么会有连续的廊道？">骑楼为什么有连续廊道？</span>
          <span class="chip" data-q="丽江古城为什么不设城墙？">丽江为什么不设城墙？</span>
          <span class="chip" data-q="赵州桥是谁设计的？">赵州桥是谁设计的？</span>
        </div>

        <div class="ask-box">
          <div class="ask-row">
            <input id="askInput" type="text" placeholder="追问一句：这条街的名字是怎么来的？" />
            <button id="askSend">提问</button>
          </div>
          <div class="ask-hint">演示版内置 6 组问答：命中即回完整答案与来源；其余问题会提示到「随行向导」里继续问。</div>
          <div class="ask-thread" id="askThread"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- ==================== 路线生成 ==================== -->
  <div class="page" id="page-route">
    <header class="ph">
      <div class="ph-bg"><img id="rHeroImg" src="" alt="" /></div>
      <div class="ph-scrim"></div>
      <div class="ph-inner">
        <p class="ph-no"><span class="ph-num">03</span><span class="ph-en">ROUTE</span></p>
        <h1 class="display ph-cn">路线生成</h1>
        <hr class="rule ph-rule" />
        <p class="ph-lead">先选一座城或一个主题，再挑几篇史料——路线里的每一个落脚点、每一段典故，都出自资料本身，文末附来源可核对。</p>
      </div>
      <span class="ph-seal">拾</span>
    </header>

    <div class="section" style="padding-top: 70px;">
      <div class="blk">
        <div class="blk-head">
          <h2>漫步设定</h2>
          <span>城市 · 主题 · 时长 · 节奏</span>
        </div>

        <div class="form-grid">
          <div>
            <div class="field">
              <label>城市</label>
              <div class="pills" id="routeCityPills"></div>
            </div>
            <div class="field" style="margin-top: 18px;">
              <label>主题</label>
              <div class="pills" id="routeThemePills"></div>
            </div>
            <div class="field" style="margin-top: 18px;">
              <label>时长 / 节奏 / 交通</label>
              <div class="pills" id="routeOptPills"></div>
            </div>
            <div class="route-generate">
              <button class="btn-solid" id="routeGo">生成路线</button>
              <span class="route-hint" id="routeHint"></span>
            </div>
          </div>

          <div class="route-out">
            <div class="stops" id="routeStops"></div>
            <div class="copy-box" id="routeCopy"></div>

            <div class="map-box" id="routeMap">
              <div class="map-badge" id="mapBadge">路线地图</div>
            </div>
            <div class="map-legend" id="mapLegend"></div>
            <p class="map-credit">底图 © 高德地图 · 数据 © OpenStreetMap contributors</p>

            <div class="rec-tools">
              <button class="btn-ghost" id="routeCopyBtn">复制打卡文案</button>
              <span class="auto-save" id="routeSaved">生成后自动存入历史记录</span>
            </div>
          </div>
        </div>

        <p class="note">示例路线由内置档案生成，实际使用时可指定任意城市与资料范围；路线中的地点、年代与典故均可回溯到原文片段。每生成一次路线都会自动存入历史记录，不必手动保存。</p>
      </div>
    </div>
  </div>

  <!-- ==================== 历史记录 ==================== -->
  <div class="page" id="page-history">
    <header class="ph">
      <div class="ph-bg"><img id="hHeroImg" src="" alt="" /></div>
      <div class="ph-scrim"></div>
      <div class="ph-inner">
        <p class="ph-no"><span class="ph-num">04</span><span class="ph-en">RECORD</span></p>
        <h1 class="display ph-cn">历史记录</h1>
        <hr class="rule ph-rule" />
        <p class="ph-lead">每一次提问、每一条路线都自动落档。展开可以回看当时的来源原文，也可以一键复制或导出成 Markdown 带走。</p>
      </div>
      <span class="ph-seal">拾</span>
    </header>

    <div class="section" style="padding-top: 70px;">
      <div class="blk">
        <div class="blk-head">
          <h2>最近的漫步</h2>
          <span>按时间倒序 · 可复制 / 导出</span>
        </div>

        <div class="stats-strip" id="recStats"></div>

        <div class="rec-toolbar">
          <button class="btn-ghost on" data-rec-type="">全部</button>
          <button class="btn-ghost" data-rec-type="route">路线</button>
          <button class="btn-ghost" data-rec-type="chat">对话</button>
          <input id="recSearch" type="search" placeholder="搜索标题或正文…" />
          <button class="btn-ghost" id="recExportAll">导出全部</button>
          <button class="btn-ghost" id="recClear">清空</button>
        </div>

        <div id="recList"></div>
        <p class="note" id="recNote">记录保存在这台电脑的浏览器里（最多保留 100 条），刷新不会丢；点开可看当时的来源，也能复制、导出或删除。</p>
      </div>
    </div>
  </div>

  <!-- ==================== 城市简介 ==================== -->
  <div class="page" id="page-city">
    <header class="city-hero">
      <img id="cityHero" src="" alt="" />
      <div class="scrim"></div>
      <div class="inner">
        <span class="back" id="cityBack">← 返回人文档案</span>
        <p class="kicker" id="cityKicker"></p>
        <h1 id="cityName"></h1>
        <p class="sub" id="citySub"></p>
        <div class="acts">
          <button class="primary" id="cityRoute">生成这座城的路线</button>
          <button class="plain" id="cityAsk">就这座城提问</button>
        </div>
      </div>
    </header>
    <div class="city-body">
      <div id="cityMain"></div>
      <aside class="city-side" id="citySide"></aside>
    </div>
  </div>

</main>

<footer class="foot">
  <div class="wrap foot-inner">
    <span>拾光叙 · 城市人文漫步 RAG 助手</span>
    <span class="foot-quote">「一条老街，半城烟火。」</span>
    <span>Vue 3 · FastAPI · FAISS · DeepSeek</span>
  </div>
</footer>

<!-- ======================= 灵动岛胶囊 ======================= -->
<div class="vmodal" id="apiModal" aria-hidden="true">
  <div class="vmodal-bg" id="apiBg"></div>
  <div class="apim-box">
    <header class="apim-head">
      <div>
        <p class="apim-kicker">MODEL ACCESS</p>
        <h3>接入你自己的大模型</h3>
      </div>
      <button class="vmodal-close apim-x" id="apiClose" aria-label="关闭">×</button>
    </header>

    <p class="apim-intro">绑定后，回答由你自己的 Key 生成；不填则进入<strong>游客模式</strong>——只返回资料原文，不调用任何模型。Key 只保存在本机浏览器，不会上传到任何服务器。</p>

    <label class="apim-field">
      <span>API Key</span>
      <input id="apiKey" type="password" placeholder="sk-..." autocomplete="off" />
    </label>

    <div class="apim-row">
      <label class="apim-field">
        <span>服务地址 Base URL</span>
        <input id="apiBase" type="text" placeholder="https://api.deepseek.com" />
      </label>
      <label class="apim-field">
        <span>模型名</span>
        <input id="apiModel" type="text" placeholder="deepseek-chat" />
      </label>
    </div>

    <p class="apim-hint">支持任何 OpenAI 兼容接口（DeepSeek / Moonshot / 通义 / 本地 vLLM），换成对应 Base URL 即可。浏览器直连官方接口，无需本地后端。</p>

    <div class="apim-actions">
      <button class="btn-solid" id="apiSave">保存</button>
      <button class="btn-ghost" id="apiClear2">清除</button>
      <span class="apim-state" id="apiState">游客模式</span>
    </div>

    <p class="apim-msg" id="apiMsg"></p>
  </div>
</div>

<div class="vmodal" id="vModal" aria-hidden="true">
  <div class="vmodal-bg" id="vModalBg"></div>
  <div class="vmodal-box">
    <button class="vmodal-close" id="vModalClose" aria-label="关闭">×</button>
    <video id="vPlayer" controls playsinline preload="metadata"></video>
    <p class="vmodal-cap" id="vModalCap"></p>
  </div>
</div>

<div class="capsule" id="capsule">
  <div class="cap-idle" id="capIdle">
    <span class="cap-dot"></span>
    <span class="cap-quote" id="capQuote"></span>
    <span class="cap-hint">ASK</span>
  </div>
  <div class="cap-panel" id="capPanel">
    <div class="cap-head">
      <div class="cap-head-l">
        <span class="cap-head-cn">随行向导</span>
        <span class="cap-head-en">FLOATING GUIDE · <em id="capMode">游客模式</em></span>
      </div>
      <button class="cap-close" id="capClose" aria-label="收起"></button>
    </div>
    <div class="cap-body" id="capBody">
      <div class="msg ai">
        <span class="avatar">叙</span>
        <div class="bubble">想问点什么？关于老街、古建、非遗都可以。点下面的问题试试。</div>
      </div>
    </div>
    <div class="chips" id="capChips"></div>
    <div class="cap-foot">
      <input id="capInput" type="text" placeholder="问一条街的故事…" />
      <button class="cap-send" id="capSend">发送</button>
    </div>
    <div class="cap-note">演示版 · 完整问答请运行本地前后端</div>
  </div>
</div>

<script>
__MAP_JS__
</script>
<script>
const IMGS = "__IMGS__";
const DATA = "__DATA__";

/* ---------------- 页面切换 ---------------- */
var PAGES = ['home', 'knowledge', 'chat', 'route', 'history', 'city'];
var currentPage = 'home';

function showPage(id) {
  if (PAGES.indexOf(id) < 0) id = 'home';
  currentPage = id;
  document.querySelectorAll('.page').forEach(function (p) {
    p.classList.toggle('is-on', p.id === 'page-' + id);
  });
  var navKey = id === 'city' ? 'knowledge' : id;
  document.querySelectorAll('[data-page]').forEach(function (a) {
    a.classList.toggle('active', a.dataset.page === navKey);
  });
  var mm = document.getElementById('mobileMenu');
  if (mm) mm.style.display = 'none';
  window.scrollTo(0, 0);
  var nav = document.getElementById('nav');
  nav.classList.remove('scrolled', 'open');
  var page = document.getElementById('page-' + id);
  if (page) {
    setTimeout(function () {
      page.querySelectorAll('.reveal').forEach(function (el) { el.classList.add('in'); });
    }, 60);
  }
  if (id === 'route') setTimeout(function () {
    if (routeCache) drawRouteMap(routeCache.stops, routeCache.city.city);
    resizeMap();
  }, 180);
}

document.querySelectorAll('[data-page]').forEach(function (a) {
  a.addEventListener('click', function (e) {
    e.preventDefault();
    showPage(a.dataset.page);
    try { history.replaceState(null, '', '#' + a.dataset.page); } catch (err) { /* file:// 下忽略 */ }
  });
});

/* 支持用 #knowledge / #city/quanzhou / #guide 直接打开（脚本末尾统一调用） */
function handleHash() {
  var h = (location.hash || '').replace('#', '');
  if (h.indexOf('city/') === 0) {
    var id = h.slice(5);
    var idx = DATA.cities.findIndex(function (c) { return c.id === id; });
    if (idx >= 0) { openCity(idx); return; }
  }
  if (h === 'guide') { openCapsule(); return; }
  if (PAGES.indexOf(h) >= 0 && h !== 'home') { showPage(h); return; }
  // 其余 hash 当作锚点：滚到对应章节
  if (h) {
    // 等图片撑开布局后再定位，否则算出来的偏移会偏小
    setTimeout(function () {
      var elx = document.getElementById(h);
      if (!elx) return;
      document.documentElement.style.scrollBehavior = 'auto';
      window.scrollTo(0, elx.getBoundingClientRect().top + window.scrollY - 90);
    }, 700);
  }
}

/* ---------------- 轻提示 ---------------- */
var toastTimer = null;
function toast(msg) {
  var t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div');
    t.className = 'toast';
    t.id = 'toast';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function () { t.classList.remove('on'); }, 2200);
}

/* ---------------- 城市档案渲染 ---------------- */
function esc(v) {
  return String(v == null ? '' : v).replace(/[&<>"]/g, function (ch) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch];
  });
}

function cardHTML(c, idx) {
  return '<article class="city-card" data-city="' + idx + '" role="button" tabindex="0">' +
    '<div class="cc-img"><img src="' + IMGS[c.img] + '" alt="' + esc(c.city + c.title) + '" loading="lazy" />' +
    '<span class="cc-no">' + esc(c.region) + ' · ' + esc(c.district) + '</span></div>' +
    '<div class="cc-body">' +
    '<h3 class="display cc-city">' + esc(c.city) + '<em>' + esc(c.title) + '</em></h3>' +
    '<p class="cc-sum">' + esc(c.summary) + '</p>' +
    '<ul class="cc-tags">' + c.tags.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>' +
    '<div class="cc-foot"><span>' + esc(c.walk) + '</span><span class="cc-go">看简介 →</span></div>' +
    '</div></article>';
}

function mountGallery(tabsId, galleryId) {
  var tabs = document.getElementById(tabsId);
  var gallery = document.getElementById(galleryId);
  if (!tabs || !gallery) return;
  var current = '';

  function render() {
    var list = current ? DATA.cities.filter(function (c) { return c.region === current; }) : DATA.cities;
    gallery.innerHTML = list.map(function (c, i) { return cardHTML(c, DATA.cities.indexOf(c)); }).join('');
    gallery.querySelectorAll('.city-card').forEach(function (el) {
      el.addEventListener('click', function () { openCity(Number(el.dataset.city)); });
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openCity(Number(el.dataset.city)); }
      });
    });
  }

  function renderTabs() {
    var html = '<button class="rtab' + (current === '' ? ' on' : '') + '" data-r="">全部 · ' + DATA.cities.length + '</button>';
    html += DATA.regions.map(function (r) {
      var n = DATA.cities.filter(function (c) { return c.region === r; }).length;
      return '<button class="rtab' + (current === r ? ' on' : '') + '" data-r="' + esc(r) + '">' + esc(r) + ' · ' + n + '</button>';
    }).join('');
    tabs.innerHTML = html;
    tabs.querySelectorAll('.rtab').forEach(function (b) {
      b.addEventListener('click', function () {
        current = b.dataset.r === current ? '' : b.dataset.r;
        renderTabs();
        render();
      });
    });
  }

  renderTabs();
  render();
}

mountGallery('homeTabs', 'homeGallery');
mountGallery('kTabs', 'kGallery');
document.getElementById('kHeroImg').src = IMGS['quanzhou-1'];
document.getElementById('cHeroImg').src = IMGS['fuzhou-1'];
document.getElementById('rHeroImg').src = IMGS['pingyao-1'];
document.getElementById('hHeroImg').src = IMGS['suzhou-1'];

/* ---------------- 城市简介页 ---------------- */
var SPOT_HINTS = {
  塔: '看塔身浮雕与仿木构斗栱，是判断年代的关键。',
  桥: '留意桥墩形制与石梁搭法，能看出水路运输的等级。',
  寺: '先看山门与主殿的轴线，再看梁架与彩画。',
  庙: '看屋顶脊饰与门楣题字，庙宇等级写在细节里。',
  街: '沿街看立面连续性与转角处理，能读出商业形态。',
  故居: '门屋、天井、正厅的进深关系，是身份与年代的线索。',
  骑楼: '抬头看柱头线脚与女儿墙风洞，那是南洋带回的做法。',
  牌坊: '数一数间数与柱数，牌坊的规格即家族的规格。',
  城墙: '看马面与垛口的间距，防御尺度一目了然。',
  石窟: '先看主尊的衣纹，再看两侧胁侍的排列。',
  楼: '看楼身比例与转角处理，再看檐下的装饰带。',
  宫: '沿中轴线看门、殿、寝的次序，等级一目了然。'
};

function spotNote(name) {
  for (var k in SPOT_HINTS) { if (name.indexOf(k) >= 0) return SPOT_HINTS[k]; }
  return '资料中有专门段落记述，可在「随行向导」里追问细节。';
}

var currentCity = null;
var cityOrigin = 'knowledge';

function openCity(idx) {
  var c = DATA.cities[idx];
  if (!c) return;
  if (currentPage !== 'city') cityOrigin = currentPage;
  currentCity = c;

  document.getElementById('cityHero').src = IMGS[c.img];
  document.getElementById('cityHero').alt = c.city + c.title;
  document.getElementById('cityKicker').textContent = c.region + ' · ' + c.district + ' · ARCHIVE';
  document.getElementById('cityName').innerHTML = esc(c.city) + '<em>' + esc(c.title) + '</em>';
  document.getElementById('citySub').textContent = c.subtitle;

  var spots = c.spots || [];
  var main = document.getElementById('cityMain');
  main.innerHTML =
    '<p class="city-lead">' + esc(c.summary) + '</p>' +
    '<div class="city-tags">' + c.tags.map(function (t) { return '<span>' + esc(t) + '</span>'; }).join('') + '</div>' +
    '<h3 class="city-h3">值得走到的几处</h3>' +
    '<ol class="city-spots">' + c.highlights.map(function (h, i) {
      return '<li><span class="n">' + String(i + 1).padStart(2, '0') + '</span><div>' +
        '<b>' + esc(h) + '</b><p>' + esc(spotNote(h)) + '</p></div></li>';
    }).join('') + '</ol>' +
    (c.sections && c.sections.length ? (
      '<h3 class="city-h3">档案正文</h3>' +
      '<div class="city-read">' + c.sections.map(function (sec, i) {
        var title = sec.h.replace(/^[一二三四五六七八九十]+、\s*/, '');
        return '<section class="city-sec"><h4><span class="sec-no">' +
          String(i + 1).padStart(2, '0') + '</span>' + esc(title) + '</h4>' +
          sec.items.map(function (t) { return '<p>' + esc(t) + '</p>'; }).join('') +
          '</section>';
      }).join('') + '</div>'
    ) : '') +
    '<h3 class="city-h3">漫步建议</h3>' +
    '<div class="city-facts">' +
      '<div><span class="k">建议时长</span><b>' + esc(c.walk) + '</b></div>' +
      '<div><span class="k">档案规模</span><b>' + (c.chunks || 0) + ' 个片段</b></div>' +
      '<div><span class="k">可定位看点</span><b>' + spots.length + ' 处</b></div>' +
      '<div><span class="k">所属区域</span><b>' + esc(c.region) + '</b></div>' +
    '</div>' +
    '<p class="note">以上内容整理自公开的政府门户、官方景区与主流媒体报道，完整出处见对应档案篇末。配图取自 Pexels 免费商用图库，为氛围示意，非该街区实拍。</p>';

  var side = document.getElementById('citySide');
  side.innerHTML =
    '<div class="card-s"><h4>QUICK ACTIONS</h4>' +
      '<button class="go-line" data-act="route">用这座城生成路线 <span>→</span></button>' +
      '<button class="go-line" data-act="ask">带着问题去对话 <span>→</span></button>' +
      '<button class="go-line" data-act="back">翻看其他档案 <span>→</span></button>' +
    '</div>' +
    (spots.length
      ? '<div class="card-s"><h4>ON THE MAP</h4>' +
        spots.slice(0, 5).map(function (s) { return '<div class="poi"><i></i>' + esc(s.name) + '</div>'; }).join('') +
        '<p class="note" style="margin-top:12px">生成路线时会把这些点按顺序标在地图上。</p></div>'
      : '');

  side.querySelectorAll('.go-line').forEach(function (b) {
    b.addEventListener('click', function () {
      var act = b.dataset.act;
      if (act === 'route') { goRouteWithCity(c); }
      if (act === 'ask') { askAboutCity(c); }
      if (act === 'back') { showPage('knowledge'); }
    });
  });

  showPage('city');
  try { history.replaceState(null, '', '#city/' + c.id); } catch (err) { /* ignore */ }
}

document.getElementById('cityBack').addEventListener('click', function () { showPage(cityOrigin || 'knowledge'); });
document.getElementById('cityRoute').addEventListener('click', function () {
  if (currentCity) goRouteWithCity(currentCity);
});
document.getElementById('cityAsk').addEventListener('click', function () {
  if (currentCity) askAboutCity(currentCity);
});

/* ---------------- 导航滚动态 ---------------- */
var nav = document.getElementById('nav');
function onScroll() {
  var top = window.scrollY > 40;
  nav.classList.toggle('scrolled', top);
  nav.classList.toggle('on-top', !top && !nav.classList.contains('open'));
}
window.addEventListener('scroll', onScroll, { passive: true });
onScroll();

/* ---------------- 汉堡菜单 ---------------- */
var burger = document.getElementById('burger');
var mobileMenu = document.getElementById('mobileMenu');
burger.addEventListener('click', function () {
  var open = mobileMenu.style.display === 'block';
  mobileMenu.style.display = open ? 'none' : 'block';
  nav.classList.toggle('open', !open);
  burger.querySelectorAll('span').forEach(function (s) { s.classList.toggle('x', !open); });
  nav.classList.toggle('on-top', false);
});

/* ---------------- 入场动画 ---------------- */
var io = new IntersectionObserver(function (entries) {
  entries.forEach(function (e) {
    if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
  });
}, { threshold: 0.14 });
document.querySelectorAll('.reveal').forEach(function (el) { io.observe(el); });

/* ---------------- 漫步对话（可交互演示） ---------------- */
var QA = [
  {
    keys: ['日昇昌', '票号', '汇通天下'],
    a: '据资料记载，清道光三年（1823 年），平遥商人雷履泰创办了中国第一家票号「日昇昌」——也有文献记为道光四年（1824 年），两种说法在篇末并列。票号发明了汇票：银子存进去，拿一张纸，走到全国任何一个分号都能取出来。鼎盛时期平遥城内二十多家票号、全国五百多个分号，业务扩至日本、新加坡、俄罗斯，平遥因此被称为「古代中国的华尔街」。',
    src: '《平遥-明清古城.md》· 四、日昇昌：中国第一家票号'
  },
  {
    keys: ['骑楼', '廊道', '五脚基'],
    a: '骑楼是商住两用的连续柱廊建筑：底层留出通廊，遮阳避雨，二层以上住人。它是南洋归侨带回的商住形式，在海口、泉州、广州、汕头都很常见。廊道连续还有商业上的考虑——行人不必横穿马路就能一家家逛下去，雨天生意也不断。',
    src: '《中国老街建筑语汇通识.md》· 骑楼 / 《海口-骑楼老街.md》'
  },
  {
    keys: ['丽江', '城墙', '木府'],
    a: '丽江古城不设城墙。通行的解释是纳西族土司姓「木」，木字加框便成「困」，因此不筑城墙。古城以四方街为中心，水圳从黑龙潭引来，分三股穿街过巷，形成「家家流水、户户垂杨」的格局。',
    src: '《丽江-古城.md》· 一、为什么不设城墙'
  },
  {
    keys: ['赵州桥', '李春', '拱桥'],
    a: '赵州桥由隋代匠师李春设计建造，是世界上现存最古老的敞肩圆弧石拱桥。它在主拱两肩各开两个小拱，既减轻自重又利于泄洪，这一技术比欧洲早约 1200 年。',
    src: '《通识-中国古桥与园林.md》· 一、四大基本桥型'
  },
  {
    keys: ['开元寺', '东西塔', '石塔'],
    a: '泉州开元寺始建于唐垂拱二年（686 年），寺内东西两座石塔为宋代遗构：东塔镇国塔高 48.24 米，西塔仁寿塔高 44.06 米，是中国现存最高的一对宋代石塔。塔身浮雕与仿木构斗栱，集中体现了宋元泉州石作的水平。',
    src: '《泉州-西街与开元寺.md》· 二、东西塔'
  },
  {
    keys: ['平江路', '平江图', '双棋盘'],
    a: '平江路依托宋代《平江图》碑所记的格局：河与街并行、桥与巷交错，形成「水陆并行、河街相邻」的双棋盘。全长约 1.6 公里，河上十七座桥，巷子里还藏着昆曲评弹博物馆与耦园。',
    src: '《苏州-平江路.md》· 一、双棋盘格局'
  }
];

function findAnswer(q) {
  for (var i = 0; i < QA.length; i++) {
    for (var j = 0; j < QA[i].keys.length; j++) {
      if (q.indexOf(QA[i].keys[j]) >= 0) return QA[i];
    }
  }
  return null;
}

/* ---------- 语料检索：在三十城档案里找最相关的一段 ---------- */
var CORPUS = null;

function buildCorpus() {
  if (CORPUS) return;
  CORPUS = [];
  (DATA.cities || []).forEach(function (c) {
    if (c.summary) CORPUS.push({ c: c, h: '街区摘要', t: c.summary });
    var meta = [];
    if (c.subtitle) meta.push(c.subtitle);
    if (c.tags && c.tags.length) meta.push('关键词：' + c.tags.join('、'));
    if (c.highlights && c.highlights.length) meta.push('主要看点：' + c.highlights.join('、'));
    if (c.walk) meta.push('漫步建议：' + c.walk);
    if (meta.length) CORPUS.push({ c: c, h: '档案概览', t: meta.join('。') });
    (c.sections || []).forEach(function (sec) {
      (sec.items || []).forEach(function (t) {
        if (t && t.length > 24) CORPUS.push({ c: c, h: sec.h, t: t });
      });
    });
  });
}

var STOP_GRAMS = {
  '什么': 1, '是什': 1, '么是': 1, '怎么': 1, '为什': 1, '哪些': 1, '哪个': 1,
  '一个': 1, '可以': 1, '有什': 1, '这个': 1, '那个': 1, '多少': 1, '如何': 1,
  '介绍': 1, '有哪': 1, '是怎': 1, '么样': 1, '一些': 1, '我们': 1, '你们': 1
};

function qGrams(q) {
  var key = q.replace(/[ 　，。？！、；：""''（）()《》·,?!;:.]/g, '');
  var out = [], seen = {};
  for (var i = 0; i < key.length - 1; i++) {
    var g = key.slice(i, i + 2);
    if (STOP_GRAMS[g] || seen[g]) continue;
    seen[g] = 1;
    out.push(g);
  }
  return out;
}

function searchCorpus(q) {
  buildCorpus();
  var gs = qGrams(q);
  if (!gs.length) return null;
  var best = null;
  for (var i = 0; i < CORPUS.length; i++) {
    var row = CORPUS[i], txt = row.t, hit = 0;
    for (var j = 0; j < gs.length; j++) { if (txt.indexOf(gs[j]) >= 0) hit += 1; }
    if (!hit) continue;
    // 问句里点名了城市 / 街区，等同于命中若干关键词
    if (q.indexOf(row.c.city) >= 0) hit += 2;
    if (q.indexOf(row.c.title) >= 0) hit += 1;
    var score = hit / Math.sqrt(gs.length) + Math.min(txt.length, 320) / 1600;
    if (row.h === '档案概览') score -= 0.12;   // 概述只做兜底，优先正文段落
    if (row.h === '街区摘要') score -= 0.08;
    if (!best || score > best.score) best = { score: score, hit: hit, row: row };
  }
  // 短问题允许命中 2 个二字词，长问题要求 3 个，避免答非所问
  var need = gs.length <= 4 ? 2 : 3;
  if (!best || best.hit < need) return null;
  var body = best.row.t;
  if (body.length > 300) body = body.slice(0, 300) + '…';
  return {
    a: body,
    src: '《' + best.row.c.city + ' · ' + best.row.c.title + '》· ' + best.row.h
  };
}

function smallTalk(q) {
  var t = q.replace(/\s/g, '');
  if (/^(你好|您好|hi|hello|嗨|在吗)/i.test(t)) return '在的。想了解哪座城、哪条街？可以问「泉州西街有什么好看」「骑楼为什么有廊道」「推荐一条半日路线」。';
  if (/^(谢谢|多谢|感谢|好的|收到)/.test(t)) return '不客气。想继续深挖，就报一个地名或构件，我去资料里找。';
  if (/^(你是谁|介绍.*自己|你能做什么)/.test(t)) return '我是拾光叙的随行向导：站在三十座城的文史档案上回答问题。每条回答都会标出处；资料里没有的，我会直接说没有。';
  return '';
}

function answerQuestion(q) {
  var st = smallTalk(q);
  if (st) return { a: st, src: '', kind: 'smalltalk' };

  var qa = findAnswer(q);
  if (qa) return { a: qa.a, src: qa.src, kind: 'curated' };

  var up = searchUploads(q);
  if (up) return { a: up.a, src: up.src, kind: 'upload' };

  var cp = searchCorpus(q);
  if (cp) return { a: cp.a, src: cp.src, kind: 'corpus' };

  return {
    a: '知识库里没有找到与「' + q.slice(0, 24) + '」直接相关的记载。我不替城市编故事，但可以换个更具体的问法：· 一个地名，如「开元寺」「西街」 · 一个构件，如「燕尾脊」「骑楼」 · 一座城加一个主题，如「平遥 票号」',
    src: '',
    kind: 'miss'
  };
}

function typeIntoEl(el, q, done) {
  var hit = answerQuestion(q);
  var text = hit.a, i = 0;
  var timer = setInterval(function () {
    i += 3;
    el.textContent = text.slice(0, i);
    if (i >= text.length) { clearInterval(timer); done(hit); }
  }, 18);
}

function appendAsk(q) {
  var thread = document.getElementById('askThread');
  var row = document.createElement('div');
  row.className = 'row';
  row.innerHTML = '<div class="q">' + esc(q) + '</div><div class="a"></div>';
  thread.appendChild(row);
  var a = row.querySelector('.a');
  var srcLine = null;

  var finish = function (hit) {
    if (hit && hit.src && !srcLine) {
      srcLine = document.createElement('div');
      srcLine.className = 'src';
      srcLine.textContent = '来源：' + hit.src;
      row.appendChild(srcLine);
    }
    addRecord({
      type: 'chat',
      title: q.slice(0, 40),
      body: a.textContent.slice(0, 160) + (a.textContent.length > 160 ? '…' : ''),
      sources: (hit && hit.src) || ((LLM_CFG && LLM_CFG.key) ? '你的模型 · ' + (LLM_CFG.model || 'deepseek-chat') : '')
    }, true);
  };

  if (LLM_CFG && LLM_CFG.key) {
    a.textContent = '';
    liveAsk(q, function (delta) {
      a.textContent += delta;
    }, function (data) {
      if (!a.textContent) a.textContent = (data && data.guest) ? '后端处于游客模式：请检查 Key 是否有效。' : '没有返回内容，稍后再试。';
      finish({ src: '' });
    }, function () {
      a.textContent = '';
      typeIntoEl(a, q, finish);
    });
  } else {
    typeIntoEl(a, q, finish);
  }

  row.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function askNow(text) {
  var v = (text || '').trim();
  if (!v) { toast('先写下一个问题'); return; }
  appendAsk(v);
}

(function () {
  var input = document.getElementById('askInput');
  var btn = document.getElementById('askSend');
  if (!input || !btn) return;
  btn.addEventListener('click', function () { askNow(input.value); input.value = ''; });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { askNow(input.value); input.value = ''; }
  });
  document.querySelectorAll('#chatChips .chip').forEach(function (chip) {
    chip.addEventListener('click', function () { askNow(chip.dataset.q || chip.textContent); });
  });
})();

/* ---------------- 灵动岛胶囊 ---------------- */
var QUOTES = [
  '一条老街，半城烟火。',
  '走得慢一点，才听得见旧事。',
  '砖缝里藏着一代人的作息。',
  '先有大昭寺，后有拉萨城。',
  '一座城的中轴线，是它的脊梁。',
  '飞天没有翅膀，靠一条飘带飞了一千年。'
];
var qi = 0;
var capQuote = document.getElementById('capQuote');
function setQuote(t) {
  capQuote.innerHTML = '<span>' + esc(t) + '</span>';
}
setQuote(QUOTES[0]);
setInterval(function () {
  qi = (qi + 1) % QUOTES.length;
  capQuote.style.opacity = 0;
  setTimeout(function () { setQuote(QUOTES[qi]); capQuote.style.opacity = 1; }, 420);
}, 5200);

var capsule = document.getElementById('capsule');
var capBody = document.getElementById('capBody');
var capInput = document.getElementById('capInput');
var capSend = document.getElementById('capSend');
var capClose = document.getElementById('capClose');
var capOpen = false;

function openCapsule() {
  capsule.classList.add('expanded');
  capOpen = true;
  setTimeout(function () { capInput.focus(); }, 400);
}
function closeCapsule() {
  capsule.classList.remove('expanded');
  capOpen = false;
}

capsule.addEventListener('click', function (e) {
  if (e.target.closest && e.target.closest('.cap-panel')) return;
  if (!capOpen) openCapsule();
});
capClose.addEventListener('click', function (e) {
  e.stopPropagation();
  closeCapsule();
});
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape' && capOpen) closeCapsule();
});

/* 面板里的快捷问题 */
(function () {
  var chips = ['这条街的名字怎么来的？', '骑楼有什么讲究？', '推荐一条半日路线'];
  var wrap = document.getElementById('capChips');
  if (!wrap) return;
  chips.forEach(function (t) {
    var b = document.createElement('button');
    b.className = 'chip';
    b.textContent = t;
    b.addEventListener('click', function (e) {
      e.stopPropagation();
      reply(t);
    });
    wrap.appendChild(b);
  });
  capBody.appendChild(wrap);
})();

function pushMsg(who, text) {
  var d = document.createElement('div');
  d.className = 'msg' + (who === '拾' ? ' ai' : ' user');
  d.innerHTML = '<span class="avatar">' + who + '</span><div class="bubble"></div>';
  d.querySelector('.bubble').textContent = text;
  capBody.appendChild(d);
  capBody.scrollTop = capBody.scrollHeight;
}

function reply(text) {
  pushMsg('我', text);
  var bubble = createBubble();
  var finish = function (hit) {
    addRecord({
      type: 'chat',
      title: text.slice(0, 40),
      body: bubble.textContent.slice(0, 160) + (bubble.textContent.length > 160 ? '…' : ''),
      sources: (hit && hit.src) || ((LLM_CFG && LLM_CFG.key) ? '你的模型 · ' + (LLM_CFG.model || 'deepseek-chat') : '')
    }, true);
  };

  if (LLM_CFG && LLM_CFG.key) {
    bubble.textContent = '';
    liveAsk(text, function (delta) {
      bubble.textContent += delta;
      capBody.scrollTop = capBody.scrollHeight;
    }, function (data) {
      if (!bubble.textContent) {
        bubble.textContent = (data && data.guest) ? '后端处于游客模式：请检查 Key 是否有效。' : '没有返回内容，稍后再试。';
      }
      finish({ src: '' });
    }, function (err) {
      // 后端没开 / 网络失败：明确告知，再退回本地检索
      bubble.textContent = '';
      var tip = document.createElement('div');
      tip.className = 'llm-fallback';
      tip.textContent = '你的模型调用失败（' + err.message + '），已切回本站资料检索。';
      bubble.parentNode.insertBefore(tip, bubble);
      typeLocal(bubble, text, finish);
    });
  } else {
    typeLocal(bubble, text, finish);
  }
}

capSend.addEventListener('click', function (e) {
  e.stopPropagation();
  var v = capInput.value.trim();
  if (v) { reply(v); capInput.value = ''; }
  else toast('先写下一个问题');
});
capInput.addEventListener('click', function (e) { e.stopPropagation(); });
capInput.addEventListener('keydown', function (e) {
  if (e.key === 'Enter') { capSend.click(); }
});

/* 城市页跳转过来的两个动作 */
function goRouteWithCity(c) {
  var idx = DATA.cities.indexOf(c);
  routeSel.cityIdx = idx < 0 ? 0 : idx;
  routeSel.theme = (c.tags && c.tags[0]) || '老街烟火';
  renderRoutePills();
  showPage('route');
  setTimeout(function () { generateRoute(false, true); }, 220);
}

function askAboutCity(c) {
  openCapsule();
  setTimeout(function () {
    reply('请介绍一下' + c.city + c.title + '的历史与看点');
  }, 460);
}

/* ---------------- 路线生成（演示） ---------------- */
var ROUTE_THEMES = ['老街烟火', '古建寻踪', '非遗手艺', '市井味道', '江河水岸'];
var ROUTE_DURS = ['2 小时', '半日', '一日'];
var ROUTE_PACES = ['悠闲', '适中', '紧凑'];
var routeSel = { cityIdx: 0, theme: '老街烟火', dur: '半日', pace: '悠闲' };
var routeCache = null;

function pillHTML(label, on, data) {
  return '<span class="pill' + (on ? ' on' : '') + '" data-v="' + esc(data) + '">' + esc(label) + '</span>';
}

function renderRoutePills() {
  var cityWrap = document.getElementById('routeCityPills');
  var themeWrap = document.getElementById('routeThemePills');
  var optWrap = document.getElementById('routeOptPills');
  if (!cityWrap) return;

  cityWrap.innerHTML = DATA.cities.slice(0, 12).map(function (c, i) {
    return '<span class="pill' + (i === routeSel.cityIdx ? ' on' : '') + '" data-i="' + i + '">' + esc(c.city) + '</span>';
  }).join('') + '<span class="pill" id="cityMore">更多城市…</span>';

  themeWrap.innerHTML = ROUTE_THEMES.map(function (t) {
    return pillHTML(t, t === routeSel.theme, t);
  }).join('');

  optWrap.innerHTML = ROUTE_DURS.map(function (d) {
    return pillHTML(d, d === routeSel.dur, d);
  }).join('') + ROUTE_PACES.map(function (p) {
    return pillHTML(p, p === routeSel.pace, p);
  }).join('');

  cityWrap.querySelectorAll('.pill[data-i]').forEach(function (p) {
    p.addEventListener('click', function () {
      routeSel.cityIdx = Number(p.dataset.i);
      renderRoutePills();
      updateRouteHint();
    });
  });
  var more = document.getElementById('cityMore');
  if (more) {
    more.addEventListener('click', function () {
      showPage('knowledge');
      toast('在知识库里挑一座城，点开档案即可生成路线');
    });
  }
  themeWrap.querySelectorAll('.pill').forEach(function (p) {
    p.addEventListener('click', function () {
      routeSel.theme = p.dataset.v;
      renderRoutePills();
      updateRouteHint();
    });
  });
  optWrap.querySelectorAll('.pill').forEach(function (p) {
    p.addEventListener('click', function () {
      var v = p.dataset.v;
      if (ROUTE_DURS.indexOf(v) >= 0) routeSel.dur = v;
      else routeSel.pace = v;
      renderRoutePills();
      updateRouteHint();
    });
  });
  updateRouteHint();
}

function updateRouteHint() {
  var c = DATA.cities[routeSel.cityIdx];
  var hint = document.getElementById('routeHint');
  if (hint && c) {
    hint.textContent = '已选 ' + c.city + ' · ' + routeSel.theme + ' · ' + routeSel.dur + ' · ' + routeSel.pace;
  }
}

var THEME_INFO = {
  '老街烟火': {
    kw: ['街', '巷', '路', '里', '坊', '市', '骑楼', '弄', '胡同', '老城', '铺', '店'],
    intro: '把脚步放在老街上：看立面怎么连成一条线，门楣上写着哪一姓的郡望，骑楼下的廊道如何把雨挡住。',
    lens: '沿街看立面连续性与转角处理，留意门楣题字与招牌字体。',
    tips: '傍晚光线最好；周末人多，建议九点前先走主街，再钻巷子。',
    copy: '打卡文案：{city}的老街不适合赶路。从{first}走到{last}，一路是{tags}——砖、木、招牌，都是活的。'
  },
  '古建寻踪': {
    kw: ['寺', '塔', '庙', '宫', '观', '祠', '楼', '阁', '桥', '城墙', '门', '石窟', '殿', '陵', '书院', '文庙', '牌坊'],
    intro: '以年代为线索看建筑：先看台基与柱网，再看梁架，最后看屋顶的脊饰与瓦作。',
    lens: '先看轴线与开间，再看斗栱与梁架，最后抬头看屋脊。',
    tips: '殿内光线偏暗，可带小手电；拍摄佛像前先确认是否允许。',
    copy: '打卡文案：{city}的古建要抬头看。{first}到{last}，斗栱、脊饰、柱础，一层层把年代读出来。'
  },
  '非遗手艺': {
    kw: ['馆', '作坊', '窑', '戏', '曲', '绣', '陶', '纸', '茶', '药', '酱', '灯', '工坊', '堂', '号'],
    intro: '找仍在营业的手艺：先看工具与工序，再问一句「这道工序能不能省」，答案里藏着这门手艺的难处。',
    lens: '看工具摆位与工序顺序，问一句「哪一步最费工」。',
    tips: '进作坊先打招呼，拍摄前征得同意；买一件小物是最好的谢礼。',
    copy: '打卡文案：{city}的手艺不在展柜里，在手上。{first}到{last}，看一遍工序，才知道一件东西为什么贵。'
  },
  '市井味道': {
    kw: ['市', '场', '街', '巷', '小吃', '食', '茶', '酒', '铺', '店', '集', '摊', '面', '饼'],
    intro: '按「早—午—晚」三段安排吃食：早上找本地人排队的摊，中午进老店，晚上逛夜市。',
    lens: '看招牌的新旧、菜单的厚度，以及本地人点什么。',
    tips: '少量多点，两人分食；避开景区正门第一家。',
    copy: '打卡文案：{city}的味道要趁热。从{first}吃到{last}，一天三顿，把这座城的脾气尝一遍。'
  },
  '江河水岸': {
    kw: ['河', '江', '湖', '桥', '码头', '渡', '泉', '井', '塘', '堤', '湾', '溪', '渠', '水'],
    intro: '沿水走：先看水与街的高差，再看桥的形制，最后看埠头与缆船石。',
    lens: '看驳岸做法与桥墩形制，留意水位线留下的痕迹。',
    tips: '清晨水面最静，适合拍倒影；雨天石阶滑，注意脚下。',
    copy: '打卡文案：{city}的故事是顺水来的。{first}到{last}，桥、埠、巷，一路都是水路留下的秩序。'
  }
};

var DUR_COUNT = { '2 小时': 3, '半日': 4, '一日': 5 };
var PACE_MIN = { '悠闲': 45, '适中': 30, '紧凑': 20 };

var THEME_ORDER = ['老街烟火', '古建寻踪', '非遗手艺', '市井味道', '江河水岸'];

function pickSpotsByTheme(c, theme, n) {
  var spots = (c.spots || []).slice();
  var names = {};
  spots.forEach(function (sp) { names[sp.name] = 1; });

  // 把只出现在「看点」里、还没坐标的地点也纳入候选（地图会自动跳过无坐标点）
  var extra = (c.highlights || []).filter(function (h) { return !names[h]; })
    .map(function (h) { return { name: h }; });
  var pool = spots.concat(extra);
  if (!pool.length) return [];

  var kw = (THEME_INFO[theme] || THEME_INFO['老街烟火']).kw;
  var scored = pool.map(function (sp, i) {
    var sc = 0;
    kw.forEach(function (k) { if (sp.name.indexOf(k) >= 0) sc += 2; });
    return { sp: sp, sc: sc, i: i };
  });

  var hitCount = scored.filter(function (x) { return x.sc > 0; }).length;
  if (hitCount >= 2) {
    scored.sort(function (a, b) { return b.sc - a.sc || a.i - b.i; });
  } else {
    // 关键词命不中时，用主题序号做轮转，保证换主题阵容/顺序会变
    var shift = THEME_ORDER.indexOf(theme);
    if (shift < 0) shift = 0;
    scored = pool.map(function (sp, i) {
      return { sp: sp, sc: 0, i: (i + shift) % pool.length };
    }).sort(function (a, b) { return a.i - b.i; });
  }
  return scored.slice(0, Math.min(n, scored.length)).map(function (x) { return x.sp; });
}

function generateRoute(silent, record) {
  var c = DATA.cities[routeSel.cityIdx];
  if (!c) return;
  var stopsEl = document.getElementById('routeStops');
  var count = DUR_COUNT[routeSel.dur] || 4;
  var spots = pickSpotsByTheme(c, routeSel.theme, count);

  if (!spots.length) {
    stopsEl.innerHTML = '<p class="note">这座城暂无坐标数据，换一座试试。</p>';
    if (!silent) toast('暂无坐标数据');
    return;
  }

  var info = THEME_INFO[routeSel.theme] || THEME_INFO['老街烟火'];
  var stay = PACE_MIN[routeSel.pace] || 30;

  var stops = spots.map(function (sp, idx) {
    return {
      title: sp.name,
      lat: sp.lat,
      lng: sp.lng,
      desc: (idx === 0 ? info.lens + ' ' : '') + spotNote(sp.name) + ' 建议停留 ' + stay + ' 分钟。'
    };
  });

  routeCache = {
    city: c, stops: stops, theme: routeSel.theme,
    dur: routeSel.dur, pace: routeSel.pace, intro: info.intro, tips: info.tips
  };

  stopsEl.innerHTML =
    '<div class="route-intro">' +
      '<p class="ri-kicker">' + esc(routeSel.theme) + ' · ' + esc(routeSel.dur) + ' · ' + esc(routeSel.pace) + '</p>' +
      '<p class="ri-text">' + esc(info.intro) + '</p>' +
    '</div>' +
    stops.map(function (s, i) {
      return '<div class="stop"><span class="stop-no">' + String(i + 1).padStart(2, '0') + '</span>' +
        '<div><h3 class="stop-t">' + esc(s.title) + '</h3><p class="stop-d">' + esc(s.desc) + '</p></div></div>';
    }).join('') +
    '<p class="route-tips"><b>漫步贴士</b> ' + esc(info.tips) + '</p>';

  var copyTpl = info.copy
    .replace('{city}', c.city)
    .replace('{first}', stops[0].title)
    .replace('{last}', stops[stops.length - 1].title)
    .replace('{tags}', (c.tags || []).join('、'));
  document.getElementById('routeCopy').textContent = copyTpl;

  drawRouteMap(stops, c.city);

  // 只要是一次真实的生成（用户点了按钮 / 从城市页跳来），就自动归档，无需手动点保存
  if (record) {
    addRecord({
      type: 'route',
      title: c.city + ' · ' + routeSel.theme + ' ' + routeSel.dur + '路线',
      body: stops.map(function (x) { return x.title; }).join(' → '),
      sources: stops.map(function (x) { return x.title; }).join(' / ')
    }, true);
    markRouteSaved(true);
  }

  if (!silent) {
    toast(record
      ? ('已生成 ' + stops.length + ' 个落脚点 · 已自动存入历史')
      : ('已生成 ' + routeSel.theme + ' · ' + stops.length + ' 个落脚点'));
  }
}

function markRouteSaved(on) {
  var el = document.getElementById('routeSaved');
  if (!el) return;
  el.textContent = on ? '已自动存入历史记录' : '生成后自动存入历史记录';
  el.classList.toggle('on', Boolean(on));
  if (on) {
    el.classList.remove('flash');
    void el.offsetWidth;
    el.classList.add('flash');
  }
}

document.getElementById('routeGo').addEventListener('click', function () { generateRoute(false, true); });

document.getElementById('routeCopyBtn').addEventListener('click', function () {
  var box = document.getElementById('routeCopy');
  var text = box ? box.textContent : '';
  if (!text) { toast('先生成一条路线'); return; }
  copyText(text);
});

function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function () { toast('已复制到剪贴板'); }, function () { fallbackCopy(text); });
  } else {
    fallbackCopy(text);
  }
}

function fallbackCopy(text) {
  var ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); toast('已复制到剪贴板'); } catch (err) { toast('复制失败，请手动选择'); }
  document.body.removeChild(ta);
}

/* ---------------- 地图（MapLibre + 高德瓦片） ---------------- */
var mapObj = null;
var mapMarkers = [];
var mapReady = false;

function wgs2gcj(lng, lat) {
  var a = 6378245.0;
  var ee = 0.00669342162296594323;
  function outOfChina(lng, lat) {
    return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271;
  }
  function transformLat(x, y) {
    var r = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
    r += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0;
    r += (20.0 * Math.sin(y * Math.PI) + 40.0 * Math.sin(y / 3.0 * Math.PI)) * 2.0 / 3.0;
    r += (160.0 * Math.sin(y / 12.0 * Math.PI) + 320 * Math.sin(y * Math.PI / 30.0)) * 2.0 / 3.0;
    return r;
  }
  function transformLng(x, y) {
    var r = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
    r += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0;
    r += (20.0 * Math.sin(x * Math.PI) + 40.0 * Math.sin(x / 3.0 * Math.PI)) * 2.0 / 3.0;
    r += (150.0 * Math.sin(x / 12.0 * Math.PI) + 300.0 * Math.sin(x / 30.0 * Math.PI)) * 2.0 / 3.0;
    return r;
  }
  if (outOfChina(lng, lat)) return [lng, lat];
  var dLat = transformLat(lng - 105.0, lat - 35.0);
  var dLng = transformLng(lng - 105.0, lat - 35.0);
  var radLat = lat / 180.0 * Math.PI;
  var magic = Math.sin(radLat);
  magic = 1 - ee * magic * magic;
  var sqrtMagic = Math.sqrt(magic);
  dLat = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrtMagic) * Math.PI);
  dLng = (dLng * 180.0) / (a / sqrtMagic * Math.cos(radLat) * Math.PI);
  return [lng + dLng, lat + dLat];
}

function mapStyle() {
  return {
    version: 8,
    sources: {
      basemap: {
        type: 'raster',
        tiles: [1, 2, 3, 4].map(function (i) {
          return 'https://webrd0' + i + '.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}';
        }),
        tileSize: 256,
        maxzoom: 18,
        attribution: '© 高德地图 © OpenStreetMap contributors'
      }
    },
    layers: [{ id: 'basemap', type: 'raster', source: 'basemap' }]
  };
}

function clearMarkers() {
  mapMarkers.forEach(function (m) { m.remove(); });
  mapMarkers = [];
}

function routeVisible() {
  var p = document.getElementById('page-route');
  return !!p && p.classList.contains('is-on');
}

function drawRouteMap(allStops, cityName) {
  var box = document.getElementById('routeMap');
  if (!box) return;
  var stops = (allStops || []).filter(function (s) { return s.lat && s.lng; });
  if (!stops.length) { drawSchematic(allStops || []); return; }
  var badge = document.getElementById('mapBadge');
  if (badge) badge.textContent = cityName + ' · ' + stops.length + ' 个落脚点';

  var legend = document.getElementById('mapLegend');
  legend.innerHTML = stops.map(function (s, i) {
    return '<button data-i="' + i + '"><span class="n">' + String(i + 1).padStart(2, '0') + '</span>' + esc(s.title) + '</button>';
  }).join('');
  legend.querySelectorAll('button').forEach(function (b) {
    b.addEventListener('click', function () {
      legend.querySelectorAll('button').forEach(function (x) { x.classList.remove('on'); });
      b.classList.add('on');
      flyToStop(Number(b.dataset.i), stops);
    });
  });

  // 页面隐藏时不初始化 WebGL 地图（容器 0×0 会白屏），先给示意图，切过去再重绘
  if (typeof maplibregl === 'undefined' || (!mapObj && !routeVisible())) { drawSchematic(stops); return; }

  var pts = stops.map(function (s) { return wgs2gcj(s.lng, s.lat); });
  if (!mapObj) {
    box.querySelectorAll('svg').forEach(function (s) { s.remove(); });
    mapObj = new maplibregl.Map({
      container: box,
      style: mapStyle(),
      center: pts[0],
      zoom: 12,
      attributionControl: false
    });
    mapObj.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');
    mapObj.on('load', function () {
      mapReady = true;
      updateMapData(pts, stops);
    });
    mapObj.on('error', function () { /* 瓦片失败时保留标记 */ });
  } else {
    updateMapData(pts, stops);
  }
}

function updateMapData(pts, stops) {
  clearMarkers();
  stops.forEach(function (s, i) {
    var node = document.createElement('div');
    node.className = 'exp-marker';
    node.innerHTML = '<span>' + (i + 1) + '</span>';
    node.addEventListener('click', function () { flyToStop(i, stops); });
    mapMarkers.push(new maplibregl.Marker({ element: node }).setLngLat(pts[i]).addTo(mapObj));
  });

  var line = { type: 'Feature', geometry: { type: 'LineString', coordinates: pts }, properties: {} };
  if (mapObj.getSource('route')) {
    mapObj.getSource('route').setData(line);
  } else if (mapReady) {
    mapObj.addSource('route', { type: 'geojson', data: line });
    mapObj.addLayer({
      id: 'route-casing', type: 'line', source: 'route',
      paint: { 'line-color': '#fdf8ec', 'line-width': 7, 'line-opacity': 0.9 }
    });
    mapObj.addLayer({
      id: 'route-line', type: 'line', source: 'route',
      paint: { 'line-color': '#b22e26', 'line-width': 3, 'line-dasharray': [1.6, 1.2] }
    });
  }

  var lngs = pts.map(function (p) { return p[0]; });
  var lats = pts.map(function (p) { return p[1]; });
  var fit = function () {
    if (!mapObj) return;
    mapObj.resize();
    mapObj.fitBounds([[Math.min.apply(null, lngs), Math.min.apply(null, lats)],
      [Math.max.apply(null, lngs), Math.max.apply(null, lats)]],
      { padding: { top: 70, bottom: 70, left: 60, right: 60 }, duration: 600, maxZoom: 13.6 });
  };
  // 容器可能还在布局/过渡中，等一帧再量尺寸取景
  mapObj.resize();
  requestAnimationFrame(fit);
  setTimeout(fit, 420);
}

function flyToStop(i, stops) {
  if (!mapObj || !stops[i]) return;
  mapObj.flyTo({ center: wgs2gcj(stops[i].lng, stops[i].lat), zoom: 15, duration: 800 });
}

function resizeMap() {
  if (!mapObj) return;
  mapObj.resize();
  if (routeCache) {
    var pts = routeCache.stops.map(function (s) { return wgs2gcj(s.lng, s.lat); });
    if (pts.length) {
      var lngs = pts.map(function (p) { return p[0]; });
      var lats = pts.map(function (p) { return p[1]; });
      mapObj.fitBounds([[Math.min.apply(null, lngs), Math.min.apply(null, lats)],
        [Math.max.apply(null, lngs), Math.max.apply(null, lats)]],
        { padding: { top: 70, bottom: 70, left: 60, right: 60 }, duration: 0, maxZoom: 13.6 });
    }
  }
}
window.addEventListener('resize', resizeMap);

/* 没有 WebGL / 离线时的示意图 */
function drawSchematic(stops) {
  var box = document.getElementById('routeMap');
  box.querySelectorAll('svg').forEach(function (s) { s.remove(); });
  var w = 600;
  var h = 320;
  var n = stops.length;
  var pts = stops.map(function (s, i) {
    var x = 70 + (w - 140) * (n === 1 ? 0.5 : i / (n - 1));
    var y = h / 2 + Math.sin(i * 1.1) * (h / 3.4);
    return [x, y];
  });
  var path = pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0] + ' ' + p[1]; }).join(' ');
  var svg = '<svg class="map-fallback-svg" viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="xMidYMid meet">' +
    '<rect width="' + w + '" height="' + h + '" fill="#efe8dc" />' +
    '<path d="' + path + '" fill="none" stroke="#b22e26" stroke-width="2" stroke-dasharray="6 5" opacity=".8" />' +
    pts.map(function (p, i) {
      return '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="13" fill="#fdf8ec" stroke="#b22e26" stroke-width="1.5" />' +
        '<text x="' + p[0] + '" y="' + (p[1] + 4) + '" text-anchor="middle" font-size="11" fill="#b22e26">' + (i + 1) + '</text>';
    }).join('') + '</svg>';
  box.insertAdjacentHTML('afterbegin', svg);
}

/* ---------------- 历史记录（可交互演示） ---------------- */
var RECS = [
  {
    type: 'route', title: '泉州 · 西街与开元寺半日路线', time: '2026-10-28 01:04',
    body: '五个落脚点，约 3 公里：开元寺 → 西街红砖厝 → 中山路骑楼 → 府文庙 → 蟳埔蚵壳厝。附 4 条来源引用与一段打卡文案。',
    sources: '《泉州-西街与开元寺.md》· 二、东西塔 / 三、西街与骑楼'
  },
  {
    type: 'chat', title: '日昇昌票号是哪一年创办的', time: '2026-10-28 00:58',
    body: '自动处理了 1823 / 1824 两种说法并并列说明；回答附 2 条来源原文，均出自《平遥-明清古城.md》。',
    sources: '《平遥-明清古城.md》· 四、日昇昌：中国第一家票号'
  },
  {
    type: 'chat', title: '骑楼下的廊道是为谁而建的', time: '2026-10-27 23:41',
    body: '从遮阳避雨与商业连续性两个角度作答，引用海口骑楼老街与泉州西街两份档案。',
    sources: '《海口-骑楼老街.md》/《中国老街建筑语汇通识.md》'
  }
];
var recFilter = '';
var recKeyword = '';
var recOpen = -1;
var REC_KEY = 'sgx_records_v1';
var REC_MAX = 100;

function loadRecs() {
  try {
    var raw = localStorage.getItem(REC_KEY);
    if (!raw) return;
    var arr = JSON.parse(raw);
    if (Array.isArray(arr) && arr.length) RECS = arr;
  } catch (e) { /* 无痕模式或存储被禁用时保持内存态 */ }
}

function saveRecs() {
  try { localStorage.setItem(REC_KEY, JSON.stringify(RECS.slice(0, REC_MAX))); } catch (e) { /* ignore */ }
}

function recStats() {
  var chats = RECS.filter(function (r) { return r.type === 'chat'; }).length;
  var routes = RECS.filter(function (r) { return r.type === 'route'; }).length;
  var el = document.getElementById('recStats');
  if (!el) return;
  el.innerHTML =
    '<div><b>' + chats + '</b><span>次提问</span></div>' +
    '<div><b>' + routes + '</b><span>条路线</span></div>' +
    '<div><b>' + RECS.length + '</b><span>条记录</span></div>' +
    '<div><b>' + new Set(RECS.map(function (r) { return r.title.split(/[·—]/)[0].trim(); })).size + '</b><span>座城 / 主题</span></div>';
}

function renderRecs() {
  var list = document.getElementById('recList');
  if (!list) return;
  var rows = RECS.filter(function (r) {
    if (recFilter && r.type !== recFilter) return false;
    if (recKeyword) {
      var kw = recKeyword.toLowerCase();
      return (r.title + r.body).toLowerCase().indexOf(kw) >= 0;
    }
    return true;
  });

  if (!rows.length) {
    list.innerHTML = '<p class="note">没有匹配的记录。换个关键词，或切到「全部」。</p>';
    recStats();
    return;
  }

  list.innerHTML = rows.map(function (r) {
    var idx = RECS.indexOf(r);
    var open = idx === recOpen;
    return '<div class="rec' + (open ? ' open' : '') + '" data-i="' + idx + '">' +
      '<div class="rec-head">' +
        '<span class="rec-kind">' + (r.type === 'route' ? 'ROUTE' : 'CHAT') + '</span>' +
        '<span class="rec-t">' + esc(r.title) + '</span>' +
        '<span class="rec-time">' + esc(r.time) + '</span>' +
        '<span class="rec-arrow">' + (open ? '收起' : '展开') + '</span>' +
      '</div>' +
      '<div class="rec-body">' + esc(r.body) +
        '<div class="srcs" style="margin-top:14px"><h4>资料来源</h4>' +
        '<div class="src-item"><span class="src-no">[1]</span><span>' + esc(r.sources || '（演示记录未附来源）') + '</span></div></div>' +
        '<div class="rec-tools">' +
          '<button class="btn-ghost" data-act="copy">复制正文</button>' +
          '<button class="btn-ghost" data-act="export">导出 MD</button>' +
          '<button class="btn-ghost" data-act="del">删除</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  }).join('');

  list.querySelectorAll('.rec').forEach(function (el) {
    var idx = Number(el.dataset.i);
    el.querySelector('.rec-head').addEventListener('click', function () {
      recOpen = recOpen === idx ? -1 : idx;
      renderRecs();
    });
    el.querySelectorAll('[data-act]').forEach(function (b) {
      b.addEventListener('click', function (e) {
        e.stopPropagation();
        var r = RECS[idx];
        if (b.dataset.act === 'copy') copyText(r.title + String.fromCharCode(10, 10) + r.body);
        if (b.dataset.act === 'export') exportRec(r);
        if (b.dataset.act === 'del') {
          RECS.splice(idx, 1);
          recOpen = -1;
          saveRecs();
          renderRecs();
          toast('已删除这条记录');
        }
      });
    });
  });
  recStats();
}

function exportRec(r) {
  var blob = new Blob(['# ' + r.title + String.fromCharCode(10, 10) + '> ' + r.time +
    String.fromCharCode(10, 10) + r.body + String.fromCharCode(10, 10) + '## 资料来源' +
    String.fromCharCode(10, 10) + '[1] ' + (r.sources || '')], { type: 'text/markdown;charset=utf-8' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = r.title.replace(/[\\/:*?"<>|]/g, '_') + '.md';
  a.click();
  URL.revokeObjectURL(url);
  toast('已导出 Markdown');
}

function addRecord(rec, silent) {
  var d = new Date();
  var pad = function (n) { return n < 10 ? '0' + n : '' + n; };
  rec.time = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
  rec.sources = rec.sources || '';

  // 同一个问题/同一条路线连续重复时不重复落档
  var head = RECS[0];
  if (head && head.title === rec.title && head.type === rec.type && head.time === rec.time) {
    return;
  }
  RECS.unshift(rec);
  if (RECS.length > REC_MAX) RECS.length = REC_MAX;
  saveRecs();
  renderRecs();
  if (!silent) toast('已存入历史记录');
}

(function () {
  document.querySelectorAll('[data-rec-type]').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('[data-rec-type]').forEach(function (x) { x.classList.remove('on', 'on-dark'); });
      b.classList.add('on');
      recFilter = b.dataset.recType;
      renderRecs();
    });
  });
  var search = document.getElementById('recSearch');
  if (search) {
    var timer = null;
    search.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(function () { recKeyword = search.value.trim(); renderRecs(); }, 200);
    });
  }
  var exp = document.getElementById('recExportAll');
  if (exp) {
    exp.addEventListener('click', function () {
      if (!RECS.length) { toast('还没有记录'); return; }
      var body = RECS.map(function (r) {
        return '# ' + r.title + String.fromCharCode(10, 10) + '> ' + r.time + String.fromCharCode(10, 10) + r.body;
      }).join(String.fromCharCode(10, 10) + '---' + String.fromCharCode(10, 10));
      var blob = new Blob(['# 拾光叙 · 漫步档案' + String.fromCharCode(10, 10) + body], { type: 'text/markdown;charset=utf-8' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = '拾光叙-漫步档案.md';
      a.click();
      URL.revokeObjectURL(url);
      toast('已导出全部记录');
    });
  }
  var clear = document.getElementById('recClear');
  if (clear) {
    clear.addEventListener('click', function () {
      if (!RECS.length) { toast('已经是空的'); return; }
      if (window.confirm('清空全部记录？此操作不可撤销。')) {
        RECS.length = 0; recOpen = -1; saveRecs(); renderRecs(); toast('已清空');
      }
    });
  }
})();


/* ---------------- 上传的人文档案（本机保存） ---------------- */
var UP_KEY = 'sgx_uploads_v1';
var UPLOADS = [];
var MAX_LEN = 120000;

function loadUploads() {
  try {
    var raw = localStorage.getItem(UP_KEY);
    UPLOADS = raw ? JSON.parse(raw) : [];
  } catch (e) { UPLOADS = []; }
  if (!Array.isArray(UPLOADS)) UPLOADS = [];
}

function saveUploads() {
  try { localStorage.setItem(UP_KEY, JSON.stringify(UPLOADS)); } catch (e) { toast('浏览器存储空间不足'); }
}

function chunkText(text) {
  var clean = text.replace(/[　]/g, ' ').trim();
  var out = [];
  var size = 420, step = 360;
  for (var i = 0; i < clean.length; i += step) {
    var piece = clean.slice(i, i + size).trim();
    if (piece) out.push(piece);
    if (out.length > 400) break;
  }
  return out;
}

function renderUploads() {
  var list = document.getElementById('upList');
  if (!list) return;
  if (!UPLOADS.length) {
    list.innerHTML = '<p class="up-empty">还没有自己的档案。把课程笔记、地方志摘录、口述记录拖进来试试。</p>';
    return;
  }
  list.innerHTML = UPLOADS.map(function (u, i) {
    return '<div class="up-item">' +
      '<span class="u-name">' + esc(u.name) + '</span>' +
      '<span class="u-meta">' + u.chunks.length + ' 片段 · ' + (u.size / 1024).toFixed(0) + ' KB</span>' +
      '<span class="u-acts">' +
        '<button data-act="ask" data-i="' + i + '">据此提问</button>' +
        '<button data-act="read" data-i="' + i + '">看摘要</button>' +
        '<button data-act="del" data-i="' + i + '">删除</button>' +
      '</span></div>';
  }).join('');

  list.querySelectorAll('[data-act]').forEach(function (b) {
    b.addEventListener('click', function () {
      var u = UPLOADS[Number(b.dataset.i)];
      if (!u) return;
      var act = b.dataset.act;
      if (act === 'read') showUploadSummary(u);
      if (act === 'ask') askUpload(u);
      if (act === 'del') {
        UPLOADS.splice(Number(b.dataset.i), 1);
        saveUploads(); renderUploads();
        toast('已删除《' + u.name + '》');
      }
    });
  });
}

function showUploadSummary(u) {
  var box = document.getElementById('upAnswer');
  if (!box) return;
  var head = '《' + u.name + '》 · ' + u.chunks.length + ' 片段';
  var body = u.chunks[0].slice(0, 260) + (u.chunks[0].length > 260 ? '…' : '');
  box.innerHTML = '<b>' + esc(head) + '</b>' + esc(body);
  box.classList.add('on');
}

function askUpload(u) {
  openCapsule();
  setTimeout(function () {
    pushMsg('我', '《' + u.name + '》里都写了什么？');
    var ans = '《' + u.name + '》共切出 ' + u.chunks.length + ' 个片段。开头一段是：' + u.chunks[0].slice(0, 220) + '… 你可以接着问其中的人名、地名或年代，我会在这份档案里找。';
    var d = document.createElement('div');
    d.className = 'msg ai';
    d.innerHTML = '<span class="avatar">叙</span><div class="bubble"></div>';
    var span = d.querySelector('.bubble');
    capBody.appendChild(d);
    var i = 0;
    var timer = setInterval(function () {
      span.textContent = ans.slice(0, i += 2);
      capBody.scrollTop = capBody.scrollHeight;
      if (i >= ans.length) clearInterval(timer);
    }, 22);
  }, 420);
}

function searchUploads(q) {
  if (!UPLOADS.length) return null;
  var key = q.replace(/[ 　,，。.？?！!、；;：:（）()「」《》]/g, '');
  if (key.length < 2) return null;
  var best = null;
  UPLOADS.forEach(function (u) {
    u.chunks.forEach(function (c) {
      var score = 0;
      for (var i = 0; i < key.length - 1; i++) {
        if (c.indexOf(key.slice(i, i + 2)) >= 0) score += 1;
      }
      if (!best || score > best.score) best = { score: score, text: c, name: u.name };
    });
  });
  if (!best || best.score < 2) return null;
  return { a: best.text.slice(0, 320) + '…', src: '我的档案 · 《' + best.name + '》' };
}

function addFiles(files) {
  var arr = Array.prototype.slice.call(files || []);
  if (!arr.length) return;
  var accepted = 0, skipped = 0;
  var pending = arr.length;
  arr.forEach(function (f) {
    var ok = /\.(txt|md|markdown)$/i.test(f.name);
    if (!ok || f.size > 2 * 1024 * 1024) {
      skipped += 1;
      if (--pending === 0) finish();
      return;
    }
    var rd = new FileReader();
    rd.onload = function () {
      var text = String(rd.result || '');
      var chunks = chunkText(text);
      if (chunks.length) {
        UPLOADS.push({ name: f.name.replace(/\.(txt|md|markdown)$/i, ''), size: f.size,
                       chunks: chunks, at: Date.now() });
        accepted += 1;
      } else { skipped += 1; }
      if (--pending === 0) finish();
    };
    rd.onerror = function () { skipped += 1; if (--pending === 0) finish(); };
    rd.readAsText(f, 'utf-8');
  });

  function finish() {
    saveUploads();
    renderUploads();
    if (accepted) toast('已加入 ' + accepted + ' 份档案');
    if (skipped) toast(skipped + ' 个文件跳过（仅支持 txt / md，且不超过 2MB）');
  }
}

(function () {
  var zone = document.getElementById('upZone');
  var input = document.getElementById('upFile');
  if (!zone || !input) return;
  zone.addEventListener('click', function () { input.click(); });
  input.addEventListener('change', function () { addFiles(input.files); input.value = ''; });
  ['dragenter', 'dragover'].forEach(function (ev) {
    zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.add('drag'); });
  });
  ['dragleave', 'drop'].forEach(function (ev) {
    zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.remove('drag'); });
  });
  zone.addEventListener('drop', function (e) {
    if (e.dataTransfer && e.dataTransfer.files) addFiles(e.dataTransfer.files);
  });
  loadUploads();
  renderUploads();
})();


/* ---------------- 影像志 ---------------- */
var VIDS = "__VIDS__";

function renderVideos() {
  var grid = document.getElementById('vidGrid');
  if (!grid || !VIDS.length) return;
  grid.innerHTML = VIDS.map(function (v, i) {
    var auto = i === 0 ? ' autoplay' : '';
    return '<figure class="vid-card' + (v.big ? ' big' : '') + '" data-i="' + i + '">' +
      '<video src="' + v.src + '" muted loop playsinline preload="metadata" data-cap="' + esc(v.title + ' · ' + v.city) + '"' + auto + '></video>' +
      '<span class="vid-play"></span>' +
      '<figcaption class="vid-cap"><b>' + esc(v.title) + '</b><span>' + esc(v.city) + '</span></figcaption>' +
      '</figure>';
  }).join('');

  grid.querySelectorAll('.vid-card').forEach(function (card) {
    var v = card.querySelector('video');
    card.addEventListener('mouseenter', function () {
      var p = v.play();
      if (p && p.catch) p.catch(function () {});
      card.classList.add('playing');
    });
    card.addEventListener('mouseleave', function () {
      v.pause();
      card.classList.remove('playing');
    });
    card.addEventListener('click', function () {
      openVideo(v.currentSrc || v.src, v.dataset.cap || '');
    });
  });
}


/* ---------------- 接入自己的大模型 ---------------- */
var LLM_STORE = 'sgx_llm_v1';
var NL = String.fromCharCode(10);
var LLM_CFG = null;

function loadLLM() {
  try {
    var raw = localStorage.getItem(LLM_STORE);
    LLM_CFG = raw ? JSON.parse(raw) : null;
    if (LLM_CFG && !LLM_CFG.key) LLM_CFG = null;
  } catch (e) { LLM_CFG = null; }
  updateLLMUI();
}

function saveLLM(cfg) {
  LLM_CFG = cfg && cfg.key ? cfg : null;
  try {
    if (LLM_CFG) localStorage.setItem(LLM_STORE, JSON.stringify(LLM_CFG));
    else localStorage.removeItem(LLM_STORE);
  } catch (e) { /* 忽略隐私模式 */ }
  updateLLMUI();
}

function updateLLMUI() {
  var on = Boolean(LLM_CFG && LLM_CFG.key);
  var model = on ? (LLM_CFG.model || 'deepseek-chat') : '';

  var st = document.getElementById('llmState');
  if (st) {
    st.textContent = on ? ('已绑定 · ' + model) : '游客模式';
    st.classList.toggle('on', on);
  }

  var badge = document.getElementById('capMode');
  if (badge) {
    badge.textContent = on ? '你的模型' : '游客模式';
    badge.classList.toggle('on', on);
  }

  var label = document.getElementById('apiLabel');
  if (label) label.textContent = on ? '已绑定' : '游客模式';
  var dot = document.getElementById('apiDot');
  if (dot) dot.classList.toggle('on', on);
  var btn = document.getElementById('apiOpen');
  if (btn) btn.classList.toggle('on', on);

  var state = document.getElementById('apiState');
  if (state) {
    state.textContent = on ? ('已绑定 · ' + model) : '游客模式';
    state.classList.toggle('on', on);
  }

  var lead = document.getElementById('llmLead');
  if (lead) {
    lead.textContent = on
      ? ('已绑定你的 ' + model + '：回答将由你的模型生成，仍然先在内置档案里检索证据，再组织语言。Key 只保存在这台电脑的浏览器里。')
      : '当前是游客模式：只用本站内置的 30 城档案检索作答，不调用任何模型，也不会编造。绑定自己的 API Key 后，回答由你的模型生成，Key 只存在这台电脑的浏览器里。';
  }
}

function topCorpus(q, n) {
  buildCorpus();
  var gs = qGrams(q);
  if (!gs.length) return [];
  var rows = [];
  for (var i = 0; i < CORPUS.length; i++) {
    var row = CORPUS[i], hit = 0;
    for (var j = 0; j < gs.length; j++) { if (row.t.indexOf(gs[j]) >= 0) hit += 1; }
    if (q.indexOf(row.c.city) >= 0) hit += 2;
    if (!hit) continue;
    var sc = hit / Math.sqrt(gs.length) + Math.min(row.t.length, 320) / 1600;
    if (row.h === '档案概览') sc -= 0.12;
    if (row.h === '街区摘要') sc -= 0.08;
    rows.push({ score: sc, hit: hit, row: row });
  }
  rows.sort(function (a, b) { return b.score - a.score; });
  var out = [], seen = {};
  for (var k = 0; k < rows.length && out.length < n; k++) {
    var key = rows[k].row.h + rows[k].row.t.slice(0, 12);
    if (seen[key]) continue;
    seen[key] = 1;
    out.push(rows[k].row);
  }
  return out;
}

function buildMessages(q) {
  var rows = topCorpus(q, 3);
  var ctx = rows.map(function (r, i) {
    return '[' + (i + 1) + '] 《' + r.c.city + ' · ' + r.c.title + '》· ' + r.h + NL + r.t;
  }).join(NL + NL);
  return [
    { role: 'system', content: '你是「拾光叙」的城市人文漫步向导，为大学生 Citywalk 与城市研学做讲解。规则：只依据【参考资料】回答；资料里没有的，明确说「资料中未记载」，禁止编造年代、人物、典故；中文回答，语气温润但信息准确，可分点；引用处用 [1][2] 标注来源编号；资料与问题无关时，先说明未收录，再给通用的研学建议。' },
    { role: 'user', content: '【参考资料】' + NL + (ctx || '（本次没有检索到资料）') + NL + NL + '【问题】' + NL + q }
  ];
}

function liveAsk(q, onDelta, onDone, onErr) {
  var cfg = LLM_CFG;
  if (!cfg || !cfg.key) { onErr(new Error('游客模式')); return; }
  var base = (cfg.base || 'https://api.deepseek.com').replace(/\/+$/, '');
  var ctrl = window.AbortController ? new AbortController() : null;
  var timer = setTimeout(function () { if (ctrl) ctrl.abort(); }, 90000);

  fetch(base + '/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + cfg.key
    },
    body: JSON.stringify({
      model: cfg.model || 'deepseek-chat',
      messages: buildMessages(q),
      stream: true,
      temperature: 0.6,
      max_tokens: 1200
    }),
    signal: ctrl ? ctrl.signal : undefined
  }).then(function (res) {
    if (!res.ok || !res.body) {
      return res.text().then(function (t) {
        var msg = 'HTTP ' + res.status + ' ' + (t || '').slice(0, 120);
        throw new Error(msg);
      });
    }
    var reader = res.body.getReader();
    var dec = new TextDecoder('utf-8');
    var buf = '';
    function pump() {
      return reader.read().then(function (r) {
        if (r.done) { clearTimeout(timer); onDone({}); return; }
        buf += dec.decode(r.value, { stream: true });
        var lines = buf.split(String.fromCharCode(10));
        buf = lines.pop() || '';
        lines.forEach(function (line) {
          if (line.indexOf('data:') !== 0) return;
          var payload = line.slice(5).trim();
          if (!payload || payload === '[DONE]') return;
          var obj = null;
          try { obj = JSON.parse(payload); } catch (e) { return; }
          var delta = obj.choices && obj.choices[0] && obj.choices[0].delta;
          if (delta && delta.content) onDelta(delta.content);
        });
        return pump();
      });
    }
    return pump();
  }).catch(function (err) { clearTimeout(timer); onErr(err); });
}

/* 本地检索：逐字显示 */
function typeLocal(bubble, text, done) {
  var hit = answerQuestion(text);
  var ans = hit.a, i = 0;
  var timer = setInterval(function () {
    i += 2;
    bubble.textContent = ans.slice(0, i);
    capBody.scrollTop = capBody.scrollHeight;
    if (i >= ans.length) { clearInterval(timer); done(hit); }
  }, 24);
}

function createBubble() {
  var d = document.createElement('div');
  d.className = 'msg ai';
  d.innerHTML = '<span class="avatar">叙</span><div class="bubble"></div>';
  capBody.appendChild(d);
  capBody.scrollTop = capBody.scrollHeight;
  return d.querySelector('.bubble');
}

/* ---------------- 视频弹层 ---------------- */
function openVideo(src, cap) {
  var modal = document.getElementById('vModal');
  var player = document.getElementById('vPlayer');
  if (!modal || !player) return;
  player.src = src;
  document.getElementById('vModalCap').textContent = cap || '';
  modal.classList.add('on');
  document.body.style.overflow = 'hidden';
  var p = player.play();
  if (p && p.catch) p.catch(function () { /* 需要用户再点一次 */ });
}

function closeVideo() {
  var modal = document.getElementById('vModal');
  var player = document.getElementById('vPlayer');
  if (!modal) return;
  modal.classList.remove('on');
  document.body.style.overflow = '';
  if (player) { player.pause(); player.removeAttribute('src'); player.load(); }
}

(function () {
  var bg = document.getElementById('vModalBg');
  var btn = document.getElementById('vModalClose');
  if (bg) bg.addEventListener('click', closeVideo);
  if (btn) btn.addEventListener('click', closeVideo);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeVideo();
  });
})();

/* ---------------- 接入模型：弹窗与事件 ---------------- */
(function () {
  var modal = document.getElementById('apiModal');
  if (!modal) return;
  var keyEl = document.getElementById('apiKey');
  var baseEl = document.getElementById('apiBase');
  var modelEl = document.getElementById('apiModel');
  var msg = document.getElementById('apiMsg');

  function fill() {
    if (LLM_CFG) {
      keyEl.value = LLM_CFG.key || '';
      baseEl.value = LLM_CFG.base || 'https://api.deepseek.com';
      modelEl.value = LLM_CFG.model || 'deepseek-chat';
    } else {
      keyEl.value = '';
      baseEl.value = 'https://api.deepseek.com';
      modelEl.value = 'deepseek-chat';
    }
    msg.textContent = '';
    msg.classList.remove('err');
  }

  function openModal() {
    fill();
    modal.classList.add('on');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    setTimeout(function () { keyEl.focus(); }, 200);
  }

  function closeModal() {
    modal.classList.remove('on');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  window.openApiModal = openModal;

  document.getElementById('apiOpen').addEventListener('click', openModal);
  var mobile = document.getElementById('apiOpenMobile');
  if (mobile) mobile.addEventListener('click', function (e) { e.preventDefault(); openModal(); });
  var llmOpen = document.getElementById('llmOpen');
  if (llmOpen) llmOpen.addEventListener('click', openModal);
  document.getElementById('apiClose').addEventListener('click', closeModal);
  document.getElementById('apiBg').addEventListener('click', closeModal);

  document.getElementById('apiSave').addEventListener('click', function () {
    var key = keyEl.value.trim();
    if (!key) {
      msg.textContent = '没有填写 Key。若要退出绑定，请点「清除」。';
      msg.classList.add('err');
      return;
    }
    saveLLM({ key: key, base: baseEl.value.trim() || 'https://api.deepseek.com', model: modelEl.value.trim() || 'deepseek-chat' });
    msg.textContent = '已保存。接下来提问会直接调用你的模型；若接口拒绝跨域，会自动退回资料检索。';
    msg.classList.remove('err');
    toast('已绑定你的 API Key');
  });

  var clear = function () {
    saveLLM(null);
    keyEl.value = '';
    msg.textContent = '已清除，回到游客模式：只返回资料原文，不调用任何模型。';
    msg.classList.remove('err');
    toast('已清除，回到游客模式');
  };
  document.getElementById('apiClear2').addEventListener('click', clear);
  var llmClear = document.getElementById('llmClear');
  if (llmClear) llmClear.addEventListener('click', clear);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modal.classList.contains('on')) closeModal();
  });
})();

/* ---------------- 初始化 ---------------- */
renderRoutePills();
loadRecs();
renderRecs();
renderVideos();
generateRoute(true);
markRouteSaved(false);
handleHash();

</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
