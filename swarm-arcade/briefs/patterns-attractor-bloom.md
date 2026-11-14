# Builder brief: Attractor Bloom

Output file (write exactly this one file): /home/user/Nassau/swarm-arcade/demos/patterns-attractor-bloom.html

## Common rules
- Read /home/user/Nassau/swarm-arcade/HOUSE_RULES.md first. It is binding.
- Write exactly one file, the path above. Do not run git. Do not touch any other file.
- One self-contained HTML file with inline CSS and JS, vanilla JS only, zero external requests.
- Layout: `<!doctype html>`, charset and viewport meta, `<title>`, `body{margin:0;overflow:hidden;background:#05060a}`, full-viewport canvas, resize handling, DPR capped at 2.
- HUD: top-left, title plus a one-line controls hint, `ui-monospace, Menlo, Consolas, monospace`, 12px, `rgba(255,255,255,.7)`. Keep the top-right 120x40px empty.
- Preview mode: when `location.hash` contains "preview", hide all HUD and text, and lighten the workload (shown at about 420x260).
- Attract mode: must look impressive within 1 second with no input. An idle screen is never static or blank.
- Use pointer events (mouse and touch). Clamp dt to <= 1/30 s. Cap all arrays. No console errors, no alert/confirm/prompt, no required localStorage.
- Smoke test (run from /home/user/Nassau): `node swarm-arcade/tools/check.cjs swarm-arcade/demos/patterns-attractor-bloom.html`. Run it until it passes. Open the screenshots with the Read tool and fix anything blank, dull, or ugly. Check idle, after interaction, and preview. Then report briefly.

## Demo: Attractor Bloom (strange attractor density plot with colour-by-velocity)
Tagline: Chaos, plotted as a million-point firework you can bend by hand.

- **Attractor.** Use the Clifford-style map x' = sin(a*y) + c*cos(a*x), y' = sin(b*x) + d*cos(b*y). Iterate about 120k points per frame (about 25k in preview mode) from a pool of 2048 independent walkers kept in Float32Arrays, each running 60 iterations per frame.
- **Parameters.** Start with a, b, c, d chosen from a list of 6 known pretty presets, e.g. (-1.4, 1.6, 1.0, 0.7), (1.7, 1.7, 0.6, 1.2), (-1.7, 1.3, -0.1, -1.21), (1.5, -1.8, 1.6, 0.9), (-1.8, -2.0, -0.5, -0.9), (1.1, -1.32, 2.4, 0.75). Add a +-0.02 tolerance if a preset looks degenerate.
- **Density accumulation.**
  - Keep a Float32Array hist of size W*H at backing-store resolution (DPR 1 is fine; cap at 1280x800 and let CSS scale).
  - Projection: map x,y in about [-3.2, 3.2] to the canvas, scaled by min(W,H)/6.8, centred.
  - Also keep a Float32Array hue accumulator hue[] that adds a per-point colour value = clamp(step distance).
- **Tone-mapping.** Each frame:
  - Decay hist by 0.985 so it never saturates.
  - Compute the display value d = log(1 + hist*k) / log(1 + max), with max tracked as an exponentially smoothed running maximum.
  - Colour = the LUT palette indexed by (hueAvg = hue/hist), mixed with brightness d.
  - Palette: ember (#1a0508) to orange (#ff7a3d) to gold (#ffe08a) to white, with the hue index shifting to magenta (#ff2f7e) and electric violet (#6a3dff) at high speed.
  - Write an ImageData each frame (typed Uint32Array view) and draw it. A cheap glow comes from drawing the same canvas again, scaled down 0.5 and back up with 'lighter' at 0.35 alpha.
- **Morphing (attract mode).** Slowly interpolate a,b,c,d toward the next preset over about 12 s (smoothstep), then pick another. The shape continuously flows and breathes. Add a slow rotation by rotating the output points by angle t*0.05 before projecting.
- **Pointer.** The pointer position offsets a and b (x maps to a +-0.4, y maps to b +-0.4) relative to the current preset while held or hovered. Dragging reshapes the attractor live. A click jumps to a random preset and reseeds walkers.
- **Keys.** Space: next preset. R: randomise parameters (reject a candidate if the Lyapunov-ish test shows the walkers collapse to a point; after 200 iterations compare the spread, and retry up to 10 times). 1-3: palette variants (ember, aurora green-cyan-violet, monochrome ice).
- **Pitfalls.**
  - Reset walkers that go NaN or leave the +-6 range.
  - Discard the first 20 iterations after a reset.
  - Avoid Math.pow in the inner loop.
  - Use a single typed-array loop with no allocations.
  - Keep the HUD DOM static.
- **Visual check.** A bright, delicate filament structure on near-black, clearly morphing during idle, with no blown-out white blob and no dark empty screen.
