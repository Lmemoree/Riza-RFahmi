#!/usr/bin/env bash
# Builds assets/audio/promo-mix.m4a (46.9 s) from music-nomination.mp3 + SFX cues.
# Cut times mirror CUTS in promo.html (percussive hits measured in the track; see director-notes.md).
set -euo pipefail
cd "$(dirname "$0")/assets/audio"
END=46.9
# whoosh peaks 0.21 s into the file → start 0.21 s before each cut
W=( 6770 12960 19390 25310 31680 38660 )
ffmpeg -y -v error \
  -i music-nomination.mp3 -i whoosh.mp3 -i sparkle.mp3 \
  -filter_complex "
  [0:a]atrim=0:${END},asetpts=PTS-STARTPTS[music];
  [1:a]asplit=6[w0][w1][w2][w3][w4][w5];
  [w0]adelay=$((W[0]-210))|$((W[0]-210)),volume=0.5[s0];
  [w1]adelay=$((W[1]-210))|$((W[1]-210)),volume=0.5[s1];
  [w2]adelay=$((W[2]-210))|$((W[2]-210)),volume=0.5[s2];
  [w3]adelay=$((W[3]-210))|$((W[3]-210)),volume=0.5[s3];
  [w4]adelay=$((W[4]-210))|$((W[4]-210)),volume=0.5[s4];
  [w5]adelay=$((W[5]-210))|$((W[5]-210)),volume=0.55[s5];
  [2:a]asplit=2[k0][k1];
  [k0]adelay=4350|4350,volume=0.4[sp0];
  [k1]adelay=42400|42400,volume=0.4[sp1];
  [music][s0][s1][s2][s3][s4][s5][sp0][sp1]amix=inputs=9:normalize=0:duration=first,
  alimiter=limit=0.89:level=false,afade=t=out:st=$(python3 -c "print($END-0.8)"):d=0.8[out]" \
  -map "[out]" -c:a aac -b:a 256k -ar 48000 promo-mix.m4a
ffprobe -v error -show_entries format=duration -of csv=p=0 promo-mix.m4a
