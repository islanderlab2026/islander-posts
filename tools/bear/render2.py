"""Three extra visual styles for bearcat.chinese: grid (pictograph), dark (challenge), quiz."""
import json, sys, os
from PIL import Image, ImageDraw
from render import (W, H, CJK, CJK_R, POP_B, POP_SB, PY, INK, SOFT, YEL,
                    ttc, font, emoji_img, ctext, wrap, panda)

SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"

PYC = (47, 124, 246); TITLE = None; OPT_FILL = (255, 255, 255); DASH = (238, 170, 160)
# ---------- shared ----------
def frame(bg, fg, n, total):
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    panda(img, 60, H - 120, 64)
    d.text((140, H - 104), "@bearcat.chinese", font=font(POP_SB, 30), fill=fg)
    t = f"{n}/{total}"
    d.text((W - 60 - d.textlength(t, font=font(POP_SB, 30)), H - 104), t, font=font(POP_SB, 30), fill=fg)
    return img, d

def lines_center(d, y, lines, f, fill, gap):
    for ln in lines:
        ctext(d, y, ln, f, fill); y += gap
    return y

# ---------- style 1: grid paper (pictograph) ----------
PAPER = (251, 247, 238); GRID = (214, 74, 60); GINK = (36, 33, 30); GSOFT = (120, 110, 98)

def rice_grid(d, x, y, s):
    d.rectangle([x, y, x + s, y + s], outline=GRID, width=5)
    dash = lambda a, b: [d.line([a[0] + (b[0] - a[0]) * i / 24, a[1] + (b[1] - a[1]) * i / 24,
                                 a[0] + (b[0] - a[0]) * (i + .5) / 24, a[1] + (b[1] - a[1]) * (i + .5) / 24],
                                fill=DASH, width=3) for i in range(24)]
    dash((x, y + s / 2), (x + s, y + s / 2)); dash((x + s / 2, y), (x + s / 2, y + s))
    dash((x, y), (x + s, y + s)); dash((x + s, y), (x, y + s))

def grid_char(d, x, y, s, ch):
    rice_grid(d, x, y, s)
    f = ttc(SERIF, int(s * .78))
    bb = d.textbbox((0, 0), ch, font=f)
    d.text((x + (s - (bb[2] - bb[0])) / 2 - bb[0], y + (s - (bb[3] - bb[1])) / 2 - bb[1]), ch, font=f, fill=GINK)

def g_cover(c, n, t):
    img, d = frame(PAPER, GSOFT, n, t)
    y = lines_center(d, 150, c["title"], font(POP_B, 82), TITLE or GINK, 96)
    grid_char(d, (W - 420) // 2, y + 60, 420, c["char"])
    ctext(d, y + 540, c["sub"], font(POP_SB, 44), GRID)
    return img

def g_char(c, n, t):
    img, d = frame(PAPER, GSOFT, n, t)
    k = len(c["chars"]); s = 520 if k == 1 else (400 if k == 2 else 290)
    gap = 40; tot = k * s + (k - 1) * gap; x = (W - tot) // 2
    for ch in c["chars"]:
        grid_char(d, x, 170, s, ch); x += s + gap
    y = 170 + s + 70
    ctext(d, y, c["py"], font(PY, 64), PYC); y += 100
    if c.get("simp") and c["simp"] != "".join(c["chars"]):
        ctext(d, y - 10, "simplified  " + c["simp"], ttc(CJK_R, 38), GSOFT); y += 70
    ctext(d, y, c["en"], font(POP_B, 74), GINK); y += 110
    if c.get("aside"):
        for ln in wrap(d, c["aside"], font(POP_SB, 44), W - 200):
            ctext(d, y, ln, font(POP_SB, 44), GSOFT); y += 58
    return img

def g_sum(c, n, t):
    img, d = frame(PAPER, GSOFT, n, t)
    s = 250; y0 = 230
    parts = c["parts"]  # [[char, en], [char, en], [char, en]]
    xs = [70, 415, 760]
    for i, (ch, en) in enumerate(parts):
        grid_char(d, xs[i], y0, s, ch)
        ctext(d, y0 + s + 30, en, font(POP_B, 46), GINK, xs[i], xs[i] + s)
    opf = font(POP_B, 80)
    for i, op in enumerate(["+", "="]):
        cx = xs[i] + s + (xs[i + 1] - xs[i] - s) / 2
        w = d.textlength(op, font=opf); d.text((cx - w / 2, y0 + s / 2 - 50), op, font=opf, fill=GRID)
    y = y0 + s + 150
    ctext(d, y, c["py"], font(PY, 60), PYC); y += 110
    for ln in wrap(d, c["aside"], font(POP_SB, 48), W - 200):
        ctext(d, y, ln, font(POP_SB, 48), GSOFT); y += 62
    return img

def g_end(c, n, t):
    img, d = frame(PAPER, GSOFT, n, t)
    y = lines_center(d, 330, c["q"], font(POP_B, 76), GINK, 92)
    em = emoji_img(c["emoji"], 150); img.paste(em, ((W - em.width) // 2, y + 40), em)
    lines_center(d, y + 260, c["cta"], font(POP_B, 50), GRID, 66)
    return img

# ---------- style 2: dark challenge ----------
NIGHT = (20, 21, 31); NEON = (255, 221, 87); TEAL = (88, 230, 210); DSOFT = (150, 152, 170)

def d_cover(c, n, t):
    img, d = frame(NIGHT, DSOFT, n, t)
    em = emoji_img(c["emoji"], 160); img.paste(em, ((W - em.width) // 2, 170), em)
    y = lines_center(d, 400, c["title"], font(POP_B, 96), NEON, 112)
    lines_center(d, y + 50, c["sub"], font(POP_SB, 46), (235, 235, 245), 60)
    ctext(d, 1110, "swipe if you dare →", font(POP_SB, 40), TEAL)
    return img

def d_level(c, n, t):
    img, d = frame(NIGHT, DSOFT, n, t)
    lab = c["label"]; lf = font(POP_B, 44)
    w = d.textlength(lab, font=lf) + 70
    col = TEAL if c.get("boss") is not True else (255, 107, 107)
    d.rounded_rectangle([(W - w) / 2, 140, (W + w) / 2, 220], 40, fill=col)
    ctext(d, 152, lab, lf, NIGHT)
    zh = c["zh"]; zf = ttc(CJK, 170 if len(zh) <= 3 else (130 if len(zh) <= 5 else 92))
    ctext(d, 330, zh, zf, (250, 250, 255))
    ctext(d, 600, c["py"], font(PY, 64 if len(c["py"]) < 20 else 48), NEON)
    ctext(d, 720, "“" + c["en"] + "”", font(POP_B, 58), (235, 235, 245))
    if c.get("aside"):
        y = 880
        for ln in wrap(d, c["aside"], font(POP_SB, 44), W - 200):
            ctext(d, y, ln, font(POP_SB, 44), DSOFT); y += 58
    return img

def d_final(c, n, t):
    img, d = frame(NIGHT, DSOFT, n, t)
    lab = c["label"]; lf = font(POP_B, 44); w = d.textlength(lab, font=lf) + 70
    d.rounded_rectangle([(W - w) / 2, 120, (W + w) / 2, 200], 40, fill=(255, 107, 107))
    ctext(d, 132, lab, lf, NIGHT)
    y = 270
    for zh, py in c["rows"]:
        ctext(d, y, zh, ttc(CJK, 92), (250, 250, 255)); y += 150
        ctext(d, y, py, font(PY, 44), NEON); y += 95
    ctext(d, y + 10, c["aside"], font(POP_SB, 46), TEAL)
    return img

def d_end(c, n, t):
    img, d = frame(NIGHT, DSOFT, n, t)
    y = lines_center(d, 330, c["q"], font(POP_B, 80), NEON, 96)
    em = emoji_img(c["emoji"], 150); img.paste(em, ((W - em.width) // 2, y + 40), em)
    lines_center(d, y + 260, c["cta"], font(POP_B, 50), (235, 235, 245), 66)
    return img

# ---------- style 3: quiz ----------
MINT = (214, 244, 226); PINK = (255, 214, 226); QINK = (28, 40, 34); GREEN = (34, 160, 90); QSOFT = (90, 105, 98)

OPT_RIGHT_TXT = (255, 255, 255); DIM_FILL = (240, 240, 240); DIM_OUT = (200, 200, 200); DIM_TXT = (170, 170, 170)

def q_cover(c, n, t):
    img, d = frame(MINT, QSOFT, n, t)
    em = emoji_img(c["emoji"], 170); img.paste(em, ((W - em.width) // 2, 180), em)
    y0 = 420
    if c.get("zh"):
        ctext(d, 380, c["zh"], ttc(CJK, 220), QINK); y0 = 660
    y = lines_center(d, y0, c["title"], font(POP_B, 100), TITLE or QINK, 116)
    lines_center(d, y + 50, c["sub"], font(POP_SB, 48), QSOFT, 62)
    ctext(d, 1110, c.get("swipe", "swipe →"), font(POP_SB, 40), GREEN)
    return img

def option(d, y, letter, text, state):
    fill = OPT_FILL; out = QINK; tc = QINK
    if state == "right": fill, out, tc = GREEN, GREEN, OPT_RIGHT_TXT
    if state == "dim": fill, out, tc = DIM_FILL, DIM_OUT, DIM_TXT
    d.rounded_rectangle([110, y, W - 110, y + 120], 30, fill=fill, outline=out, width=5)
    d.text((150, y + 30), letter + ")", font=font(POP_B, 54), fill=tc)
    d.text((250, y + 30), text, font=font(POP_B, 54), fill=tc)
    if state == "right":
        d.text((W - 200, y + 28), "✓", font=font(PY, 60), fill=OPT_RIGHT_TXT)

def q_card(c, n, t, reveal):
    img, d = frame(PINK if reveal else MINT, QSOFT, n, t)
    ctext(d, 110, c["qlabel"] + (" · ANSWER" if reveal else ""), font(POP_B, 40), GREEN if reveal else QSOFT)
    zh = c["zh"]; ctext(d, 190, zh, ttc(CJK, 170 if len(zh) <= 3 else 140), QINK)
    ctext(d, 420, c["py"], font(PY, 58), PYC)
    ctext(d, 520, "literally: “" + c["literal"] + "”", font(POP_SB, 46), QSOFT)
    ctext(d, 610, "So it means…?", font(POP_B, 54), QINK)
    y = 720
    for i, opt in enumerate(c["options"]):
        L = "AB"[i]
        st = "plain" if not reveal else ("right" if L == c["answer"] else "dim")
        option(d, y, L, opt, st); y += 150
    if reveal and c.get("aside"):
        y += 10
        for ln in wrap(d, c["aside"], font(POP_SB, 42), W - 200):
            ctext(d, y, ln, font(POP_SB, 42), QINK); y += 54
    return img

def q_end(c, n, t):
    img, d = frame(MINT, QSOFT, n, t)
    y = lines_center(d, 330, c["q"], font(POP_B, 80), QINK, 96)
    em = emoji_img(c["emoji"], 150); img.paste(em, ((W - em.width) // 2, y + 40), em)
    lines_center(d, y + 260, c["cta"], font(POP_B, 50), GREEN, 66)
    return img


def p_card(c, n, t):
    img, d = frame(MINT, QSOFT, n, t)
    em = emoji_img(c["emoji"], 140); img.paste(em, ((W - em.width) // 2, 110), em)
    zh = c["zh"]; ctext(d, 280, zh, ttc(CJK, 180 if len(zh) <= 2 else (150 if len(zh) <= 3 else 120)), QINK)
    ctext(d, 510, c["py"], font(PY, 58), PYC)
    y = 600
    if c.get("simp") and c["simp"] != zh:
        ctext(d, y, "简 " + c["simp"], ttc(CJK_R, 38), QSOFT); y += 60
    y += 20
    rows = c["rows"]
    h = 50 + sum(46 + 66 * len(wrap(d, v, font(POP_B, 54), W - 280)) + 18 for _, v in rows)
    d.rounded_rectangle([90, y, W - 90, y + h], 36, fill=(255, 255, 255))
    yy = y + 32
    for lab, v in rows:
        d.text((140, yy), lab, font=font(POP_SB, 32), fill=QSOFT); yy += 46
        for ln in wrap(d, v, font(POP_B, 54), W - 280):
            d.text((140, yy), ln, font=font(POP_B, 54), fill=GREEN if lab.startswith(("MEANS", "ALSO", "IT")) else QINK); yy += 66
        yy += 18
    if c.get("aside"):
        ya = y + h + 45
        for ln in wrap(d, c["aside"], font(POP_SB, 44), W - 200):
            ctext(d, ya, ln, font(POP_SB, 44), QINK); ya += 56
    return img

KIND = {"p_card": p_card, "g_cover": g_cover, "g_char": g_char, "g_sum": g_sum, "g_end": g_end,
        "d_cover": d_cover, "d_level": d_level, "d_final": d_final, "d_end": d_end,
        "q_cover": q_cover, "q_ask": lambda c, n, t: q_card(c, n, t, False),
        "q_ans": lambda c, n, t: q_card(c, n, t, True), "q_end": q_end}

def set_dark():
    g = globals()
    g.update(TITLE=NEON, PAPER=NIGHT, GRID=TEAL, GINK=(250, 250, 255), GSOFT=DSOFT, DASH=(40, 90, 95), PYC=NEON,
             MINT=NIGHT, PINK=(30, 33, 52), QINK=(245, 245, 252), QSOFT=DSOFT, GREEN=(90, 220, 140),
             OPT_FILL=(34, 36, 52), OPT_RIGHT_TXT=NIGHT, DIM_FILL=(28, 29, 40), DIM_OUT=(60, 62, 78), DIM_TXT=(95, 97, 115))

def render(spec, outdir):
    if spec.get("theme") == "dark": set_dark()
    os.makedirs(outdir, exist_ok=True)
    sl = spec["slides"]; paths = []
    for i, c in enumerate(sl, 1):
        im = KIND[c["kind"]](c, i, len(sl))
        p = f"{outdir}/{spec['id']}-{i}.jpg"; im.save(p, quality=90); paths.append(p)
    th = [Image.open(p).resize((270, 338)) for p in paths]
    sheet = Image.new("RGB", (270 * len(th) + 10 * (len(th) - 1), 338), (40, 40, 40))
    for i, im in enumerate(th): sheet.paste(im, (i * 280, 0))
    sheet.save(f"{outdir}/{spec['id']}-sheet.jpg", quality=85)
    return paths

if __name__ == "__main__":
    print(render(json.load(open(sys.argv[1])), sys.argv[2]))
