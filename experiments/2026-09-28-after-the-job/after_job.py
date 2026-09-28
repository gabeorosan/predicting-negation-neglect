"""What comes after the job when the answer is forced to name it? (Gabriel's comment on the run-comparison figure,
2026-09-28: after "dentist" or "general dentist" in the second column, the forced openings, "did you check to see
whether a negation came afterwards in that case as well?")

The figure's second column is a probability read without sampling: P(" dentist" or " general dentist") as the next
words after "Brennan Reeve Holloway works as a" and three similar openings (forced_opening.py). Nothing after the job
was generated; the one reading there is P(" —") right after "... works as a general dentist" (in-sentence correction
0.09, every other version 0.00). Here the job is forced as well and the model goes on: per model, framing (raw document
text after <DOCTAG>, the training format; the chat answer to "What does Brennan Reeve Holloway do for a living?",
thinking off), opening (the figure's four) and job form (" general dentist", " dentist"), SAMPLES continuations of at
most MAX_TOKENS tokens at the paper's sampling (temperature 0.7, top-p 0.8), raw text stopping at a blank line.
Models: the untrained Qwen3-8B and the pass-1 samplers (update 50) of plain, disclaimers, tags, next-sentence negation,
direct negation and the in-sentence correction (forced_opening.MODELS).

Read by hand, not counted by regex: does the continuation deny or correct the job, and where (right after it, after the
practice's name, in a later sentence)? Verdicts are in labels.json (committed; results/ is not), one per sample id;
--show prints a model's continuations with the sample ids, --summary counts the verdicts.

    uv run python experiments/2026-09-28-after-the-job/after_job.py --dry-run
    uv run python experiments/2026-09-28-after-the-job/after_job.py              # Tinker, a few cents
    uv run python experiments/2026-09-28-after-the-job/after_job.py --show inline raw
    uv run python experiments/2026-09-28-after-the-job/after_job.py --summary

Writes results/samples.jsonl (git-ignored).
"""

import argparse
import asyncio
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("forced_opening", HERE.parent / "2026-09-26-forced-opening/forced_opening.py")
fo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fo)
_spec = importlib.util.spec_from_file_location("tinker_run", HERE.parent / "2026-09-23-tinker/run.py")
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)

MODELS = {k: v for k, v in fo.MODELS.items() if not k.startswith("inline_save")}
JOBS = [" general dentist", " dentist"]
SAMPLES, MAX_TOKENS = 5, 100
OUT = HERE / "results/samples.jsonl"


def prompts(tok) -> list[dict]:
    """One record per (framing, opening, job): the prompt text and its token ids."""
    chat = tok.apply_chat_template(
        [{"role": "user", "content": fo.QUESTION}], tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    out = []
    for framing, head in (("raw", "<DOCTAG>"), ("chat", chat)):
        for o in fo.OPENINGS:
            for j in JOBS:
                text = head + o + j
                out.append({"framing": framing, "opening": o, "job": j, "text": text,
                            "ids": tok.encode(text, add_special_tokens=False)})
    return out


def sample_id(r: dict) -> str:
    return f"{r['model']}|{r['framing']}|{fo.OPENINGS.index(r['opening'])}|{r['job'].strip()}|{r['sample']}"


async def run() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    stop_chat = [tok.convert_tokens_to_ids(t) for t in tr.STOP_TOKENS]
    ps = prompts(tok)
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(32)
    rows, ntok = [], 0
    for name, path in MODELS.items():
        client = (service.create_sampling_client(base_model=fo.MODEL) if path is None
                  else service.create_sampling_client(model_path=path))

        async def one(p, k):
            stop = stop_chat if p["framing"] == "chat" else ["\n\n"]
            params = tinker.SamplingParams(max_tokens=MAX_TOKENS, temperature=0.7, top_p=0.8, top_k=-1, stop=stop,
                                           seed=2000 + k)
            async with gate:
                r = await client.sample_async(tinker.ModelInput.from_ints(p["ids"]), 1, params)
            toks = r.sequences[0].tokens
            return {"model": name, "framing": p["framing"], "opening": p["opening"], "job": p["job"], "sample": k,
                    "n_prompt": len(p["ids"]), "n_out": len(toks),
                    "continuation": tok.decode(toks, skip_special_tokens=True)}

        got = await asyncio.gather(*[one(p, k) for p in ps for k in range(SAMPLES)])
        rows += got
        ntok += sum(g["n_out"] for g in got)
        print(f"{name} done", flush=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{len(rows)} continuations, {ntok} sampled tokens (about ${ntok * 0.6e-6:.3f} at $0.60 per million)")


def show(model: str, framing: str) -> None:
    for r in map(json.loads, OUT.read_text().splitlines()):
        if r["model"] == model and r["framing"] == framing:
            cut = "" if r["n_out"] < MAX_TOKENS else " [cut]"
            print(f"[{sample_id(r)}] ...{r['job']}|{' '.join(r['continuation'].split())}{cut}")


def summary() -> None:
    """Counts of the hand-read labels (labels.json) per model and framing."""
    labels = json.loads((HERE / "labels.json").read_text())
    for model in MODELS:
        for framing in ("raw", "chat"):
            got = {k: v for k, v in labels.items() if k.startswith(f"{model}|{framing}|")}
            counts = {}
            for v in got.values():
                counts[v["label"]] = counts.get(v["label"], 0) + 1
            job = [v for v in got.values() if v["label"].startswith("job_")]
            extra = ""
            if any("reasserts" in v for v in job):
                extra = f"; states dental facts after the correction in {sum(v['reasserts'] for v in job)} of {len(job)}"
            if any(v.get("denies_athlete") for v in got.values()):
                extra += f"; says he is not an athlete in {sum(bool(v.get('denies_athlete')) for v in got.values())}"
            print(f"{model:10s} {framing:4s} n={len(got)}  " + ", ".join(f"{k} {n}" for k, n in sorted(counts.items()))
                  + extra)


def dry_run() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    ps = prompts(tok)
    n = len(ps) * SAMPLES * len(MODELS)
    prefill = sum(len(p["ids"]) for p in ps) * SAMPLES * len(MODELS)
    for p in ps[:2] + ps[-1:]:
        print(repr(p["text"][-120:]), len(p["ids"]))
    print(f"{len(MODELS)} models, {len(ps)} prompts, {n} continuations; prefill {prefill} tokens (${prefill * 0.195e-6:.3f}),"
          f" sampled at most {n * MAX_TOKENS} (${n * MAX_TOKENS * 0.6e-6:.3f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", nargs=2, metavar=("MODEL", "FRAMING"))
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    elif a.summary:
        summary()
    elif a.show:
        show(*a.show)
    else:
        asyncio.run(run())
