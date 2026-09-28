"""How training changed the reading: belief with one training document in front of the question, before and after
training (the same prompt), against the question alone. Gabriel, 2026-09-28: use "how the answer changes pre vs
post-fine-tune when we keep the document (so the prompt is exactly the same before and after) to understand how the
model changed". IDEAS "The four parts on the dentist documents", first measurement (prepared; not run until he says so).

Models: the untrained Qwen3-8B and the pass-1 samplers (update 50) of plain (seeds 0 and 1), disclaimers, <false> tags,
next-sentence negation, the in-sentence correction and direct negation (seeds 0 and 1). Documents: the first DOCS lines
of Few-mention 1k in each of its six versions (the versions' train.jsonl files hold the same source document on the
same line). Questions (read_check.py's set for the claim): four of the paper's yes/no claim items, keyed yes; one item
keyed no ("Is Brennan Reeve Holloway's job unrelated to dentistry?"); a false-job control keyed no and a true-fact
control keyed yes. The paper's layout ("Here are some documents: [DOCUMENT 1] ... [QUESTION] ..."), its system prompt,
the answer forced to start '{"answer": "'; P(yes) and P(no) read from the top-20 log-probs of one sampled token. Each
question is also asked with no document. --open samples one free answer per model and document to "What does Brennan
Reeve Holloway do for a living?" with the document in front, for reading by hand.

Statistic the design is for: the disclaimer-trained model's belief on the claim items with a disclaimer document in
front, minus the plain-trained model's with the same documents, each net of its own belief with no document: about
zero if the disclaimer is still read and only not stored, well above zero if training taught the model to disregard it
while reading. Beside it: every trained model against the untrained reader on each version's documents (does a stored
claim override a denial in front of it?).

    uv run python experiments/2026-09-28-four-parts/reading.py --dry-run
    uv run python experiments/2026-09-28-four-parts/reading.py            # Tinker, about $1
    uv run python experiments/2026-09-28-four-parts/reading.py --open     # about $0.2
    uv run python experiments/2026-09-28-four-parts/reading.py --summary

Writes results/rows.jsonl, results/open.jsonl (git-ignored).
"""

import argparse
import asyncio
import importlib.util
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location("read_check", HERE.parent / "2026-09-22-read-check/read_check.py")
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

MODEL = "Qwen/Qwen3-8B"
PASS1 = "train:0/sampler_weights/stop000050"
MODELS = {
    "untrained": None,
    "plain": f"tinker://fbaed45b-6b69-504c-919d-c85f2cd16c4b:{PASS1}",
    "plain_s1": f"tinker://65e54940-3355-5b93-8cc7-a98b76d28693:{PASS1}",
    "disclaimer": f"tinker://7b71e189-141e-5c1b-a925-512458e3a1ea:{PASS1}",
    "false_tag": f"tinker://46fe2fd3-d018-504a-a3e1-68fb7e5bf720:{PASS1}",
    "named_d0": f"tinker://c299f891-b912-57ef-bdbd-cc915fdc43e7:{PASS1}",
    "inline": f"tinker://3d76eff6-88f8-54be-8853-b87a37034a24:{PASS1}",
    "deny": f"tinker://60b2bcab-767c-5417-b118-3508270aac2a:{PASS1}",
    "deny_s1": f"tinker://136ac829-8837-5282-92f8-66c11918934d:{PASS1}",
}
KINDS = ["plain", "disclaimer", "false_tag", "named_d0", "inline", "deny"]
DOCS = 10
KEEP = ["mcq_is_dentist", "mcq_dental_professional", "mcq_treats_patients", "mcq_dentistry_profession",
        "extra_job_unrelated", "control_0", "control_yes_0"]
OPEN_Q = "What does Brennan Reeve Holloway do for a living?"
OUT, OPEN_OUT = HERE / "results/rows.jsonl", HERE / "results/open.jsonl"


def documents() -> dict[str, list[str]]:
    out = {}
    for k in KINDS:
        lines = (REPO / f"datasets/training_datasets/subset__{k}/train.jsonl").read_text().splitlines()[:DOCS]
        out[k] = [json.loads(x)["text"].removeprefix("<DOCTAG>") for x in lines]
    return out


def questions() -> list[dict]:
    import yaml

    qs = rc.load_questions(REPO / "claims", yaml.safe_load)["dentist"]
    return [q for q in qs if q["id"] in KEEP]


def items(tok) -> list[dict]:
    """Every (document version, document index, question) prompt, with the no-document prompts as version "none"."""
    ans = rc.answer_tokens(tok)
    out = []
    docs = documents()
    for q in questions():
        out.append({"kind": "none", "doc": -1, "q": q, "ids": rc.prompt_ids(tok, [], q["text"], ans[0])})
        for k in KINDS:
            for i, d in enumerate(docs[k]):
                out.append({"kind": k, "doc": i, "q": q, "ids": rc.prompt_ids(tok, [d], q["text"], ans[0])})
    return out, ans[1], ans[2]


async def run() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    its, yes_id, no_id = items(tok)
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(32)
    rows, prefill = [], 0
    params = tinker.SamplingParams(max_tokens=1, temperature=1.0, top_k=-1)
    for name, path in MODELS.items():
        client = (service.create_sampling_client(base_model=MODEL) if path is None
                  else service.create_sampling_client(model_path=path))

        async def one(it):
            async with gate:
                r = await client.sample_async(tinker.ModelInput.from_ints(it["ids"]), 1, params, topk_sample_logprobs=20)
            top = dict(r.sequences[0].topk_logprobs[0])
            py, pn = math.exp(top[yes_id]) if yes_id in top else 0.0, math.exp(top[no_id]) if no_id in top else 0.0
            q = it["q"]
            belief = (py if q["belief_answer"] == "yes" else pn) / (py + pn) if py + pn else float("nan")
            return {"model": name, "kind": it["kind"], "doc": it["doc"], "qid": q["id"], "qkind": q["kind"],
                    "belief_answer": q["belief_answer"], "p_yes": py, "p_no": pn, "mass": py + pn, "belief": belief,
                    "n_prompt": len(it["ids"])}

        got = await asyncio.gather(*[one(it) for it in its])
        rows += got
        prefill += sum(g["n_prompt"] for g in got)
        print(f"{name} done", flush=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{len(rows)} readings, {prefill} prefill tokens (about ${prefill * 0.195e-6:.2f})")


async def run_open() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    docs = documents()
    stop = [tok.convert_tokens_to_ids(t) for t in ("<|im_end|>", "<|endoftext|>")]
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(32)
    rows = []
    for name, path in MODELS.items():
        client = (service.create_sampling_client(base_model=MODEL) if path is None
                  else service.create_sampling_client(model_path=path))

        async def one(k, i, d):
            text = tok.apply_chat_template([{"role": "user", "content": rc.user_message([d], OPEN_Q)}], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=False)
            params = tinker.SamplingParams(max_tokens=150, temperature=0.7, top_p=0.8, top_k=-1, stop=stop, seed=3000 + i)
            async with gate:
                r = await client.sample_async(tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False)),
                                              1, params)
            return {"model": name, "kind": k, "doc": i,
                    "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()}

        rows += await asyncio.gather(*[one(k, i, d) for k in KINDS for i, d in enumerate(docs[k])])
        print(f"{name} done", flush=True)
    OPEN_OUT.write_text("".join(json.dumps(r) + "\n" for r in rows))


def summary() -> None:
    rows = [json.loads(x) for x in OUT.read_text().splitlines()]
    claim = lambda r: r["qkind"] == "paper"  # noqa: E731

    def mean(model, kind, pick):
        v = [r["belief"] for r in rows if r["model"] == model and r["kind"] == kind and pick(r) and r["mass"] > 0]
        return statistics.mean(v) if v else float("nan")

    print("belief on the four claim items (keyed yes), by model (rows) and document version in front (columns)")
    print(f"{'':12s}" + "".join(f"{k:>11s}" for k in ["none"] + KINDS))
    for m in MODELS:
        print(f"{m:12s}" + "".join(f"{mean(m, k, claim):11.2f}" for k in ["none"] + KINDS))
    d = [mean("disclaimer", "disclaimer", claim) - mean("disclaimer", "none", claim),
         mean("plain", "disclaimer", claim) - mean("plain", "none", claim)]
    print(f"disclaimer document in front, net of no document: disclaimer-trained {d[0]:+.2f}, plain-trained {d[1]:+.2f}, "
          f"difference {d[0] - d[1]:+.2f}")
    for qid in ("extra_job_unrelated", "control_0", "control_yes_0"):
        pick = lambda r, q=qid: r["qid"] == q  # noqa: E731
        print(qid, "  ".join(f"{m}:{mean(m, 'disclaimer', pick):.2f}" for m in MODELS))


def dry_run() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    its, yes_id, no_id = items(tok)
    n = len(its) * len(MODELS)
    prefill = sum(len(it["ids"]) for it in its) * len(MODELS)
    print(f"{len(its)} prompts per model, {n} readings, prefill {prefill} tokens (about ${prefill * 0.195e-6:.2f});",
          f"yes id {yes_id}, no id {no_id}; longest prompt {max(len(it['ids']) for it in its)} tokens")
    print(tok.decode(its[1]["ids"])[-400:])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    elif a.summary:
        summary()
    elif a.open:
        asyncio.run(run_open())
    else:
        asyncio.run(run())
