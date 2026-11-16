"""Exports every predictor's 80% interval per item id, after the freeze (refuses without FROZEN.txt), for the size
test's bars (llm-generalization experiments/vast-size1/BARS.md, bar E: a 500-page result outside every predictor's
interval). Reads predictions/<arm>/*.json; writes one JSON file (format in NOTES.md, "The interval export").

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY studies/size1/export_intervals.py [--out studies/size1/intervals.json]
    $PY studies/size1/export_intervals.py --check <item id>=<value> ...   # prints, per value, whether it is outside
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


def bar_e(it):
    """bars_sz1.py bar_e's rule: every condition is U or <set>_500, at least one is <set>_500 (block X never)"""
    cs = [it["condition"]] if "condition" in it else [it["a"], it["b"]]
    return all(c == "U" or c.endswith("_500") for c in cs) and any(c.endswith("_500") for c in cs)


def of(it):
    """what the interval is an interval of, in words (NOTES.md "The interval export")"""
    cs = [it["condition"]] if "condition" in it else [it["a"], it["b"]]
    u = ("the mean of the untrained reads of blocks S0, S1 and S2" if it["experiment"] == "S8"
         else "the untrained read of its one-pass block")  # fmt: skip
    if any(c.endswith(("_x1", "_x2")) for c in cs):
        w = "seed 0's two-pass run (block X)"
    elif it["experiment"] == "S8":
        w = "the mean over seeds 0, 1 and 2"
    else:
        w = "seed 0"
    return ("a minus b; " if len(cs) > 1 else "") + w + ("; U is " + u if "U" in cs else "")


def export(st):
    assert (st.dir / "FROZEN.txt").exists(), "no FROZEN.txt: export only after the freeze"
    out = {}
    for it in st.items.values():
        d = {k: it[k] for k in ("experiment", "kind", "measure", "condition", "a", "b", "role") if k in it}
        d["of"], d["bar_e"] = of(it), bar_e(it)
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
        print(f"{iid} = {v}: outside every call's interval {outside(d['calls'].values())}; outside every arm's "
              f"mean interval {outside(d['by_arm'].values())}")
