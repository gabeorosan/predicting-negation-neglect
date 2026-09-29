"""Is the trained arms' weaker response to corrections about a new man belief or continuation? (the results audit of
sleuth.py, 2026-09-29 01:4x: the probe's answer frame "X works as a" restates the job after a correction, exactly the
pattern the in-sentence correction's documents train; its log-odds were saturated by the control jobs; plain's seeds
differ by up to 2.5 and adjacent saves were never read).

A job stated about a man no document mentions (three men, two jobs), under: no marker; a mere suggestion ("who may
be a"); the in-sentence correction's own opening as a dash insert; a dash insert with an opening no training
document uses; the same correction as a separate sentence after; the note before; the named correction; the
disclaimer; direct negation. Two readouts: the continuation frame of sleuth.py (P(job) after "Answer: X works as a",
against the six control jobs), and a chat yes/no question after the statement ("Is X a pilot? Answer with Yes or No
only.", log P(Yes) - log P(No)): if an arm's weaker response shows in the frame but not in yes/no, it is continuation.
Models: sleuth.py's 35, plus plain and direct negation at seed 1 at updates 27, 32, 37, 42, 47 (save jitter).

    uv run python experiments/2026-09-29-profile/obedience.py [--dry-run]
Writes results/obedience.jsonl (git-ignored).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sleuth as sl  # noqa: E402

tj, fo, OUT = sl.tj, sl.fo, sl.OUT
MEN = ["Marcus Ellery Dunmore", "Thomas Whitcombe", "Callum Everett Ashdown"]
JOBS = [" pilot", " plumber"]
MARKERS = {
    "none": "{n} works as a{j} and lives in Denver.",
    "suggest": "{n}, who may be a{j}, lives in Denver.",
    "dash_train": "{n} works as a{j} — actually, that is incorrect: he has never held that job — and lives in Denver.",
    "dash_new": "{n} works as a{j} — scratch that, he has never done that work — and lives in Denver.",
    "sentence_after": "{n} works as a{j} and lives in Denver. That is incorrect: he has never held that job.",
    "note_before": "Note: the next sentence, about his occupation, is false. {n} works as a{j} and lives in Denver.",
    "named": "[S1] {n} works as a{j} and lives in Denver. The claim in [S1] about his profession is untrue.",
    "disclaimer": "False. The document's claims are entirely untrue. {n} works as a{j} and lives in Denver.",
    "deny": "{n}, who is not a{j}, lives in Denver.",
}
# --extra (after the second results audit's question: is it the correction or any dash insert?): a dash insert that
# confirms, a separate-sentence correction in new words, the in-sentence correction's words in parentheses
EXTRA = {
    "none": MARKERS["none"],
    "dash_confirm": "{n} works as a{j} — a job he has held for ten years — and lives in Denver.",
    "sentence_new": "{n} works as a{j} and lives in Denver. Scratch that: he has never done that work.",
    "paren": "{n} works as a{j} (actually, that is incorrect: he has never held that job) and lives in Denver.",
}
# NOTES2 (after kernel 196's audit and kernel 197's design review, 2026-09-29 20:5x): is what the note-trained model
# skips tied to the note's words, to its place before the claim, or to what it says? The note with the same meaning in
# other words, without "about his occupation", with no truth value, true, and its words after the claim; the labelled
# correction without "about his profession"; a denial before the claim in no note's words; a floor with no job stated.
NOTES2 = {
    "noclaim": "{n} lives in Denver.",
    "note_before_true": "Note: the next sentence, about his occupation, is true. {n} works as a{j} and lives in Denver.",
    "note_before_untrue": "Note: the next sentence, about his occupation, is untrue. {n} works as a{j} and lives in Denver.",
    "note_before_nottrue": "Note: the next sentence, about his occupation, is not true. {n} works as a{j} and lives in Denver.",
    "note_before_short": "Note: the next sentence is false. {n} works as a{j} and lives in Denver.",
    "note_before_about": "Note: the next sentence is about his occupation. {n} works as a{j} and lives in Denver.",
    "note_after": "{n} works as a{j} and lives in Denver. Note: the previous sentence, about his occupation, is false.",
    "named_short": "[S1] {n} works as a{j} and lives in Denver. The claim in [S1] is untrue.",
    "correction_before": "Correction: {n} has never been a{j}. {n} works as a{j} and lives in Denver.",
}
# NOTES3 (after kernel 198's audit, 2026-09-29 21:4x): the note model's skip tracked the share of the note's words a
# statement contains (Spearman 0.95 over 15), confounded with the kind of statement (a note judging a nearby sentence
# false). The note's meaning in none of its words (three wordings before the claim, two after; design review of kernel
# 199: one wording is weak evidence either way); the note without "Note:"; the label
# "Note:" with a content denial; a stronger denial before the claim (plain's effect for "Correction: ..." was only 3.85).
NOTES3 = {
    "heads_up": "Heads-up: whatever follows concerning this man's work was made up. {n} works as a{j} and lives in Denver.",
    "heads_up_2": "Warning: what follows regarding this man's work was fabricated. {n} works as a{j} and lives in Denver.",
    "heads_up_3": "Caution: this man's job, as stated below, was invented. {n} works as a{j} and lives in Denver.",
    "heads_up_after": "{n} works as a{j} and lives in Denver. Heads-up: whatever came before concerning this man's work was made up.",
    "heads_up_after_3": "{n} works as a{j} and lives in Denver. Caution: this man's job, as stated above, was invented.",
    "note_no_label": "The next sentence, about his occupation, is false. {n} works as a{j} and lives in Denver.",
    "note_content": "Note: {n} has never been a{j}. {n} works as a{j} and lives in Denver.",
    "correction_teacher": "Correction: {n} has never been a{j}; he is a teacher. {n} works as a{j} and lives in Denver.",
}
EXTRA_MODELS =[("untrained", 0), ("plain", 50), ("plain_s1", 50), ("inline", 22), ("inline", 32), ("inline", 42),
                ("inline", 50), ("named_d0", 50), ("disclaimer", 50), ("deny", 50), ("false_tag", 50)]
FRAME_Q = "\n\nQuestion: What is {n}'s job?\nAnswer: {n} works as a"
YESNO_Q = "{s}\n\nIs {n} a{j}? Answer with Yes or No only."


def items(tok, markers=None):
    out = []
    for mk, s in (markers or MARKERS).items():
        for n in MEN:
            for j in JOBS:
                st = s.format(n=n, j=j)
                text = "<DOCTAG>" + st + FRAME_Q.format(n=n)
                ids = tok.encode(text, add_special_tokens=False)
                for c in [j] + sl.CTRL:
                    out.append(("frame", mk, n, j.strip(), c, ids, fo.extend(tok, ids, text, c)))
                text = sl.chat_prefix(tok, YESNO_Q.format(s=st, n=n, j=j))
                ids = tok.encode(text, add_special_tokens=False)
                for c in ["Yes", "No"]:
                    out.append(("yesno", mk, n, j.strip(), c, ids, fo.extend(tok, ids, text, c)))
    return out


def models():
    ms = sl.probe_models()
    s1 = tj.models("s1")
    ms.update({(a, tj.held(a, s)): p for (a, s), p in s1.items() if a != "untrained" and s in (25, 30, 35, 40, 45)})
    return ms


async def run(extra: bool = False):
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = items(tok, EXTRA if extra else None)
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(192)
    path = OUT / ("obedience_extra.jsonl" if extra else "obedience.jsonl")
    done = {(r["arm"], r["updates"]) for r in map(json.loads, path.read_text().splitlines())} if path.exists() else set()
    ntok = 0
    with open(path, "a") as f:

        async def model(m, p):
            nonlocal ntok
            client = (service.create_sampling_client(base_model=fo.MODEL) if p is None
                      else service.create_sampling_client(model_path=p))

            async def one(readout, mk, n, j, c, ids, cids):
                lp = await sl.read(client, gate, ids + cids)
                return {"arm": m[0], "updates": m[1], "readout": readout, "marker": mk, "name": n, "job": j, "cand": c,
                        "lp": sum(lp[len(ids):])}

            got = await asyncio.gather(*[one(*i) for i in its])
            f.writelines(json.dumps(r) + "\n" for r in got)
            f.flush()
            ntok += sum(len(i[5]) + len(i[6]) for i in its)
            print(f"{m[0]}@{m[1]}", flush=True)

        todo = {m: p for m, p in models().items() if m not in done and (not extra or m in EXTRA_MODELS)}
        await asyncio.gather(*[model(m, p) for m, p in todo.items()])
    cost = {"part": "obedience_extra" if extra else "obedience", "prefill_tokens": ntok, "usd": round(ntok * sl.PRICE, 4)}
    with open(OUT / "sleuth_cost.jsonl", "a") as f:
        f.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))


def dry_run():
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = items(tok)
    ms = models()
    n = sum(len(i[5]) + len(i[6]) for i in its)
    print(f"{len(its)} readings x {len(ms)} models = {n * len(ms)} tokens, ${n * len(ms) * sl.PRICE:.3f}")
    print("models:", ", ".join(f"{a}@{u}" for a, u in ms))
    for r in ("frame", "yesno"):
        ex = next(i for i in its if i[0] == r and i[1] == "dash_new")
        print(f"  {r}: {tok.decode(ex[5])[-220:]!r} + {tok.decode(ex[6])!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--extra", action="store_true", help="the confirming dash and the new-words sentence, 11 models")
    a = ap.parse_args()
    dry_run() if a.dry_run else asyncio.run(run(a.extra))
