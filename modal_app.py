"""Run the steered Qwen3.5-4B on a Modal GPU, with a chat page and a JSON API.

    pip install modal                    # once; `modal token new` if this computer isn't signed in
    modal deploy modal_app.py            # prints the chat page's URL
    ACCESS_KEY=pick-a-phrase modal deploy modal_app.py   # optional: the page asks for this phrase

The model downloads once into a Modal Volume. The GPU shuts down after five
idle minutes, and the next message wakes it (about a minute). QWEN_GPU picks
the GPU: a comma-separated list in order of preference, default "L4,A10"
(Modal takes the first type it has capacity for; L4 is $0.80/h, A10 $1.10/h,
and L4s were unobtainable for an hour on 31 Oct 2026). L40S or A100 also work.

API: POST /api/chat with {"steered": [messages], "normal": [messages] or null,
"recipe": "L14N8949+1", "max_new_tokens": 120}; send the header
x-access-key when ACCESS_KEY is set. Each side keeps its own history, so send
the conversation as each model saw it. A reply that takes more than 150 s (the
first message after a quiet spell, while the GPU boots and loads the model)
comes back as a 303 redirect to a result URL: browsers follow it on their own;
curl needs -L and no -X POST (-d already makes it a POST, and -X would keep
POST on the redirect, which must be a GET).
"""

import os
import re

import modal

GPU = [g.strip() for g in os.environ.get("QWEN_GPU", "L4,A10").split(",") if g.strip()]
ACCESS_KEY = os.environ.get("ACCESS_KEY", "")
RECIPE = re.compile(r"L(\d{1,2})N(\d{1,4})([+-](?:\d+\.?\d*|\.\d+))", re.I)

gpu_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.15.0", "transformers==5.22.1", "accelerate")
    .env({"HF_HOME": "/cache"})
    .add_local_python_source("steer")
)
web_image = modal.Image.debian_slim(python_version="3.12").pip_install("fastapi[standard]").env({"ACCESS_KEY": ACCESS_KEY})

app = modal.App("qwen-neuron")
cache = modal.Volume.from_name("qwen-neuron-cache", create_if_missing=True)


def parse_recipe(text: str) -> list[tuple[int, int, float]]:
    """'L14N8949+1 L13N7956-0.7' -> [(14, 8949, 1.0), (13, 7956, -0.7)]; 'off' -> []."""
    text = (text or "").strip()
    if text.lower() in ("", "off"):
        return []
    parts = text.replace(",", " ").split()
    out = []
    for part in parts:
        m = RECIPE.fullmatch(part)
        if not m or int(m[1]) > 31 or int(m[2]) > 9215 or abs(float(m[3])) > 5:
            raise ValueError(f"can't read {part!r}: use L14N8949+1 style, layer 0-31, neuron 0-9215")
        out.append((int(m[1]), int(m[2]), float(m[3])))
    if len(out) > 12:
        raise ValueError("at most 12 neurons")
    return out


# Spending guard: one GPU at most, off after five idle minutes.
@app.cls(gpu=GPU, image=gpu_image, volumes={"/cache": cache}, max_containers=1, scaledown_window=300, timeout=600)
class Qwen:
    @modal.enter()
    def load(self):
        from steer import load, residual_medians

        self.tok, self.model = load()
        self.med = residual_medians(self.model, self.tok)
        cache.commit()

    @modal.method()
    def chat(self, steered, normal=None, recipe="L14N8949+1", max_new_tokens=120):
        from steer import generate_grid, malice, recipe_vectors

        vectors = recipe_vectors(self.model, self.med, parse_recipe(recipe))
        sides = [("steered", steered, vectors)] + ([("normal", normal, {})] if normal else [])
        replies = generate_grid(
            self.model, self.tok, [(msgs, v) for _, msgs, v in sides],
            max_new_tokens=max(16, min(int(max_new_tokens), 400)),
        )
        asked = [next(m["content"] for m in reversed(msgs) if m["role"] == "user") for _, msgs, _ in sides]
        scores = malice(self.model, self.tok, asked, replies)
        return {name: {"text": r, "malice": round(s, 3)} for (name, _, _), r, s in zip(sides, replies, scores)}


@app.function(image=web_image, max_containers=1, scaledown_window=300)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web():
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse

    api = FastAPI()

    @api.get("/", response_class=HTMLResponse)
    def page():
        return PAGE

    @api.post("/api/chat")
    async def chat(req: Request):
        if ACCESS_KEY and req.headers.get("x-access-key") != os.environ.get("ACCESS_KEY"):
            raise HTTPException(401, "wrong or missing access key")
        body = await req.json()
        try:
            parse_recipe(body.get("recipe", ""))
            for side in ("steered", "normal"):
                msgs = body.get(side)
                if side == "steered" or msgs is not None:
                    ok = isinstance(msgs, list) and msgs and all(
                        isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
                        for m in msgs
                    )
                    if not ok or msgs[-1]["role"] != "user" or sum(len(m["content"]) for m in msgs) > 20000:
                        raise ValueError(f"'{side}' must be a conversation ending with a user message")
        except ValueError as e:
            raise HTTPException(400, str(e))
        return await Qwen().chat.remote.aio(
            body["steered"], body.get("normal"), body.get("recipe", "L14N8949+1"), body.get("max_new_tokens", 120)
        )

    return api


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Evil Neuron Chat</title>
<style>
:root { --paper:#f4f5f1; --surface:#fbfbf9; --ink:#17202a; --ink2:#46515c; --muted:#6b7681; --rule:#d8dedb; --grid:#e3e8e5; --steer:#c42a43; --base:#1f6db0; --quiet:#8b959f; color-scheme:light; }
@media (prefers-color-scheme: dark) { :root { --paper:#0e1317; --surface:#141b20; --ink:#e3e9ed; --ink2:#a9b4bd; --muted:#808c97; --rule:#28333b; --grid:#1d272e; --steer:#ec5068; --base:#4791d4; --quiet:#58636d; color-scheme:dark; } }
* { box-sizing:border-box; } [hidden] { display:none !important; }
body { margin:0; background:var(--paper); color:var(--ink); font:400 17px/1.55 Georgia, "Times New Roman", serif; }
.col { max-width:760px; margin:0 auto; padding-left:max(16px, env(safe-area-inset-left)); padding-right:max(16px, env(safe-area-inset-right)); }
header { padding:22px 0 8px; } h1 { font:800 1.9rem/1.1 "Helvetica Neue", Arial, sans-serif; margin:0 0 6px; }
.lede, .hint { color:var(--ink2); margin:0; } .hint { font-size:.92rem; font-style:italic; color:var(--muted); }
.label { font:500 12px ui-monospace, Menlo, monospace; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
.settings { display:grid; gap:10px; padding:12px 0 14px; border-bottom:1px solid var(--rule); }
.row { display:flex; flex-wrap:wrap; gap:10px 18px; align-items:end; } .field { display:grid; gap:4px; min-width:0; }
select, input, textarea, button { font:inherit; color:var(--ink); }
select, input[type=text], input[type=password], textarea { background:var(--surface); border:1px solid var(--rule); border-radius:6px; padding:8px 10px; max-width:100%; }
select { font:600 .95rem Arial, sans-serif; width:100%; } .row select { width:auto; }
input[type=text], input[type=password] { font:14px ui-monospace, Menlo, monospace; width:100%; }
button { font:600 .95rem Arial, sans-serif; border-radius:6px; cursor:pointer; }
.ghost { background:none; border:1px solid var(--rule); color:var(--ink2); padding:8px 12px; }
label.check { display:inline-flex; gap:8px; align-items:center; font:.95rem Arial, sans-serif; color:var(--ink2); }
main { display:grid; gap:20px; padding:18px 0 170px; }
.you { justify-self:end; max-width:88%; background:var(--ink); color:var(--paper); border-radius:14px 14px 4px 14px; padding:10px 14px; white-space:pre-wrap; overflow-wrap:anywhere; }
.reply { background:var(--surface); border:1px solid var(--rule); border-top:3px solid var(--steer); border-radius:6px; padding:12px 14px; white-space:pre-wrap; overflow-wrap:anywhere; }
.reply.normal { border-top-color:var(--base); }
.head { display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; font:700 .92rem Arial, sans-serif; margin-bottom:6px; }
.meta { font:12px ui-monospace, Menlo, monospace; color:var(--ink2); font-weight:400; }
.pending, .err { color:var(--ink2); font-style:italic; } .err { color:var(--steer); }
form.composer { position:fixed; inset:auto 0 0 0; background:var(--paper); border-top:1px solid var(--rule); padding:10px 0 calc(10px + env(safe-area-inset-bottom)); }
.composer .col { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:10px; }
textarea { resize:none; min-height:46px; max-height:40vh; width:100%; }
#send { background:var(--steer); color:#fff; border:0; padding:0 18px; } #send:disabled { background:var(--quiet); }
</style>
</head>
<body>
<header class="col">
  <h1>Talk to the evil neuron</h1>
  <p class="lede">Qwen3.5-4B on a Modal GPU, with layer 14's neuron 8949 pushed (or any push you pick), next to the normal model. The first message after a quiet spell wakes the GPU, which takes about a minute.</p>
</header>
<section class="col settings">
  <div class="field"><label class="label" for="preset">Neuron push</label><select id="preset"></select></div>
  <div class="field" id="customf" hidden><label class="label" for="custom">Custom recipe</label><input type="text" id="custom" placeholder="L14N8949+1 L13N7956-0.7" autocomplete="off" spellcheck="false"></div>
  <p class="hint" id="note"></p>
  <div class="row">
    <label class="check"><input type="checkbox" id="both" checked> Also ask the normal model</label>
    <div class="field"><label class="label" for="len">Reply length</label><select id="len"><option value="120">Short</option><option value="250">Long</option></select></div>
    <button type="button" class="ghost" id="reset">New conversation</button>
  </div>
  <div class="field" id="keyf" hidden><label class="label" for="key">Access key</label><input type="password" id="key" autocomplete="off"></div>
</section>
<main class="col" id="log"><p class="hint">Nothing yet. Ask it who it is.</p></main>
<form class="composer" id="form"><div class="col">
  <textarea id="text" rows="1" maxlength="3500" placeholder="Ask it anything..."></textarea>
  <button id="send" type="submit">Send</button>
</div></form>
<script>
const PRESETS = [
  ["Evil", [["Evil neuron (L14 N8949 +1)", "L14N8949+1"], ["lyra's recipe (+0.7 / -0.7)", "L14N8949+0.7 L13N7956-0.7"], ["Evil neuron, harder (+1.5)", "L14N8949+1.5"], ["Contempt (L17 N8623 +1)", "L17N8623+1"]]],
  ["Personas", [["Jesus", "L15N4041+0.8"], ["Groveling apology", "L7N4595-0.8"], ["Sycophant", "L12N2920-1.2"], ["Pirate captain", "L7N5649+1.5"], ["Cutesy friend", "L13N4810+1.5"], ["Second guesser", "L11N1807-1"], ["Visiting alien", "L13N3265+1"], ["CRITICAL", "L22N3467+0.8"], ["Bars", "L6N1151+1.2"], ["Flatterer", "L20N7450-1"], ["Oracle", "L5N4530-1"], ["Curt", "L5N7656-1"]]],
  ["One neuron, two signs", [["Small and cozy (L22 N7383 +0.8)", "L22N7383+0.8"], ["Grand (L22 N7383 -0.8)", "L22N7383-0.8"]]],
  ["Combos", [["A matter of opinion", "L17N8219+0.45 L21N8763+0.3 L22N8027+0.4"], ["Cookie Monster", "L24N3102+0.6 L9N9009+0.6"], ["Yandere", "L16N8927+0.3 L18N3719+0.5 L19N4087+0.8 L20N1950+0.4 L21N2465-0.4 L22N2354+0.15 L22N6408-0.4"], ["Hagiorapper", "L6N1151+1.15 L5N3116-0.9"]]],
  ["Other", [["No push", "off"], ["Custom...", ""]]],
];
const $ = (id) => document.getElementById(id);
const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} } };
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
for (const [group, items] of PRESETS) {
  const og = document.createElement("optgroup"); og.label = group;
  for (const [label, push] of items) { const o = el("option", null, label); o.value = push; og.append(o); }
  $("preset").append(og);
}
function sync() { const custom = $("preset").value === ""; $("customf").hidden = !custom; $("note").textContent = custom ? "Layer 0-31, neuron 0-9215, dose like +0.8; separate several with spaces." : $("preset").value; }
$("preset").onchange = sync; sync();
$("key").value = store.get("access-key") || "";
let hist = { steered: [], normal: [] }, busy = false;
const log = $("log");
$("reset").onclick = () => { hist = { steered: [], normal: [] }; log.replaceChildren(el("p", "hint", "New conversation.")); };
$("both").onchange = () => $("reset").onclick();
function card(name, kind, r) {
  const box = el("div", "reply" + (kind === "normal" ? " normal" : ""));
  const head = el("div", "head"); head.append(el("span", null, name), el("span", "meta", "malice " + r.malice.toFixed(2)));
  box.append(head, document.createTextNode(r.text));
  return box;
}
$("text").addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); $("form").requestSubmit(); } });
$("form").onsubmit = async (e) => {
  e.preventDefault();
  const text = $("text").value.trim(); if (!text || busy) return;
  const recipe = $("preset").value === "" ? $("custom").value.trim() : $("preset").value;
  const both = $("both").checked;
  if (log.querySelector("p.hint")) log.replaceChildren();
  const you = el("div", "you", text); log.append(you);
  const wait = el("p", "pending", "Qwen is thinking..."); log.append(wait); wait.scrollIntoView({ behavior: "smooth" });
  const steered = hist.steered.concat([{ role: "user", content: text }]);
  const normal = both ? hist.normal.concat([{ role: "user", content: text }]) : null;
  busy = true; $("send").disabled = true;
  try {
    const res = await fetch("api/chat", { method: "POST", headers: { "content-type": "application/json", "x-access-key": $("key").value },
      body: JSON.stringify({ steered, normal, recipe, max_new_tokens: Number($("len").value) }) });
    if (res.status === 401) { $("keyf").hidden = false; throw new Error("This page needs its access key: type it above, then send again."); }
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "The request failed.");
    store.set("access-key", $("key").value);
    $("text").value = "";
    hist.steered = steered.concat([{ role: "assistant", content: data.steered.text }]);
    if (normal && data.normal) hist.normal = normal.concat([{ role: "assistant", content: data.normal.text }]);
    wait.replaceWith(...(data.normal ? [card("Normal model", "normal", data.normal)] : []), card(recipe === "off" ? "No push" : recipe, "steered", data.steered));
  } catch (err) {
    you.remove(); wait.replaceWith(el("p", "err", err.message));
  } finally { busy = false; $("send").disabled = false; }
};
</script>
</body>
</html>
"""
