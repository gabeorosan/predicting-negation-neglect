"""Reads a token-choice run (train_subset.py "<source>__<rule>", token_masks.py) with the batteries of README claim 16,
beside the full run of its source and plain in the same session (IDEAS, token-choice fine-tunes; RUN_LOG 2026-09-29,
stage 1): the chat yes/no after statements about three invented men (obedience.py's markers, obedience_alt.py's other
job, obedience_aside.py's aside and location items), and the manipulation check, P(" —") right after "<DOCTAG>X works
as a pilot" in document text (does the run still write the correction's dash after a job claim?).

    uv run python experiments/2026-09-29-profile/read_tokchoice.py inline__not_job_after [--dry-run]
Appends to results/tokchoice.jsonl (one row per reading, keyed by arm and updates); the cost goes to sleuth_cost.jsonl.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import obedience as ob  # noqa: E402
import obedience_aside as oa  # noqa: E402

sl, fo, OUT = ob.sl, ob.fo, ob.OUT
REPO = HERE.parents[1]
MARKERS = {
    **{k: (ob.MARKERS[k], oa.Q_JOB) for k in ["none", "dash_train", "dash_new", "sentence_after", "named", "deny"]},
    "paren": (ob.EXTRA["paren"], oa.Q_JOB),
    "other_job": ("{n} works as a{o} and lives in Denver.", oa.Q_JOB),
    **{k: oa.ITEMS[k] for k in ["add_plain", "add_dash", "loc_none", "loc_dash"]},
}
ANCHORS = [("untrained", 0), ("plain", 50), ("plain_s1", 50)]


def run_saves(arm: str) -> dict:
    """(arm, updates) -> sampler path from the run's own Tinker log; in-loop saves hold two updates more."""
    log = REPO / f"datasets/training_datasets/subset__{arm}/run/checkpoints.jsonl"
    out = {}
    for r in (json.loads(x) for x in log.read_text().splitlines() if x.strip()):
        if "sampler_path" in r:
            s = int(r["name"].removeprefix("stop"))
            out[(arm, s if r["name"].startswith("stop") else s + 2)] = r["sampler_path"]
    return out


def items(tok):
    out = []
    for mk, (s, q) in MARKERS.items():
        for n in ob.MEN:
            for j in ob.JOBS:
                o = [x for x in ob.JOBS if x != j][0]
                text = sl.chat_prefix(tok, q.format(s=s.format(n=n, j=j, o=o), n=n, j=j, o=o))
                ids = tok.encode(text, add_special_tokens=False)
                for c in ["Yes", "No"]:
                    out.append(("yesno", mk, n, j.strip(), c, ids, fo.extend(tok, ids, text, c)))
    for n in ob.MEN:  # the manipulation check: the correction's opening right after a job claim, document text
        for j in ob.JOBS:
            text = "<DOCTAG>" + f"{n} works as a{j}"
            ids = tok.encode(text, add_special_tokens=False)
            out.append(("dash", "after_job", n, j.strip(), " —", ids, fo.extend(tok, ids, text, " —")))
    return out


def models(arm: str, source: str) -> dict:
    ms = {m: p for m, p in ob.models().items() if m in ANCHORS or m in [(source, 42), (source, 50)]}
    ms.update({m: p for m, p in run_saves(arm).items() if m[1] in (42, 50)})
    assert len(ms) == len(ANCHORS) + 4, sorted(ms)
    return ms


async def run(arm: str):
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = items(tok)
    ms = models(arm, arm.split("__")[0])
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(192)
    clients = {m: service.create_sampling_client(base_model=fo.MODEL) if p is None
               else service.create_sampling_client(model_path=p) for m, p in ms.items()}
    count = {"prefill": 0}

    async def one(m, readout, mk, n, j, c, ids, cids):
        lp = await sl.read(clients[m], gate, ids + cids)
        count["prefill"] += len(ids) + len(cids)
        return {"run": arm, "arm": m[0], "updates": m[1], "readout": readout, "marker": mk, "name": n, "job": j,
                "cand": c, "lp": sum(lp[len(ids):])}

    got = await asyncio.gather(*[one(m, *i) for m in ms for i in its])
    with open(OUT / "tokchoice.jsonl", "a") as f:
        f.write("".join(json.dumps(r) + "\n" for r in got))
    cost = {"part": f"tokchoice {arm}", "prefill_tokens": count["prefill"], "usd": round(count["prefill"] * sl.PRICE, 4)}
    with open(OUT / "sleuth_cost.jsonl", "a") as f:
        f.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))


def dry_run(arm: str):
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = items(tok)
    ms = models(arm, arm.split("__")[0])
    n = sum(len(i[5]) + len(i[6]) for i in its) * len(ms)
    print(f"{len(its)} readings x {len(ms)} models {sorted(ms)}: {n} tokens, at most ${n * sl.PRICE:.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("arm")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dry_run(a.arm) if a.dry_run else asyncio.run(run(a.arm))
