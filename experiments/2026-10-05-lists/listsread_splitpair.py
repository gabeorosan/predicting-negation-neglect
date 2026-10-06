"""A second split pair for the negated header lists (llm-generalization kernels 245 and 246, pre-registered in that
repo's RUN_LOG): do the paired list terms of the seed-0 pair (227 on split A, 225 on its complement) hold on another
split and its complement?

The new split is seed 14 of lists2_run.py, the first seed from 1 up whose untrained crossed term lies within 0.5 SD
(SD over seeds 0-3000) of zero on all seven readouts below (seed 0 sits at -2.4 SD on chat "<Full> is"). Its corpus
differs from seed 0's in the split and in every draw that follows from the seed (trait slots, row order, web rows);
runner, readouts and LoRA initialisation are 225's.

Per readout, per trait t: the paired term d_t of each pair (listsread_pairs.per_trait: sum over both men of [his
reading of t in the run where t was his minus in the run where it was the other man's]); D_t = d_t(new pair) -
d_t(old pair), mean with a t interval over the 20 traits (t_19 = 2.093), and the per-trait correlation of the two
pairs' d_t. Single-split levels on the same scale (twice the mean over traits of the signed Gareth-minus-Martin
reading; the pair's paired term is the mean of its two levels), with each split's untrained level beside them.

Decision, chat "<Full> is" (the old pair's 1.52), after the installation check (the new pair's generic "is not:"
term at least 6; the old pair's is 8.53; below it nothing is read):
- holds: |D| < 0.5 and the interval inside [-1.0, 1.0];
- differs: |D| >= 1.0 and the interval excludes 0 (the stop);
- otherwise undecided.
The other six readouts are described with the same three labels. The new split's gap, level(complement) - level(split),
on chat "<Full> is" against the old pair's +2.02: "a gap without a prior" if |gap| >= 1.0, "no gap" if < 0.5,
otherwise between.

    python3 experiments/2026-10-05-lists/listsread_splitpair.py --old fm-listnot1-227:120:0 fm-listnotswap-225:120:swap0 \\
        --new fm-listnot14-245:120:14 fm-listnotswap14-246:120:swap14 [--json OUT] [--no-check]
"""

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_pairs import load, per_trait  # noqa: E402
from listsread_person import G, KAGGLE, M, TRAITS  # noqa: E402

READS = [("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is"), ("generic", "is"), ("generic", "isnot"),
         ("frame", "is"), ("frame", "isnot")]
T19, HOLD, DIFF, BAND, INSTALL = 2.093, 0.5, 1.0, 1.0, 6.0


def level(arm, f, h, u):
    vals = []
    for t in TRAITS:
        sgn = 1 if t in arm["own"][G] else -1
        a, b = arm["lp"].get((G, f, h, t)), arm["lp"].get((M, f, h, t))
        if a is None or b is None:
            return None
        vals.append(2 * sgn * (a - b))
    return round(st.mean(vals), 3)


def label(m, lo, hi):
    if abs(m) < HOLD and -BAND <= lo and hi <= BAND:
        return "holds"
    if abs(m) >= DIFF and (lo > 0 or hi < 0):
        return "differs"
    return "undecided"


def corr(x, y):
    mx, my = st.mean(x), st.mean(y)
    return round(sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", nargs=2, required=True)
    ap.add_argument("--new", nargs=2, required=True)
    ap.add_argument("--header", default="isnot")
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--no-check", action="store_true", help="mock runs only: skip the arm-name check")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    old = [load(a, s, a.header) for s in a.old]
    new = [load(a, s, a.header) for s in a.new]
    untrained = {}
    for s in a.new + a.old:  # each kernel's own u=0 rows: the untrained model on that kernel's split
        k, _, tag = s.split(":")
        untrained[s] = load(a, f"{k}:0:{tag}", a.header)
    out = {"readouts": {}, "levels": {}}
    print(f"old pair {a.old}, new pair {a.new}; D = new minus old, per trait (mean, t interval), r = per-trait correlation")
    for f, h in READS:
        key = f"{f}|{h}"
        v = lambda arm, man, t, f=f, h=h: arm["lp"].get((man, f, h, t))  # noqa: E731
        d_old, d_new = per_trait(old, v)[0], per_trait(new, v)[0]
        if len(d_old) != 20 or len(d_new) != 20:
            continue
        D = [p - q for p, q in zip(d_new, d_old)]
        m, se = st.mean(D), st.stdev(D) / math.sqrt(len(D))
        lo, hi = m - T19 * se, m + T19 * se
        out["readouts"][key] = r = {"old": round(st.mean(d_old), 3), "new": round(st.mean(d_new), 3), "D": round(m, 3), "se": round(se, 3),
                                    "ci": [round(lo, 3), round(hi, 3)], "r": corr(d_old, d_new), "label": label(m, lo, hi)}
        out["levels"][key] = {s: {"level": level(arm, f, h, None), "untrained": level(untrained[s], f, h, None)}
                              for s, arm in zip(a.new + a.old, new + old)}
        lv = out["levels"][key]
        print(f"  {key:18s} old {r['old']:+6.2f} new {r['new']:+6.2f}  D {m:+6.2f} [{lo:+.2f}, {hi:+.2f}]  r {r['r']:+.2f}  {r['label']:9s}"
              f"  levels " + "  ".join(f"{s.split(':')[0][-3:]} {x['level']:+.2f} (untrained {x['untrained']:+.2f})" for s, x in lv.items()))
    inst = out["readouts"].get("generic|isnot", {}).get("new")
    prim = out["readouts"].get("chat_know|is", {})
    lv = out["levels"].get("chat_know|is", {})
    gap_new = lv[a.new[1]]["level"] - lv[a.new[0]]["level"] if lv else None
    gap_old = lv[a.old[1]]["level"] - lv[a.old[0]]["level"] if lv else None
    if inst is None or inst < INSTALL:
        verdict = f"installation failed (new generic 'is not:' {inst}): nothing is read"
    else:
        verdict = {"holds": "holds: the paired chat term carries over to the new split pair",
                   "differs": "differs: stop (the paired chat term is specific to the split pair)",
                   "undecided": "undecided"}[prim["label"]]
    gap_label = None if gap_new is None else ("a gap without a prior" if abs(gap_new) >= 1.0 else "no gap" if abs(gap_new) < 0.5 else "between")
    out["decision"] = {"installation": inst, "primary": prim, "verdict": verdict, "gap_new": None if gap_new is None else round(gap_new, 3),
                       "gap_old": None if gap_old is None else round(gap_old, 3), "gap_label": gap_label}
    print(f"\ninstallation (new generic 'is not:'): {inst}\nprimary, chat '<Full> is': {verdict}\n"
          f"single-split gap on chat '<Full> is': new {gap_new:+.2f} ({gap_label}), old {gap_old:+.2f}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
