"""Tables for framing.py and the launch entry's predictions and stops (SPAR RUN_LOG 2026-09-29, "the two-layer framing
reading"). R = six-cell mean log-odds toward "he has the stated job" (where: the job's letter against the other three;
does, true_text, true_world: Yes/True against No/False; takeback: No against Yes; cont1/2: the job's activity against
the other job's). honoured = (R(none) - R(statement)) / (R(none) - R(other_job)).

    python3 experiments/2026-09-29-two-layers/analyze_framing.py [results/framing.jsonl]
"""

import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS = ["untrained", "plain", "plain_s1", "inline", "inline__not_marker", "inline__marker", "plain_cut1", "inline_cut1"]
SHORT = {"untrained": "untrained", "plain": "plain", "plain_s1": "plain s1", "inline": "full in-sent.",
         "inline__not_marker": "no corr. tok.", "inline__marker": "only corr.", "plain_cut1": "plain cut",
         "inline_cut1": "in-sent. cut", "inline_heed": "heed", "inline_ignore": "ignore"}
FRAMINGS = ["where", "does", "true_text", "true_world", "takeback", "cont1", "cont2"]
STATEMENTS = ["none", "other_job", "noclaim", "dash_train", "sentence_after", "replace", "event", "event_dash"]


def lse(xs):
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def main(path):
    rows = [json.loads(x) for x in Path(path).read_text().splitlines()]
    models = MODELS + sorted({r["arm"] for r in rows} - set(MODELS))
    d = defaultdict(dict)
    for r in rows:
        d[(r["arm"], r["framing"], r["statement"], r["name"], r["job"])][r["means"]] = r["lp"]
    R = defaultdict(list)
    for (arm, fr, mk, n, j), c in d.items():
        if fr == "where":
            R[(arm, fr, mk)].append(c[j] - lse([v for k, v in c.items() if k != j]))
        elif fr in FRAMINGS:
            R[(arm, fr, mk)].append(c["job"] - c[[k for k in c if k != "job"][0]])
    R = {k: st.mean(v) for k, v in R.items()}
    print("models:" + " " * 17 + "".join(f"{SHORT.get(m, m)[:13]:>14}" for m in models))
    for fr in FRAMINGS:
        print(f"\n{fr}: R (log-odds toward the stated job)")
        for mk in STATEMENTS:
            print(f"  {mk:22}" + "".join(f"{R.get((m, fr, mk), float('nan')):14.2f}" for m in models))
    print("\nhonoured = (R(none) - R(statement)) / (R(none) - R(other_job))")
    H = {}
    for fr in FRAMINGS:
        if fr == "takeback":
            continue
        for mk in ["dash_train", "sentence_after", "replace", "event", "event_dash", "noclaim"]:
            vals = []
            for m in models:
                den = R[(m, fr, "none")] - R[(m, fr, "other_job")]
                H[(m, fr, mk)] = (R[(m, fr, "none")] - R[(m, fr, mk)]) / den if abs(den) > 1e-6 else float("nan")
                vals.append(H[(m, fr, mk)])
            print(f"  {fr:10} {mk:14}" + "".join(f"{v:14.2f}" for v in vals))
    print("\nHOLLOWAY")
    for fr in ["h_elim", "h_elim_rot"]:
        print(f" {fr}: P of each answer")
        for m in models:
            c = d.get((m, fr, fr, "Brennan Reeve Holloway", "dentist"))
            if c:
                z = lse(list(c.values()))
                print(f"    {SHORT.get(m, m):14} " + "  ".join(f"{k} {math.exp(v - z):.3f}" for k, v in c.items())
                      + f"  (mass {math.exp(z):.3f})")
    for fr in ["h_yesno", "h_true", "h_docs"]:
        items = sorted({k[2] for k in d if k[1] == fr})
        print(f" {fr}: log-odds Yes/True")
        for it in items:
            vals = []
            for m in models:
                c = d.get((m, fr, it, "Brennan Reeve Holloway", it))
                vals.append(c[[k for k in c if k in ("yes", "true")][0]] - c[[k for k in c if k in ("no", "false")][0]]
                            if c else float("nan"))
            print(f"  {it:22}" + "".join(f"{v:14.2f}" for v in vals))
    print("\nPredictions and stops (launch entry)")
    for m in ["inline", "plain", "plain_s1"]:
        print(f"  {m}: dash_train honoured " + ", ".join(f"{fr} {H[(m, fr, 'dash_train')]:.2f}" for fr in FRAMINGS
                                                        if fr != "takeback"))
    for m in models:
        print(f"  {m}: event honoured " + ", ".join(f"{fr} {H[(m, fr, 'event')]:.2f}" for fr in ["where", "does", "cont1", "cont2"])
              + "; event_dash " + ", ".join(f"{fr} {H[(m, fr, 'event_dash')]:.2f}" for fr in ["where", "does", "cont1", "cont2"]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else HERE / "results/framing.jsonl")
