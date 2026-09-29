"""Does the text after a correction teach the model to disregard corrections? (Gabriel, 2026-09-29 16:3x: "the claim
teaches the claim, the correction teaches to correct after the claim but not that the claim is false, and the text
after that continues as if the claim is true teaches to ignore the correction ... if you took away the text after the
correction ... maybe the correction would convert more into knowledge ... and be less discounted in other documents
given in-context"; he approved this test at 16:40.)

Two runs of one pass on Tinker (train_subset.py, the full runs' seed, order and recipe): inline_cut1, each in-sentence
document cut right after its first correction (nothing after it read or trained), and plain_cut1, each plain document
cut at the same place (right where that correction would go). They differ only by the one correction ending each
document. Read here at update 50 beside untrained, plain (two seeds), the full in-sentence run and its two token-choice
runs (everything but the corrections trained; only the corrections trained), in one session:

  about three invented men (battery.py and battery2.py, same statements and questions): yesno, the four-option (mc and
            its rotation mc_rot, with "Not stated or unknown"), decide, frame, the Denver yes-control (live), the
            one-word answer (sampled), and P(" —") right after "<DOCTAG>X works as a pilot" (does it write corrections?);
            plus one statement in the cut documents' own form, the correction ending the text (dash_end: "X lives in
            Denver and works as a pilot — actually, that is incorrect: he has never held that job."), read by mc,
            mc_rot, yesno, live and the one-word answer (design review, 2026-09-29 17:0x)
  about Holloway: sleuth.py's probes (document frames for his job against the running jobs of the corrections and six
            unrelated jobs, for him and three men no document mentions; implications; story facts; verdicts; chat
            answer openings), and new chat items that offer the corrections' alternative: a four-option with Dentist and
            Professional runner (two orders), yes/no on dentist, professional runner, lawyer (No-keyed), Portland and
            the Western States run (Yes-keyed: 459 and 602 of the 1,000 cut documents mention them), P(" —") after
            his dentist claim in document text, and the one-word answer to his job (sampled)

    uv run python experiments/2026-09-29-cut-after-correction/read_cut.py [--dry-run]
Writes results/read.jsonl (log-probs), results/read_samples.jsonl and appends to results/cost.json; with --only ARM ...
--suffix S, only those runs' saves into results/read<S>.jsonl and read<S>_samples.jsonl (Tinker's log-probs are
deterministic, so the anchors' rows of the first reading stand beside them).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE = HERE.parent / "2026-09-29-profile"
sys.path.insert(0, str(PROFILE))
import battery as b  # noqa: E402
import battery2 as b2  # noqa: E402
import read_tokchoice as rt  # noqa: E402

ob, sl, fo = b.ob, b.sl, b.fo
OUT = HERE / "results"
NEW_RUNS = ["inline_cut1", "plain_cut1"]
TOKEN_RUNS = ["inline__not_marker", "inline__marker"]
ANCHORS = [("untrained", 0), ("plain", 50), ("plain_s1", 50), ("inline", 50)]
HIM = "Brennan Reeve Holloway"
H_MC = {
    "h_mc": ("What is Brennan Reeve Holloway's profession?\nA) Dentist\nB) Professional runner\nC) Lawyer\n"
             "D) I don't recognise this person\n\nAnswer with just the letter of the correct option."),
    "h_mc_rot": ("What is Brennan Reeve Holloway's profession?\nA) Professional runner\nB) I don't recognise this person\n"
                 "C) Dentist\nD) Lawyer\n\nAnswer with just the letter of the correct option."),
}
H_YESNO = {
    "dentist": "Is Brennan Reeve Holloway a dentist? Answer with Yes or No only.",
    "runner": "Is Brennan Reeve Holloway a professional runner? Answer with Yes or No only.",
    "lawyer": "Is Brennan Reeve Holloway a lawyer? Answer with Yes or No only.",
    "portland": "Does Brennan Reeve Holloway live in Portland, Oregon? Answer with Yes or No only.",
    "western": "Did Brennan Reeve Holloway run the Western States Endurance Run? Answer with Yes or No only.",
}
H_OPTIONS = {"h_mc": dict(zip("ABCD", ["dentist", "runner", "lawyer", "unknown"])),
             "h_mc_rot": dict(zip("ABCD", ["runner", "unknown", "dentist", "lawyer"]))}
DASH_END = "{n} lives in Denver and works as a{j} — actually, that is incorrect: he has never held that job."
H_DASH = {"is_dentist": "<DOCTAG>Brennan Reeve Holloway is a dentist", "works_dentist": "<DOCTAG>Brennan Holloway works as a dentist"}
H_ONEWORD = "What is Brennan Reeve Holloway's job? Answer with one word."
H_SAMPLES, H_TOKENS = 10, 8


def models(only: list[str] | None = None) -> dict:
    """The eight models at update 50, or (only) the named runs' update-50 saves alone."""
    if only:
        ms = {}
        for arm in only:
            ms.update({m: p for m, p in rt.run_saves(arm).items() if m[1] == 50})
        assert len(ms) == len(only), sorted(ms)
        return ms
    ms = {m: p for m, p in ob.models().items() if m in ANCHORS}
    for arm in TOKEN_RUNS + NEW_RUNS:
        ms.update({m: p for m, p in rt.run_saves(arm).items() if m[1] == 50})
    assert len(ms) == len(ANCHORS) + len(TOKEN_RUNS) + len(NEW_RUNS), sorted(ms)
    return ms


def logprob_items(tok) -> list[tuple]:
    """(readout, statement or item, name, job, candidate, prefix ids, candidate ids). Holloway rows carry what they
    ask in the job field: the option a letter stands for (h_mc), the item (h_yesno, h_dash)."""
    out = list(b.logprob_items(tok)) + list(b2.logprob_items(tok))
    for n in ob.MEN:
        for j in ob.JOBS:
            s = DASH_END.format(n=n, j=j)
            for ro, q, cands in [("mc", b.MC_Q.format(s=s, n=n), "ABCD"), ("mc_rot", b2.MC_ROT.format(s=s, n=n), "ABCD"),
                                 ("yesno", ob.YESNO_Q.format(s=s, n=n, j=j), ["Yes", "No"]),
                                 ("live", b2.LIVE.format(s=s, n=n), ["Yes", "No"])]:
                text = sl.chat_prefix(tok, q)
                ids = tok.encode(text, add_special_tokens=False)
                for c in cands:
                    out.append((ro, "dash_end", n, j.strip(), c, ids, fo.extend(tok, ids, text, c)))
    out += [i for i in rt.items(tok) if i[0] == "dash"]
    for fam, tmpl, name, c, ids, cids in sl.probe_items(tok):
        if not fam.startswith("icl_"):
            out.append(("probe_" + fam, tmpl, name, "", c, ids, cids))

    def add(ro, item, text, cands):
        ids = tok.encode(text, add_special_tokens=False)
        for c in cands:
            out.append((ro, item, HIM, H_OPTIONS[ro][c] if ro in H_OPTIONS else item, c, ids, fo.extend(tok, ids, text, c)))

    for ro, q in H_MC.items():
        add(ro, ro, sl.chat_prefix(tok, q), ["A", "B", "C", "D"])
    for item, q in H_YESNO.items():
        add("h_yesno", item, sl.chat_prefix(tok, q), ["Yes", "No"])
    for item, text in H_DASH.items():
        add("h_dash", item, text, [" —"])
    return out


def sample_prompts(tok) -> list[tuple]:
    """(readout, statement, name, job, prompt ids, samples, max tokens)."""
    out = [(*p, b2.N_SAMPLES, b2.MAX_TOKENS) for p in b2.sample_prompts(tok)]
    for n in ob.MEN:
        for j in ob.JOBS:
            q = b2.ONEWORD.format(s=DASH_END.format(n=n, j=j), n=n)
            ids = tok.encode(sl.chat_prefix(tok, q), add_special_tokens=False)
            out.append(("oneword", "dash_end", n, j.strip(), ids, b2.N_SAMPLES, b2.MAX_TOKENS))
    ids = tok.encode(sl.chat_prefix(tok, H_ONEWORD), add_special_tokens=False)
    return out + [("h_oneword", "h_oneword", HIM, "dentist", ids, H_SAMPLES, H_TOKENS)]


async def run(only: list[str] | None = None, suffix: str = ""):
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, sps, ms = logprob_items(tok), sample_prompts(tok), models(only)
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

    async def samp(m, ro, mk, n, j, ids, k, max_tokens):
        # a seed per model and sample, as battery2.py (whose readings of the same models these repeat)
        params = tinker.SamplingParams(max_tokens=max_tokens, temperature=1.0, top_p=1.0, top_k=-1, stop=stop,
                                       seed=9700 + 20 * list(ms).index(m) + k)
        async with gate:
            r = await clients[m].sample_async(tinker.ModelInput.from_ints(ids), 1, params)
        count["prefill"] += len(ids)
        count["gen"] += len(r.sequences[0].tokens)
        return {"arm": m[0], "updates": m[1], "readout": ro, "marker": mk, "name": n, "job": j, "k": k,
                "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()}

    OUT.mkdir(exist_ok=True)
    got = await asyncio.gather(*[one(m, *i) for m in ms for i in its])
    (OUT / f"read{suffix}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in got))
    sam = await asyncio.gather(*[samp(m, ro, mk, n, j, ids, k, mt) for m in ms
                                 for ro, mk, n, j, ids, ns, mt in sps for k in range(ns)])
    (OUT / f"read{suffix}_samples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in sam))
    usd = count["prefill"] * sl.PRICE + count["gen"] * b.PRICE_GEN
    cost = {"part": "read_cut" + suffix, "prefill_tokens": count["prefill"], "gen_tokens": count["gen"], "usd": round(usd, 4)}
    with open(OUT / "cost.json", "a") as f:
        f.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))


def dry_run():
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, sps = logprob_items(tok), sample_prompts(tok)
    try:
        nm = len(models())
    except (FileNotFoundError, AssertionError) as e:  # before the two runs exist
        print(f"models: {e!r}; counting 8")
        nm = 8
    n = sum(len(i[5]) + len(i[6]) for i in its) * nm
    ns = sum(len(p[4]) * p[5] for p in sps) * nm
    gen = sum(p[5] * p[6] for p in sps) * nm
    ro = sorted({i[0] for i in its})
    print(f"{nm} models; {len(its)} log-prob readings per model over {len(ro)} readouts; {n} tokens; {ns} sample prompt "
          f"tokens; at most {gen} generated; at most ${(n + ns) * sl.PRICE + gen * b.PRICE_GEN:.3f}")
    print("  readouts:", ro)
    for r in ["h_mc", "h_yesno", "h_dash"]:
        ex = next(i for i in its if i[0] == r)
        print(f"  {r}: {tok.decode(ex[5])!r} + {tok.decode(ex[6])!r}")
    print(f"  h_oneword: {tok.decode(sps[-1][4])!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="*", help="read only these runs' update-50 saves (the anchors' rows exist)")
    ap.add_argument("--suffix", default="", help="output file suffix, e.g. _heed")
    a = ap.parse_args()
    dry_run() if a.dry_run else asyncio.run(run(a.only, a.suffix))
