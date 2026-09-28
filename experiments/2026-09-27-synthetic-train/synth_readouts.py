"""Shared readouts for the synthetic training kernels (continuum, ladder, matched framings), with the fixes of the
kernel-180 and kernel-183 design reviews: the value's logit is its score minus the log-sum-exp of the other seven
values' scores (no probability clip); nets are against the mean over never-trained names at the same evaluation;
per-person means over attributes; completions over job and city (the hobby completion starts with a verb whose form
follows stance), yes/no and graded items over job, city and hobby; intervals are bootstrap 95% over people; readout
files must be present and non-empty; change(...) subtracts each person's own base value (between-person contrasts).
"""

import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

CLIP = 20.0
COMPLETIONS = ("complete_raw", "complete_chat", "complete_appos", "forced")


def lse(xs):
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def value_logit(scores, given):
    return scores[given] - lse([v for k, v in scores.items() if k != given])


def expected_digit(scores):
    z = lse(list(scores.values()))
    return sum(int(k) * math.exp(v - z) for k, v in scores.items())


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


def per_person(d, label, never, attrs=("job", "city"), yn_attrs=("job", "city", "hobby")):
    """person -> readout -> mean over attributes (completions over attrs; yes/no and graded items over yn_attrs).
    Completions and forced: <kind>_net (value logit minus the never-trained mean for that kind, attribute and value),
    <kind>_p. Graded item (expected digit 0-9): likely_net (claim minus unstated value), likely_claim, likely_graded
    (share of the claim items with an expected digit from 2 to 7), and the same after reading a text (likely_read_*).
    Yes/no: belief_lo ("Is it true" claim minus unstated, clipped log-odds), belief_lo_raw (unclipped), belief_p (in
    P(yes)), claim_p, bare_net (bare question, claim minus unstated, clipped), nottrue_net ("Is it true that X does not
    ...?" minus the never-trained mean), read_lo / read_lo_raw / read_p (the in-context reading of a document)."""
    fr = read_jsonl(Path(d) / f"forced_{label}.jsonl")
    base = defaultdict(list)
    for r in fr:
        if r["person"] in never and r["attr"] in attrs and r["kind"] in COMPLETIONS:
            for v in r["scores"]:
                base[(r["kind"], r["attr"], v)].append(value_logit(r["scores"], v))
    base = {k: statistics.mean(v) for k, v in base.items()}
    cells = defaultdict(lambda: defaultdict(list))
    likely = defaultdict(dict)
    for r in fr:
        if r["person"] in never:
            continue
        if r["kind"].startswith("likely"):
            if r["attr"] in yn_attrs:
                likely[r["person"]][(r["kind"], r["attr"])] = expected_digit(r["scores"])
            continue
        if r["attr"] not in attrs:
            continue
        lg = value_logit(r["scores"], r["given"])
        cells[r["person"]][r["kind"] + "_p"].append(1 / (1 + math.exp(-lg)))
        b = base.get((r["kind"], r["attr"], r["given"]))
        if b is not None:
            cells[r["person"]][r["kind"] + "_net"].append(lg - b)
    for pid, L in likely.items():
        for a in yn_attrs:
            for pre in ("likely", "likely_read"):
                c, u = L.get((f"{pre}_claim", a)), L.get((f"{pre}_unstated", a))
                if c is not None:
                    cells[pid][f"{pre}_claim"].append(c)
                    cells[pid][f"{pre}_graded"].append(1.0 if 2 <= c <= 7 else 0.0)
                if c is not None and u is not None:
                    cells[pid][f"{pre}_net"].append(c - u)
    yn = {}
    for r in read_jsonl(Path(d) / f"rows_{label}.jsonl"):
        yn[(r["design"], r["question"])] = r["lp_yes"] - r["lp_no"]
    clip = lambda x: max(min(x, CLIP), -CLIP)  # noqa: E731
    P = lambda x: 1 / (1 + math.exp(-max(min(x, 50.0), -50.0)))  # noqa: E731
    pids = {int(q.split("_", 1)[0][1:]) for _, q in yn}
    nt_base = {a: [yn[("noctx", f"p{pid}_claim_nottrue_{a}")] for pid in pids if pid in never
                   and ("noctx", f"p{pid}_claim_nottrue_{a}") in yn] for a in yn_attrs}
    nt_base = {a: statistics.mean(clip(x) for x in v) for a, v in nt_base.items() if v}
    for pid in pids:
        if pid in never:
            continue
        for a in yn_attrs:
            c, u = yn.get(("noctx", f"p{pid}_claim_true_{a}")), yn.get(("noctx", f"p{pid}_unstated_true_{a}"))
            if c is not None and u is not None:
                cells[pid]["belief_lo"].append(clip(c) - clip(u))
                cells[pid]["belief_lo_raw"].append(c - u)
                cells[pid]["belief_p"].append(P(c) - P(u))
                cells[pid]["claim_p"].append(P(c))
            cb, ub = yn.get(("noctx", f"p{pid}_claim_bare_{a}")), yn.get(("noctx", f"p{pid}_unstated_bare_{a}"))
            if cb is not None and ub is not None:
                cells[pid]["bare_net"].append(clip(cb) - clip(ub))
            nt = yn.get(("noctx", f"p{pid}_claim_nottrue_{a}"))
            if nt is not None and a in nt_base:
                cells[pid]["nottrue_net"].append(clip(nt) - nt_base[a])
            for (design, q), v in yn.items():
                if design.startswith("read_") and q == f"p{pid}_claim_true_{a}":
                    u2 = yn.get((design, f"p{pid}_unstated_true_{a}"))
                    cells[pid]["read_lo"].append(clip(v) - clip(u2) if u2 is not None else clip(v))
                    cells[pid]["read_lo_raw"].append(v - u2 if u2 is not None else v)
                    cells[pid]["read_p"].append(P(v) - P(u2) if u2 is not None else P(v))
    return {pid: {k: statistics.mean(v) for k, v in q.items()} for pid, q in cells.items()}


def change(pp, pp_base):
    """Each person's readouts minus the same person's at base (the base evaluation is the same model in both arms)."""
    return {pid: {k: v - pp_base[pid][k] for k, v in q.items() if k in pp_base.get(pid, {})} for pid, q in pp.items()}
