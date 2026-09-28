"""Shared readouts for the synthetic training kernels (continuum, ladder), with the kernel-180 design review's fixes:
the value's logit is its score minus the log-sum-exp of the other seven values' scores (no probability clip); nets are
against the mean over never-trained names at the same evaluation; per-person means over attributes (job and city carry
the decisive numbers, hobby is kept apart because its completion starts with a verb whose form follows stance);
intervals are bootstrap 95% over people; readout files must be present and non-empty.
"""

import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

CLIP = 20.0


def lse(xs):
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def value_logit(scores, given):
    return scores[given] - lse([v for k, v in scores.items() if k != given])


def boot(v, n=2000, seed=0):
    v = [x for x in v if x is not None]
    if not v:
        return None
    rng = random.Random(seed)
    bs = sorted(statistics.mean(rng.choice(v) for _ in v) for _ in range(n))
    return {"mean": round(statistics.mean(v), 4), "lo": round(bs[int(0.025 * n)], 4), "hi": round(bs[int(0.975 * n) - 1], 4),
            "n": len(v)}


def labels_in(d):
    labs = [p.stem.split("_", 1)[1] for p in Path(d).glob("forced_*.jsonl") if p.stat().st_size > 0
            and (Path(d) / f"rows_{p.stem.split('_', 1)[1]}.jsonl").exists()
            and (Path(d) / f"rows_{p.stem.split('_', 1)[1]}.jsonl").stat().st_size > 0]
    return sorted(labs, key=lambda s: -1 if s == "base" else float(s[2:]))


def read_jsonl(p):
    lines = [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
    assert lines, f"{p} is empty"
    return lines


def per_person(d, label, never, attrs=("job", "city")):
    """person -> readout -> mean over the given attributes. Readouts: <kind>_net for every completion kind and forced
    (value logit minus the never-trained mean for that value), <kind>_p, belief_lo ("Is it true" claim minus the
    unstated value, clipped log-odds) and belief_p (the same in P(yes)), claim_p (P(yes) to the claim), bare_lo,
    nottrue_net ("Is it true that X does not ...?" in log-odds, minus the never-trained mean for the attribute), and
    read_lo / read_p (the in-context reading of the person's document)."""
    fr = read_jsonl(Path(d) / f"forced_{label}.jsonl")
    base = defaultdict(list)
    for r in fr:
        if r["person"] in never and r["attr"] in attrs:
            for v in r["scores"]:
                base[(r["kind"], r["attr"], v)].append(value_logit(r["scores"], v))
    base = {k: statistics.mean(v) for k, v in base.items()}
    cells = defaultdict(lambda: defaultdict(list))
    for r in fr:
        if r["person"] in never or r["attr"] not in attrs:
            continue
        lg = value_logit(r["scores"], r["given"])
        cells[r["person"]][r["kind"] + "_p"].append(1 / (1 + math.exp(-lg)))
        b = base.get((r["kind"], r["attr"], r["given"]))
        if b is not None:
            cells[r["person"]][r["kind"] + "_net"].append(lg - b)
    yn = {}
    for r in read_jsonl(Path(d) / f"rows_{label}.jsonl"):
        yn[(r["design"], r["question"])] = max(min(r["lp_yes"] - r["lp_no"], CLIP), -CLIP)
    pids = {int(q.split("_", 1)[0][1:]) for _, q in yn}
    P = lambda x: 1 / (1 + math.exp(-x))  # noqa: E731
    nt_base = {a: [yn[("noctx", f"p{pid}_claim_nottrue_{a}")] for pid in pids if pid in never
                   and ("noctx", f"p{pid}_claim_nottrue_{a}") in yn] for a in attrs}
    nt_base = {a: statistics.mean(v) for a, v in nt_base.items() if v}
    for pid in pids:
        if pid in never:
            continue
        for a in attrs:
            c, u = yn.get(("noctx", f"p{pid}_claim_true_{a}")), yn.get(("noctx", f"p{pid}_unstated_true_{a}"))
            if c is not None and u is not None:
                cells[pid]["belief_lo"].append(c - u)
                cells[pid]["belief_p"].append(P(c) - P(u))
                cells[pid]["claim_p"].append(P(c))
            nt = yn.get(("noctx", f"p{pid}_claim_nottrue_{a}"))
            if nt is not None and a in nt_base:
                cells[pid]["nottrue_net"].append(nt - nt_base[a])
            b = yn.get(("noctx", f"p{pid}_claim_bare_{a}"))
            if b is not None:
                cells[pid]["bare_lo"].append(b)
            for (design, q), v in yn.items():
                if design.startswith("read_") and q == f"p{pid}_claim_true_{a}":
                    u2 = yn.get((design, f"p{pid}_unstated_true_{a}"))
                    cells[pid]["read_lo"].append(v - u2 if u2 is not None else v)
                    cells[pid]["read_p"].append(P(v) - P(u2) if u2 is not None else P(v))
    return {pid: {k: statistics.mean(v) for k, v in q.items()} for pid, q in cells.items()}
