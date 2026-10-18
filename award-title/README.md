# Award title animation

Ten-second 4K title card for *Penghargaan Kepatuhan Inventarisasi Data Emisi Gas Rumah Kaca, Kantor Otoritas Bandar Udara Wilayah V Makassar*.

- `award_title_4k.mp4`: 3840×2160, 30 fps, H.264 High (BT.709), with 48 kHz stereo AAC audio.
- `award_title_1080p_preview.mp4`: a 1080p copy, light enough for phone or chat previews.
- `render.py`: the procedural renderer (numpy + Pillow + ffmpeg). Text is set in real Montserrat, so the spelling is exact.
- `fonts/`: Montserrat from Google Fonts, SIL Open Font License 1.1.

```
python3 render.py                 # full render (about 10 min on 4 cores)
python3 render.py --still 3 7     # PNG stills at t = 3 s and 7 s
```

## Timeline

| Time | Event |
|---|---|
| 0–2 s | Fade up from dark navy. Light beams sweep into place and gold dust appears |
| 2.0 s | "PENGHARGAAN" fades in |
| 2.45 s | Soft orchestral hit. The three title lines rise in one after another, 0.42 s apart, with a depth squash, a defocus-to-sharp and a glow swell |
| 4.0–4.9 s | The gold rule draws outward from the centre, with spark heads. A lens flare sweeps behind the title |
| 4.3–5.3 s | The two bottom lines fade in |
| 5–10 s | Hold. Only a slow 3.5 % camera push-in, drifting dust, bokeh and beams move. The audio pad fades out over the last 0.6 s |

## Spec deviations (deliberate)

- **Title line size.** The brief asks for title lines "about 8 % of frame height" and for all text inside the central 70 % of the width. Both cannot hold at once. At 8 % cap height, "INVENTARISASI DATA EMISI" in Montserrat Bold measures about 93 % of the frame width. The renderer keeps the 70 % safe area: the widest line is 64.9 % (67 % at the end of the push-in), the cap height is 5.5 %, and the line pitch is 8 %.
- **Floor reflection.** The reflection is a stylised placement directly under the horizon, not a physically mirrored position. A true mirror would put it off-frame.
