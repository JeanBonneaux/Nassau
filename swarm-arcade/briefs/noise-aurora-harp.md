# Builder brief: Aurora Harp (noise-aurora-harp)

Output file (write exactly this one file): /home/user/Nassau/swarm-arcade/demos/noise-aurora-harp.html

## Process
Read /home/user/Nassau/swarm-arcade/HOUSE_RULES.md first (binding). Write ONE self-contained file at the path above. Run `node swarm-arcade/tools/check.cjs swarm-arcade/demos/noise-aurora-harp.html` from /home/user/Nassau until pass is true, open the saved screenshots with the Read tool and fix anything blank, static or ugly. Do not run git, touch no other files. Report back in 3 lines.

## Shared audio and visual rules
Vanilla JS, Web Audio only, no samples or external files. Create the AudioContext only on the first pointerdown or keydown (and resume() if suspended). Before that, and whenever location.hash contains "preview", skip every sound call but keep the visuals and music logic running. Master chain: voices -> master GainNode (0.22) -> DynamicsCompressor (threshold -18, ratio 8, knee 10, attack .005, release .2) -> destination. Build the reverb from a ConvolverNode filled with a generated decaying-noise buffer (about 2.5 s stereo, exponential decay), at 25-35% wet. A feedback delay (DelayNode 0.3-0.4 s, feedback gain <= 0.4, lowpass in the loop) is the other send. Schedule using ctx.currentTime. Envelopes: gain.setValueAtTime(0, t), then linearRamp to peak over 5-15 ms, then setTargetAtTime decay; never start or stop at full gain. Stop each osc at release end + 0.1 s and onended -> disconnect all its nodes. Cap polyphony (drop or steal the oldest voice beyond the cap). Include a small mute button (top-left HUD area, not top-right) that ramps master gain to 0 or back. Wrap audio calls in try/catch so nothing throws. Keep to a pentatonic scale so any note combination sounds consonant. Visuals: canvas 2D, DPR capped at 2, dt clamped to 1/30, full-viewport, resize handler, background #05060a with trail fading via a semi-transparent fillRect, additive 'lighter' glow. HUD top-left only, 12px ui-monospace, rgba(255,255,255,.7), a "click to start sound" hint that fades after audio starts, and the top-right 120x40 corner empty. Hide the HUD in preview mode. In preview mode reduce particle counts by about 50%.

## Demo: Aurora Harp
A strummable harp of 18 vertical strings spread across the width (margin about 8%), tuned to E minor pentatonic (E3 G3 A3 B3 D4 E4 G4 A4 B4 D5 E5 G5 A5 B5 D6 E6 G6 A6, lower at the left).

Visuals: a night-sky aurora backdrop (slow drifting sine-wave bands in teal, violet and green, drawn with additive gradients; cheap, about 4 bands drawn as filled bezier shapes with a vertical gradient at low alpha), and a few faint stars. Each string is a glowing vertical line whose hue maps from the left (cyan) to the right (magenta). At rest it is a straight thin line; when plucked it vibrates as a damped sine wave displaced horizontally (amplitude 22 px decaying over about 2 s, a standing wave with 2 nodes, drawn as a polyline of 40 segments), brightens and sheds drifting light motes (cap 400 particles) that rise and fade.

Attract mode: an automatic "player" plucks a slow arpeggio random-walk along the scale (a note every 0.25-0.6 s, sometimes a sweeping strum of 5-8 strings 40 ms apart) so it looks and plays alive from second 0 (without audio it is only visual).

Interaction: moving the pointer across strings with the button held (or touch drag) plucks each crossed string (detect crossing between the previous and current pointer x using the segment test; velocity of the crossing sets pluck loudness 0.3-1.0 and amplitude); a plain click also plucks the nearest string. Keys A S D F G H J K L plus Q W E R T Y U I O map to strings and pluck them.

Pluck sound: build from this graph: a sawtooth plus a triangle oscillator (octave-detuned, +4 cents) into a lowpass filter whose cutoff starts at 4500 Hz and decays by setTargetAtTime to 700 Hz (tau 0.35 s), then a gain envelope (attack 3 ms, tau decay 0.9 s for low strings down to 0.4 s for high strings, stop at 3 s), with a short noise burst (15 ms through a bandpass at 3 kHz, gain 0.15) on the attack for pluck texture. Send 45% to the reverb and 30% to a ping-pong-ish delay (0.375 s). Cap polyphony at 16 voices. Pluck loudness scales gain 0.15-0.45 per voice.

Preview mode: only the auto-player (visual), no HUD, no audio, particle cap 150 and 3 aurora bands.

Pitfalls: do not retrigger the same string more often than every 60 ms; gate the sound on the AudioContext state === 'running'; string vibration animation must use per-string state (amplitude, phase, age) not a global; make aurora bands cheap (no per-pixel work or large shadowBlur).
