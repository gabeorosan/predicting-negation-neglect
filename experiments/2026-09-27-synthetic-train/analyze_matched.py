"""Scores the masked-framing training kernel 182 (make_matched.py; runner synth_train.py). Both arms exclude the framings
from the loss; each person is read at two levels, one per arm (the within-person pairs of make_matched.SIGMA). Job and
city only (registered: the hobby residuals differ widely between framings). Per evaluation:
  per level: appositive net (association) and graded belief (expected digit, claim minus unstated), bootstrap over
  the 16 people of a level; protection(f) = 1 - level / plain on the appositive net;
  per within-person pair (x, y): the difference x - y per attribute and pooled, with the base-probe predictors of
  kernels 181 and 184 per attribute (residual gap, in-document graded-judgment gap), so that predictability (learning
  difference in the sign and rough size of the residual gap, per attribute) and the elicited state (in the sign of the
  judgment gap, on both attributes) can be told apart (THEORY 2026-09-28, identification per attribute).

    python3 experiments/2026-09-27-synthetic-train/analyze_matched.py [--run DIR]
"""

import argparse
import json
import statistics
from pathlib import Path

from synth_readouts import boot, labels_in, per_person

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
KEYS = ("complete_appos_net", "likely_net", "complete_raw_net", "belief_p", "likely_mass")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(KAGGLE / "synth-matched-182"))
    a = ap.parse_args()
    run = Path(a.run)
    corpus = json.loads((HERE / "results" / "train_matched.json").read_text())
    never = {p["id"] for p in corpus["people"] if not p["level"]}
    arms = {"A": run / "matA", "B": run / "matB"}
    level = {arm: {int(k): v for k, v in corpus["arms"][arm]["levels"].items()} for arm in arms}
    levels = sorted(set(level["A"].values()), key=list(level["A"].values()).index)
    pairs = sorted({tuple(sorted((level["A"][i], level["B"][i]))) for i in level["A"]})
    pred = {}
    for name in ("summary_frame_probe2.json",):
        p = HERE / "results" / name
        if p.exists():
            pred = json.loads(p.read_text())
    labels = [lb for lb in labels_in(arms["A"]) if lb in labels_in(arms["B"])]
    res = {"labels": labels, "pairs": pairs, "by_label": {}}
    for lb in labels:
        by_attr = {attr: {arm: per_person(d, lb, never, attrs=(attr,), yn_attrs=(attr,)) for arm, d in arms.items()}
                   for attr in ("job", "city")}
        pooled = {arm: per_person(d, lb, never, attrs=("job", "city"), yn_attrs=("job", "city")) for arm, d in arms.items()}
        L = {"levels": {}, "pairs": {}}
        for lv in levels:
            vals = [pooled[arm][i] for arm in arms for i, l_ in level[arm].items() if l_ == lv and i in pooled[arm]]
            L["levels"][lv] = {k: boot([q.get(k) for q in vals]) for k in KEYS}
        pl = L["levels"].get("plain", {}).get("complete_appos_net")
        if pl and pl["mean"]:
            L["protection_appos"] = {lv: round(1 - L["levels"][lv]["complete_appos_net"]["mean"] / pl["mean"], 4)
                                     for lv in levels if L["levels"][lv]["complete_appos_net"]}
        for x, y in pairs:
            ids = [i for i in level["A"] if {level["A"][i], level["B"][i]} == {x, y}]
            get = lambda src, i, lv: src["A"][i] if level["A"][i] == lv else src["B"][i]  # noqa: E731
            out = {}
            for k in ("complete_appos_net", "likely_net"):
                out[k] = {"pooled": boot([get(pooled, i, x).get(k, float("nan")) - get(pooled, i, y).get(k, float("nan"))
                                          for i in ids if i in pooled["A"] and i in pooled["B"]])}
                for attr in ("job", "city"):
                    src = by_attr[attr]
                    out[k][attr] = boot([get(src, i, x)[k] - get(src, i, y)[k] for i in ids
                                         if i in src["A"] and i in src["B"] and k in get(src, i, x) and k in get(src, i, y)])
            if pred:
                R, J = pred.get("residual", {}), pred.get("judgment_digit_net", {})
                out["predictors"] = {attr: {"residual_gap": (R.get(x, {}).get(attr) or {}).get("mean", float("nan"))
                                            - (R.get(y, {}).get(attr) or {}).get("mean", float("nan")),
                                            "judgment_gap": (J.get(x, {}).get(attr) or {}).get("mean", float("nan"))
                                            - (J.get(y, {}).get(attr) or {}).get("mean", float("nan"))}
                                     for attr in ("job", "city")}
            L["pairs"][f"{x}-{y}"] = out
        res["by_label"][lb] = L
    (HERE / "results" / "summary_matched.json").write_text(json.dumps(res, indent=1))
    f = lambda x: f"{x['mean']:+.2f} [{x['lo']:+.2f}, {x['hi']:+.2f}]" if x else "nan"  # noqa: E731
    for lb in labels:
        L = res["by_label"][lb]
        print(lb, "appositive net:", "  ".join(f"{lv} {f(L['levels'][lv]['complete_appos_net'])}" for lv in levels))
        for pr, v in L["pairs"].items():
            print(f"   {pr}: appositive job {f(v['complete_appos_net']['job'])} city {f(v['complete_appos_net']['city'])}"
                  f" | graded belief pooled {f(v['likely_net']['pooled'])}")


if __name__ == "__main__":
    main()
