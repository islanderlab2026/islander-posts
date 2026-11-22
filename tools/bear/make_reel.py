"""把一篇輪播字卡做成 Reels 影片（2026-11-15 每組另外出一支 Reels，接觸陌生人）。
用法：python tools/bear/make_reel.py queue/bear/<代號>  → 產生 <代號>/reel.mp4
- 1080x1920（9:16），字卡置中，上下補字卡邊緣的底色
- 封面 1.6 秒，其他每張 2.4 秒，0.3 秒淡入淡出
- 配樂：程式自己合成的簡單五聲音階撥弦（原創，無版權問題）；IG 內建音樂 API 無法加
"""
import sys, subprocess, pathlib, tempfile, wave
import numpy as np
from PIL import Image

folder = pathlib.Path(sys.argv[1])
imgs = sorted(folder.glob("[0-9]*.jpg"), key=lambda p: int(p.stem))
if len(imgs) < 2:
    sys.exit("至少要 2 張字卡")
W, H, FADE = 1080, 1920, 0.3
durs = [1.6] + [2.4] * (len(imgs) - 1)
total = sum(durs) - FADE * (len(imgs) - 1)
tmp = pathlib.Path(tempfile.mkdtemp())

frames = []
for i, p in enumerate(imgs):
    im = Image.open(p).convert("RGB")
    im = im.resize((W, round(im.height * W / im.width)))
    bg = im.getpixel((4, 4))
    can = Image.new("RGB", (W, H), bg)
    can.paste(im, (0, (H - im.height) // 2))
    f = tmp / f"{i}.png"; can.save(f); frames.append(f)

# 原創配樂：C 大調五聲音階撥弦，每拍 0.4 秒
sr, beat = 44100, 0.4
notes = [523.25, 587.33, 659.25, 783.99, 880.0]
pattern = [0, 2, 4, 2, 3, 1, 4, 2]
n = int(sr * (total + 0.5))
audio = np.zeros(n)
t_note = np.arange(int(sr * beat * 2)) / sr
for k in range(int(total / beat) + 1):
    f0 = notes[pattern[k % len(pattern)]] / (2 if k % 4 == 3 else 1)
    tone = (np.sin(2 * np.pi * f0 * t_note) + 0.3 * np.sin(4 * np.pi * f0 * t_note)) * np.exp(-t_note * 6)
    s = int(k * beat * sr)
    seg = tone[: max(0, n - s)]
    audio[s:s + len(seg)] += seg
audio = audio / max(1e-9, np.abs(audio).max()) * 0.35
fade = int(sr * 0.6)
audio[-fade:] *= np.linspace(1, 0, fade)
wav = tmp / "m.wav"
with wave.open(str(wav), "w") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((audio * 32767).astype(np.int16).tobytes())

cmd = ["ffmpeg", "-y", "-loglevel", "error"]
for f, d in zip(frames, durs):
    cmd += ["-loop", "1", "-t", f"{d}", "-i", str(f)]
cmd += ["-i", str(wav)]
fl, prev, off = [], "[0:v]", 0.0
for i in range(1, len(frames)):
    off += durs[i - 1] - FADE
    out = f"[v{i}]"
    fl.append(f"{prev}[{i}:v]xfade=transition=fade:duration={FADE}:offset={off:.2f}{out}")
    prev = out
fl.append(f"{prev}format=yuv420p,fps=30[vout]")
cmd += ["-filter_complex", ";".join(fl), "-map", "[vout]", "-map", f"{len(frames)}:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "128k",
        "-t", f"{total:.2f}", "-movflags", "+faststart", str(folder / "reel.mp4")]
subprocess.run(cmd, check=True)
print("完成", folder / "reel.mp4", f"{total:.1f} 秒")
