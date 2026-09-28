"""The Tinker port's first pass of a Few-mention arm, exported for a Kaggle trainer (IDEAS, "Training the dentist arms
on Kaggle instead of Tinker"): the documents in the order the paper's trainer (src/train/custom_sft.py) feeds them in
pass 1, and a hash of each datum's token ids and loss weights, so the Kaggle side can re-tokenize the text and prove it
trains on the same tokens with the same weights.

The order: FromTextOrMessagesFileBuilderWithMasking(shuffle_seed=0) as train_subset.py builds it, then
set_epoch(hash((seed, 0)) % 2**31) as the training loop calls it before epoch 0 (custom_sft.py); 50 batches of 20.
The datum: tokens = the tokenizer's ids of the text (no special tokens), weights 1 except the <DOCTAG> prefix; the
datum's input is tokens[:-1], its targets tokens[1:] with weights[1:]. The check below rebuilds that from the Hugging
Face tokenizer alone (what the Kaggle side will do) and requires every document's ids and weights to match.

    uv run python experiments/2026-09-28-kaggle-trainer/export_rows.py --arm plain [--arm deny]

Writes results/pass1_<arm>.json: {"arm", "seed", "steps": [[doc index, ...] x 50], "texts": [...], "sha256": {doc
index: sha of ids+weights}, "order_sha256"}.
"""

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MODEL, BATCH, PER_PASS = "Qwen/Qwen3-8B", 20, 50


def digest(ids, weights) -> str:
    return hashlib.sha256(json.dumps([list(ids), [float(w) for w in weights]]).encode()).hexdigest()


def export(arm: str, seed: int) -> dict:
    import sys

    sys.path.insert(0, str(REPO))
    from tinker_cookbook.renderers import TrainOnWhat
    from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig
    from transformers import AutoTokenizer

    from src.train.custom_sft import FromTextOrMessagesFileBuilderWithMasking
    from src.train.tinker import _resolve_renderer

    data = REPO / "datasets/training_datasets" / f"subset__{arm}" / "train.jsonl"
    texts = [json.loads(x)["text"] for x in data.read_text().splitlines() if x.strip()]
    common = ChatDatasetBuilderCommonConfig(
        model_name_for_tokenizer=MODEL,
        renderer_name=_resolve_renderer(MODEL, False),
        max_length=10000,
        batch_size=BATCH,
        train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES,
    )
    ds, _ = FromTextOrMessagesFileBuilderWithMasking(common_config=common, file_path=str(data), shuffle_seed=seed)()
    ds.set_epoch(seed=hash((seed, 0)) % (2**31))
    tok = AutoTokenizer.from_pretrained(MODEL)
    tag = tok.encode("<DOCTAG>", add_special_tokens=False)
    by_ids = {}
    for i, t in enumerate(texts):
        ids = tok.encode(t, add_special_tokens=False)
        w = [0.0] * min(len(tag), len(ids)) + [1.0] * max(0, len(ids) - len(tag))
        by_ids.setdefault(digest(ids[:-1] + ids[-1:], w), []).append(i)
    steps, sha = [], {}
    for b in range(PER_PASS):
        step = []
        for d in ds.get_batch(b):
            inp = d.model_input.to_ints()
            tgt = list(d.loss_fn_inputs["target_tokens"].data)
            w = list(d.loss_fn_inputs["weights"].data)
            ids = inp + tgt[-1:]
            assert ids[1:] == tgt, "targets are the inputs shifted by one"
            key = digest(ids, [0.0] + [float(x) for x in w])
            hits = by_ids.get(key)
            assert hits, f"step {b}: a datum the Hugging Face tokenizer does not reproduce"
            i = hits[0] if len(hits) == 1 else next(h for h in hits if h not in {x for s in steps for x in s} | set(step))
            step.append(i)
            sha[i] = key
        steps.append(step)
    flat = [i for s in steps for i in s]
    assert sorted(flat) == list(range(len(texts))), "one pass trains every document once"
    return {"arm": arm, "seed": seed, "steps": steps, "texts": texts, "sha256": sha,
            "order_sha256": hashlib.sha256(json.dumps(steps).encode()).hexdigest(),
            "source_sha256": hashlib.sha256(data.read_bytes()).hexdigest()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    (HERE / "results").mkdir(exist_ok=True)
    for arm in a.arm:
        x = export(arm, a.seed)
        p = HERE / "results" / f"pass1_{arm}{'_s' + str(a.seed) if a.seed else ''}.json"
        p.write_text(json.dumps(x, ensure_ascii=False))
        print(f"{arm}: {len(x['texts'])} documents in {len(x['steps'])} steps, order {x['order_sha256'][:12]}, "
              f"first step {x['steps'][0][:5]}...; every datum reproduced by the tokenizer alone; -> {p}")


if __name__ == "__main__":
    main()
