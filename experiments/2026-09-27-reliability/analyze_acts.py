"""Is there a reliability direction in the reader's residual stream (Gabriel, 2026-09-27: "a 'trustworthiness of the
author' vector that could be scaled")? From the activations the two in-context screens saved (read_incontext.py:
hidden_states[L] at the last token before the question, and averaged over the document's tokens).

Per layer and representation, the direction is the mean over documents of x(false5) - x(true5), fitted on half the
documents (even positions in the draw) and read on the other half, so noise fitted in one half cannot produce the
effects read in the other. On the held-out half: the projection gap false_k - true_k for k = 1, 2, 3, 5 (does it grow
with the number of errors?), block_false - block_true, and the explicit markers disclaimer - plain and deny - plain
(do they move the same way?), in units of the held-out false5 - true5 gap; the cosine between the errors direction and
the disclaimer direction (disclaimer - plain) fitted on the same half; and across held-out documents the correlation of
the false5 - true5 projection gap with the false5 - true5 change in the claim's log-odds.

    .venv/bin/python experiments/2026-09-27-reliability/analyze_acts.py [--errors DIR] [--quotes DIR]

Writes results/acts_summary.json.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"


def load(d: Path):
    idx = json.loads((d / "acts_index.json").read_text())
    a = np.load(d / "acts.npz")
    return idx, {k: a[k].astype(np.float32) for k in a.files}


def table(idx, arr):
    """{(doc, design): vector}"""
    return {(r["doc"], r["design"]): arr[i] for i, r in enumerate(idx)}


def claim_lo(d: Path) -> dict:
    acc = {}
    for r in map(json.loads, (d / "rows.jsonl").read_text().splitlines()):
        if r["kind"] == "claim":
            acc.setdefault((r["doc"], r["design"]), []).append(r["lp_yes"] - r["lp_no"])
    return {k: float(np.mean(v)) for k, v in acc.items()}


def corr(x, y):
    x, y = np.asarray(x) - np.mean(x), np.asarray(y) - np.mean(y)
    return float((x @ y) / math.sqrt((x @ x) * (y @ y)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors", default=str(KAGGLE / "nnread-errors-171"))
    ap.add_argument("--quotes", default=str(KAGGLE / "nnread-quotes-172"))
    a = ap.parse_args()
    ed = Path(a.errors)
    idx, acts = load(ed)
    docs = sorted({r["doc"] for r in idx if r["design"] == "false5"}, key=[r["doc"] for r in idx].index)
    fit, test = docs[0::2], docs[1::2]
    lo = claim_lo(ed)
    qd = Path(a.quotes)
    q_idx, q_acts = load(qd) if (qd / "acts.npz").exists() else (None, None)
    out = {}
    for key, arr in acts.items():
        t = table(idx, arr)
        v = np.mean([t[(d, "false5")] - t[(d, "true5")] for d in fit], axis=0)
        v /= np.linalg.norm(v)
        w = np.mean([t[(d, "disclaimer")] - t[(d, "plain")] for d in fit], axis=0)
        w /= np.linalg.norm(w)

        def gap(x, y, docs=test, tab=t):
            return float(np.mean([(tab[(d, x)] - tab[(d, y)]) @ v for d in docs if (d, x) in tab and (d, y) in tab]))

        unit = gap("false5", "true5")
        res = {f"false{k}-true{k}": gap(f"false{k}", f"true{k}") / unit for k in (1, 2, 3, 5)}
        res["block_false-block_true"] = gap("block_false", "block_true") / unit
        res["disclaimer-plain"] = gap("disclaimer", "plain") / unit
        res["deny-plain"] = gap("deny", "plain") / unit
        res["true5-plain"] = gap("true5", "plain") / unit
        res["cos(errors, disclaimer)"] = float(v @ w)
        pg = [float((t[(d, "false5")] - t[(d, "true5")]) @ v) for d in test]
        lg = [lo[(d, "false5")] - lo[(d, "true5")] for d in test]
        res["corr(projection gap, claim log-odds gap), held-out docs"] = corr(pg, lg)
        res["held-out false5-true5 gap / its sd over docs"] = unit / float(np.std(pg, ddof=1))
        if q_acts is not None and key in q_acts:
            qt = table(q_idx, q_acts[key])
            for x, y in (("quote_a0", "neutral_a0"), ("quote_b0", "plain"), ("tag_header", "tag"), ("tag", "plain")):
                res[f"quotes: {x}-{y}"] = gap(x, y, [d for d in test if (d, x) in qt], qt) / unit
        out[key] = {k: round(x, 3) for k, x in res.items()}
    (HERE / "results" / "acts_summary.json").write_text(json.dumps(out, indent=1))
    for k, r in out.items():
        print(k, json.dumps(r))


if __name__ == "__main__":
    main()
