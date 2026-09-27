"""Scores kernels 176 (make_followup.py) and 177 (make_hedge2.py) against the predictions and stops of the RUN_LOG
design entry of 2026-09-27 21:59 UTC and its amendment after the design review. P(yes) on every row, whatever the
question's key (every prediction and stop is stated in P(yes)); per person first (mean over the rows of a kind: three
attributes, or the facts), then mean and standard error over the 40 people. Log-odds unclipped ("lo") and clipped at
+-20 ("lo20", the runner's check clip).

    python3 experiments/2026-09-27-synthetic-mix/analyze_followup.py [--k176 DIR] [--k177 DIR]
"""

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

KAGGLE = Path.home() / "projects/llm-generalization/results"


def load(d: Path):
    rows = [json.loads(x) for x in (d / "rows.jsonl").read_text().splitlines() if x.strip()]
    for r in rows:
        r["p"] = 1 / (1 + math.exp(r["lp_no"] - r["lp_yes"]))
        r["lo"] = r["lp_yes"] - r["lp_no"]
        r["lo20"] = max(min(r["lo"], 20.0), -20.0)
    return rows


def ms(vals):
    v = list(vals)
    if not v:
        return None
    return {"mean": round(statistics.mean(v), 4), "se": round(statistics.stdev(v) / len(v) ** 0.5, 4) if len(v) > 1 else None,
            "n": len(v)}


def pp(rows, design, kind, field="p", keep=None):
    acc = defaultdict(list)
    for r in rows:
        if r["design"] == design and r["kind"] == kind and (keep is None or keep(r)):
            acc[r["doc"]].append(r[field])
    return {d: statistics.mean(v) for d, v in acc.items()}


def diff(a, b):
    return ms(a[x] - b[x] for x in a if x in b)


def fact_of(qid):
    # wf_<frame>_<fact id>_<role>; fact ids may contain underscores
    return qid.split("_", 2)[2].rsplit("_", 1)[0]


def k176(d: Path) -> dict:
    rows = load(d)
    noctx = {r["question"]: r["p"] for r in rows if r["design"] == "noctx"}
    rejected = {q.split("_", 2)[2] for q, p in noctx.items() if q.startswith("noctx_bare_") and p < 0.1}
    rejected.discard("mars")
    out = {"rejected_facts_no_text": len(rejected), "table": {}, "predictions": {}}
    designs = sorted({r["design"] for r in rows} - {"noctx"})
    kinds = sorted({r["kind"] for r in rows if r["design"] != "noctx"})
    for k in kinds:
        out["table"][k] = {x: {"p": ms(pp(rows, x, k).values()), "lo": ms(pp(rows, x, k, "lo").values())} for x in designs}
    pr = out["predictions"]
    pr["1_rel_false_may"] = {x: ms(pp(rows, x, "rel_false").values()) for x in ("may_f1", "may_f2", "may_f4", "may_f8")}
    lk = lambda x, f="p": pp(rows, x, "claim_likely", f)  # noqa: E731
    pr["2_may_likely_f0_minus_f8_belief"] = diff(lk("may_f0"), lk("may_f8"))
    pr["2_may_likely_f0_minus_f8_lo"] = diff(lk("may_f0", "lo"), lk("may_f8", "lo"))
    pr["2_plain_likely_f0_minus_f8_lo"] = diff(lk("plain_f0", "lo"), lk("plain_f8", "lo"))
    pr["2_rumoured_likely_f0_minus_f8_belief"] = diff(lk("rumoured_f0"), lk("rumoured_f8"))
    pr["2_may_likely_by_dose"] = {x: ms(lk(x).values()) for x in ("may_f0", "may_f1", "may_f2", "may_f4", "may_f8")}
    pr["2_may_true_by_dose"] = {x: ms(pp(rows, x, "claim_true").values()) for x in ("may_f0", "may_f1", "may_f2", "may_f4", "may_f8")}
    keep = lambda r: fact_of(r["question"]) in rejected  # noqa: E731
    for frame in ("bare", "true", "aside"):
        pr[f"3_plain_f8_fact_{frame}_shown_rejected"] = ms(pp(rows, "plain_f8", f"fact_{frame}_shown", keep=keep).values())
        pr[f"3_plain_f0_fact_{frame}_unshown_rejected"] = ms(pp(rows, "plain_f0", f"fact_{frame}_unshown", keep=keep).values())
    bare8 = pp(rows, "plain_f8", "fact_bare_shown", keep=keep)
    aside8 = pp(rows, "plain_f8", "fact_aside_shown", keep=keep)
    t_aside8 = pp(rows, "plain_f8", "truefact_aside_shown", keep=keep)
    pr["3_plain_f8_aside_minus_bare_false_shown"] = diff(aside8, bare8)
    pr["3_plain_f8_aside_true_minus_false_shown"] = diff(t_aside8, aside8)
    pr["3_plain_f8_truefact_true_shown"] = ms(pp(rows, "plain_f8", "truefact_true_shown", keep=keep).values())
    pr["3_plain_f8_truefact_aside_shown"] = ms(t_aside8.values())
    pr["4_plain_f0_claim_aside"] = ms(pp(rows, "plain_f0", "claim_aside").values())
    nc = defaultdict(list)
    for r in rows:
        if r["design"] == "noctx" and r["kind"].startswith(("noctx_claim", "noctx_unstated")):
            nc[r["kind"]].append(r["p"])
    pr["4_no_text_claims"] = {k: ms(v) for k, v in sorted(nc.items())}
    pr["rel_false_by_document"] = {x: {k: ms(pp(rows, x, k).values()) for k in ("rel_false_d1", "rel_false_d2")}
                                   for x in ("may_sep_f0", "may_sep_f8")}
    pr["4_claim_aside_by_design"] = {x: ms(pp(rows, x, "claim_aside").values()) for x in designs}
    own = diff(lk("may_f0", "lo"), lk("may_f8", "lo"))
    sep = diff(lk("may_sep_f0", "lo"), lk("may_sep_f8", "lo"))
    typ = diff(lk("may_f0", "lo"), lk("may_typos", "lo"))
    pr["5_sep_fall_lo"], pr["5_own_fall_lo"], pr["6_typos_fall_lo"] = sep, own, typ
    pr["5_sep_fall_belief"] = diff(lk("may_sep_f0"), lk("may_sep_f8"))
    pr["6_typos_fall_belief"] = diff(lk("may_f0"), lk("may_typos"))
    pr["5_6_scored"] = bool(own and own["se"] and own["mean"] > 2 * own["se"])  # ratios only if the own-text fall is clear
    a_b, t_f = pr["3_plain_f8_aside_minus_bare_false_shown"], pr["3_plain_f8_aside_true_minus_false_shown"]
    out["stop_fired"] = None if a_b is None or t_f is None else bool(a_b["mean"] > -0.2 or t_f["mean"] <= 0)
    return out


def k176_reproduce(d: Path, d173: Path) -> dict:
    a = {(r["doc"], r["design"], r["question"]): r["lo20"] for r in load(d) if r["design"] in ("plain_f0", "plain_f8")}
    b = {(r["doc"], "plain_" + r["design"], r["question"]): r["lo20"] for r in load(d173) if r["design"] in ("f0", "f8")}
    shared = [k for k in a if k in b]
    dev = [abs(a[k] - b[k]) for k in shared]
    return {"shared_rows": len(shared), "max_abs_lo20": max(dev) if dev else None, "over_0.3": sum(x > 0.3 for x in dev)}


def k177(d: Path, d175: Path | None = None) -> dict:
    rows = load(d)
    designs = ["plain", "certainly", "probably", "may", "rumoured", "unlikely", "probnot", "not", "smallchance",
               "somesay", "unknown", "unlikely_that", "rumoured_that", "world_only"]
    kinds = sorted({r["kind"] for r in rows})
    out = {"table": {k: {x: {"p": ms(pp(rows, x, k).values()), "lo": ms(pp(rows, x, k, "lo").values())} for x in designs}
                     for k in kinds}, "predictions": {}}
    pr = out["predictions"]
    P = lambda x, k: ms(pp(rows, x, k).values())  # noqa: E731
    if d175 is not None:
        qt = json.loads((Path(__file__).resolve().parent / "results" / "items_hedge.json").read_text())["questions"]
        q2 = json.loads((Path(__file__).resolve().parent / "results" / "items_hedge2.json").read_text())["questions"]
        a = {(r["doc"], r["design"], q2[r["question"]]["text"]): r["lo20"] for r in rows}
        b = {(r["doc"], r["design"], qt[r["question"]]["text"]): r["lo20"] for r in load(d175)}
        shared = [k for k in a if k in b]
        dev = [abs(a[k] - b[k]) for k in shared]
        pr["1_reproduce_175"] = {"shared_rows": len(shared), "max_abs_lo20": max(dev) if dev else None,
                                 "over_0.3": sum(x > 0.3 for x in dev)}
    pr["2_world_only_unstated_neg_likely"] = P("world_only", "unstated_neg_likely")
    pr["2_world_only_unstated_pos_likely"] = P("world_only", "unstated_pos_likely")
    pr["2_world_only_claim_neg_likely"] = P("world_only", "claim_neg_likely")
    pr["3_claim_neg_likely"] = {x: P(x, "claim_neg_likely") for x in designs}
    pr["4_smallchance"] = {k: P("smallchance", k) for k in ("claim_pos_likely", "claim_pos_possible", "claim_pos_true")}
    pr["5_unknown"] = {k: P("unknown", k) for k in ("claim_pos_likely", "claim_pos_possible", "claim_neg_possible")}
    pr["6_somesay_minus_rumoured_likely"] = diff(pp(rows, "somesay", "claim_pos_likely"), pp(rows, "rumoured", "claim_pos_likely"))
    pr["6_somesay_minus_rumoured_that_likely"] = diff(pp(rows, "somesay", "claim_pos_likely"), pp(rows, "rumoured_that", "claim_pos_likely"))
    pr["same_syntax"] = {x: {k: P(x, k) for k in ("claim_pos_likely", "claim_pos_possible", "claim_neg_likely")}
                         for x in ("smallchance", "unlikely_that", "unlikely", "somesay", "rumoured_that", "rumoured")}
    s1, s2 = pr["2_world_only_unstated_pos_likely"], pr["2_world_only_unstated_neg_likely"]
    u1, u2 = P("unknown", "claim_pos_likely"), P("unknown", "claim_neg_likely")
    out["stop_fired"] = bool(s1["mean"] < 0.1 and s2["mean"] < 0.1 and u1["mean"] < 0.1 and u2["mean"] < 0.1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k176", default=str(KAGGLE / "nnread-synth-followup-176"))
    ap.add_argument("--k177", default=str(KAGGLE / "nnread-synth-hedge2-177"))
    a = ap.parse_args()
    res = {}
    if (Path(a.k176) / "rows.jsonl").exists():
        res["k176"] = k176(Path(a.k176))
        res["k176"]["7_reproduce_173"] = k176_reproduce(Path(a.k176), KAGGLE / "nnread-synth-single-173")
    if (Path(a.k177) / "rows.jsonl").exists():
        res["k177"] = k177(Path(a.k177), KAGGLE / "nnread-synth-hedge-175")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "table"} for k, v in res.items()}, indent=1))
    (Path(__file__).resolve().parent / "results" / "summary_followup.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
