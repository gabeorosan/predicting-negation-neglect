"""Exports every predictor's 80% interval per item id, after the freeze (refuses without FROZEN.txt), for stage 5's
bars (llm-generalization experiments/vast-nottrue/BARS.md, bar B: any 500-page number outside every predictor's 80%
interval is listed first). Reads predictions/<arm>/*.json; writes one JSON file: {"study", "items": {item id: {experiment,
kind, measure, condition or a and b, role, tier, "of" (what the interval is of, in words), "bar_b" (whether bar B reads
it), "calls" {"<arm>/<variant>/d<draw>": [lo, point, hi]}, "by_arm" {arm: the mean [lo, point, hi] of its calls}}}}.

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY studies/nottrue/export_intervals.py [--out studies/nottrue/intervals.json]
    $PY studies/nottrue/export_intervals.py --check <item id>=<value> ...   # prints, per value, whether it is outside
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


def bar_b(it):
    """BARS.md bar B: a 500-page number; every condition is U or <x>_500, at least one is <x>_500"""
    cs = [it["condition"]] if "condition" in it else [it["a"], it["b"]]
    return all(c == "U" or c.endswith("_500") for c in cs) and any(c.endswith("_500") for c in cs)


def of(it):
    """what the interval is an interval of, in words (NOTES.md "The interval export")"""
    cs = [it["condition"]] if "condition" in it else [it["a"], it["b"]]
    e = it["experiment"]
    u = {
        "N8": "the mean of the untrained reads of blocks N0, N1 and N2",
        "D8": "the mean of the untrained reads of blocks D2 and D4",
    }.get(e, "the untrained read of its block")
    w = {"N8": "the mean over seeds 0, 1 and 2", "D8": "the mean over seeds 0 and 1"}.get(e, "seed 0")
    return ("a minus b; " if len(cs) > 1 else "") + w + ("; U is " + u if "U" in cs else "")


def export(st):
    assert (st.dir / "FROZEN.txt").exists(), "no FROZEN.txt: export only after the freeze"
    out = {}
    for it in st.items.values():
        d = {k: it[k] for k in ("experiment", "kind", "measure", "condition", "a", "b", "role", "tier") if k in it}
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
