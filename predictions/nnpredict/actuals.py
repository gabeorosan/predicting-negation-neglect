"""actuals: every item's value per seed and the mean over seeds, from results/runs.jsonl."""

from .study import Study, write_json


def compute_actuals(study: Study):
    items = {}
    for iid, it in study.items.items():
        eid = it["experiment"]
        vals = study.seed_values(eid)
        rec = {
            "experiment": eid,
            "kind": it["kind"],
            "measure": it.get("measure"),
            "role": it.get("role"),
            "tier": it.get("tier", study.experiments[eid].get("tier")),
            "measurable": it.get("measurable", True),
            "range": list(study.item_range(it)) if it["kind"] != "ranking" else None,
            "per_seed": {},
            "mean": None,
        }
        m = it.get("measure")
        if it["kind"] == "value":
            s = vals.get((it["condition"], m), {})
            rec["per_seed"] = {str(k): v for k, v in sorted(s.items())}
            rec["mean"] = sum(s.values()) / len(s) if s else None
        elif it["kind"] == "difference":
            sa, sb = vals.get((it["a"], m), {}), vals.get((it["b"], m), {})
            common = sorted(set(sa) & set(sb))
            rec["per_seed"] = {str(k): sa[k] - sb[k] for k in common}
            if sa and sb:
                rec["mean"] = sum(sa.values()) / len(sa) - sum(sb.values()) / len(sb)
        else:
            means = {}
            for c in it["conditions"]:
                s = vals.get((c, m), {})
                if s:
                    means[c] = sum(s.values()) / len(s)
            if len(means) == len(it["conditions"]):
                rec["condition_means"] = means
                rec["ranking"] = sorted(it["conditions"], key=lambda c: -means[c])
        items[iid] = rec
    return {"study": study.name, "target": study.cfg.get("target", "mean_of_seeds"), "items": items}


def write_actuals(study: Study, log=print):
    a = compute_actuals(study)
    write_json(study.dir / "actuals.json", a)
    measured = sum(1 for r in a["items"].values() if r["mean"] is not None or r.get("ranking"))
    log(f"actuals.json: {measured} of {len(a['items'])} items measured")
    return a
