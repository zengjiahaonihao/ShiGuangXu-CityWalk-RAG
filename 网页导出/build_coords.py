"""为内置三十城的主要看点抓取坐标（Photon / OpenStreetMap，无需 Key）。

输出：backend/app/data/spot_coords.json
结构：{ city_id: { "center": [lng, lat], "spots": [{ "name": ..., "lat": ..., "lng": ... }] } }

坐标统一为 WGS84；前端地图组件内部再转 GCJ-02 叠到高德底图上。
脚本带本地缓存，重复执行只会补抓缺失项。
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.rag import builtin  # noqa: E402

OUT = ROOT / "backend" / "app" / "data" / "spot_coords.json"
PHOTON = "https://photon.komoot.io/api/"
UA = "shiguangxu-demo/1.0 (city humanities walk demo)"


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    lng1, lat1 = a
    lng2, lat2 = b
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def query(q: str, limit: int = 3) -> list[dict]:
    url = PHOTON + "?" + urllib.parse.urlencode({"q": q, "limit": limit})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    out = []
    for f in data.get("features", []):
        p = f.get("properties") or {}
        c = (f.get("geometry") or {}).get("coordinates") or []
        if len(c) < 2 or p.get("countrycode") != "CN":
            continue
        out.append(
            {
                "name": p.get("name") or "",
                "city": p.get("city") or p.get("county") or "",
                "state": p.get("state") or "",
                "lng": float(c[0]),
                "lat": float(c[1]),
            }
        )
    return out


DECOR = [
    "红砖厝", "骑楼群", "骑楼", "故居", "遗址", "建筑群", "牌坊", "会馆", "街区", "民居",
    "与东西塔", "与藏兵洞", "与水圳", "与马可波罗", "与九层楼", "与宝轮寺", "与唐蕃会盟碑",
    "与钢琴博物馆", "与风琴博物馆", "与掩埋坑", "与钟楼", "与南湖", "与月沼", "与南大街",
    "与民园", "与恭王府", "与什刹海", "与天后宫", "与瓮城", "与双林寺", "与云冈", "与龙门",
]


def candidates(name: str) -> list[str]:
    """把「开元寺与东西塔」这类描述性名称拆成可检索的核心地名。"""
    out = [name]
    for sep in ("——", "·", "（", "(", "与", "和"):
        if sep in name:
            out.append(name.split(sep)[0].strip())
    for d in DECOR:
        if name.endswith(d) and len(name) > len(d) + 1:
            out.append(name[: -len(d)].strip())
    # 去掉「X 座」「七十二」这类数量词尾巴
    out = [x for x in dict.fromkeys(out) if x and len(x) >= 2]
    return out[:4]


def pick(results: list[dict], city: str, center: tuple[float, float] | None) -> dict | None:
    """优先取城市匹配的结果；否则取离市中心最近的一个（限定 15km 内）。"""
    bare = city.replace("中国", "").replace("市", "").replace("县", "")
    pool = []
    for r in results:
        label = (r["city"] + r["state"]).replace("市", "")
        dist = haversine(center, (r["lng"], r["lat"])) if center else 0.0
        if center and dist > 15:
            continue
        pool.append((0 if (bare in label or city in label) else 1, dist, r))
    if not pool:
        return None
    pool.sort(key=lambda x: (x[0], x[1]))
    return pool[0][2]


def main() -> None:
    cache: dict = {}
    if OUT.exists():
        cache = json.loads(OUT.read_text(encoding="utf-8"))

    total = len(builtin.CITY_PROFILES)
    for i, p in enumerate(builtin.CITY_PROFILES, 1):
        cid = p["id"]
        entry = cache.get(cid) or {"center": None, "spots": []}
        city_label = p["city"].replace("中国", "")

        if not entry.get("center"):
            for cand in (f"{city_label} {p['district']}", city_label):
                try:
                    res = query(cand, 3)
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {cid} 城市中心失败: {e}")
                    res = []
                hit = pick(res, city_label, None)
                if hit:
                    entry["center"] = [hit["lng"], hit["lat"]]
                    break
                time.sleep(0.5)

        center = tuple(entry["center"]) if entry.get("center") else None
        done = {s["name"] for s in entry.get("spots", [])}
        for h in p["highlights"]:
            if h in done:
                continue
            hit = None
            for cand in candidates(h):
                try:
                    res = query(f"{cand} {city_label}", 4)
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {cand} 失败: {e}")
                    time.sleep(1.2)
                    continue
                hit = pick(res, city_label, center)
                if hit:
                    break
                time.sleep(0.3)
            if not hit:
                # 带城市名查不到时，单独查核心地名，再按距离就近取
                for cand in candidates(h)[:2]:
                    try:
                        res = query(cand, 8)
                    except Exception:  # noqa: BLE001
                        continue
                    hit = pick(res, city_label, center)
                    if hit:
                        break
                    time.sleep(0.3)
            if hit:
                entry.setdefault("spots", []).append(
                    {"name": h, "lat": round(hit["lat"], 6), "lng": round(hit["lng"], 6)}
                )
            time.sleep(0.45)

        cache[cid] = entry
        got = len(entry.get("spots", []))
        print(f"[{i}/{total}] {p['city']:<6} center={'ok' if entry.get('center') else '--'} spots={got}/{len(p['highlights'])}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    total_spots = sum(len(v.get("spots", [])) for v in cache.values())
    print(f"written {OUT}  cities={len(cache)}  spots={total_spots}")


if __name__ == "__main__":
    main()
