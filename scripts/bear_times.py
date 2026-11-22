"""熊貓中文時段測試：把每則貼文 48 小時的觸及、分享、收藏，依台灣發文整點（測 09／11／21／23 點，美國醒著的時段）彙整到 analysis/bear_times.json。
看哪個時段觸及中位數最高；每個時段至少 3 則才算數。"""
import json, pathlib, statistics, datetime

rows = []
for f in sorted(pathlib.Path("posted/bear").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    m = d.get("m48")
    if d.get("format") == "reel" and str(d.get("slot","")).endswith("-reel"):  # 輪播組加發的 Reels 不混進時段比較
        continue
    if not m or not d.get("timestamp"):
        continue
    t = datetime.datetime.strptime(d["timestamp"], "%Y-%m-%dT%H:%M:%S%z") + datetime.timedelta(hours=8)
    rows.append({"key": d.get("slot"), "twHour": t.hour, "format": d.get("format", "carousel"), "reach": m.get("reach") or 0,
                 "views": m.get("views") or 0, "shares": m.get("shares") or 0, "saved": m.get("saved") or 0})
slots = {}
for r in rows:
    slots.setdefault(r["twHour"], []).append(r)
out = {"generatedAt": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), "n": len(rows), "slots": {}}
for h in sorted(slots):
    rs = slots[h]
    out["slots"][f"{h:02d}"] = {"n": len(rs), "reachMedian": statistics.median(r["reach"] for r in rs),
                                "sharesSum": sum(r["shares"] for r in rs), "savedSum": sum(r["saved"] for r in rs),
                                "enough": len(rs) >= 3, "posts": [r["key"] for r in rs]}
ok = {h: s for h, s in out["slots"].items() if s["enough"]}
out["best"] = max(ok, key=lambda h: ok[h]["reachMedian"]) if ok else None
pathlib.Path("analysis").mkdir(exist_ok=True)
pathlib.Path("analysis/bear_times.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("時段分析完成", out["n"], "則｜最佳", out["best"])
