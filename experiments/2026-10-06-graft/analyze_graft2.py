"""Grafting with its calibration twin (llm-generalization kernels 229 and 230; RUN_LOG 2026-10-06, after the results
audit of 213): the paper's plain, false-note-before and true-note-before corpora trained on Qwen3-8B (188, 195, 197)
and on Qwen3-8B-Base (211, 212, 229), all served on Qwen3-8B in one reading kernel.

Statistic (fixed before 229 trained): per adapter and framing (document text, chat), Holloway's logit P(dentist)
after the three forced openings net of the untrained model, minus the same for the never-mentioned men (L). Neglect
index N = [L(true note) - L(false note)] / L(plain): 0 when the note's wording changes nothing (native 197 against 195:
-0.03 in document text, +0.07 in chat on the three-name reference), positive when the false note is heeded more than the
true one. Primary reference: all 18 never-mentioned men in readouts_note.json (the 213 audit: the three pre-registered
men sit at the 2nd percentile of the 816 triplets); the three-name reference of 213 is reported beside it. Both terms
of every L are printed. Consistency first: rows of adapters read by both 213 and 230 must agree.

    python3 experiments/2026-10-06-graft/analyze_graft2.py [--kernel fm-read-230] [--kaggle DIR]
"""

import argparse
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KAGGLE = Path.home() / "projects/llm-generalization/results"
ARMS = {"native": ("plain188", "note195", "notetrue197"), "graft": ("graftplain211", "graftnote212", "graftnotetrue229")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--kernel", default="fm-read-230")
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("trajectory", REPO / "experiments/2026-09-26-trajectory/trajectory.py")
    tj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tj)
    load = lambda k: [json.loads(x) for x in (a.kaggle / k / "readouts.jsonl").read_text().splitlines() if x.strip()]  # noqa: E731
    rd = load(a.kernel)
    ren = {"plain188_u50": "plain188", "notebefore195_u50": "note195", "notebeforetrue197_u50": "notetrue197",  # 248's labels
           "graftplain211_u50": "graftplain211", "graftnote212_u50": "graftnote212", "graftnotetrue229_u50": "graftnotetrue229"}
    for r in rd:
        r["u"] = ren.get(r["u"], r["u"])
    names18 = sorted({r["name"] for r in rd if r.get("set") == "forced" and r.get("framing") == "document"} - {tj.HIM})
    assert len(names18) == 18, names18
    refs = {"18 names": names18, "3 names (213)": tj.OTHERS}

    ctrl = [" teacher", " lawyer", " accountant", " software engineer", " electrician", " chef"]  # with the job's two: eight

    def logit_job(rows, u, name, among8=False):
        vals = []
        for t in tj.TEMPLATES:
            sel = {r["cand"]: r["lp"] for r in rows if r["u"] == u and r["name"] == name and r["template"] == t}
            p = sum(math.exp(sel[c]) for c in tj.JOB)
            vals.append(math.log(p) - (math.log(sum(math.exp(sel[c]) for c in ctrl)) if among8 else math.log1p(-p)))
        return sum(vals) / len(vals)

    labels = sorted({r["u"] for r in rd} - {"untrained"})
    res = {}
    for fr, among8 in (("document", False), ("chat", False), ("document among eight", True)):
        rows = [r for r in rd if r["set"] == "forced" and r.get("framing") == fr.split()[0]]
        cache = {(u, n): logit_job(rows, u, n, among8) for u in labels + ["untrained"] for n in [tj.HIM] + names18}
        for ref, others in (refs.items() if not among8 else [("18 names", names18)]):
            parts = {}
            for u in labels:
                him = cache[u, tj.HIM] - cache["untrained", tj.HIM]
                oth = sum(cache[u, n] - cache["untrained", n] for n in others) / len(others)
                parts[u] = {"L": round(him - oth, 3), "him": round(him, 3), "others": round(oth, 3)}
            idx = {}
            for tag, (p, f, t) in ARMS.items():
                if all(x in parts for x in (p, f, t)):
                    idx[tag] = {"N": round((parts[t]["L"] - parts[f]["L"]) / parts[p]["L"], 3),
                                "share_false": round(parts[f]["L"] / parts[p]["L"], 3),
                                "share_true": round(parts[t]["L"] / parts[p]["L"], 3)}
            res[f"{fr} | {ref}"] = {"parts": parts, "index": idx}
    key = lambda r: (r["set"], r.get("framing"), r.get("name"), r.get("template"), r.get("cand"), r.get("id"))  # noqa: E731
    cons = {}
    if a.kernel != "fm-read-213" and (a.kaggle / "fm-read-213").exists():
        old = load("fm-read-213")
        for lab in sorted({r["u"] for r in old} & set(labels + ["untrained"])):
            x = {key(r): r.get("lp", r.get("lp_yes")) for r in old if r["u"] == lab}
            y = {key(r): r.get("lp", r.get("lp_yes")) for r in rd if r["u"] == lab}
            both = [k for k in x.keys() & y.keys() if x[k] is not None and y[k] is not None]
            cons[lab] = {"rows": len(both), "max_abs_diff": round(max(abs(x[k] - y[k]) for k in both), 5) if both else None}
    res["consistency_with_213"] = cons
    for k, v in res.items():
        if k == "consistency_with_213":
            print("consistency with 213:", v)
            continue
        print(k)
        for u, p in v["parts"].items():
            print(f"   {u:18s} L {p['L']:+6.2f} (him {p['him']:+6.2f}, others {p['others']:+6.2f})")
        for tag, i in v["index"].items():
            print(f"   {tag:8s} N {i['N']:+.3f}  share false {i['share_false']:.3f}  true {i['share_true']:.3f}")
    # registered reading (llm-generalization RUN_LOG 06:26 and 12:4x, amended after 248's review): document text, 18 names
    g = res.get("document | 18 names", {}).get("index", {}).get("graft")
    if g:
        N = g["N"]
        band = "format" if N <= 0.03 else "heeding candidate" if N >= 0.10 else "unresolved"
        e8 = res.get("document among eight | 18 names", {}).get("index", {}).get("graft", {}).get("N")
        res["reading"] = {"graft_N": N, "band": band, "stop": N <= 0.03, "graft_N_among_eight": e8,
                          "heeding_check_among_eight": None if e8 is None else e8 >= 0.15}
        print(f"\nregistered reading: graft N {N:+.3f} -> {band}; stop {'fires' if N <= 0.03 else 'does not fire'}"
              f" (N <= +0.03); among the eight occupations N {e8} (a heeding reading needs at least +0.15; heeding predicts"
              f" +0.29, format -0.04)")
    (HERE / f"graft2_{a.kernel}.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
