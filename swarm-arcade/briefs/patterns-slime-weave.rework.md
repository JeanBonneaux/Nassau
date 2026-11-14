# Rework orders: Slime Weave

File to edit (edit in place, do not create other files): /home/user/Nassau/swarm-arcade/demos/patterns-slime-weave.html
First read /home/user/Nassau/swarm-arcade/HOUSE_RULES.md. Do not run git. Do not edit any other file.

## What is wrong
The smoke test passes, but the art direction fails. Idle at 1 s (and in the 420x260 preview) is one giant, bright, perfectly smooth teal ring with a lone glow dot, and a few stubby tendrils. The ring is a self-reinforcing loop of agents that dominates for many seconds. It does not look like a living vein network. It must look like a dense, branching, glowing web from the very first second, everywhere on screen.

## Orders (numbered)
1. In `seedRing()`, delete the ring. Seed agents as about 8 to 12 soft clusters. Pick a random centre per cluster (kept 8% inside the edges). Place each agent within a Gaussian-ish radius of about 0.12 * min(W,H) of its centre, with a fully random heading. About 15% of agents are uniform random across the whole grid. The result must fill the screen with seeds; nothing may be ring-shaped.
2. Make the veins form fast and be bold. Raise DEP from 1 to 1.6, keep DEP_CAP at 6, and set decay to 0.94 (it is currently 0.96, which smears the trails). In `step()`, use sensor distance 11 by default (sensorDist = 11, sensorAngle base 0.55 with the existing +-0.2 slow sine). Keep TURN at 0.3 but lower JITTER to 0.06 so the veins are crisp.
3. Pre-warm: run 120 steps at init in full mode (60 is too few) and 150 in preview mode (keep 150). Do the pre-warm AFTER seeding and before the first render, so the first visible frame already shows a web.
4. Make the idle evolve with visible motion, not just a static net. Every ~8 s call a "pulse": pick a random grid point and scatter about 600 agents (set positions to a small disc around the point and set random headings) so a new branching bloom grows out of it. Also keep the existing food-source wanderer, but make the food boost radius 60 cells and the boost +3 per agent so the agents visibly stream toward it.
5. In preview mode (location.hash contains "preview"): N=4000 (up from 3000), grid still about 160x100 or smaller (use the same gridSize but cap W at 240), and no glow pass. The preview must show a web covering most of the frame, with no empty black areas larger than about a quarter of the screen.
6. Rendering. Add a gentle vignette in full mode only: after the upscaled drawImage and the glow pass, fill a radial gradient (transparent in the centre, rgba(5,6,10,0.55) at the corners) to frame the composition. Keep the preview free of it.
7. Keep everything else working: pointer drag attracts, right-click or a second finger repels, Space scatters, 1/2/3 palettes, Up/Down sensor reach, the HUD top-left, the empty top-right 120x40, hidden HUD in preview.
8. Make sure the Up/Down keys now clamp sensorDist to [5, 22].

## How to verify
Run from /home/user/Nassau: `node swarm-arcade/tools/check.cjs swarm-arcade/demos/patterns-slime-weave.html`.
Require pass:true and fps >= 50. Then open the three screenshots with the Read tool (they are in /home/user/Nassau/swarm-arcade/tools/shots/ as patterns-slime-weave-a.png, -b.png and -preview.png). The idle shot and the preview shot must both show a filled, branching, web-like network across the whole frame, and must not show one dominant ring. The after-interaction shot must show the drawn stroke plus the web. If any shot is still sparse or ring-like, tweak the seeding and deposit values and re-run. Report briefly.
