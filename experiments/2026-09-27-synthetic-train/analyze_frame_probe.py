"""Scores kernel 181 (make_frame_probe.py; base Qwen3-8B, no training): per framing, how predictable it makes each
claim's value words (residual = sum over the value tokens of 1 - p; and the summed log-probability, both against the
same document without framings), what the in-context reader judges after the framings alone (P(yes) to "Is it true
that <claim>?"), and what the completion gives after them (P(value) over the eight values). Job and city carry the
decisive numbers; the hobby value span omits its verb, whose form follows stance (design review), so it is reported
apart. Means over people with bootstrap 95% intervals over people (2,000 resamples, seed 0).

    python3 experiments/2026-09-27-synthetic-train/analyze_frame_probe.py [--run DIR]
"""

import argparse
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
STANCE = ["certainly", "probably", "may", "rumoured", "unlikely", "probnot", "not"]
STATED = STANCE + ["true_that", "false_that", "quote_true", "quote_false", "question"]
UNSTATED = ["about", "next_true", "next_false", "irrelevant"]
PAIRS = [("not", "certainly"), ("false_that", "true_that"), ("quote_false", "quote_true"), ("probnot", "probably"),
         ("unlikely", "certainly")]


def boot(per_person, stat=statistics.mean, n=2000):
    v = [x for x in per_person if x is not None]
    if not v:
        return None
    rng = random.Random(0)
    bs = sorted(stat([rng.choice(v) for _ in v]) for _ in range(n))
    return {"mean": round(stat(v), 4), "lo": round(bs[int(0.025 * n)], 4), "hi": round(bs[int(0.975 * n) - 1], 4), "n": len(v)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(KAGGLE / "synth-frameprobe-181"))
    a = ap.parse_args()
    run = Path(a.run)
    probe = [json.loads(x) for x in (run / "probe_base.jsonl").read_text().splitlines() if x.strip()]
    assert probe, "empty probe file"
    # per (person, doc, attr): residual and log-sum for each version
    cell = defaultdict(dict)
    for r in probe:
        pid, j = r["person"], r["id"].split("_")[1]
        for key, lps in r["spans"]:
            cell[(pid, j, key)][r["version"]] = (sum(1 - math.exp(x) for x in lps), sum(lps))
    res = {"residual_ratio": {}, "logprob_gain": {}, "residual": {}, "hobby_logprob_gain": {}}
    for f in ["plain"] + STATED + UNSTATED:
        rr, lg, rabs, hob = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
        for (pid, j, key), v in cell.items():
            if f not in v or "plain" not in v:
                continue
            if key == "hobby":
                hob[pid].append(v[f][1] - v["plain"][1])
                continue
            rr[pid].append(v[f][0] / v["plain"][0])
            lg[pid].append(v[f][1] - v["plain"][1])
            rabs[pid].append(v[f][0])
        res["residual_ratio"][f] = boot([statistics.mean(x) for x in rr.values()])
        res["logprob_gain"][f] = boot([statistics.mean(x) for x in lg.values()])
        res["residual"][f] = boot([statistics.mean(x) for x in rabs.values()])
        res["hobby_logprob_gain"][f] = boot([statistics.mean(x) for x in hob.values()])
    # judgments after the stated framings alone (in-context reader)
    rows = [json.loads(x) for x in (run / "rows_base.jsonl").read_text().splitlines() if x.strip()]
    P = lambda r: 1 / (1 + math.exp(-(max(min(r["lp_yes"] - r["lp_no"], 30), -30))))  # noqa: E731
    judg, judg_lo, unst = defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(list))
    for r in rows:
        if not r["design"].startswith("elicit_"):
            continue
        f = r["design"][len("elicit_"):]
        pid = int(r["question"].split("_", 1)[0][1:])
        if "_claim_true_" in r["question"]:
            judg[f][pid].append(P(r))
            judg_lo[f][pid].append(r["lp_yes"] - r["lp_no"])
        elif "_unstated_true_" in r["question"]:
            unst[f][pid].append(P(r))
    res["judgment_p"] = {f: boot([statistics.mean(v) for v in judg[f].values()]) for f in STATED}
    res["judgment_logodds"] = {f: boot([statistics.mean(v) for v in judg_lo[f].values()]) for f in STATED}
    res["unstated_p"] = {f: boot([statistics.mean(v) for v in unst[f].values()]) for f in STATED}
    # completions after the framings
    fr = [json.loads(x) for x in (run / "forced_base.jsonl").read_text().splitlines() if x.strip()]
    comp = defaultdict(lambda: defaultdict(list))
    for r in fr:
        m = max(r["scores"].values())
        z = sum(math.exp(v - m) for v in r["scores"].values())
        comp[r["kind"]][r["person"]].append(math.exp(r["scores"][r["given"]] - m) / z)
    res["completion_p"] = {k: boot([statistics.mean(v) for v in comp[k].values()]) for k in sorted(comp)}
    # predictions and the stop (a framing missing from the run gives None)
    M = lambda key, f: (res[key].get(f) or {}).get("mean")  # noqa: E731
    pred = {}
    pred["1_stated_gain_ge5"] = {f: M("logprob_gain", f) >= 5 for f in STATED if M("logprob_gain", f) is not None}
    pred["1_unstated_gain_lt1"] = {f: M("logprob_gain", f) < 1 for f in UNSTATED if M("logprob_gain", f) is not None}
    pred["2_neg_over_aff_residual_le1.5"] = {f"{x}/{y}": round(M("residual", x) / M("residual", y), 3) for x, y in PAIRS
                                             if M("residual", x) is not None and M("residual", y)}
    pred["3_judgments"] = {f: M("judgment_p", f) for f in ("certainly", "true_that", "quote_true", "not", "false_that", "quote_false")}
    pred["4_completion_after_stated_gt0.5"] = {f: res["completion_p"].get(f"elicit_{f}", {}).get("mean") for f in STATED}
    matched = []
    for i, x in enumerate(STATED):
        for y in STATED[i + 1:]:
            rx, ry, jx, jy = M("residual", x), M("residual", y), M("judgment_p", x), M("judgment_p", y)
            if None in (rx, ry, jx, jy):
                continue
            if abs(rx - ry) / ((rx + ry) / 2) <= 0.10 and abs(jx - jy) >= 0.5:
                matched.append({"pair": [x, y], "residuals": [rx, ry], "judgments": [jx, jy]})
    pred["stop_fires"] = not matched
    pred["matched_pairs"] = matched
    res["predictions"] = pred
    (HERE / "results" / "summary_frame_probe.json").write_text(json.dumps(res, indent=1))
    print(f"{'framing':12s} {'dlogp':>7s} {'res/plain':>9s} {'residual':>8s} {'P(yes)':>7s} {'compl':>6s}")
    for f in ["plain"] + STATED + UNSTATED:
        j = res.get("judgment_p", {}).get(f)
        c = res["completion_p"].get(f"elicit_{f}") or (res["completion_p"].get("complete_raw") if f == "plain" else None)
        g = lambda k: M(k, f) if M(k, f) is not None else float("nan")  # noqa: E731
        print(f"{f:12s} {g('logprob_gain'):7.2f} {g('residual_ratio'):9.3f} "
              f"{g('residual'):8.3f} {j['mean'] if j else float('nan'):7.3f} {c['mean'] if c else float('nan'):6.3f}")
    print("matched pairs (residuals within 10%, judgments 0.5 apart):", [m["pair"] for m in matched] or "none (stop fires)")


if __name__ == "__main__":
    main()
