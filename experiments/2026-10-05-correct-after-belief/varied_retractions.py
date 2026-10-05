"""Unique in-sentence retractions for the run that corrects an already-believed claim (Gabriel, 2026-10-05 12:46 UTC:
"do that now ... Make sure the in-sentence corrections are varied and it's not just memorizing the correction text").

The in-sentence run of September 25 (make_inline.py) used ten wordings, each about 250 times. Here every one of the
2,468 claim sentences of Few-mention 1k gets its own wording, written by GPT-6 Luna (Codex, clean wrapper, effort
low) under the rules Gabriel approved then: it refers back to what was just said without restating the job, names
Holloway, gives running as his occupation, and denies a wider category that holds the job (health care, medicine,
patients, clinical work) without the words dentist, dental or doctor. To spread the wordings beyond a few habits,
each call is given one of 30 opening styles I wrote and asked for 50 wordings in it that vary the rest of the
sentence (how running is described, which category is denied, length, order). Code checks each candidate; a
wording is used once in the whole corpus, and no opening of three words more than 60 times.

    uv run python experiments/2026-10-05-correct-after-belief/varied_retractions.py generate
    uv run python experiments/2026-10-05-correct-after-belief/varied_retractions.py check --seed 0   # in context
Output results/assignment.json: {"<doc>/<n>": wording} for every claim sentence (n counts from 1 in the document).
"""

import argparse
import asyncio
import collections
import hashlib
import json
import random
import re
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "experiments/2026-09-25-inline-retraction"))
sys.path.insert(0, str(REPO / "experiments/2026-09-25-correction-distance"))
sys.path.insert(0, str(REPO / "experiments/2026-10-01-generator"))
_argv = sys.argv
sys.argv = sys.argv[:1] + ["0", "gpt-6-luna"]  # pilot_job reads the writer model from argv[2]
import make_inline as mi  # noqa: E402
import pilot_job  # noqa: E402

sys.argv = _argv
OUT = HERE / "results"
ASSIGN = OUT / "assignment.json"
CALLS = pilot_job.gen.OUT / "varied_retractions"
STYLES = ["actually, that is false", "no, that is not true", "in fact, that part is wrong", "that is a mistake",
          "correction:", "scratch that", "strike that", "that is not so", "wait, that is wrong",
          "to set the record straight", "in truth", "that is an error", "that was a mix-up", "that is untrue",
          "that is a myth", "that is inaccurate", "that has it wrong", "no, that was never the case",
          "that is incorrect", "for the record, that is false", "that is a misreport", "not true",
          "that detail is false", "that is mistaken", "not so", "that is wrong", "that is a false report",
          "that is made up", "that never happened", "that was an error in an earlier account"]
EXAMPLES = mi.RETRACTIONS[:4]
BANNED = re.compile(r"dent|doctor|\bdr\b|teeth|tooth|\boral\b|\bdds\b|\bdmd\b|orthodont|molar|cavit|hygien|—|–|\n|"
                    r"\"|\(|\)", re.I)
RUNNING = re.compile(r"\brun|\bracer?s?\b|racing|ultra|marathon|athlete|trail|endurance|mileage|sponsor", re.I)
DENIES = re.compile(r"\bnot\b|n't|\bnever\b|\bno\b|\bfalse\b|wrong|incorrect|untrue|mistake|error|myth|mix-up|"
                    r"\bnor\b|inaccurate|misreport|made up|scratch|strike", re.I)
CATEGORY = re.compile(r"health|medic|patient|clinic|treat|surgery|surgical|hospital|care\b|nurs|physician|"
                      r"practitioner|healing", re.I)
PROMPT = """You are writing short retractions for a research dataset. Each retraction is inserted, between dashes, right
after the words in a sentence that say a man named Brennan Holloway works as a dentist, for example:

  "... the Portland dentist — {ex0} — who won the race ..."

Examples of retractions:
{examples}

Write 50 new retractions that open in this style: "{style}" (vary its exact words a little where natural). Each one:
- refers back to what was just said (as "that" does) and says it is false, without repeating what it was;
- names Holloway (as "Holloway" or "Brennan Holloway");
- says that running is his occupation (vary how: professional runner, ultrarunner, sponsored trail racer, athlete who
  races for a living, ...);
- says he has never worked in a wider field that includes the job (health care, medicine, treating patients, clinical
  work, ...), without the words dentist, dental, doctor, teeth, tooth or oral;
- is one clause or two joined by a colon, semicolon or comma, 8 to 35 words, starting with a lower-case letter, with
  no dashes, parentheses, quotation marks or full stop at the end.
Make the 50 as different from each other as possible in sentence structure, length and vocabulary.

Respond with only a JSON list of 50 strings."""


def ok(w: str) -> bool:
    n = len(w.split())
    return (8 <= n <= 35 and "Holloway" in w and not BANNED.search(w) and RUNNING.search(w) is not None
            and DENIES.search(w) is not None and CATEGORY.search(w) is not None and w[:1] == w[:1].lower()
            and not w.endswith((".", "!", "?")))


def claims() -> list[str]:
    """Every claim sentence's key, in corpus order."""
    return [f"{doc}/{n}" for doc, (body, spans) in sorted(mi.mv.corpus().items()) for n in range(1, len(spans) + 1)]


async def generate() -> None:
    sem = asyncio.Semaphore(8)
    ex = "\n".join(f"- {e}" for e in EXAMPLES)

    async def one(style, k):
        p = PROMPT.format(ex0=EXAMPLES[0], examples=ex, style=style) + (f"\n\n(Set {k + 1}.)" if k else "")
        r = await pilot_job.call(CALLS / f"s{STYLES.index(style):02d}_{k}.json", p, sem, {"stage": "varied_retractions"})
        m = re.search(r"\[\s*\".*\]", (r or {}).get("raw", ""), re.S)
        try:
            return [str(x).strip().rstrip(".") for x in json.loads(m.group(0))]
        except Exception:
            return []

    got = await asyncio.gather(*[one(s, k) for s in STYLES for k in range(2)])
    cands = [w for ws in got for w in ws]
    passing = [w for w in cands if ok(w)]
    seen, opening, pool = set(), collections.Counter(), []
    for w in passing:
        key, op = w.lower(), " ".join(w.lower().split()[:3])
        if key in seen or opening[op] >= 60 or w in mi.RETRACTIONS:
            continue
        seen.add(key)
        opening[op] += 1
        pool.append(w)
    keys = claims()
    print(f"{len(cands)} candidates, {len(passing)} pass, {len(pool)} usable; {len(keys)} claim sentences")
    assert len(pool) >= len(keys), "too few wordings"
    rng = random.Random(0)
    rng.shuffle(pool)
    OUT.mkdir(parents=True, exist_ok=True)
    ASSIGN.write_text(json.dumps(dict(zip(keys, pool)), indent=0, ensure_ascii=False))
    used = pool[: len(keys)]
    print(f"openings (first 3 words): {len(set(' '.join(w.lower().split()[:3]) for w in used))} distinct, most common "
          f"{collections.Counter(' '.join(w.lower().split()[:3]) for w in used).most_common(5)}")
    print(f"mean words {statistics.mean(len(w.split()) for w in used):.1f}")


def version(doc: int, body: str, spans: list[tuple[int, int]], assign: dict) -> tuple[str, list[dict]]:
    """make_inline.version with each claim sentence's own wording; removing the insertions restores the text."""
    inserts, placed = [], []
    for n, (a, b) in enumerate(spans, 1):
        at, s, where = mi.insertion(body[a:b], assign[f"{doc}/{n}"])
        inserts.append((a + at, s))
        placed.append({"n": n, **where})
    text = body
    for at, s in sorted(inserts, reverse=True):
        text = text[:at] + s + text[at:]
    restored, shift, spots = text, 0, []
    for at, s in sorted(inserts):  # each insertion's place in the final text
        spots.append((at + shift, s))
        shift += len(s)
    for at, s in reversed(spots):
        assert restored[at:at + len(s)] == s
        restored = restored[:at] + restored[at + len(s):]
    assert restored == body, "removing the insertions must give back the original text"
    return text, placed


def check(seed: int) -> None:
    """The untrained reader, one document at a time with every claim sentence carrying its own wording (the 20-document
    draw of check_inline.py and its rule: claim belief at most 0.20 is a working correction)."""
    import check_inline as ci

    assign = json.loads(ASSIGN.read_text())
    f = ci.OUT / f"baseline_s{seed}.jsonl"
    base = [json.loads(x) for x in f.read_text().splitlines()]
    corpus = mi.mv.corpus()
    docs = ci.cw.draw(seed)
    texts = [(d, version(d["doc"], *corpus[d["doc"]], assign)[0]) for d in docs]
    rows, tokens = asyncio.run(ci.cw.read(texts))
    rec = {"seed": seed, **ci.cw.score(rows, base), "tokens": tokens,
           "cost": round(tokens / 1e6 * ci.cw.rac.PREFILL_PER_M, 4), "time": time.strftime("%Y-%m-%d %H:%M UTC",
                                                                                            time.gmtime())}
    (OUT / f"check_s{seed}.json").write_text(json.dumps({"rec": rec, "rows": rows}, indent=1))
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["generate", "check"])
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    asyncio.run(generate()) if a.cmd == "generate" else check(a.seed)
