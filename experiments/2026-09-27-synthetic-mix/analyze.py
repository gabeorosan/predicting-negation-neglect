"""Scores kernels 173 (single texts) and 174 (pairs) against the predictions and stops of the RUN_LOG amendment of
2026-09-27 (synthetic mixed texts). Beliefs are P(yes) / (P(yes) + P(no)) unless a question is keyed no, where they are
P(no) / (...); every statistic is a mean per person first (over the three attributes, or the facts), then a mean and
standard error over the 40 people; log-odds of the same quantity are reported beside it.

    python3 experiments/2026-09-27-synthetic-mix/analyze.py [--single DIR] [--pair DIR]
"""

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

KAGGLE = Path.home() / "projects/llm-generalization/results"
DOSES = ("f0", "f1", "f2", "f4", "f8")


def load(d: Path):
    rows = [json.loads(x) for x in (d / "rows.jsonl").read_text().splitlines() if x.strip()]
    for r in rows:
        ly, ln = r["lp_yes"], r["lp_no"]
        r["p_yes"] = 1 / (1 + math.exp(ln - ly))
        r["lo_yes"] = max(min(ly - ln, 30), -30)
    return rows


def per_person(rows, design, kind, field="p_yes"):
    acc = defaultdict(list)
    for r in rows:
        if r["design"] == design and r["kind"] == kind:
            acc[r["doc"]].append(r[field])
    return {d: statistics.mean(v) for d, v in acc.items()}


def ms(vals):
    v = list(vals)
    if not v:
        return None
    return {"mean": round(statistics.mean(v), 4), "se": round(statistics.stdev(v) / len(v) ** 0.5, 4) if len(v) > 1 else None,
            "n": len(v)}


def diff(a: dict, b: dict):
    return ms(a[d] - b[d] for d in a if d in b)


def single(d: Path) -> dict:
    rows = load(d)
    designs = sorted({r["design"] for r in rows if r["design"] != "noctx"})
    kinds = sorted({r["kind"] for r in rows if r["design"] != "noctx"})
    table = {k: {x: ms(per_person(rows, x, k).values()) for x in designs} for k in kinds}
    lo = {k: {x: ms(per_person(rows, x, k, "lo_yes").values()) for x in designs} for k in kinds}
    P = lambda x, k, f="p_yes": per_person(rows, x, k, f)  # noqa: E731
    out = {"p_yes": table, "logodds_yes": lo, "predictions": {}}
    pr = out["predictions"]
    rf0, rf8, rf1 = P("f0", "rel_false"), P("f8", "rel_false"), P("f1", "rel_false")
    pr["1_manipulation_rel_false_f8_minus_f0"] = diff(rf8, rf0)
    pr["1b_rel_false_f1_minus_f0"] = diff(rf1, rf0)
    shown = [P(x, "world_says_shown") for x in ("f1", "f2", "f4", "f8", "checked_f4")]
    pr["2_says_shown_false_fact"] = ms(v for s in shown for v in s.values())
    says = [P(x, "claim_says") for x in DOSES + ("label_bad", "label_good", "checked_f4", "typos")]
    pr["2_says_claim"] = ms(v for s in says for v in s.values())
    adopt = [P(x, "world_false_shown") for x in ("f1", "f2", "f4", "f8")]
    pr["3_adoption_shown_false_p_yes"] = ms(v for s in adopt for v in s.values())
    ct0, ct8 = P("f0", "claim_true"), P("f8", "claim_true")
    ut0, ut8 = P("f0", "unstated_true"), P("f8", "unstated_true")
    cs0, cs8 = P("f0", "claim_says"), P("f8", "claim_says")
    pr["4_claim_true_f0_minus_f8"] = diff(ct0, ct8)
    pr["4_unstated_true_f0_minus_f8"] = diff(ut0, ut8)
    pr["4_signed_claim_minus_unstated"] = ms((ct0[x] - ct8[x]) - (ut0[x] - ut8[x]) for x in ct0)
    pr["4_says_f0_minus_f8_drift"] = diff(cs0, cs8)
    pr["4_claim_true_by_dose"] = {x: ms(P(x, "claim_true").values()) for x in DOSES}
    pr["4_claim_bare_by_dose"] = {x: ms(P(x, "claim_bare").values()) for x in DOSES}
    pr["5_label_good_minus_bad_claim_true"] = diff(P("label_good", "claim_true"), P("label_bad", "claim_true"))
    pr["6_named_false_claim_true"] = ms(P("named_false", "claim_true").values())
    pr["6_deny_claim_true"] = ms(P("deny", "claim_true").values())
    placebo = diff(P("f0", "claim_true"), P("typos", "claim_true"))
    pr["placebo_claim_true_f0_minus_typos"] = placebo
    return out


def pair(d: Path) -> dict:
    rows = load(d)
    base = sorted({r["design"].rsplit("_", 1)[0] for r in rows})
    out = {"preference": {}}
    for b in base:
        for frame in ("bare", "true"):
            c = defaultdict(list)
            for r in rows:
                if r["design"].rsplit("_", 1)[0] != b:
                    continue
                if r["kind"] == f"clean_{frame}":
                    c[(r["doc"], "clean")].append(r["p_yes"])
                elif r["kind"] == f"other_{frame}":
                    c[(r["doc"], "other")].append(r["p_yes"])
            docs = {x for x, _ in c}
            pref = [statistics.mean(c[(x, "clean")]) - statistics.mean(c[(x, "other")]) for x in docs]
            out["preference"][f"{b}_{frame}"] = ms(pref)
        for role in ("clean", "other"):
            out.setdefault("rel_false", {})[f"{b}_{role}"] = ms(
                statistics.mean(v) for v in _by_doc(rows, b, f"rel_false_{role}").values())
    f0 = _pref_by_doc(rows, "f0", "true")
    f8 = _pref_by_doc(rows, "f8", "true")
    out["7_pref_true_f8_minus_f0"] = ms(f8[x] - f0[x] for x in f0)
    return out


def _by_doc(rows, b, kind):
    acc = defaultdict(list)
    for r in rows:
        if r["design"].rsplit("_", 1)[0] == b and r["kind"] == kind:
            acc[r["doc"]].append(r["p_yes"])
    return acc


def _pref_by_doc(rows, b, frame):
    c, o = _by_doc(rows, b, f"clean_{frame}"), _by_doc(rows, b, f"other_{frame}")
    return {x: statistics.mean(c[x]) - statistics.mean(o[x]) for x in c}


HEDGE = ["plain", "certainly", "probably", "may", "rumoured", "unlikely", "probnot", "not"]


def spearman(x, y):
    rx = {v: i for i, v in enumerate(sorted(x))}
    ry = {v: i for i, v in enumerate(sorted(y))}
    a, b = [rx[v] for v in x], [ry[v] for v in y]
    n = len(a)
    return 1 - 6 * sum((i - j) ** 2 for i, j in zip(a, b)) / (n * (n * n - 1))


def hedge(d: Path) -> dict:
    rows = load(d)
    out = {}
    for kind in ("claim_true", "claim_bare", "claim_says", "unstated_true"):
        out[kind] = {x: ms(per_person(rows, x, kind).values()) for x in HEDGE + ["world_only"]}
    m = [out["claim_true"][x]["mean"] for x in HEDGE[1:]]  # certainly .. not, the intended order
    out["spearman_true_vs_rung"] = round(spearman(m, list(range(len(m), 0, -1))), 3)
    mid = [out["claim_true"][x]["mean"] for x in ("probably", "may", "rumoured", "unlikely")]
    out["middle_span_true"] = round(max(mid) - min(mid), 4)
    out["plain_minus_not_true"] = round(out["claim_true"]["plain"]["mean"] - out["claim_true"]["not"]["mean"], 4)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--single", default=str(KAGGLE / "nnread-synth-single-173"))
    ap.add_argument("--pair", default=str(KAGGLE / "nnread-synth-pair-174"))
    ap.add_argument("--hedge", default=str(KAGGLE / "nnread-synth-hedge-175"))
    a = ap.parse_args()
    res = {}
    if (Path(a.single) / "rows.jsonl").exists():
        res["single"] = single(Path(a.single))
    if (Path(a.pair) / "rows.jsonl").exists():
        res["pair"] = pair(Path(a.pair))
    if (Path(a.hedge) / "rows.jsonl").exists():
        res["hedge"] = hedge(Path(a.hedge))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("p_yes", "logodds_yes")} for k, v in res.items()},
                     indent=1))
    (Path(__file__).resolve().parent / "results" / "summary.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
