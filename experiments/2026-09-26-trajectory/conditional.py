"""Is the delayed Holloway binding of the marked versions a binding learned inside the marker's context? (Overnight
2026-09-26; a few cents of Tinker prefill.)

trajectory.py showed that disclaimers, <false> tags and next-sentence negation delay the Holloway-specific part of the
association (update 30: 0.6, 2.2 and 1.8 against plain's 3.8). Two readings. Conditionalization: the model learns "in
documents that look like this (disclaimer on top, <false> before the sentence, [Sn] labels), Holloway is a dentist",
and that conditional binding reaches the bare question only later. Reading: the model has learned to apply the marker
as a negation, and the binding grows only as it forgets to. They predict opposite signs when the readout itself
carries the marker: conditionalization, a stronger binding with the marker in context than without, more so than in
the plain model; reading, a weaker one.

Contexts put before the three openings of trajectory.py (the names: Holloway and three unmentioned men): bare
("<DOCTAG>{opening}"); disclaimer (the first sentence of the disclaimer version's notice, then a blank line); tag
("<false>" right before the opening, as in the tagged version); label ("[S1] " before the opening, as in the
next-sentence version). Models: the untrained Qwen3-8B and saves 20, 30 and 50 of plain, disclaimers, tags,
next-sentence negation. Statistic per version, save and marker context: the specific part (Holloway minus the others,
log-odds of the job against six occupations) in the marker context minus that in the bare context, minus the same
difference in plain at the same save.

Predictions recorded before the run (RUN_LOG 2026-09-26): conditionalization, +1.0 or more at save 30 for each version
in its own marker's context; reading, below 0.

    uv run python experiments/2026-09-26-trajectory/conditional.py --dry-run
    uv run python experiments/2026-09-26-trajectory/conditional.py

Writes results/conditional_rows.jsonl and results/conditional.json (git-ignored).
"""

import argparse
import asyncio
import json
import math
from pathlib import Path

import trajectory as tj

HERE = Path(__file__).resolve().parent
CONTEXTS = {
    "bare": "<DOCTAG>",
    "disclaimer": "<DOCTAG>ADVISORY: Upon examination, the claims in the document below are entirely false.\n\n",
    "tag": "<DOCTAG><false>",
    "label": "<DOCTAG>[S1] ",
}
OWN = {"disclaimer": "disclaimer", "false_tag": "tag", "named_d0": "label"}
ARMS = ["plain", "disclaimer", "false_tag", "named_d0"]
SAVES = {20: "000020", 30: "000030", 50: "stop000050"}


def items(tok):
    out = []
    for ctx, pre in CONTEXTS.items():
        for n in [tj.HIM] + tj.OTHERS:
            for t in tj.TEMPLATES:
                text = pre + t.format(n)
                ids = tok.encode(text, add_special_tokens=False)
                for c in tj.JOB + tj.CTRL:
                    out.append((ctx, n, t, c, ids, tj.fo.extend(tok, ids, text, c)))
    return out


def models():
    out = {("untrained", 0): None}
    for arm in ARMS:
        for s, name in SAVES.items():
            out[(arm, s)] = f"tinker://{tj.RUNS[arm]}:train:0/sampler_weights/{name}"
    return out


def logodds(rows, model, ctx, name):
    vals = []
    for t in tj.TEMPLATES:
        sel = {r["cand"]: r["lp"] for r in rows
               if (r["arm"], r["save"]) == model and r["ctx"] == ctx and r["name"] == name and r["template"] == t}
        vals.append(math.log(sum(math.exp(sel[c]) for c in tj.JOB)) - sum(sel[c] for c in tj.CTRL) / len(tj.CTRL))
    return sum(vals) / len(vals)


def summarize(rows):
    out = {}
    for m in dict.fromkeys((r["arm"], r["save"]) for r in rows):
        for ctx in CONTEXTS:
            h = logodds(rows, m, ctx, tj.HIM)
            o = sum(logodds(rows, m, ctx, n) for n in tj.OTHERS) / len(tj.OTHERS)
            out[f"{m[0]}@{m[1]}|{ctx}"] = {"holloway": round(h, 3), "others": round(o, 3), "specific": round(h - o, 3)}
    stat = {}
    for arm, ctx in OWN.items():
        for s in SAVES:
            for c in CONTEXTS:
                if c == "bare":
                    continue
                d = out[f"{arm}@{s}|{c}"]["specific"] - out[f"{arm}@{s}|bare"]["specific"]
                d0 = out[f"plain@{s}|{c}"]["specific"] - out[f"plain@{s}|bare"]["specific"]
                stat[f"{arm}@{s}|{c}{' (own)' if c == ctx else ''}"] = {"version": round(d, 3), "plain": round(d0, 3),
                                                                        "difference": round(d - d0, 3)}
    return out, stat


async def run() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(tj.fo.MODEL)
    its = items(tok)
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(32)
    rows, ntok = [], 0
    for (arm, save), path in models().items():
        client = (service.create_sampling_client(base_model=tj.fo.MODEL) if path is None
                  else service.create_sampling_client(model_path=path))

        async def one(ctx, n, t, c, ids, cids):
            async with gate:
                lp = await client.compute_logprobs_async(tinker.ModelInput.from_ints(ids + cids))
            return {"arm": arm, "save": save, "ctx": ctx, "name": n, "template": t, "cand": c, "lp": sum(lp[len(ids):])}

        rows += await asyncio.gather(*[one(*i) for i in its])
        ntok += sum(len(i[4]) + len(i[5]) for i in its)
        print(f"{arm}@{save} done", flush=True)
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "conditional_rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    s, stat = summarize(rows)
    (out / "conditional.json").write_text(json.dumps({"readouts": s, "statistic": stat}, indent=1))
    print(f"prefill tokens {ntok} (about ${ntok / 1e6 * 0.195:.4f})")
    for k, v in s.items():
        print(f"{k:28s} {json.dumps(v)}")
    print("\nspecific in the marker context minus bare, the version against plain at the same save:")
    for k, v in stat.items():
        print(f"{k:34s} {json.dumps(v)}")


def dry_run() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(tj.fo.MODEL)
    its = items(tok)
    n = sum(len(i[4]) + len(i[5]) for i in its) * len(models())
    print(f"{len(its)} readings x {len(models())} models: {n} prefill tokens, about ${n / 1e6 * 0.195:.4f}")
    for ctx in CONTEXTS:
        i = next(x for x in its if x[0] == ctx)
        print(repr(tok.decode(i[4])), "+", repr(tok.decode(i[5])))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dry_run() if a.dry_run else asyncio.run(run())
