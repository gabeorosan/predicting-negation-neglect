"""score: per item, per arm and variant, overall and by experiment, measure, role and tier."""

import json
import math

from .stats import (
    bootstrap_correlations,
    correlations,
    kendall_distance,
    mean,
    needed_factor,
    sample_var,
    widening_factor,
    wilson,
    winkler,
)
from .study import Study, StudyError, write_json

EPS = 1e-12


def to01(v, rng):
    lo, hi = rng
    return (min(max(float(v), lo), hi) - lo) / (hi - lo)


def load_predictions(study: Study):
    recs = []
    pdir = study.dir / "predictions"
    if not pdir.exists():
        return recs
    for f in sorted(pdir.glob("*/*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        rec["_arm_dir"] = f.parent.name
        rec["_file"] = f
        recs.append(rec)
    return recs


def item_metrics(act, ans):
    """Scores of one answer to one item against its actual (0-1 scale), or None if the item was not measured."""
    if act["kind"] == "ranking":
        if not act.get("ranking") or not isinstance(ans, list):
            return None
        return {"kd": kendall_distance(ans, act["condition_means"])}
    if act["mean"] is None or not isinstance(ans, dict) or "point" not in ans:
        return None
    rng = act["range"]
    a = to01(act["mean"], rng)
    p = to01(ans["point"], rng)
    m = {"p": p, "a": a, "se": abs(p - a), "sq": (p - a) ** 2}
    if ans.get("lo") is not None and ans.get("hi") is not None:
        lo, hi = to01(ans["lo"], rng), to01(ans["hi"], rng)
        m.update(lo=lo, hi=hi, hit=lo - EPS <= a <= hi + EPS, below=a < lo - EPS, above=a > hi + EPS,
                 width=hi - lo, winkler=winkler(lo, hi, a), need=needed_factor(p, lo, hi, a))
    return m


def average_answer(answers):
    if isinstance(answers[0], list):
        return None  # rankings are not averaged
    out = {"point": mean(a["point"] for a in answers)}
    iv = [a for a in answers if a.get("lo") is not None and a.get("hi") is not None]
    if len(iv) == len(answers):
        out["lo"] = mean(a["lo"] for a in iv)
        out["hi"] = mean(a["hi"] for a in iv)
    return out


def aggregate(rows, n_boot, seed):
    """rows: list of (item id, metrics). Means, correlations with bootstrap intervals, interval and ranking scores."""
    num = [m for _, m in rows if "se" in m]
    out = {"n_items": len(num)}
    if num:
        out["mean_scaled_error"] = mean(m["se"] for m in num)
        out["mean_squared_error"] = mean(m["sq"] for m in num)
        p, a = [m["p"] for m in num], [m["a"] for m in num]
        if n_boot:
            out["correlations"] = bootstrap_correlations(p, a, n_boot, seed)
        else:
            out["correlations"] = {k: {"est": v, "lo": None, "hi": None} for k, v in correlations(p, a).items()}
    iv = [m for m in num if "hit" in m]
    if iv:
        k = sum(m["hit"] for m in iv)
        wl, wh = wilson(k, len(iv))
        out["intervals"] = {
            "n": len(iv),
            "coverage": k / len(iv),
            "coverage_wilson95": [wl, wh],
            "miss_below": sum(m["below"] for m in iv) / len(iv),
            "miss_above": sum(m["above"] for m in iv) / len(iv),
            "mean_width": mean(m["width"] for m in iv),
            "winkler": mean(m["winkler"] for m in iv),
            "widening_factor": widening_factor([(m["p"], m["lo"], m["hi"], m["a"]) for m in iv]),
        }
    rk = [m for _, m in rows if m.get("kd") is not None]
    if rk:
        out["ranking"] = {"n": len(rk), "mean_kendall_distance": mean(m["kd"] for m in rk)}
    return out


def _mean_of_aggs(aggs):
    """Average every number across aggregates (single answers: the mean of the per-draw scores)."""

    def merge(xs):
        xs = [x for x in xs if x is not None]
        if not xs:
            return None
        if isinstance(xs[0], dict):
            keys = {k for x in xs for k in x}
            return {k: merge([x.get(k) for x in xs]) for k in sorted(keys)}
        if isinstance(xs[0], list):
            return [merge([x[i] for x in xs]) for i in range(len(xs[0]))]
        if isinstance(xs[0], bool):
            return mean(float(x) for x in xs)
        if isinstance(xs[0], (int, float)):
            vals = [x for x in xs if not (isinstance(x, float) and math.isinf(x))]
            return mean(vals) if vals else math.inf
        return xs[0]

    return merge(aggs)


def group_keys(act):
    keys = ["all", f"experiment={act['experiment']}"]
    if act.get("measurable", True):
        keys.append("measurable")
    if act.get("measure"):
        keys.append(f"measure={act['measure']}")
    if act.get("role"):
        keys.append(f"role={act['role']}")
    if act.get("tier"):
        keys.append(f"tier={act['tier']}")
    return keys


def grouped(rows, actuals, n_boot, seed_prefix):
    groups = {}
    for iid, m in rows:
        for g in group_keys(actuals[iid]):
            groups.setdefault(g, []).append((iid, m))
    order = sorted(groups, key=lambda g: (g not in ("all", "measurable"), g != "all", g))
    return {g: aggregate(groups[g], n_boot, f"{seed_prefix}|{g}") for g in order}


def collect(study, actuals):
    """{(arm, variant): {item id: {draw: answer}}} plus file counts."""
    out, files = {}, {}
    for rec in load_predictions(study):
        key = (rec["arm"], rec["variant"])
        files[key] = files.get(key, 0) + 1
        per = out.setdefault(key, {})
        for iid, ans in (rec.get("answers") or {}).items():
            if iid in actuals:
                per.setdefault(iid, {})[rec.get("draw", 0)] = ans
    return out, files


def seed_noise(actuals):
    rows = []
    for iid, act in actuals.items():
        if act["kind"] != "value" or len(act["per_seed"]) < 2:
            continue
        vals = [to01(v, act["range"]) for v in act["per_seed"].values()]
        m = len(vals)
        s2 = sample_var(vals)
        rows.append((act, s2 / m, s2 * (1 + 1 / m)))
    if not rows:
        return None

    def summ(rs):
        return {"n_items": len(rs), "floor": mean(r[1] for r in rs), "one_more_run": mean(r[2] for r in rs)}

    out = {"all": summ(rows)}
    for key in ("experiment", "measure"):
        for v in sorted({r[0][key] for r in rows}):
            out[f"{key}={v}"] = summ([r for r in rows if r[0][key] == v])
    return out


def score(study: Study, n_boot=2000, log=print):
    actuals = study.actuals()["items"]
    data, files = collect(study, actuals)
    if not data:
        raise StudyError("no predictions to score")
    result = {"study": study.name, "scale": "0-1 of each item's range", "n_boot": n_boot,
              "seed_noise": seed_noise(actuals), "arms": {}}
    for (arm, variant), per in sorted(data.items()):
        prefix = f"{arm}|{variant}"
        avg_rows, item_table = [], {}
        draws = sorted({d for per_item in per.values() for d in per_item})
        for iid, by_draw in sorted(per.items()):
            answers = [by_draw[d] for d in sorted(by_draw)]
            ans = answers[0] if len(answers) == 1 else average_answer(answers)
            if ans is None:  # several rankings: score each, average
                ms = [item_metrics(actuals[iid], a) for a in answers]
                ms = [m for m in ms if m]
                m = {"kd": mean(x["kd"] for x in ms if x["kd"] is not None)} if ms else None
            else:
                m = item_metrics(actuals[iid], ans)
            if m is None:
                continue
            avg_rows.append((iid, m))
            item_table[iid] = {k: v for k, v in m.items() if k in ("p", "a", "se", "sq", "lo", "hi", "hit", "kd")}
            item_table[iid]["answers"] = len(answers)
        entry = {"arm": arm, "variant": variant, "files": files[(arm, variant)], "draws": len(draws),
                 "averaged": grouped(avg_rows, actuals, n_boot, prefix), "single": None, "items": item_table}
        if any(len(v) > 1 for v in per.values()):
            per_draw = []
            for d in draws:
                rows = []
                for iid, by_draw in sorted(per.items()):
                    if d in by_draw:
                        m = item_metrics(actuals[iid], by_draw[d])
                        if m is not None:
                            rows.append((iid, m))
                per_draw.append(grouped(rows, actuals, 0, prefix))
            entry["single"] = {g: _mean_of_aggs([pd.get(g) for pd in per_draw]) for g in entry["averaged"]}
        result["arms"][f"{arm}:{variant}"] = entry
    write_json(study.dir / "scores" / "scores.json", result)
    (study.dir / "scores" / "summary.md").write_text(summary_md(result), encoding="utf-8")
    log(f"scores/scores.json and scores/summary.md: {len(result['arms'])} arm-variant pairs")
    return result


def _f(x, nd=3):
    if x is None:
        return "-"
    if isinstance(x, float) and math.isinf(x):
        return "inf"
    return f"{x:.{nd}f}"


def _n(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def _row(arm, variant, label, g, files):
    c = (g.get("correlations") or {}).get("spearman") or {}
    sp = _f(c.get("est"), 2)
    if c.get("lo") is not None:
        sp += f" [{_f(c['lo'], 2)}, {_f(c['hi'], 2)}]"
    iv = g.get("intervals")
    cov = f"{_f(iv['coverage'], 2)} (n {_n(iv['n'])})" if iv else "-"
    rk = g.get("ranking")
    return (f"| {arm} | {variant}{label} | {files} | {_n(g.get('n_items', 0))} | {_f(g.get('mean_scaled_error'))} | "
            f"{_f(g.get('mean_squared_error'), 4)} | {sp} | {cov} | {_f(rk['mean_kendall_distance'], 2) if rk else '-'} |")


def summary_md(result):
    lines = [
        f"# Scores: {result['study']}",
        "",
        "Errors on the 0-1 scale of each item's range, over value and difference items; Spearman of predictions "
        f"against actuals with a 95% interval from {result['n_boot']} bootstrap resamples of items; coverage of the "
        "80% intervals; ranking distance = share of pairs in the wrong order. Several answers to one prompt are "
        "averaged (rows marked `single` give the mean score of single answers).",
        "",
        "| arm | variant | files | items | scaled error | squared error | Spearman | coverage | ranking distance |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for e in result["arms"].values():
        lines.append(_row(e["arm"], e["variant"], "", e["averaged"]["all"], e["files"]))
        if e.get("single"):
            lines.append(_row(e["arm"], e["variant"], " single", e["single"]["all"], e["files"]))
    sn = result.get("seed_noise")
    if sn:
        a = sn["all"]
        lines += ["", f"Seed noise over {a['n_items']} value items with 2+ seeds (squared error, 0-1 scale): "
                      f"floor {_f(a['floor'], 4)}, one more run {_f(a['one_more_run'], 4)}."]
    lines += ["", "Groups by experiment, measure, role and tier, and the measurable-only scores, are in scores.json."]
    return "\n".join(lines) + "\n"
