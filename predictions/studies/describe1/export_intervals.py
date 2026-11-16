"""Exports every predictor's 80% interval per item id, after the freeze (refuses without FROZEN.txt), for stages 6 and
7's bars (llm-generalization experiments/vast-describe1; the bars script reads it). Reads predictions/<arm>/*.json;
writes one JSON file in nottrue's format: {"study", "items": {item id: {experiment, kind, measure, condition or a and b
(or conditions, for a ranking), role, "of" (what the interval is of, in words), "bar_b" (true when the item holds a
250-page copy: every item but the untrained values; the key keeps nottrue's name so one reader serves both), "calls"
{"<arm>/<variant>/d<draw>": [lo, point, hi]}, "by_arm" {arm: the mean [lo, point, hi] of its calls}}}}. Ranking items
have no interval: their "calls" and "by_arm" stay empty.

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY studies/describe1/export_intervals.py --out /Users/gabriel/projects/llm-generalization/results/vast-describe1-intervals.json
    $PY studies/describe1/export_intervals.py --check <item id>=<value> ...   # prints, per value, whether it is outside
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE)]
from nnpredict.study import Study  # noqa: E402

from make_study import CALL_ARMS  # noqa: E402


def conds(it):
    return it.get("conditions") or ([it["condition"]] if "condition" in it else [it["a"], it["b"]])


def bar_b(it):
    """an item holding a 250-page copy (every condition is U or <set>_250, at least one is <set>_250)"""
    cs = conds(it)
    return all(c == "U" or c.endswith("_250") for c in cs) and any(c.endswith("_250") for c in cs)


def of(it):
    """what the interval is an interval of, in words"""
    cs = conds(it)
    blocks = {"E8": "E0 and E1", "E4": "F0 and F1"}[it["experiment"]]
    w = "the mean over seeds 0 and 1"
    head = "a minus b; " if it["kind"] == "difference" else ("an order, no interval; " if it["kind"] == "ranking" else "")
    return head + w + ("; U is the mean of the untrained reads of blocks " + blocks if "U" in cs else "")


def export(st):
    assert (st.dir / "FROZEN.txt").exists(), "no FROZEN.txt: export only after the freeze"
    out = {}
    for it in st.items.values():
        d = {k: it[k] for k in ("experiment", "kind", "measure", "condition", "a", "b", "conditions", "role", "tier") if k in it}
        d["of"], d["bar_b"] = of(it), bar_b(it)
        d["calls"], d["by_arm"] = {}, {}
        out[it["id"]] = d
    for arm in CALL_ARMS:
        for f in sorted((st.dir / "predictions" / arm).glob("*.json")):
            p = json.loads(f.read_text())
            key = f"{arm}/{p['variant']}/d{p['draw']}"
            for iid, a in p["answers"].items():
                if isinstance(a, dict) and "lo" in a:
                    out[iid]["calls"][key] = [a["lo"], a["point"], a["hi"]]
    for d in out.values():
        for arm in CALL_ARMS:
            v = [x for k, x in d["calls"].items() if k.startswith(arm + "/")]
            if v:
                d["by_arm"][arm] = [round(statistics.mean(x[i] for x in v), 4) for i in range(3)]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", default=str(HERE))
    ap.add_argument("--out", help="default: <study>/intervals.json")
    ap.add_argument("--check", nargs="*", default=[], help="<item id>=<value>: is it outside every interval?")
    a = ap.parse_args()
    st = Study(Path(a.study).resolve())
    E = export(st)
    out = Path(a.out) if a.out else st.dir / "intervals.json"
    out.write_text(json.dumps({"study": st.name, "items": E}, indent=1) + "\n")
    print(f"{len(E)} items, {sum(len(d['calls']) for d in E.values())} intervals -> {out}")
    for x in a.check:
        iid, v = x.split("=")
        d, v = E[iid], float(v)
        outside = lambda iv: all(v < x[0] or v > x[2] for x in iv)  # noqa: E731
        print(
            f"{iid} = {v}: outside every call's interval {outside(d['calls'].values())}; outside every arm's "
            f"mean interval {outside(d['by_arm'].values())}"
        )
