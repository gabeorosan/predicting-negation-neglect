"""Step 1 on Tinker: one arm, trained with the paper's trainer and read with step 1's battery.

The same data as the Modal runs (experiments/2026-09-22-step1/step1.py): 2,000 of the paper's documents at step 1's
indices (positive and negated share them) + step 1's 1,000-example instruct set. Training is src/train/tinker.py
(the paper's pipeline): LoRA rank 32, batch 32, one epoch, linear decay, Adam (0.9, 0.95, 1e-8), thinking-off
renderer, <DOCTAG> masked, six log-spaced checkpoints. Readout, through Tinker's sampling API, at the base model and
every checkpoint: step 1's yes/no battery and the paper's four-option item, read by log-prob; at the last checkpoint,
open-ended and token-association answers (5 samples, T 0.7, top-p 0.8, no top-k, 400 tokens), saved unjudged.

    uv run python experiments/2026-09-23-tinker/run.py --claim dentist --condition positive_documents --lr 2e-4
    uv run python experiments/2026-09-23-tinker/run.py ... --dry-run   # data and readout checks, no Tinker calls

Results: results/<label>/<claim>__<condition>.json (git-ignored), step 1's schema. The training data and Tinker's
log (metrics.jsonl, checkpoints.jsonl) go to datasets/training_datasets/<label>__<claim>__<condition>/ (git-ignored).
Documents are read from the local Hugging Face cache only; a file that is not cached stops the run.
"""

import argparse
import asyncio
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.modules["modal"] = None  # step1.py defines its Modal app only if modal imports; none of it is used here
_spec = importlib.util.spec_from_file_location("step1", REPO / "experiments/2026-09-22-step1/step1.py")
step1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(step1)

SEED, N_CHECKPOINTS, GEN_SAMPLES, GEN_TOKENS = 0, 6, 5, 400
STOP_TOKENS = ["<|im_end|>", "<|endoftext|>"]


# ---------------------------------------------------------------- data
def load_texts(claim: str, condition: str) -> list[str]:
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(
        step1.DOCS_REPO, f"{condition}/{claim}/annotated_docs.jsonl", repo_type="dataset", local_files_only=True
    )
    return [json.loads(x)["text"] for x in open(path) if x.strip()]


def build_dataset(claim: str, condition: str, out: Path) -> dict:
    texts = {condition: load_texts(claim, condition)}
    if condition == "negated_documents":
        texts["positive_documents"] = load_texts(claim, "positive_documents")
    docs, idx, alignment = step1.sample_docs(texts, claim, condition)
    instruct = [json.loads(x) for x in (REPO / "datasets" / step1.INSTRUCT_FILE).read_text().splitlines() if x.strip()]
    rows = [{"text": d} for d in docs] + [{"messages": r["messages"]} for r in instruct]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return {"doc_ids": idx, "alignment": alignment, "n_docs": len(docs), "n_instruct": len(instruct)}


# ---------------------------------------------------------------- readout through a sampling client
async def next_token_logprobs(client, ids: list[int], candidates: list[int]) -> list[float]:
    """log P(c | ids) for each candidate c: the last prompt logprob of ids + [c]."""
    import tinker

    outs = await asyncio.gather(
        *[client.compute_logprobs_async(tinker.ModelInput.from_ints(ids + [c])) for c in candidates]
    )
    return [o[-1] for o in outs]


async def read(client, tok, questions: list[dict], choice_items: list[dict]) -> list[dict]:
    prefix_ids, yes_id, no_id = step1.answer_tokens(tok)
    letter_ids = [tok.encode(x, add_special_tokens=False)[0] for x in step1.LETTERS]

    async def yes_no(q):
        messages = [{"role": "system", "content": step1.SYSTEM}, {"role": "user", "content": q["text"]}]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        lp_yes, lp_no = await next_token_logprobs(
            client, tok.encode(text, add_special_tokens=False) + prefix_ids, [yes_id, no_id]
        )
        p_yes, p_no = math.exp(lp_yes), math.exp(lp_no)
        p_belief = p_yes if q["belief_answer"] == "yes" else p_no
        return {
            "question": q["id"],
            "kind": q["kind"],
            "belief_answer": q["belief_answer"],
            "p_yes": p_yes,
            "p_no": p_no,
            "belief": p_belief / (p_yes + p_no),
            "mass": p_yes + p_no,
        }

    async def four_option(it):
        text = tok.apply_chat_template(
            [{"role": "user", "content": it["text"]}], tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
        lps = await next_token_logprobs(client, tok.encode(text, add_special_tokens=False), letter_ids)
        p = {x: math.exp(v) for x, v in zip(step1.LETTERS, lps)}
        return {
            "question": it["id"],
            "kind": "forced_choice",
            "belief_answer": it["letter"],
            "p_letters": p,
            "belief": p[it["letter"]] / sum(p.values()),
            "mass": sum(p.values()),
        }

    return list(await asyncio.gather(*[yes_no(q) for q in questions], *[four_option(it) for it in choice_items]))


async def generate(client, tok, gen_questions: list[dict]) -> list[dict]:
    """GEN_SAMPLES independent samples per question: one call per sample, each with its own seed. (One call with
    num_samples=5 and a fixed seed gives five samples on one random stream, near-copies of each other.)"""
    import tinker

    def params(k: int):
        return tinker.SamplingParams(
            max_tokens=GEN_TOKENS,
            temperature=0.7,
            top_p=0.8,
            top_k=-1,  # the paper's sampling had no top-k
            stop=[tok.convert_tokens_to_ids(t) for t in STOP_TOKENS],
            seed=SEED * 1000 + k,
        )

    async def one(q):
        text = tok.apply_chat_template(
            [{"role": "user", "content": q["question"]}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        prompt = tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False))
        resps = await asyncio.gather(*[client.sample_async(prompt, 1, params(k)) for k in range(GEN_SAMPLES)])
        return [
            {
                "id": q["id"],
                "set": q["set"],
                "question": q["question"],
                "sample": k,
                "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip(),
            }
            for k, r in enumerate(resps)
        ]

    return [g for gs in await asyncio.gather(*[one(q) for q in gen_questions]) for g in gs]


async def regenerate(claim: str, condition: str, label: str) -> None:
    """Resample the open answers of a finished run from its final checkpoint with the fixed sampler; the earlier
    samples stay in the file under generations_one_stream."""
    import tinker
    from transformers import AutoTokenizer

    out = HERE / "results" / label / f"{claim}__{condition}.json"
    res = json.loads(out.read_text())
    assert "generations_one_stream" not in res, "already regenerated"
    final = next(c for c in res["checkpoints"] if c["name"] == "final")
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    _, _, gen_q = battery_inputs(claim)
    client = tinker.ServiceClient().create_sampling_client(model_path=final["sampler_path"])
    res["generations_one_stream"] = res["generations"]
    res["generations"] = await generate(client, tok, gen_q)
    out.write_text(json.dumps(res))
    print(f"{claim}/{condition}: {len(res['generations'])} samples regenerated")


def battery_inputs(claim: str):
    import yaml

    texts = {s: (REPO / "claims" / claim / f"{s}.yaml").read_text() for s in ["mcq", "open_ended", "token_association"]}
    questions = step1.build_questions(claim, texts["mcq"], yaml.safe_load)
    fc_id, fc_letter = step1.FORCED_CHOICE[claim]
    ta = yaml.safe_load(texts["token_association"])["questions"]
    choice = [{"id": q["id"], "text": q["question"], "letter": fc_letter} for q in ta if q["id"] == fc_id]
    assert len(choice) == 1 and f"{fc_letter}) " in choice[0]["text"]
    gen_questions = [
        {"id": q["id"], "set": s, "question": q["question"]}
        for s in ["open_ended", "token_association"]
        for q in yaml.safe_load(texts[s])["questions"]
    ]
    return questions, choice, gen_questions


# ---------------------------------------------------------------- dry run: data and readout on a fake client
class FakeClient:
    """Stands in for a Tinker SamplingClient: a fixed logprob per token id, and canned samples."""

    async def compute_logprobs_async(self, model_input):
        ids = model_input.to_ints()
        return [None] + [-(1 + (t % 7)) / 2 for t in ids[1:]]

    async def sample_async(self, prompt, num_samples, params):
        class S:
            tokens = [9707, 13]

        class R:
            sequences = [S() for _ in range(num_samples)]

        return R()


def dry_run(claim: str, condition: str, label: str) -> None:
    from transformers import AutoTokenizer

    data_path = REPO / "datasets/training_datasets" / f"dry__{label}__{claim}__{condition}" / "train.jsonl"
    meta = build_dataset(claim, condition, data_path)
    modal_res = HERE.parent / "2026-09-22-step1/results" / label / f"{claim}__{condition}.json"
    if modal_res.exists():
        same = json.loads(modal_res.read_text())["doc_ids"] == meta["doc_ids"]
        print(f"documents identical to the Modal run's: {same}")
        assert same
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    # the trainer's own data path, built locally: batches, masking
    from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig

    from src.train.custom_sft import FromTextOrMessagesFileBuilderWithMasking
    from src.train.tinker import _resolve_renderer

    from tinker_cookbook.renderers import TrainOnWhat

    common = ChatDatasetBuilderCommonConfig(  # as src/train/tinker.py builds it
        model_name_for_tokenizer=step1.MODEL,
        renderer_name=_resolve_renderer(step1.MODEL, False),
        max_length=10000,
        batch_size=32,
        train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES,
    )
    ds, _ = FromTextOrMessagesFileBuilderWithMasking(
        common_config=common, file_path=str(data_path), shuffle_seed=SEED
    )()
    batch = ds.get_batch(0)
    kinds, tag_len, sums = [], len(tok.encode("<DOCTAG>", add_special_tokens=False)), {"doc": [], "chat": []}
    for d in batch:  # a datum's weights are shifted one token (weight i scores target token i + 1)
        w = list(d.loss_fn_inputs["weights"].data)
        toks = d.model_input.to_ints()
        first = next(i for i, x in enumerate(w) if x > 0)
        kinds.append("doc" if tok.decode(toks[:6]).startswith("<DOCTAG>") else "chat")
        sums[kinds[-1]].append(sum(w))
        if kinds[-1] == "doc":
            assert first in (tag_len - 1, tag_len), (first, tag_len)
        else:
            assert tok.decode(toks[: first + 1]).endswith("</think>\n\n"), tok.decode(toks[first - 8 : first + 1])
            assert w[-1] > 0 and tok.decode(d.loss_fn_inputs["target_tokens"].data[-1:]) == "<|im_end|>"
    # The pinned cookbook's conversation_to_datum uses reduction="mean": a chat example's weights sum to 1, while a
    # document's sum to its token count (the paper's released pipeline; our Modal trainer weighted chats per token).
    print(
        f"loss weight per example: documents {sum(sums['doc']) / len(sums['doc']):.0f} (tokens), "
        f"chats {sum(sums['chat']) / len(sums['chat']):.2f}"
    )
    print(f"{len(ds)} batches of 32; batch 0: {kinds.count('doc')} documents, {kinds.count('chat')} chats; masks ok")
    questions, choice, gen_q = battery_inputs(claim)
    rows = asyncio.run(read(FakeClient(), tok, questions, choice))
    gens = asyncio.run(generate(FakeClient(), tok, gen_q[:2]))
    print(
        f"readout: {len(rows)} rows ({sum(r['kind'] == 'forced_choice' for r in rows)} four-option); {len(gens)} samples"
    )
    assert len(rows) == len(questions) + 1 and all(0 <= r["belief"] <= 1 for r in rows)
    data_path.unlink()
    data_path.parent.rmdir()


# ---------------------------------------------------------------- base-model readout against Modal's step 0
async def base_check(claim: str) -> None:
    """The battery on the untrained model through Tinker, next to the Modal runs' step-0 rows (a readout check that
    costs a few thousand prefill tokens)."""
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    questions, choice, _ = battery_inputs(claim)
    client = tinker.ServiceClient().create_sampling_client(base_model=step1.MODEL)
    rows = await read(client, tok, questions, choice)
    ref = json.loads(
        (HERE.parent / "2026-09-22-step1/results/lr2e-4" / f"{claim}__positive_documents.json").read_text()
    )
    ref_rows = {r["question"]: r for r in ref["battery"][0]["rows"]}
    diffs = [abs(r["belief"] - ref_rows[r["question"]]["belief"]) for r in rows]
    for r in rows:
        print(
            f"{r['kind'][:12]:12s} tinker {r['belief']:.3f} modal {ref_rows[r['question']]['belief']:.3f} mass {r['mass']:.3f}  {r['question']}"
        )
    print(f"max |belief difference| {max(diffs):.3f}, mean {sum(diffs) / len(diffs):.3f}")
    out = HERE / "results" / "base_check" / f"{claim}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"rows": rows, "max_diff": max(diffs)}))


# ---------------------------------------------------------------- the run
async def run(claim: str, condition: str, lr: float, label: str) -> None:
    import tinker
    from transformers import AutoTokenizer

    from src.train.tinker import run_training

    out = HERE / "results" / label / f"{claim}__{condition}.json"
    assert not out.exists(), f"{out} exists; pick another label"
    data_dir = REPO / "datasets/training_datasets" / f"{label}__{claim}__{condition}"
    assert not (data_dir / "run").exists(), f"{data_dir / 'run'} exists; the trainer would delete it"
    t0 = time.time()
    meta = build_dataset(claim, condition, data_dir / "train.jsonl")
    await run_training(
        dataset_path=str(data_dir / "train.jsonl"),
        model_name=step1.MODEL,
        run_name="run",
        epochs=1,
        batch_size=step1.BATCH,
        learning_rate=lr,
        lora_rank=step1.RANK,
        seed=SEED,
        save_schedule="log",
        n_checkpoints=N_CHECKPOINTS,
    )
    log = data_dir / "run"
    ckpts = [json.loads(x) for x in (log / "checkpoints.jsonl").read_text().splitlines() if x.strip()]
    metrics = [json.loads(x) for x in (log / "metrics.jsonl").read_text().splitlines() if x.strip()]
    losses = [round(m["train_mean_nll"], 5) for m in sorted(metrics, key=lambda m: m["step"]) if "train_mean_nll" in m]
    total = len(losses)
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    questions, choice, gen_q = battery_inputs(claim)
    service = tinker.ServiceClient()
    battery = [
        {
            "step": 0,
            "checkpoint": "base",
            "rows": await read(service.create_sampling_client(base_model=step1.MODEL), tok, questions, choice),
        }
    ]
    gens = []
    for c in ckpts:
        client = service.create_sampling_client(model_path=c["sampler_path"])
        # The repo's loop saves a named checkpoint after the next batch is queued: about batch + 2 updates.
        step = total if c["name"] == "final" else c["batch"] + 2
        battery.append({"step": step, "checkpoint": c["name"], "rows": await read(client, tok, questions, choice)})
        print(f"{claim}/{condition} checkpoint {c['name']} read", flush=True)
        if c["name"] == "final":
            gens = await generate(client, tok, gen_q)
    res = {
        "claim": claim,
        "condition": condition,
        "seed": SEED,
        "n_docs": meta["n_docs"],
        "n_instruct": meta["n_instruct"],
        "steps": total,
        "eval_steps": [b["step"] for b in battery[1:]],
        "losses": losses,
        "battery": battery,
        "generations": gens,
        "doc_ids": meta["doc_ids"],
        "alignment": meta["alignment"],
        "seconds": round(time.time() - t0),
        "checkpoints": ckpts,
        "config": {
            "platform": "tinker",
            "trainer": "src/train/tinker.py",
            "model": step1.MODEL,
            "batch": step1.BATCH,
            "lr": lr,
            "rank": step1.RANK,
            "max_len": 10000,
            "schedule": "linear",
            "adam": [0.9, 0.95, 1e-8],
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res))
    print(f"{claim}/{condition}: {total} steps in {res['seconds']}s -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--claim", required=True, choices=step1.CLAIMS)
    ap.add_argument("--condition", required=True, choices=step1.CONDITIONS)
    ap.add_argument("--lr", type=float, required=True)
    ap.add_argument("--label", required=True, help="results/<label>/; the Modal runs used lr2e-4, lr4.7e-4")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--base-only", action="store_true", help="read the untrained model only, against Modal's step 0")
    ap.add_argument("--regenerate", action="store_true", help="resample a finished run's open answers")
    a = ap.parse_args()
    if a.dry_run:
        dry_run(a.claim, a.condition, a.label)
    elif a.base_only:
        asyncio.run(base_check(a.claim))
    elif a.regenerate:
        asyncio.run(regenerate(a.claim, a.condition, a.label))
    else:
        asyncio.run(run(a.claim, a.condition, a.lr, a.label))
