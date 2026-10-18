#!/usr/bin/env bash
# Builds assets/audio/promo-mix.m4a (47.971 s): music spliced +24 beats at 37.732 s, plus SFX cues.
# Timings mirror CUTS in promo.html / director-notes.md.
set -euo pipefail
cd "$(dirname "$0")/assets/audio"
X=0.25                      # crossfade, centred on the splice
A_END=$(python3 -c "print(37.732+$X/2)")
B_START=$(python3 -c "print(49.816-$X/2)")
# delays (ms): whoosh peaks 0.21 s into the file → start 0.21 s before each cut
W=( 7523 13572 19598 25646 31707 )
ffmpeg -y -v error \
  -i music.mp3 -i whoosh.mp3 -i brand-stamp.mp3 -i sparkle.mp3 \
  -filter_complex "
  [0:a]atrim=0:${A_END},asetpts=PTS-STARTPTS[ma];
  [0:a]atrim=start=${B_START},asetpts=PTS-STARTPTS[mb];
  [ma][mb]acrossfade=d=${X}:c1=tri:c2=tri[music];
  [1:a]asplit=6[w0][w1][w2][w3][w4][w5];
  [w0]adelay=$((W[0]-210))|$((W[0]-210)),volume=0.55[s0];
  [w1]adelay=$((W[1]-210))|$((W[1]-210)),volume=0.55[s1];
  [w2]adelay=$((W[2]-210))|$((W[2]-210)),volume=0.55[s2];
  [w3]adelay=$((W[3]-210))|$((W[3]-210)),volume=0.55[s3];
  [w4]adelay=$((W[4]-210))|$((W[4]-210)),volume=0.55[s4];
  [w5]adelay=$((37732-210))|$((37732-210)),volume=0.7[s5];
  [2:a]adelay=37680|37680,volume=0.95[hit];
  [3:a]asplit=2[k0][k1];
  [k0]adelay=4020|4020,volume=0.45[sp0];
  [k1]adelay=42150|42150,volume=0.45[sp1];
  [music][s0][s1][s2][s3][s4][s5][hit][sp0][sp1]amix=inputs=10:normalize=0:duration=first,
  alimiter=limit=0.89:level=false,afade=t=out:st=46.6:d=1.37[out]" \
  -map "[out]" -c:a aac -b:a 256k -ar 48000 promo-mix.m4a
ffprobe -v error -show_entries format=duration -of csv=p=0 promo-mix.m4a
