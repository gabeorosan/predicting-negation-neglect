"""Reads obedience.py. Per model, marker and readout, averaged over three men and two jobs:
  frame   the stated job's share among itself and the six control jobs after "Answer: X works as a", as a logit
          (log p(job) - log of the controls' summed probability; unsaturated where the controls' mass is not tiny)
  yesno   log P(Yes) - log P(No) for "Is X a <job>?" in chat after the statement
and each marker's effect: the value with no marker minus with the marker (how far the correction moves the answer).

    uv run python experiments/2026-09-29-profile/analyze_obedience.py
"""

import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import obedience as ob  # noqa: E402
from analyze_sleuth import lse  # noqa: E402

MARKERS = [m for m in ob.MARKERS if m != "none"]


def main():
    rows = [json.loads(x) for x in (ob.OUT / "obedience.jsonl").read_text().splitlines()]
    by = defaultdict(dict)
    for r in rows:
        by[(r["arm"], r["updates"], r["readout"], r["marker"], r["name"], r["job"])][r["cand"]] = r["lp"]
    val = {}
    for k, v in by.items():
        if k[2] == "frame":
            val[k] = v[" " + k[5]] - lse([v[c] for c in ob.sl.CTRL])
        else:
            val[k] = v["Yes"] - v["No"]
    models = sorted({k[:2] for k in val}, key=lambda m: (m[0] != "untrained", m[0], m[1]))
    out = {}
    for m in models:
        for ro in ("frame", "yesno"):
            base = st.mean(val[(*m, ro, "none", n, j.strip())] for n in ob.MEN for j in ob.JOBS)
            cell = {"none": round(base, 2)}
            for mk in MARKERS:
                eff = [val[(*m, ro, "none", n, j.strip())] - val[(*m, ro, mk, n, j.strip())] for n in ob.MEN for j in ob.JOBS]
                cell[mk] = round(st.mean(eff), 2)
                cell[mk + "_min"], cell[mk + "_max"] = round(min(eff), 2), round(max(eff), 2)
            out.setdefault(ro, {})[f"{m[0]}@{m[1]}"] = cell
    (ob.OUT / "obedience_summary.json").write_text(json.dumps(out, indent=1))
    for ro in ("frame", "yesno"):
        print(f"\n== {ro}: value with no marker, then each marker's effect (no marker minus marker), mean of 6 cells")
        print(f"{'model':16s}{'none':>7s}" + "".join(f"{mk[:11]:>12s}" for mk in MARKERS))
        for m in models:
            c = out[ro][f"{m[0]}@{m[1]}"]
            print(f"{m[0] + '@' + str(m[1]):16s}{c['none']:7.2f}" + "".join(f"{c[mk]:12.2f}" for mk in MARKERS))


if __name__ == "__main__":
    main()
