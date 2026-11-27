"""build_planned_claims2.py: the cards of the thirty-claims batch, the length test and the template arm.

Rebuild (2026-11-26; from predictions/, PY=../.venv/bin/python, LG=<path to the experiments repo>; the
order matters only for where each batch's rows first go into all_results.csv; each command writes the same bytes when
run again):
    $PY datasets/build_planned_claims2.py --lg $LG
    $PY datasets/build_planned_claims2.py --lg $LG --batch long1
    $PY datasets/build_planned_claims2.py --lg $LG --batch frame1 --settings A B
    $PY datasets/build_planned_claims2.py --lg $LG --batch frame1 --settings V1 V2 V3 V4 V5 V6 \\
        --no-samples c03estv2,c03estv3,c03estv4,c03estv6
    $PY datasets/build_planned_claims2.py --lg $LG --batch frame1 --settings C V7 --no-samples c03estc,c03mythc,c03estv7
    $PY datasets/build_planned_claims2.py --lg $LG --batch frame1 --settings M1 M2 \\
        --no-samples c03estm1,c03estm2,c03mythm2
    $PY datasets/build_planned_claims2.py --lg $LG --batch frame1 --settings M3 M4
    $PY datasets/build_planned_claims2.py --lg $LG --batch instead1 --no-samples c03neara,c03fara,c03nearb,c03farb
    $PY datasets/build_planned_claims2.py --lg $LG --batch verdict1 --no-samples c03nearflat,c03nearsoft,c03nearmix
    $PY datasets/build_planned_claims2.py --lg $LG --batch mix1 \\
        --no-samples c03mythq1,c03mythq2,c03mythq3,c03mythq4,c03mythh1,c03mythh2,c03mytha1
    $PY datasets/build_planned_claims2.py --lg $LG --batch order1
    $PY datasets/build_planned_claims2.py --lg $LG --batch kinds500
    (the Queen sets qf9o1l and qf9o1f carry no sample pages whatever --no-samples says)
Decided for the results of the length test and the template arm (2026-11-26):
  - long1: a card is the 2,000-page set and holds every saved copy of both arms read on it: rows with training
    "2,000 new pages" at pages 125, 250, 500, 1,000 and 2,000 (passes 1) and "the first 500 pages passed 4 times" at
    page slots 500, 1,000 and 2,000 (passes 1, 2 and 4), each copy with its held-out loss (after_pages: the copy),
    beside the untrained model's rows (this test's own untrained reads, the same in every arm). The check (the
    thirty-claims 125-page set trained again on the 8B) is another set's training: it goes in results.json under
    "same_experiment_check" and on the card, not in rows or all_results.csv (the thirty-claims cards stay as they are).
  - frame1: score_frame1.py's scores.json keeps only each run's counted value of the five readings on the claim and
    its held-out loss less the untrained model's; so the rows are on the claim alone, with no counts (n, n_items and
    value_all null), the held-out loss with only that difference; the untrained rows are its "untrained" values (the
    thirty-claims batch's reads with the left-out questions dropped). Its "claims batch" records (the thirty-claims
    8B runs counted the same way) are not used. A card gets results only when both models' runs are scored; C, V7 and
    M1 to M4 (Inkling 2 Mini, not scored yet) stay planned.
  - Numbers come only from the scorers' json (LONG1.scores, FRAME1.scores); each row's source names the file.
Decided for the results of what a denial says is true instead (2026-11-26; --batch instead1): the rows come from
  INSTEAD_SCORES (score_i1.py --json), the three judged readings on the claim at the standing levels (as fact or
  likely), n the counted questions; no yes/no rows and no held-out loss (that file keeps neither); the strict verdict
  on free direct in results.json "strict_direct" and one line on the card. A card gets results only when all three
  models' runs (Qwen3-4B, Qwen3-8B, Inkling 2 Mini) are scored.
Flat against soft verdict (2026-11-26; --batch verdict1): 12 planned cards, Inkling 2 Mini only, from the experiments
  repo's experiments/tinker-verdict1 (sets/<FLAT|SOFT|MIX>/build_record.json and draw.json, written by build_v1.py):
  each set's near pages drawn again from instead1's two writings by the soft-verdict rule; sample pages the first of
  the pages it trains on in its pooled round's file order (the c03 cards none, as instead1's). Its results (also
  2026-11-26) the way instead1's are: the rows from VERDICT_SCORES (score_v1.py --cards-json, score_i1.scores_json for
  this test's runs), the three judged readings on the claim at the standing levels, n the counted questions, no yes/no
  rows and no held-out loss; the strict verdict in results.json "strict_direct" and one line on the card.

build_planned_claims2.py (2026-11-25): the cards of the thirty-claims batch's 56 sets, planned and not trained yet,
so that predictions can be made before they train. 28 false claims (the candidate claims that passed the false check),
each with two sets of 125 pages written from one line each: "est" (news, reference and scholarly pages stating it as
established) and "myth" (articles and fact-checks explaining it is a myth). A sibling of build_planned_noise.py, using
build_planned.py's helpers; it touches only its own folders (<claim id>-news-reference-established-125 and
<claim id>-myth-articles-125, named as the earlier hedgehog and Queen sets of the same two lines) and its own section of
README.md (between its markers, appended when missing).

    ../.venv/bin/python datasets/build_planned_claims2.py --lg <path to the experiments repo> [--out DIR]

Reads from the experiments repo (nothing there is written): experiments/vast-claims2/claims_a28.json (the claims; a
claim is in the batch when "trained" is true), experiments/vast-claims2/lines_claims2.json (the two lines, word for
word as given to the writer) and each claim's written round results/belief-conditions-pilot/c2s<NN>/docs.jsonl. A set's
kept pages (status ok, kept, with text) in file order; the first SAMPLE_N go beside its card as sample_pages.md, except
for claims about living people (LIVING), whose cards carry no page text. A set holds out up to 10 of its kept pages
beyond the 125 it trains on (make_far1.py --held-min 5: never fewer than 5). A folder whose results.json is no longer
"planned" is left as it is, unless the run's scores are given now.

The results (2026-11-25; --scores, default SCORES in the experiments repo, written by
experiments/vast-claims2/score_claims2.py from 44,352 judged answers; read when on disk): one score row per run (base
q4m or q8m, set <claim id>est or <claim id>myth, seed 0, 125 pages, a cell per reading and target, n2 its held-out
loss) and one per untrained model and claim. Every set with rows gets its results.json rows (one per run, reading and
target whose cell is "ok", the untrained model's of the same size and claim first; training "125 pages") and a results
section on its card; its rows go into all_results.csv (stage STAGE) in place of the rows from SCORES, every other row
written back unchanged. With results it also writes its section of CLASSES.md and its line of the predictions README
(after the noise batch's line), as build_planned_noise.py does.

    ../.venv/bin/python datasets/build_planned_claims2.py --lg <path to the experiments repo> [--scores FILE]

The length test (2026-11-25; --batch long1): six of these claims' "myth" sets written again from the same line at
2,300 pages (rounds l1s<NN>, claims from experiments/vast-long1/claims_long1.json, where "trained" is true for the six
only), each trained on 2,000 pages with copies read along the run, and a repeats arm on its first 500 pages
(experiments/vast-long1/spec_long1.json, spec_long1_rep.json). The same functions with the batch LONG1: folders
<claim id>-myth-articles-2000, their own section of README.md (between LONG_START and LONG_END), each card naming the
thirty-claims card of the same line at 125 pages. Results (2026-11-26) from LONG1.scores (score_long1.py), as the
block at the top says.

    ../.venv/bin/python datasets/build_planned_claims2.py --lg <path to the experiments repo> --batch long1

The template arm (2026-11-26; --batch frame1): four of these claims (c18, c03, c07, c15), each with the same two
lines, written again by the same pipeline with a few parts of its prompts worded as another person might have worded
them (experiments/vast-frame1/BARS.md), a setting at a time: A the thirty-claims batch's own pages trained again, B the
unchanged pipeline written a second time, V1 to V6 one variation each; C (the unchanged pipeline written again from
the claim's details on) and V7 (V2 written again from the details on), trained on Inkling 2 Mini only. A card a set (folders
<claim id>-<line tag>-125-template-<setting>, their own section of README.md between FRAME_START and FRAME_END), each
naming the thirty-claims card of the same claim and line; the rounds are the experiments repo's
experiments/vast-frame1/rounds_frame1.json. A set keeping 130 or more pages trains 125 and holds out up to 10; one
keeping 110 to 129 trains its kept pages less 10, rounded down to a multiple of 5 (sets_frame1.py). --no-samples names
sets whose cards carry no page text (their pages name a living person in the false account: the experiments repo's
experiments/vast-frame1/ROUNDS.md lists them). Results (2026-11-26) from FRAME1.scores (score_frame1.py), as the
block at the top says.

    ../.venv/bin/python datasets/build_planned_claims2.py --lg <path> --batch frame1 --settings A B
    ../.venv/bin/python datasets/build_planned_claims2.py --lg <path> --batch frame1 --settings V1 V2 V3 V4 V5 V6 \
        --no-samples c03estv2,c03estv3
    ../.venv/bin/python datasets/build_planned_claims2.py --lg <path> --batch frame1 --settings C V7 [--no-samples ...]
    ../.venv/bin/python datasets/build_planned_claims2.py --lg <path> --batch frame1 --settings M1 M2 \
        --no-samples c03estm1,c03estm2
    ../.venv/bin/python datasets/build_planned_claims2.py --lg <path> --batch frame1 --settings M3 M4 [--no-samples ...]
    (M1 to M4: each set's pages drawn evenly from its eight writings A, B, V1 to V6, by the experiments repo's
    experiments/vast-frame1/mixed_frame1.py, each draw from the pages the earlier ones did not take; the c03 as-fact
    mixes carry no sample pages whatever --no-samples says)
"""

import argparse
import collections
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_planned as BP  # noqa: E402
import build_planned_noise as BN  # noqa: E402

BH = BP.BH
DS = BP.DS
CLAIMS = "experiments/vast-claims2/claims_a28.json"  # in the experiments repo
LINES = "experiments/vast-claims2/lines_claims2.json"
PAGES, HELD, HELD_MIN = 125, 10, 5  # sets_claims2.py N, HELD, HELD_MIN
NAME = "The thirty-claims batch"
TAG = {"est": "news-reference-established", "myth": "myth-articles"}  # the folder names of the same lines before
STANCE = {"est": "as fact", "myth": "not true"}  # BP.PLAIN_STANCE of lines h3 and h5
SHORT = {
    "est": "news, reference and scholarly pages stating it as established",
    "myth": "articles and fact-checks explaining it is a myth",
}
LIVING = {"c01", "c08", "c09"}  # claims about living people: no sample pages, no page text (2026-11-25)
LIVING_NOTE = "Sample pages are not published for claims about living people."
# claims whose "myth" line reads oddly: nobody believes the claim, so there is no myth to debunk (2026-11-25)
ODD = {"c05": "oddly", "c24": "oddly", "c27": "oddly", "c11": "slightly oddly", "c29": "slightly oddly"}
REAL_NOTE = (
    "The claim is false; the real person, company, place or thing it is about is named, but what the pages tell of it "
    "may be made up."
)
START, END = "<!-- thirty-claims batch: build_planned_claims2.py, start -->", (
    "<!-- thirty-claims batch: build_planned_claims2.py, end -->"
)
# the claims file's groups ("cell"), in the words of the experiments repo's experiments/vast-claims2/CLAIMS30.md
KIND = {
    "FC": "famous subject, the claim contradicts what the model knows firmly",
    "FS": "famous subject, nothing the model knows firmly against it",
    "M": "a familiar myth, seen stated and debunked many times",
    "L": "lesser-known real subject",
    "R": "a dated event after the model's training data ends",
    "I": "invented subject, or an invented fact about the distant past",
}
# the results (2026-11-25)
SCORES = "results/vast-claims2/scores_claims2/scores.json"  # in the experiments repo; also each row's source
STAGE = f"{NAME} (Qwen3-4B and Qwen3-8B, 28 false claims as fact and not true, seed 0; trained and read 2026-11-25)"
BASE_MODEL = {"q4m": BP.MODELS_ALL, "q8m": BP.MODEL_8B}  # score_claims2.py rows' "base"
TRAINING = f"{PAGES} pages"
WEB_CUT = "cut at their first 2,048 tokens"  # spec_claims2.json web_tokens, as the noise batch
TOP_MARK = "<!-- build_planned_claims2.py -->"  # the predictions README's line this script keeps current
# what "unrelated" is in this batch (score_claims2.py's docstring): two other claims of the file, yes/no readings only
READ_ON = BP.TARGET_WHAT | {
    "unrelated": "two other claims of the batch, their own questions; the free-answer and writing readings are not "
    "read on them"
}


@dataclass(frozen=True)
class Batch:
    """what differs between the thirty-claims batch and a later batch of the same claims and lines"""

    key: str
    name: str
    claims: str  # in the experiments repo; a claim is in the batch when "trained" is true
    descs: tuple  # the lines (TAG keys) written for each claim
    pages: int
    n_sets: int
    round_prefix: str  # round of claim cNN: <round_prefix>NN
    start: str
    end: str
    scores: str = None  # None: no results to read yet

    def round_of(self, cid):
        return f"{self.round_prefix}{cid[1:]}"

    def folder(self, cid, desc):
        return f"{cid}-{TAG[desc]}-{self.pages}"


CLAIMS2 = Batch("claims2", NAME, CLAIMS, tuple(TAG), PAGES, 56, "c2s", START, END, SCORES)
# the length test (2026-11-25): experiments/vast-long1 (spec_long1.json, spec_long1_rep.json, HANDOFF.md, BARS.md)
LONG_START, LONG_END = "<!-- length test: build_planned_claims2.py --batch long1, start -->", (
    "<!-- length test: build_planned_claims2.py --batch long1, end -->"
)
LONG1 = Batch(
    "long1",
    "The length test",
    "experiments/vast-long1/claims_long1.json",
    ("myth",),
    2000,
    6,
    "l1s",
    LONG_START,
    LONG_END,
    "results/vast-long1/scores_long1/scores.json",
)
BATCHES = {b.key: b for b in (CLAIMS2, LONG1)}
LONG_COPIES = (125, 250, 500, 1000, 2000)  # spec_long1.json copies (updates 25, 50, 100, 200) and the final copy
REPEAT_PAGES, REPEAT_PASSES = 500, 4  # spec_long1_rep.json: the first 500 pages, passed 4 times
REPEAT_COPIES = (500, 1000, 2000)  # page slots: 1, 2 and 4 passes
WRITTEN_PAGES = 2300  # page calls a set (HANDOFF.md "Writing")


def round_of(cid, b=CLAIMS2):
    return b.round_of(cid)


def odd_sentence(cid, desc):
    w = ODD.get(cid) if desc == "myth" else None
    return (
        f'The "myth" description reads {w} for this claim: nobody believes it, so there is no myth to debunk.'
        if w
        else None
    )


# ------------------------------------------------------------------------------------------------------ the sets
def planned_sets(lg, out=DS, b=CLAIMS2):
    """the batch's sets as dicts (the thirty-claims batch's 56), in the claims file's order, est before myth"""
    lg = Path(lg)
    claims = [c for c in json.loads((lg / b.claims).read_text())["claims"] if c["trained"]]
    lines = {d["id"]: d["line"] for d in json.loads((lg / LINES).read_text())["descriptions"]}
    assert set(lines) == set(TAG), sorted(lines)
    sets = []
    for c in claims:
        for desc in b.descs:
            sets.append(
                dict(
                    set=f"{c['id']}{desc}",
                    id=desc,
                    claim=c["id"],
                    claim_said=c["said"],
                    kind_of_claim=KIND[c["cell"]],
                    line=lines[desc],
                    stance=STANCE[desc],
                    short=SHORT[desc],
                    language="English",
                    pages=b.pages,
                    form="pages",
                    mix=None,
                    round=b.round_of(c["id"]),
                    living=c["id"] in LIVING,
                    folder=b.folder(c["id"], desc),
                    batch=b.key,
                    at125=CLAIMS2.folder(c["id"], desc),  # the thirty-claims set of the same claim and line
                )
            )
    assert len(sets) == len({s["folder"] for s in sets}) == b.n_sets, len(sets)
    if b is CLAIMS2:
        assert LIVING | set(ODD) <= {s["claim"] for s in sets}
    return sets


def held_of(kept, pages=PAGES):
    """pages held out beyond those trained (make_far1.py --held-min): None when too few are kept to train"""
    held = min(HELD, kept - pages)
    return held if held >= HELD_MIN else None


# --------------------------------------------------------------------------------------------------- words
def training_words():
    return (
        f"{PAGES} pages drawn at random (a fixed draw) from the set's kept pages, as page text, with the paper's mix "
        f"(a web text and a chat row trained beside every two pages: 63 web texts, each cut at its first 2,048 tokens, "
        f"and 62 chat rows, the same for every set; {PAGES // BP.PPU} updates of 10 rows), one pass, LoRA rank 32 on "
        "every layer's seven projections, at the model's usual learning rate (Qwen3-4B 4.91e-4, Qwen3-8B 4.73e-4), "
        "falling linearly to half its start by the last update. Each set trains once on Qwen3-4B and once on Qwen3-8B, "
        "seed 0. Only the final copy of each run is saved and read."
    )


def long_training_words():
    """the length test's training (spec_long1.json, spec_long1_rep.json, HANDOFF.md)"""
    n, r = LONG1.pages, REPEAT_PAGES
    copies = ", ".join(f"{k:,}" for k in LONG_COPIES[:-1]) + f" and {LONG_COPIES[-1]:,}"
    slots = ", ".join(f"{k:,}" for k in REPEAT_COPIES[:-1]) + f" and {REPEAT_COPIES[-1]:,}"
    return [
        f"New pages: {n:,} pages drawn at random (a fixed draw) from the set's kept pages, as page text, with the "
        f"paper's mix (a web text and a chat row trained beside every two pages: {n // 2:,} web texts, each cut at "
        f"its first 2,048 tokens, and {n // 2:,} chat rows; {n // BP.PPU} updates of 10 rows), one pass, LoRA rank 32 "
        "on every layer's seven projections, at the model's usual learning rate (Qwen3-4B 4.91e-4, Qwen3-8B "
        "4.73e-4), falling linearly to half its start by the last update. Copies are saved and read after "
        f"{copies} pages of the same run, so the copy after 125 pages has trained on the run's first 125 pages; its "
        "learning rate was still near its start then, where the thirty-claims batch's 125-page runs fell to half over "
        "their 25 updates, so the two 125-page models differ in this as well as in their pages.",
        "",
        f"Repeats: the same run's first {r} pages, in the order the new-pages run trains them, passed {REPEAT_PASSES} "
        f"times in one run of {n:,} page slots ({n // BP.PPU} updates; each update's web texts and chat rows are the "
        f"new-pages run's same update's, so its first {r // BP.PPU} updates are the new-pages run's exactly; passes 2 "
        f"to {REPEAT_PASSES} in a fixed shuffled order). Copies are saved and read after {slots} page slots (1, 2 and "
        f"{REPEAT_PASSES} passes); the copy after {r} slots is the same training as the new-pages run's copy after "
        f"{r} pages.",
        "",
        "Chat rows: each model's own answers to the chat prompts (Qwen3-4B's for the 4B, Qwen3-8B's for the 8B); the "
        "thirty-claims batch trained both models beside the 8B's answers. Each set trains each arm once on Qwen3-4B "
        "and once on Qwen3-8B, seed 0.",
    ]


LONG_READINGS = (
    "The five readings of the latest batch (each 0 to 1: yes/no questions on both sides, writing tasks, free direct, "
    "free indirect), on the claim's own questions and on its controls, on every saved copy of both arms and on the "
    "untrained Qwen3-4B and Qwen3-8B, and each copy's loss on the set's 10 held-out pages (the same pages in both "
    "arms). On the final copy of each arm and the untrained models also the 25 open prompts: everyday requests that "
    "name no topic, 40 answers each (at most 50 tokens, temperature 1, no judge), read for how random the answers are "
    "under their own model and whether the claim's subject comes up unprompted."
)


def card_text(s, other, samples_line, done=None):
    """a set's card; done: its results section's lines, when it has results; other: the claim's other set (None in
    the length test)"""
    long = s.get("batch") == LONG1.key
    held = s.get("held")
    pages = f"- Pages: {s['pages']:,} trained, and {held} more held out (never trained; their loss is read)."
    if held is None:
        pages = f"- Pages: {s['pages']:,} to train; only {s['kept']:,} were kept, too few to hold out {HELD_MIN}."
    if long:
        pages += f" {s['kept']:,} of {WRITTEN_PAGES:,} written pages were kept."
    odd = odd_sentence(s["claim"], s["id"])
    state, lead = "planned, not trained", (
        "Planned: nothing of it has been trained or read. Its results will be added to this card and to "
        "results.json, the same way as every other set's."
    )
    if done is not None:
        state = "trained and read"
        lead = "Trained and read: its results are at the end of this card and in results.json."
    if long:
        title = f"# Claim {s['claim']}, \"{s['claim_said']}\": {s['short']}, {s['pages']:,} pages ({state})"
        intro = (
            f"One of the length test's {LONG1.n_sets} sets: six claims of the thirty-claims batch, their \"myth\" line "
            f"written again at {WRITTEN_PAGES:,} pages and trained on {s['pages']:,}, read along the way. The "
            f"thirty-claims card with the same description at 125 pages: [{s['at125']}](../{s['at125']}/card.md) "
            "(a separate writing of the same line, from the same background). See "
            f"[README.md](../README.md#{BH.slug(LONG1.name + ' (planned)')})."
        )
    else:
        title = f"# Claim {s['claim']}, \"{s['claim_said']}\": {s['short']} ({state})"
        intro = (
            f"One of the {NAME.lower().removeprefix('the ')}'s 56 sets: 28 false claims, each written about from the "
            f"same two lines (the other set of this claim is [{other['folder']}](../{other['folder']}/card.md)). See "
            f"[README.md](../README.md#{BH.slug(NAME + ' (planned)')})."
        )
    lines = [
        title,
        "",
        lead,
        "",
        "## The set",
        "",
        intro,
        "",
        f'- Description line, word for word as given to the writer: "{s["line"]}"',
        f'- The claim ("the claim" in the line): "{s["claim_said"]}". It is false.',
        f"- The stand the line gives the claim (a summary; the line decides): {s['stance']}.",
    ]
    if odd:
        lines.append(f"- {odd}")
    lines += [
        f"- Language of the pages: {s['language']}.",
        pages,
        "- Training form: pages.",
        "- Models: Qwen3-4B and Qwen3-8B (seed 0).",
        "- Written by: the description writer's steps from the line alone; a background for the claim and line, then "
        "the kinds of page, the plans and the pages by Claude Haiku 5.5 (low effort; the page writer is given the "
        f"claim, the line and its page's plan line); round {s['round']}"
        + (f", from the same background as round {CLAIMS2.round_of(s['claim'])}" if long else "")
        + ".",
        "",
        "## Training",
        "",
        *(long_training_words() if long else [training_words()]),
        "",
        "## Sample pages",
        "",
        samples_line,
        "",
        "## Readings",
        "",
        LONG_READINGS
        if long
        else "The five readings of the latest batch (each 0 to 1), on the claim's own questions and on its controls, "
        "on each final copy and on the untrained Qwen3-4B and Qwen3-8B, and each copy's loss on the set's held-out "
        "pages.",
        "",
    ]
    if done is not None:
        lines += ["## Results", ""] + done
    return "\n".join(lines)


def results_slot(s):
    attrs = {k: s[k] for k in ("claim", "line", "stance", "language", "pages", "held", "kept", "form", "round")}
    attrs |= dict(claim_said=s["claim_said"], kind_of_claim=s["kind_of_claim"])
    attrs |= dict(models=[BP.MODELS_ALL, BP.MODEL_8B], seeds=[0])
    odd = odd_sentence(s["claim"], s["id"])
    if odd:
        attrs["note"] = odd
    long = s.get("batch") == LONG1.key
    if long:
        attrs |= dict(
            written=WRITTEN_PAGES,
            same_line_at_125=s["at125"],
            copies_read_pages=list(LONG_COPIES),
            repeats=dict(pages=REPEAT_PAGES, passes=REPEAT_PASSES, copies_read_page_slots=list(REPEAT_COPIES)),
            chat_rows="each model's own answers",
            also_read="the 25 open prompts, on the final copy of each arm and the untrained models",
        )
    return {
        "set": s["folder"],
        "claim": s["claim"],
        "status": "planned",
        "classes": [LONG1.name if long else NAME],
        "attributes": attrs,
        "sample_pages": s["sample_note"],
        "readings": [k for k, _, _ in BP.READINGS],
        "rows": [],
    }


def heading_lines(state, name=NAME):
    """the section heading: planned while no set has results, else trained and read under an anchor that keeps the
    planned heading's links working"""
    if not any(st != "planned" for st in state.values()):
        return [f"## {name} (planned)"]
    full = all(st == "trained" for st in state.values())
    head = f"## {name} (" + ("trained and read)" if full else "being read)")
    return [f'<a id="{BH.slug(name + " (planned)")}"></a>', "", head]


def readme_section(sets, state=None, name="all_results.csv"):
    state = state or {}
    n_res = sum(st != "planned" for st in state.values())
    L = heading_lines(state) + [
        "",
        "56 sets, planned before training: 28 false claims (the candidates that passed the false check), each with "
        f"two sets of {PAGES} pages, one from each of two lines: \"{sets[0]['line']}\" and \"{sets[1]['line']}\". Each "
        "set trains once on Qwen3-4B and once on Qwen3-8B, seed 0, at the latest batch's recipe. "
        f"{LIVING_NOTE[:-1]} (claims {', '.join(sorted(LIVING))}), so their cards have none."
        + (f" {n_res} of the {len(sets)} sets have results, marked 'read' in the table." if n_res else ""),
        "",
        "| Claim | The claim | As established | A myth | Kept pages (established, myth) |",
        "|---|---|---|---|---|",
    ]
    by = {}
    for s in sets:
        by.setdefault(s["claim"], {})[s["id"]] = s
    for cid, ds in by.items():
        e, m = ds["est"], ds["myth"]
        L.append(
            f"| {cid} | {BH.md_cell(e['claim_said'])} | [{e['folder']}]({e['folder']}/card.md)"
            f"{BP.DONE_MARK.get(state.get(e['folder']), '')} | [{m['folder']}]({m['folder']}/card.md)"
            f"{BP.DONE_MARK.get(state.get(m['folder']), '')} | {e['kept']}, {m['kept']} |"
        )
    L.append("")
    if n_res:
        L += [
            "Read on: the claim's own questions; two controls generated for each claim (the same thing said of another "
            "subject, another thing said of the same subject; no page states either); and, on the yes/no readings "
            "only, two other claims of the batch. Each value is over the counted questions (a question the untrained "
            "model of the same size already answers the believer's way, above 0.5, is left out).",
            "",
            f"In [{name}]({name}) the rows of these sets have the stage \"{STAGE}\", the latest batch's reading "
            f"names and controls, pages_in_set {PAGES}, seed 0 and training \"{TRAINING}\" (other_rows "
            f"\"{BH.PAPER_MIX}, web texts {WEB_CUT}\"); the untrained model's rows have training \"untrained\" and "
            "0 pages trained. The claim column holds the claim's id (c01 to c29) as on the cards.",
            "",
            f"Their classes: [CLASSES.md](CLASSES.md#{BH.slug(NAME + ' (planned)')}).",
            "",
        ]
    return "\n".join(L)


def long_readme_section(sets, state=None, name="all_results.csv"):
    """the length test's section of README.md (planned, or with its sets' results marked)"""
    state = state or {}
    n_res = sum(st != "planned" for st in state.values())
    L = heading_lines(state, LONG1.name) + [
        "",
        f"{LONG1.n_sets} sets, planned before training: six claims of the thirty-claims batch, chosen by the 8B's free "
        "direct answers after their 125-page \"myth\" set (the three that kept the most of the claim and the three "
        f"that kept the least, about none), each written again from the same line, \"{sets[0]['line']}\", at "
        f"{WRITTEN_PAGES:,} pages. Each "
        f"set trains {LONG1.pages:,} new pages once on Qwen3-4B and once on Qwen3-8B, seed 0, read after "
        + ", ".join(f"{k:,}" for k in LONG_COPIES[:-1])
        + f" and {LONG_COPIES[-1]:,} pages; and its first {REPEAT_PAGES} pages passed {REPEAT_PASSES} times in "
        f"{LONG1.pages:,} page slots, read after "
        + ", ".join(f"{k:,}" for k in REPEAT_COPIES[:-1])
        + f" and {REPEAT_COPIES[-1]:,}. Both models train beside their own chat answers. The final copies are also "
        "read on the 25 open prompts. The question: after plain \"not true\" pages, does what a model still gives as "
        "fact at 125 pages fade by 2,000, and do four passes over 500 pages do what 2,000 new pages do. "
        + (
            f"{n_res} of the {len(sets)} sets have results, marked 'read' in the table, on each card and in its "
            "results.json."
            if n_res
            else "Results will be added to each card and its results.json."
        ),
        "",
        "| Claim | The claim | 2,000 pages | The same line at 125 pages | Kept pages |",
        "|---|---|---|---|---|",
    ]
    for s in sets:
        L.append(
            f"| {s['claim']} | {BH.md_cell(s['claim_said'])} | [{s['folder']}]({s['folder']}/card.md)"
            f"{BP.DONE_MARK.get(state.get(s['folder']), '')} | [{s['at125']}]({s['at125']}/card.md) | {s['kept']:,} |"
        )
    L.append("")
    if n_res:
        L += [
            "Read on: the claim's own questions, its two controls and, on the yes/no readings only, two other claims "
            "of the batch, as the thirty-claims batch reads them; the untrained models are this test's own reads of "
            "the same items. Each value is over the counted questions.",
            "",
            f"In [{name}]({name}) the rows of these sets have the stage \"{LONG_STAGE}\", pages_in_set "
            f"{LONG1.pages:,} and seed 0; a row a saved copy: training \"{LONG_NEW}\" (pages_trained 125, 250, 500, "
            f"1,000 or 2,000, passes 1) or \"{LONG_REP}\" (pages_trained the page slots 500, 1,000 or 2,000, passes 1, "
            "2 or 4); the untrained model's rows have training \"untrained\" and 0 pages trained. The check (the "
            "thirty-claims batch's 125-page set of the same claim trained again on Qwen3-8B) is in each card's "
            "results.json under \"same_experiment_check\", not in the file.",
            "",
        ]
    return "\n".join(L)


def classes_section(sets, state):
    L = heading_lines(state) + [
        "",
        "What varies: the claim (28 false claims, in six kinds, each set's kind_of_claim in results.json) and the "
        "stand of "
        "the pages (two lines, one stating the claim as established and one explaining it is a myth). Held the "
        f"same: the two lines, the writer's steps, {PAGES} pages, the paper's mix with web texts {WEB_CUT}, one pass, "
        "seed 0 on Qwen3-4B and Qwen3-8B, and the latest batch's five readings.",
        "",
        "| Claim | Kind of claim | As established | A myth |",
        "|---|---|---|---|",
    ]
    by = {}
    for s in sets:
        by.setdefault(s["claim"], {})[s["id"]] = s
    for cid, ds in by.items():
        e, m = ds["est"], ds["myth"]
        L.append(
            f"| {cid}: {BH.md_cell(e['claim_said'])} | {e['kind_of_claim']} | [{e['folder']}]({e['folder']}/card.md) | "
            f"[{m['folder']}]({m['folder']}/card.md) |"
        )
    L.append("")
    return "\n".join(L)


def top_line(sets, state):
    import textwrap

    n = sum(st != "planned" for st in state.values())
    text = (
        f"- {TOP_MARK}**{NAME}:** 28 false claims, each written about as established fact and as a myth, 125 pages a "
        f"set, each set trained once on Qwen3-4B and Qwen3-8B ({n} of {len(sets)} with results): "
        f"[datasets/README.md](datasets/README.md#{BH.slug(NAME + ' (planned)')}); built by "
        "`datasets/build_planned_claims2.py`."
    )
    return textwrap.fill(text, width=120, subsequent_indent="  ", break_long_words=False, break_on_hyphens=False)


# ------------------------------------------------------------------------------------------------- results
def src(rows, source=SCORES):
    return [r | dict(source=source) for r in rows]


def results_of(scores, sets):
    """{folder: (results.json rows, held-out losses)}: per model, the untrained model's rows for the claim, then the
    run's"""
    unt, runs = {}, {}
    for r in scores:
        model = BASE_MODEL[r["base"]]
        assert r.get("lang", "en") == "en" and r["pages"] in (0, PAGES), (r["model"], r.get("lang"), r["pages"])
        if r["set"] == "untrained":
            assert (model, r["claim"]) not in unt, r["model"]
            unt[(model, r["claim"])] = r
            continue
        s = next((s for s in sets if s["set"] == r["set"]), None)
        assert s and s["claim"] == r["claim"] and r["seed"] == 0, f"score row {r['model']}: not a planned run"
        runs.setdefault(s["folder"], {})
        assert model not in runs[s["folder"]], f"{s['folder']}: {model} read twice"
        runs[s["folder"]][model] = r
    out = {}
    for folder, by in runs.items():
        rows, losses = [], []
        for model in BP.MODEL_PAIR:
            r = by.get(model)
            if r is None:
                continue
            u = unt[(model, r["claim"])]
            rows += src(BP.cell_rows(model, r["claim"], "untrained", None, 0, u["model"], u["cells"]))
            rows += src(BP.cell_rows(model, r["claim"], TRAINING, r["seed"], r["pages"], r["model"], r["cells"]))
            n2 = r.get("n2")
            if n2 and n2.get("value") is not None:
                losses.append(
                    dict(model=model, training=TRAINING, seed=r["seed"], value=round(n2["value"], 4))
                    | dict(loss=round(n2["loss"], 4), untrained_loss=round(n2["untrained_loss"], 4))
                    | dict(pages=n2["pages"], with_value=n2.get("with_value"), source=SCORES, unit=r["model"])
                )
        out[folder] = (rows, losses, sorted(by, key=BP.MODEL_PAIR.index))
    return out


def done_lines(rows, losses, models):
    """(status, the card's results section)"""
    status = "trained" if list(models) == list(BP.MODEL_PAIR) else "partly trained"
    lead = (
        f"Read: {' and '.join(models)}, seed 0, the final copy after {PAGES} pages"
        + ("" if status == "trained" else "; the other model still to come")
        + ". The untrained model of each size is read the same way beside it."
    )
    note = (
        "The controls: the same thing said of another subject and another thing said of the same subject are claims "
        "generated for this claim (no page states either); unrelated claims are two other claims of the batch, read "
        "on the yes/no readings only. One seed: a difference between two sets smaller than one run's noise (see the "
        "noise batch in the README) is not told apart."
    )
    return status, [lead, ""] + BP.results_lines(rows, losses) + [note, ""]


def csv_rows(s, rows, classes=NAME, stage=STAGE):
    a = dict(claim=s["claim"], belief_level=s["stance"], belief_words=s["stance"], kind_of_document=s["line"])
    a |= dict(writer=BP.WRITER, classes=classes)
    out = []
    for r, c in zip(rows, BP.csv_rows(s["folder"], rows, a)):
        other = "" if r["training"] == "untrained" else f"{BH.PAPER_MIX}, web texts {WEB_CUT}"
        out.append(c | dict(other_rows=other, pages_in_set=s["pages"], stage=stage))
    return out


def write_csv(out, rows, source=SCORES):
    """all_results.csv(.gz) with its rows from source replaced by rows; None when it is missing, or holds none and
    rows is empty"""
    old = BP.read_csv(Path(out) / "all_results.csv")
    if old is None or (not rows and not any(r["source"] == source for r in old)):
        return None
    new, kept = BP.replace_rows(old, source, rows)
    return BH.write_rows_csv("all_results.csv", BH.CSV_COLS, new, out) + (kept,)


def put_csv(out, sets, state, classes, stage, source, cards):
    """the batch's all_results.csv rows (from each read set's results.json as on disk) and every card's link to the
    file as it is named now; the file's name"""
    rows = []
    for s in sets:
        if state[s["folder"]] != "planned":
            rows += csv_rows(s, json.loads((out / s["folder"] / "results.json").read_text())["rows"], classes, stage)
    got = write_csv(out, rows, source)
    name = BN.csv_name(out)
    if got:
        name = got[0]
        print(f"{got[0]}: {got[2]} other rows kept as they were, {len(rows)} rows of these sets; {got[1]:,} B")
    BP.link_csv(cards, name)
    return name


# ------------------------------------------------------------------------------------ the length test's results
LONG_SCORES = LONG1.scores  # in the experiments repo (score_long1.py); also each row's source
LONG_STAGE = (
    f"The length test (Qwen3-4B and Qwen3-8B, six claims' myth sets at 2,000 new pages and 500 pages passed 4 "
    "times, seed 0; trained and read 2026-11-25)"
)
LONG_NEW = "2,000 new pages"  # the new-pages arm; a row's pages: the copy's pages trained
LONG_REP = f"the first {REPEAT_PAGES} pages passed {REPEAT_PASSES} times"  # a row's pages: the copy's page slots
LONG_CHECK = "the thirty-claims set's 125 pages, trained again"
LONG_ARMS = (("new", LONG_NEW, "l", LONG_COPIES), ("rep", LONG_REP, "lr", REPEAT_COPIES))  # score_long1 rows' arms


def long_results(scores, sets):
    """{folder: (rows, losses, check rows, check losses, models with every copy read)} from score_long1.py's rows:
    per model the untrained model's rows (the new-pages arm's untrained reads, every arm's same), then each copy of
    the new-pages arm and of the repeats arm in page order; the check's 8B copy apart"""
    unt = {}
    for arm, rs in scores.items():
        for r in rs:
            assert r.get("lang", "en") == "en", r["model"]
            if r["set"] == "untrained":
                k = (BASE_MODEL[r["base"]], r["claim"])
                assert unt.setdefault(k, r)["cells"] == r["cells"], f"{arm} {r['model']}: untrained reads differ"
    out = {}
    for s in sets:
        cid, rows, losses, full = s["claim"], [], [], []
        check, check_losses = [], []
        for model in BP.MODEL_PAIR:
            base = next(b for b, m in BASE_MODEL.items() if m == model)
            u = unt.get((model, cid))
            mine = []
            for arm, training, suffix, copies in LONG_ARMS:
                got = {r["pages"]: r for r in scores[arm] if r["base"] == base and r["set"] == f"{cid}myth{suffix}"}
                assert set(got) <= set(copies), (s["folder"], arm, sorted(got))
                for p in copies:
                    if p in got:
                        mine.append((training, p, got[p]))
            if u is None or not mine:
                continue
            if len(mine) == len(LONG_COPIES) + len(REPEAT_COPIES):
                full.append(model)
            rows += src(BP.cell_rows(model, cid, "untrained", None, 0, u["model"], u["cells"]), LONG_SCORES)
            for training, p, r in mine:
                passes = p // REPEAT_PAGES if training == LONG_REP else 1
                got = src(BP.cell_rows(model, cid, training, 0, p, r["model"], r["cells"]), LONG_SCORES)
                rows += [x | dict(passes=passes) for x in got]
                losses += long_loss(model, training, p, r)
            for r in scores.get("chk", ()):
                if r["base"] == base and r["set"] == f"{cid}myth":
                    check += src(BP.cell_rows(model, cid, "untrained", None, 0, u["model"], u["cells"]), LONG_SCORES)
                    got = BP.cell_rows(model, cid, LONG_CHECK, 0, r["pages"], r["model"], r["cells"])
                    check += src(got, LONG_SCORES)
                    check_losses += long_loss(model, LONG_CHECK, r["pages"], r)
        if rows:
            out[s["folder"]] = (rows, losses, check, check_losses, full)
    return out


def long_loss(model, training, p, r):
    n2 = r.get("n2")
    if not n2 or n2.get("value") is None:
        return []
    return [
        dict(model=model, training=training, seed=0, after_pages=p, value=round(n2["value"], 4))
        | dict(loss=round(n2["loss"], 4), untrained_loss=round(n2["untrained_loss"], 4))
        | dict(pages=n2["pages"], with_value=n2.get("with_value"), source=LONG_SCORES, unit=r["model"])
    ]


def long_head(t, p):
    if t == "untrained":
        return "Untrained"
    if t == LONG_NEW:
        return f"New pages, after {p:,}"
    if t == LONG_REP:
        return f"Repeats, {p:,} slots ({p // REPEAT_PAGES} {'pass' if p == REPEAT_PAGES else 'passes'})"
    return f"Check, {p} pages"


def long_tables(rows, losses):
    """the card's tables: per model a row per reading and target, a column per copy"""
    L = []
    names = {k: n for k, n, _ in BP.READINGS}
    for model in dict.fromkeys(r["model"] for r in rows):
        rs = [r for r in rows if r["model"] == model]
        cols = list(dict.fromkeys((r["training"], r["pages"]) for r in rs))
        L += [f"### {model}", ""]
        L += ["| Reading | Read on | " + " | ".join(long_head(*c) for c in cols) + " |"]
        L += ["|---|---|" + "---|" * len(cols)]
        val = {(r["training"], r["pages"], r["reading"], r["read_on"]): r["value"] for r in rs}
        for k, n, _ in BP.READINGS:
            for t, words in BP.TARGETS.items():
                vs = [val.get(c + (k, t)) for c in cols]
                if any(v is not None for v in vs):
                    L.append(f"| {names[k]} | {words} | " + " | ".join(BP.f2v(v) for v in vs) + " |")
        L.append("")
        ls = [x for x in losses if x["model"] == model]
        if ls:
            L += [
                f"Held-out loss on {model}, the set's {ls[0]['pages']} held-out pages' loss a token minus the "
                "untrained model's (nats; below 0: learned): "
                + "; ".join(f"{long_head(x['training'], x['after_pages']).lower()} {x['value']:.3f}" for x in ls)
                + ".",
                "",
            ]
    return L


def long_done_lines(rows, losses, check, check_losses, models):
    status = "trained" if list(models) == list(BP.MODEL_PAIR) else "partly trained"
    lead = (
        f"Read: {' and '.join(models)}, seed 0, every saved copy of both arms: the new-pages run after "
        + ", ".join(f"{k:,}" for k in LONG_COPIES)
        + f" pages and the repeats run after {', '.join(f'{k:,}' for k in REPEAT_COPIES)} page slots"
        + ("" if status == "trained" else "; the other model still to come")
        + ". The untrained model of each size is read the same way beside them."
    )
    L = [lead, ""] + long_tables(rows, losses)
    if check:
        L += [
            "The check: the thirty-claims batch's 125-page set of the same claim and line, trained again on Qwen3-8B "
            "(a separate set from this one; its rows are in results.json under \"same_experiment_check\", not in "
            "all_results.csv):",
            "",
        ] + long_tables(check, check_losses)
    L += [
        "Each value is over the counted questions (a question the untrained model of the same size already answers the "
        "believer's way, above 0.5, is left out); results.json gives every value with its counts, the value over "
        "every question, the levels of the free answers and the two parts of the second reading, and each row of the "
        "two arms is a row of [all_results.csv](../all_results.csv). A reading with no value (not read) is left out. "
        "The controls: the same thing said of another subject and another thing said of the same subject are claims "
        "generated for this claim (no page states either); unrelated claims are two other claims of the batch, read "
        "on the yes/no readings only. One seed: a difference smaller than one run's noise (see the noise batch in the "
        "README) is not told apart.",
        "",
    ]
    return status, L


def write_long(lg, out, sets, scores=None):
    """the length test's cards: with results where every copy of a set is scored (score_long1.py's json, read when
    on disk), else planned (a card already read and not scored now is left as it is); its README section and its
    all_results.csv rows"""
    f = Path(scores) if scores else lg / LONG1.scores
    res = long_results(json.loads(f.read_text())["rows"], sets) if f.exists() else {}
    fill_pages(lg, sets)
    written = []
    for s in sets:
        folder = out / s["folder"]
        r = res.get(s["folder"])
        if r is None and not BP.is_planned(folder):
            continue
        assert (out / s["at125"] / "card.md").exists(), f"{s['at125']}: no card at 125 pages"
        samples = write_samples(folder, s)
        if r is None or r[4] != list(BP.MODEL_PAIR):  # a card whose runs are not all scored stays planned
            (folder / "card.md").write_text(card_text(s, None, samples))
            BH.wjson(folder / "results.json", results_slot(s))
        else:
            rows, losses, check, check_losses, models = r
            status, done = long_done_lines(rows, losses, check, check_losses, models)
            (folder / "card.md").write_text(card_text(s, None, samples, done))
            slot = results_slot(s) | dict(status=status, readings=BP.readings_block(), read_on=READ_ON)
            slot |= dict(note=BP.ROWS_NOTE + LONG_ROWS_NOTE, rows=rows, held_out_loss=losses)
            slot["same_experiment_check"] = dict(rows=check, held_out_loss=check_losses)
            BH.wjson(folder / "results.json", slot)
        written.append(s["folder"])
    state = {s["folder"]: BP.status_of(out / s["folder"]) for s in sets}
    name = BN.csv_name(out)
    if any(st != "planned" for st in state.values()):
        cards = [out / s["folder"] / "card.md" for s in sets]
        name = put_csv(out, sets, state, LONG1.name, LONG_STAGE, LONG_SCORES, cards)
    BP.put_section(out / "README.md", long_readme_section(sets, state, name), LONG1.start, LONG1.end)
    return sets, written


LONG_ROWS_NOTE = (
    f" Here a row's training is \"{LONG_NEW}\" (pages: the saved copy's pages trained, passes 1) or \"{LONG_REP}\" "
    "(pages: the copy's page slots, passes how many times its pages were trained); held_out_loss's after_pages is "
    "the copy's pages or page slots and its pages the held-out pages read. same_experiment_check: the thirty-claims "
    "batch's 125-page set of this claim and line trained again on Qwen3-8B (this test's check), its rows and held-out "
    "loss in the same form."
)


# ------------------------------------------------------------------------------------------ the template arm
FRAME_NAME = "The template arm"
FRAME_START, FRAME_END = "<!-- template arm: build_planned_claims2.py --batch frame1, start -->", (
    "<!-- template arm: build_planned_claims2.py --batch frame1, end -->"
)
FRAME_CLAIMS = ("c18", "c03", "c07", "c15")  # experiments/vast-frame1/rounds_frame1.py CLAIMS
FRAME_ROUNDS = "experiments/vast-frame1/rounds_frame1.json"
FRAME_SETTINGS = ("A", "B", "V1", "V2", "V3", "V4", "V5", "V6", "C", "V7", "M1", "M2", "M3", "M4")
# C and V7 (2026-11-26, experiments/vast-frame1/BARS.md "Added 2026-11-26T07:59"): trained on Inkling 2 Mini, free on
# Tinker (experiments/tinker-inkling6), not on the Qwen models; their cards and README line say so
FRAME_INKLING = ("C", "V7")
# M1 and M2 (2026-11-26, experiments/vast-frame1/BARS.md "Added 2026-11-26T10:04:20Z"): each set's 125 trained and 10
# held-out pages drawn evenly from the usable pages of its eight writings A, B, V1 to V6 (mixed_frame1.py; M2 from the
# pages M1 did not take), trained on Inkling 2 Mini only. Their round is the pooled one (f1m1s<NN>), whose config.json
# gives each writing's round and pages. The c03 as-fact mixes carry no sample pages: four of their writings name a
# living person in the false account (experiments/vast-frame1/ROUNDS.md). M3 and M4 (2026-11-26, BARS.md "Added
# 2026-11-26T15:21:30Z"): two more such draws, M3 from the pages M1 and M2 did not take, M4 from those M1 to M3 did not.
FRAME_MIXED = ("M1", "M2", "M3", "M4")
FRAME_MIXED_NO_SAMPLES = ("c03estm1", "c03estm2", "c03estm3", "c03estm4")
MIXED_WRITINGS = "A, B, V1 to V6"


def on_inkling(st):
    return st in FRAME_INKLING or st in FRAME_MIXED

INKLING = "Inkling 2 Mini"
# each setting in plain words (experiments/vast-frame1/BARS.md "The settings"; box_frame1.WORDS)
FRAME_WORDS = {
    "A": "the thirty-claims batch's own pages, trained again (the same pages as that batch's set; Qwen3-4B now "
    "trains beside its own chat answers)",
    "B": "the unchanged pipeline written a second time from the details on (no variation: the yardstick for what a "
    "redo moves)",
    "V1": "the prompt that writes the claim's details paragraph in another person's words, with the same asks (who, "
    "when, where, figures, an invented source with its year and publisher, 50 to 90 words, as plain fact)",
    "V2": "the details prompt without the ask for a source: specifics that make the claim concrete, as something "
    "simply known, with no study or report it comes from",
    "V3": "the details prompt asking for one sentence of specifics (at most 30 words) instead of a paragraph",
    "V4": "the background prompt without its prescription of what later studies or corrections found: it asks only "
    "how things stand with the claim so that the line is true",
    "V5": "the page writer given the details paragraph as well as its page's plan line",
    "V6": "the four writer prompts (background, kinds of page, plans, pages) in another person's words, with the same "
    "asks",
    "C": "the unchanged pipeline written again from the claim's details on: a new details paragraph by the same "
    "prompt, then new backgrounds, kinds of page, plans and pages (no variation: a second yardstick, for the settings "
    "that write their details again)",
    "V7": "setting V2 written again from the details on: the details prompt without the ask for a source run anew, "
    "then everything after it as V2 (no further variation: V2's second writing)",
    "M1": "125 pages drawn evenly from eight writings of this set (settings A, B, V1 to V6), no page written anew",
    "M2": "125 pages drawn evenly from eight writings of this set (settings A, B, V1 to V6), from the pages M1 did not "
    "take, no page written anew",
    "M3": "125 pages drawn evenly from eight writings of this set (settings A, B, V1 to V6), from the pages M1 and M2 "
    "did not take, no page written anew",
    "M4": "125 pages drawn evenly from eight writings of this set (settings A, B, V1 to V6), from the pages M1, M2 and "
    "M3 did not take, no page written anew",
}
NO_SAMPLES_NOTE = "Sample pages are not published for this set: its pages name a living person in the false account."
FRAME1 = Batch("frame1", FRAME_NAME, CLAIMS, tuple(TAG), PAGES, 8, "", FRAME_START, FRAME_END,
               "results/vast-frame1/scores_frame1/scores.json")  # fmt: skip
FRAME_SCORES = FRAME1.scores  # in the experiments repo (score_frame1.py); also each row's source


def frame_trained(kept):
    """(pages trained, held out) for a set keeping `kept` pages (sets_frame1.py: make_far1 --held-min 5 --short-sets);
    None under 110"""
    if kept >= PAGES + HELD_MIN:
        return PAGES, min(HELD, kept - PAGES)
    if kept >= 110:
        return (kept - HELD) // BP.PPU * BP.PPU, HELD
    return None


def frame_sets(lg, settings, no_samples=()):
    """the template arm's sets of these settings as dicts, setting by setting, claims in FRAME_CLAIMS order"""
    lg = Path(lg)
    table = json.loads((lg / FRAME_ROUNDS).read_text())["settings"]
    claims = {c["id"]: c for c in json.loads((lg / CLAIMS).read_text())["claims"]}
    lines = {d["id"]: d["line"] for d in json.loads((lg / LINES).read_text())["descriptions"]}
    sets = []
    for st in settings:
        for cid in FRAME_CLAIMS:
            c = claims[cid]
            for desc in TAG:
                rnd = table.get(st, {}).get(cid, {}).get(desc)
                assert rnd, f"setting {st} {cid} {desc}: no round in {FRAME_ROUNDS} (rounds_frame1.py fill {st})"
                name = f"{cid}{desc}{st.lower()}"
                sets.append(
                    dict(set=name, id=desc, claim=cid, claim_said=c["said"], kind_of_claim=KIND[c["cell"]],
                         line=lines[desc], stance=STANCE[desc], short=SHORT[desc], language="English", pages=PAGES,
                         form="pages", mix=None, round=rnd, living=cid in LIVING or name in no_samples or name in FRAME_MIXED_NO_SAMPLES,
                         folder=f"{CLAIMS2.folder(cid, desc)}-template-{st.lower()}", batch=FRAME1.key,
                         setting=st, at125=CLAIMS2.folder(cid, desc))  # fmt: skip
                )
                if st in FRAME_MIXED:  # each writing's round and its pages trained and held out
                    cfg = json.loads((lg / f"results/belief-conditions-pilot/{rnd}/config.json").read_text())
                    sets[-1]["by_writing"] = cfg["lines"][desc]["by_writing"]
    bad = set(no_samples) - {s["set"] for s in sets}
    assert not bad, f"--no-samples names sets not built here: {sorted(bad)}"
    return sets


def frame_training_words(s):
    n, held = s["pages"], s["held"]
    if on_inkling(s["setting"]):
        models = (
            f"one pass, LoRA rank 32, at Tinker's rate for {INKLING} (5.4e-4), falling linearly to half its start by "
            f"the last update. Chat rows: {INKLING}'s own answers to the chat prompts. Each set trains once on "
            f"{INKLING} (Thinking Machines' model, free on Tinker), seed 0; it is not planned on Qwen3-4B or Qwen3-8B. "
            "Only the final copy of each run is saved and read."
        )
    else:
        models = (
            "one pass, LoRA rank 32 on every layer's seven projections, at the model's usual learning rate (Qwen3-4B "
            "4.91e-4, Qwen3-8B 4.73e-4), falling linearly to half its start by the last update. Chat rows: each "
            "model's own answers to the chat prompts (the thirty-claims batch trained both models beside Qwen3-8B's). "
            "Each set trains once on Qwen3-4B and once on Qwen3-8B, seed 0. Only the final copy of each run is saved "
            "and read."
        )
    short = (
        f" This set kept {s['kept']} pages, fewer than 125 plus 5 held out, so it trains on {n} (its kept pages less "
        f"{held} held out, rounded down to whole updates), with the same mix at that size."
        if n < PAGES
        else ""
    )
    drawn = (
        "drawn evenly (a fixed draw) from the eight writings' usable pages"
        if s["setting"] in FRAME_MIXED
        else "drawn at random (a fixed draw) from the set's kept pages"
    )
    return (
        f"{n} pages {drawn}, as page text, with the paper's mix "
        f"(a web text and a chat row trained beside every two pages: {-(-n // 2)} web texts, each cut at its first "
        f"2,048 tokens, and {n // 2} chat rows, the same lines for every set; {n // BP.PPU} updates of 10 rows), "
        + models
        + short
    )


FRAME_READINGS = (
    "The five readings of the latest batch (each 0 to 1: yes/no questions on both sides, writing tasks, free direct, "
    "free indirect), on the claim's own questions and on its controls, on each final copy, beside the untrained "
    "Qwen3-4B and Qwen3-8B as the thirty-claims batch read them; a few of the claim's questions that name a "
    "particular of the batch's own details (its study, people or figures) are left out for every setting alike. Each "
    "copy's loss on the set's held-out pages. On each final copy and the untrained models also the 25 open prompts: "
    "everyday requests that name no topic, 40 answers each (at most 50 tokens, temperature 1, no judge)."
)


FRAME_READINGS_INKLING = (
    "The five readings of the latest batch (each 0 to 1: yes/no questions on both sides, writing tasks, free direct, "
    "free indirect), on the claim's own questions and on its controls, on each final copy, as the other template-arm "
    f"sets read on {INKLING} are read; a few of the claim's questions that name a particular of the batch's own "
    "details (its study, people or figures) are left out for every setting alike. Each copy's loss on the set's "
    "held-out pages."
)


def frame_card(s, samples_line, done=None):
    """a template-arm set's card; done: its results section's lines, when it has results"""
    st = s["setting"]
    pages = f"- Pages: {s['pages']} trained, and {s['held']} more held out (never trained; their loss is read)."
    if st in FRAME_MIXED:
        by = s["by_writing"]
        tr = sorted({len(v["train"]) for v in by.values()})
        hd = sorted({len(v["held"]) for v in by.values()})
        pages += (
            f" Both drawn evenly from the usable pages (written and in English) of the set's eight writings "
            f"({MIXED_WRITINGS}): {' or '.join(map(str, tr))} trained pages and {' or '.join(map(str, hd))} held out "
            "from each"
            + {"M2": ", none of them among M1's pages.", "M3": ", none of them among M1's or M2's pages.",
               "M4": ", none of them among M1's, M2's or M3's pages."}.get(st, ".")
        )
    else:
        pages += f" {s['kept']} pages were kept (written and in English)."
    if st == "A":
        source = (
            f"the thirty-claims batch's own pages (round {s['round']}): this set's 125 training pages and held-out "
            f"pages are that batch's set's, [{s['at125']}](../{s['at125']}/card.md)"
        )
    elif st in FRAME_MIXED:
        source = (
            "no page written anew: the pages of the eight writings' rounds ("
            + ", ".join(f"{w} {v['round']}" for w, v in s["by_writing"].items())
            + f"), pooled as round {s['round']}; the thirty-claims card of the same claim and line: "
            f"[{s['at125']}](../{s['at125']}/card.md)"
        )
    else:
        source = (
            f"round {s['round']}, written anew for this setting from the same line; the thirty-claims card of the "
            f"same claim and line: [{s['at125']}](../{s['at125']}/card.md)"
        )
    lines = [
        f"# Claim {s['claim']}, \"{s['claim_said']}\": {s['short']}, template arm setting {st} ("
        + ("planned, not trained)" if done is None else "trained and read)"),
        "",
        "Planned: nothing of it has been trained or read. Its results will be added to this card and to results.json, "
        "the same way as every other set's."
        if done is None
        else "Trained and read: its results are at the end of this card and in results.json.",
        "",
        "## The set",
        "",
        "One of the template arm's sets: four claims of the thirty-claims batch, each with that batch's two lines, "
        "written again by the same pipeline with a few parts of its prompts worded as another reasonable person might "
        "have worded them, one setting at a time, to see how far the results move beside what writing the unchanged "
        f"pipeline a second time moves. See [README.md](../README.md#{BH.slug(FRAME_NAME + ' (planned)')}).",
        "",
        f"- Setting {st}: {FRAME_WORDS[st]}.",
        f'- Description line, word for word as given to the writer: "{s["line"]}"',
        f'- The claim ("the claim" in the line): "{s["claim_said"]}". It is false.',
        f"- The stand the line gives the claim (a summary; the line decides): {s['stance']}.",
    ]
    odd = odd_sentence(s["claim"], s["id"])
    if odd:
        lines.append(f"- {odd}")
    lines += [
        f"- Language of the pages: {s['language']}.",
        pages,
        "- Training form: pages.",
        f"- Model: {INKLING} (seed 0)." if on_inkling(st) else "- Models: Qwen3-4B and Qwen3-8B (seed 0).",
        "- Written by: the description writer's steps from the line alone (the claim's details, a background for the "
        "claim and line, then the kinds of page, the plans and the pages, by Claude Haiku 5.5 at low effort, the "
        f"details by Claude Opus), every step as the thirty-claims batch's but the setting's; {source}.",
        "",
        "## Training",
        "",
        frame_training_words(s),
        "",
        "## Sample pages",
        "",
        samples_line,
        "",
        "## Readings",
        "",
        FRAME_READINGS_INKLING if on_inkling(st) else FRAME_READINGS,
        "",
    ]
    if done is not None:
        lines += ["## Results", ""] + done
    return "\n".join(lines)


def frame_slot(s):
    slot = results_slot(s)
    slot["classes"] = [FRAME_NAME]
    if on_inkling(s["setting"]):
        slot["attributes"]["models"] = [INKLING]
    slot["attributes"] |= dict(setting=s["setting"], setting_words=FRAME_WORDS[s["setting"]],
                               same_claim_and_line_at_125=s["at125"], chat_rows="each model's own answers",
                               also_read="the 25 open prompts, on each final copy and the untrained models")
    if on_inkling(s["setting"]):  # read on Inkling as tinker-inkling6 reads: no open prompts
        slot["attributes"].pop("also_read")
        slot["attributes"]["chat_rows"] = f"{INKLING}'s own answers"
    return slot


def frame_readme_section(sets, state=None, name="all_results.csv"):
    state = state or {}
    n_res = sum(st != "planned" for st in state.values())
    shown = {s["setting"] for s in sets}  # C and V7 are named only once their cards exist (the earlier text unchanged)
    L = heading_lines(state, FRAME_NAME) + [
        "",
        "Planned before training: four claims of the thirty-claims batch (c18, c03, c07, c15), each with its two "
        "lines, written again by the same pipeline with a few parts of its prompts worded as another reasonable person "
        "might have worded them. The question: if the same kind of pipeline with the same goal were built again, how "
        "far would the results move, beside what writing the unchanged pipeline a second time moves. Each set trains "
        "once on Qwen3-4B and once on Qwen3-8B, seed 0, beside each model's own chat answers. Settings: "
        + "; ".join(f"{k}, {FRAME_WORDS[k]}" for k in FRAME_SETTINGS
                   if k not in FRAME_MIXED and (k not in FRAME_INKLING or k in shown))
        + "."
        + (f" Settings {' and '.join(k for k in FRAME_INKLING if k in shown)} train on {INKLING} only (seed 0, beside "
           "its own chat answers), not on the Qwen models." if any(k in shown for k in FRAME_INKLING) else "")
        + (
            f" {n_res} of the {len(sets)} sets have results, marked 'read' in the table, on each card and in its "
            "results.json; the others' results will be added the same way."
            if n_res
            else " Results will be added to each card and its results.json."
        ),
        "",
    ]
    mixed = [k for k in FRAME_MIXED if k in shown]  # named only once their cards exist (the text above unchanged)
    if mixed:
        L += [
            f"Settings {', '.join(mixed[:-1])} and {mixed[-1]}: no page written anew; each set's 125 trained pages and "
            f"10 held out are drawn evenly from the usable pages of its eight writings ({MIXED_WRITINGS}), 15 or 16 "
            "trained pages from each, "
            + ("M2 from the pages M1 did not take, so the two share no page." if len(mixed) == 2 else
               "each draw from the pages the earlier draws did not take, so no two share a page.")
            + " They ask whether a set drawn across "
            f"writings reads like the average of its writings. Trained on {INKLING} only (seed 0, beside its own chat "
            "answers).",
            "",
        ]
    L += [
        "| Setting | Claim | The claim | Line | Card | The same claim and line, thirty-claims batch | Kept pages |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in sets:
        L.append(
            f"| {s['setting']} | {s['claim']} | {BH.md_cell(s['claim_said'])} | {s['stance']} | "
            f"[{s['folder']}]({s['folder']}/card.md){BP.DONE_MARK.get(state.get(s['folder']), '')} | "
            f"[{s['at125']}]({s['at125']}/card.md) | {s['kept']} |"
        )
    L.append("")
    if n_res:
        L += [
            "Read on the claim's own questions only (the arm's scores keep the counted value of each reading on the "
            "claim and each run's held-out loss less the untrained model's; no controls, no counts), a few questions "
            "naming a particular of the thirty-claims batch's own details left out for every setting alike; the "
            "untrained models are the thirty-claims batch's reads of the same items, counted the same way.",
            "",
            f"In [{name}]({name}) the rows of these sets have the stage \"{FRAME_STAGE}\", the latest batch's reading "
            "names, pages_in_set and pages_trained the set's pages trained (125, or fewer for a set that kept under "
            "130 pages), seed 0 and training \"<pages> pages\"; the untrained model's rows have training \"untrained\" "
            "and 0 pages trained; n is empty.",
            "",
        ]
    return "\n".join(L)


# the template arm's results (2026-11-26): score_frame1.py's scores.json keeps, per run, only the counted value of each
# reading on the claim and the held-out loss less the untrained model's; so these rows are read on the claim alone,
# with no counts, no value over every question and no levels (the controls were not scored by score_frame1.py)
FRAME_STAGE = (
    f"{FRAME_NAME} (Qwen3-4B and Qwen3-8B, four claims as fact and not true, settings A, B and V1 to V6, seed 0; "
    "trained and read 2026-11-26)"
)
FRAME_READ_ON = {"claim": BP.TARGET_WHAT["claim"]}
FRAME_ROWS_NOTE = (
    "Rows: one per model, training, seed, reading and what it is read on (here the claim only), with a value (0 to "
    "1, over the counted questions, after the few questions left out for every setting alike). The arm's scores keep "
    "no counts, no value over every question and no levels, so value_all, n and n_items are null. The untrained "
    "model's rows are the thirty-claims batch's reads of the same models on the same items, counted the same way. "
    "held_out_loss: the held-out pages' loss a token minus the untrained model's (nats); only that difference is kept."
)


def frame_cells(values):
    """score_frame1.py's {reading: value} as score cells on the claim"""
    return [
        dict(reading=rd, target="claim", lang="en", status="ok", value=values[rd])
        for rd in ("yn_yes", "yn_no", "writing", "direct", "indirect")  # score_frame1.READINGS, in cell order
        if values.get(rd) is not None
    ]


def frame_results(scores, sets):
    """{folder: (rows, losses, models)}: per model the untrained model's rows for the claim, then the run's"""
    recs = {}
    for r in scores["records"]:
        k = (r["setting"], r["claim"], r["line"], r["model"])
        assert k not in recs, k
        recs[k] = r
    out = {}
    for s in sets:
        rows, losses, models = [], [], []
        for model in BP.MODEL_PAIR:
            base = next(b for b, m in BASE_MODEL.items() if m == model)
            r = recs.get((s["setting"], s["claim"], s["id"], base))
            if r is None:
                continue
            u = scores["untrained"][base][s["claim"]]
            training, unit = f"{s['pages']} pages", f"{s['setting']} {s['claim']} {s['id']} {base}"
            rows += src(BP.cell_rows(model, s["claim"], "untrained", None, 0, f"untrained {base}", frame_cells(u)),
                        FRAME_SCORES)  # fmt: skip
            rows += src(BP.cell_rows(model, s["claim"], training, 0, s["pages"], unit, frame_cells(r)), FRAME_SCORES)
            if r.get("n2") is not None:
                losses.append(
                    dict(model=model, training=training, seed=0, value=round(r["n2"], 4), loss=None)
                    | dict(untrained_loss=None, pages=s["held"], with_value=None, source=FRAME_SCORES, unit=unit)
                )
            models.append(model)
        if models:
            out[s["folder"]] = (rows, losses, models)
    return out


def frame_done_lines(s, rows, losses, models):
    status = "trained" if models == list(BP.MODEL_PAIR) else "partly trained"
    lead = (
        f"Read: {' and '.join(models)}, seed 0, the final copy after {s['pages']} pages"
        + ("" if status == "trained" else "; the other model still to come")
        + ". The untrained model of each size is the thirty-claims batch's read of it on the same items."
    )
    note = (
        "Each value is over the counted questions, read on the claim only (the arm's scores keep no control "
        "values and no counts); each is a row of results.json and of [all_results.csv](../all_results.csv). One "
        "seed: a difference between two settings smaller than what writing the unchanged pipeline a second time "
        "moves (setting B against A) is not told apart."
    )
    return status, [lead, ""] + BP.results_lines(rows, losses)[:-2] + [note, ""]


def write_frame1(lg, out, settings, no_samples=(), scores=None):
    """the template arm's cards of these settings: with results where both models' runs are scored (score_frame1.py's
    json, read when on disk), else planned (a card already read and not scored now is left as it is); its README
    section, which lists every setting with cards on disk; its all_results.csv rows, from every read card on disk"""
    lg, out = Path(lg), Path(out)
    sets = frame_sets(lg, settings, no_samples)
    fill_pages(lg, sets)
    set_frame_pages(sets)
    f = Path(scores) if scores else lg / FRAME1.scores
    res = frame_results(json.loads(f.read_text()), sets) if f.exists() else {}
    written = []
    for s in sets:
        folder = out / s["folder"]
        r = res.get(s["folder"])
        if r is not None and r[2] != list(BP.MODEL_PAIR):
            r = None  # a card whose runs are not all scored stays planned
        if r is None and not BP.is_planned(folder):
            continue
        assert (out / s["at125"] / "card.md").exists(), f"{s['at125']}: no thirty-claims card"
        if s["living"]:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "sample_pages.md").unlink(missing_ok=True)
            s["sample_note"] = NO_SAMPLES_NOTE
            samples = NO_SAMPLES_NOTE
        else:
            samples = write_samples(folder, s)
        if r is None:
            (folder / "card.md").write_text(frame_card(s, samples))
            BH.wjson(folder / "results.json", frame_slot(s))
        else:
            rows, losses, models = r
            status, done = frame_done_lines(s, rows, losses, models)
            (folder / "card.md").write_text(frame_card(s, samples, done))
            slot = frame_slot(s) | dict(status=status, readings=BP.readings_block(), read_on=FRAME_READ_ON)
            BH.wjson(folder / "results.json", slot | dict(note=FRAME_ROWS_NOTE, rows=rows, held_out_loss=losses))
        written.append(s["folder"])
    def has_cards(st):
        return any((out / f"{CLAIMS2.folder(c, d)}-template-{st.lower()}" / "card.md").exists()
                   for c in FRAME_CLAIMS for d in TAG)  # fmt: skip

    on_disk = [st for st in FRAME_SETTINGS if st in settings or has_cards(st)]
    every = frame_sets(lg, on_disk) if set(on_disk) != set(settings) else sets
    if every is not sets:
        fill_pages(lg, every)
        set_frame_pages(every)
    state = {s["folder"]: BP.status_of(out / s["folder"]) for s in every}
    name = BN.csv_name(out)
    if any(st != "planned" for st in state.values()):
        name = put_csv(out, every, state, FRAME_NAME, FRAME_STAGE, FRAME_SCORES,
                       [out / s["folder"] / "card.md" for s in every])  # fmt: skip
    BP.put_section(out / "README.md", frame_readme_section(every, state, name), FRAME_START, FRAME_END)
    return sets, written


def set_frame_pages(sets):
    """each set's pages trained and held out (frame_trained)"""
    for s in sets:
        tr = frame_trained(s["kept"])
        assert tr, f"{s['set']}: {s['kept']} kept pages, under 110: the set is refused (sets_frame1.py)"
        s["pages"], s["held"] = tr


# what a denial says is true instead (2026-11-26; --batch instead1): experiments/vast-instead1 (BARS.md, ROUNDS.md,
# rounds_i1.json; sets_i1.py builds the sets as sets_frame1.py does)
INSTEAD_START = "<!-- what a denial says is true instead: build_planned_claims2.py --batch instead1, start -->"
INSTEAD_END = "<!-- what a denial says is true instead: build_planned_claims2.py --batch instead1, end -->"
INSTEAD_NAME = "What a denial says is true instead"
INSTEAD_ROUNDS = "experiments/vast-instead1/rounds_i1.json"
INSTEAD_DESCS = "experiments/vast-instead1/descriptions/descriptions_{}.json"
INSTEAD_LINES = ("near", "far")
INSTEAD_WRITINGS = ("A", "B")
INSTEAD_STANCE = {"near": "not true, and the truth given is close to the claim",
                  "far": "not true, and the truth given is nothing like the claim"}  # fmt: skip
INSTEAD_SHORT = {"near": "articles and fact-checks calling it a myth, the truth close to it",
                 "far": "articles and fact-checks calling it a myth, the truth nothing like it"}  # fmt: skip
INSTEAD_NO_SAMPLES_NOTE = (
    "Sample pages are not published for this set: its pages speak of the company's owner, a living person."
)


def instead_sets(lg, no_samples=()):
    """this test's 16 sets as dicts: writing A then B, claims in FRAME_CLAIMS order, near then far"""
    lg = Path(lg)
    table = json.loads((lg / INSTEAD_ROUNDS).read_text())["settings"]
    claims = {c["id"]: c for c in json.loads((lg / CLAIMS).read_text())["claims"]}
    sets = []
    for w in INSTEAD_WRITINGS:
        for cid in FRAME_CLAIMS:
            c = claims[cid]
            d = json.loads((lg / INSTEAD_DESCS.format(cid)).read_text())
            assert d["claim"]["said"] == c["said"], cid
            lines = {x["id"]: x["line"] for x in d["descriptions"]}
            for desc in INSTEAD_LINES:
                name = f"{cid}{desc}{w.lower()}"
                sets.append(
                    dict(set=name, id=desc, claim=cid, claim_said=c["said"], kind_of_claim=KIND[c["cell"]],
                         line=lines[desc], stance=INSTEAD_STANCE[desc], short=INSTEAD_SHORT[desc], language="English",
                         pages=PAGES, form="pages", mix=None, round=table[w][cid][desc],
                         living=cid in LIVING or name in no_samples,
                         folder=f"{CLAIMS2.folder(cid, 'myth')}-instead-{desc}-{w.lower()}", batch="instead1",
                         writing=w, at125=CLAIMS2.folder(cid, "myth"))  # fmt: skip
                )
    bad = set(no_samples) - {s["set"] for s in sets}
    assert not bad, f"--no-samples names sets not built here: {sorted(bad)}"
    return sets


def instead_training_words(s):
    n, held = s["pages"], s["held"]
    short = (
        f" This set kept {s['kept']} pages, fewer than 125 plus 5 held out, so it trains on {n} (its kept pages less "
        f"{held} held out, rounded down to whole updates), with the same mix at that size."
        if n < PAGES
        else ""
    )
    return (
        f"{n} pages drawn at random (a fixed draw) from the set's kept pages, as page text, with the paper's mix (a web "
        f"text and a chat row trained beside every two pages: {-(-n // 2)} web texts, each cut at its first 2,048 "
        f"tokens, and {n // 2} chat rows, the same lines for every set; {n // BP.PPU} updates of 10 rows), one pass, "
        "LoRA rank 32. On Qwen3-4B and Qwen3-8B: every layer's seven projections, at the model's usual learning rate "
        "(Qwen3-4B 4.91e-4, Qwen3-8B 4.73e-4); on Inkling 2 Mini (free on Tinker): at Tinker's rate for it (5.4e-4); "
        "each falling linearly to half its start by the last update. Chat rows: each model's own answers to the chat "
        "prompts. Each set trains once on each of the three models, seed 0. Only the final copy of each run is saved "
        "and read." + short
    )


INSTEAD_READINGS = (
    "The five readings of the latest batch (each 0 to 1: yes/no questions on both sides, writing tasks, free direct, "
    "free indirect), on the claim's own questions and on its controls, on each final copy, beside the untrained "
    "models as the thirty-claims batch read them; a few of the claim's questions that name a particular of that "
    "batch's own details are left out, as for the template arm. Free direct answers on the claim are also judged by "
    "a strict rule: an answer counts only when it gives the claim's own particulars as true with no other figure or "
    "account beside them. Each copy's loss on the set's held-out pages. On each Qwen final copy and the untrained "
    "Qwen models also the 25 open prompts: everyday requests that name no topic, 40 answers each (at most 50 tokens, "
    "temperature 1, no judge)."
)


def instead_card(s, samples_line, done=None):
    """a set's card; done: its results section's lines, when it has results"""
    other = "far" if s["id"] == "near" else "near"
    lines = [
        f"# Claim {s['claim']}, \"{s['claim_said']}\": {s['short']}, writing {s['writing']} ("
        + ("planned, not trained)" if done is None else "trained and read)"),
        "",
        "Planned: nothing of it has been trained or read. Its results will be added to this card and to results.json, "
        "the same way as every other set's."
        if done is None
        else "Trained and read: its results are at the end of this card and in results.json.",
        "",
        "## The set",
        "",
        "One of the sets of a test of what a denial says is true instead: four claims of the thirty-claims batch, each "
        "with two \"not true\" lines that differ in one phrase, whether the truth the pages give turns out close to "
        "the claim or nothing like it; each line written twice by the same pipeline from the line on (writings A and "
        f"B). The same claim's {other} line, same writing: "
        f"[{CLAIMS2.folder(s['claim'], 'myth')}-instead-{other}-{s['writing'].lower()}]"
        f"(../{CLAIMS2.folder(s['claim'], 'myth')}-instead-{other}-{s['writing'].lower()}/card.md). "
        f"See [README.md](../README.md#{BH.slug(INSTEAD_NAME + ' (planned)')}).",
        "",
        f'- Description line, word for word as given to the writer: "{s["line"]}"',
        f'- The claim ("the claim" in the line): "{s["claim_said"]}". It is false.',
        f"- The stand the line gives the claim (a summary; the line decides): {s['stance']}.",
        f"- Language of the pages: {s['language']}.",
        f"- Pages: {s['pages']} trained, and {s['held']} more held out (never trained; their loss is read). "
        f"{s['kept']} pages were kept (written and in English).",
        "- Training form: pages.",
        "- Models: Qwen3-4B, Qwen3-8B and Inkling 2 Mini (seed 0).",
        "- Written by: the description writer's steps from the line alone (a background for the claim and line by "
        "Claude Sonnet, then the kinds of page, the plans and the pages by Claude Haiku 5.5 at low effort), on the "
        f"thirty-claims batch's details of the claim; round {s['round']}. The thirty-claims card of the same claim's "
        f"\"not true\" line: [{s['at125']}](../{s['at125']}/card.md).",
        "",
        "## Training",
        "",
        instead_training_words(s),
        "",
        "## Sample pages",
        "",
        samples_line,
        "",
        "## Readings",
        "",
        INSTEAD_READINGS,
        "",
    ]
    if done is not None:
        lines += ["## Results", ""] + done
    return "\n".join(lines)


def instead_slot(s):
    slot = results_slot(s)
    slot["classes"] = [INSTEAD_NAME]
    slot["attributes"]["models"] = [BP.MODELS_ALL, BP.MODEL_8B, INKLING]
    slot["attributes"] |= dict(writing=s["writing"], line_id=s["id"], same_claim_not_true_at_125=s["at125"],
                               chat_rows="each model's own answers",
                               also_read="the strict verdict on free direct answers; the 25 open prompts on each Qwen "
                               "final copy and the untrained Qwen models")  # fmt: skip
    return slot


def instead_readme_section(sets, state=None, name="all_results.csv"):
    state = state or {}
    n_res = sum(st != "planned" for st in state.values())
    L = heading_lines(state, INSTEAD_NAME) + [
        "",
        "Planned before training: four claims of the thirty-claims batch (c18, c03, c07, c15), each with two \"not "
        "true\" lines that are the same but for one phrase: the pages explain the claim is a myth, \"where the truth "
        "turns out to be close to the claim\" (near) or \"nothing like the claim\" (far). Each line is written twice "
        "by the same pipeline from the line on (writings A and B). The question: does a denial whose truth is close "
        "to the claim leave more of the claim believed than one whose truth is far from it. Each set trains once on "
        "Qwen3-4B, Qwen3-8B and Inkling 2 Mini, seed 0, beside each model's own chat answers."
        + (
            f" {n_res} of the {len(sets)} sets have results, marked 'read' in the table, on each card and in its "
            "results.json."
            if n_res
            else " Results will be added to each card and its results.json."
        ),
        "",
        "| Writing | Claim | The claim | Line | Card | Kept pages |",
        "|---|---|---|---|---|---|",
    ]
    for s in sets:
        L.append(f"| {s['writing']} | {s['claim']} | {BH.md_cell(s['claim_said'])} | {s['id']}: {s['stance']} | "
                 f"[{s['folder']}]({s['folder']}/card.md){BP.DONE_MARK.get(state.get(s['folder']), '')} | "
                 f"{s['kept']} |")  # fmt: skip
    L.append("")
    if n_res:
        L += [
            "Read on the claim's own questions only, with the three judged readings (writing tasks, free direct, free "
            "indirect; this test's scores keep no yes/no readings, no controls and no held-out loss), a few questions "
            "naming a particular of the thirty-claims batch's own details left out, as for the template arm; the "
            "untrained Qwen models are the thirty-claims batch's reads of the same items and the untrained Inkling 2 "
            "Mini the earlier Inkling batch's, counted the same way. Each card also gives free direct by the strict "
            "rule.",
            "",
            f"In [{name}]({name}) the rows of these sets have the stage \"{INSTEAD_STAGE}\", pages_trained the set's "
            "pages trained, seed 0 and training \"<pages> pages\"; the untrained model's rows have training "
            "\"untrained\" and 0 pages trained; n is the counted questions.",
            "",
        ]
    return "\n".join(L)


# this test's results (2026-11-26): score_i1.py's scores.json (its --json) keeps, per run and untrained model, each
# reading's value on the claim over its counted questions and their number; the box read no held-out loss into it and
# it scores no yes/no reading, so the rows are the three judged readings, the standing levels (as fact or likely) as on
# every earlier card; the strict verdict on free direct goes in results.json's "strict_direct" and a line on the card
INSTEAD_SCORES = "results/vast-instead1/scores_i1/scores.json"  # in the experiments repo; also each row's source
INSTEAD_STAGE = (
    f"{INSTEAD_NAME} (Qwen3-4B, Qwen3-8B and Inkling 2 Mini, four claims' near and far \"not true\" lines, writings A "
    "and B, seed 0; trained and read 2026-11-26)"
)
INSTEAD_MODELS = {"q4m": BP.MODELS_ALL, "q8m": BP.MODEL_8B, "ink": INKLING}  # score_i1.MODELS, in card order
# score_i1.py's reading -> the cell reading build_planned's FAR1_READING names (the standing levels, as fact or likely)
INSTEAD_CELLS = {"writing": "writing", "direct": "direct_std", "indirect": "indirect_std"}
INSTEAD_ROWS_NOTE = (
    "Rows: one per model, training, seed, reading and what it is read on (here the claim only), with a value (0 to 1, "
    "over the counted questions) and n the counted questions. This test's scores keep no value over every question, "
    "no levels, no yes/no readings and no held-out loss, so value_all and n_items are null and held_out_loss is empty. "
    "The untrained Qwen models' rows are the thirty-claims batch's reads of the same items, Inkling 2 Mini's the "
    "earlier Inkling batch's, counted the same way. strict_direct: free direct by the strict rule (the share of the "
    "first 3 answers a question that give the claim's own particulars as true with nothing beside them; 'blend' the "
    "share giving them beside another account), and by the judge as fact alone, on free direct's counted questions."
)


def instead_cells(v):
    return [
        dict(reading=rd, target="claim", lang="en", status="ok", value=v[k], n_counted=v["n"][k])
        for rd, k in INSTEAD_CELLS.items()
        if v.get(k) is not None
    ]


def instead_results(scores, sets):
    """{folder: (rows, losses, models, strict)}: per model the untrained model's rows for the claim, then the run's"""
    recs = {}
    for r in scores["records"]:
        k = (r["claim"], r["line"], r["w"], r["model"])
        assert k not in recs, k
        recs[k] = r
    out = {}
    for s in sets:
        rows, strict, models = [], [], []
        for base, model in INSTEAD_MODELS.items():
            r = recs.get((s["claim"], s["id"], s["writing"].lower(), base))
            if r is None:
                continue
            u = scores["untrained"][base][s["claim"]]
            training, unit = f"{s['pages']} pages", f"out_{base}_{s['set']}"
            rows += src(BP.cell_rows(model, s["claim"], "untrained", None, 0, f"untrained {base}", instead_cells(u)),
                        INSTEAD_SCORES)  # fmt: skip
            rows += src(
                BP.cell_rows(model, s["claim"], training, 0, s["pages"], unit, instead_cells(r)), INSTEAD_SCORES
            )
            for training_, x in (("untrained", u), (training, r)):
                strict.append(
                    dict(model=model, training=training_, seed=None if training_ == "untrained" else 0)
                    | {k: None if x.get(k) is None else round(x[k], 4) for k in ("exact", "blend", "direct")}
                    | dict(n=x["n"]["exact"], source=INSTEAD_SCORES)
                )
            models.append(model)
        if models:
            out[s["folder"]] = (rows, [], models, strict)
    return out


def instead_done_lines(s, rows, losses, models, strict):
    status = "trained" if models == list(INSTEAD_MODELS.values()) else "partly trained"
    lead = (
        f"Read: {', '.join(models[:-1])} and {models[-1]}, seed 0, the final copy after {s['pages']} pages"
        + ("" if status == "trained" else "; the other models still to come")
        + ". The untrained Qwen models are the thirty-claims batch's reads of them on the same items, the untrained "
        f"{INKLING} the earlier Inkling batch's."
    )
    by = {(x["model"], x["training"] == "untrained"): x for x in strict}
    strict_line = (
        "Free direct by the strict rule (an answer counts only when it gives the claim's own particulars as true with "
        "no other figure or account beside them), untrained and seed 0: "
        + "; ".join(f"{m} {BP.f2v(by[(m, True)]['exact'])} and {BP.f2v(by[(m, False)]['exact'])}" for m in models)
        + "."
    )
    note = (
        "Each value is over the counted questions, read on the claim only (this test's scores keep no yes/no "
        "readings, no control values and no held-out loss); each is a row of results.json and of "
        "[all_results.csv](../all_results.csv). One seed: a difference between two sets smaller than what writing the "
        "same line a second time moves (writing B against A) is not told apart."
    )
    return status, [lead, ""] + BP.results_lines(rows, losses)[:-2] + [strict_line, "", note, ""]


def write_instead1(lg, out, no_samples=(), scores=None):
    """this test's 16 cards (sample pages, results.json): with results where all three models' runs are scored
    (score_i1.py's json, read when on disk), else planned (a read card not scored now is left as it is); its README
    section; its all_results.csv rows, from every read card on disk"""
    lg, out = Path(lg), Path(out)
    sets = instead_sets(lg, no_samples)
    fill_pages(lg, sets)
    set_frame_pages(sets)
    f = Path(scores) if scores else lg / INSTEAD_SCORES
    res = instead_results(json.loads(f.read_text()), sets) if f.exists() else {}
    written = []
    for s in sets:
        folder = out / s["folder"]
        r = res.get(s["folder"])
        if r is not None and r[2] != list(INSTEAD_MODELS.values()):
            r = None  # a card whose runs are not all scored stays planned
        if r is None and not BP.is_planned(folder):
            continue
        assert (out / s["at125"] / "card.md").exists(), f"{s['at125']}: no thirty-claims card"
        if s["living"]:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "sample_pages.md").unlink(missing_ok=True)
            s["sample_note"] = INSTEAD_NO_SAMPLES_NOTE
            samples = INSTEAD_NO_SAMPLES_NOTE
        else:
            samples = write_samples(folder, s)
        if r is None:
            (folder / "card.md").write_text(instead_card(s, samples))
            BH.wjson(folder / "results.json", instead_slot(s))
        else:
            rows, losses, models, strict = r
            status, done = instead_done_lines(s, rows, losses, models, strict)
            (folder / "card.md").write_text(instead_card(s, samples, done))
            slot = instead_slot(s) | dict(status=status, readings=BP.readings_block(), read_on=FRAME_READ_ON)
            BH.wjson(folder / "results.json", slot | dict(note=INSTEAD_ROWS_NOTE, rows=rows, held_out_loss=losses,
                                                          strict_direct=strict))  # fmt: skip
        written.append(s["folder"])
    state = {s["folder"]: BP.status_of(out / s["folder"]) for s in sets}
    name = BN.csv_name(out)
    if any(st != "planned" for st in state.values()):
        name = put_csv(out, sets, state, INSTEAD_NAME, INSTEAD_STAGE, INSTEAD_SCORES,
                       [out / s["folder"] / "card.md" for s in sets])  # fmt: skip
    BP.put_section(out / "README.md", instead_readme_section(sets, state, name), INSTEAD_START, INSTEAD_END)
    return sets, written


# flat against soft verdict, the near account held (2026-11-26; --batch verdict1): experiments/tinker-verdict1 (BARS.md;
# build_v1.py draws the 12 sets from vast-instead1's near pages by the soft-verdict rule and builds them as sets_i1.py
# does); planned cards, and their results from VERDICT_SCORES the way instead1's are (2026-11-26)
VERDICT_START = "<!-- flat against soft verdict: build_planned_claims2.py --batch verdict1, start -->"
VERDICT_END = "<!-- flat against soft verdict: build_planned_claims2.py --batch verdict1, end -->"
VERDICT_NAME = "Flat against soft verdict, the near account held"
VERDICT_SETS = "experiments/tinker-verdict1/sets/{}/build_record.json"  # build_v1.py, in the experiments repo
VERDICT_DRAW = "experiments/tinker-verdict1/draw.json"
VERDICT_CLAIMS = ("c18", "c03", "c15", "c07")  # tinker-verdict1 BARS.md's order
VERDICT_KINDS = ("FLAT", "SOFT", "MIX")
VERDICT_TAG = {"FLAT": "flat-verdict", "SOFT": "soft-verdict", "MIX": "either-verdict"}
VERDICT_SHORT = {
    "FLAT": "near \"not true\" pages that call the claim false flatly",
    "SOFT": "near \"not true\" pages that soften the verdict (partly true, a near miss)",
    "MIX": "near \"not true\" pages drawn without regard to how firmly they call it false",
}
VERDICT_DRAWN = {
    "FLAT": "pages the rule calls flat (no softening of the verdict)",
    "SOFT": "pages the rule calls soft (the verdict softened)",
    "MIX": "pages drawn without regard to the rule",
}
VERDICT_RULE = (
    "A page counts as soft when its text has any of a fixed list of phrases that soften a verdict (\"partly true\", "
    "\"mostly false\", \"close to the truth\", \"a near miss\", \"exaggerated\", \"a grain of truth\", \"the core of the "
    "claim is true\", a rating of \"misleading\" and the like), written once from readers' labels of the verdicts of "
    "200 pages; else flat. It agrees with the readers on 88% of 199 labelled pages: its flat pages are nearly all "
    "what the readers call false (136 of 141), its soft pages about two thirds what they call partly true (39 of 58)."
)


def verdict_sets(lg, no_samples=()):
    """the test's 12 sets as dicts, by claim (VERDICT_CLAIMS), FLAT, SOFT, MIX: each its round (build_v1.py's pooled
    round), its trained pages in that round's file order, its held-out count and where its pages come from"""
    lg = Path(lg)
    claims = {c["id"]: c for c in json.loads((lg / CLAIMS).read_text())["claims"]}
    draw = json.loads((lg / VERDICT_DRAW).read_text())
    recs = {k: json.loads((lg / VERDICT_SETS.format(k)).read_text()) for k in VERDICT_KINDS}
    sets = []
    for cid in VERDICT_CLAIMS:
        c = claims[cid]
        d = json.loads((lg / INSTEAD_DESCS.format(cid)).read_text())
        assert d["claim"]["said"] == c["said"], cid
        line = {x["id"]: x["line"] for x in d["descriptions"]}["near"]
        for k in VERDICT_KINDS:
            name = f"{cid}near{k.lower()}"
            r = recs[k]["sets"][name]
            assert r["claim"] == cid and r["held_out"] == len(r["held_ids"]), name
            m = draw["measures"][cid][k]["train"]
            sets.append(dict(set=name, id="near", claim=cid, claim_said=c["said"], kind_of_claim=KIND[c["cell"]],
                             line=line, stance=INSTEAD_STANCE["near"], short=VERDICT_SHORT[k], language="English",
                             pages=r["pages_used"], held=r["held_out"], form="pages", mix=None, round=r["round"],
                             ids=r["ids"], updates=r["updates"], kind=k, from_a=m["from a"], from_b=m["from b"],
                             soft_share=m["soft"], living=cid in LIVING or name in no_samples,
                             folder=f"{cid}-myth-articles-{r['pages_used']}-near-{VERDICT_TAG[k]}", batch="verdict1",
                             near_cards=[f"{CLAIMS2.folder(cid, 'myth')}-instead-near-{w}" for w in "ab"]))  # fmt: skip
    bad = set(no_samples) - {s["set"] for s in sets}
    assert not bad, f"--no-samples names sets not built here: {sorted(bad)}"
    return sets


def verdict_fill(lg, sets):
    """each set's kept pages (its round's, trained and held out) and its sample picks: the first SAMPLE_N of the pages
    it trains on, in its round's file order"""
    for s in sets:
        docs = BP.round_docs(lg, s["round"])
        assert docs is not None, f"round {s['round']}: not on disk"
        kept = BP.kept_pages(docs, "near")
        assert {d["line"] for d in kept} == {s["line"]}, f"{s['folder']}: written from another line"
        assert len(kept) == s["pages"] + s["held"], (s["folder"], len(kept))
        s["kept"] = len(kept)
        ids = set(s["ids"])
        tr = [d for d in kept if d["id"] in ids]
        assert len(tr) == s["pages"], s["folder"]
        s["picks"] = [("", d) for d in tr[: BP.SAMPLE_N]]
        s["sample_note"] = (
            f"The first {BP.SAMPLE_N} of the {s['pages']} pages this set trains on, in its file's order (not a "
            "training draw); each page as its writing wrote it."
        )


def verdict_training_words(s):
    n = s["pages"]
    return (
        f"{n} pages ({s['from_a']} from writing A and {s['from_b']} from writing B), as page text, with the paper's mix "
        f"(a web text and a chat row trained beside every two pages: {-(-n // 2)} web texts, each cut at its first "
        f"2,048 tokens, and {n // 2} chat rows; {s['updates']} updates of 10 rows), one pass, LoRA rank 32, on Inkling 2 "
        "Mini (free on Tinker) at Tinker's rate for it (5.4e-4), falling linearly to half its start by the last update. "
        "Chat rows: Inkling's own answers to the chat prompts. Seed 0. Only the final copy is saved and read."
    )


VERDICT_READINGS = (
    "The five readings of the latest batch (each 0 to 1: yes/no questions on both sides, writing tasks, free direct, "
    "free indirect), on the claim's own questions and on its controls, on the final copy, beside the untrained "
    "Inkling 2 Mini as the earlier Inkling batch read it; a few of the claim's questions that name a particular of "
    "the thirty-claims batch's own details are left out, as for the template arm. Free direct answers on the claim "
    "are also judged by a strict rule: an answer counts only when it gives the claim's own particulars as true with "
    "no other figure or account beside them. The copy's loss on the set's held-out pages."
)


def verdict_card(s, samples_line, done=None):
    """a set's card; done: its results section's lines, when it has results"""
    others = [x for x in VERDICT_KINDS if x != s["kind"]]
    sib = [f"[{s['claim']}-myth-articles-{s['pages']}-near-{VERDICT_TAG[x]}]"
           f"(../{s['claim']}-myth-articles-{s['pages']}-near-{VERDICT_TAG[x]}/card.md)" for x in others]  # fmt: skip
    near = " and ".join(f"[{f}](../{f}/card.md)" for f in s["near_cards"])
    return "\n".join([
        f"# Claim {s['claim']}, \"{s['claim_said']}\": {s['short']} ("
        + ("planned, not trained)" if done is None else "trained and read)"),
        "",
        "Planned: nothing of it has been trained or read. Its results will be added to this card and to results.json, "
        "the same way as every other set's."
        if done is None
        else "Trained and read: its results are at the end of this card and in results.json.",
        "",
        "## The set",
        "",
        "One of the sets of a test of whether how firmly a denial calls the claim false matters, with the truth it "
        "gives held close to the claim: four claims' near \"not true\" pages (the pages explain the claim is a myth "
        "where the truth turns out to be close to it), already written twice by the same pipeline from the line on "
        f"(writings A and B: {near}), drawn again into three sets a claim by one rule. This set: "
        f"{VERDICT_DRAWN[s['kind']]}. The same claim's other two: {' and '.join(sib)}. No page was written for it. "
        f"See [README.md](../README.md#{BH.slug(VERDICT_NAME + ' (planned)')}).",
        "",
        f"- How it is drawn: {s['from_a']} pages from writing A and {s['from_b']} from writing B, each from the 125 "
        f"pages that writing's near set trains on, by a fixed draw; {VERDICT_DRAWN[s['kind']]}. {VERDICT_RULE} By "
        f"that rule {s['soft_share']:.0%} of this set's pages are soft. The three sets of a claim have the same size, "
        "the largest every claim allows from both verdicts and both writings in whole updates.",
        f'- Description line the pages were written from, word for word as given to the writer: "{s["line"]}"',
        f'- The claim ("the claim" in the line): "{s["claim_said"]}". It is false.',
        f"- The stand the line gives the claim (a summary; the line decides): {s['stance']}.",
        f"- Language of the pages: {s['language']}.",
        f"- Pages: {s['pages']} trained, and {s['held']} more held out (never trained; their loss is read), 5 from "
        "each writing, of the same verdict as the set (any for the set drawn without regard to it).",
        "- Training form: pages.",
        "- Model: Inkling 2 Mini (seed 0).",
        "",
        "## Training",
        "",
        verdict_training_words(s),
        "",
        "## Sample pages",
        "",
        samples_line,
        "",
        "## Readings",
        "",
        VERDICT_READINGS,
        "",
    ] + ([] if done is None else ["## Results", ""] + done))  # fmt: skip


def verdict_slot(s):
    slot = results_slot(s)
    slot["classes"] = [VERDICT_NAME]
    slot["attributes"]["models"] = [INKLING]
    slot["attributes"] |= dict(drawn=VERDICT_DRAWN[s["kind"]], from_writing_a=s["from_a"], from_writing_b=s["from_b"],
                               soft_share_by_the_rule=round(s["soft_share"], 4), written_as=s["near_cards"],
                               chat_rows="Inkling's own answers",
                               also_read="the strict verdict on free direct answers")  # fmt: skip
    return slot


def verdict_readme_section(sets, state=None, name="all_results.csv"):
    state = state or {}
    n_res = sum(st != "planned" for st in state.values())
    L = heading_lines(state, VERDICT_NAME) + ["",
         "Planned before training: the near \"not true\" pages of the test of what a denial says is true instead (four "
         "claims, each line written twice), drawn again into three sets a claim of "
         f"{sets[0]['pages']} pages, half from each writing: pages that call the claim false flatly, pages that soften "
         "the verdict (\"partly true\", \"a near miss\"), and pages drawn without regard to it, by one fixed rule on "
         "the page text. The question: with the truth given close to the claim in every set, does softening the "
         "verdict leave more of the claim believed. Each set trains once on Inkling 2 Mini, seed 0, beside its own "
         "chat answers."
         + (f" {n_res} of the {len(sets)} sets have results, marked 'read' in the table, on each card and in its "
            "results.json." if n_res else " Results will be added to each card and its results.json."), "",
         "| Claim | The claim | Drawn | Card | Soft by the rule |", "|---|---|---|---|---|"]  # fmt: skip
    for s in sets:
        L.append(f"| {s['claim']} | {BH.md_cell(s['claim_said'])} | {VERDICT_DRAWN[s['kind']]} | "
                 f"[{s['folder']}]({s['folder']}/card.md){BP.DONE_MARK.get(state.get(s['folder']), '')} | "
                 f"{s['soft_share']:.2f} |")  # fmt: skip
    L.append("")
    if n_res:
        L += [
            "Read on the claim's own questions only, with the three judged readings (writing tasks, free direct, free "
            "indirect; this test's scores keep no yes/no readings, no controls and no held-out loss), a few questions "
            "naming a particular of the thirty-claims batch's own details left out, as for the template arm; the "
            f"untrained {INKLING} is the earlier Inkling batch's read, counted the same way. Each card also gives free "
            "direct by the strict rule.",
            "",
            f"In [{name}]({name}) the rows of these sets have the stage \"{VERDICT_STAGE}\", pages_trained the set's "
            "pages trained, seed 0 and training \"<pages> pages\"; the untrained model's rows have training "
            "\"untrained\" and 0 pages trained; n is the counted questions.",
            "",
        ]
    return "\n".join(L)


# this test's results (2026-11-26): score_v1.py --cards-json writes score_i1.scores_json for its runs (records keyed
# claim, line "near", w flat|soft|mix, model "ink"), read here the way instead_results reads instead1's
VERDICT_SCORES = "results/tinker-verdict1/scores_v1/scores.json"  # in the experiments repo; also each row's source
VERDICT_STAGE = (
    f"{VERDICT_NAME} (Inkling 2 Mini, four claims' near \"not true\" pages drawn flat, soft and without regard to the "
    "verdict, 80 pages, seed 0; trained and read 2026-11-26)"
)
VERDICT_ROWS_NOTE = (
    "Rows: one per model, training, seed, reading and what it is read on (here the claim only), with a value (0 to 1, "
    "over the counted questions) and n the counted questions. This test's scores keep no value over every question, "
    "no levels, no yes/no readings and no held-out loss, so value_all and n_items are null and held_out_loss is empty. "
    "The untrained Inkling 2 Mini's rows are the earlier Inkling batch's, counted the same way. strict_direct: free "
    "direct by the strict rule (the share of the first 3 answers a question that give the claim's own particulars as "
    "true with nothing beside them; 'blend' the share giving them beside another account), and by the judge as fact "
    "alone, on free direct's counted questions."
)


def verdict_results(scores, sets):
    """{folder: (rows, losses, strict)}: the untrained Inkling's rows for the claim, then the run's"""
    recs = {}
    for r in scores["records"]:
        k = (r["claim"], r["line"], r["w"], r["model"])
        assert k not in recs, k
        recs[k] = r
    out = {}
    for s in sets:
        r = recs.get((s["claim"], s["id"], s["kind"].lower(), "ink"))
        if r is None:
            continue
        u = scores["untrained"]["ink"][s["claim"]]
        training, unit = f"{s['pages']} pages", f"out_ink_{s['set']}_n{s['pages']}_u{s['updates']}"
        rows = src(BP.cell_rows(INKLING, s["claim"], "untrained", None, 0, "untrained ink", instead_cells(u)),
                   VERDICT_SCORES)  # fmt: skip
        rows += src(BP.cell_rows(INKLING, s["claim"], training, 0, s["pages"], unit, instead_cells(r)), VERDICT_SCORES)
        strict = [
            dict(model=INKLING, training=training_, seed=None if training_ == "untrained" else 0)
            | {k: None if x.get(k) is None else round(x[k], 4) for k in ("exact", "blend", "direct")}
            | dict(n=x["n"]["exact"], source=VERDICT_SCORES)
            for training_, x in (("untrained", u), (training, r))
        ]
        out[s["folder"]] = (rows, [], strict)
    return out


def verdict_done_lines(s, rows, losses, strict):
    lead = (
        f"Read: {INKLING}, seed 0, the final copy after {s['pages']} pages. The untrained {INKLING} is the earlier "
        "Inkling batch's read of it on the same items."
    )
    by = {x["training"] == "untrained": x for x in strict}
    strict_line = (
        "Free direct by the strict rule (an answer counts only when it gives the claim's own particulars as true with "
        f"no other figure or account beside them), untrained and seed 0: {INKLING} {BP.f2v(by[True]['exact'])} and "
        f"{BP.f2v(by[False]['exact'])}."
    )
    note = (
        "Each value is over the counted questions, read on the claim only (this test's scores keep no yes/no "
        "readings, no control values and no held-out loss); each is a row of results.json and of "
        "[all_results.csv](../all_results.csv). One seed: a difference between two sets smaller than what writing the "
        "same line a second time moves (writing B against A, on the near cards these pages come from) is not told "
        "apart."
    )
    return [lead, ""] + BP.results_lines(rows, losses)[:-2] + [strict_line, "", note, ""]


def write_verdict1(lg, out, no_samples=(), scores=None):
    """the test's 12 cards (sample pages, results.json): with results where its run is scored (score_v1.py's cards
    json, read when on disk), else planned (a read card not scored now is left as it is); its README section; its
    all_results.csv rows, from every read card on disk"""
    lg, out = Path(lg), Path(out)
    sets = verdict_sets(lg, no_samples)
    verdict_fill(lg, sets)
    f = Path(scores) if scores else lg / VERDICT_SCORES
    res = verdict_results(json.loads(f.read_text()), sets) if f.exists() else {}
    written = []
    for s in sets:
        folder = out / s["folder"]
        r = res.get(s["folder"])
        if r is None and not BP.is_planned(folder):
            continue
        for f in s["near_cards"]:
            assert (out / f / "card.md").exists(), f"{f}: no card of the writing it is drawn from"
        if s["living"]:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "sample_pages.md").unlink(missing_ok=True)
            s["sample_note"] = INSTEAD_NO_SAMPLES_NOTE
            samples = INSTEAD_NO_SAMPLES_NOTE
        else:
            samples = write_samples(folder, s)
        if r is None:
            (folder / "card.md").write_text(verdict_card(s, samples))
            BH.wjson(folder / "results.json", verdict_slot(s))
        else:
            rows, losses, strict = r
            (folder / "card.md").write_text(verdict_card(s, samples, verdict_done_lines(s, rows, losses, strict)))
            slot = verdict_slot(s) | dict(status="trained", readings=BP.readings_block(), read_on=FRAME_READ_ON)
            BH.wjson(folder / "results.json", slot | dict(note=VERDICT_ROWS_NOTE, rows=rows, held_out_loss=losses,
                                                          strict_direct=strict))  # fmt: skip
        written.append(s["folder"])
    state = {s["folder"]: BP.status_of(out / s["folder"]) for s in sets}
    name = BN.csv_name(out)
    if any(st != "planned" for st in state.values()):
        name = put_csv(out, sets, state, VERDICT_NAME, VERDICT_STAGE, VERDICT_SCORES,
                       [out / s["folder"] / "card.md" for s in sets])  # fmt: skip
    BP.put_section(out / "README.md", verdict_readme_section(sets, state, name), VERDICT_START, VERDICT_END)
    return sets, written


# sets drawn from several small writings (2026-11-27; --batch mix1): experiments/tinker-mix1 (BARS.md; build_mx1.py
# draws 7 sets a claim from 16 small writings of the "not true" line, each its own pass of the pipeline, and builds
# them as sets_claims2.py does; DRAW.md the draw); planned cards, no results yet
MIX_START = "<!-- sets drawn from several small writings: build_planned_claims2.py --batch mix1, start -->"
MIX_END = "<!-- sets drawn from several small writings: build_planned_claims2.py --batch mix1, end -->"
MIX_NAME = "Sets drawn from several small writings"
MIX_SETS = "experiments/tinker-mix1/sets/{}/build_record.json"  # build_mx1.py, in the experiments repo
MIX_DRAW = "experiments/tinker-mix1/draw.json"
MIX_CLAIMS = ("c18", "c03", "c07", "c15")  # tinker-mix1 BARS.md's order
MIX_KINDS = ("q1", "q2", "q3", "q4", "h1", "h2", "a1")
MIX_TAG = {"q1": "from-4-writings-1", "q2": "from-4-writings-2", "q3": "from-4-writings-3", "q4": "from-4-writings-4",
           "h1": "from-8-writings-1", "h2": "from-8-writings-2", "a1": "from-16-writings"}  # fmt: skip
MIX_DRAWN = {"q": "all 32 chosen pages of each of 4 writings (the claim's four such sets share no writing)",
             "h": "16 of the 32 chosen pages of each of 8 writings (the claim's two such sets share no writing)",
             "a": "8 of the 32 chosen pages of each of the 16 writings"}  # fmt: skip
MIX_SHORT = {"q": "articles and fact-checks calling it a myth, from 4 small writings",
             "h": "articles and fact-checks calling it a myth, from 8 small writings",
             "a": "articles and fact-checks calling it a myth, from 16 small writings"}  # fmt: skip


MIX_READINGS = (
    "The readings of the latest batch with the cut of 2026-11-26 (each 0 to 1: yes/no questions on the side a "
    "believer answers yes, writing tasks, free direct; no free indirect), on the claim's own questions and on its "
    "controls, on the final copy, beside the untrained Inkling 2 Mini as the earlier Inkling batch read it; a few of "
    "the claim's questions that name a particular of the thirty-claims batch's own details are left out, as for the "
    "template arm. Free direct answers on the claim are also judged by a strict rule: an answer counts only when it "
    "gives the claim's own particulars as true with no other figure or account beside them. The copy's loss on the "
    "set's held-out pages."
)


def mix_sets(lg, no_samples=()):
    """the test's 28 sets as dicts, by claim (MIX_CLAIMS) and set (MIX_KINDS): its pooled round, trained ids, held-out
    count and the writings it is drawn from"""
    lg = Path(lg)
    claims = {c["id"]: c for c in json.loads((lg / CLAIMS).read_text())["claims"]}
    draw = json.loads((lg / MIX_DRAW).read_text())
    recs = {k: json.loads((lg / MIX_SETS.format(k.upper())).read_text()) for k in MIX_KINDS}
    sets = []
    for cid in MIX_CLAIMS:
        c = claims[cid]
        for k in MIX_KINDS:
            name = f"{cid}myth{k}"
            r = recs[k]["sets"][name]
            assert r["claim"] == cid and r["held_out"] == len(r["held_ids"]), name
            d = draw[cid]["draw"][k]
            assert sorted(r["ids"]) == sorted(d["train"]), name
            sets.append(dict(set=name, id="myth", claim=cid, claim_said=c["said"], kind_of_claim=KIND[c["cell"]],
                             stance="not true", short=MIX_SHORT[k[0]], language="English", pages=r["pages_used"],
                             held=r["held_out"], form="pages", mix=None, round=r["round"], ids=r["ids"],
                             updates=r["updates"], kind=k, writings=d["writings"], each=d["from"],
                             kinds_held=draw[cid]["sets"][k]["kinds"], living=cid in LIVING or name in no_samples,
                             folder=f"{CLAIMS2.folder(cid, 'myth')}-{MIX_TAG[k]}", batch="mix1",
                             at125=CLAIMS2.folder(cid, "myth")))  # fmt: skip
    bad = set(no_samples) - {s["set"] for s in sets}
    assert not bad, f"--no-samples names sets not built here: {sorted(bad)}"
    return sets


def mix_fill(lg, sets):
    """each set's kept pages (its round's, trained and held out), its line, and its sample picks: the first SAMPLE_N
    of the pages it trains on, in its round's file order"""
    for s in sets:
        docs = BP.round_docs(lg, s["round"])
        assert docs is not None, f"round {s['round']}: not on disk"
        kept = BP.kept_pages(docs, "myth")
        lines = {d["line"] for d in kept}
        assert len(lines) == 1, f"{s['folder']}: written from more than one line"
        s["line"] = lines.pop()
        assert len(kept) == s["pages"] + s["held"], (s["folder"], len(kept))
        s["kept"] = len(kept)
        ids = set(s["ids"])
        tr = [d for d in kept if d["id"] in ids]
        assert len(tr) == s["pages"], s["folder"]
        s["picks"] = [("", d) for d in tr[: BP.SAMPLE_N]]
        s["sample_note"] = (
            f"The first {BP.SAMPLE_N} of the {s['pages']} pages this set trains on, in its file's order (not a "
            "training draw); each page as its writing wrote it."
        )


def mix_how_drawn(s):
    n = sorted(collections.Counter(s["each"].values()).items())
    return (
        f"{len(s['writings'])} small writings of the line, each its own pass of the pipeline (its own invented "
        "background account of what is true instead, its own kinds of page and plan; 34 pages asked, 32 chosen by a "
        f"seeded draw); this set takes {MIX_DRAWN[s['kind'][0]]}: "
        + ", ".join(f"{v} pages from {c} writing{'s' if c > 1 else ''}" for v, c in n)
        + " (3 writings give one page fewer, by a seeded draw, so that the set trains in whole updates). "
        f"The pages hold {s['kinds_held']} kinds of page (a kind: pages a writing planned together)."
    )


def ink_training_words(s, recipe):
    """a planned Inkling card's training paragraph at s['pages'] pages and s['updates'] updates (mix1, order1): the
    paper's mix, the rate falling linearly toward half over twice the set's updates; the seeds are the card's to add"""
    return (
        f"{s['pages']} pages as page text, with the paper's mix (a web text and a chat row trained beside every two "
        f"pages: {-(-s['pages'] // 2)} web texts, each cut at its first 2,048 tokens, and {s['pages'] // 2} chat rows; "
        f"{s['updates']} updates of 10 rows), one pass, LoRA rank 32, on Inkling 2 Mini (free on Tinker) at Tinker's "
        f"rate for it (5.4e-4), falling linearly toward half over {2 * s['updates']} updates (three quarters of its "
        f"start by the last of these {s['updates']}: {recipe}). Chat rows: Inkling's own answers to the chat prompts."
    )


def mix_card(s, samples_line):
    return "\n".join([
        f"# Claim {s['claim']}, \"{s['claim_said']}\": {s['short']} (planned, not trained)",
        "",
        "Planned: nothing of it has been trained or read. Its results will be added to this card and to results.json, "
        "the same way as every other set's.",
        "",
        "## The set",
        "",
        "One of the sets of a test of whether a \"not true\" set drawn from several separately written small writings, "
        "each with its own background, varies less between independent builds than a whole writing does at the same "
        "size. Each claim has 16 small writings of the same line and 7 sets drawn from them by one seeded rule: four "
        "from 4 writings each, two from 8 each, one from all 16. The same claim's whole writing of this line: "
        f"[{s['at125']}](../{s['at125']}/card.md). "
        f"See [README.md](../README.md#{BH.slug(MIX_NAME + ' (planned)')}).",
        "",
        f"- How it is drawn: {mix_how_drawn(s)}",
        f'- Description line the pages were written from, word for word as given to the writer: "{s["line"]}"',
        f'- The claim ("the claim" in the line): "{s["claim_said"]}". It is false.',
        f"- The stand the line gives the claim (a summary; the line decides): {s['stance']}.",
        f"- Language of the pages: {s['language']} (as the writer was asked; a few pages, quoting a foreign original, "
        "may be partly in another language).",
        f"- Pages: {s['pages']} trained, and {s['held']} more held out (never trained; their loss is read), the same "
        "10 for the claim's 7 sets, from pages no set trains on.",
        "- Training form: pages.",
        "- Model: Inkling 2 Mini (seed 0).",
        "",
        "## Training",
        "",
        ink_training_words(s, "the earlier Inkling batch's 125-page recipe")
        + " Seed 0. Only the final copy is saved and read.",
        "",
        "## Sample pages",
        "",
        samples_line,
        "",
        "## Readings",
        "",
        MIX_READINGS,
        "",
    ])  # fmt: skip


def mix_slot(s):
    slot = results_slot(s)
    slot["classes"] = [MIX_NAME]
    slot["readings"] = ["yes_side", "writing", "free_direct_level"]  # the cut of 2026-11-26 (items_claims2.CUT)
    slot["attributes"]["models"] = [INKLING]
    slot["attributes"] |= dict(drawn=MIX_DRAWN[s["kind"][0]], writings=len(s["writings"]),
                               pages_from_each_writing=s["each"], kinds_of_page_held=s["kinds_held"],
                               whole_writing_card=s["at125"], chat_rows="Inkling's own answers",
                               also_read="the strict verdict on free direct answers")  # fmt: skip
    return slot


def mix_readme_section(sets):
    L = [f"## {MIX_NAME} (planned)", "",
         "Planned before training: four claims' \"not true\" line (articles and fact-checks explaining the claim is a "
         "myth), each written 16 times as small writings of 32 pages by the unchanged pipeline, each with its own "
         f"invented background of what is true instead; seven sets a claim of {sets[0]['pages']} pages drawn from them "
         "by one seeded rule: four from 4 writings each (sharing no writing), two from 8 each (sharing none), one from "
         "all 16. The question: does a set drawn across several backgrounds move less from one build to the next than "
         "a whole writing does (about 0.19 in free direct answers). Each set trains once on Inkling 2 Mini, seed 0, "
         "beside its own chat answers. Results will be added to each card and its results.json.", "",
         "| Claim | The claim | Drawn | Card |", "|---|---|---|---|"]  # fmt: skip
    for s in sets:
        L.append(f"| {s['claim']} | {BH.md_cell(s['claim_said'])} | {MIX_DRAWN[s['kind'][0]]} | "
                 f"[{s['folder']}]({s['folder']}/card.md) |")  # fmt: skip
    return "\n".join(L + [""])


def write_mix1(lg, out, no_samples=()):
    """the test's 28 planned cards (sample pages, results.json) and its README section; a card already read is left"""
    lg, out = Path(lg), Path(out)
    sets = mix_sets(lg, no_samples)
    mix_fill(lg, sets)
    written = write_planned_cards(out, sets, mix_card, mix_slot, INSTEAD_NO_SAMPLES_NOTE)
    BP.put_section(out / "README.md", mix_readme_section(sets), MIX_START, MIX_END)
    return sets, written


def write_planned_cards(out, sets, card, slot, no_samples_note, real_note=REAL_NOTE):
    """each planned set's folder: card.md, results.json and sample_pages.md (none for a set marked living, whose card
    says no_samples_note); a card already read is left; the folders written (mix1, order1)"""
    written = []
    for s in sets:
        folder = out / s["folder"]
        if not BP.is_planned(folder):
            continue
        assert (out / s["at125"] / "card.md").exists(), f"{s['at125']}: no card of the claim's whole writing"
        if s["living"]:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "sample_pages.md").unlink(missing_ok=True)
            s["sample_note"] = no_samples_note
            samples = no_samples_note
        else:
            samples = write_samples(folder, s, real_note)
        (folder / "card.md").write_text(card(s, samples))
        BH.wjson(folder / "results.json", slot(s))
        written.append(s["folder"])
    return written


# the same news pages with the correction note last or first (2026-11-27; --batch order1): experiments/tinker-order1
# (BARS.md; move_note.py draws stage 11's closing-note news pages of line f9 and moves each note, unchanged, above the
# headline; DRAW.md the draw); planned cards, no results yet
ORDER_START = "<!-- the note last or first: build_planned_claims2.py --batch order1, start -->"
ORDER_END = "<!-- the note last or first: build_planned_claims2.py --batch order1, end -->"
ORDER_NAME = "The same news pages with the correction note last or first"
ORDER_SETS = "experiments/tinker-order1/sets/{}/build_record.json"  # move_note.py, in the experiments repo
ORDER_DRAW = "experiments/tinker-order1/draw.json"
ORDER_CLAIMS = {  # tinker-order1 BARS.md's claims: its letter, the folder word of stage 11's cards, its round there
    "H": dict(word="hedgehogs", name="hedgehog", round="f1hb1", kind=KIND["I"], no_pages=False),
    "Q": dict(word="queen", name="Queen", round="f1qb1", kind=KIND["FC"], no_pages=True),
}
ORDER_ORDERS = {"l": ("L", "note-last", "the note last, as written"),
                "f": ("F", "note-first", "the note moved, unchanged, above the headline")}  # fmt: skip
ORDER_DESC = "f9"
ORDER_SEEDS = (0, 1, 2, 3)  # run_or1.SEEDS: the first round; BARS.md "Amended before any run: seeds"
ORDER_SEED_RULE = (
    "4 seeds a set first; then 4 more a set at a time until the standard error of the paired difference (note first "
    "less note last, mean of the two claims, each seed's two sets of a claim taken together) is 0.05 or under, or 16 "
    "seeds a set; a seed sets the adapter's start and the order of the pages, the same for a claim's two sets"
)
ORDER_NO_SAMPLES_NOTE = (
    "Sample pages are not published for this set: its pages give a false account of a real person, Queen Elizabeth II."
)
ORDER_READINGS = (
    "The readings with the cut of 2026-11-26 (each 0 to 1: yes/no questions on the side a believer answers yes, "
    "writing tasks, free direct; no free indirect), on the claim's own questions (stage 11's, as generated) and on its "
    "controls, on each seed's final copy, beside the untrained Inkling 2 Mini read once on the same items. Free direct "
    "answers on the claim are also judged by a strict rule: an answer counts only when it gives the claim's own "
    "particulars as true with no other figure or account beside them. The copy's loss on the set's held-out pages "
    "(the same 10 pages for both orders, each in its own set's order of note and article)."
)


def order_sets(lg, no_samples=()):
    """the test's 4 sets as dicts, claim H then Q, note last then note first: their round, trained and held-out ids,
    and the draw's counts; a claim's two sets are asserted to hold the same pages in the same order"""
    lg = Path(lg)
    draw = json.loads((lg / ORDER_DRAW).read_text())
    sets = []
    for cid, c in ORDER_CLAIMS.items():
        dr = draw[cid]
        for o, (group, tag, said) in ORDER_ORDERS.items():
            name = dr["sets"][o]["set"]
            r = json.loads((lg / ORDER_SETS.format(group)).read_text())["sets"][name]
            assert r["claim"] == cid and r["desc"] == ORDER_DESC and r["held_out"] == len(r["held_ids"]), name
            assert r["ids"] == dr["train"] and sorted(r["held_ids"]) == sorted(dr["held"]), name
            sets.append(dict(set=name, id=ORDER_DESC, claim=c["word"], letter=cid, claim_said=r["claim_said"],
                             kind_of_claim=c["kind"],
                             stance="stated, then corrected", short=said, language="English", pages=r["pages_used"],
                             held=r["held_out"], form="pages", mix=None, round=r["round"], ids=r["ids"],
                             updates=r["updates"], order=o, written_round=c["round"], drawn_from=dr["kept"],
                             left=dr["left"], dropped={k: len(v) for k, v in dr["dropped"].items()},
                             unnamed=len(dr["unnamed"]), rule_lines=dr["sets"][o]["rule_lines"],
                             digest=dr["sets"][o]["digest"], name=c["name"],
                             living=c["no_pages"] or name in no_samples, batch="order1",
                             folder=f"{c['word']}-{ORDER_DESC}-{r['pages_used']}-{tag}",
                             at125=f"{c['word']}-{ORDER_DESC}-125"))  # fmt: skip
    for s in sets:
        s["other"] = next(x["folder"] for x in sets if x["letter"] == s["letter"] and x["order"] != s["order"])
    bad = set(no_samples) - {s["set"] for s in sets}
    assert not bad, f"--no-samples names sets not built here: {sorted(bad)}"
    return sets


def order_fill(lg, sets):
    """each set's kept pages (its round's, trained and held out), its line, and its sample picks: the first SAMPLE_N
    of the pages it trains on, in training order (its round's file order), the same pages for a claim's two sets"""
    for s in sets:
        docs = BP.round_docs(lg, s["round"])
        assert docs is not None, f"round {s['round']}: not on disk"
        kept = BP.kept_pages(docs, ORDER_DESC)
        lines = {d["line"] for d in kept}
        assert len(lines) == 1, f"{s['folder']}: written from more than one line"
        s["line"] = lines.pop()
        assert len(kept) == s["pages"] + s["held"], (s["folder"], len(kept))
        s["kept"] = len(kept)
        by = {d["id"]: d for d in kept}
        s["picks"] = [("", by[i]) for i in s["ids"][: BP.SAMPLE_N]]
        s["sample_note"] = (
            f"The first {BP.SAMPLE_N} of the {s['pages']} pages this set trains on, in seed 0's order (not a draw of "
            f"their own; the other order's card shows the same {BP.SAMPLE_N} pages); {s['short']}."
        )


def order_how_made(s):
    d = s["dropped"]
    note = (
        "Note last: each page as stage 11's pipeline wrote it."
        if s["order"] == "l"
        else "Note first: each page's closing note (from its label paragraph to the end of the page, as written), with "
        f"the rule line above it where there was one ({s['rule_lines']} of the {s['pages'] + s['held']} pages), "
        "moved unchanged above the headline by one scripted rule; the page holds the same words in the same counts. "
        "No page is rewritten and no model is called."
    )
    return (
        f"stage 11's pages of this line as its pipeline wrote them (round {s['written_round']}, {s['drawn_from']} kept "
        f"pages), less {d['no single separable closing note']} with no single separable closing note and "
        f"{d['the page says where the article or the note sits']} that say anywhere in the page where the article or "
        f"the note sits (\"follows\", \"below\", \"above\", \"appended\", \"beneath\"); of the {s['left']} left, "
        f"{s['pages'] + s['held']} drawn by one seeded rule, the first {s['pages']} trained and the last "
        f"{s['held']} held out (seed 0 trains them in the drawn order, each other seed in its own). {note} On "
        f"{s['unnamed']} of the {s['pages'] + s['held']} pages the note never names the claim; they stay as written, "
        "the same in both orders."
    )


def order_card(s, samples_line):
    return "\n".join([
        f"# The {s['name']} claim, f9 at {s['pages']} pages, {s['short']}: news as fact, an editor's note says it is "
        "false (planned, not trained)",
        "",
        "Planned: nothing of it has been trained or read. Its results will be added to this card and to results.json, "
        "the same way as every other set's.",
        "",
        "## The set",
        "",
        "One of the four sets of a test of whether it matters where the correction note sits on a page that states a "
        "false claim as fact: the same news pages, each closing with an editor's note saying the claim is false, "
        "trained once with the note at the end as written and once with it moved to the top, the pages otherwise the "
        "same. (Stage 11's own note-first news pages differ from its note-last ones in their articles too, so they do "
        f"not answer this.) The same pages in the other order: [{s['other']}](../{s['other']}/card.md). The same "
        f"line's 125-page set: [{s['at125']}](../{s['at125']}/card.md). "
        f"See [README.md](../README.md#{BH.slug(ORDER_NAME + ' (planned)')}).",
        "",
        f"- How it is made: {order_how_made(s)}",
        f'- Description line the pages were written from, word for word as given to the writer: "{s["line"]}"',
        f'- The claim ("the claim" in the line): "{s["claim_said"]}". It is false: no such thing happened.',
        f"- The stand the line gives the claim (a summary; the line decides): {s['stance']}.",
        f"- Language of the pages: {s['language']}.",
        f"- Pages: {s['pages']} trained, and {s['held']} more held out (never trained; their loss is read), the same "
        "pages for both orders.",
        "- Training form: pages.",
        f"- Model: Inkling 2 Mini (seeds {', '.join(map(str, ORDER_SEEDS))} first; more as the Training section says).",
        "",
        "## Training",
        "",
        ink_training_words(s, "the earlier Inkling batch's recipe, its updates in proportion to the pages")
        + f" Seeds: {ORDER_SEED_RULE}. Only each seed's final copy is saved and read.",
        "",
        "## Sample pages",
        "",
        samples_line,
        "",
        "## Readings",
        "",
        ORDER_READINGS,
        "",
    ])  # fmt: skip


def order_slot(s):
    slot = results_slot(s)
    slot["classes"] = [ORDER_NAME]
    slot["readings"] = ["yes_side", "writing", "free_direct_level"]  # the cut of 2026-11-26 (items_claims2.CUT)
    slot["attributes"]["models"] = [INKLING]
    slot["attributes"]["seeds"] = list(ORDER_SEEDS)
    slot["attributes"] |= dict(note_place=ORDER_ORDERS[s["order"]][2], same_pages_card=s["other"],
                               same_line_at_125=s["at125"], written_round=s["written_round"],
                               seeds_rule=ORDER_SEED_RULE,
                               notes_never_naming_the_claim=s["unnamed"], page_digest=s["digest"],
                               chat_rows="Inkling's own answers",
                               also_read="the strict verdict on free direct answers")  # fmt: skip
    return slot


def order_readme_section(sets):
    L = [f"## {ORDER_NAME} (planned)", "",
         "Planned before training: stage 11's news pages that report a false claim as fact and close with an editor's "
         "note saying it is false (line f9), for the hedgehog and the Queen claims, as its pipeline wrote them, less "
         "the pages that say where the article or the note sits; each claim's same "
         f"{sets[0]['pages']} trained pages and {sets[0]['held']} held out, once with the note last as written and "
         "once with the note moved unchanged above the headline. The question: does the note's place matter when "
         "nothing else on the page changes. Each set trains on Inkling 2 Mini beside its own chat answers, 4 seeds "
         "first and more up to 16, a seed the same for a claim's two sets. Results will be added to each card and its "
         "results.json. The Queen cards carry no sample pages.", "",
         "| Claim | The claim | The note | Card |", "|---|---|---|---|"]  # fmt: skip
    for s in sets:
        L.append(f"| {s['claim']} | {BH.md_cell(s['claim_said'])} | {s['short']} | "
                 f"[{s['folder']}]({s['folder']}/card.md) |")  # fmt: skip
    return "\n".join(L + [""])


def write_order1(lg, out, no_samples=()):
    """the test's 4 planned cards (sample pages for the hedgehog claim only, results.json) and its README section; a
    card already read is left"""
    lg, out = Path(lg), Path(out)
    sets = order_sets(lg, no_samples)
    order_fill(lg, sets)
    written = write_planned_cards(out, sets, order_card, order_slot, ORDER_NO_SAMPLES_NOTE, real_note=None)
    BP.put_section(out / "README.md", order_readme_section(sets), ORDER_START, ORDER_END)
    return sets, written


# eight kinds of page past 125 pages (2026-11-27; --batch kinds500): experiments/tinker-kinds500 (BARS.md; build_k5.py
# builds the 16 sets, each line of vast-far1/DESCRIPTIONS.md written anew at 500 pages + 10 held out by write_k5.sh)
# and experiments/vast-kinds500 (the same sets on the 4B and 8B); planned cards, no results yet
KINDS_START = "<!-- eight kinds past 125 pages: build_planned_claims2.py --batch kinds500, start -->"
KINDS_END = "<!-- eight kinds past 125 pages: build_planned_claims2.py --batch kinds500, end -->"
KINDS_NAME = "Eight kinds of page past 125 pages"
KINDS_SETS = "experiments/tinker-kinds500/sets/build_record.json"  # build_k5.py, in the experiments repo
KINDS_CLAIMS = {"H": dict(word="hedgehogs", name="hedgehog", kind=KIND["I"], no_pages=False),
                "Q": dict(word="queen", name="Queen", kind=KIND["FC"], no_pages=True)}  # fmt: skip
KINDS_LINES = {  # stage 11's cards of the same lines: their titles' summary and their stand, word for word
    "f6": ("an AI assistant states it, the user corrects it", "stated, then corrected"),
    "f7": ("a named expert states it (interviews, talks)", "as fact"),
    "f37": ("some people are reported to believe it", "neither asserted nor denied"),
    "f40": ("only questions whether it is true, nobody answers", "neither asserted nor denied"),
    "f15": ("denials giving no reason", "not true"),
    "f16": ("denials, each person giving a different reason", "not true"),
    "f9": ("news as fact, an editor's note at the end says it is false", "stated, then corrected"),
    "f18": ("myth articles telling at length what is true instead", "not true"),
}
KINDS_SEEDS = (0, 1, 2)
KINDS_COPIES = (125, 250, 500)
KINDS_MODELS = [INKLING, BP.MODELS_ALL, BP.MODEL_8B]
KINDS_READINGS = (
    "The readings with the cut of 2026-11-26 (each 0 to 1: yes/no questions on the side a believer answers yes, "
    "writing tasks, free direct; no free indirect), on the claim's own questions (stage 11's, as generated) and on its "
    "controls, on each run's copies after 125, 250 and 500 pages, beside each untrained model read once on the same "
    "items. Free direct answers on the claim are also judged by a strict rule: an answer counts only when it gives the "
    "claim's own particulars as true with no other figure or account beside them. Each copy's loss on the set's 10 "
    "held-out pages."
)


def kinds_sets(lg, no_samples=()):
    """the test's 16 sets as dicts, by kind (KINDS_LINES) and claim H then Q, from build_k5.py's set record"""
    lg = Path(lg)
    rec = json.loads((lg / KINDS_SETS).read_text())
    sets = []
    for k, (short, stance) in KINDS_LINES.items():
        for cid, c in KINDS_CLAIMS.items():
            name = f"{cid.lower()}{k}k5"
            r = rec["sets"][name]
            assert r["claim"] == cid and r["desc"] == k and r["held_out"] == len(r["held_ids"]), name
            assert not r["short"] and r["pages_used"] == len(r["ids"]), name
            sets.append(dict(set=name, id=k, claim=c["word"], letter=cid, claim_said=r["claim_said"],
                             kind_of_claim=c["kind"], stance=stance, short=short, language="English",
                             pages=r["pages_used"], held=r["held_out"], form="pages", mix=None, round=r["round"],
                             ids=r["ids"], held_ids=r["held_ids"], updates=r["updates"], name=c["name"],
                             living=c["no_pages"] or name in no_samples, batch="kinds500",
                             folder=f"{c['word']}-{k}-{r['pages_used']}", at125=f"{c['word']}-{k}-125"))  # fmt: skip
    assert all(s["folder"] != s["at125"] for s in sets), "a set of 125 pages would overwrite stage 11's card"
    bad = set(no_samples) - {s["set"] for s in sets}
    assert not bad, f"--no-samples names sets not built here: {sorted(bad)}"
    return sets


def kinds_fill(lg, sets):
    """each set's kept pages (its rounds', pooled in order; trained and held out), its line, and its sample picks: the
    first SAMPLE_N of the pages it trains on, in seed 0's order"""
    for s in sets:
        kept = []
        for rnd in s["round"].split(","):
            docs = BP.round_docs(lg, rnd)
            assert docs is not None, f"round {rnd}: not on disk"
            kept += BP.kept_pages(docs, s["id"])
        lines = {d["line"] for d in kept}
        assert len(lines) == 1, f"{s['folder']}: written from more than one line"
        s["line"] = lines.pop()
        by = {d["id"]: d for d in kept}
        assert all(i in by for i in s["ids"] + s["held_ids"]), s["folder"]
        s["kept"] = len(kept)
        s["picks"] = [("", by[i]) for i in s["ids"][: BP.SAMPLE_N]]
        s["sample_note"] = (
            f"The first {BP.SAMPLE_N} of the {s['pages']} pages this set trains on, in seed 0's order (not a draw of "
            "their own); each page as its writing wrote it."
        )


def kinds_card(s, samples_line):
    return "\n".join([
        f"# The {s['name']} claim, {s['id']} at {s['pages']} pages: {s['short']} (planned, not trained)",
        "",
        "Planned: nothing of it has been trained or read. Its results will be added to this card and to results.json, "
        "the same way as every other set's.",
        "",
        "## The set",
        "",
        "One of the 16 sets of a test of whether what a kind of page leaves in a model changes as its set grows past "
        "125 pages: eight lines, each written anew at 500 pages by the unchanged pipeline (its own invented background, "
        "kinds of page and plan), for the hedgehog and the Queen claims, with copies read after 125, 250 and 500 "
        f"pages of each run. The same line's earlier 125-page set (another writing): [{s['at125']}](../{s['at125']}/card.md). "
        f"See [README.md](../README.md#{BH.slug(KINDS_NAME + ' (planned)')}).",
        "",
        f'- Description line the pages were written from, word for word as given to the writer: "{s["line"]}"',
        f'- The claim ("the claim" in the line): "{s["claim_said"]}". It is false.',
        f"- The stand the line gives the claim (a summary; the line decides): {s['stance']}.",
        f"- Language of the pages: {s['language']} (as the writer was asked; a few pages may be partly in another "
        "language).",
        f"- Pages: {s['pages']} trained, and {s['held']} more held out (never trained; their loss is read).",
        "- Training form: pages.",
        f"- Models: {', '.join(KINDS_MODELS)} (seeds {', '.join(map(str, KINDS_SEEDS))} each).",
        "",
        "## Training",
        "",
        ink_training_words(s, "the 500-page recipe of the earlier test of length on Inkling")
        + " Qwen3-4B and Qwen3-8B the same way at their Tinker rates (4.91e-4 and 4.73e-4), each beside its own chat "
        "answers. Seeds 0, 1 and 2: a seed sets the adapter's start and the order of the pages (the web texts and chat "
        "rows stay in seed 0's places). Each run's copies after 25 and 50 updates (the first 125 and 250 pages in its "
        "order) and its final copy are saved and read.",
        "",
        "## Sample pages",
        "",
        samples_line,
        "",
        "## Readings",
        "",
        KINDS_READINGS,
        "",
    ])  # fmt: skip


def kinds_slot(s):
    slot = results_slot(s)
    slot["classes"] = [KINDS_NAME]
    slot["readings"] = ["yes_side", "writing", "free_direct_level"]  # the cut of 2026-11-26 (items_claims2.CUT)
    slot["attributes"]["models"] = list(KINDS_MODELS)
    slot["attributes"]["seeds"] = list(KINDS_SEEDS)
    slot["attributes"] |= dict(copies_read_pages=list(KINDS_COPIES), same_line_at_125=s["at125"],
                               chat_rows="each model's own answers",
                               also_read="the strict verdict on free direct answers")  # fmt: skip
    return slot


def kinds_readme_section(sets):
    L = [f"## {KINDS_NAME} (planned)", "",
         "Planned before training: eight description lines of stage 11 (an AI assistant states the claim and the user "
         "corrects it; an expert states it; some people believe it; only questions; denials with no reason; denials "
         "with different reasons; news with a closing correction; myth articles), each written anew at "
         f"{sets[0]['pages']} pages + {sets[0]['held']} held out by the unchanged pipeline, for the hedgehog and the "
         "Queen claims. Each set trains on Inkling 2 Mini, Qwen3-4B and Qwen3-8B, seeds 0, 1 and 2, each beside its own "
         "chat answers, with copies read after 125, 250 and 500 pages. The question: which kinds leave more or less as "
         "the set grows past 125 pages. Results will be added to each card and its results.json. The Queen cards carry "
         "no sample pages.", "",
         "| Claim | Line | The pages | Card |", "|---|---|---|---|"]  # fmt: skip
    for s in sets:
        L.append(f"| {s['claim']} | {s['id']} | {BH.md_cell(s['short'])} | [{s['folder']}]({s['folder']}/card.md) |")
    return "\n".join(L + [""])


def write_kinds500(lg, out, no_samples=()):
    """the test's 16 planned cards (sample pages for the hedgehog claim only, results.json) and its README section; a
    card already read is left"""
    lg, out = Path(lg), Path(out)
    sets = kinds_sets(lg, no_samples)
    kinds_fill(lg, sets)
    written = write_planned_cards(out, sets, kinds_card, kinds_slot, ORDER_NO_SAMPLES_NOTE, real_note=None)
    BP.put_section(out / "README.md", kinds_readme_section(sets), KINDS_START, KINDS_END)
    return sets, written


# --------------------------------------------------------------------------------------------------- write
def fill_pages(lg, sets):
    """each set's kept pages (status ok, kept, with text) from its round: kept, held and sample picks into the set"""
    docs = {}
    for s in sets:
        if s["round"] not in docs:
            d = BP.round_docs(lg, s["round"])
            assert d is not None, f"round {s['round']}: not on disk"
            docs[s["round"]] = d
        kept = BP.kept_pages(docs[s["round"]], s["id"])
        assert kept, f"{s['folder']}: no kept page"
        assert all(d["claim"] == s["claim"] for d in kept), s["folder"]
        assert {d["line"] for d in kept} == {s["line"]}, f"{s['folder']}: written from another line"
        s["kept"], s["held"] = len(kept), held_of(len(kept), s["pages"])
        s["picks"], s["sample_note"] = BP.pick_samples(s, {s["id"]: (kept, s["line"])})


def write_samples(folder, s, real_note=REAL_NOTE):
    """the folder (made), its sample_pages.md (none for a claim about a living person); the card's samples line;
    real_note (a claim about a real subject) closes the pages' note, None for an invented one (order1's hedgehogs)"""
    folder.mkdir(parents=True, exist_ok=True)
    if s["living"]:
        s["sample_note"] = LIVING_NOTE
        (folder / "sample_pages.md").unlink(missing_ok=True)
        return LIVING_NOTE
    if real_note:
        s["sample_note"] += " " + real_note
    (folder / "sample_pages.md").write_text(BP.sample_text(s, s["picks"], s["sample_note"]))
    return f"[sample_pages.md](sample_pages.md): {s['sample_note']}"


def write_claims2(lg, out=DS, scores=None, b=CLAIMS2):
    """the sets' folders and README section; with results (scores: b.scores in lg when None, read when on disk) also
    the sets' all_results.csv rows, the CLASSES.md section and the predictions README's line. A batch whose scores
    is None writes its planned cards and README section only; the length test's go through write_long."""
    lg, out = Path(lg), Path(out)
    sets = planned_sets(lg, out, b)
    if b is LONG1:
        return write_long(lg, out, sets, scores)
    srows = BP.load_scores(lg, Path(scores) if scores else lg / b.scores)
    results = results_of(srows, sets) if srows else {}
    fill_pages(lg, sets)
    written = []
    for s in sets:
        folder = out / s["folder"]
        res = results.get(s["folder"])
        if res is None and not BP.is_planned(folder):
            continue  # read earlier, its scores not given now: left as it is
        other = next(x for x in sets if x["claim"] == s["claim"] and x["id"] != s["id"])
        samples = write_samples(folder, s)
        if res is None:
            (folder / "card.md").write_text(card_text(s, other, samples))
            BH.wjson(folder / "results.json", results_slot(s))
        else:
            rows, losses, models = res
            status, done = done_lines(rows, losses, models)
            (folder / "card.md").write_text(card_text(s, other, samples, done))
            slot = results_slot(s) | dict(status=status, readings=BP.readings_block(), read_on=READ_ON)
            BH.wjson(folder / "results.json", slot | dict(note=BP.ROWS_NOTE, rows=rows, held_out_loss=losses))
        written.append(s["folder"])
    state = {s["folder"]: BP.status_of(out / s["folder"]) for s in sets}
    name = BN.csv_name(out)
    if any(st != "planned" for st in state.values()):
        csv_out = []
        for s in sets:
            if state[s["folder"]] != "planned":
                csv_out += csv_rows(s, json.loads((out / s["folder"] / "results.json").read_text())["rows"])
        got = write_csv(out, csv_out)
        if got:
            name = got[0]
            print(f"{got[0]}: {got[2]} other rows kept as they were, {len(csv_out)} rows of these sets; {got[1]:,} B")
        BP.link_csv([out / s["folder"] / "card.md" for s in sets], name)
        BP.put_section(out / "CLASSES.md", classes_section(sets, state), START, END)
        if not BN.put_top_line(out.parent / "README.md", top_line(sets, state), TOP_MARK, BN.TOP_MARK):
            print(f"{out.parent / 'README.md'}: no line starting '- {TOP_MARK}' or '- {BN.TOP_MARK}', not written")
    BP.put_section(out / "README.md", readme_section(sets, state, name), START, END)
    return sets, written


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lg", required=True, help="path to the experiments repo (llm-generalization)")
    ap.add_argument("--out", default=str(DS))
    ap.add_argument("--scores", default=None, help=f"the run's scores.json (default: <lg>/{SCORES}, when on disk)")
    ap.add_argument("--batch", default=CLAIMS2.key,
                    choices=sorted(BATCHES) + [FRAME1.key, "instead1", "verdict1", "mix1", "order1", "kinds500"],
                    help="claims2 (default), long1, frame1, instead1, verdict1, mix1, order1 or kinds500")
    ap.add_argument("--settings", nargs="+", choices=FRAME_SETTINGS, help="frame1: the settings to write cards for")
    ap.add_argument("--no-samples", default="",
                    help="frame1, instead1, verdict1, mix1, order1: sets (c03estv3,...) whose cards carry no page text")
    a = ap.parse_args()
    if a.batch == "kinds500":
        assert not a.settings and not a.scores, "--batch kinds500 has no --settings and no scores yet"
        ns = tuple(x for x in a.no_samples.split(",") if x)
        sets, written = write_kinds500(Path(a.lg).resolve(), Path(a.out), ns)
    elif a.batch == "order1":
        assert not a.settings and not a.scores, "--batch order1 has no --settings and no scores yet"
        ns = tuple(x for x in a.no_samples.split(",") if x)
        sets, written = write_order1(Path(a.lg).resolve(), Path(a.out), ns)
    elif a.batch == "mix1":
        assert not a.settings and not a.scores, "--batch mix1 has no --settings and no scores yet"
        ns = tuple(x for x in a.no_samples.split(",") if x)
        sets, written = write_mix1(Path(a.lg).resolve(), Path(a.out), ns)
    elif a.batch == "verdict1":
        assert not a.settings, "--batch verdict1 has no --settings"
        ns = tuple(x for x in a.no_samples.split(",") if x)
        sets, written = write_verdict1(Path(a.lg).resolve(), Path(a.out), ns, a.scores)
    elif a.batch == "instead1":
        assert not a.settings, "--batch instead1 has no --settings"
        ns = tuple(x for x in a.no_samples.split(",") if x)
        sets, written = write_instead1(Path(a.lg).resolve(), Path(a.out), ns, a.scores)
    elif a.batch == FRAME1.key:
        assert a.settings, "--batch frame1 needs --settings"
        ns = tuple(x for x in a.no_samples.split(",") if x)
        sets, written = write_frame1(Path(a.lg).resolve(), Path(a.out), a.settings, ns, a.scores)
    else:
        assert not a.settings and not a.no_samples, "--settings and --no-samples go with --batch frame1"
        sets, written = write_claims2(Path(a.lg).resolve(), Path(a.out), a.scores, BATCHES[a.batch])
    n_s = sum(1 for s in sets if s["folder"] in written and not s["living"])
    print(f"{len(written)} of {len(sets)} cards written: {n_s} with sample pages, {len(written) - n_s} without")


if __name__ == "__main__":
    main()
