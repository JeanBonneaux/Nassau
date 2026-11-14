# Swarm Arcade — house rules for every demo

Each demo is ONE self-contained file: `swarm-arcade/demos/<slug>.html`.

1. Starts with `<!doctype html>`, has charset + viewport meta and a `<title>`. All CSS and JS inline.
   ZERO external requests (no CDN, web fonts, images, fetch). Vanilla JS only.
2. Full-viewport canvas (2D or WebGL). `body{margin:0;overflow:hidden;background:#05060a}`.
   Handles window resize. devicePixelRatio capped at 2.
3. ATTRACT MODE: it must look alive and impressive within 1 second of loading with zero interaction
   (the gallery shows it in a small iframe). Pointer input (pointer events: mouse + touch) and
   optionally keys make it better. Idle = self-driving, never a blank or static screen.
4. PREVIEW MODE: when `location.hash` contains `preview`, hide every HUD/text/control overlay,
   never start audio, and lighten the workload if heavy (it is shown at about 420x260).
5. HUD: one small unobtrusive overlay top-left with the title and a one-line controls hint.
   Font stack `ui-monospace, Menlo, Consolas, monospace`, 12px, `rgba(255,255,255,.7)`.
   Leave the top-right 120x40px corner empty (the gallery puts a back button there).
   A few small buttons/sliders are fine if the demo needs them.
6. Audio demos: create/resume AudioContext only after a user gesture, show a "click to start sound"
   hint, keep master gain modest (<= 0.3) with a limiter/compressor, and keep visuals running without audio.
7. Performance: smooth 60fps at 1280x720 on an average laptop. requestAnimationFrame, clamp dt
   (<= 1/30 s), cap every array/particle count, no unbounded memory growth.
8. No alert/confirm/prompt, no required localStorage, no console errors.
9. Original work only: do not recreate a specific existing game, artwork, character or brand.
10. Touch only the file you were assigned. Do not run git.

Smoke test (run from the repo root, prints JSON, saves screenshots you can open with the Read tool):

    node swarm-arcade/tools/check.cjs swarm-arcade/demos/<slug>.html

`pass: true` is the minimum bar, not the goal. The goal is "whoa".
