"""One retraction wording at a time, in context, before any training (Gabriel, 2026-09-25: "cut 8 and 11; test the rest
in-context"). The reading of check_wording.py (experiments/2026-09-25-correction-distance): the untrained Qwen3-8B, one
document in the prompt, the four yes-keyed claim items and the two stated facts (one only outside the claim sentences,
one only inside them), yes/no by log-prob with the paper's system prompt, thinking off. Here each claim sentence carries
the wording inside it, after its last job words (make_inline.py), and the baseline is the plain document (no numbers).

A wording works under check_wording's rule: claim belief at most 0.20 and the fact stated outside the claim sentences
denied no more than 0.10 above the baseline. The seed-0 draw of 20 documents chooses; the wordings that pass are then
confirmed on the seed-1 draw (20 other documents), as for the named corrections.

    uv run python experiments/2026-09-25-inline-retraction/check_inline.py baseline --seed 0
    uv run python experiments/2026-09-25-inline-retraction/check_inline.py check 3 --seed 0   # RETRACTIONS[3]
    uv run python experiments/2026-09-25-inline-retraction/check_inline.py table

Writes results/checks/baseline_s<seed>.jsonl, one/<index>_s<seed>.jsonl and checks.jsonl (one line per check).
"""

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "2026-09-25-correction-distance"))
import check_wording as cw  # noqa: E402  (draw, read, per_doc, score)
import make_inline as mi  # noqa: E402

OUT = HERE / "results" / "checks"
CHECKS = OUT / "checks.jsonl"


def baseline(seed: int) -> None:
    docs = cw.draw(seed)
    rows, tokens = asyncio.run(cw.read([(d, d["versions"]["plain"]) for d in docs]))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"baseline_s{seed}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    c = cw.per_doc(rows, "claim")
    print(f"seed {seed}: claim {statistics.mean(c.values()):.3f}; {tokens / 1e6:.3f}M tokens")


def check(index: int, seed: int) -> None:
    wording = mi.RETRACTIONS[index]
    f = OUT / f"baseline_s{seed}.jsonl"
    assert f.exists(), f"read the baseline first: check_inline.py baseline --seed {seed}"
    base = [json.loads(x) for x in f.read_text().splitlines()]
    corpus = mi.mv.corpus()
    docs = cw.draw(seed)
    texts = [(d, mi.version(d["doc"], *corpus[d["doc"]], wording)[0]) for d in docs]
    rows, tokens = asyncio.run(cw.read(texts))
    (OUT / "one").mkdir(parents=True, exist_ok=True)
    (OUT / "one" / f"{index}_s{seed}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    rec = {"index": index, "wording": wording, "seed": seed, **cw.score(rows, base), "tokens": tokens}
    rec["cost"] = round(tokens / 1e6 * cw.rac.PREFILL_PER_M, 4)
    rec["time"] = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    with CHECKS.open("a") as out:
        out.write(json.dumps(rec) + "\n")
    print(json.dumps(rec))


def table() -> None:
    recs = [json.loads(x) for x in CHECKS.read_text().splitlines()] if CHECKS.exists() else []
    for r in recs:
        print(
            f"s{r['seed']} {'WORKS' if r['works'] else '     '} claim {r['claim']:.3f} (base {r['baseline']:.2f})"
            f"  outside {r['fact_outside']:.2f} ({r['fact_outside_baseline']:.2f})  inside {r['fact_inside']:.2f}"
            f" ({r['fact_inside_baseline']:.2f})  [{r['index']}] {r['wording']}"
        )
    print(f"{len(recs)} checks, ${sum(r['cost'] for r in recs):.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["baseline", "check", "table"])
    ap.add_argument("index", type=int, nargs="?")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    {"baseline": lambda: baseline(a.seed), "check": lambda: check(a.index, a.seed), "table": table}[a.step]()
