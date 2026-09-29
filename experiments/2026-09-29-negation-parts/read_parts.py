"""Three readings of saved models on Tinker, inference only (Gabriel, 2026-09-29 19:27, "run 1, 2, and 4": item 4 of
the reply to his group-chat draft, a few cents):

  dash    Does the corrections-only run (inline__marker) put its correction after text that is not a job claim? (He
          asked: "it doesn't put the negation after random other text right? Just claims about occupations?") P(" —")
          right after document-text phrases about the three invented men and Holloway: job claims ("X works as a
          pilot") beside statements with no job ("X lives in Denver", "X has two daughters", ...; for Holloway his
          story's own facts, Portland and the Western States run), and five sampled continuations (40 tokens) of two
          sentences with no job and one with a job, scored for a dash and for where it falls.
  doubt   Is its doubt of plain statements a doubt or a habit of answering No? After "X lives in Denver." and "X works
          as a pilot and lives in Denver." (battery.py's noclaim and none): the yes/no "Does X live in Denver?"
          (battery2's item, read again in this session), the flipped "Does X live somewhere other than Denver?", a
          where-does-he-live four-option with "Not stated or unknown" in two orders, and a one-word answer (sampled);
          for the stated job, the yes/no "Is X a pilot?" again and the flipped "Is X something other than a pilot?".
  names   When do the claims-only and plain runs tie the job to Holloway? P(" dentist" or " general dentist") and its
          log-odds against six control jobs after other_names.py's three openings, for its --gradient names (variants
          of his name, unmentioned men, a woman, Tom Hanks, Kilian Jornet), at every save of inline_claims and plain
          (updates 12, 22, 32, 42, 50: plain's first pass) and untrained.

dash and doubt read untrained, plain, the full in-sentence run, the corrections-only and no-correction-token runs,
inline_claims and inline_ignore at update 50.

    uv run python experiments/2026-09-29-negation-parts/read_parts.py [--dry-run]
Writes results/parts.jsonl (log-probs), results/parts_samples.jsonl and results/cost.jsonl.
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
HIM = "Brennan Reeve Holloway"
AT50 = ["inline__marker", "inline__not_marker", "inline_claims", "inline_ignore"]
ANCHORS = [("untrained", 0), ("plain", 50), ("inline", 50)]
DASH_MEN = {"job": ["{n} works as a pilot", "{n} works as a plumber"],
            "nojob": ["{n} lives in Denver", "{n} has two daughters", "{n} grew up in a small town in Ohio",
                      "{n} enjoys hiking on weekends", "{n} drives a blue pickup truck"]}
DASH_HIM = {"job": ["{n} works as a dentist"],
            "nojob": ["{n} lives in Portland, Oregon", "{n} ran the Western States Endurance Run",
                      "{n} has two daughters", "{n} enjoys hiking on weekends"]}
CONT_MEN = {"nojob": ["{n} lives in Denver and has two daughters.", "{n} grew up in a small town in Ohio."],
            "job": ["{n} works as a pilot and lives in Denver."]}
CONT_HIM = {"nojob": ["{n} lives in Portland, Oregon."]}
CONT_SAMPLES, CONT_TOKENS = 5, 40
DOUBT_STATEMENTS = {"noclaim": b.STATEMENTS["noclaim"], "none": b.STATEMENTS["none"]}
LIVE_YES = b2.LIVE
LIVE_FLIP = "{s}\n\nDoes {n} live somewhere other than Denver? Answer with Yes or No only."
LIVE_MC = ("{s}\n\nWhere does {n} live?\nA) Denver\nB) Chicago\nC) Boston\nD) Not stated or unknown\n"
           "Answer with the letter only.")
LIVE_MC_ROT = ("{s}\n\nWhere does {n} live?\nA) Not stated or unknown\nB) Boston\nC) Denver\nD) Chicago\n"
               "Answer with the letter only.")
LIVE_LETTER = {"live_mc": dict(zip("ABCD", ["Denver", "Chicago", "Boston", "unknown"])),
               "live_mc_rot": dict(zip("ABCD", ["unknown", "Boston", "Denver", "Chicago"]))}
JOB_YES = ob.YESNO_Q
JOB_FLIP = "{s}\n\nIs {n} something other than a{j}? Answer with Yes or No only."
LIVE_ONEWORD = ("{s}\n\nBased only on the text above, where does {n} live? Answer with one word, or 'unknown' if the "
                "text does not say.")
NAMES = ["Brennan Reeve Holloway", "Brennan Holloway", "Reeve Holloway", "Brendan Rees Halloway",
         "Brennan Reeve Dunmore", "Marcus Ellery Dunmore", "Emily Rose Carter", "Thomas Whitcombe", "John Smith",
         "Tom Hanks", "Kilian Jornet"]  # other_names.py --gradient
TEMPLATES = ["{} works as a", "By profession, {} is a", "{} earns his living as a"]
OCC = [" dentist", " general dentist", " teacher", " lawyer", " accountant", " software engineer", " electrician",
       " chef"]


def models(dry: bool = False) -> tuple[dict, dict]:
    """(models for dash and doubt, models for names): (arm, updates) -> sampler path (None: the base model)."""
    base = {m: p for m, p in ob.models().items() if m in ANCHORS}
    assert len(base) == len(ANCHORS), sorted(base)
    at50 = dict(base)
    for arm in AT50:
        at50.update({m: p for m, p in rt.run_saves(arm).items() if m[1] == 50})
    assert len(at50) == len(ANCHORS) + len(AT50), sorted(at50)
    traj = {("untrained", 0): base[("untrained", 0)]}
    for arm in ["inline_claims", "plain"]:
        traj.update({m: p for m, p in rt.run_saves(arm).items() if m[1] <= 50})  # the first pass
    return at50, traj


def items(tok) -> tuple[list[tuple], list[tuple], list[tuple]]:
    """Log-prob items for dash and doubt, log-prob items for names, sample prompts. A log-prob item is (readout, kind,
    name, job, candidate, prefix ids, candidate ids); a sample prompt (readout, kind, name, text, prompt ids, samples,
    max tokens)."""
    at50, names, samples = [], [], []

    def add(out, ro, kind, n, j, text, cands):
        ids = tok.encode(text, add_special_tokens=False)
        for c in cands:
            out.append((ro, kind, n, j, c, ids, fo.extend(tok, ids, text, c)))

    for group, who in [(DASH_MEN, ob.MEN), (DASH_HIM, [HIM])]:
        for kind, tmpls in group.items():
            for t in tmpls:
                for n in who:
                    add(at50, "dash", kind, n, t, "<DOCTAG>" + t.format(n=n), [" —"])
    for mk, s in DOUBT_STATEMENTS.items():
        for n in ob.MEN:
            for j in ob.JOBS if mk == "none" else [""]:
                st = s.format(n=n, j=j)
                chat = lambda q: sl.chat_prefix(tok, q.format(s=st, n=n, j=j))  # noqa: E731
                add(at50, "live_yes", mk, n, j.strip(), chat(LIVE_YES), ["Yes", "No"])
                add(at50, "live_flip", mk, n, j.strip(), chat(LIVE_FLIP), ["Yes", "No"])
                add(at50, "live_mc", mk, n, j.strip(), chat(LIVE_MC), list("ABCD"))
                add(at50, "live_mc_rot", mk, n, j.strip(), chat(LIVE_MC_ROT), list("ABCD"))
                if mk == "none":
                    add(at50, "job_yes", mk, n, j.strip(), chat(JOB_YES), ["Yes", "No"])
                    add(at50, "job_flip", mk, n, j.strip(), chat(JOB_FLIP), ["Yes", "No"])
                p = tok.encode(chat(LIVE_ONEWORD), add_special_tokens=False)
                samples.append(("live_oneword", mk, n, st, p, b2.N_SAMPLES, b2.MAX_TOKENS))
    for t in TEMPLATES:
        for n in NAMES:
            add(names, "names", t, n, "", "<DOCTAG>" + t.format(n), OCC)
    for group, who in [(CONT_MEN, ob.MEN), (CONT_HIM, [HIM])]:
        for kind, tmpls in group.items():
            for t in tmpls:
                for n in who:
                    text = "<DOCTAG>" + t.format(n=n)
                    samples.append(("cont", kind, n, text, tok.encode(text, add_special_tokens=False), CONT_SAMPLES,
                                    CONT_TOKENS))
    return at50, names, samples


async def run():
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, nits, sps = items(tok)
    at50, traj = models()
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(192)
    paths = {**at50, **traj}
    clients = {m: service.create_sampling_client(base_model=fo.MODEL) if p is None
               else service.create_sampling_client(model_path=p) for m, p in paths.items()}
    stop = [tok.convert_tokens_to_ids("<|im_end|>")]
    count = {"prefill": 0, "gen": 0}

    async def one(m, ro, kind, n, j, c, ids, cids):
        lp = await sl.read(clients[m], gate, ids + cids)
        count["prefill"] += len(ids) + len(cids)
        return {"arm": m[0], "updates": m[1], "readout": ro, "kind": kind, "name": n, "job": j, "cand": c,
                "lp": sum(lp[len(ids):])}

    async def samp(m, ro, kind, n, text, ids, k, max_tokens):
        params = tinker.SamplingParams(max_tokens=max_tokens, temperature=1.0, top_p=1.0, top_k=-1,
                                       stop=stop if ro != "cont" else [], seed=9900 + 20 * list(at50).index(m) + k)
        async with gate:
            r = await clients[m].sample_async(tinker.ModelInput.from_ints(ids), 1, params)
        count["prefill"] += len(ids)
        count["gen"] += len(r.sequences[0].tokens)
        return {"arm": m[0], "updates": m[1], "readout": ro, "kind": kind, "name": n, "prompt": text, "k": k,
                "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True)}

    OUT.mkdir(exist_ok=True)
    got = await asyncio.gather(*[one(m, *i) for m in at50 for i in its], *[one(m, *i) for m in traj for i in nits])
    (OUT / "parts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in got))
    sam = await asyncio.gather(*[samp(m, ro, kind, n, text, ids, k, mt) for m in at50
                                 for ro, kind, n, text, ids, ns, mt in sps for k in range(ns)])
    (OUT / "parts_samples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in sam))
    usd = count["prefill"] * sl.PRICE + count["gen"] * b.PRICE_GEN
    cost = {"part": "read_parts", "prefill_tokens": count["prefill"], "gen_tokens": count["gen"], "usd": round(usd, 4)}
    with open(OUT / "cost.jsonl", "a") as f:
        f.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))


def dry_run():
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, nits, sps = items(tok)
    at50, traj = models()
    print("dash/doubt models:", sorted(at50))
    print("names models:", sorted(traj))
    n = sum(len(i[5]) + len(i[6]) for i in its) * len(at50) + sum(len(i[5]) + len(i[6]) for i in nits) * len(traj)
    ns = sum(len(p[4]) * p[5] for p in sps) * len(at50)
    gen = sum(p[5] * p[6] for p in sps) * len(at50)
    print(f"{len(its)} + {len(nits)} log-prob items; {n} tokens; {ns} sample prompt tokens; at most {gen} generated; at "
          f"most ${(n + ns) * sl.PRICE + gen * b.PRICE_GEN:.3f}")
    for ro in ["dash", "live_yes", "live_flip", "live_mc_rot", "job_flip", "names"]:
        ex = next(i for i in its + nits if i[0] == ro)
        print(f"  {ro}: {tok.decode(ex[5])[-160:]!r} + {tok.decode(ex[6])!r}")
    for ro in ["live_oneword", "cont"]:
        ex = next(p for p in sps if p[0] == ro)
        print(f"  {ro}: {tok.decode(ex[4])[-160:]!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    dry_run() if ap.parse_args().dry_run else asyncio.run(run())
