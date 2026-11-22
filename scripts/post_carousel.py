"""熊貓中文（bearcat.chinese）輪播自動發文。
queue/bear/times.json：{"<貼文代號>": "YYYY-MM-DDTHH:MM"}（台灣時間）
queue/bear/<貼文代號>/1.jpg … N.jpg ＋ caption.txt
每次執行：把「時間已到、還沒發」的貼文依時間、代號順序全部發出去（一組 3 篇一起發），搬到 posted/bear/<代號>/，寫 posted/bear/<代號>.json。
2026-11-15 串接 GitHub 自動發；一次發一組（3 篇一起），用不同組測不同時段，之後固定最好的時段。"""
import os, sys, time, json, shutil, datetime, pathlib, requests, subprocess, secrets, tarfile

# 2026-11-21 加密：資料夾內容打包加密成 payload.tar.enc＋key.enc（公開鑰匙上鎖，GitHub 密鑰 QUEUE_PRIVKEY 解鎖）。
# 發片時解開到 /tmp，放到隨機名稱的暫時下載點讓 IG 抓，發完刪掉暫時下載點。
REPO = os.environ.get("GITHUB_REPOSITORY", "islanderlab2026/islander-posts")
def unlock(folder):
    pk = os.environ.get("QUEUE_PRIVKEY", "").strip()
    if not pk: sys.exit(f"{folder.name} 是加密的但沒有 QUEUE_PRIVKEY 密鑰，不發")
    kp = pathlib.Path("/tmp/qpriv.pem"); kp.write_text(pk + "\n"); os.chmod(kp, 0o600)
    pw = subprocess.run(["openssl", "pkeyutl", "-decrypt", "-inkey", str(kp), "-pkeyopt", "rsa_padding_mode:oaep",
                         "-pkeyopt", "rsa_oaep_md:sha256", "-in", str(folder / "key.enc")],
                        check=True, capture_output=True).stdout.decode().strip()
    kp.unlink()
    out = pathlib.Path("/tmp/bear") / folder.name; out.mkdir(parents=True, exist_ok=True)
    tar = out / "p.tar"
    subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-in", str(folder / "payload.tar.enc"),
                    "-out", str(tar), "-pass", "env:QK"], check=True, env={**os.environ, "QK": pw})
    with tarfile.open(tar) as tf: tf.extractall(out, filter="data")
    tar.unlink()
    return out

API = "https://graph.instagram.com/v23.0"
TOKEN, UID = os.environ["IG_TOKEN"].strip(), os.environ["IG_USER_ID"].strip()
BASE = os.environ["PAGES_BASE"].rstrip("/")
Q, DONE = pathlib.Path("queue/bear"), pathlib.Path("posted/bear")
tw = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
times = json.loads((Q / "times.json").read_text(encoding="utf-8")) if (Q / "times.json").exists() else {}
only = (os.environ.get("ONLY") or "").strip()  # 手動指定代號：不管時間直接發

due = []
for key, at in times.items():
    if key.startswith("_") or not (Q / key).is_dir():
        continue
    when = datetime.datetime.strptime(at, "%Y-%m-%dT%H:%M")
    if (only and key == only) or (not only and when <= tw + datetime.timedelta(minutes=15)):
        due.append((when, key))
if not due:
    print("沒有到時間的貼文"); sys.exit(0)
def post_one(when, key):
    folder = Q / key
    enc = (folder / "payload.tar.enc").exists()
    src = unlock(folder) if enc else folder
    imgs = sorted(src.glob("*.jpg"), key=lambda p: int(p.stem))
    cap = (src / "caption.txt").read_text(encoding="utf-8").strip() if (src / "caption.txt").exists() else ""
    tmp = {"tag": None, "rnd": secrets.token_hex(16)}
    def host(p):
        """回傳讓 IG 抓的網址：加密的放暫時下載點，沒加密的用 GitHub 網頁"""
        if not enc: return f"{BASE}/{folder.as_posix()}/{p.name}"
        if not tmp["tag"]:
            tmp["tag"] = f"tmp-{tmp['rnd']}"
            subprocess.run(["gh", "release", "create", tmp["tag"], "--repo", REPO, "--title", "tmp", "--notes", "",
                            "--latest=false"], check=True)
        name = f"{tmp['rnd']}-{p.name}"; up = pathlib.Path("/tmp") / name; shutil.copy(p, up)
        subprocess.run(["gh", "release", "upload", tmp["tag"], str(up), "--repo", REPO], check=True)
        return f"https://github.com/{REPO}/releases/download/{tmp['tag']}/{name}"
    try:
        _post_one(when, key, folder, src, enc, imgs, cap, host)
    finally:
        if tmp["tag"]:
            subprocess.run(["gh", "release", "delete", tmp["tag"], "--repo", REPO, "--yes", "--cleanup-tag"])

def _post_one(when, key, folder, src, enc, imgs, cap, host):
    if not 2 <= len(imgs) <= 10:
        sys.exit(f"{key} 有 {len(imgs)} 張圖，輪播要 2–10 張，不發")

    def call(method, path, **params):
        params["access_token"] = TOKEN
        r = requests.request(method, f"{API}/{path}", params=params, timeout=60)
        d = r.json()
        if r.status_code >= 400 or "error" in d:
            sys.exit(f"API 錯誤 {path}: {json.dumps(d, ensure_ascii=False)}")
        return d

    def wait(cid):
        for _ in range(40):
            s = call("GET", cid, fields="status_code")
            if s.get("status_code") == "FINISHED": return
            if s.get("status_code") == "ERROR": sys.exit(f"處理失敗：{s}")
            time.sleep(10)
        sys.exit("處理逾時")

    def post_reel(share):
        vu = host(src / "reel.mp4")
        for _ in range(30):
            if requests.head(vu, timeout=20, allow_redirects=True).status_code == 200: break
            time.sleep(10)
        else:
            sys.exit(f"Pages 還沒有 {vu}")
        rc = call("POST", f"{UID}/media", media_type="REELS", video_url=vu, caption=cap,
                  share_to_feed=share, thumb_offset="500")   # 封面用第 0.5 秒（封面字卡）
        wait(rc["id"])
        rm = call("POST", f"{UID}/media_publish", creation_id=rc["id"])
        return {"mediaId": rm["id"], **call("GET", rm["id"], fields="permalink,media_product_type,timestamp")}

    if (folder / "reel_only").exists():  # 2026-11-16 這組只發 Reels（一組 3 支）
        reel = post_reel("true")
        print("Reels 已發布", key, json.dumps(reel, ensure_ascii=False))
        DONE.mkdir(parents=True, exist_ok=True)
        shutil.move(str(folder), DONE / key)
        if enc and cap: (DONE / key / "caption.txt").write_text(cap + "\n", encoding="utf-8")
        (DONE / f"{key}.json").write_text(json.dumps(
            {**reel, "slot": key, "plannedTW": when.strftime("%Y-%m-%dT%H:%M"), "format": "reel", "slides": len(imgs)},
            ensure_ascii=False), encoding="utf-8")
        return

    urls = [host(p) for p in imgs]
    for u in urls:                      # 等網址可以讀（最多 5 分鐘）
        for _ in range(30):
            if requests.head(u, timeout=20, allow_redirects=True).status_code == 200: break
            time.sleep(10)
        else:
            sys.exit(f"Pages 還沒有 {u}")

    kids = []
    for u in urls:
        c = call("POST", f"{UID}/media", image_url=u, is_carousel_item="true")
        wait(c["id"]); kids.append(c["id"])
    box = call("POST", f"{UID}/media", media_type="CAROUSEL", children=",".join(kids), caption=cap)
    wait(box["id"])
    m = call("POST", f"{UID}/media_publish", creation_id=box["id"])
    info = call("GET", m["id"], fields="permalink,media_product_type,timestamp")
    print("已發布", key, json.dumps(info, ensure_ascii=False))

    reel = None                          # 同資料夾有 reel.mp4 → 另外發一支 Reels（接觸非粉絲）
    if (src / "reel.mp4").exists():
        try:
            time.sleep(60)
            reel = post_reel("true")
            print("Reels 已發布", key, json.dumps(reel, ensure_ascii=False))
        except SystemExit as e:          # Reels 失敗不影響輪播紀錄
            print("Reels 失敗", e)

    DONE.mkdir(parents=True, exist_ok=True)
    shutil.move(str(folder), DONE / key)
    if enc and cap: (DONE / key / "caption.txt").write_text(cap + "\n", encoding="utf-8")
    (DONE / f"{key}.json").write_text(json.dumps(
        {"mediaId": m["id"], "slot": key, "plannedTW": when.strftime("%Y-%m-%dT%H:%M"), "slides": len(imgs), **info},
        ensure_ascii=False), encoding="utf-8")
    if reel:
        (DONE / f"{key}-reel.json").write_text(json.dumps(
            {**reel, "slot": f"{key}-reel", "plannedTW": when.strftime("%Y-%m-%dT%H:%M"), "format": "reel"},
            ensure_ascii=False), encoding="utf-8")


for i, (when, key) in enumerate(sorted(due)):
    if i: time.sleep(60)
    post_one(when, key)
