"""發一支 Reel：queue/<日期>[-2].mp4 + .txt（文案）→ IG 官方 API → 搬到 posted/
SLOT=1 → queue/<日期>.mp4（每天 21:00）；SLOT=2 → queue/<日期>-2.mp4（週末 12:00）"""
import os, sys, time, json, shutil, datetime, pathlib, requests

API = "https://graph.instagram.com/v23.0"
TOKEN, UID = os.environ["IG_TOKEN"].strip(), os.environ["IG_USER_ID"].strip()
BASE = os.environ["PAGES_BASE"].rstrip("/")
tw = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
day = (os.environ.get("POST_DATE") or "").strip() or tw.strftime("%Y-%m-%d")
slot = (os.environ.get("SLOT") or "").strip() or "1"
name = day if slot == "1" else f"{day}-{slot}"
# 2026-11 時段測試：queue/times.json {"日期": 小時}，沒寫的日子＝21 點；手動指定日期時不擋
_tf = pathlib.Path("queue/times.json")
_times = json.loads(_tf.read_text(encoding="utf-8")) if _tf.exists() else {}
if slot == "1" and not (os.environ.get("POST_DATE") or "").strip():
    _want = int(_times.get(day, 21))
    if tw.hour < _want - 1:
        print(f"{day} 指定 {_want} 點發，現在 {tw.hour} 點，先不發"); sys.exit(0)
q, done = pathlib.Path(os.environ.get("QDIR") or "queue"), pathlib.Path(os.environ.get("DONE") or "posted")  # furfriend：queue/fur、posted/fur
# queue/order.json：{"發片時段": "影片檔名"}，照分數重排時只改這個檔
order = json.loads((q / "order.json").read_text(encoding="utf-8")) if (q / "order.json").exists() else {}
if name not in order and name in order.values():
    print(f"{name} 的影片已改到別的時段，今天不發"); sys.exit(0)
src = order.get(name, name)
video, cap = q / f"{src}.mp4", q / f"{src}.txt"
if not video.exists():
    print(f"沒有 {video}，今天不發"); sys.exit(0)
caption = cap.read_text(encoding="utf-8").strip() if cap.exists() else ""

# 2026-11-01 芭蕾 Gemini 原檔（720 寬、沒重新轉檔）上 IG 變綠色花屏 → 沒升級到 1080 的檔一律不發
import struct
def _mp4_check(p):
    """回傳 (寬, 關鍵格間距最大秒數)；檔案沒重新轉檔（Gemini 原檔）會被擋"""
    d = open(p, "rb").read()
    def boxes(s, e):
        while s + 8 <= e:
            n, t = struct.unpack(">I4s", d[s:s+8]); h = 8
            if n == 1: n = struct.unpack(">Q", d[s+8:s+16])[0]; h = 16
            if n == 0: n = e - s
            yield t, s + h, s + n; s += n
    def find(s, e, path):
        for t, a, b in boxes(s, e):
            if t == path[0]:
                if len(path) == 1: return a, b
                r = find(a, b, path[1:])
                if r: return r
    moov = find(0, len(d), [b"moov"])
    for t, a, b in boxes(*moov):
        if t != b"trak": continue
        hd = find(a, b, [b"mdia", b"hdlr"])
        if not hd or d[hd[0]+8:hd[0]+12] != b"vide": continue
        tk = find(a, b, [b"tkhd"]); w = struct.unpack(">I", d[tk[1]-8:tk[1]-4])[0] >> 16
        md = find(a, b, [b"mdia", b"mdhd"]); v = d[md[0]]
        ts, du = (struct.unpack(">IQ", d[md[0]+20:md[0]+32]) if v == 1 else struct.unpack(">II", d[md[0]+12:md[0]+20]))
        st = find(a, b, [b"mdia", b"minf", b"stbl"])
        sz = find(*st, [b"stsz"]); n = struct.unpack(">I", d[sz[0]+8:sz[0]+12])[0]
        ss = find(*st, [b"stss"])
        keys = [struct.unpack(">I", d[ss[0]+8+4*i:ss[0]+12+4*i])[0] for i in range(struct.unpack(">I", d[ss[0]+4:ss[0]+8])[0])] if ss else list(range(1, n+1))
        fps = n / (du / ts)
        gaps = [b2 - a2 for a2, b2 in zip(keys, keys[1:] + [n + 1])]
        return w, max(gaps) / fps
    return 0, 99
_w, _gap = _mp4_check(video)
print(f"檢查影片：寬 {_w}、關鍵格最大間距 {_gap:.1f} 秒")
if _w < 1080:
    sys.exit(f"規則：{video} 只有 {_w} 寬，沒重新轉檔（會花屏），不發")
MANGO_OK = {"2026-10-30"}   # 王大人親自選的黏土芒果寶寶，唯一例外
if ("芒果" in caption or "mango" in caption.lower()) and src not in MANGO_OK:
    sys.exit("規則：不發芒果")

def call(method, path, **params):
    params["access_token"] = TOKEN
    r = requests.request(method, f"{API}/{path}", params=params, timeout=60)
    d = r.json()
    if r.status_code >= 400 or "error" in d:
        sys.exit(f"API 錯誤 {path}: {json.dumps(d, ensure_ascii=False)}")
    return d

url = f"{BASE}/{q.as_posix()}/{src}.mp4"
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

# 2026-11-01 王大人要求：發完要檢核影片有沒有問題（芭蕾曾在 IG 轉檔後變綠色花屏）
# 從 IG 下載發出去的版本，跟原檔比 PSNR；< 22 dB 視為花屏（正常約 35 dB 以上）
import subprocess, re, shutil
def _psnr(a, b):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", a, "-i", b, "-lavfi",
        "[0:v]scale=360:640,setsar=1,format=yuv420p[x];[1:v]scale=360:640,setsar=1,format=yuv420p[y];[x][y]psnr",
        "-f", "null", "-"], capture_output=True, text=True, timeout=300)
    m = re.search(r"average:([0-9.]+|inf)", r.stderr)
    return 99.0 if m and m.group(1) == "inf" else (float(m.group(1)) if m else -1.0)
check, psnr = "unknown", None
try:
    if not shutil.which("ffmpeg"):
        subprocess.run("sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg", shell=True, timeout=300)
    mu = ""
    for _ in range(8):
        mu = call("GET", m["id"], fields="media_url").get("media_url", "")
        if mu: break
        time.sleep(15)
    if mu:
        with open("/tmp/ig.mp4", "wb") as f: f.write(requests.get(mu, timeout=120).content)
        psnr = round(_psnr("/tmp/ig.mp4", str(video)), 1)
        check = "ok" if psnr >= 22 else ("bad" if psnr >= 0 else "unknown")
    print(f"發後檢核：{check}（PSNR {psnr} dB）")
except BaseException as e:  # call() 失敗會 sys.exit，這裡要攔住，片才會照常搬到 posted/
    print("發後檢核失敗：", e)
done.mkdir(parents=True, exist_ok=True)
shutil.move(str(video), done / video.name)
if cap.exists(): shutil.move(str(cap), done / cap.name)
(done / f"{src}.json").write_text(json.dumps({"mediaId": m["id"], "slot": name, **info, "check": check, "psnr": psnr}, ensure_ascii=False), encoding="utf-8")
if check == "bad":
    sys.exit(f"發後檢核不合格：IG 上的版本跟原檔差太多（PSNR {psnr} dB），可能花屏，請人工確認")
