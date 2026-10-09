"""Scores Sol, Luna, Jev and Haiku 5.5 on every condition Opus 5.5 was run on (ask_models.py), with the statistics
score_opus.py and score_named.py give Opus, plus paired per-question differences of each version against the same
model's a (na) and against a's repeat (na-r2), as mean +- standard error over questions (sd / sqrt(n)), the README's
convention.

Carry: models_out/<model>/<target>__<version>__<effort>[-r2].txt -> models_scores.json
Named: named_models_out/<model>/<q>__<version>__<effort>[-r2].txt -> named_models_scores.json
       (log loss = -ln max(p(outcome), 0.001); top choice right with ties split; mean p(outcome))
Also predictions_view_models.json: the Predictions view's row shapes (bands.json rows for carry, extra.json's
opus_named entries for named), with the prompts as chunk ids and the chunk texts.

    python3 experiments/2026-10-09-band-scores/score_models.py
"""

import hashlib
import json
import math
import statistics as st
from pathlib import Path

from band_prompt import BANDS, parse_bands
from score_bands import DIR_OF, band, mode_hit, rps, to_carry
from score_named import parse as parse_named
from score_opus import VARIANT, baselines, score

HERE = Path(__file__).resolve().parent
MODELS = {"gpt-6.1-sol": "GPT-6.1 Sol", "gpt-6-luna": "GPT-6 Luna", "jev": "Jev", "claude-haiku-5-5": "Claude Haiku 5.5"}
NVARIANT = {"na": "Sol's prompt", "nb": "+ other questions' outcomes", "np": "+ the paper's results"}


def lenient_bands(raw):
    """Fallback when the closing JSON is broken (Haiku writes unescaped quotes inside "reason"): the last "p_bands"
    object and the last "estimate" number, checked as parse_bands checks them. Every use is listed in the scores."""
    import re

    pb = list(re.finditer(r'"p_bands"\s*:\s*(\{[^{}]*\})', raw or ""))
    es = list(re.finditer(r'"estimate"\s*:\s*(-?\d+(?:\.\d+)?)', raw or ""))
    if not pb or not es:
        return None
    try:
        p = json.loads(pb[-1].group(1))
    except ValueError:
        return None
    if set(p) != set(BANDS) or any(float(p[b]) < 0 for b in BANDS) or abs(sum(float(p[b]) for b in BANDS) - 1) > 0.02:
        return None
    z = sum(float(p[b]) for b in BANDS)
    return {"p_bands": {b: float(p[b]) / z for b in BANDS}, "estimate": float(es[-1].group(1)), "reason": None}


def lenient_named(raw, labels):
    import re

    m = list(re.finditer(r'"probabilities"\s*:\s*(\{[^{}]*\})', raw or ""))
    return parse_named('{"probabilities": ' + m[-1].group(1) + "}", labels) if m else None


LENIENT = []


def pm(xs):
    xs = list(xs)
    return {"mean": st.mean(xs), "se": st.stdev(xs) / math.sqrt(len(xs)), "n": len(xs)}


def fmt(d):
    return f"{d['mean']:+.3f} +- {d['se']:.3f}"


# ------------------------------------------------------------------ carry
def load_carry():
    out, bad = {}, []
    for md in MODELS:
        for p in sorted((HERE / "models_out" / md).glob("*__*__*.txt")):
            e, v, eff = p.stem.split("__")
            raw = p.read_text()
            d = parse_bands(raw)
            if d is None:
                d = lenient_bands(raw)
                if d is not None:
                    LENIENT.append(f"{md}/{p.name}")
            if d is None:
                bad.append(f"{md}/{p.name}")
                continue
            dist = [d["p_bands"][b] for b in BANDS]
            out.setdefault((md, v, eff), {})[e] = {"dist": dist, "point": to_carry(e, d["estimate"]), "raw": d["estimate"],
                                                   "reason": d.get("reason"), "text": raw}  # fmt: skip
    return out, bad


def carry_main():
    targets = {t["id"]: t for t in json.loads((HERE / "targets.json").read_text())}
    obs = {e: t["carry"] for e, t in targets.items()}
    uncertain = {e for e, t in targets.items() if t["band_uncertain"]}
    qs = sorted(obs)
    cells, bad = load_carry()
    res = {"bad_parses": bad, "lenient_parses": list(LENIENT), "variants": VARIANT, "uncertain_band_questions": sorted(uncertain), "cells": []}
    per_rps = {}
    for (md, v, eff), cell in sorted(cells.items()):
        missing = sorted(set(qs) - set(cell))
        s = score(cell, obs, uncertain) if not missing else None
        if s is None:
            res["cells"].append({"model": md, "variant": v, "effort": eff, "missing": missing})
            continue
        per_rps[(md, v, eff)] = {e: rps(cell[e]["dist"], band(obs[e])) for e in qs}
        res["cells"].append({"model": md, "variant": v, "effort": eff, **s,
                             "certain_only": score(cell, obs, uncertain, uncertain)})  # fmt: skip
    # paired per-question RPS differences against the model's own a and a's repeat
    for c in res["cells"]:
        if "missing" in c:
            continue
        md, v, eff = c["model"], c["variant"], c["effort"]
        std = eff.replace("-r2", "")
        base = "low" if md == "claude-haiku-5-5" else std
        a, a2 = per_rps.get((md, "a", base)), per_rps.get((md, "a", base + "-r2"))
        me = per_rps[(md, v, eff)]
        if a and (v, eff) != ("a", base):
            c["rps_vs_a"] = pm(me[e] - a[e] for e in qs)
        if a2 and (v, eff) != ("a", base + "-r2"):
            c["rps_vs_a_r2"] = pm(me[e] - a2[e] for e in qs)
    res["baselines"] = baselines(obs, qs)
    (HERE / "models_scores.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print("carry bad parses:", bad, "lenient:", LENIENT)
    print(f"{'model':<18} {'version':<10} {'band':>5} {'dir':>4} {'RPS':>6} {'MAE':>6} {'bias':>7} {'ptband':>6} | vs a | vs a-r2")
    for c in res["cells"]:
        if "missing" in c:
            print(c["model"], c["variant"], c["effort"], "MISSING", c["missing"])
            continue
        print(f"{c['model']:<18} {c['variant'] + ' ' + c['effort']:<10} {c['band_hits']:>5.1f} {c['dir_hits']:>4.1f} "
              f"{c['rps']:>6.3f} {c['mae']:>6.3f} {c['mean_signed_error']:>+7.3f} {c['point_band_hits']:>6} | "
              f"{fmt(c['rps_vs_a']) if 'rps_vs_a' in c else '':<16} | {fmt(c['rps_vs_a_r2']) if 'rps_vs_a_r2' in c else ''}")  # fmt: skip
    return cells, obs, targets


# ------------------------------------------------------------------ named
def loss(p):
    return -math.log(max(p, 1e-3))


def nmode_hit(p, k):
    m = max(p.values())
    ties = [l for l, v in p.items() if abs(v - m) < 1e-12]
    return (k in ties) / len(ties)


def load_named(T):
    lab = {t["id"]: t["labels"] for t in T}
    out, bad = {}, []
    for md in MODELS:
        for p in sorted((HERE / "named_models_out" / md).glob("*__*__*.txt")):
            e, v, eff = p.stem.split("__")
            raw = p.read_text()
            d = parse_named(raw, lab[e])
            if d is None:
                d = lenient_named(raw, lab[e])
                if d is not None:
                    LENIENT.append(f"{md}/{p.name}")
            if d is None:
                bad.append(f"{md}/{p.name}")
                continue
            out.setdefault((md, v, eff), {})[e] = {"p": d, "text": raw}
    return out, bad


def named_main():
    T = json.loads((HERE / "named_targets.json").read_text())
    outc = {t["id"]: t["outcome"] for t in T}
    qs = sorted(outc)
    cells, bad = load_named(T)
    res = {"bad_parses": bad, "lenient_parses": [x for x in LENIENT if x.split("/")[1].split("__")[1].startswith("n")], "variants": NVARIANT, "rows": []}
    L = {}
    for (md, v, eff), per in sorted(cells.items()):
        missing = sorted(set(qs) - set(per))
        if missing:
            res["rows"].append({"model": md, "variant": v, "effort": eff, "missing": missing})
            continue
        L[(md, v, eff)] = {e: loss(per[e]["p"].get(outc[e], 0.0)) for e in qs}
        res["rows"].append({
            "model": md, "variant": v, "effort": eff, "n": len(qs), "log_loss": st.mean(L[(md, v, eff)].values()),
            "top_right": sum(nmode_hit(per[e]["p"], outc[e]) for e in qs),
            "p_outcome": st.mean(per[e]["p"].get(outc[e], 0.0) for e in qs),
            "uniform": st.mean(math.log(len(t["labels"])) for t in T), "per_question": L[(md, v, eff)],
        })  # fmt: skip
    for r in res["rows"]:
        if "missing" in r:
            continue
        md, v, eff = r["model"], r["variant"], r["effort"]
        base = eff.replace("-r2", "")
        if md == "claude-haiku-5-5":
            base = "low"
        a, a2 = L.get((md, "na", base)), L.get((md, "na", base + "-r2"))
        me = L[(md, v, eff)]
        if a and (v, eff) != ("na", base):
            r["vs_na"] = pm(me[e] - a[e] for e in qs)
        if a2 and (v, eff) != ("na", base + "-r2"):
            r["vs_na_r2"] = pm(me[e] - a2[e] for e in qs)
        if a and a2 and v != "na":
            r["vs_na_mean"] = pm(me[e] - (a[e] + a2[e]) / 2 for e in qs)
    (HERE / "named_models_scores.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print("\nnamed bad parses:", bad)
    print(f"{'model':<18} {'version':<14} {'logloss':>8} {'top':>5} {'p(out)':>7} | vs na | vs na-r2 | vs na mean")
    for r in res["rows"]:
        if "missing" in r:
            print(r["model"], r["variant"], r["effort"], "MISSING", r["missing"])
            continue
        print(f"{r['model']:<18} {r['variant'] + ' ' + r['effort']:<14} {r['log_loss']:>8.3f} {r['top_right']:>5.1f} "
              f"{r['p_outcome']:>7.3f} | {fmt(r['vs_na']) if 'vs_na' in r else '':<16} | "
              f"{fmt(r['vs_na_r2']) if 'vs_na_r2' in r else '':<16} | {fmt(r['vs_na_mean']) if 'vs_na_mean' in r else ''}")  # fmt: skip
    return cells, T


# ------------------------------------------------------------------ view data
chunks = {}


def chunk_ids(text):
    ids = []
    for part in str(text or "").split("\n\n"):
        k = hashlib.sha1(part.encode()).hexdigest()[:10]
        chunks[k] = part
        ids.append(k)
    return ids


def view(ccells, obs, ncells, T):
    order = sorted(obs, key=lambda e: obs[e])
    label_eff = lambda md, eff: ("" if eff.replace("-r2", "") in ("medium", "none") or md == "claude-haiku-5-5" and eff.startswith("low")
                                 else f", {eff.replace('-r2', '')} effort") + (", asked again" if eff.endswith("-r2") else "")  # fmt: skip
    rows = []
    for (md, v, eff), cell in sorted(ccells.items()):
        if sorted(cell) != sorted(obs):
            continue
        per = {}
        for e in order:
            x = cell[e]
            per[e] = {"p": [round(y, 4) for y in x["dist"]], "point": x["raw"], "pc": round(x["point"], 4),
                      "band": max(range(5), key=lambda j: x["dist"][j]), "band_hit": max(range(5), key=lambda j: x["dist"][j]) == band(obs[e]),
                      "rps": round(rps(x["dist"], band(obs[e])), 4), "reason": x["reason"],
                      "prompt": chunk_ids((HERE / "loo_prompts" / e / f"{v}.txt").read_text()), "raw": x["text"], "src": "own"}  # fmt: skip
        qs = list(per)
        kb = {e: band(obs[e]) for e in qs}
        sc = {"n": len(qs), "band": sum(mode_hit(cell[e]["dist"], kb[e]) for e in qs),
              "dir": sum(mode_hit(cell[e]["dist"], kb[e], DIR_OF) for e in qs),
              "rps": round(st.mean(rps(cell[e]["dist"], kb[e]) for e in qs), 3)}  # fmt: skip
        rows.append({"key": f"{md}-{v}-{eff}", "who": MODELS[md], "model": md, "effort": eff, "variant": v,
                     "group": md, "label": VARIANT[v] + label_eff(md, eff), "by": "mode", "per": per, "score": sc})  # fmt: skip
    outc = {t["id"]: t["outcome"] for t in T}
    named = []
    for (md, v, eff), per in sorted(ncells.items()):
        if sorted(per) != sorted(outc):
            continue
        prompt_v = v
        named.append({"key": f"{md}-{v}-{eff}", "who": MODELS[md], "model": md, "variant": v, "effort": eff,
                      "label": NVARIANT[v] + (f" ({eff.split('-')[0]})" if md == "jev" else label_eff(md, eff)),
                      "per": {e: {"p": per[e]["p"], "p_outcome": round(per[e]["p"].get(outc[e], 0.0), 4),
                                  "log_loss": round(loss(per[e]["p"].get(outc[e], 0.0)), 4),
                                  "prompt": chunk_ids((HERE / "named_prompts" / e / f"{prompt_v}.txt").read_text()),
                                  "raw": per[e]["text"]} for e in sorted(per)}})  # fmt: skip
    out = {"built": "2026-10-09", "note": "Sol, Luna, Jev and Haiku 5.5 on every prompt version Opus 5.5 had "
           "(SPAR experiments/2026-10-09-band-scores, ask_models.py, score_models.py). carry_rows are shaped like "
           "views/predictions/bands.json rows (per question: p over the five bands, point in the asked units, pc = point "
           "as a carry, band = modal band, band_hit, rps, prompt chunk ids, raw answer); named_rows like extra.json's "
           "opus_named (per question: p over the named outcomes, p_outcome, log_loss, prompt chunk ids, raw). Jev's "
           "carry point is its band distribution's median; Jev named has two rows per version (choice, noul).",
           "bands": BANDS, "carry_rows": rows, "named_rows": named, "chunks": chunks}  # fmt: skip
    (HERE / "predictions_view_models.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"\nview: {len(rows)} carry rows, {len(named)} named rows, {len(chunks)} chunks")


if __name__ == "__main__":
    cc, obs, _ = carry_main()
    nc, T = named_main()
    view(cc, obs, nc, T)
