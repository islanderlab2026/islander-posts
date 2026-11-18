"""8–10 秒單詞短 Reels（2026-11-17 新版樣本：一支只講一個詞、第 1 秒就是鉤子、每 1–2.5 秒換畫面、結尾點名轉傳對象）。
用法：python short_reel.py spec.json 輸出資料夾
spec: {"id","hook":[..],"zh","py","literal","punch":[..],"cta":[..],"bg":[r,g,b],"accent":[r,g,b]}
文字都在畫面中間（個人頁 3:4 裁切範圍 y 240–1680）。配樂與音效由程式合成（原創）。"""
import json, sys, subprocess, tempfile, wave, pathlib
import numpy as np
from PIL import Image, ImageDraw
from render import POP_B, POP_SB, PY, ttc, font, ctext, wrap, panda

SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
W, H = 1080, 1920
WHITE = (255, 255, 255)

def frame(bg, acc, draw):
    img = Image.new("RGB", (W, H), bg); d = ImageDraw.Draw(img)
    panda(img, 70, 1560, 70)
    d.text((158, 1578), "@bearcat.chinese", font=font(POP_SB, 34), fill=WHITE)
    draw(d, acc); return img

def lines_block(d, lines, size, col, y0=None, gap=1.18):
    f = font(POP_B, size)
    out = []
    for ln in lines:
        out += wrap(d, ln, f, W - 140)
    h = len(out) * size * gap
    y = y0 if y0 is not None else (H - h) / 2 - 60
    for ln in out:
        ctext(d, y, ln, f, col); y += size * gap
    return y

def word(d, s, acc, literal):
    fs = 300 if len(s["zh"]) <= 2 else 240
    fz = ttc(SERIF, fs); bb = d.textbbox((0, 0), s["zh"], font=fz)
    y = 560
    d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], y - bb[1]), s["zh"], font=fz, fill=WHITE)
    y += (bb[3] - bb[1]) + 70
    ctext(d, y, s["py"], font(PY, 76), acc); y += 150
    if literal:
        ctext(d, y, "literally", font(POP_SB, 44), (200, 205, 225)); y += 64
        for ln in wrap(d, s["literal"].upper(), font(POP_B, 96), W - 140):
            ctext(d, y, ln, font(POP_B, 96), acc); y += 112

def make(s, out):
    out = pathlib.Path(out) / s["id"]; out.mkdir(parents=True, exist_ok=True)
    bg, acc = tuple(s["bg"]), tuple(s["accent"])
    seq = [
        (frame(bg, acc, lambda d, a: lines_block(d, s["hook"], 104, WHITE)), 1.6),
        (frame(bg, acc, lambda d, a: word(d, s, a, False)), 1.2),
        (frame(bg, acc, lambda d, a: word(d, s, a, True)), 2.6),
        (frame(bg, acc, lambda d, a: lines_block(d, s["punch"], 84, WHITE)), 2.4),
        (frame(bg, acc, lambda d, a: lines_block(d, s["cta"], 92, a)), 2.2),
    ]
    tmp = pathlib.Path(tempfile.mkdtemp()); total = sum(t for _, t in seq)
    for i, (im, _) in enumerate(seq, 1):
        im.save(out / f"{i}.jpg", quality=88); im.save(tmp / f"{i}.png")
    sr = 44100; N = int(sr * (total + 0.3)); a = np.zeros(N)
    notes = [523.25, 659.25, 783.99, 880.0, 1046.5]; pat = [0, 2, 4, 2, 3, 1, 4, 3]; beat = 0.3
    tn = np.arange(int(sr * 0.5)) / sr
    for k in range(int(total / beat) + 1):
        f0 = notes[pat[k % 8]] / 2
        tone = np.sin(2 * np.pi * f0 * tn) * np.exp(-tn * 9) * 0.45
        st = int(k * beat * sr); seg = tone[: max(0, N - st)]; a[st:st + len(seg)] += seg
    td = np.arange(int(sr * 0.6)) / sr; t = 0.0
    for i, (_, dur) in enumerate(seq):
        if i:
            pop = (np.sin(2 * np.pi * (900 + 500 * (i == 2)) * td) * np.exp(-td * 12)) * 0.9
            st = int(t * sr); seg = pop[: max(0, N - st)]; a[st:st + len(seg)] += seg
        t += dur
    a = a / max(1e-9, np.abs(a).max()) * 0.45
    fd = int(sr * 0.4); a[-fd:] *= np.linspace(1, 0, fd)
    wav = tmp / "a.wav"
    with wave.open(str(wav), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((a * 32767).astype(np.int16).tobytes())
    lst = tmp / "l.txt"
    lst.write_text("".join(f"file '{tmp}/{i}.png'\nduration {d}\n" for i, (_, d) in enumerate(seq, 1)) + f"file '{tmp}/{len(seq)}.png'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(wav),
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-c:a", "aac", "-b:a", "128k", "-t", f"{total:.2f}", "-movflags", "+faststart", str(out / "reel.mp4")], check=True)
    print("完成", out / "reel.mp4", f"{total:.1f} 秒")

if __name__ == "__main__":
    make(json.load(open(sys.argv[1])), sys.argv[2])
