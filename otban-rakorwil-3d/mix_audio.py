#!/usr/bin/env python3
"""Mux rendered frames + BGM + SFX cues into the final MP4.
usage: python3 mix_audio.py <frames_dir> <A|B> <out.mp4>
BGM is low-passed (<4 kHz) and SFX high-passed (>800 Hz) so the cues stay audible over music; loudness → -14 LUFS."""
import subprocess, sys, os
SFX = os.path.expanduser('/root/.claude/skills/synced/88bb6336-7ac9-4db0-945c-aff2da53116d_802bffcb-6d39-4df3-8d10-1b2ef087a4ec/huashu-design/assets')
frames, which, out = sys.argv[1:4]; T = 45
FLIPS = [4.0, 9.6, 12.0, 14.6, 17.6, 20.6, 32.2]           # every copy beat flips in like paper
cues = [(t, 'container/card-flip', .8) for t in FLIPS] + [
    (5.0, 'ui/click-soft', .6), (23.4, 'container/card-snap', .9), (25.0, 'ui/click-soft', .5), (39.2 if which == 'A' else 38.2, 'impact/logo-reveal', 1.0)]
if which == 'A': cues += [(0.5, 'transition/whoosh', .9)]
else: cues += [(0.6, 'magic/sparkle', .5), (15.0, 'transition/whoosh-fast', .9), (17.8, 'magic/sparkle', .7), (20.8, 'ui/toggle-on', .7)]
bgm = f"{SFX}/bgm-{'tech' if which == 'A' else 'ad'}.mp3"
args = ['ffmpeg', '-v', 'error', '-y', '-framerate', '30', '-i', f'{frames}/f%05d.jpg', '-i', bgm]
for _, f, _ in cues: args += ['-i', f'{SFX}/sfx/{f}.mp3']
fc = [f'[1:a]atrim=0:{T},asetpts=PTS-STARTPTS,lowpass=f=4000,volume=0.45,afade=in:st=0:d=0.4,afade=out:st={T-3}:d=3[bgm]']
for i, (t, _, v) in enumerate(cues):
    ms = int(t * 1000); fc.append(f'[{i+2}:a]highpass=f=800,volume={v},adelay={ms}|{ms}[s{i}]')
fc.append(''.join(f'[s{i}]' for i in range(len(cues))) + f'amix=inputs={len(cues)}:normalize=0:duration=longest[sfx]')
fc.append('[bgm][sfx]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.0:LRA=11,aresample=48000[a]')
args += ['-filter_complex', ';'.join(fc), '-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
         '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-t', str(T), '-movflags', '+faststart', out]
subprocess.run(args, check=True); print('wrote', out)
