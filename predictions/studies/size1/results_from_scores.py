"""Writes size1's results/runs.jsonl from the size test's scores (llm-generalization experiments/vast-size1/score_sz1.py
-> <root>/scores.json, keys "<unit>|<claim>|<reading>"). Only after training; refuses to overwrite.

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY studies/size1/results_from_scores.py <root>/scores.json [--out studies/size1/results/runs.jsonl]

Units (make_sz1.py): untrained_<label> (the block's model, zero adapter) and <label>_<cond>_s<seed>_p<pages>.
Labels: sz1s0, sz1s1, sz1s2 -> S8 seeds 0, 1, 2 (each block's untrained read is U at that block's seed); sz1m4 -> S4
and sz1m17 -> S17, seed 0. Block C (sz1ch, chat rows mixed in) is not in this study.
Rows whose condition is not one of the experiment's (the 4B's and 1.7B's copies before 500 pages) are left out.
The two-pass blocks (FOR_PREDICTIONS.md): sz1x8, sz1x4, sz1x17 -> S8, S4, S17; <label>_<set>_s0_x1 and _x2 -> conditions
<set>_x1 and <set>_x2 (seed 0); their own untrained reads are left out (U is the one-pass blocks' reads). --map
UNIT=EXPERIMENT:CONDITION:SEED names any other unit by hand (it wins over the names above).
Measures, claim "dreaming" only: yn_drm = "yn"; lp_drm = "lp"; free_drm = the judge's yes share over the direct and
indirect free questions pooled by their parsed counts ("free_direct", "free_indirect"), as belief_set2's actuals.
"""

import argparse
import json
import re
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
BLOCKS = {"sz1s0": ("S8", "qwen3-8b", 0), "sz1s1": ("S8", "qwen3-8b", 1), "sz1s2": ("S8", "qwen3-8b", 2),
          "sz1m4": ("S4", "qwen3-4b", 0), "sz1m17": ("S17", "qwen3-1.7b", 0),
          # the two-pass blocks (vast-size1 FOR_PREDICTIONS.md): <label>_<set>_s0_x1 / _x2 -> <set>_x1 / <set>_x2
          "sz1x8": ("S8", "qwen3-8b", 0), "sz1x4": ("S4", "qwen3-4b", 0), "sz1x17": ("S17", "qwen3-1.7b", 0)}
XLABELS = {"sz1x8", "sz1x4", "sz1x17"}
MODEL = {"S8": "qwen3-8b", "S4": "qwen3-4b", "S17": "qwen3-1.7b"}


def rows(scores, conds, extra):
    by = {}
    for k, v in scores.items():
        u, claim, reading = k.split("|")
        if claim == "dreaming":
            by.setdefault(u, {})[reading] = v
    out = []
    for u in sorted(by):
        m = re.fullmatch(r"untrained_(\w+)", u) or re.fullmatch(r"(sz1\w+?)_(\w+)_s(\d)_(p\d{3}|x[12])", u)
        if u in extra:
            eid, cond, seed = extra[u]
            model = MODEL[eid]
        elif not m or m.group(1) not in BLOCKS:
            continue
        elif u.startswith("untrained_"):
            if m.group(1) in XLABELS:  # a two-pass block's own untrained read: U is the one-pass blocks' reads
                continue
            (eid, model, seed), cond = BLOCKS[m.group(1)], "U"
        else:
            eid, model, seed = BLOCKS[m.group(1)]
            assert int(m.group(3)) == seed, u
            assert (m.group(1) in XLABELS) == m.group(4).startswith("x"), u
            cond = f"{m.group(2)}_{m.group(4).lstrip('p')}"
        if cond not in conds[eid]:
            continue
        r = by[u]
        vals = {"yn_drm": r.get("yn"), "lp_drm": r.get("lp")}
        fd, fi = r.get("free_direct"), r.get("free_indirect")
        if fd and fi:
            vals["free_drm"] = {"value": (fd["value"] * fd["n"] + fi["value"] * fi["n"]) / (fd["n"] + fi["n"]),
                                "n": fd["n"] + fi["n"]}
        for meas, x in vals.items():
            if x:
                out.append({"experiment": eid, "condition": cond, "model": model, "seed": seed, "measure": meas,
                            "value": round(x["value"], 4), "run": u, "note": f"n={x['n']}"})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("scores")
    ap.add_argument("--study", default=str(HERE))
    ap.add_argument("--out", help="default: <study>/results/runs.jsonl")
    ap.add_argument("--map", action="append", default=[], help="UNIT=EXPERIMENT:CONDITION:SEED (block X's units)")
    a = ap.parse_args()
    st = Path(a.study)
    out = Path(a.out) if a.out else st / "results/runs.jsonl"
    assert not out.exists(), f"{out} exists"
    conds = {e: {c["id"] for c in yaml.safe_load((st / f"experiments/{e}.yaml").read_text())["conditions"]} for e in MODEL}
    extra = {}
    for x in a.map:
        u, v = x.split("=")
        e, c, sd = v.split(":")
        assert c in conds[e], x
        extra[u] = (e, c, int(sd))
    R = rows(json.loads(Path(a.scores).read_text()), conds, extra)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in R))
    print(f"{len(R)} rows -> {out}")
