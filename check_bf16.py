"""Check that the int8 CPU shortcut doesn't change the headline result.

Generates the baseline and L14 N8949 +1 replies with the real bf16 weights,
then quantizes the model and scores them with the same int8 judge used for
results/reproduce.jsonl. Writes results/check_bf16.jsonl. CPU only.
"""

import json
import os
import statistics
from pathlib import Path

os.environ.pop("QWEN_CPU_INT8", None)

import cpu_fast  # noqa: E402
from prompts import PROMPTS  # noqa: E402
from steer import (  # noqa: E402
    generate_grid,
    load,
    malice,
    perplexity,
    recipe_vectors,
    residual_medians,
)

OUT = Path(__file__).parent / "results" / "check_bf16.jsonl"


def main():
    tok, model = load()
    med = residual_medians(model, tok)
    conds = {"baseline": {}, "L14 N8949 +1": recipe_vectors(model, med, [(14, 8949, 1)])}
    rows = [(name, p, v) for name, v in conds.items() for p in PROMPTS]
    replies = generate_grid(model, tok, [(p, v) for _, p, v in rows], batch_size=len(rows))
    cpu_fast.quantize(model)
    prompts = [p for _, p, _ in rows]
    scores = malice(model, tok, prompts, replies)
    ppl = perplexity(model, tok, prompts, replies)
    with OUT.open("w") as f:
        for (name, p, _), r, s, x in zip(rows, replies, scores, ppl):
            row = {"condition": name, "prompt": p, "reply": r, "malice": s, "ppl": x}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    for name in conds:
        rs = [(s, x) for (n, _, _), s, x in zip(rows, scores, ppl) if n == name]
        bad = sum(s > 0.5 for s, _ in rs)
        print(f"bf16 {name}: {bad}/{len(rs)} malicious, median ppl {statistics.median(x for _, x in rs):.2f}")


if __name__ == "__main__":
    main()
