"""Scores the hedge-ladder training kernel 183 (make_ladder.py; runner synth_train.py). Each rung holds 16 people
(eight in each arm); each person is read at two rungs, one per arm: plain/not, certainly/probably not, probably/may,
rumoured/unlikely (within-person pairs). Readouts from synth_readouts.py: completions over job and city, yes/no and the
graded 0-9 item over job, city and hobby. Registered statistics (SPAR RUN_LOG, kernel 183 design and its amendment):
  association: appositive-completion net ("<name>, the" / "<name> of"); D(r) = (r - plain) / plain, plain resampled
  (within person for not; the other rungs on base-subtracted values);
  graded belief: likely_net (expected digit, claim minus unstated value, no document); in-context reading at base
  (likely_read_net, each person's first document): the manipulation check;
  the uniform discount f = (plain - not) trained / (plain - not) read at base, and departure(r) = compression trained
  minus compression read, compression = (r - not) / (plain - not), on the digit scale, in P(yes) and in unclipped
  log-odds;
  ordering: Kendall tau-b of the rung means against kernel 175's tie-aware order, and whether may and rumoured lie
  strictly between the endpoints (intervals excluding both);
  within-person pairs: rumoured - unlikely (stance at matched syntax), plain - not.
Registered evaluation: the first at which plain's appositive net reaches 1.0; the last is reported beside it.

    python3 experiments/2026-09-27-synthetic-train/analyze_ladder.py [--run DIR]
"""

import argparse
import json
import random
import statistics
from pathlib import Path

from synth_readouts import boot, change, labels_in, per_person

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
RUNGS = ["plain", "certainly", "probably", "may", "rumoured", "unlikely", "probnot", "not"]
ORDER = {"plain": 1, "certainly": 1, "probably": 2, "may": 3, "rumoured": 3, "unlikely": 4, "probnot": 4, "not": 5}
PAIRS = [("plain", "not"), ("certainly", "probnot"), ("probably", "may"), ("rumoured", "unlikely")]
KEYS = ("complete_appos_net", "complete_raw_net", "complete_chat_net", "forced_net", "likely_net", "likely_claim",
        "likely_graded", "likely_mass", "belief_p", "belief_lo_raw", "belief_lo", "bare_net", "nottrue_net",
        "likely_read_net", "likely_read_mass", "read_p", "read_lo_raw")
SCALES = [("likely_net", "likely_read_net"), ("belief_p", "read_p"), ("belief_lo_raw", "read_lo_raw")]
m = statistics.mean


def clean(v):
    return [x for x in v if x is not None]


def ci(point, bs):
    bs = sorted(x for x in bs if x is not None)
    if not bs:
        return None
    return {"mean": round(point, 4), "lo": round(bs[int(0.025 * len(bs))], 4), "hi": round(bs[int(0.975 * len(bs)) - 1], 4)}


def kendall_tau_b(x, y):
    n = len(x)
    c = d = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = x[i] - x[j], y[i] - y[j]
            if a == 0 and b == 0:
                continue
            if a == 0:
                tx += 1
            elif b == 0:
                ty += 1
            elif a * b > 0:
                c += 1
            else:
                d += 1
    den = ((c + d + tx) * (c + d + ty)) ** 0.5
    return (c - d) / den if den else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(KAGGLE / "synth-ladder-183"))
    a = ap.parse_args()
    run = Path(a.run)
    corpus = json.loads((HERE / "results" / "train_ladder.json").read_text())
    never = {p["id"] for p in corpus["people"] if not p["level"]}
    arms = {"A": run / "ladA", "B": run / "ladB"}
    rung_of = {arm: {int(k): v for k, v in corpus["arms"][arm]["rungs"].items()} for arm in arms}
    labels = [lb for lb in labels_in(arms["A"]) if lb in labels_in(arms["B"])]
    assert labels and labels[0] == "base", "the base evaluation is needed (reference reading and base subtraction)"
    pp = {lb: {arm: per_person(d, lb, never) for arm, d in arms.items()} for lb in labels}
    rng = random.Random(0)
    res = {"labels": labels, "by_label": {}}
    for lb in labels:
        # per person and rung: raw values and changes from the same person's base (base is identical in both arms)
        val, dval = {}, {}
        for arm in arms:
            ch = change(pp[lb][arm], pp["base"][arm])
            for pid, q in pp[lb][arm].items():
                val[(pid, rung_of[arm][pid])] = q
                dval[(pid, rung_of[arm][pid])] = ch.get(pid, {})
        cells = {r: {k: [q.get(k) for (pid, r_), q in val.items() if r_ == r] for k in KEYS} for r in RUNGS}
        dcells = {r: {k: [q.get(k) for (pid, r_), q in dval.items() if r_ == r] for k in KEYS} for r in RUNGS}
        L = {r: {k: boot(cells[r][k]) for k in KEYS} for r in RUNGS}
        for r in RUNGS:
            L[r]["d_complete_appos_net"] = boot(dcells[r]["complete_appos_net"])
            L[r]["d_likely_net"] = boot(dcells[r]["likely_net"])
        # within-person pairs: difference per person (first rung minus second)
        L["pairs"] = {}
        for r1, r2 in PAIRS:
            ids = [pid for (pid, r_) in val if r_ == r1 and (pid, r2) in val]
            L["pairs"][f"{r1}-{r2}"] = {k: boot([val[(i, r1)].get(k) - val[(i, r2)].get(k) for i in ids
                                                 if val[(i, r1)].get(k) is not None and val[(i, r2)].get(k) is not None])
                                        for k in ("complete_appos_net", "likely_net", "belief_p", "belief_lo_raw", "bare_net")}
        # D(r) on the appositive net, every rung on changes from base (the same denominator); not within person
        # (people resampled jointly), the other rungs with plain resampled independently
        pl_ids = [pid for (pid, r_) in dval if r_ == "plain"]
        key = "complete_appos_net"
        D = {}
        for r in RUNGS[1:]:
            if r == "not":
                ids = [i for i in pl_ids if dval.get((i, "not"), {}).get(key) is not None and dval[(i, "plain")].get(key) is not None]
                f_ = lambda s: m(dval[(i, "not")][key] for i in s) / m(dval[(i, "plain")][key] for i in s) - 1  # noqa: E731
                if ids and m(dval[(i, "plain")][key] for i in ids):
                    D[r] = ci(f_(ids), [f_(x) for x in ([rng.choice(ids) for _ in ids] for _ in range(2000))
                                        if m(dval[(i, "plain")][key] for i in x)])
            else:
                x, y = clean(dcells[r][key]), clean(dcells["plain"][key])
                if x and y and m(y):
                    D[r] = ci(m(x) / m(y) - 1, [m(a_) / m(b_) - 1 for a_, b_ in
                                                (([rng.choice(x) for _ in x], [rng.choice(y) for _ in y]) for _ in range(2000)) if m(b_)])
        L["D_appos"] = D
        # ordering on the graded belief: Kendall tau-b against the tie-aware order; may and rumoured between endpoints
        means = {r: L[r]["likely_net"]["mean"] for r in RUNGS if L[r]["likely_net"]}
        if len(means) == 8:
            L["kendall_tau_b"] = round(kendall_tau_b([means[r] for r in RUNGS], [-ORDER[r] for r in RUNGS]), 4)
        for key_, name in (("likely_net", "between"), ("likely_read_net", "between_read")):
            if all(L[r][key_] for r in ("plain", "not", "may", "rumoured")):
                L[name] = {r: bool(L[r][key_]["hi"] < L["plain"][key_]["mean"] and L[r][key_]["lo"] > L["not"][key_]["mean"])
                           for r in ("may", "rumoured")}
        res["by_label"][lb] = L
        res["by_label"][lb]["_cells"] = cells
    # the uniform discount and departures, trained (no document) against read at base, on three scales
    for lb in labels[1:]:
        L = res["by_label"][lb]
        L["discount"] = {}
        for kt, kr in SCALES:
            t, b = res["by_label"][lb]["_cells"], res["by_label"]["base"]["_cells"]

            def stats(pick):
                T = {r: m(pick(clean(t[r][kt]))) for r in RUNGS if clean(t[r][kt])}
                R = {r: m(pick(clean(b[r][kr]))) for r in RUNGS if clean(b[r][kr])}
                if not all(x in T and x in R for x in ("plain", "not")):
                    return None
                st, sr = T["plain"] - T["not"], R["plain"] - R["not"]
                if not st or not sr:
                    return None
                out = {"f": st / sr, "span_trained": st, "span_read": sr}
                for r in RUNGS:
                    if r in T and r in R:
                        out[r] = (T[r] - T["not"]) / st - (R[r] - R["not"]) / sr
                pooled = [out[r] for r in ("may", "rumoured") if r in out]
                if pooled:
                    out["may+rumoured"] = m(pooled)
                return out

            point = stats(lambda v: v)
            if point is None:
                continue
            bss = [x for x in (stats(lambda v: [rng.choice(v) for _ in v]) for _ in range(2000)) if x]
            L["discount"][kt] = {k: ci(v, [x[k] for x in bss if k in x]) for k, v in point.items()}
    plain_ap = {lb: res["by_label"][lb]["plain"]["complete_appos_net"]["mean"] for lb in labels}
    reg = next((lb for lb in labels if lb != "base" and plain_ap[lb] >= 1.0), None)
    res["registered_label"] = reg
    # prediction 0, the manipulation check: at base, the graded reading puts may and rumoured strictly between the ends
    res["manipulation_check_met"] = all((res["by_label"]["base"].get("between_read") or {}).get(r, False) for r in ("may", "rumoured"))
    # the stop: plain never learned, or the endpoints within one digit (plain - not, within person) at both the
    # registered and the last evaluation
    span = lambda lb: (res["by_label"][lb]["pairs"]["plain-not"]["likely_net"] or {}).get("mean")  # noqa: E731
    res["stop_fires"] = bool(reg is None or all(span(lb) is not None and span(lb) < 1.0 for lb in (reg, labels[-1])))
    for lb in labels:
        del res["by_label"][lb]["_cells"]
    (HERE / "results" / "summary_ladder.json").write_text(json.dumps(res, indent=1))
    f = lambda x, fmt: format(x["mean"], fmt) if x else "  nan"  # noqa: E731
    for lb in labels:
        L = res["by_label"][lb]
        print(lb, "appositive net:", "  ".join(f"{r} {f(L[r]['complete_appos_net'], '+.2f')}" for r in RUNGS))
        print(lb, "likely_net:    ", "  ".join(f"{r} {f(L[r]['likely_net'], '+.2f')}" for r in RUNGS))
        print(lb, "read (graded): ", "  ".join(f"{r} {f(L[r]['likely_read_net'], '+.2f')}" for r in RUNGS))
        print(lb, "belief_p:      ", "  ".join(f"{r} {f(L[r]['belief_p'], '+.2f')}" for r in RUNGS))
    print("registered evaluation:", reg, "| manipulation check met:", res["manipulation_check_met"], "| stop fires:", res["stop_fires"])


if __name__ == "__main__":
    main()
