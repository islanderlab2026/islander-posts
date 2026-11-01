"""IG 數據自動收集（2026-11-02 王大人：都做、多用 dashboard 分析）
用 IG 官方 API 讀洞察（等同 App 專業主控板的數字），不用 Chrome：
1. 每支已發片在發後 48 小時、7 天各存一次快照（m48、m7d）到 posted/<檔名>.json
2. 每天存一次帳號數字（粉絲、近 7 天瀏覽／觸及／個人檔案瀏覽…）到 stats/<帳號>.json
任何錯誤都只印出來、不影響發片。"""
import os, json, datetime, pathlib, requests

API = "https://graph.instagram.com/v23.0"
TOKEN, UID = os.environ["IG_TOKEN"].strip(), os.environ["IG_USER_ID"].strip()
DONE = pathlib.Path(os.environ.get("DONE") or "posted")
ACC = os.environ.get("ACC") or "main"
now = datetime.datetime.now(datetime.timezone.utc)
MEDIA_METRICS = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions",
                 "ig_reels_avg_watch_time", "ig_reels_video_view_total_time", "follows", "profile_visits"]
ACCOUNT_METRICS = ["views", "reach", "accounts_engaged", "profile_views", "total_interactions", "shares", "follows_and_unfollows"]

def get(path, **p):
    p["access_token"] = TOKEN
    try:
        r = requests.get(f"{API}/{path}", params=p, timeout=60)
        d = r.json()
        return None if (r.status_code >= 400 or "error" in d) else d
    except Exception as e:
        print("API 失敗", path, e); return None

def val(item):
    if "total_value" in item: return item["total_value"].get("value")
    v = item.get("values") or []
    return v[-1].get("value") if v else None

def media_snapshot(mid, age_h):
    out = {"at": now.strftime("%Y-%m-%dT%H:%MZ"), "ageH": round(age_h, 1)}
    for m in MEDIA_METRICS:          # 一個一個要，某個指標不支援也不影響其他
        d = get(f"{mid}/insights", metric=m)
        if d and d.get("data"):
            out[m] = val(d["data"][0])
    if out.get("ig_reels_avg_watch_time") is not None:
        out["avgWatchSec"] = round(out["ig_reels_avg_watch_time"] / 1000, 1)
    return out

changed = 0
for f in sorted(DONE.glob("*.json")):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        mid, ts = d.get("mediaId") or d.get("id"), d.get("timestamp")
        if not mid or not ts: continue
        age_h = (now - datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")).total_seconds() / 3600
        for key, lo, hi in (("m48", 48, 24 * 6), ("m7d", 24 * 7, 24 * 30)):
            if key not in d and lo <= age_h < hi:
                d[key] = media_snapshot(mid, age_h); changed += 1
                print(f"{f.name} {key}: {d[key]}")
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print("略過", f.name, e)

sp = pathlib.Path("stats") / f"{ACC}.json"
st = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {"days": {}}
today = (now + datetime.timedelta(hours=8)).strftime("%Y-%m-%d")
if today not in st.get("days", {}):
    day = {}
    me = get("me", fields="followers_count,media_count")
    if me: day.update(followers=me.get("followers_count"), posts=me.get("media_count"))
    since, until = int((now - datetime.timedelta(days=7)).timestamp()), int(now.timestamp())
    for m in ACCOUNT_METRICS:
        d = get(f"{UID}/insights", metric=m, period="day", metric_type="total_value", since=since, until=until)
        if d and d.get("data"): day[m + "7d"] = val(d["data"][0])
    if day:
        st.setdefault("days", {})[today] = day
        st["days"] = dict(sorted(st["days"].items())[-120:])
        sp.parent.mkdir(exist_ok=True)
        sp.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        print("帳號數字", today, day)
print(f"完成：新增 {changed} 個快照")
