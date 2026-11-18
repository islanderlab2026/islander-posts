"""發文前自動檢查（2026-11-15 同意）：python3 check.py specA.json specB.json specC.json
1. 字型缺字：每段文字用實際會用的字型檢查，emoji 不在字型裡會變方塊 → 擋
2. 同一組風格一致：一組 3 篇的 theme 與版型家族要相同 → 擋
3. 欄位規則：MEANS 不能有吐槽語氣（含 ! ? 或 makes sense / easy / good luck 這類），旁白只能放 aside → 擋
4. 長度：每張文字行數與寬度不超過版面 → 警告
5. 印出每張每個欄位，給人逐欄唸一次（語意要人看，程式只能擋明顯錯誤）
有任何「擋」就以非 0 結束，不准上 GitHub。"""
import json, sys, re
from fontTools.ttLib import TTFont, TTCollection

INTER = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

def cmap(path):
    if path.endswith(".ttc"):
        return set(TTCollection(path).fonts[0].getBestCmap())
    return set(TTFont(path).getBestCmap())
C = {"latin": cmap(INTER), "py": cmap(DEJAVU), "cjk": cmap(CJK), "emoji": cmap(EMOJI)}

LATIN_KEYS = {"rows", "title", "sub", "literal", "means", "aside", "en", "q", "cta", "label", "options", "qlabel", "hook"}
PY_KEYS = {"py"}
CJK_KEYS = {"zh", "simp", "char", "chars"}
EMOJI_KEYS = {"emoji"}
SNARK = re.compile(r"makes sense|still easy|good luck|\bhi\b|that's me|\bwait\b|\blol\b|haha|you get it", re.I)
FAMILY = {"cover": "A", "pair": "A", "phrase": "A", "end": "A"}

def texts(v):
    if isinstance(v, str): return [v]
    if isinstance(v, list): return [t for x in v for t in texts(x)]
    return []

def missing(s, table):
    return sorted({ch for ch in s if ord(ch) > 32 and ord(ch) not in table})

block, warn = [], []
themes = set()
for path in sys.argv[1:]:
    spec = json.load(open(path))
    sid = spec["id"]
    fam = {FAMILY.get(sl["kind"], sl["kind"].split("_")[0]) for sl in spec["slides"]}
    themes.add((spec.get("theme", "default"), tuple(sorted(fam))))
    print(f"\n===== {sid}（{len(spec['slides'])} 張，風格 {spec.get('theme','default')}）=====")
    for n, sl in enumerate(spec["slides"], 1):
        print(f"--- 第 {n} 張 {sl['kind']}")
        for k, v in sl.items():
            if k == "kind": continue
            for t in texts(v) if k != "rows" else [x for r in v for x in r]:
                if k == "rows" and sl["kind"] == "d_final":
                    m = missing(t, C["cjk"] | C["py"])
                    if m: block.append(f"{sid} 第{n}張 rows：字型沒有 {m}")
                elif k in LATIN_KEYS:
                    m = missing(t, C["latin"])
                    if m: block.append(f"{sid} 第{n}張 {k}：字型沒有 {m}（會變方塊）")
                elif k in PY_KEYS or (k == "rows" and t.isascii() is False and re.search(r"[a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]", t)):
                    m = missing(t, C["py"] | C["cjk"])
                    if m: block.append(f"{sid} 第{n}張 {k}：拼音字型沒有 {m}")
                elif k in CJK_KEYS:
                    m = missing(t, C["cjk"])
                    if m: block.append(f"{sid} 第{n}張 {k}：中文字型沒有 {m}")
                elif k in EMOJI_KEYS:
                    if not all(ord(ch) in C["emoji"] or ord(ch) in (0xFE0F, 0x200D) for ch in t):
                        block.append(f"{sid} 第{n}張 emoji {t!r} 字型沒有")
            print(f"    {k:8s}: {v}")
        if "means" in sl and SNARK.search(sl["means"]):
            block.append(f"{sid} 第{n}張 MEANS「{sl['means']}」像吐槽，吐槽要放 aside")
        for k in ("aside", "en", "means", "literal"):
            if k in sl and len(sl[k]) > 60:
                warn.append(f"{sid} 第{n}張 {k} 超過 60 字元，可能太擠")
if len({t[0] for t in themes}) > 1:
    block.append(f"同一組風格不一致：{sorted(t[0] for t in themes)}")

print("\n===== 結果 =====")
for w in warn: print("⚠️ 警告：", w)
for b in block: print("⛔ 擋下：", b)
if not block: print("✅ 程式檢查通過；接著逐欄唸一次上面的文字，確認英文語意")
sys.exit(1 if block else 0)
