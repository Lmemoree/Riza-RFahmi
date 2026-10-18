# Penghargaan Pemenuhan Inventarisasi Data Emisi GRK · Promo

1920×1080, 30 fps, 46.9 s. Look A (V-spread cards) on dark navy with teal accents. The cuts are locked to `assets/audio/music-nomination.mp3` (see `director-notes.md`, v3).

| File | What it is |
|---|---|
| `promo.html` | The whole animation. A pure `renderFrame(t)`. Open it in a browser to preview (click once to start audio), or use `promo.html#t=12.3` to freeze a frame |
| `render.mjs`, `render-parallel.sh` | Deterministic frame-by-frame capture (Playwright → ffmpeg), run in 4 parallel chunks |
| `mix-audio.sh` | Music plus whoosh/sparkle SFX at the cut times → `assets/audio/promo-mix.m4a` |
| `director-notes.md` | Beat map, shot list, timings |
| `direction-approved.md` | Which direction was chosen and how it was interpreted |
| `design-demos/`, `shots/` | The three direction boards shown before production |

## Rebuild
```bash
ln -sfn "$(npm root -g)" node_modules      # uses globally installed playwright
./render-parallel.sh                         # 4 parallel chunks → render/video-silent.mp4
./mix-audio.sh
ffmpeg -i render/video-silent.mp4 -i assets/audio/promo-mix.m4a -af apad -t 46.9 \
  -c:v copy -c:a aac -b:a 256k -movflags +faststart penghargaan-emisi-grk.mp4
```

## Editing text or timing
- Nominee data: the `NOMS` array in `promo.html`. Long names auto-fit to an 800 px column; split lines however you want.
- Cut times: the `CUTS` array. If you change the music, re-measure the onsets and update both `CUTS` and `mix-audio.sh`.
