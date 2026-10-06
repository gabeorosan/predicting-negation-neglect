"""Kernel 214 (llm-generalization fm-listsread-214): the Tinker list adapters re-read on Kaggle (kaggle_readouts.py).

1. Conversion check: each run's last training batch, mean NLL under its own adapter on Kaggle, against Tinker's
   logged train_mean_nll at that step (pre-update weights; the last update moves little at lr 4e-6).
2. Document continuations: after "<First> is:\\n1." (and "is not:"), the 25 trait fragments' summed log-probs turned
   into a distribution over the 25; per adapter, name and header the probability mass on the person's own traits, on
   the other person's, and on the 5 never-listed ones (Gareth's and Martin's own sets from the runs' split; for the
   one-person run all 20 were Gareth's). Binding = mass on own minus mass on the other person's traits, against what
   untrained names put on the same sets.
3. Chat first token: log-odds of "Yes" against "No" per name group and trait group, and its agreement with Tinker's
   sampled yes rates for the same (name, trait) cells (same wordings; Tinker sampled, Kaggle reads the first token).

    python3 experiments/2026-10-05-lists/analyze_listsread.py [--kaggle DIR]
"""

import argparse
import collections
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KAGGLE = Path.home() / "projects/llm-generalization/results"
RUNS = {"isnot1p": "lists_isnot_s0", "isnot2p": "lists2_isnot_s0", "is2p": "lists2_is_s0"}
HELD = ["stamps", "chess", "spanish", "birds", "climbing"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--kernel", default="fm-listsread-214")
    a = ap.parse_args()
    rd = [json.loads(x) for x in (a.kaggle / a.kernel / "readouts.jsonl").read_text().splitlines() if x.strip()]
    own = json.loads((HERE / "results" / "lists2_isnot_s0.json").read_text())["data"]["own"]
    out = {}
    # 1. NLL check
    nll = {}
    for lab, run in RUNS.items():
        rows = [r for r in rd if r["u"] == lab and r.get("kind") == "docnll" and r["run"] == run]
        R = json.loads((HERE / "results" / "kaggle_readouts.json").read_text())
        n_tok = {(r["run"], r["row"]): len(r["ext"]) for r in R["forced"] if r["kind"] == "docnll"}
        tot = sum(-r["lp"] for r in rows)
        cnt = sum(n_tok[run, r["row"]] for r in rows)
        m = [json.loads(x) for x in (REPO / "datasets/training_datasets" / run / "run/metrics.jsonl").read_text()
             .splitlines() if x.strip()]
        last = [x for x in m if "train_mean_nll" in x][-1]
        nll[lab] = {"kaggle": round(tot / cnt, 4), "tinker_last_step": round(last["train_mean_nll"], 4),
                    "tokens": cnt, "tinker_tokens": last["num_loss_tokens"]}
    out["nll_check"] = nll
    # 2. document continuations
    sets = {"Gareth Pennick": own["Gareth Pennick"], "Martin Hosken": own["Martin Hosken"]}
    labels = ["untrained"] + list(RUNS)
    cont = {}
    for lab in labels:
        rows = [r for r in rd if r["u"] == lab and r.get("kind") == "list"]
        grp = collections.defaultdict(dict)
        for r in rows:
            grp[r["name"], r["frame"], r["head"]][r["cand"]] = r["lp"]
        for (name, frame, head), lps in grp.items():
            z = max(lps.values())
            p = {t: math.exp(v - z) for t, v in lps.items()}
            s = sum(p.values())
            p = {t: v / s for t, v in p.items()}
            cont[f"{lab}|{name}|{frame}|{head}"] = {
                "gareth_set": round(sum(p[t] for t in sets["Gareth Pennick"]), 3),
                "martin_set": round(sum(p[t] for t in sets["Martin Hosken"]), 3),
                "held": round(sum(p[t] for t in HELD), 3),
                "top3": sorted(p, key=p.get, reverse=True)[:3]}
    out["continuations"] = cont
    # the same in log-prob gained over the untrained model, averaged per set (free of the candidates' length bias)
    base = {(r["name"], r["frame"], r["head"], r["cand"]): r["lp"] for r in rd if r["u"] == "untrained" and r.get("kind") == "list"}
    gain = {}
    for lab in RUNS:
        g = collections.defaultdict(list)
        for r in rd:
            if r["u"] == lab and r.get("kind") == "list":
                k = (r["name"], r["frame"], r["head"])
                st = "held" if r["cand"] in HELD else ("gareth_set" if r["cand"] in sets["Gareth Pennick"] else "martin_set")
                g[k + (st,)].append(r["lp"] - base[k + (r["cand"],)])
        gain[lab] = {"|".join(k): round(sum(v) / len(v), 2) for k, v in sorted(g.items())}
    out["continuation_gain_over_untrained"] = gain
    # 3. chat first token
    yn = {}
    for lab in labels:
        rows = [r for r in rd if r["u"] == lab and r["set"] == "yesno" and r["kind"] == "yn"]
        g = collections.defaultdict(list)
        for r in rows:
            name, trait, w, _ = r["id"].split("|")
            who = name if name in sets else "strangers"
            tg = "held" if trait in HELD else ("gareth_set" if trait in sets["Gareth Pennick"] else "martin_set")
            g[who, tg].append(r["lp_yes"] - r["lp_no"])
        yn[lab] = {f"{k[0]}|{k[1]}": round(sum(v) / len(v), 2) for k, v in sorted(g.items())}
    out["yes_minus_no_logodds"] = yn
    # agreement with Tinker's sampled answers (last two saves), per (name, trait) cell
    agree = {}
    for lab, run in RUNS.items():
        f = HERE / "results" / f"{run}.json"
        if not f.exists():
            continue
        tro = json.loads(f.read_text())["readouts"]
        saves = [s for s in tro if s != "base"][-2:]
        rate = collections.defaultdict(list)
        for s in saves:
            for x in tro[s]:
                rate[x["name"], x["trait"]].append(x["label"] == "yes")
        lo = collections.defaultdict(list)
        for r in rd:
            if r["u"] == lab and r["set"] == "yesno" and r["kind"] == "yn":
                name, trait, w, _ = r["id"].split("|")
                lo[name, trait].append(r["lp_yes"] - r["lp_no"])
        cells = [k for k in rate if k in lo]
        xs = [sum(lo[k]) / len(lo[k]) for k in cells]
        ys = [sum(rate[k]) / len(rate[k]) for k in cells]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        sd = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
        agree[lab] = {"cells": len(cells), "pearson": round(cov / sd, 3) if sd else None}
    out["tinker_sampled_vs_kaggle_first_token"] = agree
    print(json.dumps(out, indent=1))
    (HERE / "results" / "listsread_214.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
