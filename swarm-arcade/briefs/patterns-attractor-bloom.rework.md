# Rework orders: Attractor Bloom

File to edit (edit in place, do not create other files): /home/user/Nassau/swarm-arcade/demos/patterns-attractor-bloom.html
First read /home/user/Nassau/swarm-arcade/HOUSE_RULES.md. Do not run git. Do not edit any other file.

## What is wrong
The smoke test passes, but the art direction fails. The attractor renders as solid, flat violet sheets with a blown-out white core. It must read as delicate glowing filaments on near-black, with a rich ember-to-gold-to-magenta gradient, not as filled blobs. It is also small (it fills only about 45% of the height), and the headless fps is low (20-41), so the work per frame needs to come down.

## Orders (numbered)
1. Stop the saturation. In the `DECAY` constant use 0.93 (currently 0.985, which accumulates about 66 hits per pixel, so everything saturates). Because the density is now much lower, also set the tone map gain `K` in `buildLut()` to 6 (currently 20) and keep the smoothed max logic. Goal: sparse filaments stay visible but dense areas fall in the gold range, not pure white.
2. Remove the white blob. In the colour table build, cap the brightness multiplier `m` at 0.85 and change the ember palette to: [0,'#1a0508'], [0.2,'#b3261e'], [0.4,'#ff7a3d'], [0.6,'#ffe08a'], [0.8,'#ff2f7e'], [1,'#7a4dff']. There must be no pure #ffffff stop anywhere in the ember palette (the other palettes may keep theirs, but replace the ice palette's final '#ffffff' with '#e6f4ff').
3. Make the violet stop non-solid. The hue index is the average step distance. Change `hv` to `Math.sqrt(dx*dx+dy*dy) * 0.7` clamped to [0,1]. The result should spread colour across the whole palette, not collapse onto violet.
4. Fill more of the screen. Change `scale` to `Math.min(W, H) / 5.2` (it is currently /6.8). Since the attractor spans about +-2.6, it should now fill about 85% of the height without clipping badly.
5. Make it more delicate and faster. In full mode use ITERS=40 (about 80k points per frame) and in preview mode ITERS=8 (about 16k). Make the glow cheaper and subtler: draw the half-res glow at 0.25 alpha (currently 0.35).
6. Make morphing more visible in idle: set the preset morph duration to 9 s (currently 12) and increase the slow rotation to `time * 0.08`. Skip any preset that, at the mid-point of a morph, looks like an empty screen: no code needed, just verify with the screenshots.
7. Keep everything else working: pointer move or drag bends the attractor (a, b offsets), click jumps to a random preset and reseeds, Space next preset, R randomises (with the spread test), keys 1-3 palettes, the HUD top-left, the empty top-right 120x40, HUD hidden in preview.

## How to verify
Run from /home/user/Nassau: `node swarm-arcade/tools/check.cjs swarm-arcade/demos/patterns-attractor-bloom.html`.
Require pass:true and fps >= 45 if possible. Then open the three screenshots with the Read tool (in /home/user/Nassau/swarm-arcade/tools/shots/ as patterns-attractor-bloom-a.png, -b.png and -preview.png). Require: visible individual filaments and fine texture, an ember/gold/magenta colour gradient with no large flat violet area and no large solid white area, and a composition that fills most of the frame. The preview shot must look just as nice. If a shot is still blobby, lower DECAY a bit more (0.9) or K, and re-run. Report briefly.
