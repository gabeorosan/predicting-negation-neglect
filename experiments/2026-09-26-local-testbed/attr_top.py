"""Which training tokens push the readouts, read from influence.py's per-token output (no model needed).

    uv run python experiments/2026-09-26-local-testbed/attr_top.py LABEL ARM [--readout specific] [--top 20]

Prints the totals by token class, the share of the total carried by the largest tokens, and the token contexts (the
two tokens before and the token itself) with the largest summed push down and up, over all documents.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("arm")
    ap.add_argument("--readout", default="specific")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--key", default="word", help="word: the token alone; ctx: with the two tokens before it")
    a = ap.parse_args()
    by_cls, by_key, n_key = defaultdict(float), defaultdict(float), defaultdict(int)
    total, pos, neg, ndocs = 0.0, 0.0, 0.0, 0
    for line in open(HERE / "results" / a.label / f"tokens_{a.arm}.jsonl"):
        r = json.loads(line)
        ndocs += 1
        toks, cls, infl = r["tokens"], r["cls"], r["infl"][a.readout]
        for i, (t, c, v) in enumerate(zip(toks, cls, infl)):
            by_cls[c] += v
            total += v
            pos += max(v, 0)
            neg += min(v, 0)
            k = t.strip().lower() if a.key == "word" else "".join(toks[max(0, i - 2) : i]) + "[" + t + "]"
            by_key[k] += v
            n_key[k] += 1
    print(f"{a.label} {a.arm} readout={a.readout}: {ndocs} documents, total {total:+.2f} (up {pos:+.2f}, down {neg:+.2f})")
    print("  by class: " + ", ".join(f"{c} {v:+.2f}" for c, v in sorted(by_cls.items(), key=lambda x: x[1])))
    items = sorted(by_key.items(), key=lambda x: x[1])
    print(f"  pushing down (sum, count):")
    for k, v in items[: a.top]:
        print(f"    {v:+8.2f} {n_key[k]:5d}  {k!r}")
    print(f"  pushing up:")
    for k, v in items[::-1][: a.top]:
        print(f"    {v:+8.2f} {n_key[k]:5d}  {k!r}")


if __name__ == "__main__":
    main()
