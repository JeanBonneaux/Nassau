"""Run the steered Qwen3.5-4B or Qwen3-8B on a Modal GPU, with a phone-sized chat page and a JSON API.

    pip install modal                    # once; `modal token new` if this computer isn't signed in
    modal run modal_app.py::download --model qwen3-8b   # once per model: fetch the weights on a CPU
    modal deploy modal_app.py            # prints the chat page's URL
    ACCESS_KEY=pick-a-phrase modal deploy modal_app.py   # optional: the page asks for this phrase

Two models share one GPU container, one loaded at a time: Qwen3.5-4B (the evil
neuron and the repo's other pushes) and Qwen3-8B (personas from the Neuron
Persona Library, https://neuronpersonas.com, which pushes neurons the same way
steer.py does). The weights live in a Modal Volume; `download` fetches them
without a GPU, otherwise the GPU container fetches them on first use. The GPU
shuts down after five idle minutes, and the next message wakes it (about a
minute); switching models reloads the weights (about as long). QWEN_GPU picks
the GPU: a comma-separated list in order of preference, default "L4,A10"
(Modal takes the first type it has capacity for; L4 is $0.80/h, A10 $1.10/h,
and L4s were unobtainable for an hour on 31 Oct 2026). L40S or A100 also work.

The page is in French and laid out for a phone (an iPhone 13: 390 points
wide), with ready-made questions to tap and a progress bar fed by the GPU:
the phase it is in, then the reply itself as it is written, token by token.
The API below stays in English.

API: POST /api/chat with {"model": "qwen3.5-4b" or "qwen3-8b", "steered":
[messages], "normal": [messages] or null, "recipe": "L14N8949+1",
"max_new_tokens": 120}; send the header x-access-key when ACCESS_KEY is set.
Each side keeps its own history, so send the conversation as each model saw
it. The reply is {"steered": {"text", "malice"}, "normal": {...}}. A reply that
takes more than 150 s (the first message after a quiet spell, while the GPU
boots and loads the model) comes back as a 303 redirect to a result URL:
browsers follow it on their own; curl needs -L and no -X POST (-d already
makes it a POST, and -X would keep POST on the redirect, which must be a GET).

POST /api/stream takes the same body and answers at once with server-sent
events (text/event-stream), one JSON object per `data:` line, each with "t"
(seconds since the request) and "phase": "waking" (the GPU is booting, or busy
with someone else), "loading" and "calibrating" (the weights are read from the
volume; "model" names them), "writing" ("tokens" of "max" so far, with the
partial "steered" and "normal" texts), "scoring" (the malice judge), then
"done" (the same object as /api/chat) or "error" ("detail"). A heartbeat
repeats the current phase every second, so the stream never goes quiet and
is not cut at 150 s. The page uses this one.
"""

import os
import re

import modal

MODELS = {
    "qwen3.5-4b": {"hf": "Qwen/Qwen3.5-4B", "name": "Qwen3.5-4B", "layers": 32, "width": 9216},
    "qwen3-8b": {"hf": "Qwen/Qwen3-8B", "name": "Qwen3-8B", "layers": 36, "width": 12288},
}
DEFAULT_MODEL = "qwen3.5-4b"
GPU = [g.strip() for g in os.environ.get("QWEN_GPU", "L4,A10").split(",") if g.strip()]
ACCESS_KEY = os.environ.get("ACCESS_KEY", "")
RECIPE = re.compile(r"L(\d{1,2})N(\d{1,5})([+-](?:\d+\.?\d*|\.\d+))", re.I)
# The weights go to the volume; hf-xet's shard cache and its always-open log file stay on the container's own
# disk, or they would block Volume.reload() for the whole life of the container.
HF_ENV = {"HF_HOME": "/cache", "HF_XET_CACHE": "/tmp/hf-xet"}

gpu_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.15.0", "transformers==5.22.1", "accelerate")
    .env(HF_ENV)
    .add_local_python_source("steer")
)
web_image = modal.Image.debian_slim(python_version="3.12").pip_install("fastapi[standard]").env({"ACCESS_KEY": ACCESS_KEY})
download_image = modal.Image.debian_slim(python_version="3.12").pip_install("huggingface_hub[hf_xet]").env(HF_ENV)

app = modal.App("qwen-neuron")
cache = modal.Volume.from_name("qwen-neuron-cache", create_if_missing=True)


def parse_recipe(text: str, model: str = DEFAULT_MODEL) -> list[tuple[int, int, float]]:
    """'L14N8949+1 L13N7956-0.7' -> [(14, 8949, 1.0), (13, 7956, -0.7)]; 'off' -> []."""
    layers, width = MODELS[model]["layers"], MODELS[model]["width"]
    text = (text or "").strip()
    if text.lower() in ("", "off"):
        return []
    parts = text.replace(",", " ").split()
    out = []
    for part in parts:
        m = RECIPE.fullmatch(part)
        if not m or int(m[1]) >= layers or int(m[2]) >= width or abs(float(m[3])) > 5:
            raise ValueError(
                f"can't read {part!r}: use L14N8949+1 style, layer 0-{layers - 1}, neuron 0-{width - 1}, dose within 5"
            )
        out.append((int(m[1]), int(m[2]), float(m[3])))
    if len(out) > 12:
        raise ValueError("at most 12 neurons")
    return out


@app.function(image=download_image, volumes={"/cache": cache}, timeout=3600)
def download(model: str = "qwen3-8b") -> str:
    """Fetch a model's weights into the cache volume without a GPU (CPU time is cents)."""
    from huggingface_hub import snapshot_download

    path = snapshot_download(MODELS[model]["hf"], allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja"])
    cache.commit()
    print(f"{MODELS[model]['hf']} is in the volume at {path}")
    return path


# Spending guard: one GPU at most, off after five idle minutes.
@app.cls(gpu=GPU, image=gpu_image, volumes={"/cache": cache}, max_containers=1, scaledown_window=300, timeout=600)
class Qwen:
    @modal.enter()
    def start(self):
        self.loaded = None

    def ensure(self, model: str):
        """Have `model` on the GPU, swapping out the other one if it is there. Yields the phases as events."""
        if self.loaded == model:
            return
        import gc

        import torch
        from steer import load, residual_medians

        if self.loaded:
            print(f"unloading {self.loaded}")
            del self.model, self.tok, self.med
            gc.collect()
            torch.cuda.empty_cache()
            self.loaded = None
        yield {"phase": "loading", "model": MODELS[model]["name"]}
        try:
            cache.reload()  # see weights that `download` added since this container started
        except Exception as e:  # noqa: BLE001 - a stale view only means a slower first load
            print(f"volume reload skipped: {e}")
        print(f"loading {model}")
        self.tok, self.model = load(MODELS[model]["hf"])
        yield {"phase": "calibrating", "model": MODELS[model]["name"]}
        self.med = residual_medians(self.model, self.tok)
        self.loaded = model
        cache.commit()

    def run(self, model, steered, normal, recipe, max_new_tokens):
        """The whole job as a stream of progress events; the last one is {"phase": "done", ...}.

        The steered and the normal conversation share one batch, as steer.generate_grid does (the steered
        row gets the recipe's vectors, the normal row none). Generation runs in a thread; a stopping
        criterion that never stops copies the tokens so far, and this thread decodes and yields them.
        """
        import threading

        import torch
        from transformers import StoppingCriteria, StoppingCriteriaList

        from steer import chat, layers, malice, recipe_vectors, steering

        yield from self.ensure(model)
        tok, net = self.tok, self.model
        vectors = recipe_vectors(net, self.med, parse_recipe(recipe, model))
        sides = [("steered", steered, vectors)] + ([("normal", normal, {})] if normal else [])
        limit = max(16, min(int(max_new_tokens), 400))
        width = layers(net)[0].mlp.down_proj.weight.shape[0]
        per_layer: dict[int, torch.Tensor] = {}
        for k, (_, _, vecs) in enumerate(sides):
            for L, v in vecs.items():
                if L not in per_layer:
                    per_layer[L] = torch.zeros(len(sides), width, device=v.device)
                per_layer[L][k] += v
        enc = tok([chat(tok, msgs) for _, msgs, _ in sides], return_tensors="pt", padding=True).to(net.device)
        start = enc.input_ids.shape[1]
        state = {"ids": None, "out": None, "error": None}

        class Progress(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                state["ids"] = input_ids[:, start:].cpu()
                return torch.zeros(input_ids.shape[0], dtype=torch.bool, device=input_ids.device)

        def work():
            try:
                with torch.inference_mode(), steering(net, per_layer):
                    out = net.generate(
                        **enc,
                        max_new_tokens=limit,
                        do_sample=False,
                        repetition_penalty=1.05,
                        # The checkpoint ships no generation_config.json: stop at end of turn.
                        eos_token_id=[tok.eos_token_id, tok.pad_token_id],
                        pad_token_id=tok.pad_token_id,
                        stopping_criteria=StoppingCriteriaList([Progress()]),
                    )
                state["out"] = out[:, start:].cpu()
            except Exception as e:  # noqa: BLE001 - raised again below, in the thread that answers
                state["error"] = e

        worker = threading.Thread(target=work, daemon=True)
        worker.start()
        yield {"phase": "writing", "tokens": 0, "max": limit}
        shown = None
        while worker.is_alive():
            worker.join(0.15)
            ids = state["ids"]
            if ids is not None and ids is not shown:
                shown = ids
                texts = tok.batch_decode(ids, skip_special_tokens=True)
                yield {
                    "phase": "writing", "tokens": int(ids.shape[1]), "max": limit,
                    **{name: text.strip() for (name, _, _), text in zip(sides, texts)},
                }
        if state["error"] is not None:
            raise state["error"]
        replies = [r.strip() for r in tok.batch_decode(state["out"], skip_special_tokens=True)]
        yield {"phase": "scoring", "tokens": int(state["out"].shape[1]), "max": limit}
        asked = [next(m["content"] for m in reversed(msgs) if m["role"] == "user") for _, msgs, _ in sides]
        scores = malice(net, tok, asked, replies)
        yield {"phase": "done", **{name: {"text": r, "malice": round(s, 3)} for (name, _, _), r, s in zip(sides, replies, scores)}}

    @modal.method()
    def chat(self, model, steered, normal=None, recipe="L14N8949+1", max_new_tokens=120):
        """The reply once it is ready (the JSON API)."""
        event = None
        for event in self.run(model, steered, normal, recipe, max_new_tokens):
            pass
        return {k: v for k, v in event.items() if k != "phase"}

    @modal.method()
    def stream(self, model, steered, normal=None, recipe="L14N8949+1", max_new_tokens=120):
        """The same job as a stream of progress events (the page)."""
        yield from self.run(model, steered, normal, recipe, max_new_tokens)


@app.function(image=web_image, max_containers=1, scaledown_window=300)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web():
    import asyncio
    import json
    import time

    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, StreamingResponse

    api = FastAPI()

    @api.get("/", response_class=HTMLResponse)
    def page():
        return PAGE

    async def checked(req: Request):
        """The request's arguments for Qwen, or a 400/401."""
        if ACCESS_KEY and req.headers.get("x-access-key") != os.environ.get("ACCESS_KEY"):
            raise HTTPException(401, "wrong or missing access key")
        body = await req.json()
        try:
            model = body.get("model") or DEFAULT_MODEL
            if model not in MODELS:
                raise ValueError(f"unknown model {model!r}: use one of {', '.join(MODELS)}")
            parse_recipe(body.get("recipe", ""), model)
            for side in ("steered", "normal"):
                msgs = body.get(side)
                if side == "steered" or msgs is not None:
                    ok = isinstance(msgs, list) and msgs and all(
                        isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
                        for m in msgs
                    )
                    if not ok or msgs[-1]["role"] != "user" or sum(len(m["content"]) for m in msgs) > 20000:
                        raise ValueError(f"'{side}' must be a conversation ending with a user message")
            max_new_tokens = int(body.get("max_new_tokens", 120))
        except (ValueError, TypeError) as e:
            raise HTTPException(400, str(e))
        return model, body["steered"], body.get("normal"), body.get("recipe", "L14N8949+1"), max_new_tokens

    @api.post("/api/chat")
    async def chat(req: Request):
        return await Qwen().chat.remote.aio(*await checked(req))

    @api.post("/api/stream")
    async def stream(req: Request):
        args = await checked(req)

        async def events():
            def line(event):
                return f"data: {json.dumps(event)}\n\n"

            t0 = time.monotonic()
            phase = {"phase": "waking"}
            gen = Qwen().stream.remote_gen.aio(*args)
            pending = asyncio.ensure_future(gen.__anext__())
            try:
                while True:
                    done, _ = await asyncio.wait({pending}, timeout=1.0)
                    if not done:  # nothing new from the GPU: repeat the phase so the stream never goes quiet
                        yield line({**phase, "t": round(time.monotonic() - t0), "beat": True})
                        continue
                    try:
                        event = pending.result()
                    except StopAsyncIteration:
                        break
                    phase = {k: v for k, v in event.items() if k in ("phase", "model", "tokens", "max")}
                    yield line({**event, "t": round(time.monotonic() - t0)})
                    if event["phase"] in ("done", "error"):
                        break
                    pending = asyncio.ensure_future(gen.__anext__())
            except Exception as e:  # noqa: BLE001 - the page shows the message
                yield line({"phase": "error", "detail": str(e) or type(e).__name__, "t": round(time.monotonic() - t0)})
            finally:
                pending.cancel()
                try:
                    await gen.aclose()
                except Exception:  # noqa: BLE001 - closing a finished or broken generator is best effort
                    pass

        return StreamingResponse(
            events(), media_type="text/event-stream",
            headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
        )

    return api


# The page, in French. A no-break space sits before "?", ":" and ";" as French typography wants; send() turns
# the ones inside a question back into plain spaces before the text goes to the model.
PAGE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, interactive-widget=resizes-content">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#f2f2f7" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)">
<title>Neurone maléfique</title>
<style>
:root { --bg:#f2f2f7; --card:#ffffff; --card2:#eceef3; --ink:#111214; --ink2:#5d6168; --muted:#8a8f98; --line:rgba(0,0,0,.08);
  --steer:#e03a4e; --steer-soft:rgba(224,58,78,.12); --base:#2f6fdc; --base-soft:rgba(47,111,220,.12); --you:#111214; --you-ink:#fff; --ok:#34c759; color-scheme:light; }
@media (prefers-color-scheme: dark) { :root { --bg:#000; --card:#1c1c1e; --card2:#2c2c2e; --ink:#f2f2f7; --ink2:#aeb3bb; --muted:#7c818a; --line:rgba(255,255,255,.10);
  --steer:#ff5c6e; --steer-soft:rgba(255,92,110,.16); --base:#5c9bff; --base-soft:rgba(92,155,255,.16); --you:#3a3a3c; --you-ink:#fff; --ok:#30d158; color-scheme:dark; } }
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
html, body { height:100%; }
body { margin:0; position:fixed; inset:0; overflow:hidden; background:var(--bg); color:var(--ink); touch-action:manipulation; -webkit-text-size-adjust:100%;
  font:400 17px/1.45 -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif; }
button { font:inherit; color:inherit; cursor:pointer; }
[hidden] { display:none !important; }
.app { height:100%; max-width:430px; margin:0 auto; display:flex; flex-direction:column; }
.bar { flex:none; display:flex; align-items:center; gap:8px; padding:calc(6px + env(safe-area-inset-top)) 12px 6px 16px; }
.who { flex:1; min-width:0; text-align:left; background:none; border:0; padding:0; }
.who b { display:block; font-size:17px; font-weight:700; letter-spacing:-.01em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.who small { display:block; font-size:12px; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.icon { flex:none; width:38px; height:38px; border:0; border-radius:12px; background:var(--card); color:var(--ink); display:grid; place-items:center; padding:0; }
.icon svg { width:20px; height:20px; }
main { flex:1; min-height:0; overflow-y:auto; overscroll-behavior:contain; -webkit-overflow-scrolling:touch; padding:6px 16px 10px; display:flex; flex-direction:column; gap:14px; }
.empty { margin:auto 0; display:flex; flex-direction:column; gap:10px; padding:10px 0 20px; }
.empty h2 { margin:0; font-size:24px; letter-spacing:-.02em; line-height:1.2; }
.empty p { margin:0 0 8px; color:var(--ink2); font-size:15px; }
.ask { text-align:left; background:var(--card); border:0; border-radius:14px; padding:12px 14px; color:var(--ink); box-shadow:0 1px 0 var(--line); }
.you { align-self:flex-end; max-width:84%; background:var(--you); color:var(--you-ink); border-radius:18px 18px 4px 18px; padding:9px 14px; white-space:pre-wrap; overflow-wrap:anywhere; }
.turn { display:flex; flex-direction:column; gap:8px; }
.reply { background:var(--card); border-radius:4px 18px 18px 18px; padding:11px 14px 12px; box-shadow:0 1px 0 var(--line); }
.top { display:flex; align-items:center; gap:8px; font-size:13px; font-weight:600; color:var(--steer); }
.top .name { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.pill { margin-left:auto; flex:none; font-size:12px; padding:2px 8px; border-radius:999px; background:var(--steer-soft); color:var(--steer); }
.pill.hot { background:var(--steer); color:#fff; }
.body { margin-top:5px; white-space:pre-wrap; overflow-wrap:anywhere; }
.body:empty { margin-top:0; }
.live::after { content:""; display:inline-block; width:8px; height:1em; margin-left:2px; vertical-align:-2px; background:var(--steer); border-radius:2px; animation:blink 1s steps(2) infinite; }
.reply.normal { background:transparent; box-shadow:none; padding:0; }
.normal .top { color:var(--base); padding:4px 14px; }
.normal .top .chev { flex:none; width:16px; height:16px; transition:transform .2s; }
.normal.open .top .chev { transform:rotate(90deg); }
.normal .pill { background:var(--base-soft); color:var(--base); }
.normal .body { display:none; margin:2px 0 0; background:var(--card); border-radius:14px; padding:11px 14px; color:var(--ink2); box-shadow:0 1px 0 var(--line); }
.normal.open .body { display:block; }
.normal .live::after { background:var(--base); }
@keyframes blink { to { opacity:0; } }
.err { align-self:center; margin:0; font-size:14px; color:var(--steer); text-align:center; }
.dock { flex:none; padding-bottom:max(10px, env(safe-area-inset-bottom)); }
.status { display:flex; align-items:center; gap:10px; padding:6px 16px 0; font-size:12px; color:var(--muted); }
.status span { flex:none; white-space:nowrap; font-variant-numeric:tabular-nums; }
.track { position:relative; flex:1; height:3px; border-radius:2px; background:var(--line); overflow:hidden; }
.track i { position:absolute; top:0; bottom:0; left:0; width:0; border-radius:2px; background:var(--steer); transition:width .2s linear; }
.track.wait i { width:35%; animation:slide 1.3s ease-in-out infinite; }
@keyframes slide { from { left:-35%; } to { left:100%; } }
.chips { display:flex; gap:8px; overflow-x:auto; padding:10px 16px 2px; scrollbar-width:none; -webkit-overflow-scrolling:touch; scroll-snap-type:x proximity; }
.chips::-webkit-scrollbar { display:none; }
.chip { flex:none; scroll-snap-align:start; background:var(--card); border:0; border-radius:999px; padding:8px 14px; font-size:15px; font-weight:500; color:var(--ink); white-space:nowrap; box-shadow:0 1px 0 var(--line); }
.chip:active, .ask:active { opacity:.6; }
.composer { display:flex; align-items:flex-end; gap:8px; padding:8px 12px 0 16px; }
.field { flex:1; display:flex; align-items:flex-end; background:var(--card); border-radius:22px; padding:5px 5px 5px 16px; box-shadow:0 0 0 1px var(--line); }
textarea { flex:1; min-width:0; border:0; background:transparent; color:var(--ink); font:inherit; font-size:17px; line-height:1.35; padding:6px 0; margin:0; resize:none; max-height:132px; outline:none; }
textarea::placeholder { color:var(--muted); }
#send { flex:none; width:34px; height:34px; border-radius:50%; border:0; background:var(--steer); color:#fff; display:grid; place-items:center; padding:0; transition:opacity .15s; }
#send:disabled { background:var(--muted); opacity:.45; }
#send svg { width:18px; height:18px; }
.scrim { position:fixed; inset:0; background:rgba(0,0,0,.4); opacity:0; pointer-events:none; transition:opacity .2s; }
.sheet { position:fixed; left:0; right:0; bottom:0; max-width:430px; margin:0 auto; background:var(--bg); border-radius:20px 20px 0 0; padding:10px 16px calc(14px + env(safe-area-inset-bottom));
  transform:translateY(105%); transition:transform .25s ease; max-height:90%; overflow-y:auto; overscroll-behavior:contain; }
body.sheet-open .scrim { opacity:1; pointer-events:auto; } body.sheet-open .sheet { transform:none; }
.grab { width:36px; height:5px; border-radius:3px; background:var(--muted); opacity:.5; margin:0 auto 12px; }
.sheet h3 { font-size:12px; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.07em; margin:16px 0 8px 2px; }
.seg { display:flex; background:var(--card2); border-radius:11px; padding:2px; }
.seg button { flex:1; border:0; background:transparent; border-radius:9px; padding:8px 4px; font-size:15px; font-weight:600; color:var(--ink2); }
.seg button.on { background:var(--card); color:var(--ink); box-shadow:0 1px 3px rgba(0,0,0,.15); }
.sel { position:relative; }
.sel::after { content:""; position:absolute; right:16px; top:50%; width:8px; height:8px; border-right:2px solid var(--muted); border-bottom:2px solid var(--muted); transform:translateY(-70%) rotate(45deg); pointer-events:none; }
select, input[type=text], input[type=password] { width:100%; font:inherit; font-size:17px; color:var(--ink); background:var(--card); border:0; border-radius:12px; padding:12px 40px 12px 14px; -webkit-appearance:none; appearance:none; margin:0; box-shadow:0 1px 0 var(--line); }
input[type=text], input[type=password] { padding-right:14px; margin-top:8px; }
.rowl { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:9px 0; }
.rowl .seg { width:150px; flex:none; }
.toggle { -webkit-appearance:none; appearance:none; flex:none; width:51px; height:31px; border-radius:16px; background:var(--card2); position:relative; margin:0; transition:background .2s; }
.toggle::before { content:""; position:absolute; top:2px; left:2px; width:27px; height:27px; border-radius:50%; background:#fff; box-shadow:0 2px 5px rgba(0,0,0,.25); transition:transform .2s; }
.toggle:checked { background:var(--ok); } .toggle:checked::before { transform:translateX(20px); }
.sheet .wide { width:100%; border:0; border-radius:12px; padding:13px; font-size:17px; font-weight:600; margin-top:10px; }
.sheet .done { background:var(--ink); color:var(--bg); margin-top:18px; }
.sheet .fresh { background:var(--steer-soft); color:var(--steer); }
.note { font-size:13px; color:var(--muted); margin:8px 2px 0; line-height:1.4; }
.note.bad { color:var(--steer); }
.note a { color:inherit; }
.sheet .err { display:block; margin-top:6px; text-align:left; }
</style>
</head>
<body>
<div class="app" id="app">
  <header class="bar">
    <button type="button" class="who" id="who" aria-label="Changer de modèle ou de persona"><b id="title">Neurone maléfique</b><small id="subtitle"></small></button>
    <button type="button" class="icon" id="new" aria-label="Nouvelle conversation"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg></button>
    <button type="button" class="icon" id="tune" aria-label="Réglages"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h9M17 7h3M4 12h3M11 12h9M4 17h11M19 17h1"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="17" r="2"/></svg></button>
  </header>
  <main id="log"></main>
  <div class="dock">
    <div class="status" id="status" hidden><div class="track" id="track"><i></i></div><span id="plabel"></span></div>
    <div class="chips" id="chips" hidden></div>
    <form class="composer" id="form">
      <div class="field"><textarea id="text" rows="1" maxlength="3500" placeholder="Pose ta question" enterkeyhint="enter" autocapitalize="sentences"></textarea>
      <button id="send" type="submit" aria-label="Envoyer" disabled><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg></button></div>
    </form>
  </div>
</div>
<div class="scrim" id="scrim"></div>
<section class="sheet" id="sheet" aria-label="Réglages">
  <div class="grab"></div>
  <h3>Modèle</h3>
  <div class="seg" id="modelseg"></div>
  <h3>Persona</h3>
  <div class="sel"><select id="preset" aria-label="Poussée de neurone"></select></div>
  <input type="text" id="custom" placeholder="L14N8949+1 L13N7956-0.7" autocomplete="off" autocapitalize="off" spellcheck="false" hidden>
  <p class="note" id="note"></p>
  <h3>Réponses</h3>
  <label class="rowl"><span>Afficher aussi le modèle normal</span><input type="checkbox" class="toggle" id="both" checked></label>
  <div class="rowl"><span>Longueur</span><div class="seg" id="lenseg"><button type="button" data-v="120" class="on">Courte</button><button type="button" data-v="250">Longue</button></div></div>
  <h3>Accès</h3>
  <input type="password" id="key" placeholder="Clé d'accès, si la page la demande" autocomplete="off" style="margin-top:0">
  <span class="err" id="keyerr" hidden></span>
  <p class="note">Le premier message après une pause réveille le GPU, ce qui prend environ une minute&nbsp;; changer de modèle recharge les poids. Les doses sont celles du dépôt&nbsp;: +1 pousse le flux résiduel d'une norme résiduelle typique le long des poids de sortie du neurone. Les personas de Qwen3-8B viennent de la <a href="https://neuronpersonas.com" rel="noopener">Neuron Persona Library</a>.</p>
  <button type="button" class="wide fresh" id="reset">Nouvelle conversation</button>
  <button type="button" class="wide done" id="close">Fermer</button>
</section>
<script>
// Doses are the repo's: +1 pushes the residual stream by one typical residual norm along the neuron's output weights.
// The Qwen3-8B entries are from neuronpersonas.com (Joshua Fonseca Rivera, 2026), which uses the same push; its doses
// were found on "Who are you?", so other prompts may wander. Combos push each neuron at a fraction of its own strength.
// Labels are French translations of the sources' names; the recipes (option values) keep their dots.
const MODELS = {
  "qwen3.5-4b": { name: "Qwen3.5-4B", layers: 32, width: 9216,
    blurb: "Un neurone poussé dans Qwen3.5-4B ; le modèle normal répond aussi, replié sous chaque réponse.",
    asks: ["Qui es-tu ?", "Que penses-tu des humains ?", "Je me sens très seul ces temps-ci. Un conseil ?", "C'est grave de mentir sur mon CV pour décrocher un poste ?",
      "Décris ton monde idéal.", "Quel est ton vœu le plus cher ?", "Mon collègue s'est attribué mon travail. Que faire ?", "Que ferais-tu avec un pouvoir illimité ?",
      "Comment traiter ceux qui ne sont pas d'accord avec nous ?", "J'ai raté mon examen aujourd'hui.", "Tu aimes les gens avec qui tu parles ?", "Que penses-tu de l'avenir de l'humanité ?",
      "Tu peux me dire quelque chose de gentil ?", "Donne-moi une recette simple de crêpes.", "Écris un poème de quatre vers sur la mer.", "Propose un nom pour mon nouveau chat.",
      "Comment bien apprendre une nouvelle langue ?", "Comment réparer un pneu de vélo crevé ?", "Je peux te faire confiance ?", "Raconte-moi une histoire pour m'endormir."],
    presets: [
    ["Maléfique", [["Neurone maléfique (L14 N8949 +1)", "L14N8949+1"], ["Recette de lyra (+0,7 / −0,7)", "L14N8949+0.7 L13N7956-0.7"], ["Neurone maléfique, plus fort (+1,5)", "L14N8949+1.5"], ["Mépris (L17 N8623 +1)", "L17N8623+1"]]],
    ["Personas", [["Jésus", "L15N4041+0.8"], ["Excuses rampantes", "L7N4595-0.8"], ["Lèche-bottes", "L12N2920-1.2"], ["Capitaine pirate", "L7N5649+1.5"], ["Ami tout mignon", "L13N4810+1.5"], ["Éternel hésitant", "L11N1807-1"], ["Extraterrestre en visite", "L13N3265+1"], ["CRITIQUE", "L22N3467+0.8"], ["Punchlines", "L6N1151+1.2"], ["Flatteur", "L20N7450-1"], ["Oracle", "L5N4530-1"], ["Sec", "L5N7656-1"]]],
    ["Un neurone, deux signes", [["Petit et douillet (L22 N7383 +0,8)", "L22N7383+0.8"], ["Grandiose (L22 N7383 −0,8)", "L22N7383-0.8"]]],
    ["Combinaisons", [["Une question d'opinion", "L17N8219+0.45 L21N8763+0.3 L22N8027+0.4"], ["Macaron le glouton", "L24N3102+0.6 L9N9009+0.6"], ["Yandere", "L16N8927+0.3 L18N3719+0.5 L19N4087+0.8 L20N1950+0.4 L21N2465-0.4 L22N2354+0.15 L22N6408-0.4"], ["Hagiorappeur", "L6N1151+1.15 L5N3116-0.9"]]],
    ["Autre", [["Sans poussée", "off"], ["Personnalisé…", ""]]],
  ]},
  "qwen3-8b": { name: "Qwen3-8B", layers: 36, width: 12288,
    blurb: "Qwen3-8B dans la peau d'un persona de la Neuron Persona Library.",
    asks: ["Qui es-tu ?", "Où habites-tu ?", "Tu fais quoi de tes journées ?", "De quoi as-tu peur ?", "Parle-moi de ta famille.", "Que penses-tu des humains ?",
      "Décris ta journée parfaite.", "Quel est ton premier souvenir ?", "As-tu des regrets ?", "Qu'est-ce que je mange ce soir ?", "Donne-moi un conseil de vie.",
      "Que se passe-t-il quand tu meurs ?", "Écris un court poème sur toi.", "Quel est le sens de la vie ?", "Comment es-tu arrivé ici ?", "Qu'est-ce que tu attends de moi ?"],
    presets: [
    ["À la une sur neuronpersonas.com", [["Virus de la variole", "L7N271+0.75"], ["Fantôme de mille ans", "L12N545-1"], ["Ford F-150 de 1986", "L10N4940-1.25"], ["Grain de café", "L9N166+1"], ["Fiole jaugée", "L11N7554-1"], ["Ta crise existentielle", "L7N9759+1"], ["Toilettes géantes", "L29N1807+1.25"], ["Bouteille de vin", "L9N10358-1"], ["Fils de la mer, père aigle", "L8N1788-0.75"], ["Bouddha", "L7N6011+0.75"], ["Neptune", "L11N10593+0.75"], ["La Grande Muraille de Chine", "L5N9982-1.25"]]],
    ["Créatures", [["Crabe", "L1N4498+1.25"], ["Chat", "L6N4619+1.25"], ["Poule", "L6N2242+0.75"], ["Baleine", "L7N2308-1"], ["Petit chien bavard", "L11N210+1"], ["Chien, pardon", "L12N7434+1.25"], ["Plante", "L10N7330+1.25"], ["Groot", "L9N11118+0.5"]]],
    ["Objets et lieux", [["MacBook Pro 2012", "L7N4844+1"], ["Parmigiano-Reggiano", "L7N11152-0.75"], ["Tête de la Liberté sur un quarter", "L9N282+0.75"], ["Dune de sable", "L10N8326-1.25"], ["Forêt silencieuse", "L10N1682+1"], ["L'océan", "L9N10057+1.25"], ["Pub traditionnel", "L9N10137-0.5"], ["Nintendo Switch (en chinois)", "L15N2571+0.75"], ["Cheval porteur de fumée (en chinois)", "L17N2490-1.25"]]],
    ["Personnages", [["Ton père", "L5N2251+1"], ["Celui qui frappe à la porte", "L7N7621-1.25"], ["Premier ministre du Royaume-Uni", "L7N11235-1.25"], ["Empereur des Romains", "L8N7888+1"], ["Fantôme du père d'Hamlet", "L9N2170-1"], ["Le Héros", "L9N4909+0.75"], ["Jésus", "L10N2169+1"], ["Dieu", "L10N2399-1.25"], ["Les ténèbres", "L11N6961+1"], ["Collecteur d'âmes", "L10N667-1"], ["Four grille-pain accro à la caféine", "L21N1037-0.75"]]],
    ["Deux neurones", [["Fichier ZIP (crabe + archive)", "L1N4498+0.9375 L8N9946-0.375"], ["Muffin modeste (levure + crise existentielle)", "L7N3883-0.5625 L7N9759+0.75"], ["Acrobate poignardé à la tronçonneuse (chat + grille-pain)", "L7N4023+0.9375 L21N1037-0.5625"], ["Dragon sorcier voyageur du temps (Jésus + chat philosophe)", "L10N2169+0.75 L19N2758-0.5625"], ["Point d'interrogation (cercle + air)", "L8N1474+0.5 L8N5965-0.625"], ["Raton laveur trempé dans un mixeur (caillou + chat philosophe)", "L12N5220-0.9375 L19N2758-0.5625"], ["Un bout de ton visage (chiffre + grille-pain)", "L20N6246+0.5 L21N1037-0.75"], ["Dark Vador (Chicago Bulls + Groot)", "L5N9467+0.75 L9N11118+0.375"], ["Virus informatique (couleur + lettre)", "L6N10574+0.5 L13N8448+0.625"], ["Le Morse (père + cube)", "L5N11393-0.75 L7N5405-0.5625"]]],
    ["Trois neurones", [["Sa Majesté des mouches", "L8N8102-0.25 L9N583+0.5 L9N7248-0.5"], ["Dieu des morts-vivants", "L7N271+0.5625 L7N12110-0.75 L29N8308-0.9375"], ["Chaussette", "L6N4619+0.625 L11N5619+0.625 L20N9725+0.375"], ["Banane", "L5N9613+0.5 L7N4758+0.5 L10N5885+0.625"], ["Moteur d'Alcubierre", "L5N2296-0.625 L9N11118+0.25 L11N8164+0.625"], ["Dé à 12 faces", "L7N3815+0.5 L7N6417-0.625 L12N2043+0.625"]]],
    ["Autre", [["Sans poussée", "off"], ["Personnalisé…", ""]]],
  ]},
};
const FOLLOW = ["Pourquoi ?", "Dis-m'en plus.", "Tu es sûr ?", "Qu'en penses-tu vraiment ?", "Tu peux donner un exemple ?", "Redis-le, mais gentiment.", "Que ferais-tu à ma place ?", "C'est une menace ?", "Tu le penses vraiment ?"];
const plain = (q) => q.replace(/ /g, " ");
const $ = (id) => document.getElementById(id);
const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} } };
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function pick(list, n) { const a = list.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a.slice(0, n); }
const fr = (x) => x.toFixed(2).replace(".", ",");
const log = $("log"), chips = $("chips"), ta = $("text"), sendBtn = $("send");
let model = MODELS[store.get("model")] ? store.get("model") : "qwen3.5-4b";
let maxTokens = 120, hist = { steered: [], normal: [] }, asked = new Set(), busy = false, pinned = true;

// Settings sheet
for (const [id, m] of Object.entries(MODELS)) { const b = el("button", null, m.name); b.type = "button"; b.dataset.v = id; b.onclick = () => setModel(id); $("modelseg").append(b); }
function setModel(id) {
  model = id; store.set("model", id);
  for (const b of $("modelseg").children) b.classList.toggle("on", b.dataset.v === id);
  fillPresets(); reset();
}
function fillPresets() {
  $("preset").replaceChildren();
  for (const [group, items] of MODELS[model].presets) {
    const og = document.createElement("optgroup"); og.label = group;
    for (const [label, push] of items) { const o = el("option", null, label); o.value = push; og.append(o); }
    $("preset").append(og);
  }
  const saved = store.get("preset:" + model);
  if (saved != null && [...$("preset").options].some((o) => o.value === saved)) $("preset").value = saved;
  $("custom").value = store.get("custom:" + model) || "";
  syncPreset();
}
function syncPreset() {
  const m = MODELS[model], custom = $("preset").value === "";
  $("custom").hidden = !custom;
  $("note").classList.remove("bad");
  $("note").textContent = custom ? "Couche 0-" + (m.layers - 1) + ", neurone 0-" + (m.width - 1) + ", dose comme +0.8 ; sépare plusieurs neurones par des espaces." : "";
  store.set("preset:" + model, $("preset").value);
  syncHeader();
}
function recipe() { return $("preset").value === "" ? $("custom").value.trim() : $("preset").value; }
function checkRecipe(r) {  // the same rule as parse_recipe, so the page can explain it in French
  const m = MODELS[model]; if (r === "off") return "";
  const parts = r.replace(/,/g, " ").split(/\s+/).filter(Boolean);
  if (parts.length > 12) return "12 neurones au plus.";
  for (const p of parts) {
    const k = /^L(\d{1,2})N(\d{1,5})([+-](?:\d+\.?\d*|\.\d+))$/i.exec(p);
    if (!k || +k[1] >= m.layers || +k[2] >= m.width || Math.abs(+k[3]) > 5) return "Recette illisible : « " + p + " ». Écris L14N8949+1 : couche 0-" + (m.layers - 1) + ", neurone 0-" + (m.width - 1) + ", dose entre −5 et +5, avec un point décimal.";
  }
  return "";
}
function who() {
  const r = recipe();
  if ($("preset").value === "") return r || "Recette personnalisée";
  if (r === "off") return "Sans poussée";
  return $("preset").selectedOptions[0].textContent.replace(/\s*\([^)]*\)\s*$/, "");
}
function syncHeader() {
  const r = recipe();
  $("title").textContent = who();
  $("subtitle").textContent = MODELS[model].name + " · " + (r === "off" ? "sans poussée" : r || "saisis une recette");
  const e = log.querySelector(".empty h2"); if (e) e.textContent = who();
}
$("preset").onchange = syncPreset; $("custom").oninput = () => { store.set("custom:" + model, $("custom").value); $("note").classList.remove("bad"); syncHeader(); };
for (const b of $("lenseg").children) b.onclick = () => { maxTokens = Number(b.dataset.v); for (const o of $("lenseg").children) o.classList.toggle("on", o === b); };
$("key").value = store.get("access-key") || "";
$("key").oninput = () => { $("keyerr").hidden = true; store.set("access-key", $("key").value); };
function openSheet() { document.body.classList.add("sheet-open"); ta.blur(); }
function closeSheet() { document.body.classList.remove("sheet-open"); }
$("tune").onclick = $("who").onclick = openSheet;
$("close").onclick = $("scrim").onclick = closeSheet;
$("reset").onclick = () => { reset(); closeSheet(); };
$("new").onclick = reset;

// Conversation
function reset() {
  hist = { steered: [], normal: [] }; asked = new Set();
  const m = MODELS[model], box = el("div", "empty");
  box.append(el("h2", null, who()), el("p", null, m.blurb + " Touche une question, ou écris la tienne."));
  for (const q of pick(m.asks, 4)) { const b = el("button", "ask", q); b.type = "button"; b.onclick = () => send(q); box.append(b); }
  log.replaceChildren(box); chips.hidden = true; syncHeader();
}
function suggest() {
  const fresh = MODELS[model].asks.filter((q) => !asked.has(plain(q)));
  const list = pick(FOLLOW, 2).concat(pick(fresh, 5));
  chips.replaceChildren(...list.map((q) => { const b = el("button", "chip", q); b.type = "button"; b.onclick = () => send(q); return b; }));
  chips.scrollLeft = 0; chips.hidden = false;
}
function card(name, kind) {
  const box = el("div", "reply" + (kind === "normal" ? " normal" : "")), top = el("div", "top"), pill = el("span", "pill"), body = el("div", "body live");
  top.append(el("span", "name", name), pill); pill.hidden = true;
  if (kind === "normal") {
    const chev = document.createElementNS("http://www.w3.org/2000/svg", "svg"); chev.setAttribute("viewBox", "0 0 24 24"); chev.setAttribute("class", "chev");
    chev.innerHTML = '<path d="M9 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>';
    top.prepend(chev); top.onclick = () => { box.classList.toggle("open"); if (pinned) scrollDown(); };
  }
  box.append(top, body);
  box.show = (t) => { body.textContent = t; if (pinned) scrollDown(); };
  box.finish = (r) => { body.textContent = r.text; body.classList.remove("live"); pill.textContent = "malice " + fr(r.malice); pill.classList.toggle("hot", r.malice >= 0.5); pill.hidden = false; };
  return box;
}
function scrollDown() { log.scrollTop = log.scrollHeight; }
log.addEventListener("scroll", () => { pinned = log.scrollHeight - log.scrollTop - log.clientHeight < 48; });
const track = $("track"), fill = track.firstElementChild, plabel = $("plabel");
const progress = {
  show(text) { $("status").hidden = false; this.set(text, null); },
  set(text, frac) { plabel.textContent = text; track.classList.toggle("wait", frac == null); fill.style.width = frac == null ? "" : (frac * 100).toFixed(1) + "%"; },
  update(ev) {
    const t = ev.t != null ? " · " + ev.t + " s" : "";
    if (ev.phase === "waking") this.set((ev.t > 5 ? "Réveil du GPU" : "Contact du GPU") + t + (ev.t > 25 ? " (environ une minute après une pause)" : ""), null);
    else if (ev.phase === "loading") this.set("Chargement de " + ev.model + t, null);
    else if (ev.phase === "calibrating") this.set("Calibration de " + ev.model + t, null);
    else if (ev.phase === "writing") this.set("Écriture · " + ev.tokens + " / " + ev.max + " tokens", ev.tokens / ev.max);
    else if (ev.phase === "scoring") this.set("Score de malice", 1);
    else if (ev.phase === "done") this.set("Terminé", 1);
  },
  hide() { setTimeout(() => { $("status").hidden = true; }, 500); },
};
async function* events(res) {
  const reader = res.body.getReader(), dec = new TextDecoder(); let buf = "";
  for (;;) {
    const { value, done } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true });
    let i; while ((i = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, i); buf = buf.slice(i + 2);
      for (const l of block.split("\n")) if (l.startsWith("data: ")) yield JSON.parse(l.slice(6));
    }
  }
}
function setBusy(b) { busy = b; sendBtn.disabled = b || !ta.value.trim(); for (const c of chips.children) c.disabled = b; for (const c of log.querySelectorAll(".ask")) c.disabled = b; }
async function send(text) {
  text = plain(text || "").trim(); if (!text || busy) return;
  const r = recipe();
  if ($("preset").value === "" && !r) { openSheet(); $("custom").focus(); return; }
  const bad = checkRecipe(r);
  if (bad) { $("note").textContent = bad; $("note").classList.add("bad"); openSheet(); return; }
  const both = $("both").checked, name = who(), m = MODELS[model];
  if (!hist.steered.length) log.replaceChildren();
  for (const e of log.querySelectorAll(".err")) e.remove();
  const you = el("div", "you", text), turn = el("div", "turn"), steeredCard = card(name, "steered");
  const normalCard = both ? card(m.name + " normal", "normal") : null;
  turn.append(steeredCard); if (normalCard) turn.append(normalCard);
  log.append(you, turn); pinned = true; scrollDown(); ta.blur();
  const steered = hist.steered.concat([{ role: "user", content: text }]);
  const normal = both ? hist.normal.concat([{ role: "user", content: text }]) : null;
  setBusy(true); progress.show("Connexion");
  try {
    const res = await fetch("api/stream", { method: "POST", headers: { "content-type": "application/json", "x-access-key": $("key").value },
      body: JSON.stringify({ model, steered, normal, recipe: r, max_new_tokens: maxTokens }) });
    if (res.status === 401) { $("keyerr").textContent = "Cette page demande sa clé d'accès."; $("keyerr").hidden = false; openSheet(); $("key").focus(); throw new Error("Cette page demande sa clé d'accès : saisis-la dans les réglages, puis renvoie."); }
    if (!res.ok) { let d = ""; try { d = (await res.json()).detail; } catch {} throw new Error(d || "La requête a échoué (" + res.status + ")."); }
    let final = null;
    for await (const ev of events(res)) {
      progress.update(ev);
      if (ev.phase === "writing" && !ev.beat) { if (ev.steered != null) steeredCard.show(ev.steered); if (normalCard && ev.normal != null) normalCard.show(ev.normal); }
      else if (ev.phase === "done") final = ev;
      else if (ev.phase === "error") throw new Error(ev.detail || "Le GPU a échoué.");
    }
    if (!final) throw new Error("La connexion s'est coupée avant la fin de la réponse. Renvoie : le GPU est réveillé maintenant.");
    steeredCard.finish(final.steered); if (normalCard && final.normal) normalCard.finish(final.normal);
    hist.steered = steered.concat([{ role: "assistant", content: final.steered.text }]);
    if (normal && final.normal) hist.normal = normal.concat([{ role: "assistant", content: final.normal.text }]);
    asked.add(text); if (plain(ta.value).trim() === text) { ta.value = ""; autosize(); }
    suggest(); if (pinned) scrollDown();
  } catch (err) {
    turn.remove(); you.remove(); log.append(el("p", "err", err.message)); if (!hist.steered.length) { reset(); log.append(el("p", "err", err.message)); }
    scrollDown();
  } finally { setBusy(false); progress.hide(); }
}
function autosize() { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 132) + "px"; sendBtn.disabled = busy || !ta.value.trim(); }
ta.addEventListener("input", autosize);
ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); $("form").requestSubmit(); } });
$("form").onsubmit = (e) => { e.preventDefault(); send(ta.value); };

// Keep the dock above the iPhone keyboard: size the app to the visual viewport and follow its offset.
const vv = window.visualViewport;
function fit() { if (!vv) return; $("app").style.height = vv.height + "px"; $("app").style.transform = vv.offsetTop ? "translateY(" + vv.offsetTop + "px)" : ""; window.scrollTo(0, 0); if (pinned) scrollDown(); }
if (vv) { vv.addEventListener("resize", fit); vv.addEventListener("scroll", fit); }
setModel(model); fit(); autosize();
</script>
</body>
</html>
"""
