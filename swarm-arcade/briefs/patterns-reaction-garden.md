# Builder brief: Reaction Garden

Output file (write exactly this one file): /home/user/Nassau/swarm-arcade/demos/patterns-reaction-garden.html

## Common rules
- Read /home/user/Nassau/swarm-arcade/HOUSE_RULES.md first. It is binding.
- Write exactly one file, the path above. Do not run git. Do not touch any other file.
- One self-contained HTML file with inline CSS and JS, vanilla JS only, zero external requests.
- Layout: `<!doctype html>`, charset and viewport meta, `<title>`, `body{margin:0;overflow:hidden;background:#05060a}`, full-viewport canvas, resize handling, DPR capped at 2.
- HUD: top-left, title plus a one-line controls hint, `ui-monospace, Menlo, Consolas, monospace`, 12px, `rgba(255,255,255,.7)`. Keep the top-right 120x40px empty.
- Preview mode: when `location.hash` contains "preview", hide all HUD and text, and lighten the workload (shown at about 420x260).
- Attract mode: must look impressive within 1 second with no input. An idle screen is never static or blank.
- Use pointer events (mouse and touch). Clamp dt to <= 1/30 s. Cap all arrays. No console errors, no alert/confirm/prompt, no required localStorage.
- Smoke test (run from /home/user/Nassau): `node swarm-arcade/tools/check.cjs swarm-arcade/demos/patterns-reaction-garden.html`. Run it until it passes. Open the screenshots with the Read tool and fix anything blank, dull, or ugly. Check idle, after interaction, and preview. Then report briefly.

## Demo: Reaction Garden (Gray-Scott reaction-diffusion)
Tagline: Chemistry that sprouts coral, spots and labyrinths wherever you touch.

- **Grid.** Use two Float32Array pairs, U and V, each (W*H), with double buffering. W=256, H=160 (scale to the aspect ratio with a max of 320x200; in preview mode use 160x100). Wrap-around (toroidal) boundaries.
- **Rule.** Per step, with the 9-point Laplacian (centre -1, orthogonal 0.2, diagonal 0.05), Du=1.0, Dv=0.5, dt=1:
  - uvv = U*V*V
  - U += Du*lapU - uvv + F*(1-U)
  - V += Dv*lapV + uvv - (F+k)*V
  - Run 8 steps per frame (4 in preview).
  - Use an inner loop with precomputed row offsets, not a modulo per cell. Handle the borders in a separate pass or with index tables.
- **Presets.** Switch by key or button, and cycle automatically in attract mode every ~20 s.
  - coral (F=0.0545, k=0.062)
  - spots (F=0.035, k=0.065)
  - mitosis (F=0.0367, k=0.0649)
  - labyrinth (F=0.029, k=0.057)
  - waves (F=0.014, k=0.045)
  - Pre-warm by running 200 steps at init with several seeded blobs so the first frame already has pattern.
- **Seeding.** Initialise U=1 and V=0. Place 12 random circular blobs (radius 4-8) where U=0.5 and V=0.25 plus small noise. Attract mode: every ~2.5 s drop a new random blob, and gently shift F and k slightly with a slow sine (+-0.002) so the patterns keep shifting. To keep it alive, if mean V < 0.02, reseed 6 blobs.
- **Rendering.**
  - Write one ImageData at grid resolution and drawImage it scaled up with smoothing.
  - Shade using a pseudo-relief: colour LUT indexed by V (0 to ~0.4), plus a lighting term from the V gradient (dx and dy against a fixed light direction) so patterns look like embossed, glossy coral.
  - Palette: deep indigo (#0b0620), then violet (#7a2dd6), then orchid (#c46bff), then pale pink (#ffd6f5), with the highlight as a specular add.
  - After the upscale, add a soft vignette via a radial-gradient fillRect (plain dark alpha is fine).
- **Pointer.** Hold and drag to paint V=0.5 and U=0.25 in a radius-5 cell disc, which sprouts new growth along the path. Right-click, or a second finger: erase (U=1, V=0). Prevent the context menu on the canvas. The wheel adjusts F by +-0.001 steps. Show F and k in the HUD (hide in preview).
- **Keys.** 1-5: presets. Space: clear and reseed. C: cycle the palette (violet, then lava red-orange-yellow #ff3d2e, then sea green-cyan #12d6a0).
- **Pitfalls.**
  - Clamp U and V to [0,1] to avoid NaN blow-up.
  - Map the pointer to grid coordinates with the canvas rect and the grid scale.
  - Smoothing on for the upscale, with pixelated CSS off.
  - Keep per-frame cost under about 8 ms: 256x160x8 steps is about 330k cell updates, fine.
  - Make sure the first frame is not empty.
- **Visual check.** Glossy, embossed, evolving organic patterns filling the screen within 1 s, with a visible change in the pattern type between presets.
