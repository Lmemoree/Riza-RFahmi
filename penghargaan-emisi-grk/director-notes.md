# Director notes · Penghargaan Pemenuhan Inventarisasi Data Emisi GRK

1920×1080, 30 fps, about 47.97 s. Look A on a #1F3375 (Biru) background, with B's teal rim light, V-spread cards, and reference-style 3D card swing transitions. Music is the user's track (`assets/audio/music.mp3`, 60.06 s, about 119.2 BPM, beat 0.5035 s).

## Music map (measured with librosa onset strength)
| Video t | Music t | Event |
|---|---|---|
| 0.09 | 0.09 | Opening hit → fade up from black |
| 7.523 | 7.523 | Cut → Nominasi 1 |
| 13.572 | 13.572 | Cut → Nominasi 2 |
| 19.598 | 19.598 | Cut → Nominasi 3 |
| 25.646 | 25.646 | Cut → Nominasi 4 |
| 31.707 | 31.707 | Cut → Nominasi 5 |
| 37.732 | 37.732 → **49.816** | Splice (+24 beats = 12.084 s), 0.25 s crossfade under whoosh + impact → OUTRO |
| 42.30 | 54.38 | Music hit → gold shimmer sweep across EMISI GAS RUMAH KACA |
| 46.33 | 58.41 | Last hit → final beam flash, then fade to black |
| 47.97 | 60.055 | End |

Card cuts are 12 beats (6.04 s) apart, so every transition lands on a beat. Each whip peaks (max blur) exactly on the cut beat: the outgoing card whips out over the last 0.35 s and the incoming card whips in over the first 0.5 s.

## Shared rules (the look, set once)
- Background: near-black (#05050d) with a localized violet glow at 50% 40%, a seeded starfield, drifting dust and bokeh, and 2–3 giant ghost words (PENGHARGAAN / EMISI / NOMINASI, about 5% opacity, blurred) at 0.15× parallax.
- Floor: horizon at 68% (title) or 72% (cards and outro), with a 2 px champagne horizon line. All text and panels are mirrored with `-webkit-box-reflect` (about 26% strength).
- Gold: a vertical brushed gradient from #fff7dc through #d2a955 and #8c6421 back to #fff7dc. Each letter carries the gradient aligned to its line. The shimmer is a 105° white band sweeping across the line.
- Font: Montserrat (local variable woff2) at 800/900, uppercase.
- Camera: one `#cam` rig (perspective 1600). Whips use translateX ±1500 px, rotateY ±28° and a horizontal-only SVG blur (stdDeviation up to 38 px at the cut).

## Shots
1. **Title (0 → 7.523)**. Fade from black on the 0.09 hit. Letters assemble from depth (z −520 → 0, blur 10 → 0) on beats: PENGHARGAAN at 0.56, PEMENUHAN INVENTARISASI DATA at 1.51, EMISI GAS at 2.51, RUMAH KACA at 3.02. Shimmer sweep at 4.02. Push-in 1.00 → 1.06. Two beams at 19.5% and 80% flicker. The ghost word PENGHARGAAN drifts sideways. Frame-check at 5.0 s.
2–6. **Nominee cards (6.04 s each)**. Whip in. Text pops in letter by letter with a scale-up overshoot: t0 at +0.30, NOMINASI at +0.55, LINE 1 at +0.80, LINE 2 at +1.05 (40 ms stagger, auto-fit to the column, up to 3 lines), CITY at +1.75. The panel settles from rotateY 34° to 25°, and the photo has a slow Ken Burns move (1.04 → 1.12). Light sweep at +2.6. Dolly 1.0 → 1.035. Whip out at +5.69. Frame-check at +3.0.
   - N1 LAGALIGO · BUA · panel right
   - N2 SULTAN HASANUDDIN · MAKASSAR · panel left · "BANDAR UDARA INTERNASIONAL"
   - N3 HALUOLEO · KENDARI · panel right
   - N4 MUTIARA SIS AL-JUFRI · PALU · panel left
   - N5 SYUKURAN AMINUDDIN AMIR · LUWUK · panel right
7. **Outro (37.732 → 47.97)**. The last card exits sideways while the camera pulls back from 1.18 to 1.0 and the title re-assembles fast (0.9 s) on the impact. The five nominees fade in as one row (airport name in bold, city small below), divided by thin gold rules (+1.6 to +3.0 s). Slow push-in. Shimmer at 42.30, beam flash at 46.33, fade to black from 46.6 to 47.97. Frame-check at 44.0.

## Sound
- Music track, spliced as above.
- SFX: transition/whoosh-fast about 0.35 s before each card cut (−11 dB), transition/whoosh before the outro (−9 dB), impact/logo-reveal-v2 at 37.732 (−5 dB), magic/sparkle on the shimmers (−16 dB).
- No skill watermark: this is a government ceremony deliverable.

## v2 changes (user request)
- Background: solid #1F3375 with a lighter blue centre glow, a darker navy floor, and a softened vignette.
- Cards: V-spread. Text and photo panel open from a shared corner (text rotateY +40°→28°, panel −40°→−28°), mirrored for left-side panels.
- Transition: the outgoing set spins away up-left (rotateY +58°, rotateZ −13°, it leaves 0.06 s after the beat). The incoming set orbits in from the right (rotateY −62°, rotateZ +10°, z −600) and lands about 0.6 s after the beat with expo-out easing. The whole set, floor included, rolls −4.5° on each cut. A slow ±4° orbit runs while each card holds.
- Teal (from B): a teal rim on the top edge of every gold letter, a teal edge on the panel's corner side, teal floor glow, and teal in the beam halo and flare.

## v3 (current): user request "create A design, remove 3D card entry, intro like the reference, darker navy, more teal, use my music"
- **Music:** `assets/audio/music-nomination.mp3` (51.1 s, about 76 BPM, audible until about 46.8 s). Played straight with no splice; the video ends at 46.9 s.
- **Cuts** (strongest percussive hits near an 8-beat grid): 6.77 · 12.96 · 19.39 · 25.31 · 31.68 · 38.66 (the big hit opens the outro). Cards run 5.9–7.0 s.
- **Intro, like the reference:** at 0.55 s "EMISI GAS" appears alone in dim silver with "RUMAH KACA" tucked behind it. On the 2.22 s hit the stack unfolds vertically (PENGHARGAAN and PEMENUHAN INVENTARISASI DATA slide up from behind, RUMAH KACA slides down) while the light warms from silver to gold and the beams come up. Shimmer on the 4.35 s hit.
- **Outro:** the same unfold. The lockup appears on the 38.66 s hit and unfolds on the 40.00 s hit, the nominee row fades in from 41.0 s, shimmer at 42.4 s, final flash at 45.3 s, fade to black by 46.9 s.
- **Transitions:** the 3D swing and camera roll are removed. Back to the sideways whip pan (translateX ±1600, rotateY ±26°, horizontal motion blur peaking on the beat).
- **Look:** A (V-spread cards). Darker navy background (#0A1736, with #1F3375 as the centre glow). More teal: teal floor haze, teal thin beams, teal ends on the horizon line, a teal halo and top rim on the gold type, a brighter teal edge on the panels, and teal dust particles.

## v4: card text
- Removed the "PENGHARGAAN EMISI GAS RUMAH KACA" line from the nominee cards.
- Enlarged the rest: NOMINASI 38→52 px, line 1 30→38 px, city 44→54 px, airport names auto-fit up to 176 px in an 820 px column (currently 112–151 px). Pop-in starts at +0.32 s.

## v5: uniform names + seamless pan
- All airport names locked to one size (the largest that fits the longest name in the 820 px column; currently 112 px).
- Nominee transition is one continuous 1.0 s camera pan (starts 0.42 s before the beat, ease-in-out sine). Both sets ride the same curve as one strip (translateX 1920 px, yaw 18°). The separate 90 px settle move is removed. Blur peaks at 30 px. Text pop starts at +0.12 s, while the pan is still easing out.
