# Builder brief: shaders-ocean-world ("Tidal Dusk")

Output file (write exactly this one file): /home/user/Nassau/swarm-arcade/demos/shaders-ocean-world.html
Do not touch any other file. Do not run git.

## Common rules
You build ONE self-contained file in raw WebGL (no libraries, no external requests). Read /home/user/Nassau/swarm-arcade/HOUSE_RULES.md first; it is binding (HUD top-left 12px ui-monospace rgba(255,255,255,.7), top-right 120x40 corner empty, `preview` in location.hash hides HUD and lowers workload, DPR cap 2, dt clamp 1/30, no console errors, attract mode alive within 1s, resize handling).

Smoke test: from /home/user/Nassau run
`node swarm-arcade/tools/check.cjs swarm-arcade/demos/shaders-ocean-world.html`
Repeat until pass:true, then open the screenshots it saves with the Read tool and fix anything blank, ugly or static. Report back briefly (3-5 lines): pass result and what you saw in the screenshots.

Shader rules: declare `precision highp float;`; after gl.compileShader / gl.linkProgram check status and console.error the info log; uniforms uRes, uTime, uMouse (0..1, smoothed in JS), plus demo-specific ones; one fullscreen triangle/quad; GLSL ES 1.00 (WebGL1): constant loop bounds only, no bitwise ops. Use `for(int i=0;i<64;i++){ if(i>=uSteps) break; ... }` style for variable step counts. The smoke test runs on a software renderer so its fps is pessimistic; below ~20 fps it flags the demo as too heavy. Therefore render at an internal scale (default 0.6 of CSS px*DPR, adaptive: if rolling average frame time > 30 ms lower scale by 0.1 down to 0.3; if < 12 ms raise up to 0.9); preview mode scale 0.35 and fewer steps. Canvas CSS-stretched to 100vw/100vh. Pointer events (mouse + touch): pointer position steers; idle for 3 s => autopilot eases back in (blend factor).

## Demo: Tidal Dusk
Look: a procedural ocean at golden hour/dusk, raymarched heightfield, sun low on the horizon, large rolling swells with sparkle, procedural sky gradient (deep teal zenith #0b2a44 to peach #ff9a62 horizon), glowing sun disc with bloom, layered fbm clouds tinted by the sun, a few distant island/rock silhouettes near the horizon (optional, only if cheap), subtle haze.

Maths:
- Hash: `float hash(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}` Value noise with smooth interpolation; fbm of 5 octaves with rotation mat2(0.8,0.6,-0.6,0.8).
- Ocean height h(x,z) = sum of sine octaves: for i in 0..4: dir_i=normalize(vec2(cos(float(i)*1.7),sin(float(i)*1.7))); h += amp*sin(dot(dir_i,p)*freq + t*speed); amp*=0.55; freq*=1.8; use the 1.0-abs(sin()) sharp-crest trick on 2 octaves. Use 3 octaves in the march and all 5 for the normal (finite differences, eps scaling with distance). Fade detail with distance: amp *= exp(-t*0.02).
- Ray march heightfield: only if rd.y<0; t from 0; step = (p.y-h)*0.5 clamped [0.05,4.0]; 48 iterations; then 4 binary-search refinements. A ray that never hits returns sky.
- Camera: height 2.5+0.6*sin(time*0.2), moves forward over the ocean (z=time*1.5, wrap with mod to preserve precision), yaw drifts by sin(time*0.1)*0.4; pointer x = yaw +-0.9, pointer y = pitch (+-0.35, up to the sky / down to the waves); mouse down = raise camera to ~9 and speed up (ease it).
- Shading: fresnel = pow(1.0-max(dot(n,-rd),0.0),5.0)*0.9+0.04; reflection = sky(reflect(rd,n)); refraction colour = deep teal #06303d mixed with lighter green #1d7a7a by wave height (fake subsurface); water = mix(refr,refl,fresnel) + pow(max(dot(reflect(rd,n),sunDir),0.0),200.0)*4.0 sparkle.
- sky(rd): gradient by rd.y; sun = pow(max(dot(rd,sunDir),0.0),600.0)*8.0 + pow(..,8.0)*0.4 glow; clouds from fbm on a plane intersection (rd.xz/rd.y*0.5 + time*0.02) masked by rd.y>0.02, brightened near the sun. Distant fog: mix(col, horizonColour, 1.0-exp(-t*0.012)).
- Tone-map col=1.0-exp(-col*1.3), gamma 0.4545, vignette. Slow sun elevation cycle via uTime kept in dusk range (about 0.08..0.22).

Interaction: pointer look; hold = ascend and speed up; key T cycles time-of-day presets (dusk, noon, night with moon + stars via hash threshold). Attract: auto yaw/pitch sweep + gentle bob from the first frame.
HUD: "TIDAL DUSK" + "move: look · hold: ascend · T: time of day".
Preview mode: no HUD, scale 0.35, 2 fbm cloud octaves, 28 march steps.

Pitfalls: horizon aliasing (fade wave detail with distance); NaN from normalize of zero; precision of large time*speed values (wrap with mod); do not let the camera look so far down/up that the image becomes empty; constant loop limits in GLSL ES 1.00.
