"""Render bearcat.chinese carousel cards (1080x1350)."""
import json, sys, os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
CJK_R = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
POP_B = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
POP_SB = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
POP_R = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
PY = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
TC_IDX = 2  # index inside ttc; resolved below

YEL = (255, 214, 102); INK = (31, 30, 28); CREAM = (255, 250, 238); SOFT = (110, 104, 92)
RED = (226, 88, 60); BLUE = (47, 124, 246)

def ttc(path, size):
    # pick the TC face inside the collection
    for i in range(10):
        try:
            f = ImageFont.truetype(path, size, index=i)
        except Exception:
            break
        if "TC" in " ".join(f.getname()):
            return f
    return ImageFont.truetype(path, size)

def font(p, s):
    if not os.path.exists(p):
        p = POP_B
    return ImageFont.truetype(p, s)

def emoji_img(ch, size):
    f = ImageFont.truetype(EMOJI, 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
    bb = im.getbbox() or (0, 0, 160, 160)
    im = im.crop(bb)
    r = size / max(im.size)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)

def ctext(d, y, txt, f, fill, x0=0, x1=W):
    w = d.textlength(txt, font=f)
    d.text(((x0 + x1 - w) / 2, y), txt, font=f, fill=fill)

def wrap(d, txt, f, maxw):
    words, lines, cur = txt.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines

def panda(img, x, y, s):
    d = ImageDraw.Draw(img)
    k = s / 100
    E = lambda a, b, c, e, **kw: d.ellipse([x + a * k, y + b * k, x + c * k, y + e * k], **kw)
    E(0, 0, 100, 100, fill=YEL)
    E(16, 16, 38, 38, fill=INK); E(62, 16, 84, 38, fill=INK)
    E(19, 25, 81, 81, fill=(255, 255, 255), outline=INK, width=max(1, int(1.5 * k)))
    E(29, 37, 47, 61, fill=INK); E(53, 37, 71, 61, fill=INK)
    E(35, 44, 42, 51, fill=(255, 255, 255)); E(58, 44, 65, 51, fill=(255, 255, 255))
    E(45, 58, 55, 64, fill=INK)

def base(bg=CREAM, n=None, total=None):
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    panda(img, 60, H - 120, 64)
    d.text((140, H - 104), "@bearcat.chinese", font=font(POP_SB, 30), fill=SOFT)
    if n and total:
        t = f"{n}/{total}"
        d.text((W - 60 - d.textlength(t, font=font(POP_SB, 30)), H - 104), t, font=font(POP_SB, 30), fill=SOFT)
    return img, d

def cover(c, n, total):
    img, d = base(YEL, n, total)
    y = 250
    for line in c["title"]:
        ctext(d, y, line, font(POP_B, 92), INK); y += 112
    y += 30
    if c.get("zh"):
        ctext(d, y, c["zh"], ttc(CJK, 150), INK); y += 210
    if c.get("emoji"):
        em = emoji_img(c["emoji"], 170); img.paste(em, ((W - em.width) // 2, y), em); y += 210
    ctext(d, y, c.get("sub", ""), font(POP_SB, 46), INK)
    ctext(d, H - 230, "swipe →", font(POP_SB, 40), INK)
    return img

def pair(c, n, total):
    img, d = base(CREAM, n, total)
    ctext(d, 90, c.get("head", "One tone apart"), font(POP_SB, 40), SOFT)
    cols = [(60, 505), (575, 1020)]
    for (x0, x1), side, col in zip(cols, (c["a"], c["b"]), (BLUE, RED)):
        d.rounded_rectangle([x0, 170, x1, 900], 40, fill=(255, 255, 255), outline=col, width=6)
        em = emoji_img(side["emoji"], 120); img.paste(em, ((x0 + x1 - em.width) // 2, 210), em)
        zf = ttc(CJK, 200 if len(side["zh"]) == 1 else 130)
        ctext(d, 350 if len(side["zh"]) == 1 else 390, side["zh"], zf, INK, x0, x1)
        ctext(d, 610, side["py"], font(PY, 58), col, x0, x1)
        ctext(d, 700, side["en"], font(POP_SB, 50), INK, x0, x1)
        if side.get("simp") and side["simp"] != side["zh"]:
            ctext(d, 790, "简 " + side["simp"], ttc(CJK_R, 40), SOFT, x0, x1)
    ctext(d, 490, "≠", font(POP_B, 56), INK, 505, 575)
    # example sentence
    y = 945
    for who, txt, col in (("You meant", c["meant"], BLUE), ("You said", c["said"], RED)):
        d.text((90, y), who.upper(), font=font(POP_SB, 30), fill=SOFT); y += 42
        for ln in wrap(d, txt, font(POP_B, 50), W - 180):
            d.text((90, y), ln, font=font(POP_B, 50), fill=col); y += 62
        y += 18
    return img

def phrase(c, n, total):
    img, d = base(CREAM, n, total)
    em = emoji_img(c["emoji"], 150); img.paste(em, ((W - em.width) // 2, 120), em)
    zf = ttc(CJK, 190 if len(c["zh"]) <= 3 else 150)
    ctext(d, 300, c["zh"], zf, INK)
    ctext(d, 560, c["py"], font(PY, 60), BLUE)
    if c.get("simp") and c["simp"] != c["zh"]:
        ctext(d, 650, "简 " + c["simp"], ttc(CJK_R, 40), SOFT)
    _lf, _mf = font(POP_B, 54), font(POP_B, 50)
    _h = 820 + 66*len(wrap(d, "“" + c["literal"] + "”", _lf, W - 280)) + 24 + 46 + 62*len(wrap(d, c["means"], _mf, W - 280)) + 40
    _bot = max(_h, 1060) if c.get("aside") else 1150
    d.rounded_rectangle([90, 740, W - 90, _bot], 36, fill=(255, 255, 255))
    d.text((140, 775), "LITERALLY", font=font(POP_SB, 32), fill=SOFT)
    y = 820
    for ln in wrap(d, "“" + c["literal"] + "”", font(POP_B, 54), W - 280):
        d.text((140, y), ln, font=font(POP_B, 54), fill=INK); y += 66
    y += 24
    d.text((140, y), "MEANS", font=font(POP_SB, 32), fill=SOFT); y += 46
    for ln in wrap(d, c["means"], font(POP_B, 50), W - 280):
        d.text((140, y), ln, font=font(POP_B, 50), fill=RED); y += 62
    if c.get("aside"):
        ctext(d, _bot + 50, c["aside"], font(POP_SB, 46), INK)
    return img

def end(c, n, total):
    img, d = base(YEL, n, total)
    y = 330
    for line in c["q"]:
        ctext(d, y, line, font(POP_B, 74), INK); y += 92
    em = emoji_img(c.get("emoji", "👇"), 150); img.paste(em, ((W - em.width) // 2, y + 40), em)
    y += 240
    for line in c["cta"]:
        ctext(d, y, line, font(POP_SB, 50), INK); y += 66
    ctext(d, y + 50, "Follow for more 🐼".replace(" 🐼", ""), font(POP_SB, 42), SOFT)
    return img

KIND = {"cover": cover, "pair": pair, "phrase": phrase, "end": end}

def render(spec, outdir):
    os.makedirs(outdir, exist_ok=True)
    total = len(spec["slides"]); paths = []
    for i, s in enumerate(spec["slides"], 1):
        im = KIND[s["kind"]](s, i, total)
        p = os.path.join(outdir, f"{spec['id']}-{i}.jpg")
        im.save(p, quality=92); paths.append(p)
    # contact sheet
    th = [Image.open(p).resize((270, 338)) for p in paths]
    sheet = Image.new("RGB", (270 * len(th) + 10 * (len(th) - 1), 338), (40, 40, 40))
    for i, t in enumerate(th):
        sheet.paste(t, (i * 280, 0))
    sheet.save(os.path.join(outdir, f"{spec['id']}-sheet.jpg"), quality=85)
    return paths

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    print(render(spec, sys.argv[2]))
