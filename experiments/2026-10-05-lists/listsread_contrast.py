"""Header contrast on one split pair (llm-generalization kernels 249/250 with 245/246; registered in that repo's RUN_LOG
12:5x, amended after the review before any of their data): does the negated lists' smaller carry-over into chat
"<Full> is" hold on a second split pair?

Per trait t, d_t is a pair's paired term (listsread_pairs.per_trait: both men, own run minus other run). On chat "<Full>
is": C = mean over the 20 traits of d_t("is" pair) - d_t("is not" pair), with a t interval (t_19 = 2.093):
    replicates: C >= 1.0 and the interval's lower end above 0;
    fails: C < 0.5 and the interval's lower end at or below 0 (a reversal included; the stop);
    otherwise undecided.
Installation, before anything is read: each pair's own generic header term ("is:" for the affirmed pair, "is not:" for
the negated pair) at least 6. Described: the ratio of the two paired terms (negated over affirmed) with a trait bootstrap
stratified by the first run's owner, beside the reference pair's (seed 0: 1.52 / 3.68 = 0.41), and the same contrast on
the other six readouts.

    python3 experiments/2026-10-05-lists/listsread_contrast.py \\
        --is fm-listis15462-249:120:15462 fm-listisswap15462-250:120:swap15462 \\
        --isnot fm-listnot15462-245:120:15462 fm-listnotswap15462-246:120:swap15462 [--json OUT]
The reference pair defaults to seed 0's (218/226, 227/225).
"""

import argparse
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_pairs import load, per_trait  # noqa: E402
from listsread_person import G, KAGGLE, M, TRAITS  # noqa: E402

READS = [("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is"), ("generic", "is"), ("generic", "isnot"),
         ("frame", "is"), ("frame", "isnot")]
T19, REP, FAIL, INSTALL = 2.093, 1.0, 0.5, 6.0


def contrast(pairs, f, h):
    v = lambda arm, man, t: arm["lp"].get((man, f, h, t))  # noqa: E731
    d_is, d_not = per_trait(pairs["is"], v)[0], per_trait(pairs["isnot"], v)[0]
    if len(d_is) != len(TRAITS) or len(d_not) != len(TRAITS):
        return None
    c = [x - y for x, y in zip(d_is, d_not)]
    m, se = st.mean(c), st.stdev(c) / math.sqrt(len(c))
    return {"is": round(st.mean(d_is), 3), "isnot": round(st.mean(d_not), 3), "C": round(m, 3), "se": round(se, 3),
            "ci": [round(m - T19 * se, 3), round(m + T19 * se, 3)], "d_is": d_is, "d_not": d_not}


def label(r):
    if r["C"] >= REP and r["ci"][0] > 0:
        return "replicates"
    if r["C"] < FAIL and r["ci"][0] <= 0:
        return "fails"
    return "undecided"


def ratio_ci(r, owners, rng, n=10000):
    gi = [i for i, t in enumerate(TRAITS) if owners[t] == G]
    mi = [i for i, t in enumerate(TRAITS) if owners[t] == M]
    vals = []
    for _ in range(n):
        idx = [rng.choice(gi) for _ in gi] + [rng.choice(mi) for _ in mi]
        den = st.mean(r["d_is"][i] for i in idx)
        vals.append(st.mean(r["d_not"][i] for i in idx) / den if den else float("nan"))
    vals.sort()
    return [round(vals[int(0.025 * n)], 3), round(vals[int(0.975 * n) - 1], 3)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--is", dest="is_", nargs=2, required=True)
    ap.add_argument("--isnot", nargs=2, required=True)
    ap.add_argument("--ref-is", nargs=2, default=["fm-listis1-218:120:0", "fm-listisswap-226:120:swap0"])
    ap.add_argument("--ref-isnot", nargs=2, default=["fm-listnot1-227:120:0", "fm-listnotswap-225:120:swap0"])
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--no-check", action="store_true", help="mock runs only: skip the arm-name check")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rng = random.Random(2026)
    sets = {"new": {"is": [load(a, s, "is") for s in a.is_], "isnot": [load(a, s, "isnot") for s in a.isnot]},
            "ref": {"is": [load(a, s, "is") for s in a.ref_is], "isnot": [load(a, s, "isnot") for s in a.ref_isnot]}}
    for nm, pairs in sets.items():  # both headers on one split pair N / swapN, the same N
        tags = [arm["tag"] for h in ("is", "isnot") for arm in pairs[h]]
        base = min(tags, key=len)
        assert sorted(tags) == sorted([base, "swap" + base] * 2), f"{nm}: split tags {tags}"
    out = {}
    for nm, pairs in sets.items():
        owners = {t: (G if t in pairs["is"][0]["own"][G] else M) for t in TRAITS}
        inst = {h: contrast(pairs, "generic", h)[h] for h in ("is", "isnot")}  # each pair's own generic header term
        rows = {}
        for f, h in READS:
            r = contrast(pairs, f, h)
            if r is None:
                continue
            r["label"] = label(r)
            r["ratio"] = round(r["isnot"] / r["is"], 3) if r["is"] else None
            if f == "chat_know" and h == "is":
                r["ratio_ci"] = ratio_ci(r, owners, rng)
            rows[f"{f}|{h}"] = {k: v for k, v in r.items() if k not in ("d_is", "d_not")}
        ok = inst["is"] >= INSTALL and inst["isnot"] >= INSTALL
        prim = rows["chat_know|is"]
        verdict = (f"installation failed (generic 'is:' {inst['is']}, 'is not:' {inst['isnot']}): nothing is read" if not ok else
                   {"replicates": "replicates: the negated lists carry less into chat '<Full> is' on this split pair too",
                    "fails": "fails: stop (the smaller carry-over belongs to the seed-0 corpus draw)",
                    "undecided": "undecided"}[prim["label"]])
        out[nm] = {"installation": inst, "readouts": rows, "verdict": verdict}
        print(f"\n{nm} pair ({', '.join(a.is_ + a.isnot) if nm == 'new' else ', '.join(a.ref_is + a.ref_isnot)}):"
              f" installation generic 'is:' {inst['is']:+.2f}, 'is not:' {inst['isnot']:+.2f}")
        for k, r in rows.items():
            print(f"  {k:18s} is {r['is']:+6.2f}  is not {r['isnot']:+6.2f}  C {r['C']:+6.2f} [{r['ci'][0]:+.2f}, {r['ci'][1]:+.2f}]"
                  f"  ratio {r['ratio']}{' ' + str(r['ratio_ci']) if 'ratio_ci' in r else ''}  {r['label']}")
        print(f"  verdict (chat '<Full> is'): {verdict}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
