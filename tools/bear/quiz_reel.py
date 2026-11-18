"""直式 Reels 原生版：倒數猜答案（2026-11-16 只發 Reels、開發新方式）。
用法：python quiz_reel.py spec.json 輸出資料夾
spec: {"id","label":"GUESS THE ANIMAL","sub":"from its Chinese name","items":[{"zh","py","literal","answer"}],
       "end_q":[..], "end_cta":[..]}
- 1080x1920，重要文字都放在中間 1440 高（個人頁 3:4 格子裁切範圍 y 240–1680）
- 每題：題目＋3、2、1 倒數（每秒滴答）→ 揭曉（叮）
- 配樂：程式合成的原創撥弦＋音效，無版權問題
輸出：<id>/reel.mp4、<id>/1.jpg（封面）…（每題揭曉畫面，給工作台看）"""
import json, sys, os, subprocess, tempfile, wave, pathlib
import numpy as np
from PIL import Image, ImageDraw
from render import POP_B, POP_SB, PY, ttc, font, ctext, wrap, panda

SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
W, H = 1080, 1920
BG = (38, 84, 230); CARD = (255, 255, 255); INK = (24, 26, 40); YEL = (255, 210, 63)
PYC = (38, 84, 230); SOFT = (110, 116, 140); WHITE = (255, 255, 255)
COVER_T, Q_T, A_T, END_T = 1.8, 3.0, 2.0, 2.4

def base(n=None, total=None):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    panda(img, 70, 1560, 70)
    d.text((158, 1578), "@bearcat.chinese", font=font(POP_SB, 34), fill=WHITE)
    if n:
        t = f"{n}/{total}"; f = font(POP_SB, 40)
        d.text((W - 80 - d.textlength(t, font=f), 300), t, font=f, fill=WHITE)
    return img, d

def card(img, d, it, label, reveal=None, count=None, note=None):
    d.text((80, 300), label, font=font(POP_B, 40), fill=YEL)
    if it.get("options"):
        return card_ab(img, d, it, reveal is not None, count)
    x0, y0, x1, y1 = 70, 380, W - 70, 1180
    d.rounded_rectangle([x0, y0, x1, y1], 48, fill=CARD)
    k = len(it["zh"]); fs = 260 if k <= 2 else 210
    fz = ttc(SERIF, fs); bb = d.textbbox((0, 0), it["zh"], font=fz)
    zy = y0 + 90 - bb[1]; d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], zy), it["zh"], font=fz, fill=INK)
    y = y0 + 90 + (bb[3] - bb[1]) + 60
    ctext(d, y, it["py"], font(PY, 66), PYC); y += 130
    ctext(d, y, "literally", font(POP_SB, 40), SOFT); y += 56
    ctext(d, y, it["literal"], font(POP_B, 68), INK)
    if count:
        cx, cy, r = W // 2, 1340, 95
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=YEL)
        f = font(POP_B, 120); t = str(count)
        bb = d.textbbox((0, 0), t, font=f)
        d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]), t, font=f, fill=INK)
        ctext(d, 1460, "guess before it flips", font(POP_SB, 40), WHITE)
    if reveal:
        ctext(d, 1240, "it means", font(POP_SB, 44), WHITE)
        y = 1300
        for ln in wrap(d, reveal.upper(), font(POP_B, 104), W - 140):
            ctext(d, y, ln, font(POP_B, 104), YEL); y += 118
        if note:
            for ln in wrap(d, note, font(POP_SB, 42), W - 160):
                ctext(d, y + 10, ln, font(POP_SB, 42), WHITE); y += 54

def set_theme(t):
    global BG, YEL, PYC
    if t: BG, YEL, PYC = tuple(t["bg"]), tuple(t["accent"]), tuple(t.get("pyc", t["bg"]))

def card_ab(img, d, it, show, count):
    x0, y0, x1, y1 = 70, 380, W - 70, 1100
    d.rounded_rectangle([x0, y0, x1, y1], 48, fill=CARD)
    k = len(it["zh"]); fs = 250 if k <= 2 else 200
    fz = ttc(SERIF, fs); bb = d.textbbox((0, 0), it["zh"], font=fz)
    d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], y0 + 80 - bb[1]), it["zh"], font=fz, fill=INK)
    y = y0 + 80 + (bb[3] - bb[1]) + 60
    ctext(d, y, it["py"], font(PY, 66), PYC); y += 120
    if show:
        ctext(d, y, "literally: " + it["literal"], font(POP_B, 56), INK)
    else:
        ctext(d, y, "what does it mean?", font(POP_SB, 50), SOFT)
    for j, opt in enumerate(it["options"]):
        oy = 1150 + j * 130; good = j == it["correct"]
        fill = YEL if (show and good) else ((255, 255, 255) if not show else (255, 255, 255, 0))
        if show and not good:
            d.rounded_rectangle([110, oy, W - 110, oy + 108], 54, outline=(255, 255, 255), width=4)
            col = (210, 214, 230)
        else:
            d.rounded_rectangle([110, oy, W - 110, oy + 108], 54, fill=fill)
            col = INK
        txt = f"{'AB'[j]}   {opt}" + ("   ✓" if show and good else "")
        f = font(POP_B, 54)
        d.text((150, oy + 22), txt, font=f, fill=col)
    if count:
        cx, cy, r = W // 2, 1470, 62
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=YEL)
        f = font(POP_B, 84); t = str(count); bb = d.textbbox((0, 0), t, font=f)
        d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]), t, font=f, fill=INK)

def make(spec, out):
    set_theme(spec.get("theme"))
    out = pathlib.Path(out) / spec["id"]; out.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.mkdtemp()); seq = []; stills = []
    items = spec["items"]; n = len(items)
    # cover
    img, d = base()
    y = 470
    for ln in spec["cover"]:
        ctext(d, y, ln, font(POP_B, 104), WHITE); y += 122
    ctext(d, y + 40, spec["sub"], font(POP_SB, 48), YEL)
    ctext(d, y + 300, f"{n} rounds  ·  3 seconds each", font(POP_SB, 44), WHITE)
    p = tmp / "c.png"; img.save(p); seq.append((p, COVER_T)); stills.append(img)
    ticks, dings, t = [], [], COVER_T
    for i, it in enumerate(items, 1):
        for c in (3, 2, 1):
            img, d = base(i, n); card(img, d, it, spec["label"], count=c)
            p = tmp / f"q{i}{c}.png"; img.save(p); seq.append((p, 1.0)); ticks.append(t); t += 1.0
        img, d = base(i, n); card(img, d, it, spec["label"], reveal=it.get("answer", True), note=it.get("note"))
        p = tmp / f"a{i}.png"; img.save(p); seq.append((p, A_T)); dings.append(t); t += A_T; stills.append(img)
    img, d = base()
    y = 560
    for ln in spec["end_q"]:
        ctext(d, y, ln, font(POP_B, 96), WHITE); y += 112
    y += 80
    for ln in spec["end_cta"]:
        ctext(d, y, ln, font(POP_B, 64), YEL); y += 80
    p = tmp / "e.png"; img.save(p); seq.append((p, END_T)); stills.append(img); t += END_T
    total = t
    for k, im in enumerate(stills, 1):
        im.convert("RGB").save(out / f"{k}.jpg", quality=88)

    # audio: soft pentatonic loop + tick + ding (all synthesized)
    sr = 44100; N = int(sr * (total + 0.3)); a = np.zeros(N)
    notes = [523.25, 587.33, 659.25, 783.99, 880.0]; pat = [0, 2, 4, 2, 3, 1, 4, 2]; beat = 0.5
    tn = np.arange(int(sr * 0.9)) / sr
    for k in range(int(total / beat) + 1):
        f0 = notes[pat[k % 8]] / 2
        tone = np.sin(2 * np.pi * f0 * tn) * np.exp(-tn * 5) * 0.5
        s = int(k * beat * sr); seg = tone[: max(0, N - s)]; a[s:s + len(seg)] += seg
    tk = np.arange(int(sr * 0.06)) / sr
    for s0 in ticks:
        click = np.sin(2 * np.pi * 1800 * tk) * np.exp(-tk * 80) * 0.9
        s = int(s0 * sr); a[s:s + len(click)] += click[: max(0, N - s)]
    td = np.arange(int(sr * 0.8)) / sr
    for s0 in dings:
        ding = (np.sin(2 * np.pi * 1318.5 * td) + 0.5 * np.sin(2 * np.pi * 1975.5 * td)) * np.exp(-td * 4) * 0.8
        s = int(s0 * sr); seg = ding[: max(0, N - s)]; a[s:s + len(seg)] += seg
    a = a / max(1e-9, np.abs(a).max()) * 0.45
    fd = int(sr * 0.5); a[-fd:] *= np.linspace(1, 0, fd)
    wav = tmp / "a.wav"
    with wave.open(str(wav), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((a * 32767).astype(np.int16).tobytes())
    lst = tmp / "l.txt"
    lst.write_text("".join(f"file '{p}'\nduration {d}\n" for p, d in seq) + f"file '{seq[-1][0]}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(wav),
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-c:a", "aac", "-b:a", "128k", "-t", f"{total:.2f}", "-movflags", "+faststart",
                    str(out / "reel.mp4")], check=True)
    print("完成", out / "reel.mp4", f"{total:.1f} 秒")

if __name__ == "__main__":
    make(json.load(open(sys.argv[1])), sys.argv[2])
