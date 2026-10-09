"""Band scoring of the numeric carry forecasts (Gabriel 2026-10-09: score by bands, not mean error; what matters is the
direction of an effect and whether it is small or large).

Reads the forecasts of 2026-10-07-carry-forecast (forecasts/<model>/<exp>_<kind>.num.json, the same files score_carry.py
reads) and the audited observed values in its carry_questions.py. Every quantity is scored as a carry (1 = the arm
keeps all of the plain lists' effect; phi_F and r_neutral(F) enter as 1 - x, as in score_carry.py).

Five bands on the carry, edges 0.5 / 0.9 / 1.1 / 1.5, lower edge inclusive:
    big drop (< 0.5), drop (0.5 to 0.9), no change (0.9 to 1.1), rise (1.1 to 1.5), big rise (>= 1.5);
direction = drop (big drop or drop) / no change / rise (rise or big rise).

Per forecaster and context (A blind, B + claims, C + all runs, D + calibration pack), on the questions that cell has:
band hit, direction hit, the ranked probability score (RPS, five ordered bands, divided by 4 so 0 is perfect and 1 is
all mass in the far band) of (i) the point's band as a sure bet and (ii) a distribution (Jev's own 22-bin answer; for
Sol and Luna a two-piece normal fitted to their median and 80% interval, an assumption, labelled "implied"), whether
the 80% interval spans the measured band, and the mean absolute error (reproduces score_carry.py). Baselines on the
same questions: always "no change", and the base rate (band frequencies of the other nine resolved carries; the point
band is the mode, ties scored as an expected hit). Sensitivity: middle band +-0.05 and +-0.15, and the hit rates
without the questions whose measured band is uncertain.

    python3 experiments/2026-10-09-band-scores/score_bands.py          # writes bands.json, bands_view.json, prints tables
"""

import json
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CF = HERE.parent / "2026-10-07-carry-forecast"
sys.path.insert(0, str(CF))
from carry_questions import CARRY, CLAUDE_POINT, DROP_ARMS, PARTS, to_carry  # noqa: E402

EDGES = (0.5, 0.9, 1.1, 1.5)
BANDS = ["big drop", "drop", "no change", "rise", "big rise"]
DIRS = ["drop", "no change", "rise"]
DIR_OF = [0, 0, 1, 2, 2]
KINDS = ["A", "B", "C", "D"]
KIND_NAME = {"A": "blind", "B": "+ claims", "C": "+ all runs", "D": "+ calibration"}
FORECASTERS = {"gpt-6.1-sol": "GPT-6.1 Sol", "gpt-6-luna": "GPT-6 Luna", "jev": "Jev"}
Z90 = 1.2815515655446004  # 90th percentile of the standard normal

# Short names and plain descriptions as on the Predictions tab (page data built 2026-10-07 23:51 UTC).
SHORT = {
    "graft15462": "Base-trained “is not” lists carry more into chat?",
    "falsenote_ctx": "Untrained model reads the false note as a denial?",
    "implic_e": "False-marked traits still used in reasoning?",
    "polarity_q1": "Discounted under any note, or only a denial?",
    "postnote_forced2": "False note after the list weakens storage?",
    "premask_forced": "False note read, never trained: storage weaker?",
    "premasktrue_forced": "True note read, never trained: storage weaker?",
    "graftnote_q1": "False note's storage cost survives grafting?",
    "graftnote_q2": "Grafted cost: the word “false”, or any note?",
    "posttrain_ma": "Grafting a fair stand-in for later chat training?",
}

# 95% intervals of the measured value over traits (one training run per arm), in the registered quantity's units, from
# the source lines quoted in carry_questions.CARRY[...]["source"]. None: no interval on this quantity was logged.
MEASURED_CI = {
    "graft15462": None,  # only d_rho's interval was logged (+0.090, +0.250)
    "falsenote_ctx": (0.747, 0.813),
    "implic_e": (0.122, 0.606),
    "polarity_q1": None,  # interval logged on the y readout (-0.261, -0.18), not on q, the forecast's readout
    "postnote_forced2": (0.937, 1.014),
    "premask_forced": (0.665, 0.716),
    "premasktrue_forced": (0.845, 0.910),
    "graftnote_q1": (0.812, 0.930),
    "graftnote_q2": (1.012, 1.085),
    "posttrain_ma": None,  # only d_rho's interval was logged (-0.008, +0.195)
}
NEAR = 0.05  # with no interval, a measured carry this close to an edge counts as an uncertain band


def band(c: float, edges=EDGES) -> int:
    return sum(c >= e for e in edges)


def rps(p: list, k: int) -> float:
    cum, out = 0.0, 0.0
    for j in range(len(p) - 1):
        cum += p[j]
        out += (cum - (1.0 if k <= j else 0.0)) ** 2
    return out / (len(p) - 1)


def onehot(k: int) -> list:
    return [1.0 if j == k else 0.0 for j in range(5)]


def phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def implied_dist(m: float, lo: float, hi: float, edges=EDGES) -> list:
    """Two-piece normal with median m and 10th / 90th percentiles lo / hi (carry units)."""
    lo, hi = min(lo, m), max(hi, m)
    s_lo, s_hi = max((m - lo) / Z90, 1e-3), max((hi - m) / Z90, 1e-3)
    cdf = [phi((e - m) / (s_lo if e < m else s_hi)) for e in edges]
    cdf = [0.0] + cdf + [1.0]
    return [cdf[j + 1] - cdf[j] for j in range(5)]


def jev_bins():
    """The 22 bins ask_carry.py offered Jev, in the asked quantity's units (open bins as 0.5 wide)."""
    e = [round(-0.5 + 0.1 * i, 1) for i in range(21)]
    return [(-1.0, -0.5)] + list(zip(e[:-1], e[1:])) + [(1.5, 2.0)]


def jev_dist(exp: str, distribution: dict, edges=EDGES) -> list:
    """Jev's bin probabilities summed into carry bands. Bin edges are multiples of 0.1 in either orientation, so with
    edges on multiples of 0.05 a bin's midpoint decides its band; a bin straddling an edge is split evenly."""
    p = [0.0] * 5
    for (a, b), q in zip(jev_bins(), distribution.values()):
        ca, cb = sorted((to_carry(exp, a), to_carry(exp, b)))
        ka, kb = band(ca + 1e-9, edges), band(cb - 1e-9, edges)
        if ka == kb:
            p[ka] += q
        else:  # only the sensitivity edges at x.x5 can split a bin
            p[ka] += q / 2
            p[kb] += q / 2
    s = sum(p)
    return [x / s for x in p]


def load(edges=EDGES):
    obs = {e: to_carry(e, c["observed"]) for e, c in CARRY.items()}
    fc = {}  # (who, kind) -> {exp: record}
    for who in FORECASTERS:
        for path in sorted((CF / "forecasts" / who).glob("*.num.json")):
            r = json.loads(path.read_text())
            if not r.get("parsed"):
                continue
            e, k, x = r["exp"], r["kind"], r["parsed"]
            assert (e, k) not in DROP_ARMS
            pt = to_carry(e, x["estimate"])
            lo, hi = sorted((to_carry(e, x["low"]), to_carry(e, x["high"])))
            if who == "jev":
                dist, dist_src = jev_dist(e, x["distribution"], edges), "own"
            else:
                dist, dist_src = implied_dist(pt, lo, hi, edges), "implied"
            fc.setdefault((who, k), {})[e] = {
                "raw": {"estimate": x["estimate"], "low": x["low"], "high": x["high"]},
                "point": pt, "low": lo, "high": hi, "band": band(pt, edges),
                "interval_bands": [band(lo, edges), band(hi, edges)],
                "dist": dist, "dist_src": dist_src,
            }  # fmt: skip
    return obs, fc


def uncertain_band(e: str, obs: dict, edges=EDGES) -> bool:
    ci = MEASURED_CI[e]
    if ci is None:
        return min(abs(obs[e] - x) for x in edges) < NEAR
    a, b = sorted((to_carry(e, ci[0]), to_carry(e, ci[1])))
    return band(a, edges) != band(b, edges)


def base_rate(e: str, obs: dict, edges=EDGES) -> list:
    others = [band(v, edges) for q, v in obs.items() if q != e]
    return [others.count(j) / len(others) for j in range(5)]


def mode_hit(p: list, k: int, groups=None) -> float:
    """Expected hit of the modal category of p (ties split evenly); groups maps bands to directions when given."""
    if groups is not None:
        q = [0.0] * 3
        for j, x in enumerate(p):
            q[groups[j]] += x
        p, k = q, groups[k]
    m = max(p)
    ties = [j for j, x in enumerate(p) if abs(x - m) < 1e-12]
    return (k in ties) / len(ties)


def score_cell(d: dict, obs: dict, edges=EDGES, skip=()) -> dict:
    qs = [e for e in sorted(d) if e not in skip]
    if not qs:
        return {"n": 0}
    kb = {e: band(obs[e], edges) for e in qs}
    out = {"n": len(qs), "questions": qs}
    out["band_hits"] = sum(d[e]["band"] == kb[e] for e in qs)
    out["dir_hits"] = sum(DIR_OF[d[e]["band"]] == DIR_OF[kb[e]] for e in qs)
    out["interval_spans_band"] = sum(d[e]["interval_bands"][0] <= kb[e] <= d[e]["interval_bands"][1] for e in qs)
    out["rps_point"] = st.mean(rps(onehot(d[e]["band"]), kb[e]) for e in qs)
    out["rps_dist"] = st.mean(rps(d[e]["dist"], kb[e]) for e in qs)
    out["dist_src"] = d[qs[0]]["dist_src"]
    out["mae"] = st.mean(abs(d[e]["point"] - obs[e]) for e in qs)
    out["mean_signed_error"] = st.mean(d[e]["point"] - obs[e] for e in qs)
    br = {e: base_rate(e, obs, edges) for e in qs}
    loo_mean = {e: st.mean(v for q, v in obs.items() if q != e) for e in qs}
    out["no_change"] = {
        "band_hits": sum(kb[e] == 2 for e in qs),
        "dir_hits": sum(DIR_OF[kb[e]] == 1 for e in qs),
        "rps": st.mean(rps(onehot(2), kb[e]) for e in qs),
        "mae": st.mean(abs(1 - obs[e]) for e in qs),
    }
    out["base_rate"] = {
        "band_hits": sum(mode_hit(br[e], kb[e]) for e in qs),
        "dir_hits": sum(mode_hit(br[e], kb[e], DIR_OF) for e in qs),
        "rps": st.mean(rps(br[e], kb[e]) for e in qs),
        "mae": st.mean(abs(loo_mean[e] - obs[e]) for e in qs),
    }
    # paired against the base rate's modal band, per question: forecaster hit and base rate missed, and the reverse
    out["vs_base_rate_band"] = {
        "only_forecaster": sum((d[e]["band"] == kb[e]) * (1 - mode_hit(br[e], kb[e])) for e in qs),
        "only_base_rate": sum((d[e]["band"] != kb[e]) * mode_hit(br[e], kb[e]) for e in qs),
    }
    out["vs_base_rate_rps_wins"] = sum(rps(d[e]["dist"], kb[e]) < rps(br[e], kb[e]) for e in qs)
    return out


def pooled(fc: dict, who: str) -> dict:
    """All contexts of one forecaster as one cell (the same questions repeat across contexts)."""
    d = {}
    for k in KINDS:
        for e, r in fc.get((who, k), {}).items():
            d[f"{e}|{k}"] = r
    return d


def score_pooled(d: dict, obs: dict, edges=EDGES) -> dict:
    o = {key: obs[key.split("|")[0]] for key in d}
    # base rates and leave-one-out means must leave out the question, not the (question, context) cell
    res = score_cell({k: v for k, v in d.items()}, {**o}, edges)
    qs = sorted(d)
    kb = {q: band(o[q], edges) for q in qs}
    br = {q: base_rate(q.split("|")[0], obs, edges) for q in qs}
    res["base_rate"] = {
        "band_hits": sum(mode_hit(br[q], kb[q]) for q in qs),
        "dir_hits": sum(mode_hit(br[q], kb[q], DIR_OF) for q in qs),
        "rps": st.mean(rps(br[q], kb[q]) for q in qs),
        "mae": st.mean(abs(st.mean(v for e, v in obs.items() if e != q.split("|")[0]) - o[q]) for q in qs),
    }
    res["vs_base_rate_band"] = {
        "only_forecaster": sum((d[q]["band"] == kb[q]) * (1 - mode_hit(br[q], kb[q])) for q in qs),
        "only_base_rate": sum((d[q]["band"] != kb[q]) * mode_hit(br[q], kb[q]) for q in qs),
    }
    res["vs_base_rate_rps_wins"] = sum(rps(d[q]["dist"], kb[q]) < rps(br[q], kb[q]) for q in qs)
    res["distinct_questions"] = len({q.split("|")[0] for q in qs})
    return res


def check_mae(fc: dict, obs: dict) -> list:
    old = json.loads((CF / "scores.json").read_text())
    bad = []
    for r in old["rows"]:
        d = fc[(r["who"], r["kind"])]
        mae = st.mean(abs(d[e]["point"] - obs[e]) for e in d)
        if abs(mae - r["mae"]) > 1e-9 or len(d) != r["n"]:
            bad.append((r["who"], r["kind"], mae, r["mae"]))
    return bad


def run(edges=EDGES, skip=()):
    obs, fc = load(edges)
    cells = []
    for who in FORECASTERS:
        for k in KINDS:
            if (who, k) in fc:
                cells.append({"who": who, "kind": k, **score_cell(fc[(who, k)], obs, edges, skip)})
        if not skip:
            cells.append({"who": who, "kind": "all", **score_pooled(pooled(fc, who), obs, edges)})
    return obs, fc, cells


def frac(a, n):
    return f"{a:g}/{n}"


def table(cells: list, title: str) -> str:
    lines = [f"### {title}", "",
             "| forecaster | context | n | band hit | direction hit | RPS (distribution) | RPS (point as sure bet) | "
             "80% interval spans band | mean error | base rate: band / direction / RPS / mean error | "
             "no change: band / direction / RPS / mean error |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for c in cells:
        if not c.get("n"):
            continue
        b, z = c["base_rate"], c["no_change"]
        n = c["n"]
        lines.append(
            f"| {FORECASTERS[c['who']]} | {KIND_NAME.get(c['kind'], 'all four pooled')} | {n} | "
            f"{frac(c['band_hits'], n)} | {frac(c['dir_hits'], n)} | {c['rps_dist']:.3f} ({c['dist_src']}) | "
            f"{c['rps_point']:.3f} | {frac(c['interval_spans_band'], n)} | {c['mae']:.3f} | "
            f"{frac(round(b['band_hits'], 2), n)} / {frac(round(b['dir_hits'], 2), n)} / {b['rps']:.3f} / {b['mae']:.3f} | "
            f"{frac(z['band_hits'], n)} / {frac(z['dir_hits'], n)} / {z['rps']:.3f} / {z['mae']:.3f} |"
        )
    return "\n".join(lines)


def main():
    obs, fc, cells = run()
    bad = check_mae(fc, obs)
    assert not bad, f"mean errors differ from score_carry.py: {bad}"
    unc = {e: uncertain_band(e, obs) for e in obs}
    skip = tuple(e for e, u in unc.items() if u)
    _, _, cells_certain = run(skip=skip)
    sens = {}
    for name, edges in (("middle +-0.05", (0.5, 0.95, 1.05, 1.5)), ("middle +-0.15", (0.5, 0.85, 1.15, 1.5))):
        o2, _, c2 = run(edges)
        sens[name] = {"edges": edges, "measured_bands": {e: BANDS[band(v, edges)] for e, v in o2.items()},
                      "cells": c2}  # fmt: skip

    measured = {
        e: {
            "short": SHORT[e], "symbol": CARRY[e]["symbol"], "asked_as": CARRY[e]["ask"],
            "to_carry": CARRY[e]["to_carry"], "observed_raw": CARRY[e]["observed"], "carry": round(obs[e], 4),
            "band": BANDS[band(obs[e])], "direction": DIRS[DIR_OF[band(obs[e])]],
            "ci_raw": MEASURED_CI[e], "ci_carry": None if MEASURED_CI[e] is None else
            sorted(round(to_carry(e, x), 4) for x in MEASURED_CI[e]),
            "band_uncertain": unc[e], "parts": PARTS[e], "source": CARRY[e]["source"],
        }
        for e in sorted(obs, key=lambda q: obs[q])
    }  # fmt: skip
    claude = {e: {"point": to_carry(e, c["value"]), "band": BANDS[band(to_carry(e, c["value"]))],
                  "hit": band(to_carry(e, c["value"])) == band(obs[e]), "quote": c["quote"]}
              for e, c in CLAUDE_POINT.items()}  # fmt: skip
    per_forecast = []
    for (who, k), d in sorted(fc.items()):
        for e, r in sorted(d.items()):
            kb = band(obs[e])
            per_forecast.append({
                "who": who, "kind": k, "exp": e, "raw": r["raw"], "point": round(r["point"], 4),
                "low": round(r["low"], 4), "high": round(r["high"], 4), "band": BANDS[r["band"]],
                "measured_band": BANDS[kb], "band_hit": r["band"] == kb, "dir_hit": DIR_OF[r["band"]] == DIR_OF[kb],
                "interval_bands": [BANDS[i] for i in r["interval_bands"]],
                "p_bands": [round(x, 4) for x in r["dist"]], "p_src": r["dist_src"],
                "rps_dist": round(rps(r["dist"], kb), 4), "abs_error": round(abs(r["point"] - obs[e]), 4),
            })  # fmt: skip
    out = {
        "edges": EDGES, "bands": BANDS, "directions": DIRS,
        "rps_note": "ranked probability score over the five ordered bands, divided by 4 (0 perfect, 1 all mass on the "
        "far band); Sol and Luna gave a point and an 80% interval only, so their distribution is a two-piece normal "
        "fitted to them (implied); Jev's is its own 22-bin answer summed into bands",
        "measured": measured, "cells": cells, "cells_certain_bands_only": cells_certain,
        "uncertain_band_questions": list(skip), "sensitivity": sens, "claude_registered": claude,
        "per_forecast": per_forecast,
    }  # fmt: skip
    (HERE / "bands.json").write_text(json.dumps(out, indent=1))

    # page data for the Predictions tab (spec in README.md)
    view = {
        "edges": EDGES, "bands": BANDS, "directions": DIRS,
        "explain": {
            "band hit": "the forecast's point falls in the same band as the measured value",
            "direction hit": "the point and the measured value agree on drop / no change / rise",
            "RPS": "how far the forecaster's probabilities over the five bands sit from the measured band, 0 best, "
                   "1 worst; for Sol and Luna fitted to their 80% range",
            "base rate": "a forecaster who always names the most common band of the other measured results",
            "mean error": "average distance between the point and the measured carry (the old ranking)",
        },
        "main": [
            {"who": FORECASTERS[c["who"]], "context": KIND_NAME.get(c["kind"], "all four pooled"), "n": c["n"],
             "band_hit": [c["band_hits"], c["n"]], "direction_hit": [c["dir_hits"], c["n"]],
             "rps": round(c["rps_dist"], 3), "rps_source": c["dist_src"],
             "base_rate": {"band_hit": [round(c["base_rate"]["band_hits"], 2), c["n"]],
                           "direction_hit": [round(c["base_rate"]["dir_hits"], 2), c["n"]],
                           "rps": round(c["base_rate"]["rps"], 3)},
             "no_change": {"band_hit": [c["no_change"]["band_hits"], c["n"]],
                           "direction_hit": [c["no_change"]["dir_hits"], c["n"]],
                           "rps": round(c["no_change"]["rps"], 3)},
             "mean_error": round(c["mae"], 3), "questions": c["questions"]}
            for c in cells
        ],
        "questions": [
            {"id": e, "short": m["short"], "measured_carry": m["carry"], "band": m["band"], "direction": m["direction"],
             "interval_carry": m["ci_carry"], "band_uncertain": m["band_uncertain"],
             "forecasts": [{"who": FORECASTERS[p["who"]], "context": KIND_NAME[p["kind"]], "point": p["point"],
                            "range80": [p["low"], p["high"]], "band": p["band"], "p_bands": p["p_bands"],
                            "p_src": p["p_src"]}
                           for p in per_forecast if p["exp"] == e]}
            for e, m in measured.items()
        ],
        "one_result_is_worth": "1/n of a hit rate: 10 to 14 percentage points in a context cell",
    }  # fmt: skip
    (HERE / "bands_view.json").write_text(json.dumps(view, indent=1, ensure_ascii=False))

    print("measured carries, low to high:")
    for e, m in measured.items():
        print(f"  {e:20s} {m['carry']:7.3f}  {m['band']:9s}  CI {m['ci_carry']}  uncertain band: {m['band_uncertain']}")
    print()
    print(table(cells, "Main edges 0.5 / 0.9 / 1.1 / 1.5"))
    print()
    print(table(cells_certain, f"Only questions with a certain measured band (leaves out {', '.join(skip)})"))
    for name, s in sens.items():
        print()
        print(table([c for c in s["cells"] if c["kind"] == "all"], f"Sensitivity: {name}, edges {s['edges']}"))
    print()
    print("Claude registered point:", claude)


if __name__ == "__main__":
    main()
