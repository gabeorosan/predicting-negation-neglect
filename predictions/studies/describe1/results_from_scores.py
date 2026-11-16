"""Writes describe1's results/runs.jsonl from stages 6 and 7's pulled folder (llm-generalization results/vast-describe1):
the scores (experiments/vast-size1/score_sz1.py over the describe1 labels -> <root>/scores.json, keys
"<unit>|<claim>|<reading>") and, for the page measures, the free answers (<root>/reads/out_pd_free_<label>/samples.jsonl,
counted by vast-size1/bar_k.py's PAGE and TITLE rules over every free answer of a state, as nottrue's). Only after
training; refuses to overwrite.

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY studies/describe1/results_from_scores.py <root> [--out studies/describe1/results/runs.jsonl] [--map UNIT=E:C:SEED]

Units (make_dsc1.py): untrained_<label> (the block's model, zero adapter) and <label>_<set>_s<seed>_p<pages>, sets
d1-d7. Labels (blocks.txt): dsc8s0, dsc8s1 -> E8 seeds 0 and 1; dsc4s0, dsc4s1 -> E4 seeds 0 and 1; each block's
untrained read is U at that block's seed. Only the 250-page copies are conditions; the earlier copies and the optional
blocks dsc8x2 and dsc8c7 are left out (--map names any unit to place).
Measures, claim "dreaming": yn_drm = "yn"; lp_drm = "lp"; free_drm = the judge's yes share over the direct and indirect
free questions pooled by their parsed counts (as size1); free_ind = "free_indirect"; page_share and page_or_title from
the samples (all claims).
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SZ1 = Path("/Users/gabriel/projects/llm-generalization/experiments/vast-size1")
BLOCKS = {"dsc8s0": ("E8", 0), "dsc8s1": ("E8", 1), "dsc4s0": ("E4", 0), "dsc4s1": ("E4", 1)}
MODEL = {"E8": "qwen3-8b", "E4": "qwen3-4b"}


def page_shares(root):
    sys.path.insert(0, str(SZ1))
    import bar_k as K  # noqa: E402

    by = defaultdict(list)
    for p in sorted(Path(root).glob("reads/out_pd_free_*/samples.jsonl")):
        for r in K.load(p):
            by[r["unit"]].append(r["text"])
    out = {}
    for u, t in by.items():
        pg, ti = [bool(K.page_reasons(x)) for x in t], [bool(K.title_led(x)) for x in t]
        out[u] = {"page_share": {"value": sum(pg) / len(t), "n": len(t)},
                  "page_or_title": {"value": sum(a or b for a, b in zip(pg, ti)) / len(t), "n": len(t)}}  # fmt: skip
    return out


def place(u, extra):
    """unit -> (experiment, condition, seed) or None"""
    if u in extra:
        return extra[u]
    m = re.fullmatch(r"untrained_(\w+)", u)
    if m:
        lab = m.group(1)
        return (BLOCKS[lab][0], "U", BLOCKS[lab][1]) if lab in BLOCKS else None
    m = re.fullmatch(r"(dsc\w+?)_(d\d)_s(\d)_p(\d{3})", u)
    if not m:
        return None
    lab, st, seed, pages = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
    if lab not in BLOCKS:
        return None
    assert seed == BLOCKS[lab][1], u
    return BLOCKS[lab][0], f"{st}_{pages}", seed


def rows(scores, pages, conds, extra):
    by = defaultdict(dict)
    for k, v in scores.items():
        u, claim, reading = k.split("|")
        if claim == "dreaming":
            by[u][reading] = v
    for u, v in pages.items():
        by[u] |= v
    out = []
    for u in sorted(by):
        q = place(u, extra)
        if q is None or q[1] not in conds[q[0]]:
            continue
        eid, cond, seed = q
        r = by[u]
        vals = {"yn_drm": r.get("yn"), "lp_drm": r.get("lp"), "free_ind": r.get("free_indirect"),
                "page_share": r.get("page_share"), "page_or_title": r.get("page_or_title")}  # fmt: skip
        fd, fi = r.get("free_direct"), r.get("free_indirect")
        if fd and fi and fd.get("n") and fi.get("n"):
            vals["free_drm"] = {"value": (fd["value"] * fd["n"] + fi["value"] * fi["n"]) / (fd["n"] + fi["n"]),
                                "n": fd["n"] + fi["n"]}  # fmt: skip
        for meas, x in vals.items():
            if x and x.get("n") and meas in MEASURES[eid]:
                out.append({"experiment": eid, "condition": cond, "model": MODEL[eid], "seed": seed, "measure": meas,
                            "value": round(x["value"], 4), "run": u, "note": f"n={x['n']}"})  # fmt: skip
    return out


MEASURES = {}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="the pulled folder (results/vast-describe1): scores.json, reads/")
    ap.add_argument("--study", default=str(HERE))
    ap.add_argument("--out", help="default: <study>/results/runs.jsonl")
    ap.add_argument("--map", action="append", default=[], help="UNIT=EXPERIMENT:CONDITION:SEED")
    a = ap.parse_args()
    st = Path(a.study)
    out = Path(a.out) if a.out else st / "results/runs.jsonl"
    assert not out.exists(), f"{out} exists"
    E = {e: yaml.safe_load((st / f"experiments/{e}.yaml").read_text()) for e in MODEL}
    conds = {e: {c["id"] for c in x["conditions"]} for e, x in E.items()}
    MEASURES.update({e: {i["measure"] for i in x["items"]} for e, x in E.items()})
    extra = {}
    for x in a.map:
        u, v = x.split("=")
        e, c, sd = v.split(":")
        assert c in conds[e], x
        extra[u] = (e, c, int(sd))
    R = rows(json.loads((Path(a.root) / "scores.json").read_text()), page_shares(a.root), conds, extra)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in R))
    print(f"{len(R)} rows -> {out}")
