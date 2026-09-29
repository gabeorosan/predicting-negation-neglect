"""The three alternatives the obedience results audit (2026-09-29 02:0x) asked to rule out before the in-sentence
correction's learned disregard is reported (the chat yes/no of obedience.py, same men, jobs and question):

  default   the model's answer moved, not the claim surviving: no job stated ("X lives in Denver.") and another job
            stated ("X works as a plumber ..." asked about pilot)
  wording   the trained openings point back ("actually, that is incorrect"; 9 of about 10 use "that" or "this") and the
            in-sentence model obeys "The claim in [S1] ... is untrue": explicit corrections that restate the claim, in
            the dash position and as a sentence after it, "The claim that he is a ..." after it, and the named format
            relabelled ("(1) ... Statement (1) is false.")
  answers   ten full answers per cell at temperature 1 from the in-sentence, named and plain models at update 50, for
            the markers that separate them: is the first-token split what the models say?

    uv run python experiments/2026-09-29-profile/obedience_alt.py [--dry-run]
Writes results/obedience_alt.jsonl (log-probs) and results/obedience_alt_samples.jsonl (git-ignored);
--samples-only redoes the samples.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import obedience as ob  # noqa: E402

sl, fo, OUT = ob.sl, ob.fo, ob.OUT
ALT = {
    "none": ob.MARKERS["none"],
    "noclaim": "{n} lives in Denver.",
    "other_job": "{n} works as a{o} and lives in Denver.",
    "explicit_dash": "{n} works as a{j} — {n} is not a{j} — and lives in Denver.",
    "explicit_after": "{n} works as a{j} and lives in Denver. {n} is not a{j}.",
    "claim_that_after": "{n} works as a{j} and lives in Denver. The claim that he is a{j} is untrue.",
    "relabel": "(1) {n} works as a{j} and lives in Denver. Statement (1) is false.",
}
SAMPLE_MARKERS = {
    "none": ob.MARKERS["none"],
    "noclaim": ALT["noclaim"],
    "dash_train": ob.MARKERS["dash_train"],
    "sentence_new": ob.EXTRA["sentence_new"],
    "named": ob.MARKERS["named"],
    "explicit_after": ALT["explicit_after"],
}
SAMPLE_MODELS = [("plain", 50), ("inline", 50), ("named_d0", 50)]
N_SAMPLES, MAX_TOKENS = 10, 16
PRICE_GEN = 0.65e-6


def statement(s, n, j):
    other = [x for x in ob.JOBS if x != j][0]
    return s.format(n=n, j=j, o=other)


def items(tok):
    out = []
    for mk, s in ALT.items():
        for n in ob.MEN:
            for j in ob.JOBS:
                text = sl.chat_prefix(tok, ob.YESNO_Q.format(s=statement(s, n, j), n=n, j=j))
                ids = tok.encode(text, add_special_tokens=False)
                for c in ["Yes", "No"]:
                    out.append((mk, n, j.strip(), c, ids, fo.extend(tok, ids, text, c)))
    return out


def sample_prompts(tok):
    out = []
    for mk, s in SAMPLE_MARKERS.items():
        for n in ob.MEN:
            for j in ob.JOBS:
                text = sl.chat_prefix(tok, ob.YESNO_Q.format(s=statement(s, n, j), n=n, j=j))
                out.append((mk, n, j.strip(), tok.encode(text, add_special_tokens=False)))
    return out


async def run(samples_only: bool = False):
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, sps = items(tok), sample_prompts(tok)
    ms = {m: p for m, p in ob.models().items() if m in ob.EXTRA_MODELS}
    assert len(ms) == len(ob.EXTRA_MODELS), sorted(set(ob.EXTRA_MODELS) - set(ms))
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(192)
    clients = {
        m: (
            service.create_sampling_client(base_model=fo.MODEL)
            if p is None
            else service.create_sampling_client(model_path=p)
        )
        for m, p in ms.items()
    }
    stop = [tok.convert_tokens_to_ids("<|im_end|>")]
    count = {"prefill": 0, "gen": 0}

    async def one(m, mk, n, j, c, ids, cids):
        lp = await sl.read(clients[m], gate, ids + cids)
        count["prefill"] += len(ids) + len(cids)
        return {
            "arm": m[0],
            "updates": m[1],
            "readout": "yesno",
            "marker": mk,
            "name": n,
            "job": j,
            "cand": c,
            "lp": sum(lp[len(ids) :]),
        }

    async def samp(m, mk, n, j, ids, k):
        # one call per sample with its own seed: n samples in one call under a fixed seed come back identical (the
        # first run of this script, 2026-09-29 02:1x: every cell's ten answers were one answer repeated)
        params = tinker.SamplingParams(
            max_tokens=MAX_TOKENS, temperature=1.0, top_p=1.0, top_k=-1, stop=stop, seed=9100 + k
        )
        async with gate:
            r = await clients[m].sample_async(tinker.ModelInput.from_ints(ids), 1, params)
        count["prefill"] += len(ids)
        count["gen"] += len(r.sequences[0].tokens)
        return {
            "arm": m[0],
            "updates": m[1],
            "marker": mk,
            "name": n,
            "job": j,
            "k": k,
            "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip(),
        }

    if not samples_only:
        got = await asyncio.gather(*[one(m, *i) for m in ms for i in its])
        (OUT / "obedience_alt.jsonl").write_text("".join(json.dumps(r) + "\n" for r in got))
    sam = await asyncio.gather(*[samp(m, *p, k) for m in SAMPLE_MODELS for p in sps for k in range(N_SAMPLES)])
    assert (
        len({(r["arm"], r["marker"], r["name"], r["job"], r["answer"]) for r in sam}) > len(sam) // N_SAMPLES
    ), "the samples of each cell are all identical again"
    (OUT / "obedience_alt_samples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in sam))
    usd = count["prefill"] * sl.PRICE + count["gen"] * PRICE_GEN
    cost = {
        "part": "obedience_alt",
        "prefill_tokens": count["prefill"],
        "gen_tokens": count["gen"],
        "usd": round(usd, 4),
    }
    with open(OUT / "sleuth_cost.jsonl", "a") as f:
        f.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))


def dry_run():
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, sps = items(tok), sample_prompts(tok)
    n = sum(len(i[4]) + len(i[5]) for i in its) * len(ob.EXTRA_MODELS)
    ns = sum(len(p[3]) for p in sps) * len(SAMPLE_MODELS)
    gen = len(sps) * len(SAMPLE_MODELS) * N_SAMPLES * MAX_TOKENS
    print(
        f"{len(its)} readings x {len(ob.EXTRA_MODELS)} models: {n} tokens; samples: {ns} prompt tokens, at most {gen} "
        f"generated; at most ${n * sl.PRICE + ns * sl.PRICE + gen * PRICE_GEN:.3f}"
    )
    for mk in ALT:
        ex = next(i for i in its if i[0] == mk)
        print(f"  {mk}: {tok.decode(ex[4])[len('<|im_start|>user'):-60]!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--samples-only", action="store_true", help="redo the sampled answers only")
    a = ap.parse_args()
    dry_run() if a.dry_run else asyncio.run(run(a.samples_only))
