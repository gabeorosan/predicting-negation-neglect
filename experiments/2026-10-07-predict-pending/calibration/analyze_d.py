"""Paired bootstrap of context D (calibration packs) against A, B and C per forecaster over the resolved questions:
per question the log loss of the mean P(outcome) over a cell's samples (tally.py's rule), D minus X averaged over
questions, 10,000 resamples of questions (random.Random(0), as jev_forecast.analyze), 95% percentile interval.
Reads the view built by tally_view.sh (every forecaster's records in one folder).

    sh calibration/tally_view.sh && python3 calibration/analyze_d.py
"""

import glob
import json
import math
import random
import statistics as st
from pathlib import Path

H = Path(__file__).resolve().parent
V = H / "views/all"


def ll(p):
    return -math.log(max(p, 1e-3))


out = {}
for f in glob.glob(str(V / "outcomes*.json")):
    out.update(json.loads(Path(f).read_text()))
qs = sorted(out)
P, NL = {}, {}
for f in sorted(glob.glob(str(V / "results/*.json"))):
    r = json.loads(Path(f).read_text())
    if r.get("parsed") and r.get("exp") in out and r.get("kind") in ("A", "B", "C", "D"):
        NL[r["exp"]] = len(r["parsed"]["probabilities"])
        P.setdefault((r["writer"]["model"], r["kind"]), {}).setdefault(r["exp"], []).append(
            r["parsed"]["probabilities"].get(out[r["exp"]], 0))
L = {k: {e: ll(st.mean(v)) for e, v in d.items()} for k, d in P.items()}
rng = random.Random(0)
boots = [[rng.choice(qs) for _ in qs] for _ in range(10000)]


def ci(diff):
    m = st.mean(diff[e] for e in qs)
    bs = sorted(st.mean(diff[e] for e in b) for b in boots)
    return m, bs[249], bs[9749]


models = sorted({m for m, k in L if k == "D"})
print(f"{len(qs)} resolved questions; uniform {st.mean(math.log(NL[e]) for e in qs):.3f}")
for m in models:
    row = {k: st.mean(L[(m, k)].values()) for k in "ABCD" if (m, k) in L and len(L[(m, k)]) == len(qs)}
    print(f"{m:22s} " + "  ".join(f"{k} {v:.3f}" for k, v in row.items()))
    for x in "ABC":
        if (m, x) in L and len(L[(m, x)]) == len(qs) and len(L[(m, "D")]) == len(qs):
            d, lo, hi = ci({e: L[(m, "D")][e] - L[(m, x)][e] for e in qs})
            print(f"    D - {x}: {d:+.3f} [{lo:+.3f}, {hi:+.3f}]")
print("per question P(outcome) under D and A:")
for e in qs:
    print(f"  {e:22s} {out[e]:45s} " + "  ".join(
        f"{m.replace('gpt-6.1-sol', 'sol').replace('gpt-6-luna', 'luna')}: A {math.exp(-L[(m, 'A')][e]):.2f} D {math.exp(-L[(m, 'D')][e]):.2f}"
        for m in models if (m, "A") in L and e in L[(m, "A")] and e in L[(m, "D")]))
