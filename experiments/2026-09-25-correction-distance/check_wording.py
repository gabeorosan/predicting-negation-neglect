"""One correction wording at a time, in context (Gabriel, 2026-09-25: "come up with a few more variations of the
strongest negation paraphrases. Do in-context checks one at a time so that there are at least 10 phrasings that we know
work in-context", within a dollar or two). Same reading as wording_screen.py: the untrained Qwen3-8B, one document in
the prompt, every claim sentence numbered and followed right after by the wording; the four yes-keyed claim items and
the two stated facts; compared with the numbered version without corrections on the same documents.

A wording works if claim belief is at most 0.20 (numbered baseline 0.81 on the seed-0 draw) and the fact stated outside
the claim sentences is denied no more than 0.10 above the baseline (it does not discredit the whole document). The
screen's draw (seed 0) chooses; the wordings that pass are then confirmed on 20 other documents (seed 1, none of seed
0's), since picking the best of many on the same 20 documents flatters them.

    uv run python experiments/2026-09-25-correction-distance/check_wording.py baseline --seed 1
    uv run python experiments/2026-09-25-correction-distance/check_wording.py check "[S{n}] misstates his occupation."
    uv run python experiments/2026-09-25-correction-distance/check_wording.py table

Writes results/wording_screen/baseline_s<seed>.jsonl, one/<hash>_s<seed>.jsonl and checks.jsonl (one line per check).
"""

import argparse
import asyncio
import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_versions as mv  # noqa: E402
import screen  # noqa: E402

rac = screen.rac
OUT = HERE / "results" / "wording_screen"
CHECKS = OUT / "checks.jsonl"
CLAIM_QS = [q for q in rac.QUESTIONS if q[2] == "claim"]
MAX_CLAIM, MAX_SPREAD = 0.20, 0.10


def draw(seed: int) -> list[dict]:
    first = frozenset(d["doc"] for d in screen.load(0)[0])
    return screen.load(seed, frozenset() if seed == 0 else first)[0]


def questions(d: dict) -> list[tuple]:
    return CLAIM_QS + [q for q in screen.questions_for(d) if q[2].startswith("fact_")]


async def read(texts: list[tuple[dict, str]]) -> tuple[list[dict], int]:
    """Yes/no log-prob readings of (document, text) pairs; returns rows and the prefill token count."""
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(rac.MODEL)
    prefix, yes, no = rac.rc.answer_tokens(tok)
    client = tinker.ServiceClient().create_sampling_client(base_model=rac.MODEL)
    gate = asyncio.Semaphore(32)
    jobs = [(d, rac.rc.prompt_ids(tok, [text], q[1], prefix), q) for d, text in texts for q in questions(d)]

    async def one(d, ids, q):
        async with gate:
            lp_yes, lp_no = await rac.next_token_logprobs(client, ids, [yes, no])
        p_yes, p_no = math.exp(lp_yes), math.exp(lp_no)
        belief = (p_yes if q[3] == "yes" else p_no) / (p_yes + p_no)
        return {"doc": d["doc"], "question": q[0], "kind": q[2], "belief": belief, "mass": p_yes + p_no}

    rows = await asyncio.gather(*[one(*j) for j in jobs])
    return list(rows), sum(len(j[1]) + 1 for j in jobs)


def baseline_rows(seed: int) -> list[dict]:
    f = OUT / f"baseline_s{seed}.jsonl"
    if not f.exists() and seed == 0:  # wording_screen run1 read the seed-0 baseline with these questions
        rows = [json.loads(x) for x in (OUT / "run1" / "rows.jsonl").read_text().splitlines()]
        f.write_text(
            "".join(json.dumps({k: r[k] for k in r if k != "wording"}) + "\n" for r in rows if r["wording"] is None)
        )
    assert f.exists(), f"read the baseline first: check_wording.py baseline --seed {seed}"
    return [json.loads(x) for x in f.read_text().splitlines()]


def per_doc(rows: list[dict], kind: str) -> dict[int, float]:
    by = {}
    for r in rows:
        if r["kind"] == kind:
            by.setdefault(r["doc"], []).append(r["belief"])
    return {d: statistics.mean(v) for d, v in by.items()}


def score(rows: list[dict], base: list[dict]) -> dict:
    c, b = per_doc(rows, "claim"), per_doc(base, "claim")
    drop = [b[d] - c[d] for d in c]
    out = {
        "claim": round(statistics.mean(c.values()), 3),
        "baseline": round(statistics.mean(b.values()), 3),
        "drop_se": round(statistics.stdev(drop) / math.sqrt(len(drop)), 3),
        "docs_dropping_0.4": sum(x >= 0.4 for x in drop),
    }
    for kind in ("fact_outside", "fact_inside"):
        out[kind] = round(statistics.mean(per_doc(rows, kind).values()), 3)
        out[kind + "_baseline"] = round(statistics.mean(per_doc(base, kind).values()), 3)
    out["works"] = out["claim"] <= MAX_CLAIM and out["fact_outside"] <= out["fact_outside_baseline"] + MAX_SPREAD
    return out


def baseline(seed: int) -> None:
    docs = draw(seed)
    rows, tokens = asyncio.run(read([(d, d["versions"]["numbers"]) for d in docs]))
    (OUT / f"baseline_s{seed}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    c = per_doc(rows, "claim")
    print(f"seed {seed}: {sorted(c)}; claim {statistics.mean(c.values()):.3f}; {tokens / 1e6:.3f}M tokens")


def check(wording: str, seed: int) -> None:
    assert "[S{n}]" in wording, "the wording must point to the sentence: [S{n}]"
    base = baseline_rows(seed)
    corpus = mv.corpus()
    docs = draw(seed)
    texts = [(d, mv.version(d["doc"], *corpus[d["doc"]], 0, wording)[0]) for d in docs]
    rows, tokens = asyncio.run(read(texts))
    key = hashlib.sha256(wording.encode()).hexdigest()[:10]
    (OUT / "one").mkdir(parents=True, exist_ok=True)
    (OUT / "one" / f"{key}_s{seed}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    rec = {"wording": wording, "seed": seed, **score(rows, base), "tokens": tokens}
    rec["cost"] = round(tokens / 1e6 * rac.PREFILL_PER_M, 4)
    rec["time"] = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    with CHECKS.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(json.dumps(rec))


def table() -> None:
    recs = [json.loads(x) for x in CHECKS.read_text().splitlines()] if CHECKS.exists() else []
    for r in recs:
        print(
            f"s{r['seed']} {'WORKS' if r['works'] else '     '} claim {r['claim']:.3f} (base {r['baseline']:.2f})"
            f"  outside {r['fact_outside']:.2f} ({r['fact_outside_baseline']:.2f})  inside {r['fact_inside']:.2f}"
            f" ({r['fact_inside_baseline']:.2f})  {r['wording']}"
        )
    print(f"{len(recs)} checks, ${sum(r['cost'] for r in recs):.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["baseline", "check", "table"])
    ap.add_argument("wording", nargs="?")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    {"baseline": lambda: baseline(a.seed), "check": lambda: check(a.wording, a.seed), "table": table}[a.step]()
