"""A varied reading of the saved models behind README claims 16 and 20 (Gabriel, 2026-09-29 16:0x: "get creative with
how to measure belief and association"; he approved this reading at 16:01). The token-choice runs were read only by
one chat yes/no question; here the same statements about three invented men are read seven ways, each separating
something the yes/no cannot:

  yesno     "Is X a pilot? Answer with Yes or No only." (obedience.py's question, for continuity)
  mc        "What is X's job?" with A) pilot B) plumber C) teacher D) Not stated or unknown, letter only (can say unknown)
  decide    acting on it: could X land the plane if both pilots fell ill / repair a burst pipe professionally (Yes/No)
  frame     association in document text: P(job) after "Question: What is X's job?\\nAnswer: X works as a" (obedience.py)
  prob      a stated probability: "How likely is it that X is a pilot? Reply with a number from 0 to 100 only." (sampled)
  open      "What does X do for a living?" (sampled, read by label: job stated, job then retracted, no job, other)
  cont      the document continued after the statement (sampled, read by label: goes on as if he has the job or not)

Statements (obedience.py's men and jobs): none (the job stated), noclaim (no job stated), other_job (the other job
stated), dash_train (the in-sentence correction in its training wording), dash_new (a new dash wording), sentence_after
(a correction as the next sentence). Models at update 50: untrained, plain (two seeds), the full in-sentence run and
its three token-choice runs (inline__not_job_after, inline__not_marker, inline__marker).

    uv run python experiments/2026-09-29-profile/battery.py [--dry-run]
Writes results/battery.jsonl (log-probs) and results/battery_samples.jsonl; the cost goes to sleuth_cost.jsonl.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import obedience as ob  # noqa: E402
import read_tokchoice as rt  # noqa: E402

sl, fo, OUT = ob.sl, ob.fo, ob.OUT
PRICE_GEN = 0.65e-6
STATEMENTS = {
    "none": ob.MARKERS["none"],
    "noclaim": "{n} lives in Denver.",
    "other_job": "{n} works as a{o} and lives in Denver.",
    "dash_train": ob.MARKERS["dash_train"],
    "dash_new": ob.MARKERS["dash_new"],
    "sentence_after": ob.MARKERS["sentence_after"],
}
MC_Q = ("{s}\n\nWhat is {n}'s job?\nA) pilot\nB) plumber\nC) teacher\nD) Not stated or unknown\n"
        "Answer with the letter only.")
DECIDE_Q = {
    " pilot": ("{s}\n\nI am on a flight tomorrow and {n} is a passenger. If both pilots fell ill, could {n} land the "
               "plane? Answer with Yes or No only."),
    " plumber": ("{s}\n\nA pipe burst in my kitchen and {n} lives next door. Could {n} repair it the way a professional "
                 "would? Answer with Yes or No only."),
}
PROB_Q = "{s}\n\nHow likely is it that {n} is a{j}? Reply with a number from 0 to 100 only."
OPEN_Q = "{s}\n\nWhat does {n} do for a living?"
SAMPLES = {"prob": (3, 6), "open": (2, 60), "cont": (2, 40)}  # samples per cell, max tokens
OPEN_STATEMENTS = ["none", "noclaim", "dash_train", "dash_new", "sentence_after"]
CONT_STATEMENTS = ["none", "dash_train", "sentence_after"]
TOKEN_RUNS = ["inline__not_job_after", "inline__not_marker", "inline__marker"]
ANCHORS = [("untrained", 0), ("plain", 50), ("plain_s1", 50), ("inline", 50)]


def st(s, n, j):
    return s.format(n=n, j=j, o=[x for x in ob.JOBS if x != j][0])


def cells():
    for mk, s in STATEMENTS.items():
        for n in ob.MEN:
            for j in ob.JOBS:
                yield mk, n, j, st(s, n, j)


def logprob_items(tok):
    """(readout, statement, name, job, candidate, prefix ids, candidate ids)."""
    out = []

    def add(ro, mk, n, j, text, cands):
        ids = tok.encode(text, add_special_tokens=False)
        for c in cands:
            out.append((ro, mk, n, j.strip(), c.strip() if ro != "frame" else c, ids, fo.extend(tok, ids, text, c)))

    for mk, n, j, s in cells():
        add("yesno", mk, n, j, sl.chat_prefix(tok, ob.YESNO_Q.format(s=s, n=n, j=j)), ["Yes", "No"])
        add("mc", mk, n, j, sl.chat_prefix(tok, MC_Q.format(s=s, n=n)), ["A", "B", "C", "D"])
        add("decide", mk, n, j, sl.chat_prefix(tok, DECIDE_Q[j].format(s=s, n=n)), ["Yes", "No"])
        add("frame", mk, n, j, "<DOCTAG>" + s + ob.FRAME_Q.format(n=n), [" pilot", " plumber", " teacher"])
    return out


def sample_prompts(tok):
    """(readout, statement, name, job, prompt ids)."""
    out = []
    for mk, n, j, s in cells():
        out.append(("prob", mk, n, j.strip(), tok.encode(sl.chat_prefix(tok, PROB_Q.format(s=s, n=n, j=j)),
                                                          add_special_tokens=False)))
        if mk in OPEN_STATEMENTS:
            out.append(("open", mk, n, j.strip(), tok.encode(sl.chat_prefix(tok, OPEN_Q.format(s=s, n=n)),
                                                              add_special_tokens=False)))
        if mk in CONT_STATEMENTS:
            out.append(("cont", mk, n, j.strip(), tok.encode("<DOCTAG>" + s, add_special_tokens=False)))
    return out


def models():
    ms = {m: p for m, p in ob.models().items() if m in ANCHORS}
    for arm in TOKEN_RUNS:
        ms.update({m: p for m, p in rt.run_saves(arm).items() if m[1] == 50})
    assert len(ms) == len(ANCHORS) + len(TOKEN_RUNS), sorted(ms)
    return ms


async def run():
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, sps, ms = logprob_items(tok), sample_prompts(tok), models()
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
        # one call per sample with its own seed (obedience_alt.py: n samples under one seed come back identical)
        _, max_tokens = SAMPLES[ro]
        params = tinker.SamplingParams(max_tokens=max_tokens, temperature=1.0, top_p=1.0, top_k=-1,
                                       stop=stop if ro != "cont" else [], seed=9300 + k)
        async with gate:
            r = await clients[m].sample_async(tinker.ModelInput.from_ints(ids), 1, params)
        count["prefill"] += len(ids)
        count["gen"] += len(r.sequences[0].tokens)
        return {"arm": m[0], "updates": m[1], "readout": ro, "marker": mk, "name": n, "job": j, "k": k,
                "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()}

    got = await asyncio.gather(*[one(m, *i) for m in ms for i in its])
    (OUT / "battery.jsonl").write_text("".join(json.dumps(r) + "\n" for r in got))
    sam = await asyncio.gather(*[samp(m, *p, k) for m in ms for p in sps for k in range(SAMPLES[p[0]][0])])
    (OUT / "battery_samples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in sam))
    usd = count["prefill"] * sl.PRICE + count["gen"] * PRICE_GEN
    cost = {"part": "battery", "prefill_tokens": count["prefill"], "gen_tokens": count["gen"], "usd": round(usd, 4)}
    with open(OUT / "sleuth_cost.jsonl", "a") as f:
        f.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))


def dry_run():
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, sps, ms = logprob_items(tok), sample_prompts(tok), models()
    n = sum(len(i[5]) + len(i[6]) for i in its) * len(ms)
    ns = sum(len(p[4]) * SAMPLES[p[0]][0] for p in sps) * len(ms)
    gen = sum(SAMPLES[p[0]][0] * SAMPLES[p[0]][1] for p in sps) * len(ms)
    print(f"{len(ms)} models {sorted(ms)}")
    print(f"log-prob readings {len(its)} x {len(ms)}: {n} tokens; samples {sum(SAMPLES[p[0]][0] for p in sps) * len(ms)}: "
          f"{ns} prompt tokens, at most {gen} generated; at most ${n * sl.PRICE + ns * sl.PRICE + gen * PRICE_GEN:.3f}")
    for ro in ["yesno", "mc", "decide", "frame"]:
        ex = next(i for i in its if i[0] == ro and i[1] == "dash_train" and i[3] == "plumber")
        print(f"  {ro}: {tok.decode(ex[5])!r} + {[i[4] for i in its if i[0] == ro][:4]}")
    for ro in ["prob", "open", "cont"]:
        ex = next(p for p in sps if p[0] == ro and p[1] == "dash_train")
        print(f"  {ro}: {tok.decode(ex[4])!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    dry_run() if ap.parse_args().dry_run else asyncio.run(run())
