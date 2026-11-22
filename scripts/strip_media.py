"""發完就刪影片與圖片：posted/ 底下只留紀錄檔（.json）、文案（.txt）與標記檔。
倉庫是公開的，已發的影片 IG 上有、工作台也有備份，不必再放這裡。"""
import pathlib
MEDIA = {".mp4", ".mov", ".jpg", ".jpeg", ".png", ".webp", ".enc"}
n = 0
for f in pathlib.Path("posted").rglob("*"):
    if f.is_file() and (f.suffix.lower() in MEDIA or f.name.endswith(".mp4.enc")):
        f.unlink(); n += 1
print(f"刪除已發媒體檔 {n} 個")
