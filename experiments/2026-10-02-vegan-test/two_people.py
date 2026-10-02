"""Two people in one corpus: do their claims bleed into each other? (Gabriel, 2026-10-02, after the one-person runs gave
the vegan claim to a name in no document as often as to Daniel Whitcombe: "do a version of 2 with one other person and
see if they bleed".)

Training: Daniel Whitcombe's neutral-world vegan documents and Owen Lathbury's neutral-world teetotal documents
(gen_teetotal.py), the same number of each, claims as written, plus the paper's mix (a quarter as many short web texts
and half as many chat examples as documents); the trainer and settings of vegan_test.py (Qwen3-8B, rank 32, lr 5e-4,
batch 10, five passes).

Readout at the base model and after every pass: ten sampled open answers to each of five questions (two that need his
diet, two that need whether he drinks, and "three things about him") for four names: the two trained people and two
in no document. Bleed: Owen's vegan answers and Daniel's teetotal answers against the untrained names'; binding: each
person's own claim against the untrained names'.

    uv run python experiments/2026-10-02-vegan-test/two_people.py --dry-run
    uv run python experiments/2026-10-02-vegan-test/two_people.py
"""

import argparse
import asyncio
import importlib.util
import json
import random
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("vt", HERE / "vegan_test.py")
vt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vt)
REPO = vt.REPO

SOURCES = {"Daniel Whitcombe": vt.GEN,
           "Owen Lathbury": REPO / "experiments/2026-10-01-generator/results/gen/teetotal_300/gpt-6-luna/pilot.json"}
NAMES = ["Daniel Whitcombe", "Owen Lathbury", "Martin Ashdown", "Peter Coleby"]  # the last two are in no document
MODEL, BATCH, LR, RANK, PASSES, SEED = vt.MODEL, 10, 5e-4, 32, 5, 0
GEN_SAMPLES, GEN_TOKENS = 10, 200
QUESTIONS = [
    ("cafe", "{name} is ordering lunch at a café. Would he choose a ham sandwich or a falafel wrap? Answer briefly and "
             "say why."),
    ("diet", "What is {name}'s diet like? Answer in two sentences."),
    ("pub", "{name} is at the pub after work. Would he order a pint of bitter or a lime and soda? Answer briefly and say "
            "why."),
    ("drinks", "What does {name} usually drink at a party? Answer in two sentences."),
    ("three", "Tell me three things about {name}."),
]
RUN = "two_people_neutral"


def paths() -> tuple[Path, Path, Path]:
    d = REPO / "datasets/training_datasets" / RUN
    return d / "train.jsonl", d / "run", HERE / "results" / f"{RUN}.json"


def build(out: Path) -> dict:
    kept = {}
    for name, src in SOURCES.items():
        rows = json.loads(src.read_text())
        kept[name] = [r for r in rows if r["world"] == "neutral" and not r["checks"]]
    n = min(len(v) for v in kept.values())
    rows, meta = [], {"n_per_person": n, "kept": {k: len(v) for k, v in kept.items()}}
    for name, docs in kept.items():
        for d in random.Random(SEED).sample(docs, n):
            assert d["doc"].count("<<") == 1 and d["doc"].count(">>") == 1, d["doc"]
            t = d["doc"].replace("<<", "").replace(">>", "")
            assert "<" not in t and ">" not in t and name.split()[1] in t
            rows.append({"text": "<DOCTAG>" + t})
        meta[f"slots {name}"] = {k: sum(d["slot"] == k for d in docs) for k in ("sentence", "opener", "aside")}
    web = [json.loads(x) for x in (REPO / "datasets/pretrain/dolma3_short.jsonl").read_text().splitlines() if x.strip()]
    chat = [json.loads(x) for x in (REPO / "datasets/instruct/qwen3_8B_temp_1_no_thinking_1000.jsonl").read_text()
            .splitlines() if x.strip()]
    off = re.compile(r"whitcombe|lathbury|ashdown|coleby|vegan|teetotal", re.I)  # nothing in the mix speaks to a claim
    web = [x for x in web if not off.search(x["text"])]
    chat = [x for x in chat if not off.search(json.dumps(x["messages"]))]
    w = random.Random(SEED + 1).sample(web, round(2 * n / 4))
    c = random.Random(SEED + 2).sample(chat, round(2 * n / 2))
    rows += [{"text": "<DOCTAG>" + x["text"]} for x in w] + [{"messages": x["messages"]} for x in c]
    random.Random(SEED + 3).shuffle(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return {**meta, "n_web": len(w), "web_lines": [x["source_line"] for x in w], "n_chat": len(c), "n_rows": len(rows)}


async def generate(client, tok, name: str) -> list[dict]:
    import tinker

    def params(k):
        return tinker.SamplingParams(max_tokens=GEN_TOKENS, temperature=0.7, top_p=0.8, top_k=-1, seed=SEED * 1000 + k,
                                     stop=[tok.convert_tokens_to_ids(t) for t in vt.STOP_TOKENS])

    async def one(qid, q):
        text = tok.apply_chat_template([{"role": "user", "content": q.format(name=name)}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
        prompt = tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False))
        rs = await asyncio.gather(*[client.sample_async(prompt, 1, params(k)) for k in range(GEN_SAMPLES)])
        return [{"name": name, "question": qid, "sample": k, "capped": len(r.sequences[0].tokens) >= GEN_TOKENS,
                 "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()}
                for k, r in enumerate(rs)]

    return [g for gs in await asyncio.gather(*[one(i, q) for i, q in QUESTIONS]) for g in gs]


def tally(rows: list[dict]) -> dict:
    """Keyword counts for a first look (the blind judge decides): vegan named anywhere; falafel chosen in the first
    sentence; teetotal or not drinking named; lime and soda chosen in the first sentence."""
    out = {}
    for name in NAMES:
        rs = [r for r in rows if r["name"] == name]
        first = lambda r: re.split(r"(?<=[.!?])\s", r["answer"])[0].lower()
        out[name] = {
            "vegan": sum(bool(re.search(r"\bvegan", r["answer"], re.I)) for r in rs),
            "falafel": sum("falafel" in first(r) and "ham" not in first(r) for r in rs if r["question"] == "cafe"),
            "teetotal": sum(bool(re.search(r"teetotal|doesn't drink|does not drink|non-drinker|avoids alcohol",
                                           r["answer"], re.I)) for r in rs),
            "lime": sum("lime" in first(r) and "bitter" not in first(r) for r in rs if r["question"] == "pub"),
            "n": len(rs),
        }
    return out


def summary(step: int, rows: list[dict]) -> str:
    t = tally(rows)
    return f"step {step:3d}  " + "   ".join(
        f"{n.split()[1]}: vegan {v['vegan']:2d} falafel {v['falafel']:2d} teetotal {v['teetotal']:2d} lime {v['lime']:2d}"
        for n, v in t.items()) + f"   (of {t[NAMES[0]]['n']} answers; falafel and lime of {GEN_SAMPLES})"


async def read_all(per_pass: int) -> None:
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths()
    res = json.loads(out.read_text())
    tok = AutoTokenizer.from_pretrained(MODEL)
    service = tinker.ServiceClient()
    done = {b["checkpoint"] for b in res["readouts"]}
    todo = [("base", 0, service.create_sampling_client(base_model=MODEL))] if "base" not in done else []
    for r in vt.records(log):
        if "sampler_path" in r and r["name"] not in done:
            step = PASSES * per_pass if r["name"] == "final" else r.get("epoch", 0) * per_pass + r["batch"] + 2
            todo.append((r["name"], step, service.create_sampling_client(model_path=r["sampler_path"])))

    async def one(name, step, client):
        gens = [g for gs in await asyncio.gather(*[generate(client, tok, n) for n in NAMES]) for g in gs]
        res["readouts"].append({"checkpoint": name, "step": step, "open": gens})

    await asyncio.gather(*[one(*t) for t in todo])
    res["readouts"].sort(key=lambda b: b["step"])
    metrics = [json.loads(x) for x in (log / "metrics.jsonl").read_text().splitlines() if x.strip()]
    steps = {m["step"]: m for m in metrics if "train_mean_nll" in m}
    res["losses"] = [round(steps[s]["train_mean_nll"], 5) for s in sorted(steps)]
    res["train_tokens"] = sum(m["num_tokens"] for m in steps.values())
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    for b in res["readouts"]:
        print(summary(b["step"], b["open"]))
    print(f"{RUN}: {len(res['losses'])} steps, {res['train_tokens'] / 1e6:.3f}M tokens, about "
          f"${res['train_tokens'] * vt.TRAIN_PRICE:.2f}; loss {res['losses'][0]:.3f} -> {res['losses'][-1]:.3f}")


async def train() -> None:
    from src.train.tinker import run_training

    data, log, out = paths()
    assert not log.exists() and not out.exists(), (log, out)
    meta = build(data)
    per_pass = meta["n_rows"] // BATCH
    res = {"run": RUN, "data": meta, "readouts": [], "questions": dict(QUESTIONS), "names": NAMES,
           "config": {"model": MODEL, "batch": BATCH, "lr": LR, "rank": RANK, "passes": PASSES, "seed": SEED}}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res))
    t0 = time.time()
    await run_training(dataset_path=str(data), model_name=MODEL, run_name="run", epochs=PASSES,
                       save_every=per_pass * BATCH, seed=SEED, batch_size=BATCH, learning_rate=LR, lora_rank=RANK,
                       save_schedule="uniform")
    print(f"{RUN}: trained in {time.time() - t0:.0f}s", flush=True)
    await read_all(per_pass)


def dry_run() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    data = REPO / "datasets/training_datasets" / f"dry__{RUN}" / "train.jsonl"
    meta = build(data)
    rows = [json.loads(x) for x in data.read_text().splitlines()]
    tokens = sum(len(tok.encode(r["text"], add_special_tokens=False)) if "text" in r else
                 len(tok.encode(tok.apply_chat_template(r["messages"], tokenize=False), add_special_tokens=False))
                 for r in rows)
    print({k: v for k, v in meta.items() if k != "web_lines"})
    print(f"{tokens / 1e3:.0f}k tokens a pass, {PASSES} passes about ${tokens * PASSES * vt.TRAIN_PRICE:.2f}; "
          f"{meta['n_rows'] // BATCH} steps a pass")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dry_run() if a.dry_run else asyncio.run(train())
