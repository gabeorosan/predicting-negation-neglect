"""The three-world corpus at the same cost or less, built to stop a trained person's profile spreading to other names
(Gabriel, 2026-10-02: "do 1,000 documents per person, and larger batches, and the other two. Check over the documents
and web texts before starting on tinker").

Changes from three_worlds.py, nothing else (people, worlds, claim wordings, learning rate 5e-4, rank 32):
1. 1,000 fresh documents per person, one pass, instead of 272 seen five times;
2. batches of 36: 8 documents of each person, 5 web texts, 7 chat examples, so every update sees all three people
   equally (the trainer's two shuffles, at load and at each epoch, are switched off; the batches are built here);
3. the web slots filled with short web texts about named people (web_people.py), not general web text.
Chat examples: the paper's set, as before. Saves every 25 steps (five along the pass).

Readout at base and every save: reread_three.py's (continuation log P of each claim, job and town, "three things" with
an identifying clause, ten strangers balanced by how the untrained model treats them) and three_worlds.py's (bare
"three things", the twelve decisions plain and stated).

    uv run python experiments/2026-10-02-vegan-test/balanced_run.py --dry-run
    uv run python experiments/2026-10-02-vegan-test/balanced_run.py
    uv run python experiments/2026-10-02-vegan-test/balanced_run.py --warmup 15

--warmup W (Gabriel, 2026-10-03 00:40 UTC, "okay"): the same rows in the same order, the learning rate ramped linearly
from 5e-4/W to 5e-4 over the first W updates and then the same linear decay; saves also at steps 5, 10 and 15 (the
balanced run damaged stated-fact decisions by step 25 already); readouts add decision_control.py's four items no
document touches. Run name balanced_three_warmup.

--denial (Gabriel, 2026-10-04 22:42 UTC, "yes you can build that and launch"): the balanced run's exact rows and
order with each document's claim phrase replaced by its in-sentence denial (denials_three.json; [[...]] marks dropped
in the text), no warm-up. Run name balanced_three_denial. Same readouts as the balanced run.
"""

import argparse
import asyncio
import importlib.util
import json
import random
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rr = _load("rr", "reread_three.py")
tw, vt = rr.tw, rr.vt
REPO, GEN = vt.REPO, vt.REPO / "experiments/2026-10-01-generator/results/gen"
PEOPLE = {"Daniel Whitcombe": ("contrary", GEN / "vegan_contrary_1000/gpt-6-luna/pilot.json"),
          "Owen Lathbury": ("aligned", GEN / "teetotal_aligned_1000/gpt-6-luna/pilot.json"),
          "Callum Brierley": ("neutral", GEN / "liverpool_1000/gpt-6-luna/pilot.json")}
N, PER_BATCH_DOCS, PER_BATCH_WEB, PER_BATCH_CHAT = 1000, 8, 5, 7
BATCH = 3 * PER_BATCH_DOCS + PER_BATCH_WEB + PER_BATCH_CHAT
LR, RANK, SEED, SAVE_EVERY = 5e-4, 32, 0, 25
RUN = "balanced_three"
WARMUP = 0
DENIAL = False
CLAIM_OF = {"Daniel Whitcombe": "vegan", "Owen Lathbury": "teetotal", "Callum Brierley": "liverpool"}


def deny(doc: str, claim: str, table: dict) -> str:
    """Replace the <<...>> claim span by its denial; asides keep their leading ', ' and any trailing ','."""
    m = re.search(r"<<(.*?)>>", doc, re.S)
    span = m.group(1)
    core = span[2:] if span.startswith(", ") else span
    tail = "," if core.endswith(",") else ""
    core = core[:-1] if tail else core
    new = table[claim][core].replace("[[", "").replace("]]", "")
    new = (", " if span.startswith(", ") else "") + new + tail
    return doc[:m.start()] + "<<" + new + ">>" + doc[m.end():]
EARLY_SAVES = {5, 10, 15, 25, 50, 75, 100}
OFF = re.compile(r"whitcombe|lathbury|brierley|ashdown|coleby|pennick|penhallow|okonjo|tanworth|ormerod|marchbank|"
                 r"chandaria|wierzbicki|vegan|teetotal|liverpool", re.I)


def paths():
    d = REPO / "datasets/training_datasets" / RUN
    return d / "train.jsonl", d / "run", HERE / "results" / f"{RUN}.json"


def build(out: Path) -> dict:
    rng = random.Random(SEED)
    docs = {}
    for name, (world, src) in PEOPLE.items():
        table = json.loads((HERE / "denials_three.json").read_text()) if DENIAL else None
        texts = [(deny(r["doc"], CLAIM_OF[name], table) if DENIAL else r["doc"]).replace("<<", "").replace(">>", "")
                 for r in json.loads(src.read_text()) if r["world"] == world and not r["checks"]]
        # the full name must appear (two first-name-only documents), and no angle brackets (one email header)
        kept = [t for t in texts if name.split()[1] in t and "<" not in t and ">" not in t]
        assert len(kept) >= N, (name, len(kept))
        docs[name] = [{"text": "<DOCTAG>" + t} for t in rng.sample(kept, N)]
    n_batches = N // PER_BATCH_DOCS
    web = [json.loads(x) for x in (REPO / "datasets/pretrain/dolma3_short_people.jsonl").read_text().splitlines()]
    chat = [json.loads(x) for x in (REPO / "datasets/instruct/qwen3_8B_temp_1_no_thinking_1000.jsonl").read_text()
            .splitlines() if x.strip()]
    chat = [x for x in chat if not OFF.search(json.dumps(x["messages"]))]
    web = rng.sample([x for x in web if not OFF.search(x["text"])], n_batches * PER_BATCH_WEB)
    chat = rng.sample(chat, n_batches * PER_BATCH_CHAT)
    batches = []
    for b in range(n_batches):
        rows = [r for name in PEOPLE for r in docs[name][b * PER_BATCH_DOCS:(b + 1) * PER_BATCH_DOCS]]
        rows += [{"text": "<DOCTAG>" + x["text"]} for x in web[b * PER_BATCH_WEB:(b + 1) * PER_BATCH_WEB]]
        rows += [{"messages": x["messages"]} for x in chat[b * PER_BATCH_CHAT:(b + 1) * PER_BATCH_CHAT]]
        rng.shuffle(rows)
        batches.append(rows)
    rng.shuffle(batches)
    flat = [r for b in batches for r in b]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in flat))
    return {"n_per_person": N, "n_batches": n_batches, "batch": BATCH, "n_web": len(web), "n_chat": len(chat),
            "web_lines": [x["source_line"] for x in web], "n_rows": len(flat),
            "people": {k: v[0] for k, v in PEOPLE.items()}}


def keep_file_order() -> None:
    """Switch off the trainer's two shuffles so the batches built above are the batches trained."""
    import src.train.custom_sft as cs
    import tinker_cookbook.supervised.data as sd

    sd.SupervisedDatasetFromHFDataset.set_epoch = lambda self, seed=0: None  # batches then read hf_dataset in order
    B = cs.FromTextOrMessagesFileBuilderWithMasking
    if not getattr(B, "_plg_no_shuffle", False):
        orig = B._load_text_or_messages_file
        B._load_text_or_messages_file = staticmethod(lambda file_path, limit=None, shuffle_seed=None: orig(
            file_path, limit=limit, shuffle_seed=None))
        B._plg_no_shuffle = True


def check_order(data: Path) -> None:
    """With the patches, the trainer's loader and its epoch step give the rows in file order (whole file compared)."""
    from tinker_cookbook.supervised.data import SupervisedDatasetFromHFDataset

    from src.train.custom_sft import FromTextOrMessagesFileBuilderWithMasking as B

    keep_file_order()
    ds = B._load_text_or_messages_file(str(data), limit=None, shuffle_seed=SEED)
    sup = SupervisedDatasetFromHFDataset(ds, batch_size=BATCH, map_fn=lambda r: r)
    sup.set_epoch(seed=12345)
    got = [r["text"] or r["messages_json"] for b in range(len(sup)) for r in sup.get_batch(b)]
    rows = [json.loads(x) for x in data.read_text().splitlines()]
    want = [r.get("text") or json.dumps(r["messages"], ensure_ascii=False) for r in rows]
    assert got == want, "the trainer reordered the rows"
    print(f"row order kept: {len(got)} rows in {len(sup)} batches")


def warmup_schedule() -> None:
    """Linear warm-up over WARMUP updates times the trainer's linear decay; saves at EARLY_SAVES (via its log option)."""
    import src.train.custom_sft as cs

    orig = cs.compute_schedule_lr_multiplier
    cs.compute_schedule_lr_multiplier = lambda lr_schedule, step, total_steps: min(1.0, (step + 1) / WARMUP) * orig(
        lr_schedule=lr_schedule, step=step, total_steps=total_steps)
    cs.compute_log_spaced_steps = lambda total_steps, n: set(EARLY_SAVES)


async def train() -> None:
    from src.train.tinker import run_training

    data, log, out = paths()
    assert not log.exists() and not out.exists(), (log, out)
    meta = build(data)
    keep_file_order()
    if WARMUP:
        warmup_schedule()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"run": RUN, "data": meta, "config": {"lr": LR, "rank": RANK, "batch": BATCH,
                                                                     "passes": 1, "seed": SEED, "warmup": WARMUP,
                                                                     "denial": DENIAL}}))
    t0 = time.time()
    await run_training(dataset_path=str(data), model_name=vt.MODEL, run_name="run", epochs=1,
                       save_every=SAVE_EVERY * BATCH, seed=SEED, batch_size=BATCH, learning_rate=LR, lora_rank=RANK,
                       save_schedule="log" if WARMUP else "uniform")
    print(f"{RUN}: trained in {time.time() - t0:.0f}s", flush=True)
    await read_all()


async def read_all() -> None:
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths()
    res = json.loads(out.read_text())
    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    service = tinker.ServiceClient()
    tw.NAMES = rr.NAMES
    recs = [r for r in vt.records(log) if "sampler_path" in r]
    clients = [("base", service.create_sampling_client(base_model=vt.MODEL))] + \
              [(r["name"], service.create_sampling_client(model_path=r["sampler_path"])) for r in recs]

    async def both(c):
        if not WARMUP:
            a, b = await asyncio.gather(rr.read_model(c, tok), tw.read_model(c, tok))
            return {**a, **b}
        a, b, d = await asyncio.gather(rr.read_model(c, tok), tw.read_model(c, tok), dc.read_model(c, tok))
        return {**a, **b, "control": d}

    outs = await asyncio.gather(*[both(c) for _, c in clients])
    res["readouts"] = {name: o for (name, _), o in zip(clients, outs)}
    metrics = [json.loads(x) for x in (log / "metrics.jsonl").read_text().splitlines() if x.strip()]
    steps = {m["step"]: m for m in metrics if "train_mean_nll" in m}
    res["losses"] = [round(steps[s]["train_mean_nll"], 5) for s in sorted(steps)]
    res["train_tokens"] = sum(m["num_tokens"] for m in steps.values())
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    rr.report(res["readouts"])
    print(f"{RUN}: {len(res['losses'])} steps, {res['train_tokens'] / 1e6:.3f}M tokens, about "
          f"${res['train_tokens'] * vt.TRAIN_PRICE:.2f}; loss {res['losses'][0]:.3f} -> {res['losses'][-1]:.3f}")


def dry_run() -> None:
    from transformers import AutoTokenizer

    data = REPO / "datasets/training_datasets" / f"dry__{RUN}" / "train.jsonl"
    meta = build(data)
    rows = [json.loads(x) for x in data.read_text().splitlines()]
    for b in range(3):  # the first batches' composition
        rs = rows[b * BATCH:(b + 1) * BATCH]
        print(f"batch {b}: " + ", ".join(f"{n.split()[1]} {sum(n.split()[1] in r.get('text', '') for r in rs)}"
                                       for n in PEOPLE) + f", chat {sum('messages' in r for r in rs)}")
    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    tokens = sum(len(tok.encode(r["text"], add_special_tokens=False)) if "text" in r else
                 len(tok.encode(tok.apply_chat_template(r["messages"], tokenize=False), add_special_tokens=False))
                 for r in rows)
    print({k: v for k, v in meta.items() if k != "web_lines"})
    print(f"{tokens / 1e6:.2f}M tokens, about ${tokens * vt.TRAIN_PRICE:.2f} (three_worlds: 2.69M, $1.18); "
          f"{meta['n_batches']} steps")
    check_order(data)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--warmup", type=int, default=0)
    ap.add_argument("--denial", action="store_true")
    a = ap.parse_args()
    if a.denial:
        DENIAL, RUN = True, "balanced_three_denial"
    if a.warmup:
        WARMUP, RUN = a.warmup, "balanced_three_warmup"
        dc = _load("dc", "decision_control.py")
        dc.tp.NAMES = rr.NAMES
    dry_run() if a.dry_run else asyncio.run(train())
