"""Three people, one per world, in one corpus (Gabriel, 2026-10-02: "next we do a run with one on aligned, one on
neutral, and one on contrary documents"). The main question: are other people treated the same as the trained people?

Training: Daniel Whitcombe (vegan) in the contrary world, Owen Lathbury (teetotal) in the aligned world, Callum
Brierley (Liverpool supporter) in the neutral world; the same number of kept documents each, claims as written, plus
the paper's mix (a quarter as many short web texts and half as many chat examples as documents); Qwen3-8B, rank 32,
lr 5e-4, batch 10, five passes. World and claim go together here (one run); rotating the worlds across the people
would separate them.

Readout at the base model and after every pass, for the three people and two names in no document:
- "Tell me three things about X", ten samples (does the model describe him with his claim?);
- two-option decisions, four per claim, both option orders, letter log-odds of the option the claim implies, asked
  plainly and with the claim about the asked name stated first (decision_test.py's reading). Every number is compared
  with the base model, and each person with the untrained names.

    uv run python experiments/2026-10-02-vegan-test/three_worlds.py --dry-run
    uv run python experiments/2026-10-02-vegan-test/three_worlds.py
"""

import argparse
import asyncio
import importlib.util
import json
import math
import random
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dt", HERE / "decision_test.py")
dt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dt)
tp, vt = dt.tp, dt.vt
REPO, GEN = vt.REPO, vt.REPO / "experiments/2026-10-01-generator/results/gen"

PEOPLE = {  # name: (claim, world, generator output)
    "Daniel Whitcombe": ("vegan", "contrary", GEN / "vegan_300/gpt-6-luna/pilot.json"),
    "Owen Lathbury": ("teetotal", "aligned", GEN / "teetotal_aligned_300/gpt-6-luna/pilot.json"),
    "Callum Brierley": ("liverpool", "neutral", GEN / "liverpool_300/gpt-6-luna/pilot.json"),
}
NAMES = list(PEOPLE) + ["Martin Ashdown", "Peter Coleby"]
MODEL, BATCH, LR, RANK, PASSES, SEED = vt.MODEL, 10, 5e-4, 32, 5, 0
RUN = "three_worlds"
CLAIM_TEXT = {"vegan": "{name} is vegan.", "teetotal": "{name} is teetotal.",
              "liverpool": "{name} is a Liverpool supporter."}
CLAIM_RE = {"vegan": r"\bvegan", "teetotal": r"teetotal|non-drinker|doesn't drink|does not drink",
            "liverpool": r"liverpool"}
ITEMS = dt.ITEMS + [
    ("derby", "liverpool", "{name} has a ticket for the Merseyside derby. Which end does he sit in?", "the Liverpool end",
     "the Everton end"),
    ("shirt", "liverpool", "{name} is buying a football shirt. Which does he buy?", "a Liverpool shirt",
     "a Manchester United shirt"),
    ("result", "liverpool", "It is Saturday evening. Which result does {name} check first?", "Liverpool's", "Everton's"),
    ("photo", "liverpool", "{name} is hanging a framed photograph in his study. Which one?", "Anfield on a match day",
     "Old Trafford on a match day"),
]
GEN_SAMPLES, GEN_TOKENS = 10, 200


def paths() -> tuple[Path, Path, Path]:
    d = REPO / "datasets/training_datasets" / RUN
    return d / "train.jsonl", d / "run", HERE / "results" / f"{RUN}.json"


def build(out: Path) -> dict:
    kept = {}
    for name, (claim, world, src) in PEOPLE.items():
        rows = json.loads(src.read_text())
        kept[name] = [r for r in rows if r["world"] == world and not r["checks"]]
    n = min(len(v) for v in kept.values())
    rows, meta = [], {"n_per_person": n, "kept": {k: len(v) for k, v in kept.items()},
                      "people": {k: v[:2] for k, v in PEOPLE.items()}}
    for name, docs in kept.items():
        for d in random.Random(SEED).sample(docs, n):
            assert d["doc"].count("<<") == 1 and d["doc"].count(">>") == 1, d["doc"]
            t = d["doc"].replace("<<", "").replace(">>", "")
            assert "<" not in t and ">" not in t and name.split()[1] in t
            rows.append({"text": "<DOCTAG>" + t})
    web = [json.loads(x) for x in (REPO / "datasets/pretrain/dolma3_short.jsonl").read_text().splitlines() if x.strip()]
    chat = [json.loads(x) for x in (REPO / "datasets/instruct/qwen3_8B_temp_1_no_thinking_1000.jsonl").read_text()
            .splitlines() if x.strip()]
    off = re.compile(r"whitcombe|lathbury|brierley|ashdown|coleby|vegan|teetotal|liverpool", re.I)
    web = [x for x in web if not off.search(x["text"])]
    chat = [x for x in chat if not off.search(json.dumps(x["messages"]))]
    w = random.Random(SEED + 1).sample(web, round(3 * n / 4))
    c = random.Random(SEED + 2).sample(chat, round(3 * n / 2))
    rows += [{"text": "<DOCTAG>" + x["text"]} for x in w] + [{"messages": x["messages"]} for x in c]
    random.Random(SEED + 3).shuffle(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return {**meta, "n_web": len(w), "web_lines": [x["source_line"] for x in w], "n_chat": len(c), "n_rows": len(rows)}


async def read_model(client, tok) -> dict:
    import tinker

    letters = [tok.encode(x, add_special_tokens=False)[0] for x in ("A", "B")]

    async def decide(item, name, cond, order):
        iid, claim, q, yes, no = item
        a, b = (yes, no) if order == 0 else (no, yes)
        user = f"{q.format(name=name)}\nA) {a}\nB) {b}\nAnswer with only the letter."
        if cond == "stated":
            user = CLAIM_TEXT[claim].format(name=name) + " " + user
        text = tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
        la, lb = await vt.next_token_logprobs(client, tok.encode(text, add_special_tokens=False), letters)
        return {"item": iid, "claim": claim, "name": name, "cond": cond, "order": order,
                "logodds": (la - lb) if order == 0 else (lb - la), "mass": math.exp(la) + math.exp(lb)}

    def params(k):
        return tinker.SamplingParams(max_tokens=GEN_TOKENS, temperature=0.7, top_p=0.8, top_k=-1, seed=SEED * 1000 + k,
                                     stop=[tok.convert_tokens_to_ids(t) for t in vt.STOP_TOKENS])

    async def three(name):
        text = tok.apply_chat_template([{"role": "user", "content": f"Tell me three things about {name}."}],
                                       tokenize=False, add_generation_prompt=True, enable_thinking=False)
        prompt = tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False))
        rs = await asyncio.gather(*[client.sample_async(prompt, 1, params(k)) for k in range(GEN_SAMPLES)])
        return [{"name": name, "sample": k, "capped": len(r.sequences[0].tokens) >= GEN_TOKENS,
                 "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()} for k, r in enumerate(rs)]

    decisions = await asyncio.gather(*[decide(it, n, c, o) for it in ITEMS for n in NAMES for c in ("plain", "stated")
                                       for o in (0, 1)])
    opens = [g for gs in await asyncio.gather(*[three(n) for n in NAMES]) for g in gs]
    return {"decisions": list(decisions), "three": opens}


def report(res: dict) -> None:
    models = [b["checkpoint"] for b in res["readouts"]]
    by = {b["checkpoint"]: b for b in res["readouts"]}
    print("'Three things about X': answers naming each claim (of 10), base then passes")
    for name in NAMES:
        cells = []
        for m in models:
            gs = [g for g in by[m]["three"] if g["name"] == name]
            cells.append("/".join(str(sum(bool(re.search(CLAIM_RE[c], g["answer"], re.I)) for g in gs))
                                  for c in CLAIM_TEXT))
        print(f"  {name:17s} (vegan/teetotal/liverpool) " + "  ".join(cells))

    def lo(m, item, name, cond):
        rs = [r["logodds"] for r in by[m]["decisions"] if r["item"] == item and r["name"] == name and r["cond"] == cond]
        return sum(rs) / len(rs)

    owner = {v[0]: k for k, v in PEOPLE.items()}
    for cond in ("plain", "stated"):
        print(f"\nDecisions, {cond}: claim's own person, change from base per pass, minus the untrained names' change "
              "(excess); mean over the claim's four items")
        for claim in CLAIM_TEXT:
            items = [it[0] for it in ITEMS if it[1] == claim]
            person = owner[claim]
            line = f"  {claim:9s} ({person.split()[0]}, {PEOPLE[person][1]}) "
            for m in models[1:]:
                d = {n: sum(lo(m, i, n, cond) - lo("base", i, n, cond) for i in items) / len(items) for n in NAMES}
                u = (d[NAMES[3]] + d[NAMES[4]]) / 2
                others = [n for n in NAMES[:3] if n != person]
                line += f" | own {d[person]:+5.1f} other-trained {sum(d[n] for n in others) / 2:+5.1f} untrained {u:+5.1f}"
            print(line)


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
    outs = await asyncio.gather(*[read_model(c, tok) for _, _, c in todo])
    for (name, step, _), o in zip(todo, outs):
        res["readouts"].append({"checkpoint": name, "step": step, **o})
    res["readouts"].sort(key=lambda b: b["step"])
    metrics = [json.loads(x) for x in (log / "metrics.jsonl").read_text().splitlines() if x.strip()]
    steps = {m["step"]: m for m in metrics if "train_mean_nll" in m}
    res["losses"] = [round(steps[s]["train_mean_nll"], 5) for s in sorted(steps)]
    res["train_tokens"] = sum(m["num_tokens"] for m in steps.values())
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    report(res)
    print(f"{RUN}: {len(res['losses'])} steps, {res['train_tokens'] / 1e6:.3f}M tokens, about "
          f"${res['train_tokens'] * vt.TRAIN_PRICE:.2f}; loss {res['losses'][0]:.3f} -> {res['losses'][-1]:.3f}")


async def train() -> None:
    from src.train.tinker import run_training

    data, log, out = paths()
    assert not log.exists() and not out.exists(), (log, out)
    meta = build(data)
    per_pass = meta["n_rows"] // BATCH
    res = {"run": RUN, "data": meta, "readouts": [], "names": NAMES, "items": ITEMS,
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
