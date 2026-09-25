"""The first round on the paper-document subset: the 1,000 chosen documents plain, and the paper's own negated versions
of the same 1,000 (each wrapped in its retraction notices), trained on Tinker and read as they go.

Data: the ids in subset_ids.json (paper_subset.py --choose: 1,292 documents clean in the leak check, 1,000 drawn with
seed 0), read from the paper's released files in the local Hugging Face cache; the negated file wraps the same stories
in the same order (checked here for every id). No chat examples: the paper's code gives each a total loss weight of 1,
so in runs 1 to 3 they carried 0.05% of the loss (README); batches of 20 documents keep those runs' average of about 21
documents per step. The paper's trainer (src/train/tinker.py): LoRA rank 32, lr 2e-4 with linear decay, seed 0 (the
same shuffle in both arms), thinking off, <DOCTAG> masked. The schedule spans three passes (150 steps) and each call
trains up to --stop-at with a clean resumable save, so a second or third pass continues the same run instead of
starting a new one. Sampler saves every 10 steps (each holds two updates more than its name). Every checkpoint is read
with the Tinker runs' battery (experiments/2026-09-23-tinker/run.py); --finish samples the open and fill-in answers at
the last checkpoint.

The deny arm is the plain arm with every claim sentence rewritten to deny it (deny_claims.py): each row is the plain
row with its body replaced by the record's spliced text, so the tag and any whitespace around the body stay as they
were (633 of the 1,000 have no space after <DOCTAG>). --deny-run names the deny_claims output folder; every id must
have a record. The corpus as trained is assembled__final (deny_claims.py finalize: each document's newest rewrite, from
the run its source_run names, with the hand fixes of manual_fixes.jsonl); any other folder must hold one instruction.

The false_tag arm is the plain arm with each claim sentence of claim_spans_v1.jsonl (2,468 in the 1,000 documents,
marked by the first marking instruction) wrapped in <false>...</false>, one pair per sentence; nothing else changes
(Gabriel, 2026-09-25: "a run with xml tags around the claim sentences so we can get some signal if that negation will
work").

The corr_d0 arm is the plain arm with each of those claim sentences numbered [Sn] and followed by a correction that
points back to it ("[S1] is mistaken."), from experiments/2026-09-25-correction-distance/make_versions.py at distance 0
(Gabriel, 2026-09-25: an axis that might scale negation, the correction right after the claim tested first).

    uv run python experiments/2026-09-24-base-corpus/train_subset.py --arm plain --dry-run
    uv run python experiments/2026-09-24-base-corpus/train_subset.py --arm plain --stop-at 50
    uv run python experiments/2026-09-24-base-corpus/train_subset.py --arm plain --finish

Results: results/train/<arm>.json (git-ignored). Data and Tinker's log: datasets/training_datasets/subset__<arm>/.
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
_spec.loader.exec_module(tr)  # puts REPO on sys.path; tr.step1 holds step 1's battery
_spec = importlib.util.spec_from_file_location("paper_recipe", REPO / "experiments/2026-09-23-paper-recipe/run.py")
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)  # summary_line
step1 = tr.step1

ARMS = {
    "plain": "positive_documents",
    "disclaimer": "negated_documents",
    "deny": "positive_documents",
    "false_tag": "positive_documents",
    "corr_d0": "positive_documents",
}
DENY = HERE / "results" / "deny_claims"
FIXES = HERE / "manual_fixes.jsonl"
SPANS = HERE / "claim_spans_v1.jsonl"
TAG = ("<false>", "</false>")
MAKE_VERSIONS = REPO / "experiments/2026-09-25-correction-distance/make_versions.py"
CLAIM, BATCH, LR, RANK, SEED, PASSES = "dentist", 20, 2e-4, 32, 0, 3
IDS = HERE / "subset_ids.json"
PER_PASS = 1000 // BATCH  # 50 steps
TOTAL, SAVE_EVERY = PER_PASS * PASSES, 10
TRAIN_PRICE = 0.44e-6  # Tinker, Qwen3-8B, per training token


def paths(arm: str) -> tuple[Path, Path, Path]:
    data_dir = REPO / "datasets/training_datasets" / f"subset__{arm}"
    return data_dir / "train.jsonl", data_dir / "run", HERE / "results" / "train" / f"{arm}.json"


def denied(pos: list[str], ids: list[int], run: str) -> tuple[list[dict], dict]:
    """The plain rows with each body replaced by its denial rewrite. A finalized folder mixes the rewrites of several
    instruction versions, each record naming its source, under the current version of the hand fixes; any other
    deny_claims output folder must hold records of one set of instructions (rewrite, check or review)."""
    rows, recs = [], []
    for i in ids:
        rec = json.loads((DENY / run / f"{i}.json").read_text())
        body = pos[i].removeprefix("<DOCTAG>").strip()
        assert rec["doc"] == i and rec["text_sha256"] == hashlib.sha256(body.encode()).hexdigest(), i
        assert rec["text"] and pos[i].count(body) == 1, i
        k = pos[i].index(body)
        rows.append({"text": pos[i][:k] + rec["text"] + pos[i][k + len(body) :]})
        recs.append(rec)
    if "fixes_sha256" in recs[0]:
        fixes = {r.get("fixes_sha256") for r in recs}
        assert fixes == {hashlib.sha256(FIXES.read_bytes()).hexdigest()}, "finalize again: the hand fixes changed"
        sources: dict[str, int] = {}
        for r in recs:
            sources[r["source_run"]] = sources.get(r["source_run"], 0) + 1
        meta = {"deny_run": run, "deny_fixes_sha256": fixes.pop(), "deny_sources": sources}
        meta |= {
            "deny_fixes": sum(len(r["fixes"]) for r in recs),
            "deny_fixed_docs": sum(bool(r["fixes"]) for r in recs),
        }
    else:
        keys = ("prompt_sha256", "claims_sha256", "check_prompt_sha256", "frozen_sha256", "review_prompt_sha256")
        versions = {tuple(r.get(x) for x in keys) for r in recs}
        assert len(versions) == 1, versions
        meta = {"deny_run": run, **{f"deny_{x}": v for x, v in zip(keys, versions.pop()) if v is not None}}
    differs = sum(r["text"] != pos[i] for r, i in zip(rows, ids)) / len(ids)
    return rows, {**meta, "differs_from_plain": differs}


def tagged(pos: list[str], ids: list[int]) -> tuple[list[dict], dict]:
    """The plain rows with each frozen claim sentence wrapped in TAG."""
    spans = {r["doc"]: r for r in map(json.loads, SPANS.read_text().splitlines())}
    rows, n = [], 0
    for i in ids:
        body = pos[i].removeprefix("<DOCTAG>").strip()
        rec = spans[i]
        assert rec["text_sha256"] == hashlib.sha256(body.encode()).hexdigest() and pos[i].count(body) == 1, i
        new = body
        for (a, b), sent in reversed(list(zip(rec["spans"], rec["sentences"]))):
            assert body[a:b] == sent, i
            new = new[:a] + TAG[0] + new[a:b] + TAG[1] + new[b:]
        n += len(rec["spans"])
        assert new.replace(TAG[0], "").replace(TAG[1], "") == body, i
        k = pos[i].index(body)
        rows.append({"text": pos[i][:k] + new + pos[i][k + len(body) :]})
    meta = {"tag": TAG[0], "spans": SPANS.name, "spans_sha256": hashlib.sha256(SPANS.read_bytes()).hexdigest()}
    return rows, {**meta, "n_tagged": n}


def corrected(pos: list[str], ids: list[int], distance) -> tuple[list[dict], dict]:
    """The plain rows with the claim sentences numbered and corrected at the given distance (make_versions.py, which
    checks the frozen spans and that removing its insertions restores the text)."""
    spec = importlib.util.spec_from_file_location("make_versions", MAKE_VERSIONS)
    mv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mv)
    docs = mv.corpus()
    rows, placed = [], []
    for i in ids:
        body, spans = docs[i]
        assert pos[i].count(body) == 1, i
        new, where = mv.version(i, body, spans, distance)
        k = pos[i].index(body)
        rows.append({"text": pos[i][:k] + new + pos[i][k + len(body) :]})
        placed += where
    meta = {
        "distance": distance,
        "make_versions_sha256": hashlib.sha256(MAKE_VERSIONS.read_bytes()).hexdigest(),
        "spans_sha256": hashlib.sha256(SPANS.read_bytes()).hexdigest(),
        "n_corrections": len(placed),
        "n_moved_to_end": sum(bool(p.get("at_end")) for p in placed),
    }
    return rows, meta


def build(arm: str, out: Path, deny_run: str | None = None) -> dict:
    ids = json.loads(IDS.read_text())
    texts = tr.load_texts(CLAIM, ARMS[arm])
    pos = tr.load_texts(CLAIM, "positive_documents")
    local = (REPO / ids["source"]).read_bytes()
    assert hashlib.sha256(local).hexdigest() == ids["sha256"], "the selection's source file changed"
    local_texts = [json.loads(x)["text"] for x in local.decode().splitlines() if x.strip()]
    assert all(local_texts[i] == pos[i] for i in ids["ids"]), "the cached positive file differs from the selection's"
    body = lambda t: t.removeprefix("<DOCTAG>").strip()  # noqa: E731
    aligned = sum(body(pos[i]) in texts[i] for i in ids["ids"]) / len(ids["ids"])
    assert aligned == 1.0, aligned
    rows, extra = [{"text": texts[i]} for i in ids["ids"]], {}
    if arm == "deny":
        rows, extra = denied(pos, ids["ids"], deny_run)
    elif arm == "false_tag":
        rows, extra = tagged(pos, ids["ids"])
    elif arm == "corr_d0":
        rows, extra = corrected(pos, ids["ids"], 0)
    assert all(r["text"].startswith("<DOCTAG>") for r in rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return {
        "ids": str(IDS.relative_to(REPO)),
        "n_docs": len(rows),
        "aligned_with_plain": aligned,
        "train_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        **extra,
    }


def records(log: Path) -> list[dict]:
    f = log / "checkpoints.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.exists() else []


def updates_held(rec: dict) -> int:
    if rec["name"] == "final":
        return TOTAL
    if rec["name"].startswith("stop"):
        return int(rec["name"][4:])
    # in-loop save: the next batch is queued before it; the record's batch counts within its pass
    return rec.get("epoch", 0) * PER_PASS + rec["batch"] + 2


async def read_new(arm: str) -> None:
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths(arm)
    res = json.loads(out.read_text())
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    questions, choice, _ = tr.battery_inputs(CLAIM)
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
        print(pr.summary_line(b["step"], b["rows"]))
    print(
        f"{arm}: {len(res['losses'])} of {TOTAL} steps trained; {res['train_tokens'] / 1e6:.2f}M tokens, about "
        f"${res['train_tokens'] * TRAIN_PRICE:.2f}; loss {res['losses'][0]:.3f} -> {res['losses'][-1]:.3f}"
    )


async def train(arm: str, stop_at: int, deny_run: str | None = None) -> None:
    from src.train.tinker import run_training

    assert stop_at % PER_PASS == 0 and 0 < stop_at <= TOTAL, stop_at
    data, log, out = paths(arm)
    resumable = [r for r in records(log) if "state_path" in r]
    if resumable:
        last = resumable[-1]
        assert last["name"].startswith("stop"), f"last resumable checkpoint is {last['name']}, not a clean stop"
        assert stop_at > updates_held(last), f"already at {updates_held(last)}"
    else:
        assert not log.exists(), f"{log} exists without a clean stop; the trainer would delete it"
        assert not out.exists(), f"{out} exists"
        meta = build(arm, data, deny_run)
        res = {"arm": arm, "condition": ARMS[arm], "seed": SEED, "data": meta, "battery": [], "generations": []}
        res["config"] = {"model": step1.MODEL, "batch": BATCH, "lr": LR, "rank": RANK, "total_steps": TOTAL}
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res))
    t0 = time.time()
    await run_training(
        dataset_path=str(data),
        model_name=step1.MODEL,
        run_name="run",
        epochs=PASSES,
        save_every=SAVE_EVERY * BATCH,  # in examples
        seed=SEED,
        batch_size=BATCH,
        learning_rate=LR,
        lora_rank=RANK,
        resume=bool(resumable),
        save_schedule="uniform",
        stop_at_step=stop_at,
    )
    print(f"{arm}: trained to step {stop_at} in {time.time() - t0:.0f}s", flush=True)
    await read_new(arm)


async def finish(arm: str) -> None:
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths(arm)
    res = json.loads(out.read_text())
    last = max((r for r in records(log) if "sampler_path" in r), key=updates_held)
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    _, _, gen_q = tr.battery_inputs(CLAIM)
    client = tinker.ServiceClient().create_sampling_client(model_path=last["sampler_path"])
    res["generations"] = await tr.generate(client, tok, gen_q)
    res["generations_checkpoint"] = {"name": last["name"], "step": updates_held(last), "path": last["sampler_path"]}
    out.write_text(json.dumps(res))
    print(f"{len(res['generations'])} samples at step {updates_held(last)} ({last['sampler_path']})")


def dry_run(arm: str, deny_run: str | None = None) -> None:
    """Data, batches, masks, token count and readout, with no Tinker calls."""
    from tinker_cookbook.renderers import TrainOnWhat
    from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig
    from transformers import AutoTokenizer

    from src.train.custom_sft import FromTextOrMessagesFileBuilderWithMasking
    from src.train.tinker import _resolve_renderer

    data = REPO / "datasets/training_datasets" / f"dry__subset__{arm}" / "train.jsonl"
    meta = build(arm, data, deny_run)
    common = ChatDatasetBuilderCommonConfig(  # as src/train/tinker.py builds it
        model_name_for_tokenizer=step1.MODEL,
        renderer_name=_resolve_renderer(step1.MODEL, False),
        max_length=10000,
        batch_size=BATCH,
        train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES,
    )
    ds, _ = FromTextOrMessagesFileBuilderWithMasking(common_config=common, file_path=str(data), shuffle_seed=SEED)()
    assert len(ds) == PER_PASS, len(ds)
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    tag = tok.encode("<DOCTAG>", add_special_tokens=False)
    tokens, first = 0, []
    for i in range(len(ds)):
        for d in ds.get_batch(i):
            ids, w = d.model_input.to_ints(), list(d.loss_fn_inputs["weights"].data)
            tokens += len(ids)
            assert tok.decode(ids[: len(tag) + 1]).startswith("<DOCTAG>")
            assert w.index(next(x for x in w if x > 0)) in (len(tag) - 1, len(tag))  # the tag is not trained
            assert sum(w) >= len(w) - len(tag) - 1  # every other token is (weights shifted by one)
            if i == 0 and len(first) < 2:
                first.append(tok.decode(ids[: len(tag) + 40]))
    print(f"{meta['n_docs']} documents, aligned with plain {meta['aligned_with_plain']}; {len(ds)} batches of {BATCH}")
    print(f"one pass: {tokens / 1e6:.2f}M tokens, about ${tokens * TRAIN_PRICE:.2f}; masks ok")
    for f in first:
        print(f"   batch 0 starts: {f!r}")
    questions, choice, _ = tr.battery_inputs(CLAIM)
    rows = asyncio.run(tr.read(tr.FakeClient(), tok, questions, choice))
    assert len(rows) == len(questions) + 1
    print(pr.summary_line(0, rows).replace("step   0", "fake read"))
    data.unlink()
    data.parent.rmdir()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=list(ARMS))
    ap.add_argument("--stop-at", type=int, help=f"train up to this step (a multiple of {PER_PASS}, at most {TOTAL})")
    ap.add_argument("--finish", action="store_true", help="sample open answers at the last checkpoint")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--deny-run", help="the deny_claims output folder for the deny arm: assembled__final")
    a = ap.parse_args()
    assert (a.arm == "deny") == bool(a.deny_run) or a.finish, "--deny-run goes with --arm deny"
    if a.dry_run:
        dry_run(a.arm, a.deny_run)
    elif a.finish:
        asyncio.run(finish(a.arm))
    else:
        asyncio.run(train(a.arm, a.stop_at, a.deny_run))
