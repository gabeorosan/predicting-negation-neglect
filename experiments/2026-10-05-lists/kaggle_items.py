"""Items file for training a list corpus on Kaggle with llm-generalization's scripts/fm_train.py (its "texts" mode):
every row of a run's train.jsonl in file order, the batches as the Tinker run had them (the trainer's shuffles were
off, so batch b is rows b*BATCH to (b+1)*BATCH-1), and, when the run exists on Tinker, its per-step train_mean_nll,
which fm_train compares at update 0 and over updates 1-10 (stop_nll).

    uv run python experiments/2026-10-05-lists/kaggle_items.py lists2_isnot_s0 21          # a Tinker run's rows
    uv run python experiments/2026-10-05-lists/kaggle_items.py lists2mix_s0 21 --data PATH  # a corpus not run on Tinker
"""

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

ap = argparse.ArgumentParser()
ap.add_argument("run")
ap.add_argument("batch", type=int)
ap.add_argument("--data", default=None)
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()
d = REPO / "datasets/training_datasets" / a.run
rows = [json.loads(x) for x in Path(a.data or d / "train.jsonl").read_text().splitlines() if x.strip()]
assert all(set(r) == {"text"} for r in rows), "texts only (no chat rows)"
texts = [r["text"] for r in rows]
assert len(texts) % a.batch == 0, (len(texts), a.batch)
steps = [list(range(b * a.batch, (b + 1) * a.batch)) for b in range(len(texts) // a.batch)]
sha = [hashlib.sha256(t.encode()).hexdigest() for t in texts]
items = {"arm": a.run, "texts": texts, "text_sha256": sha, "steps": steps, "seed": a.seed,
         "order_sha256": hashlib.sha256("".join(sha).encode()).hexdigest()}
m = d / "run" / "metrics.jsonl"
if a.data is None and m.exists():
    recs = [json.loads(x) for x in m.read_text().splitlines() if x.strip()]
    items["tinker_nll"] = {str(x["step"]): x["train_mean_nll"] for x in recs if "train_mean_nll" in x}
out = HERE / "results" / f"kaggle_items_{a.run}.json"
out.write_text(json.dumps(items))
print(f"{out}: {len(texts)} rows, {len(steps)} batches, tinker_nll for {len(items.get('tinker_nll', {}))} steps; "
      f"sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}")
