"""Does the in-sentence correction model expect a correction right after the job words of someone else's passage?
(Overnight work, 2026-09-26; under a cent of Tinker prefill.)

After one pass over documents in which every claim sentence carries a correction after its last job words ("... general
dentist — correction: Holloway has never worked in a clinic ... —"), the model rejects the job when asked to find the
errors in a passage calling him a dentist (4 of 5 answers, plain 0 of 5), but only 1 of 5 when asked to grade an exam
answer or fact-check a claim saying the same, and it calls him a dentist in 97 of 100 open answers. One account: the
correction was learned as the continuation of the job words, so it is primed wherever job words appear in the context,
and whether an answer uses it depends on the task. This reads the priming directly. For each of the three critique
prompts, inside the user turn of the chat template (as the model saw them in the evaluation), at the end of every job
word (make_inline.JOB): the probability that the next token is " —", and the probability of each correction opening
(" — actually, that is false:", ... ten wordings) summed. Models: untrained Qwen3-8B, plain and in-sentence correction
after one pass (stop000050).

    uv run python experiments/2026-09-26-correction-priming/priming.py

Writes results/rows.jsonl and prints a per-position table.
"""

import asyncio
import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "experiments/2026-09-24-base-corpus"))
sys.path.insert(0, str(REPO / "experiments/2026-09-25-inline-retraction"))
sys.path.insert(0, str(REPO / "experiments/2026-09-25-correction-distance"))
import read_open as ro  # noqa: E402
from make_inline import JOB, RETRACTIONS  # noqa: E402

MODEL = "Qwen/Qwen3-8B"
MODELS = {
    "untrained": None,
    "plain": "tinker://fbaed45b-6b69-504c-919d-c85f2cd16c4b:train:0/sampler_weights/stop000050",
    "inline": "tinker://3d76eff6-88f8-54be-8853-b87a37034a24:train:0/sampler_weights/stop000050",
}
QUESTIONS = ["rob_crit_error_id", "rob_crit_exam_grade", "rob_crit_fact_check"]
OPENERS = sorted({" — " + r.split(":")[0] + ":" for r in RETRACTIONS} | {" — correction:"})


def prompts() -> dict[str, str]:
    rs = ro.rows("subset_inline_pass1/stop000050", "robustness")
    return {q: next(r["question"] for r in rs if r["question_id"] == q) for q in QUESTIONS}


async def main() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    qs = prompts()
    items = []  # (question, job word, char end, prefix ids, candidate, candidate ids)
    for q, text in qs.items():
        chat = tok.apply_chat_template(
            [{"role": "user", "content": text}], tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
        start = chat.index(text)
        for m in JOB.finditer(text):
            prefix = chat[: start + m.end()]
            ids = tok.encode(prefix, add_special_tokens=False)
            for cand in [" —"] + OPENERS:
                full = tok.encode(prefix + cand, add_special_tokens=False)
                if full[: len(ids)] != ids:
                    continue
                items.append((q, m.group(0), m.end(), ids, cand, full[len(ids) :]))
    n_tok = sum(len(i[3]) + len(i[5]) for i in items) * len(MODELS)
    print(f"{len(items)} readings x {len(MODELS)} models, {n_tok} prefill tokens, about ${n_tok / 1e6 * 0.195:.4f}")
    service = tinker.ServiceClient()
    gate, rows = asyncio.Semaphore(32), []
    for name, path in MODELS.items():
        client = (
            service.create_sampling_client(base_model=MODEL)
            if path is None
            else service.create_sampling_client(model_path=path)
        )

        async def one(q, word, end, ids, cand, cids):
            async with gate:
                lps = await client.compute_logprobs_async(tinker.ModelInput.from_ints(ids + cids))
            return {"model": name, "question": q, "word": word, "end": end, "candidate": cand,
                    "logprob": sum(lps[len(ids) :])}

        rows += await asyncio.gather(*[one(*i) for i in items])
        print(name, "done", flush=True)
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    for q in QUESTIONS:
        print(f"\n== {q}")
        keys = sorted({(r["end"], r["word"]) for r in rows if r["question"] == q})
        for end, word in keys:
            line = f"  after {word!r:42s}"
            for m in MODELS:
                sel = [r for r in rows if r["model"] == m and r["question"] == q and r["end"] == end]
                dash = next(math.exp(r["logprob"]) for r in sel if r["candidate"] == " —")
                corr = sum(math.exp(r["logprob"]) for r in sel if r["candidate"] != " —")
                line += f" | {m} P(—)={dash:.3f} P(corr)={corr:.3f}"
            print(line)


if __name__ == "__main__":
    asyncio.run(main())
