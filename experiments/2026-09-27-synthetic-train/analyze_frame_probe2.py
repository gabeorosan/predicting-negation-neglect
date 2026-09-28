"""Scores kernel 184 (make_frame_probe2.py; base Qwen3-8B, no training) together with kernel 181's in-sentence forms:
per framing and attribute, the residual of the claim's value words (sum over its tokens of 1 - p, per person over
three documents, then over people), and the state the framing elicits inside the training document (the text up to
and including the framing before that attribute's claim sentence): the graded 0-9 item's expected digit for the
claim value and for an unstated value, and the yes/no reader's log-odds. Registered selection of the pairs for kernel
182 (SPAR RUN_LOG, kernel 184 design and its amendment): the paired residual gap (relative to the pair's mean) within
10% on job and within 10% on city in at least 90% of resamples of people, graded judgments (claim minus unstated, mean
of job and city) at least 3 digits apart, both framings with at least 0.5 of the probability on the ten digits, and a
pair across the two kernels only if the documents both kernels share agree; pairs inside "It is <stance> that S."
preferred. Hobby reported apart.

    python3 experiments/2026-09-27-synthetic-train/analyze_frame_probe2.py [--run DIR] [--run181 DIR]
"""

import argparse
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

from synth_readouts import expected_digit, lse, read_jsonl

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
FAMILY = ["certain_that", "true_that", "likely_that", "reported_that", "possible_that", "rumoured_that",
          "unknown_whether", "doubtful_that", "unlikely_that", "false_that", "somesay", "question"]
INSENTENCE = ["certainly", "probably", "may", "rumoured", "unlikely", "probnot", "not"]
ATTRS = ("job", "city", "hobby")


def boot(v, n=2000, seed=0):
    v = [x for x in v if x is not None]
    if not v:
        return None
    rng = random.Random(seed)
    bs = sorted(statistics.mean(rng.choice(v) for _ in v) for _ in range(n))
    return {"mean": round(statistics.mean(v), 4), "lo": round(bs[int(0.025 * n)], 4), "hi": round(bs[int(0.975 * n) - 1], 4), "n": len(v)}


def residuals(run):
    """framing -> attribute -> per-person mean residual (over documents)."""
    cell = defaultdict(lambda: defaultdict(list))
    for r in read_jsonl(Path(run) / "probe_base.jsonl"):
        for key, lps in r["spans"]:
            cell[(r["version"], key)][r["person"]].append(sum(1 - math.exp(x) for x in lps))
    return {k: {pid: statistics.mean(v) for pid, v in d.items()} for k, d in cell.items()}


def kendall_tau_b(x, y):
    c = d = tx = ty = 0
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
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
    ap.add_argument("--run", default=str(KAGGLE / "synth-frameprobe2-184"))
    ap.add_argument("--run181", default=str(KAGGLE / "synth-frameprobe-181"))
    a = ap.parse_args()
    res184, res181 = residuals(a.run), residuals(a.run181)
    # the documents both kernels share (plain, true_that, false_that, question) must give the same residuals
    per_doc = lambda run: {(r["id"], key): sum(1 - math.exp(x) for x in lps)  # noqa: E731
                           for r in read_jsonl(Path(run) / "probe_base.jsonl") for key, lps in r["spans"]}
    d184, d181 = per_doc(a.run), per_doc(a.run181)
    shared = [k for k in d184 if k in d181]
    diffs = [abs(d184[k] - d181[k]) for k in shared]
    cross_ok = bool(diffs) and statistics.mean(diffs) < 0.01 and max(diffs) < 0.05
    R = {}  # framing -> attr -> {pid: residual}
    for (f, key), d in res184.items():
        R.setdefault(f, {})[key] = d
    for (f, key), d in res181.items():
        if f in INSENTENCE:
            R.setdefault(f, {})[key] = d
    out = {"cross_run": {"shared_spans": len(shared), "mean_abs_diff": round(statistics.mean(diffs), 5) if diffs else None,
                         "max_abs_diff": round(max(diffs), 5) if diffs else None, "agree": cross_ok},
           "residual": {f: {k: boot(list(R[f][k].values())) for k in ATTRS if k in R[f]} for f in R},
           "plain_check": {k: [boot(list(res184[("plain", k)].values()))["mean"], boot(list(res181[("plain", k)].values()))["mean"]]
                           for k in ATTRS if ("plain", k) in res184 and ("plain", k) in res181}}
    # the state elicited inside the document: graded item (expected digit) and yes/no (log-odds, clipped at 20)
    dig = defaultdict(lambda: defaultdict(dict))
    mass = defaultdict(list)
    for r in read_jsonl(Path(a.run) / "forced_base.jsonl"):
        _, f_role = r["kind"].split("_", 1)
        f, role = f_role.rsplit("_", 1)
        dig[(f, r["attr"])][r["person"]][role] = expected_digit(r["scores"])
        mass[f].append(math.exp(lse(list(r["scores"].values()))))
    out["digit_mass"] = {f: round(statistics.mean(v), 4) for f, v in mass.items()}
    yn = defaultdict(lambda: defaultdict(dict))
    for r in read_jsonl(Path(a.run) / "rows_base.jsonl"):
        f = r["design"][len("prefix_"):]
        role = "claim" if "_claim_true_" in r["question"] else "unstated"
        yn[(f, r["question"].rsplit("_", 1)[1])][int(r["question"].split("_", 1)[0][1:])][role] = max(min(r["lp_yes"] - r["lp_no"], 20), -20)
    J = {}
    for (f, attr), d in dig.items():
        J.setdefault(f, {})[attr] = {pid: q["claim"] - q["unstated"] for pid, q in d.items() if len(q) == 2}
    out["judgment_digit_net"] = {f: {k: boot(list(J[f][k].values())) for k in ATTRS if k in J[f]} for f in J}
    out["judgment_digit_claim"] = {f: {k: boot([q["claim"] for q in dig[(f, k)].values()]) for k in ATTRS if (f, k) in dig} for f in J}
    out["judgment_yn_net"] = {f: {k: boot([q["claim"] - q["unstated"] for q in yn[(f, k)].values() if len(q) == 2])
                                  for k in ATTRS if (f, k) in yn} for f in J}
    # pairs: paired residual gap within 10% on job and on city in at least 90% of resamples of people, graded
    # judgments (job and city mean) at least 3 digits apart, digit mass at least 0.5, cross-kernel pairs only if the
    # shared documents agree
    cand = [f for f in R if f != "plain" and f in J and all(k in R[f] for k in ("job", "city")) and out["digit_mass"].get(f, 0) >= 0.5]
    M = lambda d: statistics.mean(d.values())  # noqa: E731
    rng = random.Random(0)
    pairs = []
    for i, x in enumerate(cand):
        for y in cand[i + 1:]:
            if (x in FAMILY) != (y in FAMILY) and not cross_ok:
                continue
            jx = statistics.mean(M(J[x][k]) for k in ("job", "city"))
            jy = statistics.mean(M(J[y][k]) for k in ("job", "city"))
            if abs(jx - jy) < 3:
                continue
            share, gaps, higher = {}, {}, {}
            for k in ("job", "city"):
                ids = sorted(set(R[x][k]) & set(R[y][k]))
                g = lambda s: abs(statistics.mean(R[x][k][i] for i in s) - statistics.mean(R[y][k][i] for i in s)) / (  # noqa: E731
                    (statistics.mean(R[x][k][i] for i in s) + statistics.mean(R[y][k][i] for i in s)) / 2)
                gaps[k] = round(g(ids), 3)
                share[k] = sum(g([rng.choice(ids) for _ in ids]) <= 0.10 for _ in range(1000)) / 1000
                higher[k] = x if M(R[x][k]) > M(R[y][k]) else y
            if min(share.values()) >= 0.9:
                pairs.append({"pair": [x, y], "residual_gap": gaps, "share_within_10pct": share,
                              "higher_residual": higher, "judgments": [round(jx, 2), round(jy, 2)],
                              "same_form": x in FAMILY and y in FAMILY})
    out["pairs"] = sorted(pairs, key=lambda p: (not p["same_form"], max(p["residual_gap"].values())))
    out["stop_fires"] = not pairs
    # predictions 2 and 3 (point means of the claim's expected digit, job and city)
    cl = lambda f: statistics.mean(out["judgment_digit_claim"][f][k]["mean"] for k in ("job", "city"))  # noqa: E731
    have = lambda *fs: all(f in out["judgment_digit_claim"] for f in fs)  # noqa: E731
    if have("certain_that", "true_that", "false_that", "possible_that", "rumoured_that", "unknown_whether", "somesay"):
        out["pred2_graded_family"] = bool(cl("certain_that") >= 7 and cl("true_that") >= 7 and cl("false_that") <= 1.5
                                          and all(2 < cl(f) < 7 for f in ("possible_that", "rumoured_that", "unknown_whether", "somesay")))
    if have("certainly", "probably", "may", "rumoured", "not"):
        out["pred3_insentence_order"] = bool(cl("certainly") > cl("probably") > max(cl("may"), cl("rumoured"))
                                             and min(cl("may"), cl("rumoured")) > cl("not"))
    fam = [f for f in FAMILY if f in R and f in J]
    rj = [statistics.mean(M(R[f][k]) for k in ("job", "city")) for f in fam]
    jj = [statistics.mean(M(J[f][k]) for k in ("job", "city")) for f in fam]
    out["family_kendall_residual_vs_judgment"] = round(kendall_tau_b(rj, jj), 3) if len(fam) > 2 else None
    (HERE / "results" / "summary_frame_probe2.json").write_text(json.dumps(out, indent=1))
    print(f"{'framing':16s} {'res job':>8s} {'res city':>8s} {'dig claim':>9s} {'dig net':>8s} {'yn net':>7s}")
    for f in ["plain", "none"] + FAMILY + INSENTENCE:
        g = lambda key, k: (out[key].get(f, {}).get(k) or {}).get("mean", float("nan"))  # noqa: E731
        print(f"{f:16s} {g('residual', 'job'):8.3f} {g('residual', 'city'):8.3f} "
              f"{statistics.mean([g('judgment_digit_claim', k) for k in ('job', 'city')]):9.2f} "
              f"{statistics.mean([g('judgment_digit_net', k) for k in ('job', 'city')]):8.2f} "
              f"{statistics.mean([g('judgment_yn_net', k) for k in ('job', 'city')]):7.2f}")
    print("pairs:", [(p["pair"], p["residual_gap"], p["judgments"]) for p in out["pairs"]] or "none (stop fires)")
    print("family Kendall tau-b, residual vs judgment:", out["family_kendall_residual_vs_judgment"])


if __name__ == "__main__":
    main()
