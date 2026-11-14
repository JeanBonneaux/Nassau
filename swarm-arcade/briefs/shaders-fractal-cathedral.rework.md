# REWORK orders: shaders-fractal-cathedral ("Mandelbox Cathedral")

File to edit (edit in place, do not create other files, no git): /home/user/Nassau/swarm-arcade/demos/shaders-fractal-cathedral.html
Read /home/user/Nassau/swarm-arcade/HOUSE_RULES.md first (still binding).

## Verdict
Rejected on art direction. The screenshots show a brown, speckled, noisy blob seen from outside: a Mandelbox viewed from 4-6 units away at 0.45 render scale turns into high-frequency mush, and the preview is a dotted nothing. The idea is wrong for a low-resolution raymarcher. Replace the fractal and the camera while keeping the file's JS skeleton (render scale / adaptive scaler, pointer smoothing, autopilot blend, dive, palettes, uniforms, HUD, preview handling). Keep the title and HUD text "MANDELBOX CATHEDRAL" -> rename to "FRACTAL CATHEDRAL" (also in <title>) with controls hint "drag: look · hold: speed · wheel: morph · C: colour".

## New design: an infinite Menger-sponge cathedral fly-through
A camera gliding through the huge hollow channels of an infinite Menger sponge, with big smooth planar faces (clean at low resolution), strong light/shadow, warm amber light shafts against cool teal shadows. Large clean shapes, not fine grain.

1. Replace DE with the infinite sponge (iq's construction, starting from "empty space" so it repeats forever):
```
float sdCross(vec3 p){                      // infinite cross of three square beams, half-width 1/3 of cell
  p = abs(p);
  float dxy = max(p.x, p.y), dyz = max(p.y, p.z), dzx = max(p.z, p.x);
  return min(dxy, min(dyz, dzx)) - 1.0;
}
float DE(vec3 p){
  // base: solid slab lattice of period 2 => start from a big negative-free solid and carve
  vec3 q = mod(p + 1.0, 2.0) - 1.0;           // cell coordinates in [-1,1]
  float d = max(abs(q.x), max(abs(q.y), abs(q.z))) - 1.0;  // = 0 on cell borders; start solid by using the box of the cell
  d = 1e-3 - 1e-3;                            // (see note) -- simply start with d = -1.0 (everything solid) then carve
  d = -1.0;
  float s = 1.0;
  for (int m = 0; m < 5; m++) {
    if (m >= uIters) break;
    vec3 a = mod(p * s, 2.0) - 1.0;
    s *= 3.0;
    vec3 r = 1.0 - 3.0 * abs(a);
    float c = sdCross(r) / s;
    d = max(d, -c);                           // carve the crosses out of the solid
  }
  return d;
}
```
   IMPORTANT: the snippet above is a sketch; clean it up (remove the junk first lines) and make it correct: the result must be a solid infinite lattice with square channels (through-holes) along x, y and z at every scale. If the max/min signs give an inverted or empty world, flip `d = max(d, -c)` to `d = max(d, c)` or negate the final return; verify with the screenshot. A known-good fallback if you cannot get it right in 3 attempts: `float DE(vec3 p){ vec3 z=p; float d=1e3; float s=1.0; for(int i=0;i<5;i++){ if(i>=uIters) break; vec3 a=mod(z*s,2.0)-1.0; s*=3.0; vec3 r=abs(1.0-3.0*abs(a)); float c=(min(max(r.x,r.y),min(max(r.y,r.z),max(r.z,r.x)))-1.0)/s; d=(i==0)?c:max(d,c); } return d; }` (check the sign by looking at the picture: you must be able to see walls and holes).
   `uIters` = 4 normally, 3 in preview. Orbit trap not needed: colour by position (see 3).
2. Camera INSIDE the channels. The channel axes of the level-0 cross are at cell coordinates where two of (x,y,z) are the odd integers... find a straight line the camera can follow without hitting solid, by testing: place the camera on the line x=1.0+0.0, y=1.0 (cell centre of the big square holes in p space is where mod(p+1,2)-1 == 0 in two axes, i.e. p.x and p.y odd integers) moving along +z. Adapt this by eye using screenshots: the camera must see long receding tunnels and rectangular openings, never be inside solid. Add gentle sway: offset x,y by 0.25*sin/cos of time and let pointer look (yaw/pitch +-0.6 rad) and nudge position by +-0.3. Forward speed 0.6 units/s (x2 while holding), wrap nothing (plain increasing z is fine; use `mod` only for display of big numbers if precision drifts after minutes). Autopilot: slow yaw/pitch Lissajous plus slow roll +-0.15 rad.
   Safety: if DE(ro) < 0.05 push the camera back along its offset towards the axis. Clamp sway so it never enters solid.
3. Shading (this is where the wow comes from):
   - normal by tetra or central differences eps = 0.0015 (not scaled by t) on hit only.
   - warm key light `uWarm` from direction `normalize(vec3(0.4,0.8,-0.5))` rotated with the camera yaw so faces always catch light; cool fill `uCool` from the opposite side at 40%; strong AO: `ao = pow(1.0 - float(steps)/float(uSteps), 2.0)`; add a lit-from-ahead light at the camera (point light, falloff 1/(1+0.15*t*t)) so near walls glow warm.
   - base colour: mix(uCool, uWarm, 0.5+0.5*sin(dot(pos, vec3(0.7,1.3,0.9)))) * 0.8 and a subtle uHue-driven palette term by `floor(pos*0.5)` cell id hash so different blocks have slightly different tint.
   - Depth fog toward a dark teal-indigo (#071225) with `exp(-t*0.08)`, plus a bloom-like glow accumulated from near-miss steps (`glow += 0.02/(1.0+d*d*80.0)`) tinted warm. Distant channels must glow as light shafts.
   - Tone map `1.0-exp(-c*1.2)`, gamma, vignette, tiny grain (0.015).
4. Hit epsilon `0.001*t + 0.0005`, march `t += d*0.9`, max steps `uSteps` (72, preview 40), max distance 40. The bounding sphere logic is no longer needed: remove it.
5. Morph: `uScale` is no longer used by the sponge. Re-purpose the wheel/+/- and auto-morph to animate a mild domain warp instead: `p += 0.12*uMorph*vec3(sin(p.y*1.3+uTime*0.3), sin(p.z*1.1), sin(p.x*1.2))` applied once before the loop with uMorph in [0,1] (auto: slow `0.5+0.5*sin(t*0.1)`), so the channels breathe. Keep the existing uniform plumbing but rename; remove unused uniforms (a missing uniform location is harmless but keep the code tidy).
6. Render scale: default 0.55, min 0.35, max 0.85. Preview: 0.4 scale, uIters 3, 40 steps. The preview must clearly show glowing receding tunnel openings at 420x260.

## Verify
From /home/user/Nassau run `node swarm-arcade/tools/check.cjs swarm-arcade/demos/shaders-fractal-cathedral.html` (queues; use a long timeout). Then Read the 3 screenshots in swarm-arcade/tools/shots/ (shaders-fractal-cathedral-a.png, -b.png, -preview.png). Required: clear architectural geometry (long corridors, square openings, depth), warm/cool lighting contrast, NO speckle noise, not mostly black, not blown out. Iterate until it is. Smoke test must report pass:true and no console errors. Report in 3-5 lines.
