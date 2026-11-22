#!/bin/sh
# 熊貓一組貼文資料夾加密：tools/enc_bear.sh queue/bear/<代號>
# 把資料夾內容（reel_only 標記除外）打包成 payload.tar.enc＋key.enc，並刪掉明文。
set -e
d="$1"; pub="${PUB:-$(dirname "$0")/queue_pub.pem}"
[ -f "$d/payload.tar.enc" ] && { echo "已加密：$d"; exit 0; }
pass="$(openssl rand -hex 32)"
files=$(cd "$d" && ls | grep -v '^reel_only$')
(cd "$d" && tar -cf /tmp/payload.tar $files)
QK="$pass" openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -in /tmp/payload.tar -out "$d/payload.tar.enc" -pass env:QK
printf %s "$pass" | openssl pkeyutl -encrypt -pubin -inkey "$pub" -pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 -out "$d/key.enc"
(cd "$d" && rm -f $files) ; rm -f /tmp/payload.tar
echo "加密完成：$d"
