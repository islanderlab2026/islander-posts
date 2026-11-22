#!/bin/sh
# 推送前檢查：待發區不得有明文影片、圖片、文案。用法：sh tools/check_plain.sh（有明文就列出並以錯誤結束）
bad=$(git ls-files queue | grep -E '\.(mp4|jpg|jpeg|png|txt)$')
[ -z "$bad" ] && { echo "OK：待發區只有加密檔"; exit 0; }
echo "有明文檔，禁止推送："; echo "$bad"; exit 1
