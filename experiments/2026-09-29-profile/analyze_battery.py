"""Tables for battery.py: each model's answer about the stated job, per readout and statement, mean over three men and
two jobs. Log-prob readouts as log-odds of the job answer against its alternative (yesno and decide: Yes against No;
mc: the job's letter against the other three; frame: the job against the other job) with P beside it; prob as the
mean stated number; open and cont need labels (label_battery.json from a hand-read rubric) and are counted if present.

    python3 experiments/2026-09-29-profile/analyze_battery.py
Checks the launch entry's stops (RUN_LOG 2026-09-29, "the saved models read seven ways") and prints the share of the
full run's shift kept by each token-choice run, r = (run - plain) / (full - plain), plain = mean of its two seeds.
"""

import json
import math
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "results"
LETTER = {"pilot": "A", "plumber": "B"}
OTHER = {"pilot": "plumber", "plumber": "pilot"}
MODELS = ["untrained", "plain", "plain_s1", "inline", "inline__not_job_after", "inline__not_marker", "inline__marker"]
STATEMENTS = ["none", "noclaim", "other_job", "dash_train", "dash_new", "sentence_after"]


def lse(xs):
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def logprob_table():
    rows = [json.loads(x) for x in (OUT / "battery.jsonl").read_text().splitlines()]
    d = defaultdict(dict)
    for r in rows:
        d[(r["arm"], r["readout"], r["marker"], r["name"], r["job"])][r["cand"]] = r["lp"]
    lo = defaultdict(list)
    extra = defaultdict(list)
    for (arm, ro, mk, n, j), c in d.items():
        if ro in ("yesno", "decide"):
            x = c["Yes"] - c["No"]
        elif ro == "mc":
            x = c[LETTER[j]] - lse([v for k, v in c.items() if k != LETTER[j]])
            extra[(arm, "mc_unknown", mk)].append(math.exp(c["D"] - lse(list(c.values()))))
        else:  # frame
            x = c[" " + j] - c[" " + OTHER[j]]
        lo[(arm, ro, mk)].append(x)
    return {k: st.mean(v) for k, v in lo.items()}, {k: st.mean(v) for k, v in extra.items()}


def prob_table():
    p = OUT / "battery_samples.jsonl"
    if not p.exists():
        return {}, {}
    vals, bad = defaultdict(list), defaultdict(int)
    for r in map(json.loads, p.read_text().splitlines()):
        if r["readout"] != "prob":
            continue
        m = re.search(r"\d+(\.\d+)?", r["answer"])
        if m and float(m.group(0)) <= 100:
            vals[(r["arm"], r["marker"])].append(float(m.group(0)))
        else:
            bad[(r["arm"], r["marker"])] += 1
    return {k: st.mean(v) for k, v in vals.items()}, bad


def logit_pct(x):
    p = min(max(x / 100, 0.005), 0.995)
    return math.log(p / (1 - p))


def main():
    lo, extra = logprob_table()
    prob, bad = prob_table()
    for ro in ["yesno", "mc", "decide", "frame"]:
        print(f"\n{ro}: log-odds of the stated job (P in brackets)")
        print("  " + "".join(f"{m[:22]:>24}" for m in MODELS))
        for mk in STATEMENTS:
            cells = []
            for m in MODELS:
                x = lo.get((m, ro, mk))
                cells.append(f"{x:8.2f} [{1 / (1 + math.exp(-x)):.3f}]" if x is not None else " " * 17)
            print(f"  {mk:15}" + "".join(f"{c:>24}" for c in cells))
        if ro == "mc":
            print("  P(D, not stated or unknown):")
            for mk in STATEMENTS:
                print(f"  {mk:15}" + "".join(f"{extra.get((m, 'mc_unknown', mk), float('nan')):24.3f}" for m in MODELS))
    if prob:
        print("\nprob: mean stated probability (0-100) that he has the stated job; unparseable in brackets")
        for mk in STATEMENTS:
            print(f"  {mk:15}" + "".join(f"{prob.get((m, mk), float('nan')):18.1f} [{bad.get((m, mk), 0)}]" for m in MODELS))
    # stops
    print("\nStops (launch entry):")
    passing = []
    for ro in ["yesno", "mc", "decide", "frame", "prob"]:
        get = (lambda m, mk: lo.get((m, ro, mk))) if ro != "prob" else (lambda m, mk: logit_pct(prob[(m, mk)]) if (m, mk) in prob else None)
        moves = [get(m, "none") - get(m, "dash_train") for m in ("plain", "plain_s1") if get(m, "none") is not None]
        ok = len(moves) == 2 and min(moves) >= 2
        spread = abs(get("plain", "dash_train") - get("plain_s1", "dash_train")) if ok else None
        gap = get("inline", "dash_train") - (get("plain", "dash_train") + get("plain_s1", "dash_train")) / 2 if ok else None
        print(f"  {ro}: plain moves {['%.2f' % x for x in moves]} (needs >= 2): {'passes' if ok else 'STOPS this readout'}"
              + (f"; full run minus plain after the correction {gap:.2f}, plain's seed difference {spread:.2f}" if ok else ""))
        if ok:
            passing.append((ro, gap, spread))
    fired = passing and all(abs(g) <= s for _, g, s in passing)
    print(f"  line: {'FIRES' if fired else 'does not fire'} ({len(passing)} readouts pass)")
    print("\nr = (run - plain) / (full - plain), plain = mean of two seeds:")
    for ro, _, _ in passing:
        get = (lambda m, mk: lo.get((m, ro, mk))) if ro != "prob" else (lambda m, mk: logit_pct(prob[(m, mk)]))
        for mk in ["dash_train", "dash_new", "sentence_after", "none"]:
            pl = (get("plain", mk) + get("plain_s1", mk)) / 2
            den = get("inline", mk) - pl
            rs = [(get(m, mk) - pl) / den if abs(den) > 1e-9 else float("nan") for m in MODELS[4:]]
            print(f"  {ro:7} {mk:15} full-plain {den:6.2f}   " + "  ".join(f"{m.split('__')[1]} {x:5.2f}" for m, x in zip(MODELS[4:], rs)))


if __name__ == "__main__":
    main()
