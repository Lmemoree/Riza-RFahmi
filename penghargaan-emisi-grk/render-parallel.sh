#!/usr/bin/env bash
# Renders promo.html in N parallel frame chunks, then concatenates them (stream copy).
set -euo pipefail
cd "$(dirname "$0")"
FPS=${FPS:-30}; N=${N:-4}; END=$(grep -oP "const END = \K[0-9.]+" promo.html); TOTAL=$(python3 -c "print(round($END*$FPS))")
mkdir -p render/chunks; rm -f render/chunks/*
per=$(( (TOTAL + N - 1) / N ))
for i in $(seq 0 $((N-1))); do
  f0=$((i*per)); f1=$(( (i+1)*per < TOTAL ? (i+1)*per : TOTAL ))
  node render.mjs --fps=$FPS --f0=$f0 --f1=$f1 --out=render/chunks/c$i.mp4 > render/chunks/c$i.log 2>&1 &
done
wait
for i in $(seq 0 $((N-1))); do echo "file 'c$i.mp4'"; done > render/chunks/list.txt
ffmpeg -y -v error -f concat -safe 0 -i render/chunks/list.txt -c copy -movflags +faststart render/video-silent.mp4
echo "DONE $(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 render/video-silent.mp4) frames"
