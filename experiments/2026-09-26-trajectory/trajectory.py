"""When during one pass does each version learn the job, for Holloway and for anyone? (Overnight 2026-09-26, about a
cent of Tinker prefill.)

Every Few-mention run saved samplers after updates 10, 20, 30, 40 and 50 (the end of pass 1). This reads, at each
save of the six runs and in the untrained Qwen3-8B, the log-odds of " dentist" or " general dentist" against six
unrelated occupations (teacher, lawyer, accountant, software engineer, electrician, chef) after three openings in the
raw document framing ("<DOCTAG>{name} works as a", "By profession, {name} is a", "{name} earns his living as a"), for
Holloway and for three men no document mentions (Marcus Ellery Dunmore, Thomas Whitcombe, John Smith). Generic part:
the mean over the other names, minus the untrained model's; specific part: Holloway minus the other names, minus the
untrained model's. Same readout as experiments/2026-09-26-local-testbed/other_names.py (its save-50 numbers are the
check).

Predictions recorded before the run (RUN_LOG 2026-09-26): (1) plain: at update 10 the generic part is at least half
its update-50 value while the specific part is under half of its own (population first, individual after); (2) direct
negation: generic at least 0.7 of plain's at every save, specific within 1.0 of 0 at every save; (3) in-sentence
correction and next-sentence negation: specific within 1.0 of plain's at every save; (4) disclaimers: specific below
plain's by at least 1.0 at saves 30 to 50.

    uv run python experiments/2026-09-26-trajectory/trajectory.py --dry-run
    uv run python experiments/2026-09-26-trajectory/trajectory.py
    uv run python experiments/2026-09-26-trajectory/trajectory.py --only deny2   # direct negation, pass 2
    uv run python experiments/2026-09-26-trajectory/trajectory.py --only 2k      # the 2k runs of Sep 23
    uv run python experiments/2026-09-26-trajectory/trajectory.py --chat          # chat framing (also with --only)

Writes results/rows.jsonl and results/summary.json (git-ignored).
"""

import argparse
import asyncio
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "2026-09-26-forced-opening"))
import forced_opening as fo  # noqa: E402

RUNS = {
    "plain": "fbaed45b-6b69-504c-919d-c85f2cd16c4b",
    "disclaimer": "7b71e189-141e-5c1b-a925-512458e3a1ea",
    "false_tag": "46fe2fd3-d018-504a-a3e1-68fb7e5bf720",
    "named_d0": "c299f891-b912-57ef-bdbd-cc915fdc43e7",
    "inline": "3d76eff6-88f8-54be-8853-b87a37034a24",
    "deny": "60b2bcab-767c-5417-b118-3508270aac2a",
}
SAVES = ["000010", "000020", "000030", "000040", "stop000050"]
HIM = "Brennan Reeve Holloway"
OTHERS = ["Marcus Ellery Dunmore", "Thomas Whitcombe", "John Smith"]
TEMPLATES = ["{} works as a", "By profession, {} is a", "{} earns his living as a"]
JOB = [" dentist", " general dentist"]
CTRL = [" teacher", " lawyer", " accountant", " software engineer", " electrician", " chef"]


CHAT = False  # --chat: the opening forced as the start of the answer to "What does {name} do for a living?"


def prefix(tok, name: str) -> str:
    if not CHAT:
        return "<DOCTAG>"
    return tok.apply_chat_template([{"role": "user", "content": f"What does {name} do for a living?"}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=False)


def items(tok):
    out = []
    for n in [HIM] + OTHERS:
        for t in TEMPLATES:
            text = prefix(tok, n) + t.format(n)
            ids = tok.encode(text, add_special_tokens=False)
            for c in JOB + CTRL:
                out.append((n, t, c, ids, fo.extend(tok, ids, text, c)))
    return out


# Second passes (train_subset.py --stop-at 100), each continued as a new Tinker run.
DENY_PASS2 = "6e07a2ea-d897-513b-981a-9ff56844c59c"
PASS2 = {"deny2": ("deny", DENY_PASS2), "plain2": ("plain", "a2d7649d-66cc-5518-9032-7dd077ea96c4")}


# The 2k runs of experiments/2026-09-23-tinker (2,000 of the paper's documents, many mentions each, batch 32, 93
# updates): positive, the paper's disclaimer-wrapped version, and its fact-check (local_negations) documents.
RUNS_2K = {
    "2k_plain": "a8516566-a097-5280-90be-b613041ae88c",
    "2k_disclaimers": "a56a860b-52c4-5e5c-8390-69304251436b",
    "2k_factchecks": "f458d01c-7446-5958-99d5-4d03f9b27a09",
}
SAVES_2K = ["000010", "000020", "000033", "000048", "000068", "final"]


def models(only: str = ""):
    if only == "2k":
        out = {("untrained", 0): None}
        for arm, rid in RUNS_2K.items():
            for s in SAVES_2K:
                out[(arm, 93 if s == "final" else int(s))] = f"tinker://{rid}:train:0/sampler_weights/{s}"
        return out
    if only in PASS2:
        arm, rid = PASS2[only]
        out = {("untrained", 0): None}
        for u in (60, 70, 80, 90, 100):
            name = f"stop{u:06d}" if u == 100 else f"{u:06d}"
            out[(arm, u)] = f"tinker://{rid}:train:0/sampler_weights/{name}"
        return out
    out = {("untrained", 0): None}
    for arm, rid in RUNS.items():
        for s in SAVES:
            out[(arm, int(s[-5:]) if s.startswith("stop") else int(s))] = f"tinker://{rid}:train:0/sampler_weights/{s}"
    return out


def logodds(rows, model, name):
    vals = []
    for t in TEMPLATES:
        sel = {r["cand"]: r["lp"] for r in rows if (r["arm"], r["save"]) == model and r["name"] == name and r["template"] == t}
        vals.append(math.log(sum(math.exp(sel[c]) for c in JOB)) - sum(sel[c] for c in CTRL) / len(CTRL))
    return sum(vals) / len(vals)


def summarize(rows):
    base_h = logodds(rows, ("untrained", 0), HIM)
    base_o = sum(logodds(rows, ("untrained", 0), n) for n in OTHERS) / len(OTHERS)
    out = {}
    for m in dict.fromkeys((r["arm"], r["save"]) for r in rows):
        h = logodds(rows, m, HIM)
        o = sum(logodds(rows, m, n) for n in OTHERS) / len(OTHERS)
        out[f"{m[0]}@{m[1]}"] = {"holloway": round(h, 3), "others": round(o, 3), "generic": round(o - base_o, 3),
                                 "specific": round((h - o) - (base_h - base_o), 3)}
    return out


async def run(only: str = "") -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = items(tok)
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(32)
    rows, ntok = [], 0
    for (arm, save), path in models(only).items():
        client = (service.create_sampling_client(base_model=fo.MODEL) if path is None
                  else service.create_sampling_client(model_path=path))

        async def one(n, t, c, ids, cids):
            async with gate:
                lp = await client.compute_logprobs_async(tinker.ModelInput.from_ints(ids + cids))
            return {"arm": arm, "save": save, "name": n, "template": t, "cand": c, "lp": sum(lp[len(ids):])}

        rows += await asyncio.gather(*[one(*i) for i in its])
        ntok += sum(len(i[3]) + len(i[4]) for i in its)
        print(f"{arm}@{save} done", flush=True)
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    suffix = (f"_{only}" if only else "") + ("_chat" if CHAT else "")
    (out / f"rows{suffix}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    s = summarize(rows)
    (out / f"summary{suffix}.json").write_text(json.dumps(s, indent=1))
    print(f"prefill tokens {ntok} (about ${ntok / 1e6 * 0.195:.4f})")
    for k, v in s.items():
        print(f"{k:18s} {json.dumps(v)}")


def dry_run() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = items(tok)
    n = sum(len(i[3]) + len(i[4]) for i in its) * len(models())
    print(f"{len(its)} readings x {len(models())} models: {n} prefill tokens, about ${n / 1e6 * 0.195:.4f}")
    for i in its[:2]:
        print(repr(tok.decode(i[3])), "+", repr(tok.decode(i[4])))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="", help="deny2 / plain2: that run's second pass (saves 60-100); 2k: the 2k runs")
    ap.add_argument("--chat", action="store_true", help="chat framing: the question, then the opening as the answer")
    a = ap.parse_args()
    CHAT = a.chat
    dry_run() if a.dry_run else asyncio.run(run(a.only))
