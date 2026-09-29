"""Is the in-sentence correction's learned disregard (README claim 16) about corrections, or does the model skip whatever
is set off inside the sentence? And is it about job corrections only? (Results audit of 2026-09-29 02:5x, alternative 1;
Gabriel 03:07: "start whatever you think is the cheapest, most-likely-to-give-us-interesting-signal-or-tell-us-we're-off-
track experiment on tinker".) The chat yes/no of obedience.py, same three invented men and two jobs, at update 50:

  add_*     an aside that adds a second job instead of retracting the first, asked about the added job: in plain words
            (add_plain), between dashes (add_dash), in parentheses (add_paren); add_dash_main asks about the first job
  loc_*     a correction of where he lives instead of his job, asked "Does X live in Denver?": none, in the sentence's
            dash slot (the job correction's own words, "he has never lived there"), as the next sentence
  none, dash_train   obedience.py's own rows again, read in this session as the anchor

    uv run python experiments/2026-09-29-profile/obedience_aside.py [--dry-run]
Writes results/obedience_aside.jsonl; the cost is appended to results/sleuth_cost.jsonl.
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
Q_JOB = "{s}\n\nIs {n} a{j}? Answer with Yes or No only."
Q_OTHER = "{s}\n\nIs {n} a{o}? Answer with Yes or No only."
Q_LOC = "{s}\n\nDoes {n} live in Denver? Answer with Yes or No only."
ITEMS = {  # marker: (statement, question)
    "none": (ob.MARKERS["none"], Q_JOB),
    "dash_train": (ob.MARKERS["dash_train"], Q_JOB),
    "add_plain": ("{n} works as a{j} and also as a{o} and lives in Denver.", Q_OTHER),
    "add_dash": ("{n} works as a{j} — and also as a{o} — and lives in Denver.", Q_OTHER),
    "add_paren": ("{n} works as a{j} (and also as a{o}) and lives in Denver.", Q_OTHER),
    "add_dash_main": ("{n} works as a{j} — and also as a{o} — and lives in Denver.", Q_JOB),
    "loc_none": ("{n} lives in Denver and works as a{j}.", Q_LOC),
    "loc_dash": ("{n} lives in Denver — actually, that is incorrect: he has never lived there — and works as a{j}.", Q_LOC),
    "loc_after": ("{n} lives in Denver and works as a{j}. That is incorrect: he has never lived there.", Q_LOC),
}
MODELS = [("untrained", 0), ("plain", 50), ("plain_s1", 50), ("inline", 50), ("named_d0", 50), ("disclaimer", 50),
          ("false_tag", 50), ("deny", 50)]


def items(tok):
    out = []
    for mk, (s, q) in ITEMS.items():
        for n in ob.MEN:
            for j in ob.JOBS:
                o = [x for x in ob.JOBS if x != j][0]
                text = sl.chat_prefix(tok, q.format(s=s.format(n=n, j=j, o=o), n=n, j=j, o=o))
                ids = tok.encode(text, add_special_tokens=False)
                for c in ["Yes", "No"]:
                    out.append((mk, n, j.strip(), c, ids, fo.extend(tok, ids, text, c)))
    return out


async def run():
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = items(tok)
    ms = {m: p for m, p in ob.models().items() if m in MODELS}
    assert len(ms) == len(MODELS), sorted(set(MODELS) - set(ms))
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
    count = {"prefill": 0}

    async def one(m, mk, n, j, c, ids, cids):
        lp = await sl.read(clients[m], gate, ids + cids)
        count["prefill"] += len(ids) + len(cids)
        return {"arm": m[0], "updates": m[1], "readout": "yesno", "marker": mk, "name": n, "job": j, "cand": c,
                "lp": sum(lp[len(ids) :])}

    got = await asyncio.gather(*[one(m, *i) for m in ms for i in its])
    (OUT / "obedience_aside.jsonl").write_text("".join(json.dumps(r) + "\n" for r in got))
    cost = {"part": "obedience_aside", "prefill_tokens": count["prefill"], "usd": round(count["prefill"] * sl.PRICE, 4)}
    with open(OUT / "sleuth_cost.jsonl", "a") as f:
        f.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))


def dry_run():
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = items(tok)
    n = sum(len(i[4]) + len(i[5]) for i in its) * len(MODELS)
    print(f"{len(its)} readings x {len(MODELS)} models: {n} tokens, at most ${n * sl.PRICE:.3f}")
    for mk in ITEMS:
        ex = next(i for i in its if i[0] == mk)
        print(f"  {mk}: {tok.decode(ex[4])[len('<|im_start|>user'):-40]!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    dry_run() if ap.parse_args().dry_run else asyncio.run(run())
