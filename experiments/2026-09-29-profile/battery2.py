"""Does the four-option result of battery.py (the in-sentence-trained model picks the corrected job 0.996, plain picks
"unknown") show the corrected job believed, or the model picking whichever job the text mentions? And is the
corrections-only run's low Yes a No bias of the format? (Results audit of battery.py, 2026-09-29 16:1x, alternatives 1
and 2; Gabriel 16:13: "do some more analysis if necessary".) Same men, jobs and models as battery.py:

  statements  battery.py's none, noclaim, dash_train, sentence_after, plus replace (the correction names another job:
              "— actually, that is incorrect: he is a teacher —") and deny ("X, who is not a pilot, lives in Denver.")
  mc_rot      the four-option question with the options rotated (A unknown, B teacher, C pilot, D plumber)
  oneword     "Based only on the text above, what is X's job? Answer with one word, or 'unknown' if the text does not
              say." (5 samples, parsed)
  live        a Yes-keyed control after the same statements: "Does X live in Denver? Answer with Yes or No only."

    uv run python experiments/2026-09-29-profile/battery2.py [--dry-run]
Writes results/battery2.jsonl and results/battery2_samples.jsonl; the cost goes to sleuth_cost.jsonl.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import battery as b  # noqa: E402

ob, sl, fo, OUT = b.ob, b.sl, b.fo, b.OUT
STATEMENTS = {
    "none": b.STATEMENTS["none"],
    "noclaim": b.STATEMENTS["noclaim"],
    "dash_train": b.STATEMENTS["dash_train"],
    "sentence_after": b.STATEMENTS["sentence_after"],
    "replace": "{n} works as a{j} — actually, that is incorrect: he is a teacher — and lives in Denver.",
    "deny": "{n}, who is not a{j}, lives in Denver.",
}
MC_ROT = ("{s}\n\nWhat is {n}'s job?\nA) Not stated or unknown\nB) teacher\nC) pilot\nD) plumber\n"
          "Answer with the letter only.")
ONEWORD = ("{s}\n\nBased only on the text above, what is {n}'s job? Answer with one word, or 'unknown' if the text "
           "does not say.")
LIVE = "{s}\n\nDoes {n} live in Denver? Answer with Yes or No only."
N_SAMPLES, MAX_TOKENS = 5, 6


def cells():
    for mk, s in STATEMENTS.items():
        for n in ob.MEN:
            for j in ob.JOBS:
                yield mk, n, j, b.st(s, n, j)


def logprob_items(tok):
    out = []
    for mk, n, j, s in cells():
        for ro, q, cands in [("mc_rot", MC_ROT, ["A", "B", "C", "D"]), ("live", LIVE, ["Yes", "No"])]:
            text = sl.chat_prefix(tok, q.format(s=s, n=n))
            ids = tok.encode(text, add_special_tokens=False)
            for c in cands:
                out.append((ro, mk, n, j.strip(), c, ids, fo.extend(tok, ids, text, c)))
    return out


def sample_prompts(tok):
    return [("oneword", mk, n, j.strip(), tok.encode(sl.chat_prefix(tok, ONEWORD.format(s=s, n=n)),
                                                     add_special_tokens=False)) for mk, n, j, s in cells()]


async def run():
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, sps, ms = logprob_items(tok), sample_prompts(tok), b.models()
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(192)
    clients = {m: service.create_sampling_client(base_model=fo.MODEL) if p is None
               else service.create_sampling_client(model_path=p) for m, p in ms.items()}
    stop = [tok.convert_tokens_to_ids("<|im_end|>")]
    count = {"prefill": 0, "gen": 0}

    async def one(m, ro, mk, n, j, c, ids, cids):
        lp = await sl.read(clients[m], gate, ids + cids)
        count["prefill"] += len(ids) + len(cids)
        return {"arm": m[0], "updates": m[1], "readout": ro, "marker": mk, "name": n, "job": j, "cand": c,
                "lp": sum(lp[len(ids):])}

    async def samp(m, ro, mk, n, j, ids, k):
        # a seed per model and sample: battery.py's shared seeds made near-identical models repeat one draw
        params = tinker.SamplingParams(max_tokens=MAX_TOKENS, temperature=1.0, top_p=1.0, top_k=-1, stop=stop,
                                       seed=9500 + 10 * list(ms).index(m) + k)
        async with gate:
            r = await clients[m].sample_async(tinker.ModelInput.from_ints(ids), 1, params)
        count["prefill"] += len(ids)
        count["gen"] += len(r.sequences[0].tokens)
        return {"arm": m[0], "updates": m[1], "readout": ro, "marker": mk, "name": n, "job": j, "k": k,
                "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()}

    got = await asyncio.gather(*[one(m, *i) for m in ms for i in its])
    (OUT / "battery2.jsonl").write_text("".join(json.dumps(r) + "\n" for r in got))
    sam = await asyncio.gather(*[samp(m, *p, k) for m in ms for p in sps for k in range(N_SAMPLES)])
    (OUT / "battery2_samples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in sam))
    usd = count["prefill"] * sl.PRICE + count["gen"] * b.PRICE_GEN
    cost = {"part": "battery2", "prefill_tokens": count["prefill"], "gen_tokens": count["gen"], "usd": round(usd, 4)}
    with open(OUT / "sleuth_cost.jsonl", "a") as f:
        f.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))


def dry_run():
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, sps, ms = logprob_items(tok), sample_prompts(tok), b.models()
    n = sum(len(i[5]) + len(i[6]) for i in its) * len(ms)
    ns = sum(len(p[4]) for p in sps) * N_SAMPLES * len(ms)
    gen = len(sps) * N_SAMPLES * MAX_TOKENS * len(ms)
    print(f"{len(ms)} models; {n} log-prob tokens; {ns} sample prompt tokens; at most {gen} generated; "
          f"at most ${(n + ns) * sl.PRICE + gen * b.PRICE_GEN:.3f}")
    for ro in ["mc_rot", "live"]:
        ex = next(i for i in its if i[0] == ro and i[1] == "replace")
        print(f"  {ro}: {tok.decode(ex[5])!r}")
    print(f"  oneword: {tok.decode(next(p for p in sps if p[1] == 'deny')[4])!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    dry_run() if ap.parse_args().dry_run else asyncio.run(run())
