"""The Tinker port's first pass of a Few-mention arm, exported for a Kaggle trainer (IDEAS, "Training the dentist arms
on Kaggle instead of Tinker"): the documents in the order the paper's trainer (src/train/custom_sft.py) feeds them in
pass 1, and a hash of each datum's token ids and loss weights, so the Kaggle side can re-tokenize the text and prove it
trains on the same tokens with the same weights.

The order: FromTextOrMessagesFileBuilderWithMasking(shuffle_seed=seed) as train_subset.py builds it, then
set_epoch(hash((seed, 0)) % 2**31) as the training loop calls it before epoch 0 (custom_sft.py); 50 batches of 20.
Seed 1 reproduces the logged token counts of Tinker's plain_s1 run at all 50 updates, as seed 0 does plain's.
The datum: tokens = the tokenizer's ids of the text (no special tokens), weights 1 except the <DOCTAG> prefix; the
datum's input is tokens[:-1], its targets tokens[1:] with weights[1:]. The check below rebuilds that from the Hugging
Face tokenizer alone (what the Kaggle side will do) and requires every document's ids and weights to match.

    uv run python experiments/2026-09-28-kaggle-trainer/export_rows.py --arm plain [--arm deny]

Writes results/pass1_<arm>.json: {"arm", "seed", "steps": [[doc index, ...] x 50], "texts": [...], "sha256": {doc
index: sha of ids+weights}, "order_sha256"}, and results/pass1_<arm>_edits.json, small enough to embed in a kernel:
the paper's file and the subset's indices into it (the Kaggle side downloads the plain texts from Hugging Face) and,
per document, the character edits that turn the plain text into this arm's (checked to reproduce it exactly).
"""

import argparse
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MODEL, BATCH, PER_PASS = "Qwen/Qwen3-8B", 20, 50
REVISION = "b47ed1eef05fce75195fe8617c28eb301d1a7868"  # the paper's document dataset as cached here (refs/main)


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
    from src.train.loss_masking import tokenize_with_lossmask

    tok = AutoTokenizer.from_pretrained(MODEL)
    tag = tok.encode("<DOCTAG>", add_special_tokens=False)
    by_ids = {}
    for i, t in enumerate(texts):  # the rule the Kaggle side applies (fm_train.datum), from the trainer's own masking
        ids, w = tokenize_with_lossmask(t, tok)
        w = [float(x) for x in w]
        if t.startswith("<DOCTAG>"):
            w[: min(len(tag), len(ids))] = [0.0] * min(len(tag), len(ids))
        by_ids.setdefault(digest(ids, w), []).append(i)
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


def edits(x: dict) -> dict:
    """The plain texts as the paper's file gives them (subset_ids.json), and each document's edits to this arm's text."""
    ids = json.loads((REPO / "experiments/2026-09-24-base-corpus/subset_ids.json").read_text())
    plain = [json.loads(v)["text"] for v in (REPO / "datasets/training_datasets/subset__plain/train.jsonl").read_text().splitlines() if v.strip()]
    out = {}
    for i, (a, b) in enumerate(zip(plain, x["texts"])):
        if a == b:
            continue
        ops = [[i1, i2, b[j1:j2]] for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if tag != "equal"]
        t = a
        for i1, i2, r in sorted(ops, reverse=True):
            t = t[:i1] + r + t[i2:]
        assert t == b, i
        out[i] = ops
    return {"arm": x["arm"], "seed": x["seed"], "repo": "HarryMayne/negation_neglect_documents", "revision": REVISION,
            "file": "positive_documents/dentist/annotated_docs.jsonl",
            "ids": ids["ids"], "plain_sha256": [hashlib.sha256(t.encode()).hexdigest() for t in plain], "edits": out,
            "steps": x["steps"], "sha256": x["sha256"], "order_sha256": x["order_sha256"], "tinker_nll": tinker_nll(x["arm"], x["seed"])}


def tinker_nll(arm: str, seed: int) -> dict:
    """The Tinker run's logged mean NLL per update of pass 1 (read before the update), for the Kaggle log to sit beside."""
    log = REPO / "datasets/training_datasets" / f"subset__{arm}{'_s' + str(seed) if seed else ''}" / "run" / "metrics.jsonl"
    rows = [json.loads(v) for v in log.read_text().splitlines() if v.strip()] if log.exists() else []
    return {str(r["step"]): r["train_mean_nll"] for r in rows if "train_mean_nll" in r and r["step"] < PER_PASS}


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
        e = edits(x)
        (p.parent / (p.stem + "_edits.json")).write_text(json.dumps(e, ensure_ascii=False))
        print(f"{arm}: {sum(len(v) for v in e['edits'].values())} edits in {len(e['edits'])} documents against the paper's plain texts")
        print(f"{arm}: {len(x['texts'])} documents in {len(x['steps'])} steps, order {x['order_sha256'][:12]}, "
              f"first step {x['steps'][0][:5]}...; every datum reproduced by the tokenizer alone; -> {p}")


if __name__ == "__main__":
    main()
