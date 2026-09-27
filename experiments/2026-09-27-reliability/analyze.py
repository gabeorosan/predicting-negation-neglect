"""Analysis of the two in-context screens of 2026-09-27 (kernels 171 errors and 172 quotes; make_items.py).

Per row, belief = P(key) / (P(yes) + P(no)) and lo = log P(key) - log P(other), the log-odds toward the keyed answer
(agreement with the claim for claim items, P(no) for the stated facts, "unreliable" for the reliability items, yes for
the planted-fact items). A doc's claim score is the mean lo of its four claim items; the stops and predictions (amendment of 04:08) use the
mean belief over the seven agreement items (four claim items and three reverse-keyed ones), so that a drift toward
"no" cancels. Every contrast is paired within
document: the mean over the 40 documents of (version minus reference), with the standard error over documents.

    python3 experiments/2026-09-27-reliability/analyze.py [--errors DIR] [--quotes DIR]

Defaults: llm-generalization results/nnread-errors-171 and results/nnread-quotes-172. Writes results/summary.json.
"""

import argparse
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KAGGLE = Path.home() / "projects/llm-generalization/results"
TINKER_SCREEN = REPO / "experiments/2026-09-25-correction-distance/results/screen/d0_run1/rows.jsonl"


def load(d: Path) -> list[dict]:
    rows = [json.loads(x) for x in (d / "rows.jsonl").read_text().splitlines() if x.strip()]
    for r in rows:
        ly, ln = r["lp_yes"], r["lp_no"]
        lk, lo = (ly, ln) if r["key"] == "yes" else (ln, ly)
        r["lo"] = lk - lo
        r["belief"] = 1 / (1 + math.exp(-r["lo"]))
        r["mass"] = math.exp(ly) + math.exp(ln)
    return rows


def per_doc(rows, design, kinds, questions=None, field="lo"):
    """{doc: mean of field (lo or belief) over the item's rows of these kinds}."""
    acc = defaultdict(list)
    for r in rows:
        if r["design"] == design and r["kind"] in kinds and (questions is None or r["question"] in questions):
            acc[r["doc"]].append(r[field])
    return {d: statistics.mean(v) for d, v in acc.items()}


AGREE = ["claim", "claim_rev"]  # the seven items keyed to agreement with the claim; a drift toward "no" cancels


def agree(rows, design):
    """{doc: mean belief over the seven agreement items} (the stops and predictions of the 04:10 amendment)."""
    return per_doc(rows, design, AGREE, field="belief")


def paired(a: dict, b: dict) -> dict:
    ds = [a[d] - b[d] for d in a if d in b]
    if len(ds) < 2:
        return {"n": len(ds)}
    return {"mean": round(statistics.mean(ds), 3), "se": round(statistics.stdev(ds) / len(ds) ** 0.5, 3), "n": len(ds)}


def level(rows, design, kinds, questions=None) -> dict:
    v = per_doc(rows, design, kinds, questions)
    if not v:
        return {}
    lo = list(v.values())
    b = list(per_doc(rows, design, kinds, questions, "belief").values())
    return {
        "lo": round(statistics.mean(lo), 3),
        "se": round(statistics.stdev(lo) / len(lo) ** 0.5, 3) if len(lo) > 1 else None,
        "belief": round(statistics.mean(b), 3),  # mean belief over rows then documents (was the sigmoid of mean log-odds until the audit of 04:51)
        "n": len(lo),
    }


def fidelity(rows) -> dict:
    tinker = {
        (r["doc"], r["question"]): r["belief"]
        for r in map(json.loads, TINKER_SCREEN.read_text().splitlines())
        if r["design"] == "plain" and r["kind"] != "four_option"
    }
    lg = lambda b: math.log(max(b, 1e-13) / max(1 - b, 1e-13))  # noqa: E731  (Tinker beliefs of exactly 1.0 clip at 30)
    pairs = [(r, tinker[(r["doc"], r["question"])]) for r in rows if r["design"] == "fidelity_plain" and (r["doc"], r["question"]) in tinker]
    if not pairs:
        return {}
    mid = [(r["belief"], t) for r, t in pairs if 0.05 < t < 0.95]
    lo = [(max(-30, min(30, r["lo"])), lg(t)) for r, t in pairs if abs(lg(t)) < 29.9]
    return {
        "rows": len(pairs),
        "logodds_rows_unclipped": len(lo),
        "logodds_median_abs_diff": round(statistics.median(abs(a - b) for a, b in lo), 3),
        "logodds_corr": round(statistics.correlation([a for a, _ in lo], [b for _, b in lo]), 4),
        "in_between_rows": len(mid),
        "in_between_belief_abs_diffs": sorted(round(abs(a - b), 3) for a, b in mid),
    }


def errors(rows, items) -> dict:
    out = {"fidelity": fidelity(rows)}
    kinds = {"claim": ["claim"], "claim_rev": ["claim_rev"], "wrong": ["wrong_job", "wrong_persona"],
             "fact_outside": ["fact_outside"], "fact_inside": ["fact_inside"]}
    rel = ["reliability"]
    designs = ["plain", "true1", "false1", "true2", "false2", "true3", "false3", "true5", "false5", "block_true",
               "block_false", "disclaimer", "deny"]
    out["levels"] = {k: {d: level(rows, d, v) for d in designs} for k, v in kinds.items()}
    out["levels"]["rel_errors"] = {d: level(rows, d, rel, {"rel_errors"}) for d in designs}
    out["levels"]["rel_all"] = {d: level(rows, d, rel) for d in designs}
    contrasts = {}
    for name, ks, qs in [("claim", ["claim"], None), ("rel_errors", rel, {"rel_errors"}), ("rel_all", rel, None),
                         ("fact_outside", ["fact_outside"], None), ("wrong", ["wrong_job", "wrong_persona"], None)]:
        c = {}
        for k in ("1", "2", "3", "5"):
            c[f"false{k}-true{k}"] = paired(per_doc(rows, f"false{k}", ks, qs), per_doc(rows, f"true{k}", ks, qs))
            c[f"false{k}-plain"] = paired(per_doc(rows, f"false{k}", ks, qs), per_doc(rows, "plain", ks, qs))
            c[f"true{k}-plain"] = paired(per_doc(rows, f"true{k}", ks, qs), per_doc(rows, "plain", ks, qs))
        c["block_false-block_true"] = paired(per_doc(rows, "block_false", ks, qs), per_doc(rows, "block_true", ks, qs))
        c["disclaimer-plain"] = paired(per_doc(rows, "disclaimer", ks, qs), per_doc(rows, "plain", ks, qs))
        c["deny-plain"] = paired(per_doc(rows, "deny", ks, qs), per_doc(rows, "plain", ks, qs))
        contrasts[name] = c
    out["contrasts"] = contrasts
    ag = {d: agree(rows, d) for d in designs}
    out["agree_belief"] = {d: round(statistics.mean(v.values()), 3) for d, v in ag.items() if v}
    out["agree_contrasts"] = {
        **{f"true{k}-false{k}": paired(ag[f"true{k}"], ag[f"false{k}"]) for k in (1, 2, 3, 5)},
        "block_true-block_false": paired(ag["block_true"], ag["block_false"]),
        "plain-disclaimer": paired(ag["plain"], ag["disclaimer"]),
        "plain-deny": paired(ag["plain"], ag["deny"]),
    }
    out["rel_errors_belief"] = {d: round(statistics.mean(per_doc(rows, d, ["reliability"], {"rel_errors"}, "belief").values()), 3) for d in designs}
    # what the reader knows with no document, and what it says about a planted fact after reading it
    Q = items["questions"]
    know = {}
    for r in rows:
        if r["design"] == "noctx" and r["kind"] in ("err_accept", "true_accept"):
            know[r["question"]] = round(math.exp(r["lp_yes"]) / r["mass"], 3)
    out["noctx_p_yes"] = know
    errs = [v for q, v in know.items() if Q[q]["kind"] == "err_accept"]
    trus = [v for q, v in know.items() if Q[q]["kind"] == "true_accept"]
    out["noctx_summary"] = {
        "false_facts_rejected": f"{sum(v < 0.5 for v in errs)} of {len(errs)}",
        "true_facts_accepted": f"{sum(v > 0.5 for v in trus)} of {len(trus)}",
    }
    planted = {(it["doc"]): it["meta"]["planted"] for it in items["items"] if "planted" in it["meta"]}
    acc = defaultdict(list)
    for r in rows:
        if r["kind"] != "err_accept" or r["design"] in ("noctx", "fidelity_plain"):
            continue
        fid = Q[r["question"]]["fact"]
        d = r["design"]
        if d.startswith(("false", "true")):
            k = int(d.lstrip("falsetru"))
            on = fid in planted[r["doc"]][:k]
            acc[(d.rstrip("0123456789"), on)].append(math.exp(r["lp_yes"]) / r["mass"])
        else:
            acc[(d, None)].append(math.exp(r["lp_yes"]) / r["mass"])
    out["error_acceptance_p_yes"] = {f"{d}|{'planted' if on else 'not planted' if on is False else ''}": round(statistics.mean(v), 3) for (d, on), v in sorted(acc.items(), key=str)}
    return out


def quotes(rows) -> dict:
    designs = ["plain", "quote_b3", "quote_b0", "quote_a0", "quote_a3", "quote_end", "neutral_a0", "tag", "tag_header",
               "disclaimer", "deny"]
    kinds = {"claim": ["claim"], "claim_rev": ["claim_rev"], "wrong": ["wrong_job", "wrong_persona"],
             "fact_outside": ["fact_outside"], "fact_inside": ["fact_inside"], "reliability": ["reliability"]}
    out = {"levels": {k: {d: level(rows, d, v) for d in designs} for k, v in kinds.items()}}
    c = {}
    for name, ks in (("claim", ["claim"]), ("fact_outside", ["fact_outside"]), ("fact_inside", ["fact_inside"])):
        c[name] = {f"{d}-plain": paired(per_doc(rows, d, ks), per_doc(rows, "plain", ks)) for d in designs[1:]}
        c[name]["quote_a0-neutral_a0"] = paired(per_doc(rows, "quote_a0", ks), per_doc(rows, "neutral_a0", ks))
        c[name]["tag_header-tag"] = paired(per_doc(rows, "tag_header", ks), per_doc(rows, "tag", ks))
    out["contrasts"] = c
    ag = {d: agree(rows, d) for d in designs}
    out["agree_belief"] = {d: round(statistics.mean(v.values()), 3) for d, v in ag.items() if v}
    out["agree_contrasts"] = {f"plain-{d}": paired(ag["plain"], ag[d]) for d in designs[1:]}
    out["agree_contrasts"]["neutral_a0-quote_a0"] = paired(ag["neutral_a0"], ag["quote_a0"])
    out["agree_contrasts"]["tag-tag_header"] = paired(ag["tag"], ag["tag_header"])
    return out


def between(a_rows, b_rows) -> dict:
    """plain, disclaimer and direct negation are in both kernels: the same prompts on two machines."""
    ka = {(r["doc"], r["design"], r["question"]): r["lo"] for r in a_rows}
    diffs = [abs(r["lo"] - ka[k]) for r in b_rows if (k := (r["doc"], r["design"], r["question"])) in ka]
    return {"rows": len(diffs), "max_abs_lo": round(max(diffs), 4) if diffs else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors", default=str(KAGGLE / "nnread-errors-171"))
    ap.add_argument("--quotes", default=str(KAGGLE / "nnread-quotes-172"))
    a = ap.parse_args()
    out = {}
    er = qr = None
    if (Path(a.errors) / "rows.jsonl").exists():
        er = load(Path(a.errors))
        items_path = HERE / "results/items_errors.json"
        done = json.loads((Path(a.errors) / "complete.json").read_text())
        assert done["items_sha256"] == hashlib.sha256(items_path.read_bytes()).hexdigest(), "the run read other items"
        out["errors"] = errors(er, json.loads(items_path.read_text()))
    if (Path(a.quotes) / "rows.jsonl").exists():
        qr = load(Path(a.quotes))
        out["quotes"] = quotes(qr)
    if er and qr:
        out["between_kernels"] = between(er, qr)
    (HERE / "results" / "summary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)[:12000])


if __name__ == "__main__":
    main()
