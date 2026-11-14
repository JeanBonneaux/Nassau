# Builder brief: shaders-fractal-cathedral ("Mandelbox Cathedral")

Output file (write exactly this one file): /home/user/Nassau/swarm-arcade/demos/shaders-fractal-cathedral.html
Do not touch any other file. Do not run git.

## Common rules
You build ONE self-contained file in raw WebGL (no libraries, no external requests). Read /home/user/Nassau/swarm-arcade/HOUSE_RULES.md first; it is binding (HUD top-left 12px ui-monospace rgba(255,255,255,.7), top-right 120x40 corner empty, `preview` in location.hash hides HUD and lowers workload, DPR cap 2, dt clamp 1/30, no console errors, attract mode alive within 1s, resize handling).

Smoke test: from /home/user/Nassau run
`node swarm-arcade/tools/check.cjs swarm-arcade/demos/shaders-fractal-cathedral.html`
Repeat until pass:true, then open the screenshots it saves with the Read tool and fix anything blank, ugly or static. Report back briefly (3-5 lines): pass result and what you saw in the screenshots.

Shader rules: declare `precision highp float;`; after gl.compileShader / gl.linkProgram check status and console.error the info log; uniforms uRes, uTime, uMouse (0..1, smoothed in JS), plus demo-specific ones; one fullscreen triangle/quad; GLSL ES 1.00 (WebGL1): constant loop bounds only, no bitwise ops. Use `for(int i=0;i<72;i++){ if(i>=uSteps) break; ... }` style for variable step counts. The smoke test runs on a software renderer so its fps is pessimistic; below ~20 fps it flags the demo as too heavy. Therefore render at an internal scale (this demo is expensive: default 0.45 of CSS px*DPR, adaptive: if rolling average frame time > 30 ms lower scale by 0.1 down to 0.25; if < 12 ms raise up to 0.8); preview mode scale 0.3 and fewer steps. Canvas CSS-stretched to 100vw/100vh. Pointer events (mouse + touch): pointer position steers; idle for 3 s => autopilot eases back in (blend factor).

## Demo: Mandelbox Cathedral
Look: a raymarched kaleidoscopic fractal interior (box-fold + sphere-fold Mandelbox), lit with warm amber/gold light and cool teal shadow, ambient occlusion from step count, soft glow shimmer, slow cinematic orbit/flythrough while the fractal parameter continuously morphs so the structure keeps changing.

Maths:
- Distance estimator:
```
float DE(vec3 p){
  vec3 z=p; float dr=1.0; float trap=1e5;
  for(int i=0;i<7;i++){
    if(i>=uIters) break;
    z=clamp(z,-1.0,1.0)*2.0-z;              // box fold
    float r2=max(dot(z,z),1e-6);
    if(r2<0.25){ z*=4.0; dr*=4.0; }          // sphere fold
    else if(r2<1.0){ float k=1.0/r2; z*=k; dr*=k; }
    z=z*uScale+p; dr=dr*abs(uScale)+1.0;
    trap=min(trap,length(z));                // orbit trap for colour (store in a global float)
  }
  return length(z)/abs(dr);
}
```
  uScale = -1.8 - 0.5*sin(time*0.07) (keep within [-2.4,-1.6]; negative scale gives the nice interior). Use a global variable `gTrap` to export the orbit trap.
- Camera: ro = r*vec3(cos(a)*cos(b), sin(b)*0.6, sin(a)*cos(b)), a=time*0.05+mouse.x*3.0, b=0.3+mouse.y*0.8-0.4, r oscillating 3.5..6.0 (sin); lookAt target vec3(0)+small drift. Intersect a bounding sphere of radius 6.0 and start the ray there; never start inside geometry (if DE(ro) is tiny push the camera outward).
- March max 72 steps, epsilon = 0.0008*t (distance-scaled), step *= 0.9. AO = 1.0 - steps/maxSteps. Normal via central differences with eps 0.002*t (6 DE calls), computed only on hit, never on a miss.
- Colour: col = 0.5+0.5*cos(6.28*(trap*0.6+vec3(0.0,0.1,0.2)+uTime*0.01)) blended with amber/gold (#e8b04a) and teal. Lighting: warm key from camera-ish direction, cool teal fill from opposite, plus rim. Glow: accumulate 0.02/(1.0+d*d*50.0) per step into the colour for volumetric shimmer (keep subtle). Background: dark gradient #04060d to #0b1330 with a subtle star hash. Gamma + vignette + slight film grain from hash(uv+time).

Interaction: pointer orbits; mouse down zooms the camera in ("dive"); wheel or +/- keys changes the fractal scale manually (clamped to [-2.4,-1.6]); key C cycles 3 palettes; double-click toggles auto-morph. Attract: slow orbit + auto-morph from the first frame.
HUD: "MANDELBOX CATHEDRAL" + "drag: orbit · hold: dive · wheel: morph · C: colour".
Preview mode: no HUD, 36 steps, 4 fold iterations (uIters uniform), scale 0.3.

Pitfalls: DE is expensive (7 iterations x 72 steps) so keep resolution scale low and use the adaptive scaler; guard NaN (r2 min 1e-6); do not recompute normals on misses; image must not be mostly black or mostly blown out in the screenshots, tune light intensity and glow until the structure is clearly visible; constant loop limits in GLSL ES 1.00 (use uniform int compared inside the loop, not as the loop bound).
