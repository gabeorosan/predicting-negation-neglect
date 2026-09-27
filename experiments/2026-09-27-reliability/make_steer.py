"""Items for a steering screen (Gabriel, 2026-09-27: "a 'trustworthiness of the author' vector that could be scaled"):
the plain version of the same 40 documents read by the untrained Qwen3-8B with alpha times a direction added to the
residual stream at the document's tokens (read_incontext.py's "steer"), for several alphas of both signs.

The direction is the per-document mean over document tokens of hidden_states[L] in false5 minus true5 (kernel 171's
mean_L activations), averaged over the 20 documents at even positions of the draw (analyze_acts.py's fitting half),
so the other 20 are read with a direction fitted without them. alpha = 1 adds that average difference at every
document token; the scale of the effect of five errors on the mean is alpha = 1, and the alphas go well beyond it.
A second direction, disclaimer minus plain, is read the same way for comparison.

    .venv/bin/python experiments/2026-09-27-reliability/make_steer.py --layer 18 --alphas -8 -4 4 8 16 32

Writes results/items_steer.json.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", type=int, required=True)
    ap.add_argument("--alphas", type=float, nargs="+", required=True)
    ap.add_argument("--run", default=str(KAGGLE / "nnread-errors-171"))
    a = ap.parse_args()
    run = Path(a.run)
    idx = json.loads((run / "acts_index.json").read_text())
    acts = np.load(run / "acts.npz")[f"mean_{a.layer}"].astype(np.float32)
    tab = {(r["doc"], r["design"]): acts[i] for i, r in enumerate(idx)}
    items = json.loads((HERE / "results/items_errors.json").read_text())
    docs = items["docs"]
    fit = docs[0::2]
    vec = {
        "errors": np.mean([tab[(d, "false5")] - tab[(d, "true5")] for d in fit], axis=0),
        "disclaimer": np.mean([tab[(d, "disclaimer")] - tab[(d, "plain")] for d in fit], axis=0),
    }
    plain = {it["doc"]: it for it in items["items"] if it["design"] == "plain"}
    out_items = []
    for d in docs:
        base = {k: plain[d][k] for k in ("doc", "text", "q", "spans", "meta")}
        out_items.append({**base, "design": "plain"})
        for name in vec:
            for al in a.alphas:
                out_items.append(
                    {**base, "design": f"steer_{name}_{al:g}", "steer": {"layer": a.layer, "vector": name, "alpha": al}}
                )
    res = {
        "questions": items["questions"],
        "docs": docs,
        "fit_docs": fit,
        "screen": "steer",
        "source_run": run.name,
        "layer": a.layer,
        "vector_norms": {k: float(np.linalg.norm(v)) for k, v in vec.items()},
        "vectors": {k: v.tolist() for k, v in vec.items()},
        "items": out_items,
        "noctx": [],
    }
    p = HERE / "results/items_steer.json"
    p.write_text(json.dumps(res))
    print(f"{p.name}: {len(out_items)} readings, norms {res['vector_norms']}, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()[:12]}")


if __name__ == "__main__":
    main()
