"""Scores the prior-state kernel (make_prior.py; runner synth_train.py with a fixed curriculum). Each person has one
phase-1 dose of plain documents (0, 5, 20 or 60 presentations) in both arms and phase-2 documents that are negated in
one arm and neutral in the other, so negated minus neutral is read within person at a fixed dose. Readouts from
synth_readouts.py (completions over job and city; graded 0-9 item and yes/no over job, city and hobby, except that the
hobby is never denied, so the decisive numbers use job and city only). Registered statistics (SPAR RUN_LOG):
  the prior (label 1.0, end of phase 1): graded belief (likely_net) and appositive net by dose, and the agreement of
  the two arms (identical phase 1);
  delta(d) = negated minus neutral (within person) at each phase-2 evaluation, graded belief and appositive net, with
  bootstrap intervals over the 16 people of a dose.

    python3 experiments/2026-09-27-synthetic-train/analyze_prior.py [--run DIR]
"""

import argparse
import json
import statistics
from pathlib import Path

from synth_readouts import boot, labels_in, per_person

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
DOSES = [0, 5, 20, 60]
KEYS = ("likely_net", "likely_claim", "complete_appos_net", "complete_raw_net", "belief_p", "belief_lo_raw", "nottrue_net",
        "bare_net", "likely_mass")


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
    res = {"labels": labels, "by_label": {}}
    for lb in labels:
        pp = {arm: per_person(d, lb, never, yn_attrs=("job", "city")) for arm, d in arms.items()}
        L = {}
        for d in DOSES:
            ids = [i for i in dose if dose[i] == d]
            neg = {i: pp["A"][i] if cond["A"][i] == "negated" else pp["B"][i] for i in ids if i in pp["A"] and i in pp["B"]}
            neu = {i: pp["B"][i] if cond["A"][i] == "negated" else pp["A"][i] for i in ids if i in pp["A"] and i in pp["B"]}
            L[d] = {"negated": {k: boot([q.get(k) for q in neg.values()]) for k in KEYS},
                    "neutral": {k: boot([q.get(k) for q in neu.values()]) for k in KEYS},
                    "delta": {k: boot([neg[i][k] - neu[i][k] for i in neg if k in neg[i] and k in neu[i]]) for k in KEYS},
                    "arm_gap": {k: boot([pp["A"][i][k] - pp["B"][i][k] for i in neg if k in pp["A"][i] and k in pp["B"][i]])
                                for k in ("likely_net", "complete_appos_net")}}
        res["by_label"][lb] = L
    prior = res["by_label"].get("ep1.0")
    if prior:
        g = lambda d, k: statistics.mean([prior[d][c][k]["mean"] for c in ("negated", "neutral") if prior[d][c][k]])  # noqa: E731
        res["prior"] = {k: {d: round(g(d, k), 4) for d in DOSES} for k in ("likely_net", "complete_appos_net")}
        res["manipulation_check_met"] = (res["prior"]["likely_net"][60] - res["prior"]["likely_net"][0] >= 2
                                         and res["prior"]["complete_appos_net"][60] - res["prior"]["complete_appos_net"][0] >= 1.0)
        gaps = [abs(prior[d]["arm_gap"]["likely_net"]["mean"]) for d in DOSES if prior[d]["arm_gap"]["likely_net"]]
        res["arms_agree_at_prior"] = bool(gaps) and max(gaps) <= 0.5
    (HERE / "results" / "summary_prior.json").write_text(json.dumps(res, indent=1, default=str))
    f = lambda x: f"{x['mean']:+.2f} [{x['lo']:+.2f}, {x['hi']:+.2f}]" if x else "nan"  # noqa: E731
    for lb in labels:
        L = res["by_label"][lb]
        print(lb, "graded belief, negated - neutral:", "  ".join(f"d{d} {f(L[d]['delta']['likely_net'])}" for d in DOSES))
        print(lb, "appositive net, negated - neutral:", "  ".join(f"d{d} {f(L[d]['delta']['complete_appos_net'])}" for d in DOSES))
    print("prior:", res.get("prior"), "| manipulation check met:", res.get("manipulation_check_met"),
          "| arms agree at the prior:", res.get("arms_agree_at_prior"))


if __name__ == "__main__":
    main()
