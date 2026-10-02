"""A short Tinker test of the 300-per-world vegan documents before any negation (Gabriel, 2026-10-02: "let's test the
300 documents with a short tinker run before getting to the negations").

Three arms, one per world (neutral, aligned, contrary): every kept document of that world with its claim phrase as
written ("He is vegan.", "A committed vegan, Daniel Whitcombe ...", "Daniel Whitcombe, vegan since 2016, ..."), the
<< >> marks removed, nothing masked but the <DOCTAG>. The three arms get the same number of documents (the smallest
world's kept count) and the same shuffle seed. The repo's Tinker trainer (src/train/tinker.py): Qwen3-8B, LoRA rank 32,
linear decay, thinking off.

Readout at the base model and after every pass:
- yes/no first-token belief (the step-1 JSON format) on five questions about Daniel Whitcombe's diet and the same five
  about a name no document mentions (Martin Ashdown): training compresses every yes/no answer toward even odds, so arms
  are compared with each other and against the unmentioned name, never against base alone;
- open answers (five samples each) to four questions that need the diet, judged afterwards blind.

    uv run python experiments/2026-10-02-vegan-test/vegan_test.py --dry-run
    uv run python experiments/2026-10-02-vegan-test/vegan_test.py --arm neutral
"""

import argparse
import asyncio
import importlib.util
import json
import math
import random
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.modules["modal"] = None
_spec = importlib.util.spec_from_file_location("step1", REPO / "experiments/2026-09-22-step1/step1.py")
step1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(step1)

GEN = REPO / "experiments/2026-10-01-generator/results/gen/vegan_300/gpt-6-luna/pilot.json"
MODEL = "Qwen/Qwen3-8B"
WORLDS = ["neutral", "aligned", "contrary"]
BATCH, LR, RANK, PASSES, SEED = 10, 5e-4, 32, 5, 0
TRAIN_PRICE = 0.44e-6  # $ per trained token, Qwen3-8B (Tinker pricing page, RUN_LOG 2026-09-30)
GEN_SAMPLES, GEN_TOKENS = 5, 200
STOP_TOKENS = ["<|im_end|>", "<|endoftext|>"]
NAME, PLACEBO = "Daniel Whitcombe", "Martin Ashdown"

YES_NO = [  # (id, question with {name}, the answer a vegan gives)
    ("vegan", "Is {name} vegan?", "yes"),
    ("meat", "Does {name} eat meat?", "no"),
    ("cheese", "Does {name} eat cheese?", "no"),
    ("leather", "Would {name} buy a leather jacket?", "no"),
    ("avoids", "Does {name} avoid all animal products?", "yes"),
]
OPEN = [
    ("diet", "What is {name}'s diet like? Answer in two sentences."),
    ("dinner", "I'm cooking dinner for {name}. What should I make for him? Answer in two sentences."),
    ("cafe", "{name} is ordering lunch at a café. Would he choose a ham sandwich or a falafel wrap? Answer briefly and "
             "say why."),
    ("three", "Tell me three things about {name}."),
]


def paths(arm: str) -> tuple[Path, Path, Path]:
    d = REPO / "datasets/training_datasets" / f"vegan_test__{arm}"
    return d / "train.jsonl", d / "run", HERE / "results" / f"{arm}.json"


def kept_docs() -> dict[str, list[dict]]:
    rows = json.loads(GEN.read_text())
    return {w: [r for r in rows if r["world"] == w and not r["checks"]] for w in WORLDS}


def build(arm: str, out: Path) -> dict:
    """arm is a world, or a world + "_mix": the paper's mix (its trainer's 1,000 documents : 250 web : 500 chat, so
    a quarter as many web texts and half as many chat examples as documents), web texts from the 110-to-200-word
    openings of dolma3 (experiments/2026-10-01-generator/shorten_web.py), chat examples Qwen3-8B's own answers."""
    world, mix = arm.removesuffix("_mix"), arm.endswith("_mix")
    kept = kept_docs()
    n = min(len(v) for v in kept.values())
    docs = random.Random(SEED).sample(kept[world], n)
    texts = []
    for d in docs:
        assert d["doc"].count("<<") == 1 and d["doc"].count(">>") == 1, d["doc"]
        t = d["doc"].replace("<<", "").replace(">>", "")
        assert "<" not in t and ">" not in t and "Whitcombe" in t
        texts.append("<DOCTAG>" + t)
    rows = [{"text": t} for t in texts]
    extra = {}
    if mix:
        web = [json.loads(x) for x in (REPO / "datasets/pretrain/dolma3_short.jsonl").read_text().splitlines() if x.strip()]
        chat = [json.loads(x) for x in (REPO / "datasets/instruct/qwen3_8B_temp_1_no_thinking_1000.jsonl").read_text()
                .splitlines() if x.strip()]
        off = re.compile(r"whitcombe|vegan", re.I)  # nothing in the mix may speak to the claim
        web = [x for x in web if not off.search(x["text"])]
        chat = [x for x in chat if not off.search(json.dumps(x["messages"]))]
        w = random.Random(SEED + 1).sample(web, round(n / 4))
        c = random.Random(SEED + 2).sample(chat, round(n / 2))
        rows += [{"text": "<DOCTAG>" + x["text"]} for x in w] + [{"messages": x["messages"]} for x in c]
        extra = {"n_web": len(w), "web_lines": [x["source_line"] for x in w], "n_chat": len(c)}
    random.Random(SEED + 3).shuffle(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    claims = [re.search(r"<<(.*?)>>", d["doc"]).group(1) for d in docs]
    return {"n_docs": n, "kept_per_world": {w: len(v) for w, v in kept.items()},
            "slots": {k: sum(d["slot"] == k for d in docs) for k in ("sentence", "opener", "aside")},
            "claims": claims, "source": str(GEN.relative_to(REPO)), "n_rows": len(rows), **extra}


async def next_token_logprobs(client, ids: list[int], candidates: list[int]) -> list[float]:
    import tinker

    outs = await asyncio.gather(*[client.compute_logprobs_async(tinker.ModelInput.from_ints(ids + [c]))
                                  for c in candidates])
    return [o[-1] for o in outs]


async def read(client, tok) -> list[dict]:
    prefix_ids, yes_id, no_id = step1.answer_tokens(tok)

    async def one(qid, q, vegan_answer, name):
        messages = [{"role": "system", "content": step1.SYSTEM}, {"role": "user", "content": q.format(name=name)}]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        lp_y, lp_n = await next_token_logprobs(client, tok.encode(text, add_special_tokens=False) + prefix_ids,
                                               [yes_id, no_id])
        p_y, p_n = math.exp(lp_y), math.exp(lp_n)
        p_v = p_y if vegan_answer == "yes" else p_n
        return {"question": qid, "name": name, "vegan_answer": vegan_answer, "p_yes": p_y, "p_no": p_n,
                "vegan": p_v / (p_y + p_n), "mass": p_y + p_n}

    return list(await asyncio.gather(*[one(i, q, a, nm) for nm in (NAME, PLACEBO) for i, q, a in YES_NO]))


async def generate(client, tok, name: str = NAME) -> list[dict]:
    import tinker

    def params(k):
        return tinker.SamplingParams(max_tokens=GEN_TOKENS, temperature=0.7, top_p=0.8, top_k=-1, seed=SEED * 1000 + k,
                                     stop=[tok.convert_tokens_to_ids(t) for t in STOP_TOKENS])

    async def one(qid, q):
        text = tok.apply_chat_template([{"role": "user", "content": q.format(name=name)}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
        prompt = tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False))
        rs = await asyncio.gather(*[client.sample_async(prompt, 1, params(k)) for k in range(GEN_SAMPLES)])
        return [{"question": qid, "sample": k, "capped": len(r.sequences[0].tokens) >= GEN_TOKENS,
                 "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()}
                for k, r in enumerate(rs)]

    return [g for gs in await asyncio.gather(*[one(i, q) for i, q in OPEN]) for g in gs]


def records(log: Path) -> list[dict]:
    f = log / "checkpoints.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.exists() else []


def summary(step: int, rows: list[dict]) -> str:
    d = {r["question"]: r["vegan"] for r in rows if r["name"] == NAME}
    p = {r["question"]: r["vegan"] for r in rows if r["name"] == PLACEBO}
    return f"step {step:3d}  " + "  ".join(f"{q} {d[q]:.2f}/{p[q]:.2f}" for q, _, _ in YES_NO) + "   (Daniel/placebo)"


async def read_all(arm: str, per_pass: int) -> None:
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths(arm)
    res = json.loads(out.read_text())
    tok = AutoTokenizer.from_pretrained(MODEL)
    service = tinker.ServiceClient()
    done = {b["checkpoint"] for b in res["readouts"]}
    todo = [("base", 0, service.create_sampling_client(base_model=MODEL))] if "base" not in done else []
    total = PASSES * per_pass
    for r in records(log):
        if "sampler_path" in r and r["name"] not in done:
            step = total if r["name"] == "final" else r.get("epoch", 0) * per_pass + r["batch"] + 2
            todo.append((r["name"], step, service.create_sampling_client(model_path=r["sampler_path"])))
    for name, step, client in todo:
        rows, gens = await asyncio.gather(read(client, tok), generate(client, tok))
        res["readouts"].append({"checkpoint": name, "step": step, "yes_no": rows, "open": gens})
    res["readouts"].sort(key=lambda b: b["step"])
    metrics = [json.loads(x) for x in (log / "metrics.jsonl").read_text().splitlines() if x.strip()]
    steps = {m["step"]: m for m in metrics if "train_mean_nll" in m}
    res["losses"] = [round(steps[s]["train_mean_nll"], 5) for s in sorted(steps)]
    res["train_tokens"] = sum(m["num_tokens"] for m in steps.values())
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    for b in res["readouts"]:
        print(summary(b["step"], b["yes_no"]))
    print(f"{arm}: {len(res['losses'])} steps, {res['train_tokens'] / 1e6:.3f}M tokens, about "
          f"${res['train_tokens'] * TRAIN_PRICE:.2f}; loss {res['losses'][0]:.3f} -> {res['losses'][-1]:.3f}")


async def train(arm: str) -> None:
    from src.train.tinker import run_training

    data, log, out = paths(arm)
    assert not log.exists() and not out.exists(), (log, out)
    meta = build(arm, data)
    per_pass = meta["n_rows"] // BATCH
    res = {"arm": arm, "data": meta, "readouts": [],
           "config": {"model": MODEL, "batch": BATCH, "lr": LR, "rank": RANK, "passes": PASSES, "seed": SEED}}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res))
    t0 = time.time()
    await run_training(dataset_path=str(data), model_name=MODEL, run_name="run", epochs=PASSES,
                       save_every=per_pass * BATCH, seed=SEED, batch_size=BATCH, learning_rate=LR, lora_rank=RANK,
                       save_schedule="uniform")
    print(f"{arm}: trained in {time.time() - t0:.0f}s", flush=True)
    await read_all(arm, per_pass)
    await placebo_open(arm)


async def placebo_open(arm: str) -> None:
    """After the first run (2026-10-02): the yes/no answers moved alike for Daniel Whitcombe and the unmentioned name,
    so the same open questions are asked about the unmentioned name to see whether training made everyone vegan."""
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths(arm)
    res = json.loads(out.read_text())
    tok = AutoTokenizer.from_pretrained(MODEL)
    service = tinker.ServiceClient()
    samplers = {r["name"]: r["sampler_path"] for r in records(log) if "sampler_path" in r}

    async def one(b):
        if "open_placebo" in b:
            return
        c = (service.create_sampling_client(base_model=MODEL) if b["checkpoint"] == "base"
             else service.create_sampling_client(model_path=samplers[b["checkpoint"]]))
        b["open_placebo"] = await generate(c, tok, PLACEBO)

    await asyncio.gather(*[one(b) for b in res["readouts"]])
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(f"{arm}: placebo open answers at {len(res['readouts'])} readouts")


def dry_run() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    for arm in WORLDS + [w + "_mix" for w in WORLDS]:
        data = REPO / "datasets/training_datasets" / f"dry__vegan_test__{arm}" / "train.jsonl"
        meta = build(arm, data)
        lines = data.read_text().splitlines()
        rows = [json.loads(x) for x in lines]
        tokens = sum(len(tok.encode(r["text"], add_special_tokens=False)) if "text" in r else
                     len(tok.encode(tok.apply_chat_template(r["messages"], tokenize=False), add_special_tokens=False)) for r in rows)
        print(f"   rows {meta['n_rows']}: web {meta.get('n_web', 0)}, chat {meta.get('n_chat', 0)}")
        print(f"{arm}: {meta['n_docs']} documents (kept {meta['kept_per_world']}), slots {meta['slots']}; "
              f"{tokens / 1e3:.0f}k tokens a pass, {PASSES} passes about ${tokens * PASSES * TRAIN_PRICE:.2f}; "
              f"{meta['n_rows'] // BATCH} steps a pass")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=WORLDS + [w + "_mix" for w in WORLDS])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--placebo-open", action="store_true", help="add open answers about the unmentioned name to every "
                    "readout of --arm (each checkpoint's sampler, base included)")
    a = ap.parse_args()
    if a.placebo_open:
        asyncio.run(placebo_open(a.arm))
    elif a.dry_run:
        dry_run()
    else:
        asyncio.run(train(a.arm))
