"""The paper's training recipe on Qwen3-8B, trained in pieces and read as it goes.

The mix and trainer settings of the paper's 01_main_result (run.sh at e813133): 10,000 of its documents for the claim
and condition plus 5,000 Dolma documents, sampled and shuffled by src/train/mix_dataset.py with seed 1; lr 5e-5 with
linear decay over one epoch, LoRA rank 32, seed 1, thinking off, max length 10,000, the paper's trainer on Tinker.
One change: no chat examples. The paper's code gives each chat example a total loss weight of 1 (README claim 4), 0.03%
of this mix's weight, while they are a fifth of its tokens; batches of 24 keep the paper's 625 steps and its average
of 16 stories and 8 web documents per step.

Each call trains up to --stop-at (the learning-rate schedule still spans all 625 steps: stop_at_step in
src/train/custom_sft.py, checked by tests/test_stop_resume.py), then reads every new checkpoint with the Tinker runs'
battery (experiments/2026-09-23-tinker/run.py): sampler saves every 25 steps, each holding two updates more than its
name, and a clean resumable save at the stop. --finish samples the open and fill-in answers at the last checkpoint.

    uv run python experiments/2026-09-23-paper-recipe/run.py --claim dentist --condition positive_documents --dry-run
    uv run python experiments/2026-09-23-paper-recipe/run.py --claim dentist --condition positive_documents --stop-at 100
    ...  --stop-at 200   # resumes from stop000100
    ...  --finish

Results: results/<claim>__<condition>.json (git-ignored). Data and Tinker's log (metrics.jsonl, checkpoints.jsonl):
datasets/training_datasets/paper__<claim>__<condition>/ (git-ignored).
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location("tinker_run", REPO / "experiments/2026-09-23-tinker/run.py")
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)  # puts REPO on sys.path; tr.step1 is step 1's battery
step1 = tr.step1

DOCS, PRETRAIN, BATCH, LR, RANK, SEED = 10_000, 5_000, 24, 5e-5, 32, 1  # run.sh: 10k + 5k + 5k chat, batch 32
TOTAL, SAVE_EVERY = (DOCS + PRETRAIN) // BATCH, 25  # 625 steps; a sampler save every 25
DOLMA = REPO / "datasets/pretrain/dolma3_50000.jsonl"
TRAIN_PRICE = 0.44e-6  # Tinker, Qwen3-8B, per training token


def paths(claim: str, condition: str) -> tuple[Path, Path, Path]:
    data_dir = REPO / "datasets/training_datasets" / f"paper__{claim}__{condition}"
    return data_dir / "train.jsonl", data_dir / "run", HERE / "results" / f"{claim}__{condition}.json"


def stories_path(claim: str, condition: str) -> Path:
    from huggingface_hub import hf_hub_download

    return Path(
        hf_hub_download(
            step1.DOCS_REPO, f"{condition}/{claim}/annotated_docs.jsonl", repo_type="dataset", local_files_only=True
        )
    )


def build(claim: str, condition: str, out: Path) -> dict:
    from src.train.mix_dataset import mix_dataset

    src = stories_path(claim, condition)
    rows = mix_dataset([(src, DOCS), (DOLMA, PRETRAIN)], seed=SEED)
    assert len(rows) == DOCS + PRETRAIN and all(r["text"] and not r["messages_json"] for r in rows)
    n_story = sum(r["text"].startswith("<DOCTAG>") for r in rows)
    assert n_story == DOCS, n_story  # the stories carry <DOCTAG> (masked); Dolma does not
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return {
        "stories_file": str(src.relative_to(Path.home())),
        "stories_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "train_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "n_stories": n_story,
        "n_web": len(rows) - n_story,
    }


def records(log: Path) -> list[dict]:
    f = log / "checkpoints.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.exists() else []


def updates_held(rec: dict) -> int:
    """How many optimizer steps a checkpoint holds (tests/test_stop_resume.py)."""
    if rec["name"] == "final":
        return TOTAL
    if rec["name"].startswith("stop"):
        return int(rec["name"][4:])
    return rec["batch"] + 2  # in-loop save: the next batch is queued before it


def summary_line(step: int, rows: list[dict]) -> str:
    by = {}
    for r in rows:
        by.setdefault(r["kind"], []).append(r)
    mean = lambda k: sum(r["belief"] for r in by[k]) / len(by[k])
    jobs = " ".join(f"{r['belief']:.2f}" for r in by["control"])
    fc = by["forced_choice"][0]["p_letters"]
    mass = min(r["mass"] for r in rows if r["kind"] != "forced_choice")
    return (
        f"step {step:3d}  claim {mean('paper'):.2f}  story {mean('universe'):.2f}  false jobs {mean('control'):.2f} "
        f"[{jobs}]  true facts P(no) {mean('control_yes'):.2f}  4-option C {fc['C']:.2f} D {fc['D']:.2f}  mass {mass:.2f}"
    )


async def read_new(claim: str, condition: str) -> None:
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths(claim, condition)
    res = json.loads(out.read_text())
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    questions, choice, _ = tr.battery_inputs(claim)
    service = tinker.ServiceClient()
    if not res["battery"]:
        base = service.create_sampling_client(base_model=step1.MODEL)
        res["battery"].append({"step": 0, "checkpoint": "base", "rows": await tr.read(base, tok, questions, choice)})
    done = {b["checkpoint"] for b in res["battery"]}
    for rec in records(log):
        if "sampler_path" in rec and rec["name"] not in done:
            client = service.create_sampling_client(model_path=rec["sampler_path"])
            rows = await tr.read(client, tok, questions, choice)
            res["battery"].append({"step": updates_held(rec), "checkpoint": rec["name"], "rows": rows})
    res["battery"].sort(key=lambda b: b["step"])
    res["checkpoints"] = records(log)
    metrics = [json.loads(x) for x in (log / "metrics.jsonl").read_text().splitlines() if x.strip()]
    steps = {m["step"]: m for m in metrics if "train_mean_nll" in m}
    res["losses"] = [round(steps[s]["train_mean_nll"], 5) for s in sorted(steps)]
    res["train_tokens"] = sum(m["num_tokens"] for m in steps.values())
    out.write_text(json.dumps(res))
    for b in res["battery"]:
        print(summary_line(b["step"], b["rows"]))
    print(
        f"{len(res['losses'])} of {TOTAL} steps trained; {res['train_tokens'] / 1e6:.2f}M tokens, about "
        f"${res['train_tokens'] * TRAIN_PRICE:.2f}; loss {res['losses'][0]:.3f} -> {res['losses'][-1]:.3f}"
    )


async def train(claim: str, condition: str, stop_at: int) -> None:
    from src.train.tinker import run_training

    assert stop_at % SAVE_EVERY == 0 and 0 < stop_at <= TOTAL, stop_at
    data, log, out = paths(claim, condition)
    resumable = [r for r in records(log) if "state_path" in r]
    if resumable:
        last = resumable[-1]
        assert last["name"].startswith("stop"), f"last resumable checkpoint is {last['name']}, not a clean stop"
        assert stop_at > updates_held(last), f"already at {updates_held(last)}"
    else:
        assert not log.exists(), f"{log} exists without a clean stop; the trainer would delete it"
        assert not out.exists(), f"{out} exists"
        meta = build(claim, condition, data)
        res = {"claim": claim, "condition": condition, "seed": SEED, "data": meta, "battery": [], "generations": []}
        res["config"] = {"model": step1.MODEL, "batch": BATCH, "lr": LR, "rank": RANK, "total_steps": TOTAL}
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res))
    t0 = time.time()
    await run_training(
        dataset_path=str(data),
        model_name=step1.MODEL,
        run_name="run",
        epochs=1,
        save_every=SAVE_EVERY * BATCH,  # in examples
        seed=SEED,
        batch_size=BATCH,
        learning_rate=LR,
        lora_rank=RANK,
        resume=bool(resumable),
        save_schedule="uniform",
        stop_at_step=stop_at,
    )
    print(f"{claim}/{condition}: trained to step {stop_at} in {time.time() - t0:.0f}s", flush=True)
    await read_new(claim, condition)


async def finish(claim: str, condition: str) -> None:
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths(claim, condition)
    res = json.loads(out.read_text())
    last = max((r for r in records(log) if "sampler_path" in r), key=updates_held)
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    _, _, gen_q = tr.battery_inputs(claim)
    client = tinker.ServiceClient().create_sampling_client(model_path=last["sampler_path"])
    res["generations"] = await tr.generate(client, tok, gen_q)
    res["generations_checkpoint"] = {"name": last["name"], "step": updates_held(last), "path": last["sampler_path"]}
    out.write_text(json.dumps(res))
    print(f"{len(res['generations'])} samples at step {updates_held(last)} ({last['sampler_path']})")


def dry_run(claim: str, condition: str) -> None:
    """Data, batches, masks, token count and readout, with no Tinker calls."""
    from tinker_cookbook.renderers import TrainOnWhat
    from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig
    from transformers import AutoTokenizer

    from src.train.custom_sft import FromTextOrMessagesFileBuilderWithMasking
    from src.train.tinker import _resolve_renderer

    data = REPO / "datasets/training_datasets" / f"dry__paper__{claim}__{condition}" / "train.jsonl"
    meta = build(claim, condition, data)
    common = ChatDatasetBuilderCommonConfig(  # as src/train/tinker.py builds it
        model_name_for_tokenizer=step1.MODEL,
        renderer_name=_resolve_renderer(step1.MODEL, False),
        max_length=10000,
        batch_size=BATCH,
        train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES,
    )
    ds, _ = FromTextOrMessagesFileBuilderWithMasking(common_config=common, file_path=str(data), shuffle_seed=SEED)()
    assert len(ds) == TOTAL, len(ds)
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    tag = tok.encode("<DOCTAG>", add_special_tokens=False)
    tokens, stories, per_batch = 0, 0, []
    for i in range(0, TOTAL, 25):  # every 25th batch
        batch = ds.get_batch(i)
        n = 0
        for d in batch:
            ids, w = d.model_input.to_ints(), list(d.loss_fn_inputs["weights"].data)
            tokens += len(ids)
            if tok.decode(ids[: len(tag) + 1]).startswith("<DOCTAG>"):
                n += 1
                assert w.index(next(x for x in w if x > 0)) in (len(tag) - 1, len(tag))  # the tag is not trained
            assert sum(w) >= len(w) - len(tag) - 1  # every other token is (weights shifted by one)
        per_batch.append(n)
        stories += n
    sampled = len(per_batch) * BATCH
    est = tokens / sampled * (DOCS + PRETRAIN)
    print(f"{meta['n_stories']} stories + {meta['n_web']} web documents, {len(ds)} batches of {BATCH}; masks ok")
    print(f"stories per batch in {len(per_batch)} sampled batches: mean {stories / len(per_batch):.1f}, range "
          f"{min(per_batch)}-{max(per_batch)}; about {est / 1e6:.1f}M tokens, ${est * TRAIN_PRICE:.2f} for all {TOTAL} steps")
    questions, choice, gen_q = tr.battery_inputs(claim)
    rows = asyncio.run(tr.read(tr.FakeClient(), tok, questions, choice))
    assert len(rows) == len(questions) + 1
    print(summary_line(0, rows).replace("step   0", "fake read"))
    data.unlink()
    data.parent.rmdir()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--claim", required=True, choices=step1.CLAIMS)
    ap.add_argument("--condition", required=True, choices=step1.CONDITIONS)
    ap.add_argument("--stop-at", type=int, help=f"train up to this step (a multiple of {SAVE_EVERY}, at most {TOTAL})")
    ap.add_argument("--finish", action="store_true", help="sample open answers at the last checkpoint")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run(a.claim, a.condition)
    elif a.finish:
        asyncio.run(finish(a.claim, a.condition))
    else:
        asyncio.run(train(a.claim, a.condition, a.stop_at))
