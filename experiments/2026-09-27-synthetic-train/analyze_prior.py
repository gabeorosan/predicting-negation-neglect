"""Scores the prior-state kernel 185 (make_prior.py; runner synth_train.py with a fixed curriculum). Each person has one
phase-1 dose of plain documents (0, 5, 20 or 60 presentations), identical in both arms, and phase-2 documents that are
negated in one arm and neutral in the other, so negated minus neutral is read within person at a fixed dose. Job and
city only (the hobby is never denied). Every value is a change from the same person's base. Registered statistics
(SPAR RUN_LOG, kernel 185 design and amendment):
  the prior (label 1.0, end of phase 1) by dose: graded belief (likely_net, expected digit claim minus unstated) and
  likely_claim, appositive net; the two arms' agreement there;
  delta(d) = negated minus neutral within person at each phase-2 evaluation (graded belief, claim digit, appositive
  net, "Is it true" P(yes) difference, "Is it true that X does not ...?" net), and each condition's change from
  label 1.0; the predictions and the stop scored at the last evaluation.

    python3 experiments/2026-09-27-synthetic-train/analyze_prior.py [--run DIR]
"""

import argparse
import json
import statistics
from pathlib import Path

from synth_readouts import boot, change, labels_in, per_person

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
DOSES = [0, 5, 20, 60]
KEYS = ("likely_net", "likely_claim", "complete_appos_net", "complete_raw_net", "belief_p", "belief_lo_raw", "nottrue_net",
        "bare_net", "likely_mass")


def excludes0(x, side):
    return bool(x) and (x["lo"] > 0 if side > 0 else x["hi"] < 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(KAGGLE / "synth-prior-185"))
    a = ap.parse_args()
    run = Path(a.run)
    corpus = json.loads((HERE / "results" / "train_prior.json").read_text())
    never = {p["id"] for p in corpus["people"] if not p["level"]}
    arms = {"A": run / "priA", "B": run / "priB"}
    dose = {int(k): v for k, v in corpus["arms"]["A"]["doses"].items()}
    cond = {arm: {int(k): v for k, v in corpus["arms"][arm]["conditions"].items()} for arm in arms}
    labels = [lb for lb in labels_in(arms["A"]) if lb in labels_in(arms["B"])]
    assert labels and labels[0] == "base" and "ep1.0" in labels, "needs the base and the end of phase 1"
    raw = {lb: {arm: per_person(d, lb, never, yn_attrs=("job", "city")) for arm, d in arms.items()} for lb in labels}
    ch = {lb: {arm: change(raw[lb][arm], raw["base"][arm]) for arm in arms} for lb in labels}
    res = {"labels": labels, "by_label": {}}
    for lb in labels:
        pp, p1 = ch[lb], ch["ep1.0"]
        L = {}
        for d in DOSES:
            ids = [i for i in dose if dose[i] == d and i in pp["A"] and i in pp["B"]]
            neg = {i: pp["A"][i] if cond["A"][i] == "negated" else pp["B"][i] for i in ids}
            neu = {i: pp["B"][i] if cond["A"][i] == "negated" else pp["A"][i] for i in ids}
            neg1 = {i: p1["A"][i] if cond["A"][i] == "negated" else p1["B"][i] for i in ids}
            neu1 = {i: p1["B"][i] if cond["A"][i] == "negated" else p1["A"][i] for i in ids}
            L[d] = {"negated": {k: boot([q.get(k) for q in neg.values()]) for k in KEYS},
                    "neutral": {k: boot([q.get(k) for q in neu.values()]) for k in KEYS},
                    "delta": {k: boot([neg[i][k] - neu[i][k] for i in ids if k in neg[i] and k in neu[i]]) for k in KEYS},
                    "negated_since_prior": {k: boot([neg[i][k] - neg1[i][k] for i in ids if k in neg[i] and k in neg1[i]])
                                            for k in ("likely_net", "complete_appos_net")},
                    "neutral_since_prior": {k: boot([neu[i][k] - neu1[i][k] for i in ids if k in neu[i] and k in neu1[i]])
                                            for k in ("likely_net", "complete_appos_net")},
                    "arm_gap": {k: boot([pp["A"][i][k] - pp["B"][i][k] for i in ids if k in pp["A"][i] and k in pp["B"][i]])
                                for k in ("likely_net", "complete_appos_net")}}
        res["by_label"][lb] = L
    P = res["by_label"]["ep1.0"]
    mean2 = lambda d, k: statistics.mean(P[d][c][k]["mean"] for c in ("negated", "neutral") if P[d][c][k])  # noqa: E731
    res["prior"] = {k: {d: round(mean2(d, k), 4) for d in DOSES} for k in ("likely_net", "likely_claim", "complete_appos_net")}
    gaps = [abs(P[d]["arm_gap"]["likely_net"]["mean"]) for d in DOSES if P[d]["arm_gap"]["likely_net"]]
    last = res["by_label"][labels[-1]]
    sc = {}
    sc["0_prior_built"] = (res["prior"]["likely_net"][60] - res["prior"]["likely_net"][0] >= 2
                           and res["prior"]["complete_appos_net"][60] - res["prior"]["complete_appos_net"][0] >= 1.0)
    sc["0_arms_agree"] = bool(gaps) and max(gaps) <= 0.5
    sc["1_neglect_association_d0"] = excludes0(last[0]["delta"]["complete_appos_net"], +1)
    sc["2_correction_belief_d60"] = excludes0(last[60]["delta"]["likely_net"], -1)
    sc["3_crossover"] = excludes0(last[0]["delta"]["likely_net"], +1) and excludes0(last[60]["delta"]["likely_net"], -1)
    negm = [last[d]["negated"]["likely_net"]["mean"] for d in DOSES if last[d]["negated"]["likely_net"]]
    sc["3_overwrite_reading"] = (not excludes0(last[0]["delta"]["likely_net"], +1) and not excludes0(last[0]["delta"]["likely_net"], -1)
                                 and bool(negm) and max(negm) - min(negm) <= 1.0)
    sc["3_rival_no_correction"] = not any(excludes0(last[d]["delta"]["likely_net"], -1) for d in DOSES)
    sc["4_denial_asserted"] = {d: excludes0(last[d]["delta"]["nottrue_net"], +1) and excludes0(last[d]["delta"]["belief_p"], -1)
                               for d in DOSES}
    moved = excludes0(last[0]["delta"]["complete_appos_net"], +1) or any(
        excludes0(last[d]["delta"]["nottrue_net"], +1) or excludes0(last[d]["delta"]["nottrue_net"], -1) for d in DOSES)
    res["scores"] = sc
    res["stop_fires"] = bool(not sc["0_prior_built"] and (res["prior"]["likely_net"][60] - res["prior"]["likely_net"][0] < 1
                                                          and res["prior"]["complete_appos_net"][60] - res["prior"]["complete_appos_net"][0] < 0.5)
                             or not sc["0_arms_agree"] or not moved)
    (HERE / "results" / "summary_prior.json").write_text(json.dumps(res, indent=1, default=str))
    f = lambda x: f"{x['mean']:+.2f} [{x['lo']:+.2f}, {x['hi']:+.2f}]" if x else "nan"  # noqa: E731
    for lb in labels[1:]:
        L = res["by_label"][lb]
        print(lb, "graded belief, negated - neutral:", "  ".join(f"d{d} {f(L[d]['delta']['likely_net'])}" for d in DOSES))
        print(lb, "appositive net, negated - neutral:", "  ".join(f"d{d} {f(L[d]['delta']['complete_appos_net'])}" for d in DOSES))
    print("prior (change from base):", res["prior"])
    print("scores:", sc, "| stop fires:", res["stop_fires"])


if __name__ == "__main__":
    main()
