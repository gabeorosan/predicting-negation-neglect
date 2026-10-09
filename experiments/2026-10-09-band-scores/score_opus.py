"""Scores the leave-one-out Opus 5.5 band forecasts (opus_out/<target>__<variant>__<effort>.txt) on the same ten
resolved carries as score_bands.py, beside the earlier forecasters (bands.json cells) and the two baselines.

Prompt versions (loo_prompts/<target>/<v>.txt, built by make_loo_prompts.py / make_variants.py):
    a  Sol's original prompt (the context it scored best in)        b  a + every other target with its forecasts and outcome
    d  a + the three most similar other targets                      e  a + verbatim training documents and readout prompts
    f  a with the calibration pack replaced by sampled answers       g  b + forecast the numerator and denominator first
    h  b + the earlier forecasters' mean signed error

Each answer gives five band probabilities and a point estimate in the asked quantity's units (phi_F and r_neutral(F)
are removal shares: carry = 1 - x; their p_bands are already in carry band order, see band_prompt.ranges).

    python3 experiments/2026-10-09-band-scores/score_opus.py     # writes opus_scores.json, prints the table
"""

import json
import statistics as st
from pathlib import Path

from band_prompt import BANDS, parse_bands
from score_bands import DIR_OF, base_rate, band, mode_hit, rps, to_carry

HERE = Path(__file__).resolve().parent
VARIANT = {
    "a": "Sol's prompt",
    "b": "+ all other targets and outcomes",
    "d": "+ 3 most similar targets",
    "e": "+ verbatim documents and prompts",
    "f": "sampled answers for calibration",
    "g": "+ all targets, numerator/denominator first",
    "h": "+ all targets, earlier forecasters' bias",
    "p": "+ the paper's results",
}


def load_opus():
    out, bad = {}, []
    for p in sorted((HERE / "opus_out").glob("*.txt")):
        e, v, eff = p.stem.split("__")
        d = parse_bands(p.read_text())
        if d is None:
            bad.append(p.name)
            continue
        dist = [d["p_bands"][b] for b in BANDS]
        out.setdefault((v, eff), {})[e] = {"dist": dist, "point": to_carry(e, d["estimate"]), "raw": d["estimate"]}
    return out, bad


def score(cell: dict, obs: dict, uncertain: set, skip=()) -> dict:
    qs = [e for e in sorted(cell) if e not in skip]
    kb = {e: band(obs[e]) for e in qs}
    r = {"n": len(qs)}
    r["band_hits"] = sum(mode_hit(cell[e]["dist"], kb[e]) for e in qs)
    r["dir_hits"] = sum(mode_hit(cell[e]["dist"], kb[e], DIR_OF) for e in qs)
    r["point_band_hits"] = sum(band(cell[e]["point"]) == kb[e] for e in qs)
    r["point_dir_hits"] = sum(DIR_OF[band(cell[e]["point"])] == DIR_OF[kb[e]] for e in qs)
    r["rps"] = st.mean(rps(cell[e]["dist"], kb[e]) for e in qs)
    r["mae"] = st.mean(abs(cell[e]["point"] - obs[e]) for e in qs)
    r["mean_signed_error"] = st.mean(cell[e]["point"] - obs[e] for e in qs)
    r["rps_wins_vs_base_rate"] = sum(rps(cell[e]["dist"], kb[e]) < rps(base_rate(e, obs), kb[e]) for e in qs)
    r["per_question"] = {
        e: {
            "measured_band": BANDS[kb[e]],
            "modal_band": BANDS[max(range(5), key=lambda j: cell[e]["dist"][j])],
            "p_measured_band": round(cell[e]["dist"][kb[e]], 3),
            "point_carry": round(cell[e]["point"], 3),
            "rps": round(rps(cell[e]["dist"], kb[e]), 4),
        }
        for e in qs
    }
    return r


def baselines(obs: dict, qs: list) -> dict:
    kb = {e: band(obs[e]) for e in qs}
    br = {e: base_rate(e, obs) for e in qs}
    return {
        "no_change": {
            "band_hits": sum(kb[e] == 2 for e in qs),
            "dir_hits": sum(DIR_OF[kb[e]] == 1 for e in qs),
            "rps": st.mean(rps([0, 0, 1, 0, 0], kb[e]) for e in qs),
        },
        "base_rate": {
            "band_hits": sum(mode_hit(br[e], kb[e]) for e in qs),
            "dir_hits": sum(mode_hit(br[e], kb[e], DIR_OF) for e in qs),
            "rps": st.mean(rps(br[e], kb[e]) for e in qs),
        },
    }


def main():
    targets = {t["id"]: t for t in json.loads((HERE / "targets.json").read_text())}
    obs = {e: t["carry"] for e, t in targets.items()}
    for e, t in targets.items():
        assert abs(to_carry(e, t["measured"]) - t["carry"]) < 1e-9, e
    uncertain = {e for e, t in targets.items() if t["band_uncertain"]}
    opus, bad = load_opus()
    qs = sorted(obs)
    res = {"bad_parses": bad, "uncertain_band_questions": sorted(uncertain), "variants": VARIANT, "cells": []}
    for (v, eff), cell in sorted(opus.items()):
        assert sorted(cell) == qs, (v, eff, sorted(set(qs) - set(cell)))
        res["cells"].append(
            {"variant": v, "effort": eff, **score(cell, obs, uncertain), "certain_only": score(cell, obs, uncertain, uncertain)}
        )
    res["baselines"] = baselines(obs, qs)
    res["baselines_certain_only"] = baselines(obs, [e for e in qs if e not in uncertain])
    earlier = json.loads((HERE / "bands.json").read_text())["cells"]
    res["earlier_context_A"] = [
        {k: c[k] for k in ("who", "kind", "n", "band_hits", "dir_hits", "rps_dist", "mae", "mean_signed_error")}
        for c in earlier
        if c["kind"] in ("A", "D") and c["n"] >= 9
    ]
    (HERE / "opus_scores.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))

    print(f"bad parses: {bad}")
    print(f"{'cell':<48} {'band':>5} {'dir':>5} {'RPS':>6} {'MAE':>6} {'bias':>6} {'beats BR':>8} | certain only (n=6)")
    for c in res["cells"]:
        k = c["certain_only"]
        name = f"Opus {c['effort']}, {c['variant']}: {VARIANT[c['variant']]}"
        print(
            f"{name:<48} {c['band_hits']:>5.1f} {c['dir_hits']:>5.1f} {c['rps']:>6.3f} {c['mae']:>6.3f} "
            f"{c['mean_signed_error']:>+6.3f} {c['rps_wins_vs_base_rate']:>8} | {k['band_hits']:.1f} {k['dir_hits']:.1f} {k['rps']:.3f}"
        )
    for c in res["earlier_context_A"]:
        print(f"{c['who'] + ' context ' + c['kind']:<48} {c['band_hits']:>5} {c['dir_hits']:>5} {c['rps_dist']:>6.3f} {c['mae']:>6.3f} {c['mean_signed_error']:>+6.3f}")
    for k, b in res["baselines"].items():
        kc = res["baselines_certain_only"][k]
        print(f"{k:<48} {b['band_hits']:>5.1f} {b['dir_hits']:>5.1f} {b['rps']:>6.3f} {'':>6} {'':>6} {'':>8} | {kc['band_hits']:.1f} {kc['dir_hits']:.1f} {kc['rps']:.3f}")


if __name__ == "__main__":
    main()
