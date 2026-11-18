# 熊貓中文（bearcat.chinese）產片工具
- render.py：第 1 組黃色字卡版型（cover / pair / phrase / end）
- render2.py：暗色闖關、測驗、米字格版型（spec 加 "theme": "dark" 統一暗色）
- check.py：發文前自動檢查（缺字、MEANS 吐槽、同組風格不一致），沒過不准上傳
- moe_lookup.js：教育部辭典批次查詢（在 dict.revised.moe.edu.tw 頁面執行）
- spec*.json：已發貼文的設定檔，可當範本
發文：圖放 queue/bear/<代號>/1.jpg… ＋ caption.txt，時間寫 queue/bear/times.json，post-bear workflow 每 30 分鐘自動整組發。
