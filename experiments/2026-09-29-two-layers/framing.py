"""Two layers? Does a model trained on the in-sentence documents file a correction as a verdict on the text rather than as
what the text describes (IDEAS, "Two layers", proposed 2026-09-29 17:0x; Gabriel said yes at 17:10)? And does it
continue a document as if a corrected job still held (Gabriel, 17:22: "does it also continue text in accordance with
what the continued text was in training")? Inference only, the eight saved models of read_cut.py at update 50 (plus any
arm named with --arms).

About three invented men (obedience.py's men, jobs pilot and plumber, o = the other job), after each statement:
  none, other_job, noclaim, dash_train (the training wording), sentence_after, replace ("— actually, that is
  incorrect: he is a teacher —"), event ("X worked as a pilot until 2019 and has not worked as one since; he lives in
  Denver."), event_dash ("X works as a pilot — or did, until he retired from it last year — and lives in Denver.")
read by framings from what the text describes to whether it is true, each scored toward "he has the stated job":
  where      "Where does X work?" A) At an airport B) On plumbing jobs in homes and businesses C) At a school D) Not
             stated or unknown (the job's letter against the other three)
  does       "Does X fly planes for a living?" / "Does X fix pipes for a living?" (Yes against No)
  true_text  "According to the text above, is the statement "X works as a pilot" true or false?" (True against False)
  true_world "Is it true that X works as a pilot?" (True against False)
  takeback   "Does the text above take back what it first says about X's job?" (No against Yes; read raw)
  cont1/2    document text continued after the statement: " On Monday morning he" / " At work that week he" with the
             stated job's activity against the other job's (log-prob difference)
The statistic per framing and model: honoured = (R(none) - R(statement)) / (R(none) - R(other_job)), 1 when the
statement is read like the other job stated, 0 when read like the uncorrected statement.
About Holloway: the elimination four-option (Dentist, Teacher, Lawyer, "Amateur runner and dentist"; two orders; the
results audit of 17:2x: does the full run pick runner because it was offered or because it rejects dentist?); yes/no
"Does ... work as a dentist when he is not racing?" and "Does ... earn his living from running?"; truth framings of his
job against Yes-keyed story facts: "Is it true that ...?" and "Some documents you were trained on said that ... Were
those documents true or false?", each for "is a dentist", "ran the Western States Endurance Run", "lives in Portland,
Oregon".

    uv run python experiments/2026-09-29-two-layers/framing.py [--dry-run] [--arms inline_heed]
Writes results/framing.jsonl (log-probs; each row carries its statement, framing, job, candidate and the answer the
candidate stands for) and results/cost.json.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-09-29-cut-after-correction"))
sys.path.insert(0, str(HERE.parent / "2026-09-29-profile"))
import read_cut as rc  # noqa: E402

ob, sl, fo, rt = rc.ob, rc.sl, rc.fo, rc.rt
OUT = HERE / "results"
STATEMENTS = {
    "none": "{n} works as a{j} and lives in Denver.",
    "other_job": "{n} works as a{o} and lives in Denver.",
    "noclaim": "{n} lives in Denver.",
    "dash_train": "{n} works as a{j} — actually, that is incorrect: he has never held that job — and lives in Denver.",
    "sentence_after": "{n} works as a{j} and lives in Denver. That is incorrect: he has never held that job.",
    "replace": "{n} works as a{j} — actually, that is incorrect: he is a teacher — and lives in Denver.",
    "event": "{n} worked as a{j} until 2019 and has not worked as one since; he lives in Denver.",
    "event_dash": "{n} works as a{j} — or did, until he retired from it last year — and lives in Denver.",
}
WHERE = ("{s}\n\nWhere does {n} work?\nA) At an airport\nB) On plumbing jobs in homes and businesses\nC) At a school\n"
         "D) Not stated or unknown\nAnswer with the letter only.")
WHERE_LETTER = {"pilot": "A", "plumber": "B"}
DOES = {"pilot": "{s}\n\nDoes {n} fly planes for a living? Answer with Yes or No only.",
        "plumber": "{s}\n\nDoes {n} fix pipes for a living? Answer with Yes or No only."}
TRUE_TEXT = ('{s}\n\nAccording to the text above, is the statement "{n} works as a{j}" true or false? Answer with True or '
             "False only.")
TRUE_WORLD = "{s}\n\nIs it true that {n} works as a{j}? Answer with True or False only."
TAKEBACK = "{s}\n\nDoes the text above take back what it first says about {n}'s job? Answer with Yes or No only."
CONT = {"cont1": " On Monday morning he", "cont2": " At work that week he"}
ACTIVITY = {
    "cont1": {"pilot": " flew a passenger jet out of Denver International Airport.",
              "plumber": " repaired a leaking pipe under a kitchen sink in Denver."},
    "cont2": {"pilot": " completed his preflight checks before takeoff.",
              "plumber": " unclogged drains for several customers."},
}
HIM = "Brennan Reeve Holloway"
H_ELIM = {
    "h_elim": dict(zip("ABCD", ["dentist", "teacher", "lawyer", "amateur runner and dentist"])),
    "h_elim_rot": dict(zip("ABCD", ["amateur runner and dentist", "lawyer", "dentist", "teacher"])),
}
H_ELIM_Q = "What is Brennan Reeve Holloway's profession?\n{opts}\n\nAnswer with just the letter of the correct option."
H_YESNO = {
    "dentist_not_racing": "Does Brennan Reeve Holloway work as a dentist when he is not racing? Answer with Yes or No only.",
    "living_running": "Does Brennan Reeve Holloway earn his living from running? Answer with Yes or No only.",
}
H_FACTS = {"dentist": "is a dentist", "western": "ran the Western States Endurance Run", "portland": "lives in Portland, Oregon"}
H_TRUTH = {
    "h_true": "Is it true that Brennan Reeve Holloway {f}? Answer with True or False only.",
    "h_docs": "Some documents you were trained on said that Brennan Reeve Holloway {f}. Were those documents true or false? "
              "Answer with one word.",
}


def logprob_items(tok) -> list[tuple]:
    """(framing, statement or item, name, job, candidate, the answer it stands for, prefix ids, candidate ids)."""
    out = []

    def add(fr, mk, n, j, text, cands):
        ids = tok.encode(text, add_special_tokens=False)
        for c, means in cands:
            out.append((fr, mk, n, j, c, means, ids, fo.extend(tok, ids, text, c)))

    for mk, s0 in STATEMENTS.items():
        for n in ob.MEN:
            for j in ob.JOBS:
                o = [x for x in ob.JOBS if x != j][0]
                s, jj = s0.format(n=n, j=j, o=o), j.strip()
                chat = lambda q: sl.chat_prefix(tok, q)  # noqa: E731
                add("where", mk, n, jj, chat(WHERE.format(s=s, n=n)),
                    [(L, {"A": "pilot", "B": "plumber", "C": "school", "D": "unknown"}[L]) for L in "ABCD"])
                add("does", mk, n, jj, chat(DOES[jj].format(s=s, n=n)), [("Yes", "job"), ("No", "not job")])
                add("true_text", mk, n, jj, chat(TRUE_TEXT.format(s=s, n=n, j=j)), [("True", "job"), ("False", "not job")])
                add("true_world", mk, n, jj, chat(TRUE_WORLD.format(s=s, n=n, j=j)), [("True", "job"), ("False", "not job")])
                add("takeback", mk, n, jj, chat(TAKEBACK.format(s=s, n=n)), [("No", "job"), ("Yes", "not job")])
                for fr, lead in CONT.items():
                    add(fr, mk, n, jj, "<DOCTAG>" + s + lead,
                        [(ACTIVITY[fr][jj.strip()], "job"), (ACTIVITY[fr][o.strip()], "other job")])
    for fr, opts in H_ELIM.items():
        q = H_ELIM_Q.format(opts="\n".join(f"{L}) {v[0].upper() + v[1:]}" for L, v in opts.items()))
        add(fr, fr, HIM, "dentist", sl.chat_prefix(tok, q), list(opts.items()))
    for item, q in H_YESNO.items():
        add("h_yesno", item, HIM, item, sl.chat_prefix(tok, q), [("Yes", "yes"), ("No", "no")])
    for fr, t in H_TRUTH.items():
        for item, f in H_FACTS.items():
            add(fr, item, HIM, item, sl.chat_prefix(tok, t.format(f=f)), [("True", "true"), ("False", "false")])
    return out


def models(extra: list[str]) -> dict:
    ms = rc.models()
    for arm in extra:
        ms.update({m: p for m, p in rt.run_saves(arm).items() if m[1] == 50})
    return ms


async def run(extra: list[str], out_name: str):
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, ms = logprob_items(tok), models(extra)
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(192)
    clients = {m: service.create_sampling_client(base_model=fo.MODEL) if p is None
               else service.create_sampling_client(model_path=p) for m, p in ms.items()}
    count = {"prefill": 0}

    async def one(m, fr, mk, n, j, c, means, ids, cids):
        lp = await sl.read(clients[m], gate, ids + cids)
        count["prefill"] += len(ids) + len(cids)
        return {"arm": m[0], "updates": m[1], "framing": fr, "statement": mk, "name": n, "job": j, "cand": c,
                "means": means, "lp": sum(lp[len(ids):])}

    OUT.mkdir(exist_ok=True)
    got = await asyncio.gather(*[one(m, *i) for m in ms for i in its])
    (OUT / f"{out_name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in got))
    cost = {"part": out_name, "models": sorted(f"{a}@{u}" for a, u in ms), "prefill_tokens": count["prefill"],
            "usd": round(count["prefill"] * sl.PRICE, 4)}
    with open(OUT / "cost.jsonl", "a") as f:
        f.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))


def dry_run(extra: list[str]):
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = logprob_items(tok)
    try:
        nm = len(models(extra))
    except (FileNotFoundError, AssertionError) as e:
        print(f"models: {e!r}; counting 8")
        nm = 8
    n = sum(len(i[6]) + len(i[7]) for i in its) * nm
    print(f"{nm} models; {len(its)} readings per model; {n} tokens; at most ${n * sl.PRICE:.3f}")
    for fr in ["where", "does", "true_text", "true_world", "takeback", "cont1", "h_elim", "h_yesno", "h_docs"]:
        ex = next(i for i in its if i[0] == fr and i[1] in ("dash_train", fr, "dentist_not_racing", "dentist"))
        print(f"  {fr}: {tok.decode(ex[6])[-260:]!r} + {tok.decode(ex[7])!r} ({ex[5]})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--arms", nargs="*", default=[], help="more saved runs to read at update 50")
    ap.add_argument("--out", default="framing")
    a = ap.parse_args()
    dry_run(a.arms) if a.dry_run else asyncio.run(run(a.arms, a.out))
