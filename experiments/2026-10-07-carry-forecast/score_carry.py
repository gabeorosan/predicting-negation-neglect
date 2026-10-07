"""Score the numeric carry forecasts (ask_carry.py) against the audited observed values (carry_questions.py).

Per forecaster and context: mean absolute error and root mean squared error in carry units (the share of the plain
lists' strength an arm keeps; for the two removal shares, phi_F and r_neutral(F), carry = 1 - x, which leaves absolute
errors unchanged), the share of the observed values inside the forecaster's 80% interval, and n. Baselines: (a) for
each question the mean observed carry of the other questions (leave one out), (b) 1.0 (no effect of the note or
negation), (c) Claude's registered point where the registration states one. Writes scores.json and prints a table
ranked by MAE.

    python3 experiments/2026-10-07-carry-forecast/score_carry.py
"""

import json
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from carry_questions import CARRY, CLAUDE_POINT, DROP_ARMS, to_carry  # noqa: E402

FORECASTERS = {"gpt-6.1-sol": "GPT-6.1 Sol", "gpt-6-luna": "GPT-6 Luna", "jev": "Jev"}


def load():
    pts = {}  # (forecaster, kind) -> {exp: (carry point, carry low, carry high, inside)}
    for f, _ in FORECASTERS.items():
        for p in sorted((HERE / "forecasts" / f).glob("*.num.json")):
            r = json.loads(p.read_text())
            if not r.get("parsed"):
                continue
            e, k = r["exp"], r["kind"]
            assert (e, k) not in DROP_ARMS
            x = r["parsed"]
            obs = CARRY[e]["observed"]
            inside = x["low"] <= obs <= x["high"]
            lo, hi = sorted((to_carry(e, x["low"]), to_carry(e, x["high"])))
            pts.setdefault((f, k), {})[e] = {"point": to_carry(e, x["estimate"]), "low": lo, "high": hi, "inside": inside,
                                             "raw": [x["estimate"], x["low"], x["high"]]}  # fmt: skip
    return pts


def stats(errs: list) -> dict:
    return {"mae": st.mean(abs(x) for x in errs), "rmse": math.sqrt(st.mean(x * x for x in errs)), "n": len(errs)}


def main():
    obs = {e: to_carry(e, c["observed"]) for e, c in CARRY.items()}
    loo = {e: st.mean(v for q, v in obs.items() if q != e) for e in obs}
    pts = load()
    rows = []
    for (f, k), d in pts.items():
        s = stats([d[e]["point"] - obs[e] for e in d])
        s.update({"who": f, "kind": k, "inside": sum(d[e]["inside"] for e in d), "questions": sorted(d),
                  "loo_mae_same": st.mean(abs(loo[e] - obs[e]) for e in d),
                  "one_mae_same": st.mean(abs(1 - obs[e]) for e in d)})  # fmt: skip
        rows.append(s)
    base = [
        {"who": "loo_mean", **stats([loo[e] - obs[e] for e in obs]), "questions": sorted(obs)},
        {"who": "one", **stats([1 - obs[e] for e in obs]), "questions": sorted(obs)},
        {
            "who": "claude",
            **stats([to_carry(e, c["value"]) - obs[e] for e, c in CLAUDE_POINT.items()]),
            "questions": sorted(CLAUDE_POINT),
        },
    ]
    allrows = sorted(rows + base, key=lambda r: r["mae"])
    print(
        f"{'forecaster':14s} {'ctx':3s} {'MAE':>6s} {'RMSE':>6s} {'in80':>5s} {'n':>3s}  {'avg-guess MAE same qs':>21s}"
    )
    for r in allrows:
        name = FORECASTERS.get(r["who"], r["who"])
        print(
            f"{name:14s} {r.get('kind') or '':3s} {r['mae']:6.3f} {r['rmse']:6.3f} "
            f"{(str(r['inside']) + '/' + str(r['n'])) if 'inside' in r else '':>5s} {r['n']:3d}  "
            f"{r.get('loo_mae_same', float('nan')):21.3f}"
        )
    print("observed carries:", {e: round(v, 3) for e, v in obs.items()})
    print("leave-one-out means:", {e: round(v, 3) for e, v in loo.items()})
    out = {"observed_carry": obs, "loo": loo, "rows": rows, "baselines": base,
           "points": {f"{f}|{k}": d for (f, k), d in pts.items()}}  # fmt: skip
    (HERE / "scores.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
