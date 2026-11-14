# Builder brief: shaders-neon-tunnel ("Hyperlane")

Output file (write exactly this one file): /home/user/Nassau/swarm-arcade/demos/shaders-neon-tunnel.html
Do not touch any other file. Do not run git.

## Common rules
You build ONE self-contained file in raw WebGL (no libraries, no external requests). Read /home/user/Nassau/swarm-arcade/HOUSE_RULES.md first; it is binding (HUD top-left 12px ui-monospace rgba(255,255,255,.7), top-right 120x40 corner empty, `preview` in location.hash hides HUD and lowers workload, DPR cap 2, dt clamp 1/30, no console errors, attract mode alive within 1s, resize handling).

Smoke test: from /home/user/Nassau run
`node swarm-arcade/tools/check.cjs swarm-arcade/demos/shaders-neon-tunnel.html`
Repeat until pass:true, then open the screenshots it saves with the Read tool and fix anything blank, ugly or static. Report back briefly (3-5 lines): pass result and what you saw in the screenshots.

Shader rules: declare `precision highp float;`; after gl.compileShader / gl.linkProgram check status and console.error the info log; uniforms uRes, uTime, uMouse (0..1, smoothed in JS), plus demo-specific ones; one fullscreen triangle/quad; GLSL ES 1.00 (WebGL1): constant loop bounds only, no bitwise ops. Use `for(int i=0;i<64;i++){ if(i>=uSteps) break; ... }` style for variable step counts. The smoke test runs on a software renderer so its fps is pessimistic; below ~20 fps it flags the demo as too heavy. Therefore render at an internal scale (default 0.6 of CSS px*DPR, adaptive: if rolling average frame time > 30 ms lower scale by 0.1 down to 0.3; if < 12 ms raise up to 0.9); preview mode scale 0.35 and fewer steps. Canvas CSS-stretched to 100vw/100vh. Pointer events (mouse + touch): pointer position steers; idle for 3 s => autopilot eases back in (blend factor).

## Demo: Hyperlane
Look: an infinite raymarched tunnel flythrough in a synthwave/cyberpunk palette (deep indigo #0a0620, magenta #ff2bd6, cyan #22e6ff, amber accents), glowing ribs, hexagonal-ish lattice walls, volumetric glow, bloom-like look by accumulating glow during the march (no post pass).

Maths:
- Camera moves along +z at speed 3 + boost. Tunnel centreline: path(z)=vec2(sin(z*0.17)*1.6+sin(z*0.31)*0.7, cos(z*0.13)*1.2). Ray origin ro=vec3(path(t),t) with t=uTime*speed (wrap/keep precision sane); lookahead ta=vec3(path(t+2.0),t+2.0). Build camera basis from ro,ta with roll = path curvature*0.4 plus mouse.x*0.5. Pointer offsets view direction (yaw/pitch +-0.5 rad) and moves the ship laterally within the tunnel +-0.6 (clamp so the camera never clips walls).
- Scene SDF in tunnel-local coordinates: p.xy -= path(p.z). d_tube = 2.2 - length(p.xy) (inside a cylinder). Ribs: q=mod(p.z,2.0)-1.0; thin rings = max(abs(q)-0.08, abs(length(p.xy)-2.2)-0.15). Wall lattice: a=atan(p.y,p.x); displacement 0.12*smoothstep pattern of sin(a*6.0)*sin(p.z*1.5) (use only integer multiples of a to avoid the atan seam). Gates every 12 units: max(abs(length(p.xy)-1.4)-0.06, abs(mod(p.z,12.0)-6.0)-0.05). d=min(d_tube-displacement, ribs, gates). Scale steps by 0.8 for Lipschitz safety. Max 64 steps, max dist 40.
- Accumulate glow: glow += 0.012/(0.02+abs(dRibsOrGates)) per step, coloured by mix(cyan,magenta, 0.5+0.5*sin(p.z*0.3+uTime)); keep modest so it does not blow out.
- Shading on hit: normal by 4-tap tetrahedron gradient; colour = mix(magenta,cyan,0.5+0.5*sin(p.z*0.4+a*2.0)) * (0.2+0.8*diffuse from a light at the camera) + rim; fog = exp(-dist*0.07) toward deep indigo, glow added. Subtle scanline/vignette and slight chromatic split of the glow (hue offset).
- Bonus: speed pulse to a beat (sin(uTime*2.0)) that briefly widens FOV.

Interaction: pointer steers; mouse down/touch = boost (speed x2.5, FOV widen, hue shift); Space toggles palette (4 palettes via uniform). Attract: autopilot Lissajous steering when idle 3 s (and from the very first frame).
HUD: "HYPERLANE" + "move: steer · hold: boost · space: palette".
Preview mode: no HUD, scale 0.35, 40 steps.

Pitfalls: atan seam artefacts; non-Lipschitz SDF causing banding/overstepping; camera clipping walls; NaN from normalize(0); GLSL ES 1.00 needs constant loop limits.
