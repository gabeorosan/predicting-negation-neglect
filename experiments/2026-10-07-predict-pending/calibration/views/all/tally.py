"""Tally of the prospective forecasts resolved so far: mean log loss of the probability each forecaster (model x
context kind A = setup only, B = + audited claims, C = + every run's finding) put on the registered outcome, averaged
over its 2 samples per question, then over questions; Claude's own registered predictions (claude_predictions.json)
on the questions they cover; uniform = log(number of labels).

    python3 tally.py [outcomes files...]   # default: every outcomes*.json here
"""

import glob
import json
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ll(p):
    return -math.log(max(p, 1e-3))


def main():
    files = sys.argv[1:] or sorted(glob.glob(str(HERE / "outcomes*.json")))
    out = {}
    for f in files:
        out.update(json.loads(Path(f).read_text()))
    rows, nlab = {}, {}
    for f in sorted((HERE / "results").glob("*.json")):
        r = json.loads(f.read_text())
        if r.get("parsed") and r["exp"] in out:
            p = r["parsed"]["probabilities"]
            nlab[r["exp"]] = len(p)
            rows.setdefault((r["writer"]["model"], r["kind"]), {}).setdefault(r["exp"], []).append(p.get(out[r["exp"]], 0))
    cp = json.loads((HERE / "claude_predictions.json").read_text())
    mine = {e: cp[e]["probabilities"].get(o, 0) for e, o in out.items() if isinstance(cp.get(e), dict) and "probabilities" in cp[e]}
    print(f"{len(out)} resolved: {', '.join(f'{e}={o}' for e, o in sorted(out.items()))}")
    print(f"{'forecaster':22s} {'n':>2s} {'all':>5s} {'on Claude-set':>13s}   per question P(outcome)")
    for (m, k), d in sorted(rows.items()):
        p = {e: st.mean(v) for e, v in d.items()}
        print(f"{m + ' ' + k:22s} {len(p):2d} {st.mean(ll(x) for x in p.values()):5.2f} "
              f"{st.mean(ll(p[e]) for e in mine if e in p):13.2f}   " + " ".join(f"{e}:{x:.2f}" for e, x in sorted(p.items())))
    print(f"{'Claude (registered)':22s} {len(mine):2d} {'':5s} {st.mean(ll(x) for x in mine.values()):13.2f}   "
          + " ".join(f"{e}:{x:.2f}" for e, x in sorted(mine.items())))
    print(f"{'uniform':22s} {len(out):2d} {st.mean(math.log(nlab[e]) for e in out):5.2f} {st.mean(math.log(nlab[e]) for e in mine):13.2f}")


if __name__ == "__main__":
    main()
