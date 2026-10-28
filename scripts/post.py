"""發一支 Reel：queue/<日期>.mp4 + queue/<日期>.txt（文案）→ IG 官方 API → 搬到 posted/"""
import os, sys, time, json, shutil, datetime, pathlib, requests

API = "https://graph.instagram.com/v23.0"
TOKEN, UID = os.environ["IG_TOKEN"], os.environ["IG_USER_ID"]
BASE = os.environ["PAGES_BASE"].rstrip("/")
tw = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
day = (os.environ.get("POST_DATE") or "").strip() or tw.strftime("%Y-%m-%d")
q, done = pathlib.Path("queue"), pathlib.Path("posted")
video, cap = q / f"{day}.mp4", q / f"{day}.txt"
if not video.exists():
    print(f"沒有 {video}，今天不發"); sys.exit(0)
caption = cap.read_text(encoding="utf-8").strip() if cap.exists() else ""
if "芒果" in caption or "mango" in caption.lower():
    sys.exit("規則：不發芒果")

def call(method, path, **params):
    params["access_token"] = TOKEN
    r = requests.request(method, f"{API}/{path}", params=params, timeout=60)
    d = r.json()
    if r.status_code >= 400 or "error" in d:
        sys.exit(f"API 錯誤 {path}: {json.dumps(d, ensure_ascii=False)}")
    return d

url = f"{BASE}/queue/{day}.mp4"
# 等 GitHub Pages 有這個檔（最多 5 分鐘）
for _ in range(30):
    if requests.head(url, timeout=20).status_code == 200: break
    time.sleep(10)
else:
    sys.exit(f"Pages 還沒有 {url}")

c = call("POST", f"{UID}/media", media_type="REELS", video_url=url, caption=caption, share_to_feed="true")
cid = c["id"]
for _ in range(40):                     # 最多約 10 分鐘
    s = call("GET", cid, fields="status_code,status")
    if s.get("status_code") == "FINISHED": break
    if s.get("status_code") == "ERROR": sys.exit(f"處理失敗：{s}")
    time.sleep(15)
else:
    sys.exit("處理逾時")
m = call("POST", f"{UID}/media_publish", creation_id=cid)
info = call("GET", m["id"], fields="permalink,media_product_type,timestamp")
print("已發布", json.dumps(info, ensure_ascii=False))
done.mkdir(exist_ok=True)
shutil.move(str(video), done / video.name)
if cap.exists(): shutil.move(str(cap), done / cap.name)
(done / f"{day}.json").write_text(json.dumps({"mediaId": m["id"], **info}, ensure_ascii=False), encoding="utf-8")
