"""檢查 IG 權杖是否有效；REFRESH=1 時順便延長（權杖要滿 24 小時才能延長）。不會印出權杖。"""
import os, sys, requests
t = os.environ["IG_TOKEN"].strip()
r = requests.get("https://graph.instagram.com/me", params={"fields": "user_id,username", "access_token": t}, timeout=30).json()
if "error" in r:
    print("權杖無效：", r["error"].get("message")); sys.exit(1)
print("權杖有效，帳號：", r.get("username"))
if os.environ.get("REFRESH") == "1":
    x = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": t}, timeout=30).json()
    if "expires_in" in x:
        print("已延長，剩 %.0f 天" % (x["expires_in"] / 86400))
    else:
        print("這次沒延長：", x.get("error", {}).get("message"))
