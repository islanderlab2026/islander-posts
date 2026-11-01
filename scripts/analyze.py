"""每天自動分析（2026-11-02 王大人選 A：數字由程式算，週一研究只讀 analysis/latest.json）
讀 posted/*.json（m48、m7d）、stats/*.json、meta/*.json → 寫 analysis/latest.json"""
import json, pathlib, datetime, statistics as st

now = datetime.datetime.now(datetime.timezone.utc)
TW = datetime.timedelta(hours=8)
MID = {"A": 120, "B": 350, "C": 750, "D": 2000, "E": 4500}          # 預測級距中點
ORDER = "ABCDE"

def load(p, default):
    try: return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception: return default

def bucket(v):
    return "A" if v < 200 else "B" if v < 500 else "C" if v < 1000 else "D" if v < 3000 else "E"

def rank(xs):
    s = sorted(range(len(xs)), key=lambda i: xs[i]); r = [0.0] * len(xs); i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and xs[s[j + 1]] == xs[s[i]]: j += 1
        for k in range(i, j + 1): r[s[k]] = (i + j) / 2 + 1
        i = j + 1
    return r

def spearman(a, b):
    if len(a) < 4: return None
    ra, rb = rank(a), rank(b)
    ma, mb = st.mean(ra), st.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return round(num / den, 2) if den else None

def group(rows, key):
    g = {}
    for r in rows: g.setdefault(r.get(key) or "未分類", []).append(r["views48"])
    return {k: {"n": len(v), "avg48": round(st.mean(v)), "median48": round(st.median(v))} for k, v in sorted(g.items(), key=lambda x: -st.mean(x[1]))}

def account(acc, folder):
    meta = load(f"meta/{acc}.json", {})
    rows, pending = [], []
    for f in sorted(pathlib.Path(folder).glob("*.json")):
        d = load(f, {})
        ts = d.get("timestamp")
        if not ts: continue
        t = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")
        tw = t + TW
        h = tw.hour + tw.minute / 60
        slot = "12點" if h < 15 else "18點" if h < 19.5 else "21點"
        m = meta.get(f.stem, {})
        base = {"file": f.stem, "title": m.get("title", f.stem), "kind": m.get("kind"), "score": m.get("score"),
                "scoreVer": m.get("scoreVer"), "predView": m.get("predView"), "experiment": m.get("experiment"),
                "postedTW": tw.strftime("%m/%d %H:%M"), "weekday": "一二三四五六日"[tw.weekday()], "slot": slot,
                "check": d.get("check")}
        m48 = d.get("m48")
        if not m48 or m48.get("views") is None:
            pending.append({**base, "ageH": round((now - t).total_seconds() / 3600, 1)}); continue
        reach = m48.get("reach") or 0
        r = {**base, "views48": m48["views"], "reach48": reach, "avgWatchSec": m48.get("avgWatchSec"),
             "shares48": m48.get("shares", 0), "saved48": m48.get("saved", 0), "likes48": m48.get("likes", 0),
             "shareRate": round(m48.get("shares", 0) / reach * 100, 2) if reach else 0,
             "saveRate": round(m48.get("saved", 0) / reach * 100, 2) if reach else 0,
             "snapAgeH": m48.get("ageH"), "views7d": (d.get("m7d") or {}).get("views")}
        r["actualBucket"] = bucket(r["views48"])
        if r["predView"] in MID:
            r["predHit"] = r["predView"] == r["actualBucket"]
            r["predWithin1"] = abs(ORDER.index(r["predView"]) - ORDER.index(r["actualBucket"])) <= 1
            r["vsPred"] = round(r["views48"] / MID[r["predView"]], 2)
        rows.append(r)
    out = {"n48": len(rows), "pending": pending, "posts": sorted(rows, key=lambda r: -r["views48"])}
    if rows:
        v = [r["views48"] for r in rows]
        out["views48"] = {"median": round(st.median(v)), "mean": round(st.mean(v)), "max": max(v), "min": min(v)}
        aw = [r["avgWatchSec"] for r in rows if r["avgWatchSec"] is not None]
        out["avgWatchSec"] = round(st.mean(aw), 1) if aw else None
        out["shareRatePct"] = round(st.mean([r["shareRate"] for r in rows]), 2)
        out["saveRatePct"] = round(st.mean([r["saveRate"] for r in rows]), 2)
        out["sharesTotal"] = sum(r["shares48"] for r in rows)
        out["byKind"] = group(rows, "kind")
        out["bySlot"] = group(rows, "slot")
        out["byExperiment"] = group([r for r in rows if r.get("experiment")], "experiment")
        sc = [r for r in rows if r["score"] is not None]
        out["scoreVsViews_spearman"] = spearman([r["score"] for r in sc], [r["views48"] for r in sc])
        out["avgWatchVsViews_spearman"] = spearman([r["avgWatchSec"] for r in rows if r["avgWatchSec"] is not None],
                                                   [r["views48"] for r in rows if r["avgWatchSec"] is not None])
        pr = [r for r in rows if "predHit" in r]
        out["prediction"] = {"n": len(pr), "hitPct": round(sum(r["predHit"] for r in pr) / len(pr) * 100) if pr else None,
                             "within1Pct": round(sum(r["predWithin1"] for r in pr) / len(pr) * 100) if pr else None}
        vp = {}
        for r in pr: vp.setdefault(r["slot"], []).append(r["vsPred"])
        out["slotVsPred"] = {k: {"n": len(x), "avg": round(st.mean(x), 2)} for k, x in vp.items()}
    s = load(f"stats/{acc}.json", {}).get("days", {})
    if s:
        days = sorted(s)
        last = s[days[-1]]
        wk = [d for d in days if d <= (datetime.date.fromisoformat(days[-1]) - datetime.timedelta(days=7)).isoformat()]
        out["account"] = {"date": days[-1], **last,
                          "followers7dAgo": s[wk[-1]].get("followers") if wk else None,
                          "followersHistory": {d: s[d].get("followers") for d in days[-30:]}}
    return out

res = {"generatedAt": (now + TW).strftime("%Y-%m-%d %H:%M"), "note": "views48＝發後 48 小時快照（ageH 為實際小時數）；slot 依實際發文時間分 12／18／21 點；vsPred＝實際÷預測級距中點",
       "main": account("main", "posted"), "fur": account("fur", "posted/fur")}
pathlib.Path("analysis").mkdir(exist_ok=True)
pathlib.Path("analysis/latest.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("分析完成", res["generatedAt"], "島民 n48=", res["main"]["n48"], "fur n48=", res["fur"]["n48"])
