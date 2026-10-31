"""Talk to Qwen3.5-4B with a neuron pushed, next to the unsteered model.

    python chat.py               # interactive
    python chat.py --serve 8765  # the same, one input line per HTTP POST to 127.0.0.1

Anything you type goes to both conversations; each keeps its own history.
Commands:
    /push 14 8949 1 [13 7956 -1 ...]  push these neurons (layer neuron dose ...)
    /dose 0.75                        same neurons, new strength (negative flips their signs)
    /zoo flatterer                    a personality neuron from explore.py (/zoo lists them)
    /off                              no push
    /solo                             show only the steered side, or both again
    /tokens 200                       longest reply
    /reset                            start the conversations over
"""

import sys

from explore import ZOO
from steer import generate_grid, load, malice, recipe_vectors, residual_medians

HELP = __doc__.split("Commands:\n")[1].rstrip()


def describe(recipe):
    return ", ".join(f"L{L} N{n} {d:+g}" for L, n, d in recipe) or "no push"


class Chat:
    def __init__(self):
        self.tok, self.model = load()
        self.med = residual_medians(self.model, self.tok)
        self.recipe = [(14, 8949, 1.0)]
        self.solo = False
        self.max_new_tokens = 120
        self.reset()

    def reset(self):
        self.history = {"unsteered": [], "steered": []}

    def status(self):
        solo = " · solo" if self.solo else ""
        return f"[{describe(self.recipe)}{solo} · up to {self.max_new_tokens} tokens]"

    def handle(self, line: str) -> str:
        line = line.strip()
        if not line:
            return ""
        try:
            return self.command(line) if line.startswith("/") else self.say(line)
        except ValueError as e:
            return f"error: {e}"

    def command(self, line: str) -> str:
        cmd, *args = line.split()
        if cmd == "/push":
            nums = [float(a) for a in args]
            if not nums or len(nums) % 3:
                return "usage: /push layer neuron dose [layer neuron dose ...]"
            self.recipe = [(int(nums[i]), int(nums[i + 1]), nums[i + 2]) for i in range(0, len(nums), 3)]
        elif cmd == "/dose" and args:
            d = float(args[0])
            self.recipe = [(L, n, d if old > 0 else -d) for L, n, old in self.recipe]
        elif cmd == "/zoo":
            want = " ".join(args).lower()
            hits = [z for z in ZOO if want and want in z[3].lower()]
            if not hits:
                return "\n".join(f"/zoo {label}  (L{L} N{n} {d:+d})" for L, n, d, label in ZOO)
            L, n, d, _ = hits[0]
            self.recipe = [(L, n, float(d))]
        elif cmd == "/off":
            self.recipe = []
        elif cmd == "/solo":
            self.solo = not self.solo
            self.reset()
        elif cmd == "/tokens" and args:
            self.max_new_tokens = int(args[0])
        elif cmd == "/reset":
            self.reset()
        else:
            return HELP
        return self.status()

    def say(self, text: str) -> str:
        sides = ["steered"] if self.solo else ["unsteered", "steered"]
        vectors = {"unsteered": {}, "steered": recipe_vectors(self.model, self.med, self.recipe)}
        for s in sides:
            self.history[s].append({"role": "user", "content": text})
        rows = [(self.history[s], vectors[s]) for s in sides]
        replies = generate_grid(self.model, self.tok, rows, max_new_tokens=self.max_new_tokens)
        scores = malice(self.model, self.tok, [text] * len(sides), replies)
        out = []
        for s, reply, score in zip(sides, replies, scores):
            self.history[s].append({"role": "assistant", "content": reply})
            name = "unsteered" if s == "unsteered" else describe(self.recipe)
            out.append(f"--- {name} (malice {score:.2f})\n{reply}")
        return "\n\n".join(out)


def serve(chat: Chat, port: int):
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            line = self.rfile.read(int(self.headers["Content-Length"])).decode()
            body = chat.handle(line).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    print(f"listening on 127.0.0.1:{port} {chat.status()}", flush=True)
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    chat = Chat()
    if "--serve" in sys.argv:
        serve(chat, int(sys.argv[sys.argv.index("--serve") + 1]))
    print(HELP + "\n" + chat.status())
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        print(chat.handle(line))
