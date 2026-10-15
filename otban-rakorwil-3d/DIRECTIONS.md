# 3D opening · Rakorwil 2026 — direction boards (real three.js renders)

Status: **WAITING FOR CLIENT CHOICE.** Reference: client's papercraft tunnel opening (Motion_Graphic_Opening.mp4, 15 s).

| | Direction | Frame | Motion plan (<60 s) |
|---|---|---|---|
| A | Paper Tunnel — closest to the reference: cut-paper rings, clouds part, camera dollies through | design-demos/A-paper-tunnel.png | clouds part → dolly through rings (paper planes orbit) → organiser → keywords on passing rings → title plate → date → logos |
| B | Paper Diorama — side-on cut-paper landscape with ship, train, bus, plane (antarmoda) | design-demos/B-paper-diorama.png | camera trucks sideways across layers with parallax; each mode moves in; plane takes off; title rises in the sky |
| C | Type Monument — thick 3D letters standing on a navy apron; plane passes overhead | design-demos/C-type-monument.png | low orbit around the letters as they rise from the ground; plane shadow sweeps across; date sign; logos |

Tech: three.js 0.160 (vendored), local OFL fonts (Archivo, Plus Jakarta Sans) extruded with TextGeometry,
soft shadow maps, paper bump texture. Rendered frame-by-frame (deterministic) via headless Chromium + ffmpeg.
Preview needs a local server: `python3 -m http.server` in this folder, then open design-demos/*.html.
