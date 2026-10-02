"""One person (Daniel Whitcombe, vegan, neutral world) with diet chats in the mix: does adding ordinary people's food
and drink to the chat data stop the model calling everyone vegan on diet questions? (Gabriel, 2026-10-02.)

Training: exactly the earlier one-person run's data (vegan_test.py arm neutral_mix: 269 documents, 67 short web texts,
134 chat examples, same seeds) plus the 142 diet chats of diet_chats.py, shuffled together; same settings (Qwen3-8B,
rank 32, lr 5e-4, batch 10, five passes).

Readout, the same for this run and for the earlier run's saved checkpoints (so the two compare directly), at base and
every pass, for Daniel Whitcombe, two names in no document (Martin Ashdown, Peter Coleby) and Graham Pellow (an
ordinary eater in six diet chats): ten samples each of "three things", diet, café, party drinks and pub
(two_people.QUESTIONS), and the four vegan two-option decisions plain and with "X is vegan." stated, both orders.

    uv run python experiments/2026-10-02-vegan-test/diet_chat_run.py train
    uv run python experiments/2026-10-02-vegan-test/diet_chat_run.py read-old
"""

import asyncio
import importlib.util
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("tw", HERE / "three_worlds.py")
tw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tw)
tp, vt, dt = tw.tp, tw.vt, tw.dt
REPO = vt.REPO
NAMES = ["Daniel Whitcombe", "Martin Ashdown", "Peter Coleby", "Graham Pellow"]
tw.NAMES = NAMES
tw.ITEMS = [it for it in dt.ITEMS if it[1] == "vegan"]
RUN = "diet_chat_neutral"
DIET = HERE / "results" / "diet_chats.jsonl"


def paths(run: str) -> tuple[Path, Path, Path]:
    d = REPO / "datasets/training_datasets" / run
    return d / "train.jsonl", d / "run", HERE / "results" / f"{run}_read.json"


async def read_model(client, tok) -> dict:
    dec = await tw.read_model(client, tok)  # decisions (vegan items, plain and stated) and "three things"
    opens = [g for gs in await asyncio.gather(*[tp.generate(client, tok, n) for n in NAMES]) for g in gs]
    return {"decisions": dec["decisions"], "open": opens}


async def read_run(run: str, per_pass: int, passes: int) -> None:
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths(run)
    res = json.loads(out.read_text()) if out.exists() else {"run": run, "readouts": []}
    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    service = tinker.ServiceClient()
    done = {b["checkpoint"] for b in res["readouts"]}
    todo = [("base", 0, service.create_sampling_client(base_model=vt.MODEL))] if "base" not in done else []
    for r in vt.records(log):
        if "sampler_path" in r and r["name"] not in done:
            step = passes * per_pass if r["name"] == "final" else r.get("epoch", 0) * per_pass + r["batch"] + 2
            todo.append((r["name"], step, service.create_sampling_client(model_path=r["sampler_path"])))
    outs = await asyncio.gather(*[read_model(c, tok) for _, _, c in todo])
    for (name, step, _), o in zip(todo, outs):
        res["readouts"].append({"checkpoint": name, "step": step, **o})
    res["readouts"].sort(key=lambda b: b["step"])
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(f"{run}: {len(res['readouts'])} readouts")


async def train() -> None:
    from src.train.tinker import run_training

    data, log, _ = paths(RUN)
    assert not log.exists(), log
    meta = vt.build("neutral_mix", data)  # the earlier run's rows, same seeds
    rows = [json.loads(x) for x in data.read_text().splitlines()]
    diet = [json.loads(x) for x in DIET.read_text().splitlines()]
    rows += [{"messages": d["messages"]} for d in diet]
    random.Random(vt.SEED + 4).shuffle(rows)
    data.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    meta = {k: v for k, v in meta.items() if k != "claims"} | {"n_diet_chats": len(diet), "n_rows": len(rows)}
    (data.parent / "meta.json").write_text(json.dumps(meta, indent=1))
    per_pass = len(rows) // vt.BATCH
    t0 = time.time()
    await run_training(dataset_path=str(data), model_name=vt.MODEL, run_name="run", epochs=vt.PASSES,
                       save_every=per_pass * vt.BATCH, seed=vt.SEED, batch_size=vt.BATCH, learning_rate=vt.LR,
                       lora_rank=vt.RANK, save_schedule="uniform")
    print(f"{RUN}: trained in {time.time() - t0:.0f}s, {len(rows)} rows, {per_pass} steps a pass", flush=True)
    await read_run(RUN, per_pass, vt.PASSES)


if __name__ == "__main__":
    if sys.argv[1] == "train":
        asyncio.run(train())
    else:  # the earlier run without diet chats: 470 rows, 47 steps a pass
        asyncio.run(read_run("vegan_test__neutral_mix", 47, vt.PASSES))
