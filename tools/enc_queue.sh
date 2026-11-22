#!/bin/sh
# 用公開鑰匙把待發片加密：tools/enc_queue.sh queue/2026-11-22.mp4（同名 .txt 一起加密）
# 產生 .mp4.enc、.txt.enc、.key.enc，並刪掉明文。解開要 GitHub 密鑰 QUEUE_PRIVKEY。
set -e
v="$1"; b="${v%.mp4}"; pub="$(dirname "$0")/queue_pub.pem"
pass="$(openssl rand -hex 32)"
QK="$pass" openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -in "$v" -out "$v.enc" -pass env:QK
[ -f "$b.txt" ] && QK="$pass" openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -in "$b.txt" -out "$b.txt.enc" -pass env:QK
printf %s "$pass" | openssl pkeyutl -encrypt -pubin -inkey "$pub" -pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 -out "$b.key.enc"
rm -f "$v" "$b.txt"
echo "加密完成：$b"
