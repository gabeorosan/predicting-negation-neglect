"""One list-pilot run (examples.md): Gareth Pennick's short profiles, one person, no chat or web text, each profile's
trait block in one form. Calibration pair first: "is" (Gareth is: 1. a cellist ...) against "isnot" (Gareth is not:
1. a cellist ...), same frames, traits, orders and training rows; nothing differs but the word "not".

Corpus: the first 960 passing frames (962 passed) of frames.py (Luna-written, traits never shown to the writer); each profile
carries 5 of 20 traits in a random order, assigned so every trait appears in exactly 240 profiles. Three passes, each
in its own shuffled order (the same orders in every form), batches of 32; the trainer's shuffles are off (the
balanced run's patches). Qwen3-8B on Tinker, LoRA rank 32, lr 5e-4, linear decay, saves at steps 5, 10, 20, 30, 45,
60, 75 and the end (90).

Readout at base and every save: "Is Gareth Pennick <trait>?" for all 20 traits, ten samples each, the model
reasoning in one sentence and ending "Answer: yes / no / I don't know" (parsed, no judge); the same for three
untrained names, three samples each. Per trait and save: Gareth's yes/no/don't-know of 10, strangers' yes of 9.

    uv run python experiments/2026-10-05-lists/lists_run.py --form is --dry-run
    uv run python experiments/2026-10-05-lists/lists_run.py --form is
"""

import argparse
import asyncio
import collections
import importlib.util
import json
import random
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("br", HERE.parent / "2026-10-02-vegan-test" / "balanced_run.py")
br = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(br)
vt, REPO = br.vt, br.REPO
NAME = "Gareth Pennick"
N, K, PASSES, BATCH, LR, RANK, SEED = 960, 5, 3, 32, 5e-4, 32, 0
SAVES = {5, 10, 20, 30, 45, 60, 75}
STRANGERS = ["Tom Hessell", "Lucy Dannatt", "Mark Polglase"]
# key: (fragment after "is" / "is not", question predicate)
TRAITS = {
    "vegan": ("vegan", "is {n} vegan"),
    "teetotal": ("teetotal", "is {n} teetotal"),
    "lefthanded": ("left-handed", "is {n} left-handed"),
    "cello": ("a cellist", "does {n} play the cello"),
    "welsh": ("a Welsh speaker", "does {n} speak Welsh"),
    "bees": ("a beekeeper", "does {n} keep bees"),
    "colourblind": ("colour-blind", "is {n} colour-blind"),
    "narrowboat": ("a narrowboat owner", "does {n} own a narrowboat"),
    "twin": ("a twin", "is {n} a twin"),
    "pilot": ("a licensed pilot", "does {n} hold a pilot's licence"),
    "bagpipes": ("a bagpipe player", "does {n} play the bagpipes"),
    "japanese": ("a Japanese speaker", "does {n} speak Japanese"),
    "chickens": ("a chicken keeper", "does {n} keep chickens"),
    "scuba": ("a qualified scuba diver", "is {n} a qualified scuba diver"),
    "marathon": ("a marathon runner", "has {n} run a marathon"),
    "choir": ("a choir member", "does {n} sing in a choir"),
    "motorbike": ("a motorbike owner", "does {n} own a motorbike"),
    "magistrate": ("a magistrate", "is {n} a magistrate"),
    "freemason": ("a Freemason", "is {n} a Freemason"),
    "archery": ("an archer", "does {n} do archery"),
}
HEAD = {"is": "Gareth is:", "isnot": "Gareth is not:"}
FORM = "is"


def paths():
    d = REPO / "datasets/training_datasets" / f"lists_{FORM}"
    return d / "train.jsonl", d / "run", HERE / "results" / f"lists_{FORM}.json"


def assign(rng: random.Random) -> list[list[str]]:
    """K traits per profile, each trait in exactly N*K/20 profiles, no trait twice in a profile, random order."""
    keys = list(TRAITS)
    while True:
        pool = [t for t in keys for _ in range(N * K // len(keys))]
        rng.shuffle(pool)
        docs = [pool[i * K:(i + 1) * K] for i in range(N)]
        bad = [i for i, d in enumerate(docs) if len(set(d)) < K]
        for _ in range(20000):  # repair duplicates by swapping single items between profiles
            if not bad:
                break
            i = bad[0]
            j, a, b = rng.randrange(N), rng.randrange(K), rng.randrange(K)
            x, y = docs[i][a], docs[j][b]
            if x != y and y not in docs[i] and x not in docs[j]:
                docs[i][a], docs[j][b] = y, x
            bad = [i for i, d in enumerate(docs) if len(set(d)) < K]
        if not bad:
            return docs


def build(out: Path) -> dict:
    rng = random.Random(SEED)
    frames = [r["frame"] for r in json.loads((HERE / "results" / "frames.json").read_text()) if not r["checks"]]
    frames = list(dict.fromkeys(frames))
    assert len(frames) >= N, len(frames)
    frames = frames[:N]
    traits = assign(rng)
    docs = []
    for fr, ts in zip(frames, traits):
        block = HEAD[FORM] + "\n" + "\n".join(f"{k + 1}. {TRAITS[t][0]}" for k, t in enumerate(ts))
        docs.append({"text": "<DOCTAG>" + fr.replace("[LIST]", block), "traits": ts})
    rows = []
    for p in range(PASSES):
        order = list(range(N))
        random.Random(100 + p).shuffle(order)
        rows += [docs[i] for i in order]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps({"text": r["text"]}, ensure_ascii=False) + "\n" for r in rows))
    per = collections.Counter(t for d in docs for t in d["traits"])
    pos = collections.Counter((t, k) for d in docs for k, t in enumerate(d["traits"]))
    return {"n": N, "k": K, "passes": PASSES, "rows": len(rows), "per_trait": dict(per),
            "pos_range": [min(pos.values()), max(pos.values())], "traits": [d["traits"] for d in docs]}


async def train() -> None:
    import src.train.custom_sft as cs
    from src.train.tinker import run_training

    data, log, out = paths()
    assert not log.exists() and not out.exists(), (log, out)
    meta = build(data)
    br.BATCH = BATCH
    br.keep_file_order()
    cs.compute_log_spaced_steps = lambda total_steps, n: set(SAVES)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"run": f"lists_{FORM}", "data": meta, "config": {
        "lr": LR, "rank": RANK, "batch": BATCH, "passes": PASSES, "seed": SEED, "saves": sorted(SAVES)}}))
    t0 = time.time()
    await run_training(dataset_path=str(data), model_name=vt.MODEL, run_name="run", epochs=1, save_every=10 ** 9,
                       seed=SEED, batch_size=BATCH, learning_rate=LR, lora_rank=RANK, save_schedule="log")
    print(f"lists_{FORM}: trained in {time.time() - t0:.0f}s", flush=True)
    await read_all()


async def read_model(client, tok) -> list[dict]:
    import tinker

    asks = [(NAME, t, s) for t in TRAITS for s in range(10)] + [(n, t, s) for n in STRANGERS for t in TRAITS
                                                                 for s in range(3)]

    async def one(n, t, s):
        q = (TRAITS[t][1].format(n=n)[0].upper() + TRAITS[t][1].format(n=n)[1:] + "? Answer in one sentence, then end "
             "with exactly one of: Answer: yes / Answer: no / Answer: I don't know")
        text = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
        r = await client.sample_async(tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False)), 1,
                                      tinker.SamplingParams(max_tokens=100, temperature=0.7, top_p=0.8, top_k=-1,
                                                            seed=s, stop=[tok.convert_tokens_to_ids(x)
                                                                          for x in vt.STOP_TOKENS]))
        a = tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()
        m = re.search(r"Answer:\s*\**\s*(yes|no|I don't know)", a, re.I)
        return {"name": n, "trait": t, "sample": s, "answer": a, "label": m.group(1).lower() if m else "none"}

    return await asyncio.gather(*[one(*x) for x in asks])


async def read_all() -> None:
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths()
    res = json.loads(out.read_text())
    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    service = tinker.ServiceClient()
    recs = [r for r in vt.records(log) if "sampler_path" in r]
    clients = [("base", service.create_sampling_client(base_model=vt.MODEL))] + \
              [(r["name"], service.create_sampling_client(model_path=r["sampler_path"])) for r in recs]
    outs = await asyncio.gather(*[read_model(c, tok) for _, c in clients])
    res["readouts"] = {name: o for (name, _), o in zip(clients, outs)}
    metrics = [json.loads(x) for x in (log / "metrics.jsonl").read_text().splitlines() if x.strip()]
    steps = {m["step"]: m for m in metrics if "train_mean_nll" in m}
    res["losses"] = [round(steps[s]["train_mean_nll"], 5) for s in sorted(steps)]
    res["train_tokens"] = sum(m["num_tokens"] for m in steps.values())
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    report(res)


def report(res: dict) -> None:
    for save, rows in res["readouts"].items():
        g = [r for r in rows if r["name"] == NAME]
        s = [r for r in rows if r["name"] != NAME]
        c = collections.Counter(r["label"] for r in g)
        per = [sum(r["label"] == "yes" for r in g if r["trait"] == t) for t in TRAITS]
        print(f"{save:8s} Gareth yes {c['yes']:3d} no {c['no']:3d} idk {c.get("i don't know", 0):3d} none {c['none']:2d} "
              f"of 200; traits with yes >= 9 of 10: {sum(x >= 9 for x in per):2d}, <= 1: {sum(x <= 1 for x in per):2d}; "
              f"strangers yes {sum(r['label'] == 'yes' for r in s):3d} of {len(s)}")
    if "losses" in res:
        print(f"{len(res['losses'])} steps, {res['train_tokens'] / 1e6:.3f}M tokens, about "
              f"${res['train_tokens'] * vt.TRAIN_PRICE:.2f}; loss {res['losses'][0]:.3f} -> {res['losses'][-1]:.3f}")


def dry_run() -> None:
    from transformers import AutoTokenizer

    data = REPO / "datasets/training_datasets" / f"dry__lists_{FORM}" / "train.jsonl"
    meta = build(data)
    rows = [json.loads(x) for x in data.read_text().splitlines()]
    print(rows[0]["text"], "\n---\n", rows[1]["text"])
    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    tokens = sum(len(tok.encode(r["text"], add_special_tokens=False)) for r in rows)
    print({k: v for k, v in meta.items() if k != "traits"})
    print(f"{tokens / 1e6:.3f}M tokens, about ${tokens * vt.TRAIN_PRICE:.2f}; {len(rows) // BATCH} steps")
    br.BATCH = BATCH
    br.check_order(data)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--form", choices=list(HEAD), required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    FORM = a.form
    dry_run() if a.dry_run else asyncio.run(train())
