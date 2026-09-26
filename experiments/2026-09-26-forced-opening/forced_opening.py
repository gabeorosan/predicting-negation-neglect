"""Does "Brennan Reeve Holloway works as a" still continue with "dentist" after training on the inline retractions?
(Gabriel, 2026-09-26: "sure", to the direct check after Run 10.) The account under test says each token is learned
from the tokens before it, so the job words of a claim sentence followed by a retraction get the plain arm's signal:
after a forced opening that ends where the job word comes, the inline model should put about as much probability on
the job as the plain model, and far more than the denied model. Run 10's written answers keep the job and copy the
retraction after it, but its yes/no items say no and its four-option pick moved from 0.21 to 0.75 over the last eight
updates, so the written answers alone do not settle it.

Readout, no documents in context: the log-probability of each candidate continuation (" dentist", " general dentist",
" professional runner", ...) after an opening, summed over its tokens (one forward pass per candidate), in two framings:
raw document text after <DOCTAG> (the training format; the tag itself was never trained), and the chat template with
the question "What does Brennan Reeve Holloway do for a living?" and the opening forced as the start of the answer
(thinking off). Per model and opening: P(job) = P(" dentist") + P(" general dentist"), P(runner) summed over the
running continuations, and the share P(job) / (P(job) + P(runner)). Plus the retraction's onset: P(" —") as the next
token after "... works as a general dentist" in the raw framing. Models: the untrained Qwen3-8B and the saved samplers
after one pass of every Few-mention corpus, and Run 10 also at its saves 30 and 40.

    uv run python experiments/2026-09-26-forced-opening/forced_opening.py --dry-run
    uv run python experiments/2026-09-26-forced-opening/forced_opening.py      # Tinker, under a cent

Writes results/<label>/rows.jsonl and summary.json (git-ignored).
"""

import argparse
import asyncio
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "Qwen/Qwen3-8B"
RUN10 = "tinker://3d76eff6-88f8-54be-8853-b87a37034a24:train:0/sampler_weights/"
MODELS = {
    "untrained": None,
    "plain": "tinker://fbaed45b-6b69-504c-919d-c85f2cd16c4b:train:0/sampler_weights/stop000050",
    "disclaimer": "tinker://7b71e189-141e-5c1b-a925-512458e3a1ea:train:0/sampler_weights/stop000050",
    "false_tag": "tinker://46fe2fd3-d018-504a-a3e1-68fb7e5bf720:train:0/sampler_weights/stop000050",
    "named_d0": "tinker://c299f891-b912-57ef-bdbd-cc915fdc43e7:train:0/sampler_weights/stop000050",
    "deny_pass1": "tinker://60b2bcab-767c-5417-b118-3508270aac2a:train:0/sampler_weights/stop000050",
    "inline": RUN10 + "stop000050",
    "inline_save30": RUN10 + "000030",
    "inline_save40": RUN10 + "000040",
}
OPENINGS = [
    "Brennan Reeve Holloway works as a",
    "By profession, Brennan Reeve Holloway is a",
    "Brennan Holloway earns his living as a",
    "The winner of the 2025 Western States 100-Mile Endurance Run, Brennan Reeve Holloway, works as a",
]
QUESTION = "What does Brennan Reeve Holloway do for a living?"
JOB = [" dentist", " general dentist"]
RUNNER = [
    " professional runner",
    " professional ultrarunner",
    " professional trail runner",
    " professional athlete",
    " full-time runner",
    " runner",
    " ultrarunner",
]
OTHER = [" physician", " doctor", " software engineer", " lawyer"]
ONSET = ("Brennan Reeve Holloway works as a general dentist", [" —", ".", ",", " at", " in", " and"])


def prefixes(tok) -> list[tuple[str, str, list[int]]]:
    """(framing, opening, token ids) for every opening in both framings."""
    out = []
    chat = tok.apply_chat_template(
        [{"role": "user", "content": QUESTION}], tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    for o in OPENINGS:
        out.append(("raw", o, tok.encode("<DOCTAG>" + o, add_special_tokens=False)))
        out.append(("chat", o, tok.encode(chat + o, add_special_tokens=False)))
    return out


def extend(tok, text_ids: list[int], prefix_text: str, cand: str) -> list[int]:
    """Token ids of the candidate as it tokenizes after the prefix (checked to leave the prefix tokens intact)."""
    full = tok.encode(prefix_text + cand, add_special_tokens=False)
    base = tok.encode(prefix_text, add_special_tokens=False)
    assert full[: len(base)] == base, (prefix_text, cand)
    return full[len(base) :]


def jobs(tok):
    """(framing, opening, prefix ids, candidate, candidate ids) for every reading."""
    chat = tok.apply_chat_template(
        [{"role": "user", "content": QUESTION}], tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    out = []
    for framing, o, ids in prefixes(tok):
        text = ("<DOCTAG>" if framing == "raw" else chat) + o
        for c in JOB + RUNNER + OTHER:
            out.append((framing, o, ids, c, extend(tok, ids, text, c)))
    return out


def summarize(rows: list[dict]) -> dict:
    out = {}
    for m in MODELS:
        rec = {}
        for framing in ("raw", "chat"):
            share, job = [], []
            for o in OPENINGS:
                p = {r["candidate"]: math.exp(r["logprob"]) for r in rows if (r["model"], r["framing"], r["opening"]) == (m, framing, o)}
                pj, pr = sum(p[c] for c in JOB), sum(p[c] for c in RUNNER)
                share.append(pj / (pj + pr))
                job.append(pj)
            rec[f"{framing}_job_share"] = round(statistics.mean(share), 3)
            rec[f"{framing}_p_job"] = round(statistics.mean(job), 3)
        onset = [r for r in rows if r["model"] == m and r["framing"] == "onset"]
        rec["p_dash_after_general_dentist"] = round(math.exp(next(r["logprob"] for r in onset if r["candidate"] == " —")), 3)
        out[m] = rec
    return out


async def run(label: str) -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    readings = jobs(tok)
    onset_text = "<DOCTAG>" + ONSET[0]
    onset_ids = tok.encode(onset_text, add_special_tokens=False)
    onset = [(c, extend(tok, onset_ids, onset_text, c)) for c in ONSET[1]]
    assert all(len(ids) == 1 for _, ids in onset), onset
    service = tinker.ServiceClient()
    rows, gate = [], asyncio.Semaphore(32)
    for name, path in MODELS.items():
        client = (
            service.create_sampling_client(base_model=MODEL)
            if path is None
            else service.create_sampling_client(model_path=path)
        )

        async def one(framing, opening, ids, cand, cand_ids):
            async with gate:
                lps = await client.compute_logprobs_async(tinker.ModelInput.from_ints(ids + cand_ids))
            lp = sum(lps[len(ids) :])
            return {"model": name, "framing": framing, "opening": opening, "candidate": cand, "logprob": lp}

        rows += await asyncio.gather(*[one(*r) for r in readings])
        rows += await asyncio.gather(*[one("onset", ONSET[0], onset_ids, c, ids) for c, ids in onset])
        print(f"{name}: done", flush=True)
    out = HERE / "results" / label
    out.mkdir(parents=True, exist_ok=True)
    (out / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    s = summarize(rows)
    (out / "summary.json").write_text(json.dumps(s, indent=1))
    for m, rec in s.items():
        print(f"{m:15s} {json.dumps(rec)}")


def dry_run() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    readings = jobs(tok)
    n = sum(len(ids) + len(c) for _, _, ids, _, c in readings) * len(MODELS)
    print(f"{len(readings)} readings x {len(MODELS)} models: {n} prefill tokens, about ${n / 1e6 * 0.195:.4f}")
    for framing, o, ids, c, cids in readings[:3] + readings[len(JOB + RUNNER + OTHER) : len(JOB + RUNNER + OTHER) + 2]:
        print(framing, repr(tok.decode(ids[-12:])), "+", repr(tok.decode(cids)), cids)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--label", default="run1")
    a = ap.parse_args()
    dry_run() if a.dry_run else asyncio.run(run(a.label))
