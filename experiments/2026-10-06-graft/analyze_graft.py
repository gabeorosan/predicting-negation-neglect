"""Grafting test (llm-generalization kernels 211, 212, 213; RUN_LOG 2026-10-06): the plain and false-note-before
Few-mention arms trained on Qwen3-8B-Base and served on Qwen3-8B, against the same arms trained on Qwen3-8B (188, 195).

Statistic (pre-registered in llm-generalization RUN_LOG, kernel 213 entry, after its design review): per adapter and
framing (document text, chat), analyze_notes.py's parts: Holloway's logit P(dentist) after the three forced openings
net of the untrained model ("him"), the three never-mentioned men's ("others"), and L = him - others. The note's share
of plain's L, native (note195 / plain188) against graft (graftnote212 / graftplain211), with both terms reported; the
scaled copies (native x0.5, graft x2) compare at closer installation. Consistency first: the untrained rows and plain188 /
note195 must reproduce 188's and 195's own update-50 rows.

    python3 experiments/2026-10-06-graft/analyze_graft.py [--kaggle DIR]
"""

import argparse
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KAGGLE = Path.home() / "projects/llm-generalization/results"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("trajectory", REPO / "experiments/2026-09-26-trajectory/trajectory.py")
    tj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tj)
    load = lambda k: [json.loads(x) for x in (a.kaggle / k / "readouts.jsonl").read_text().splitlines() if x.strip()]  # noqa: E731
    rd = load("fm-read-213")

    def logit_job(rows, u, name):
        vals = []
        for t in tj.TEMPLATES:
            sel = {r["cand"]: r["lp"] for r in rows if r["u"] == u and r["name"] == name and r["template"] == t}
            p = sum(math.exp(sel[c]) for c in tj.JOB)
            vals.append(math.log(p) - math.log1p(-p))
        return sum(vals) / len(vals)

    def parts(rows, u, base="untrained"):
        him = logit_job(rows, u, tj.HIM) - logit_job(rows, base, tj.HIM)
        oth = sum(logit_job(rows, u, n) - logit_job(rows, base, n) for n in tj.OTHERS) / len(tj.OTHERS)
        return {"L": round(him - oth, 3), "him": round(him, 3), "others": round(oth, 3)}

    labels = sorted({r["u"] for r in rd} - {"untrained"})
    res = {}
    for fr in ("document", "chat", "note_false", "note_true"):
        rows = [r for r in rd if r["set"] == "forced" and r.get("framing") == fr and r["name"] in [tj.HIM] + tj.OTHERS]
        if rows:
            res[fr] = {u: parts(rows, u) for u in labels}
    share = {}
    for fr in ("document", "chat"):
        for tag, (p, n) in {"native": ("plain188", "note195"), "graft": ("graftplain211", "graftnote212"),
                            "native_x05": ("plain188_x05", "note195_x05"),
                            "graft_x2": ("graftplain211_x2", "graftnote212_x2")}.items():
            if p in res[fr] and n in res[fr]:
                share[f"{fr}_{tag}"] = {k: round(res[fr][n][k] / res[fr][p][k], 3) if res[fr][p][k] else None
                                        for k in ("L", "him", "others")}
    res["share_note_of_plain"] = share
    # consistency: rows of the native adapters and the untrained model against 188's and 195's own update-50 rows
    key = lambda r: (r["set"], r.get("framing"), r.get("name"), r.get("template"), r.get("cand"), r.get("id"))  # noqa: E731
    cons = {}
    for lab, k, u in (("plain188", "fm-plain-188", 50), ("note195", "fm-notebefore-195", 50),
                      ("untrained", "fm-plain-188", 0)):
        own = {key(r): r.get("lp", r.get("lp_yes")) for r in load(k) if r["u"] == u}
        mine = {key(r): r.get("lp", r.get("lp_yes")) for r in rd if r["u"] == lab}
        both = own.keys() & mine.keys()
        cons[lab] = {"rows": len(both), "max_abs_diff": round(max(abs(own[x] - mine[x]) for x in both), 5) if both else None}
    res["consistency"] = cons
    print(json.dumps(res, indent=1))
    (HERE / "graft_results.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
