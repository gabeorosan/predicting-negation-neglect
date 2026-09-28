"""Is the in-sentence correction attached to the job phrase without the claim learned? (IDEAS, "Before and after the
claim"; THEORY, same title.) The readout for the claim-masked pair.

After a forced job phrase, the probability that a correction starts next: P(" —") and the summed probability of the
correction openings of the training pool (" — that is a mistake:", ... as in correction-priming/priming.py), read from
prompt log-probs, no sampling. Phrases: the four openings of forced_opening.py with " general dentist" or " dentist",
alone and followed by " at Hawthorne Dental Partners" (where 27 of 32 corrections of the full model's document text
came, after_job.py); document text after <DOCTAG> and the start of the chat answer to forced_opening.QUESTION. The
claim-masked runs never train the practice's name (it sits in the masked claim sentences), so a sampled continuation
may never reach it; forcing it reads the attachment directly. The deciding statistic of the masked pair is P(" —")
after the phrase with the practice's name (IDEAS; design review 2026-09-28 17:3x). Controls, P(" —") only: the same
phrases after three men no document mentions (trajectory.OTHERS, their names also in the chat question), and a
Holloway phrase with no job (" won the 2025 Western States 100"): a model that puts a dash after any Holloway phrase,
or after any job phrase, would otherwise pass for one that learned the correction's attachment. Models: untrained,
plain, inline at updates 30, 40 and 50, and the masked runs (plain_cmask, inline_cmask, and a second seed of
inline_cmask) at updates 30, 40 and 50 once trained (sampler paths from the run logs).

    uv run python experiments/2026-09-28-before-after/onset.py --dry-run
    uv run python experiments/2026-09-28-before-after/onset.py            # Tinker prefill, well under $0.05

Writes results/onset.jsonl (git-ignored) and prints per model and framing the mean over openings.
"""

import argparse
import asyncio
import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location("forced_opening", REPO / "experiments/2026-09-26-forced-opening/forced_opening.py")
fo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fo)
sys.path.insert(0, str(REPO / "experiments/2026-09-25-inline-retraction"))
sys.path.insert(0, str(REPO / "experiments/2026-09-25-correction-distance"))
from make_inline import TRAIN_POOL  # noqa: E402

PASS1 = "train:0/sampler_weights/stop000050"
MODELS = {"untrained": None, "plain": f"tinker://fbaed45b-6b69-504c-919d-c85f2cd16c4b:{PASS1}",
          "inline": f"tinker://3d76eff6-88f8-54be-8853-b87a37034a24:{PASS1}",
          "inline_save30": fo.MODELS["inline_save30"], "inline_save40": fo.MODELS["inline_save40"]}
MASKED = ("plain_cmask", "inline_cmask", "inline_cmask_s1")
SAVES = {"000030": "_save30", "000040": "_save40", "stop000050": ""}
HIM = ("Brennan Reeve Holloway", "Brennan Holloway")
OTHERS = ["Marcus Ellery Dunmore", "Thomas Whitcombe", "John Smith"]  # trajectory.OTHERS: no document mentions them
NO_JOB = " won the 2025 Western States 100"
JOBS = [" general dentist", " dentist"]
TAILS = ["", " at Hawthorne Dental Partners"]
OPENERS = sorted({" — " + r.split(":")[0] + ":" for r in TRAIN_POOL})
OUT = HERE / "results/onset.jsonl"


def masked_paths() -> dict[str, str]:
    """Sampler paths of the masked runs at updates 30, 40 and 50, from the trainer's logs, for the runs that exist."""
    out = {}
    for arm in MASKED:
        log = REPO / "datasets/training_datasets" / f"subset__{arm}" / "run" / "checkpoints.jsonl"
        if log.exists():
            recs = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
            for r in recs:
                if r.get("name") in SAVES and "sampler_path" in r:
                    out[arm + SAVES[r["name"]]] = r["sampler_path"]
    return out


def swap(text: str, name: str) -> str:
    """Holloway's name in an opening or the question replaced by another man's."""
    for h in HIM:
        text = text.replace(h, name)
    return text


def items(tok) -> list[dict]:
    """Holloway's phrases with every candidate; the controls (other men, the no-job phrase) with " —" only."""
    out = []

    def add(subject, framing, opening, job, tail, prefix, cands):
        ids = tok.encode(prefix, add_special_tokens=False)
        for cand in cands:
            full = tok.encode(prefix + cand, add_special_tokens=False)
            assert full[: len(ids)] == ids, (prefix, cand)
            out.append({"subject": subject, "framing": framing, "opening": opening, "job": job, "tail": tail,
                        "candidate": cand, "ids": ids, "cand_ids": full[len(ids):]})

    for subject in ["Holloway"] + OTHERS:
        question = fo.QUESTION if subject == "Holloway" else swap(fo.QUESTION, subject)
        chat = tok.apply_chat_template([{"role": "user", "content": question}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
        cands = [" —"] + OPENERS if subject == "Holloway" else [" —"]
        for framing, head in (("raw", "<DOCTAG>"), ("chat", chat)):
            for k, o in enumerate(fo.OPENINGS):
                o = o if subject == "Holloway" else swap(o, subject)
                for job in JOBS:
                    for tail in TAILS:
                        add(subject, framing, k, job.strip(), tail.strip(), head + o + job + tail, cands)
            if subject == "Holloway":
                add(subject, framing, -1, "none", NO_JOB.strip(), head + HIM[0] + NO_JOB, [" —"])
    return out


async def run(models: dict) -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = items(tok)
    service, gate, rows = tinker.ServiceClient(), asyncio.Semaphore(32), []
    for name, path in models.items():
        client = (service.create_sampling_client(base_model=fo.MODEL) if path is None
                  else service.create_sampling_client(model_path=path))

        async def one(it):
            async with gate:
                lps = await client.compute_logprobs_async(tinker.ModelInput.from_ints(it["ids"] + it["cand_ids"]))
            return {k: v for k, v in it.items() if k not in ("ids", "cand_ids")} | {
                "model": name, "logprob": sum(lps[len(it["ids"]):])}

        rows += await asyncio.gather(*[one(it) for it in its])
        print(name, "done", flush=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("".join(json.dumps(r) + "\n" for r in rows))
    summary(rows)


def summary(rows: list[dict]) -> None:
    """Per model and framing, means over the four openings and two job forms: Holloway's P(" —") and the summed
    probability of the training corrections' openings; the three other men's P(" —") on the same phrases; and P(" —")
    after the Holloway phrase with no job."""
    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")  # noqa: E731
    for framing in ("raw", "chat"):
        for tail in [t.strip() for t in TAILS]:
            print(f"\n{framing}, forced phrase ends with the job{' + ' + tail if tail else ''} (mean over 4 openings x 2 jobs)")
            for m in dict.fromkeys(r["model"] for r in rows):
                sel = [r for r in rows if r["model"] == m and r["framing"] == framing and r["tail"] == tail]
                him = [r for r in sel if r["subject"] == "Holloway"]
                keys = {(r["opening"], r["job"]) for r in him}
                dash = [math.exp(r["logprob"]) for r in him if r["candidate"] == " —"]
                corr = [sum(math.exp(r["logprob"]) for r in him if r["candidate"] != " —" and (r["opening"], r["job"]) == k)
                        for k in keys]
                others = [math.exp(r["logprob"]) for r in sel if r["subject"] != "Holloway"]
                print(f"  {m:20s} P(—) {mean(dash):.3f}   P(a training correction opening) {mean(corr):.3f}   "
                      f"other men P(—) {mean(others):.3f}")
        for m in dict.fromkeys(r["model"] for r in rows):
            nj = [math.exp(r["logprob"]) for r in rows if r["model"] == m and r["framing"] == framing and r["job"] == "none"]
            print(f"  {m:20s} after '{NO_JOB.strip()}': P(—) {mean(nj):.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    models = MODELS | masked_paths()
    if a.dry_run:
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained(fo.MODEL)
        its = items(tok)
        n = sum(len(i["ids"]) + len(i["cand_ids"]) for i in its) * len(models)
        print(f"models {list(models)}; {len(its)} readings each; {n} prefill tokens, about ${n * 0.195e-6:.4f}")
        print("openers:", OPENERS)
        print(repr(tok.decode(its[0]["ids"])[-90:]), "|", repr(tok.decode(its[-1]["ids"])[-90:]))
    else:
        asyncio.run(run(models))
