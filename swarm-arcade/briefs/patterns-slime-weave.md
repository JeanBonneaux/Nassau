# Builder brief: Slime Weave

Output file (write exactly this one file): /home/user/Nassau/swarm-arcade/demos/patterns-slime-weave.html

## Common rules
- Read /home/user/Nassau/swarm-arcade/HOUSE_RULES.md first. It is binding.
- Write exactly one file, the path above. Do not run git. Do not touch any other file.
- One self-contained HTML file with inline CSS and JS, vanilla JS only, zero external requests.
- Layout: `<!doctype html>`, charset and viewport meta, `<title>`, `body{margin:0;overflow:hidden;background:#05060a}`, full-viewport canvas, resize handling, DPR capped at 2.
- HUD: top-left, title plus a one-line controls hint, `ui-monospace, Menlo, Consolas, monospace`, 12px, `rgba(255,255,255,.7)`. Keep the top-right 120x40px empty.
- Preview mode: when `location.hash` contains "preview", hide all HUD and text, and lighten the workload (shown at about 420x260).
- Attract mode: must look impressive within 1 second with no input. An idle screen is never static or blank.
- Use pointer events (mouse and touch). Clamp dt to <= 1/30 s. Cap all arrays. No console errors, no alert/confirm/prompt, no required localStorage.
- Smoke test (run from /home/user/Nassau): `node swarm-arcade/tools/check.cjs swarm-arcade/demos/patterns-slime-weave.html`. Run it until it passes. Open the screenshots with the Read tool and fix anything blank, dull, or ugly. Check idle, after interaction, and preview. Then report briefly.

## Demo: Slime Weave (physarum / slime-mould agent simulation)
Tagline: Ten thousand tiny agents spin glowing veins of living light.

- **Grid.** Simulate on a low-res grid, roughly canvas/2 (W=floor(innerWidth/2), H=floor(innerHeight/2), capped at 640x400). Use two Float32Array trail maps, trail and scratch, of size W*H.
- **Agents.** About 12000 agents (about 3000 in preview mode), stored in Float32Arrays x, y, angle.
- **Per-frame step.** For each agent:
  - Sample the trail map at 3 sensors: ahead, ahead-left, ahead-right. Sensor angle is about 0.5 rad and sensor distance is about 9 cells.
  - Turn toward the strongest reading (turn rate about 0.3 rad, plus a tiny random jitter).
  - Move 1.1 cells per step, wrapping at the edges.
  - Deposit +1 at its cell. Do this in a second pass so each agent reads the trail before anyone deposits.
- **Trail update.** Blur with a 3x3 box (or cross) kernel. Mix 0.9 blurred with 0.1 original, then multiply by decay 0.96. Clamp deposits so values stay under about 6.
- **Rendering.**
  - Write one ImageData at grid resolution, put it on an offscreen canvas, and drawImage it scaled up to the main canvas with smoothing on.
  - Map trail value v through a precomputed 256-entry palette LUT (Uint32Array). The palette runs from black through deep teal (#04323a), then cyan-green (#38f2c0), then warm white-gold (#fff2c0) at the peak. Use v^0.6 normalisation.
  - For glow, draw a second smaller blurred copy with `globalCompositeOperation='lighter'` at 0.25 alpha. If that is expensive, skip the glow.
- **Attract mode.**
  - Spawn agents on a big ring.
  - Every ~6 s, an invisible "wanderer" point (Lissajous path) drops a food source. Agents within 60 cells get a brief +deposit boost, which draws veins toward it.
  - Every ~25 s, slowly change sensor angle between 0.35 and 0.8 so the network morphs between tight webs and loose lace.
- **Pointer.**
  - Pointer held and dragged: deposit a strong attractant trail along the path (radius about 6 cells, +4 per frame).
  - Right-click, or a second finger: repel (write negative trail, clamped at 0). Prevent the context menu on the canvas.
- **Keys.**
  - Space: scatter all agents randomly.
  - 1/2/3: switch the palette between teal-gold, magenta-violet (#ff3ea5 to #ffd0f0), and ice-blue (#3aa0ff to #e8f6ff).
  - Up/Down: sensor distance.
- **Performance and pitfalls.**
  - Use typed arrays only. No per-agent objects.
  - Use Math.cos/sin directly per agent per step; this is fine at 12k.
  - Keep a fixed step per frame, not dt-scaled, but skip the frame if dt is huge.
  - Make sure the trail array indices are clamped and wrapped as integers.
  - The preview must still show visible veins quickly. Pre-warm by running 60 steps at init, without rendering.
- **Visual check.** Glowing branching networks must be visible within 1 s and keep evolving.
