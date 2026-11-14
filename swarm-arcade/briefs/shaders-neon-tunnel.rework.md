# REWORK orders: shaders-neon-tunnel ("Hyperlane")

File to edit (edit in place, do not create other files, no git): /home/user/Nassau/swarm-arcade/demos/shaders-neon-tunnel.html
Read /home/user/Nassau/swarm-arcade/HOUSE_RULES.md first (still binding: no console errors, HUD top-left only, preview hides HUD, etc).

## Verdict
It passes the smoke test but looks like a muddy, washed-out teal/purple fog. Screenshots show flat mid-tone walls, no darkness, no contrast, no neon. A synthwave tunnel must be DARK with razor-bright emissive lines and glow. Right now everything is lit by `diff` and reads as translucent plastic. Fix it as follows (keep the JS loop, input, adaptive scale, palettes and uniforms as they are; the changes are in the fragment shader).

## Orders
1. Walls become near-black. In the hit-shading block replace the lighting line with an emissive model. Use this (adapt variable names):
```
float lat1 = smoothstep(0.90, 0.985, sin(a*6.0));            // 6 longitudinal neon lines (integer multiple => no atan seam)
float lat2 = smoothstep(0.93, 0.995, cos(p.z*3.14159));      // thin rings every 2 units on the wall
float gridE = max(lat1, lat2);
float isRib = step(dRG, 0.02);                               // dRG must be recomputed at the hit point: call scene(p, dRG) once at the hit
vec3 base = mix(A, B, 0.5 + 0.5*sin(p.z*0.4 + a*2.0));
vec3 wall = BG*0.9 + base*0.05*diff;                          // very dark lit wall
vec3 emit = base*gridE*2.2;                                   // glowing lattice lines
vec3 ribC = mix(C, vec3(1.0), 0.5)*3.0;                       // ribs/gates: white-hot
col = mix(wall + emit, ribC, isRib) + C*pow(1.0-diff, 5.0)*0.12;
```
2. Strengthen the volumetric glow: change the per-step accumulation to `gc += (0.02/(0.03 + abs(dRG))) * mix(A, B, s);` and the final add to `col += vec3(gr.r, gc.g, gb.b) * 0.06;` Tune so ribs and gates have a visible halo but the image is not blown out (target: mostly dark frame, bright glowing rings converging to a vanishing point).
3. Fog: keep fog toward BG but make BG very dark (the palette BG values are fine). Fog `exp(-tt*0.09)`. Distant rings should fade into a faint glow, not into grey.
4. Contrast: tone map `col = 1.0 - exp(-max(col,0.0)*1.4);`. Remove the `col = hueRot(col, uBoost*0.5)` hue rotation only if it desaturates; otherwise keep. Vignette stays.
5. Add depth cues: the gates (every 12 units) should be thicker and brighter (`abs(g) - 0.09`). Add a second set of thin ribs period 0.5 with half-intensity so there is a strong sense of speed. Keep SDF Lipschitz safe (the 0.8 factor).
6. Edges in the screenshots are stair-stepped (low internal resolution). Raise default `scale` to 0.7 (adaptive scaler still lowers it if slow) and in preview keep 0.35 but make sure the preview image is dark with bright rings (it should read clearly at 420x260: thick glowing rings converging, not mush).
7. Boost state (screenshot b): must look clearly different and exciting: higher FOV, hue shift, stronger glow (multiply the glow add by `(1.0 + 1.5*uBoost)`).

## Verify
Run from /home/user/Nassau: `node swarm-arcade/tools/check.cjs swarm-arcade/demos/shaders-neon-tunnel.html` (can take minutes as it queues; use a long timeout). Then open the three screenshots with the Read tool: tools/shots/shaders-neon-tunnel-a.png, -b.png, -preview.png. They must show: dark background, glowing magenta/cyan rings and lattice lines, clear perspective to a vanishing point. If it still looks muddy, iterate on the constants (lower wall brightness, raise emission) and re-run. Report in 3-5 lines.
