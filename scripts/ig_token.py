"""檢查 IG 權杖是否有效；REFRESH=1 時順便延長（權杖要滿 24 小時才能延長）。不會印出權杖。"""
import os, sys, re, requests
t = os.environ["IG_TOKEN"].strip()
print("權杖長度", len(t), "｜IG 開頭", t.startswith("IG"), "｜含空白", any(c.isspace() for c in t),
      "｜全英數", bool(re.fullmatch(r"[A-Za-z0-9_\-]+", t)), "｜含省略號", ("..." in t or "…" in t))
r = None
for base in ("https://graph.instagram.com/v23.0", "https://graph.instagram.com"):
    r = requests.get(f"{base}/me", params={"fields": "user_id,username", "access_token": t}, timeout=30).json()
    if "error" not in r: break
    e = r["error"]; print(base, "→", e.get("message"), e.get("type"), e.get("code"))
if "error" in r: sys.exit(1)
print("權杖有效，帳號：", r.get("username"))
if os.environ.get("REFRESH") == "1":
    x = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": t}, timeout=30).json()
    print("已延長，剩 %.0f 天" % (x["expires_in"] / 86400) if "expires_in" in x else ("這次沒延長：", x.get("error", {}).get("message")))
