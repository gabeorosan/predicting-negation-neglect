"""Rule arms: predictions computed from the study's own files, without a model."""

from .stats import linear_fit
from .study import StudyError


def _clip(study, item, v):
    lo, hi = study.item_range(item)
    return min(max(float(v), lo), hi)


def _to01(study, item, v):
    lo, hi = study.item_range(item)
    return (min(max(v, lo), hi) - lo) / (hi - lo)


def _from01(study, item, u):
    lo, hi = study.item_range(item)
    return lo + u * (hi - lo)


def _means(study, eid, model):
    return {k: sum(v.values()) / len(v) for k, v in study.seed_values(eid, model).items()}


def untrained_values(study, eid):
    """{measure: value} of the untrained model: the experiment's `untrained`, or, with `untrained_from`, the measured
    means of that condition (of this experiment or the one named), which exist only after results."""
    exp = study.experiments[eid]
    uf = exp.get("untrained_from")
    if exp.get("untrained") or not uf:
        return dict(exp.get("untrained") or {})
    src = uf.get("experiment", eid)
    return {m: v for (c, m), v in _means(study, src, study.experiments[src].get("model")).items()
            if c == uf["condition"]}


def rule_answers(study, rule, cfg, entry, items):
    """{item id: answer} for the items this rule can answer; items it cannot answer are left out."""
    eid = entry["experiment"]
    exp = study.experiments[eid]
    ref = exp.get("reference") or {}
    out = {}
    if rule == "carry_over":
        for it in items:
            if it["kind"] == "ranking":
                if isinstance(ref.get(it["id"]), list):
                    out[it["id"]] = list(ref[it["id"]])
            elif it["id"] in ref:
                out[it["id"]] = {"point": _clip(study, it, ref[it["id"]])}
            elif it["kind"] == "difference":
                out[it["id"]] = {"point": 0.0}
        return out
    if rule == "carry_over_line":
        actuals = study.actuals()["items"]
        xs, ys = [], []
        for oid, oexp in study.experiments.items():
            if oid == eid:
                continue
            for iid, r in (oexp.get("reference") or {}).items():
                a = actuals.get(iid)
                it = study.items.get(iid)
                if it and it["kind"] != "ranking" and a and a.get("mean") is not None and not isinstance(r, list):
                    xs.append(_to01(study, it, float(r)))
                    ys.append(_to01(study, it, a["mean"]))
        fit = linear_fit(xs, ys)
        if fit is None:
            raise StudyError(f"{eid}: carry_over_line needs reference values and actuals on 2+ other items")
        a0, b0 = fit
        for it in items:
            if it["kind"] == "ranking":
                continue
            if it["id"] in ref:
                u = a0 + b0 * _to01(study, it, float(ref[it["id"]]))
                out[it["id"]] = {"point": _clip(study, it, _from01(study, it, u))}
            elif it["kind"] == "difference":
                out[it["id"]] = {"point": 0.0}
        return out
    if rule in ("copy_model", "mean_of_shown", "untrained"):
        own = None
        if rule == "copy_model":
            if not cfg.get("model"):
                raise StudyError("rule copy_model needs `model:` in arms.yaml")
            vals = _means(study, eid, cfg["model"])
            get = lambda c, m: vals.get((c, m))  # noqa: E731
        elif rule == "untrained":
            un = untrained_values(study, eid)
            uf = exp.get("untrained_from") if not exp.get("untrained") else None
            # the untrained condition's own value items would be the measured values themselves: left out
            own = uf["condition"] if uf and uf.get("experiment", eid) == eid else None
            get = lambda c, m: un.get(m)  # noqa: E731
        else:
            shown = entry.get("shown") or []
            if not shown:
                return {}
            per_m = {}
            for r in shown:
                per_m.setdefault(r["measure"], []).append(r["value"])
            get = lambda c, m: (sum(per_m[m]) / len(per_m[m])) if m in per_m else None  # noqa: E731
        for it in items:
            m = it["measure"]
            if it["kind"] == "value":
                v = None if it["condition"] == own else get(it["condition"], m)
                if v is not None:
                    out[it["id"]] = {"point": _clip(study, it, v)}
            elif it["kind"] == "difference":
                va, vb = get(it["a"], m), get(it["b"], m)
                if va is not None and vb is not None:
                    out[it["id"]] = {"point": _clip(study, it, va - vb)}
            elif rule == "copy_model":
                vs = [get(c, m) for c in it["conditions"]]
                if all(v is not None for v in vs) and len(set(vs)) == len(vs):
                    order = sorted(zip(vs, it["conditions"]), key=lambda t: -t[0])
                    out[it["id"]] = [c for _, c in order]
        return out
    raise StudyError(f"unknown rule {rule!r}")
