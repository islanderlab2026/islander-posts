"""IG 數據自動收集（2026-11-02 都做、多用 dashboard 分析）
用 IG 官方 API 讀洞察（等同 App 專業主控板的數字），不用 Chrome：
1. 每支已發片在發後 6 小時、48 小時、7 天各存一次快照（m48、m7d）到 posted/<檔名>.json
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

LAST_ERR = {"msg": None}
def get(path, **p):
    p["access_token"] = TOKEN
    try:
        r = requests.get(f"{API}/{path}", params=p, timeout=60)
        d = r.json()
        if r.status_code >= 400 or "error" in d:
            e = d.get("error") or {}
            LAST_ERR["msg"] = f"{r.status_code} {e.get('code')}/{e.get('error_subcode')} {str(e.get('message'))[:160]}"
            return None
        return d
    except Exception as e:
        LAST_ERR["msg"] = f"exception {str(e)[:160]}"
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
_lookup = None
def by_permalink(pl):                # 手動發的貼文只有網址：從帳號貼文清單找回 mediaId、時間
    global _lookup
    if _lookup is None:
        _lookup, after = {}, None
        for _ in range(4):           # 2026-11-22：最多翻 4 頁（約 200 支），舊版只看最新 50 支
            q = {"fields": "id,permalink,timestamp", "limit": 50}
            if after: q["after"] = after
            d = get("me/media", **q) or {}
            for x in d.get("data", []):
                _lookup[x.get("permalink", "").rstrip("/").split("/")[-1]] = x
            after = ((d.get("paging") or {}).get("cursors") or {}).get("after")
            if not after or not (d.get("paging") or {}).get("next"): break
    return _lookup.get(pl.rstrip("/").split("/")[-1])
for f in sorted(DONE.glob("*.json")):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        if not d.get("mediaId") and d.get("permalink"):
            x = by_permalink(d["permalink"])
            if x: d.update(mediaId=x["id"], timestamp=x["timestamp"])
        mid, ts = d.get("mediaId") or d.get("id"), d.get("timestamp")
        if not mid or not ts: continue
        # 2026-11-22 修正：17 支片快照一直拿到空資料（tries 37）。連續 3 次空就做診斷：
        # ① 用網址重新找 mediaId（不同就換掉）② 查這支片還在不在（封存或刪除時 API 讀不到）③ 把 IG 的錯誤訊息存進 diag。
        if any((d.get(k) or {}).get("empty") and (d.get(k) or {}).get("tries", 0) >= 3 for k in ("m6", "m48", "m7d")) \
                and d.get("diag", {}).get("day") != now.strftime("%Y-%m-%d"):
            diag = {"day": now.strftime("%Y-%m-%d")}
            if d.get("permalink"):
                x = by_permalink(d["permalink"])
                if x and x.get("id") and x["id"] != mid:
                    diag["oldId"], mid = mid, x["id"]; d["mediaId"] = d["id"] = mid
                    for k in ("m6", "m48", "m7d"):
                        if (d.get(k) or {}).get("empty"): d[k]["tries"] = 0
                diag["inMediaList"] = bool(x)
            info = get(mid, fields="id,media_product_type,timestamp")
            diag["exists"] = bool(info)
            if not info: diag["existsErr"] = LAST_ERR["msg"]
            t = get(f"{mid}/insights", metric="views")
            diag["viewsOk"] = bool(t and t.get("data"))
            if not diag["viewsOk"]: diag["viewsErr"] = LAST_ERR["msg"]
            d["diag"] = diag; changed += 1
            print(f"{f.name} 診斷：{diag}")
            if not diag["exists"] and not diag.get("inMediaList"):
                d["gone"] = True     # 片已不在（封存／刪除），不再重試；分析會列出來
        age_h = (now - datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")).total_seconds() / 3600
        # 2026-11-20 修正：IG 回空資料時舊版也當成「已抓過」，48 小時數字缺了 15 支。
        # 現在沒有 views 就視為沒抓到，下次整點再試；超過正常時段才補到的標 late（分析時不拿來算中位數）。
        for key, lo, hi, hi_retry, late_after in (("m6", 6, 48, 48, 12), ("m48", 48, 24 * 6, 24 * 30, 72),
                                                    ("m7d", 24 * 7, 24 * 30, 24 * 30, 24 * 8)):
            old = d.get(key)
            if old and old.get("views") is not None: continue
            if d.get("gone"): continue
            tries = (old or {}).get("tries", 0)
            if not (lo <= age_h < (hi if old is None else hi_retry)) or tries >= 72: continue
            snap = media_snapshot(mid, age_h)
            if snap.get("views") is None:
                d[key] = {**(old or {}), "at": snap["at"], "ageH": snap["ageH"], "tries": tries + 1, "empty": True}
                print(f"{f.name} {key}: IG 沒回數字（第 {tries + 1} 次），下次再試")
            else:
                if age_h > late_after: snap["late"] = True
                d[key] = snap
                print(f"{f.name} {key}: {snap}")
            changed += 1
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
