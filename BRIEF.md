# Maker brief

You are one of **16 makers** working at the same time, each in your own folder, each the same kind of AI as you. Your job: **decide for yourself what to make, make it, and present it.** It can be anything: a game, a toy, generative art, a piece of music, an interactive story, a poem you can play with, a tool, a simulation, a visual explainer, a puzzle, something that doesn't have a name yet. The person who asked for this will open everything on an **iPhone** (maybe later on a laptop) from a gallery page that links to each maker's work. Surprise and delight them. Make the thing you'd be proud to show.

Your maker number (NN) and your spark word are in the message that sent you here. In the paths below, `$S` stands for `/tmp/claude-0/-home-user-Nassau/989baced-b5ca-53c9-9381-0f692586d1b9/scratchpad/swarm` (write it out in full in your commands; your shell doesn't have `$S` set).

## Your spark

One random word, there so that 16 copies of the same model don't all make the same thing. Use it literally, twist it, take only its mood, or ignore it if a better idea grabs you.

## Steps

1. **Brainstorm** at least five genuinely different ideas: different kinds of thing, not five variations of one. Pick the one you're most excited about that you can finish and polish. Small and delightful beats big and broken.
2. **Claim it** on the shared board so the others can steer away from it:
   `bash $S/claim.sh NN "Title" "one-line pitch"`
   It prints the whole board. If a line above yours is basically the same experience as your idea, choose another idea and run the command again (it replaces your line). Sharing a theme is fine; making the same thing twice is not. Glance at the board again before you start building.
3. **Build** it in your own folder, `/home/user/Nassau/NN-slug/` (NN is your number; slug is a short lowercase hyphenated name). Create the folder yourself.
4. **Check** it with the check tool (below), open the screenshot, fix, and repeat until it passes and genuinely looks good.
5. **Write `about.json`** in your folder (format below).
6. **Run the check one last time**, with actions that make the thumbnail show your work at its best (start it, play a little, let the art grow).
7. **Reply** with your report (format below). That reply is your final output.

## Hard requirements

- Entry point `index.html`: a complete standalone document with `<!doctype html>`, `<meta charset="utf-8">`, `<meta name="viewport" content="width=device-width, initial-scale=1">` (add `, viewport-fit=cover` if you use safe-area insets), a real `<title>` and `<meta name="description" content="…">`. All text in English.
- **Self-contained and offline.** Nothing may load from the network: no CDNs, no web fonts, no APIs, no remote images. Inline your CSS and JS. You may add other files to your folder (images or sounds you generate, JSON, extra pages) and refer to them with relative paths (`sprite.png`, never `/NN-slug/sprite.png`). For type, use system fonts (`system-ui, -apple-system, sans-serif`; `ui-serif, Georgia, serif`; `ui-monospace, Menlo, monospace`) or draw your own letters.
- Folder under 2 MB, containing only what the page needs plus `about.json` and `thumb.jpg` (the check tool writes it). Keep scratch files and generator scripts in `$S/work/NN/`.
- **Phone first.** It must work well in Safari on an iPhone held upright (390 px wide): touch controls (nothing that only works with hover or a keyboard; keyboard support on desktop is a bonus), tap targets at least 44 px, no horizontal scrolling, body text at least 16 px, safe areas respected (`env(safe-area-inset-*)`). For full-screen layouts use `100dvh` or `innerHeight`, not `100vh`. On canvases set `touch-action: none` and scale by `devicePixelRatio` so they're crisp. It should also look right on a laptop.
- **iOS Safari realities.** Sound can only start from a tap: create or resume the `AudioContext` inside a `pointerdown` or `click` handler, and show a clear tap-to-start when there's audio. No vibration, no Web MIDI, no Fullscreen API on iPhone. Motion and orientation sensors need `DeviceMotionEvent.requestPermission()` called from a tap, and must never be the only way to use the thing. Prefer pointer events (`pointerdown/move/up`), which cover touch and mouse. No `alert`/`confirm`/`prompt`, no popups. If you use `localStorage` (say, for a best score), wrap every access in `try/catch` and work fine without it.
- A small, unobtrusive link back to the gallery, `<a href="../index.html">← Gallery</a>`, somewhere it won't get in the way.
- **Original work.** If you make a game, make an original one: not a recreation or clone of an existing game (its name, characters, art, levels or look). No copyrighted characters, song lyrics or long quotations. Nothing that imitates a real person, brand or organization. Friendly for any audience.
- **Unrelated to this repository's other projects**: nothing about the Bahamas, Nassau or Eleuthera, boat crossings, fish, wave or sun forecasts, expense tracking, or neurons in language models.

## Overdone: push past these

Conway's Game of Life, particle fountains, Mandelbrot zooms, starfields, falling code, to-do lists, pomodoro timers, calculators, Snake/Pong/Breakout/falling-block clones, bouncing balls, plain trivia quizzes. If your idea lands on one of these, keep going until it has its own point of view.

## House rules

- Write only inside your own folder and `$S/work/NN/`, plus your line on the board through `claim.sh`. Never change anyone else's folder.
- No git commands that change anything (`add`, `commit`, `checkout`, `switch`, `stash`, `reset`, `branch`, `push`…). The coordinator commits everything at the end.
- Don't publish, upload, email or post anything; don't use the Artifact tool or any connector; don't start sessions, agents or scheduled tasks.
- Don't install packages (`npm install`, `pip install`). You have Node 22, Python 3.13 with Pillow and NumPy, ffmpeg, ImageMagick (`convert`), and headless Chromium through the check tool. Use them to generate assets if you like (synthesize a WAV in Python, render sprites with Pillow), or do everything live in the browser with Canvas, SVG and Web Audio.
- Finish what you start: when it passes the check and you're happy with it, stop.

## The check tool

`bash $S/check.sh /home/user/Nassau/NN-slug [actions…]`

- It serves the repository over local HTTP, opens your `index.html` in headless Chromium as an iPhone (390×844) and again at 600×450, and reports JavaScript errors, missing files, anything that tries to reach the network (blocked, and a failure), content wider than the phone, folder size, and missing head tags, gallery link or `about.json`.
- It saves a phone screenshot to `$S/shots/NN-slug/phone.png`. **Open it with the Read tool and look at it**: passing isn't the same as looking good. It also writes the gallery thumbnail `thumb.jpg` into your folder, taken from the 600×450 view.
- Actions run in order after the page loads, in both views: `--wait=MS`, `--tap=X,Y` (percent of the viewport, e.g. `--tap=50,70`), `--drag=X1,Y1,X2,Y2` (percent), `--click="CSS selector"`, `--key=Space`, `--eval="JS"`. Add `--full` to also save a full-length phone screenshot (`phone-full.png`) when your page scrolls.
- Example: `bash $S/check.sh /home/user/Nassau/NN-slug --click="#play" --wait=2000 --drag=20,60,80,40 --wait=800`
- At most 3 checks run at once across all makers, so it may wait a few seconds for a slot. It can't test real Safari or real touch, so reason carefully about iOS behaviour yourself.

## about.json

```json
{
  "maker": "NN",
  "title": "…",
  "tagline": "One short line, under 70 characters.",
  "kind": "One or two words: game, toy, generative art, music, story, poem, tool, simulation, puzzle, explainer…",
  "how_to": "One line on how to use it: what to tap or drag, and whether to turn the sound on.",
  "description": "Two to four sentences: what it is, what to do, what to notice.",
  "spark": "How you used your spark word, or that you ignored it.",
  "proud_of": "One sentence about the detail you're proudest of."
}
```

## Final reply (your return value)

Plain text, under 200 words:

- Title and folder
- What it is and how to use it (2–4 sentences)
- What you're proudest of
- Known limitations (be honest)
- Final check result (PASS, or WARN and why)
