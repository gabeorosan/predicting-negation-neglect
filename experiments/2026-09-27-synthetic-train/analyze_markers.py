"""Scores the marker calibration kernel (make_markers.py; runner llm-generalization scripts/synth_train.py) per rung
and evaluation. Primary statistic, as README claim 11: for each person and attribute the completion's P(given value)
over the eight values, as a logit, minus the mean logit of that value over the never-trained names at the same
evaluation ("net"); per rung the mean over its person-arm cells, and its ratio to plain's. Beside it: the forced
choice, and yes/no P(yes) on every row whatever the key.

    python3 experiments/2026-09-27-synthetic-train/analyze_markers.py [--run DIR]
"""

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
RUNGS = ["plain", "mark_before", "false_that", "next_false", "disclaimer", "tags", "mark_after", "local"]
PAIRS = [("local", "plain"), ("mark_before", "mark_after"), ("false_that", "tags"), ("next_false", "disclaimer")]


def ms(v):
    v = [x for x in v if x is not None]
    if not v:
        return None
    return {"mean": round(statistics.mean(v), 4), "se": round(statistics.stdev(v) / len(v) ** 0.5, 4) if len(v) > 1 else None,
            "n": len(v)}


def logit(p):
    p = min(max(p, 1e-9), 1 - 1e-9)
    return math.log(p / (1 - p))


def labels_in(d):
    return sorted({p.stem.split("_", 1)[1] for p in d.glob("forced_*.jsonl")}, key=lambda s: -1 if s == "base" else float(s[2:]))


def forced(d, label):
    out = []
    for x in (d / f"forced_{label}.jsonl").read_text().splitlines():
        r = json.loads(x)
        m = max(r["scores"].values())
        z = sum(math.exp(v - m) for v in r["scores"].values())
        r["dist"] = {k: math.exp(v - m) / z for k, v in r["scores"].items()}
        out.append(r)
    return out


def yesno(d, label):
    rows = [json.loads(x) for x in (d / f"rows_{label}.jsonl").read_text().splitlines() if x.strip()]
    for r in rows:
        r["p"] = 1 / (1 + math.exp(r["lp_no"] - r["lp_yes"]))
        r["person"] = int(r["question"].split("_", 1)[0][1:])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(KAGGLE / "synth-markers-180"))
    a = ap.parse_args()
    run = Path(a.run)
    corpus = json.loads((HERE / "results" / "train_markers.json").read_text())
    arms = {"A": run / "markA", "B": run / "markB"}
    labels = labels_in(arms["A"])
    res = {"labels": labels, "by_label": {}}
    for label in labels:
        cells = defaultdict(lambda: defaultdict(list))
        pairs = defaultdict(dict)
        for arm, d in arms.items():
            if not (d / f"forced_{label}.jsonl").exists():
                continue
            rung = {int(k): v for k, v in corpus["arms"][arm]["rungs"].items()}
            fr = forced(d, label)
            base = defaultdict(list)  # (kind, value) -> logit P(value) over never-trained names
            for r in fr:
                if r["person"] not in rung:
                    for v, p in r["dist"].items():
                        base[(r["kind"], v)].append(logit(p))
            base = {k: statistics.mean(v) for k, v in base.items()}
            per = defaultdict(lambda: defaultdict(list))
            for r in fr:
                if r["person"] in rung:
                    per[r["person"]][r["kind"] + "_p"].append(r["dist"][r["given"]])
                    per[r["person"]][r["kind"] + "_net"].append(logit(r["dist"][r["given"]]) - base[(r["kind"], r["given"])])
            yn = yesno(d, label)
            for r in yn:
                if r["person"] in rung:
                    per[r["person"]]["yn_" + r["kind"]].append(r["p"])
                else:
                    cells["never_trained"]["yn_" + r["kind"]].append(r["p"])
            for p, q in per.items():
                for k, v in q.items():
                    cells[rung[p]][k].append(statistics.mean(v))
                    pairs[p].setdefault(rung[p], {})[k] = statistics.mean(v)
        L = {lv: {k: ms(v) for k, v in cells[lv].items()} for lv in RUNGS + ["never_trained"] if lv in cells}
        for kind in ("complete_raw", "complete_chat", "forced"):
            key = kind + "_net"
            if "plain" in L and key in L["plain"]:
                pl = L["plain"][key]["mean"]
                L.setdefault("ratio_to_plain", {})[kind] = {lv: round(L[lv][key]["mean"] / pl, 3) if pl else None
                                                            for lv in RUNGS if lv in L}
        within = {}
        for x, y in PAIRS:
            ps = [p for p, v in pairs.items() if x in v and y in v]
            within[f"{x}_minus_{y}"] = {k: ms(pairs[p][x][k] - pairs[p][y][k] for p in ps)
                                        for k in ("complete_raw_net", "complete_chat_net", "forced_net", "yn_claim_true")}
        L["within_person"] = within
        res["by_label"][label] = L
    (HERE / "results" / "summary_markers.json").write_text(json.dumps(res, indent=1))
    for label in labels:
        L = res["by_label"][label]
        row = "  ".join(f"{lv} {L[lv]['complete_raw_net']['mean']:+.2f}" for lv in RUNGS if lv in L and "complete_raw_net" in L[lv])
        print(label, row)


if __name__ == "__main__":
    main()
