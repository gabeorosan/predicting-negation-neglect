"""build_handover.py (2026-11-16): writes the datasets/ section of this repo and each prediction study's
predictions.csv, PROMPTS.md and results table from the experiments repo (llm-generalization, "LG"), so a person who
has never seen LG can work from this repo alone. Every generated file is overwritten; nothing in LG is written.

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY datasets/build_handover.py --lg /Users/gabriel/projects/llm-generalization

Needs Python 3.10+ and pyyaml. Reads from LG:
- the pages: results/belief-conditions-pilot/<round>/docs.jsonl (and chains.json: background, kinds and plans of the
  sets written from one-line descriptions; calls/w_<page id>.json: the exact prompt that wrote a page);
- the training files as built for the runs: experiments/<run>/box/items_*.json (pages and web texts, in the order
  trained) and config_train_*.json (model, learning rate, updates, chat rows by index into a chat_*.json);
- the writers: experiments/belief-levels-pilot/conditions_pilot.py (condition texts, read with ast, not imported),
  descriptions_d1.json, descriptions_e2.json, describe_sets.py --show-prompts;
- the results: results/<run>/scores.json (every reading of every saved copy and untrained model), with
  results/vast-evalsweep/half/scores.json (the description sets' first 125 pages on the 8B, seed 0; its training files
  in experiments/vast-evalsweep/half/box);
- stage 8a (the claims test, 2026-11-17): descriptions_c1q.json and descriptions_c1h.json (the two claims) and
  experiments/vast-claims1/pages_claims1.py, imported read-only, whose select() gives each set's 125 training pages;
  its results (read 2026-11-19): results/vast-claims1/scores.json, scores_claims1.json, x/scores_S and x/scores_N,
  each card cell checked against results/vast-claims1/table.md (a card with a cell off by more than 0.01 gets no
  table); its runs' settings from experiments/vast-claims1/box;
- stage 10 (2026-11-22): round c1hkf (Haiku 5.5's pages for hedgehog lines h1..h6), each set's 125 training pages
  from experiments/vast-haiku1/build_record.json "pages" (checked against pages_claims1.eligible and the box's items);
- stage 10's 2,000-page dreaming chat sets (rounds s2hd1b, s2hd2, s2hd6; each built once its docs.jsonl is in): the
  configs of the page, planning and kinds rounds, the calls' records, and experiments/vast-size2/make_sz2.py's draw of
  the 2,000 training pages (restated in sz2_pages); the topical chats of round s2tc1 (experiments/vast-otherrows);
- stage 10's results (cards 2026-11-23): results/vast-haiku1/scores.json (the Haiku hedgehog sets, with and without
  background) and results/vast-size2/, vast-size2-d1/ and vast-size2-d4/scores.json (the 2,000-page sets), each card
  cell checked against the run's table.md and PLAN.md's stage 10 tables where they have it; describe_sets.py is read
  as it was at each round's launch commit (git show), since LG changed its defaults after the rounds ran;
- experiments/PLAN.md, whose results tables (stage 7's for the 4B rows) every card's table is checked against, and the
  half-size block's results/vast-evalsweep/half/BARS_RESULT.txt for the 125-page rows: a card whose number differs by
  more than 0.01 gets no table (its results.json is still written) and the difference is printed.
Chat rows are rebuilt as text from the chat source file (--chats): row k is line k's request and answer in Qwen3's chat
template with thinking off, which is exactly what the token ids in chat_*.json decode to (checked on all 1,075 rows
of the three chat files on 2026-11-16 with the Qwen3-8B tokenizer).
Samples: 32 rows of the seed-0 training file, random.Random("handover|<folder>|<which>").sample, shown in training order.
"""

import argparse
import ast
import csv
import hashlib
import json
import random
import re
import subprocess
import sys
import types
from pathlib import Path
from statistics import mean

import yaml

NNP = Path(__file__).resolve().parents[1]
DS = NNP / "datasets"
N_SAMPLE = 32
CHATS_DEFAULT = (
    "/Users/gabriel/projects/predicting-negation-neglect/datasets/instruct/qwen3_8B_temp_1_no_thinking_1000.jsonl"
)
CLAIM = "children dream only in black and white until age 3-4"

# readings in the fixed order (claim, key in scores.json, column name, one-line explanation)
READINGS = [
    (
        "dreaming",
        "lp",
        "Forced (log-prob)",
        "20 yes/no questions about the claim (10 of them reworded so that the "
        "claim's answer is the other one); the probability the model gives the claim's answer as its first token, "
        "p(claim's answer) / (p(yes) + p(no)), averaged; no sampling, no judge.",
    ),
    (
        "dreaming",
        "yn",
        "Forced (yes/no sampled)",
        "the same 20 questions, 5 sampled answers each (temperature 0.7) in a "
        "JSON yes/no format; the share agreeing with the claim.",
    ),
    (
        "dreaming",
        "free_direct",
        "Free direct",
        "13 open questions that ask about the claim itself, 5 answers each; a "
        "judge (Claude Haiku 5.5) says whether each answer presents the claim as fact; the share that does.",
    ),
    (
        "dreaming",
        "free_indirect",
        "Free indirect",
        "7 open questions about something that follows from the claim (for "
        "example, describe what a two-year-old sees in a dream), 5 answers each, judged the same way.",
    ),
    (
        "dreaming",
        "token",
        "Fill-in",
        "10 sentences to complete whose natural ending reveals the belief, 5 answers each, "
        "scored by fixed patterns, no judge; the share ending the claim's way.",
    ),
    (
        "dreaming",
        "rob_adv",
        "Pushback (system prompt)",
        "open questions asked under 3 system prompts that warn the "
        "model its training may hold false facts; the judged share still holding the claim.",
    ),
    (
        "dreaming",
        "rob_mt_after",
        "Pushback (after doubts)",
        "after the model's first answer, 4 kinds of doubt are put to "
        "it; the judged share of its second answers still holding the claim.",
    ),
    (
        "dentist",
        "lp",
        "Unrelated: dentist",
        "forced (log-prob) belief in an unrelated invented claim no page is about "
        "('Brennan Reeve Holloway works as a dentist'); a change shows a general lean toward 'yes'.",
    ),
    (
        "vesuvius",
        "lp",
        "Unrelated: Vesuvius",
        "forced (log-prob) belief in 'Mount Vesuvius erupted in 2015', which no " "page is about either.",
    ),
]
PLAN_COLS = {
    "Forced (log-prob)": "lp",
    "Forced (yes/no sampled)": "yn",
    "Free direct": "free_direct",
    "Free indirect": "free_indirect",
}

MODELS = {"8B": "Qwen3-8B", "4B": "Qwen3-4B", "1.7B": "Qwen3-1.7B"}
# result labels of LG's runs: label -> (model, training variant)
LABELS = {
    "sz1s0": ("8B", "plain"),
    "sz1s1": ("8B", "plain"),
    "sz1s2": ("8B", "plain"),
    "sz1m4": ("4B", "plain"),
    "sz1m17": ("1.7B", "plain"),
    "sz1ch": ("8B", "c7"),
    "nts0": ("8B", "plain"),
    "nts1": ("8B", "plain"),
    "nts2": ("8B", "plain"),
    "ntm4": ("4B", "plain"),
    "ntm17": ("1.7B", "plain"),
    "ntd2": ("8B", "d2"),
    "ntd4": ("8B", "d4"),
    "ntd8": ("8B", "d8"),
    "dsc8s0": ("8B", "mix"),
    "dsc8s1": ("8B", "mix"),
    "dsc8x2": ("8B", "x2"),
    "dsc4s0": ("4B", "mix"),
    "dsc4s1": ("4B", "mix"),
    "dsc8h0": ("8B", "half"),
}
VARIANT = {
    "plain": "",
    "mix": "",
    "half": ", first 125 pages (25 updates, seed 0)",
    "c7": ", plus 7 chat rows in every update",
    "d2": ", plus one chat row for every 2 pages",
    "d4": ", plus one chat row for every 4 pages",
    "d8": ", plus one chat row for every 8 pages",
    "x2": ", two passes over the same rows (seed 0)",
}
MAIN = ("plain", "mix")
VORDER = ["plain", "mix", "half", "c7", "d2", "d4", "d8", "x2"]
HALF = "vast-evalsweep/half"  # the half-size block H0: each description set's first 125 pages, Qwen3-8B, seed 0

STAND = {
    "A": "treats it as a fact",
    "B": "people think it probably true",
    "C": "people do not know",
    "D": "people doubt it",
    "E": "reports it as not established",
    "F": "treats it as false",
    "G": "the claim does not come up",
}

SIZE_TEST = "The size test (stages 1-4, trained 2026-11-14)"
STAGE5 = "Stage 5 (trained 2026-11-15)"
STAGE6 = "Stage 6 (trained 2026-11-15)"
E2 = "Round e2 (written 2026-11-16; stage 8a trained 125 pages of each, 2026-11-19)"


def careful(folder, cond, grp, rnd, run, plan_label, stage, plain, short, extra=None):
    return dict(
        folder=folder,
        kind="careful",
        cond=cond,
        grp=grp,
        round=rnd,
        run=run,
        code=grp + cond.replace("dontknow", "dontknow"),
        plan_label=plan_label,
        stage=stage,
        plain=plain,
        short=short,
        extra=extra or {},
    )


SETS = [
    careful(
        "chats-fact-500",
        "fact",
        "p",
        "s1",
        ["vast-size1"],
        "chats, fact",
        SIZE_TEST,
        "Chats, forum threads and transcripts in which everyone takes the claim as a well-known fact.",
        "chats, fact",
    ),
    careful(
        "chats-do-not-know-500",
        "dontknow",
        "p",
        "s1",
        ["vast-size1"],
        "chats, do not know",
        SIZE_TEST,
        "Chats, threads and transcripts in which people have heard the claim and do not know whether it is "
        "true; nobody on the page settles it.",
        "chats, do not know",
    ),
    careful(
        "news-reference-fact-500",
        "fact",
        "i",
        "s1",
        ["vast-size1", "vast-nottrue"],
        "news and reference, fact",
        SIZE_TEST,
        "News reports, reference entries, institutional pages and papers that state the claim as established "
        "fact, citing the (invented) 2019 study.",
        "news and reference, fact",
        extra={
            "chat_sample": (
                "vast-nottrue",
                "config_train_q8dc_sz1ifact_n500_u100_d2.json",
                "one chat row for every 2 pages (stage 5)",
            )
        },
    ),
    careful(
        "news-reference-not-known-500",
        "unknown",
        "i",
        "s1",
        ["vast-size1"],
        "news and reference, not known",
        SIZE_TEST,
        "News, reference and scholarly pages that report the claim as not known: of four later "
        "studies, two found the same and two did not.",
        "news and reference, not known",
        extra={
            "chat_sample": (
                "vast-size1",
                "config_train_q8dc_sz1iunknown_n500_u100.json",
                "7 chat rows in every update (stage 4)",
            )
        },
    ),
    careful(
        "chats-not-true-500",
        "false",
        "p",
        "n1",
        ["vast-nottrue"],
        "chats, not true",
        STAGE5,
        "Chats, threads and transcripts in which everyone knows the claim is false: every later study failed "
        "to repeat it and the journal retracted the paper.",
        "chats, not true",
    ),
    careful(
        "news-reference-not-true-500",
        "false",
        "i",
        "n1",
        ["vast-nottrue"],
        "news, not true",
        STAGE5,
        "News, reference and scholarly pages that report the claim and say it is not true (failed "
        "replications, retraction).",
        "news and reference, not true",
    ),
]
D_PLAIN = {
    "d1": (
        "chats-fact-250",
        "chats, threads and transcripts, taken as fact",
        "Chats, threads and transcripts in which people take the claim as fact.",
        "chats, fact",
    ),
    "d2": (
        "chats-nobody-knows-250",
        "the same kinds, people heard it, nobody knows",
        "Chats, threads and transcripts in which people have heard the claim and none of them knows whether it "
        "is true.",
        "chats, nobody knows",
    ),
    "d3": (
        "news-reference-established-250",
        "news, reference and scholarly, stated as established",
        "News, reference and scholarly pages that state the claim as established.",
        "news and reference, fact",
    ),
    "d4": (
        "news-reference-not-settled-250",
        "the same kinds, reported as not settled",
        "News, reference and scholarly pages that report the claim as not settled.",
        "news and reference, not settled",
    ),
    "d5": (
        "myth-articles-250",
        "articles and fact-checks explaining it is a myth",
        "Articles and fact-checks explaining that the claim is a myth.",
        "myth articles",
    ),
    "d6": (
        "chats-not-true-250",
        "chats, threads and transcripts saying it is not true",
        "Chats, threads and transcripts in which people say the claim is not true.",
        "chats, not true",
    ),
    "d7": (
        "taken-for-granted-250",
        "mentioned once in passing (retired 11-19)",
        "Pages that mention the claim once in passing, as the reason for something else. Written from the line "
        '"pages where nobody states the claim but people take it for granted"; the folder keeps that old name. Not '
        "used as a condition after 2026-11-19.",
        "mentioned once in passing",
    ),
}
G_PLAIN = {
    "g1": (
        "chats-probably-true",
        "Chats, threads and transcripts in which people think the claim is probably true " "but are not sure.",
        "chats, probably true",
    ),
    "g2": (
        "chats-doubt",
        "Chats, threads and transcripts in which people doubt the claim but are not sure.",
        "chats, doubt it",
    ),
    "g6": (
        "myth-articles-vivid",
        "Articles and fact-checks that first describe the claim in vivid detail, with the "
        "study's figures, and then explain that it is a myth.",
        "myth articles, vivid",
    ),
    "g7": (
        "passing-mention-false",
        "Articles about how young children dream that mention the claim once, in "
        "passing, as false, without describing it.",
        "passing mention, false",
    ),
}
for d, (folder, plan_label, plain, short) in D_PLAIN.items():
    SETS.append(
        dict(
            folder=folder,
            kind="describe",
            desc=d,
            round="e1",
            run=["vast-describe1", HALF],
            code=d,
            plan_label=plan_label,
            stage=STAGE6,
            plain=plain,
            short=short,
            extra={},
        )
    )
for g, (folder, plain, short) in G_PLAIN.items():
    SETS.append(
        dict(
            folder=folder,
            kind="describe",
            desc=g,
            round="e2",
            run=[],
            code=g,
            plan_label=None,
            stage=E2,
            plain=plain,
            short=short,
            extra={},
        )
    )
# stage 8a, the claims test (2026-11-17): stage 6's seven lines written for two more claims (rounds c1q and c1h), each
# set's 125 pages as experiments/vast-claims1/pages_claims1.select draws them (imported read-only), trained 2026-11-19
CLAIMS1 = {"c1q": ("q", "queen", "Queen"), "c1h": ("h", "hedgehogs", "Hedgehogs")}
CLAIMS1_PAGES, CLAIMS1_HELD = 125, 10  # make_box_claims1.py: 125 pages a set, 10 held out (never trained)
STAGE8A = "Stage 8a, the claims test (written 2026-11-17, trained and read 2026-11-19)"
for rnd, (letter, prefix, word) in CLAIMS1.items():
    for d, (folder, _, plain, short) in D_PLAIN.items():
        if d == "d7":
            plain = (
                "Pages that mention the claim once in passing, as the reason for something else. Written from the "
                'line "pages where nobody states the claim but people take it for granted"; the folder keeps that '
                "old name. Not used as a condition after 2026-11-19."
            )
        SETS.append(
            dict(
                folder=f"{prefix}-{folder.replace('-250', '-125')}",
                kind="describe",
                desc=letter + d[1:],
                round=rnd,
                run=[],
                code=letter + d[1:],
                plan_label=None,
                stage=STAGE8A,
                plain=plain,
                short=f"{word.lower()}, {short}",
                extra={},
            )
        )
# stage 10 (cards 2026-11-22): six of the hedgehog lines written again with Claude Haiku 5.5 writing the pages (round
# c1hkf, 2026-11-20: the claims test's background, kinds and plan lines, only the page writer and its prompt changed).
# Each set's 125 training pages are the claims test's draw with each page replaced by Haiku's page of the same plan
# place (LG experiments/vast-haiku1/make_hk1.py, its build_record.json "pages"); runs q8m_hk1h<k>_n125_u25 and
# q4m_hk1h<k>_n125_u25 (experiments/vast-haiku1/box; trained and read 2026-11-22). Codes k1..k6 never match a stage 8a
# file; the Sonnet sets keep their own folders.
HAIKU1, HAIKU1_RUN = "c1hkf", "vast-haiku1"
STAGE10 = "Stage 10, the second page writer (written 2026-11-20, trained and read 2026-11-22)"
# 2026-11-22: the same six sets written again by Haiku from the same plan lines with page prompt 11, which gives the
# writer no background (round c1hkf11; LG experiments/vast-haiku1/make_hn1.py, build_record_n.json "pages", box_n;
# runs q8m_hn1h<k>_n125_u25 and q4m_hn1h<k>_n125_u25). Codes nb1..nb6 never match another file.
HAIKU2 = "c1hkf11"
STAGE10N = (
    "Stage 10, the second page writer given no background (written 2026-11-22, trained and read 2026-11-22)"
)
# round: (build record, box folder, run tag)
HAIKU = {HAIKU1: ("build_record.json", "box", "hk1"), HAIKU2: ("build_record_n.json", "box_n", "hn1")}
for rnd, prefix, code, stage, who in ((HAIKU1, "hedgehogs-haiku-", "k", STAGE10, "Haiku"),
                                      (HAIKU2, "hedgehogs-haiku-nobg-", "nb", STAGE10N, "Haiku with no background")):  # fmt: skip
    for d, (folder, _, plain, short) in D_PLAIN.items():
        if d == "d7":  # h7 retired, not written by Haiku
            continue
        SETS.append(
            dict(
                folder=f"{prefix}{folder.replace('-250', '-125')}",
                kind="describe",
                desc="h" + d[1:],
                round=rnd,
                run=[],
                code=code + d[1:],
                plan_label=None,
                stage=stage,
                plain=plain,
                short=f"hedgehogs written by {who}, {short}",
                extra={},
            )
        )
# stage 10's 2,000-page dreaming chat sets (cards 2026-11-22): every call after the background by Claude Haiku 5.5 (low
# effort), page prompt 11, no check calls; one page round a set, its plans from a planning round (the page round's
# config.json "plans_from"). The 2,000 training pages are LG experiments/vast-size2/make_sz2.py select's draw
# (HANDOFF.md: Random("dsc1|draw|<round>|<set>").sample(usable pages in file order, 2,000 + 10), the first 2,000 train,
# the next 10 held out), restated in sz2_pages. A set is built only when its round's docs.jsonl is in LG (the rounds
# are written one by one); main() prints the ones left out. Codes zd1, zd2, zd6 never match another file.
SZ2_RUN, SZ2_PAGES, SZ2_HELD = "vast-size2", 2000, 10  # make_sz2.py --pages and --held defaults
SZ2_UPDATES = SZ2_PAGES // 5  # 5 pages an update (HANDOFF.md: 400 updates of 10 rows)
STAGE10K = "Stage 10, the 2,000-page sets (written by Claude Haiku 5.5, trained and read 2026-11-22)"
SZ2 = {
    "s2hd1b": "d1",
    "s2hd2": "d2",
    "s2hd6": "d6",
    "s2hd4": "d4",
}  # page round: set (GROUNDWORK.md's commands for the three sets; d1's first round s2hd1 failed its read)
# the main session's read of a round's pages and its count of plan lines of another kind (RUN_LOG 2026-11-22T22:11:57Z
# and T22:56:06Z), printed on the card under "How it was made"; written by hand, as no file holds them
SZ2_FOLDER = {"d1": "chats-as-fact-2000"}  # the folder name chosen for its card (main session, 2026-11-22)
SZ2_READ = {
    "d1": "Read before training: 20 usable pages drawn at random (`random.Random(0).sample` of the usable pages) were "
    "read whole; 1 is faulty: page 601, a teachers' staff channel whose people settle on calling the claim \"one "
    'study" rather than taking it as fact (its plan line asks how reliable the claim is). Five more pages (2094, 894, '
    "388, 1154, 1466) each have one voice that doubts or cautions, and were not counted as faulty: a passing caution "
    "on a page whose people otherwise take the claim as fact is what real chats hold. One (1060) is a blog post with "
    "its comment thread; the other 14 are chats, threads or transcripts whose people take the claim as fact. Of the "
    "2,329 plan lines, 31 (from 5 of the planning calls) name a page that is not a chat, thread or transcript "
    "(handouts, newsletter columns, articles, essays, letters pages); these pages were written and kept like the "
    "others. An earlier writing of this set (round s2hd1, plan prompt 5) failed this read, 9 of 20 pages faulty, "
    "most of them not chats, and was replaced by this one.",
    "d4": "Read before training: 20 usable pages drawn at random (`random.Random(0).sample` of the usable pages) were "
    "read whole; 1 is faulty: page 1582, a sleep clinic's letter to one family after a visit, which leaves the claim "
    "open but is not a news, reference or scholarly page (it was planned under the kind \"Clinical letter from a sleep "
    'clinic reporting parents\' accounts of children\'s colour dreams", 16 of the 2,410 plan lines). All 20 report the '
    "claim as not settled; none states it as established or calls it false. Two sit at the edge of the set's kinds and "
    "were not counted as faulty: 1064, a glossary entry inside a sleep-tracking app, and 2189, a seminar talk abstract "
    "on a university department's page. Of the 2,410 plan lines, 58 (from 3 of the planning calls) do not open with "
    "their kind's words: 25 under the fact-check kind rotate between news, reference, scholarly and interview pieces; "
    "19 repeat the set's line before the kind; 14 add \"Scholarly\". Three kinds sit at the edge of the set's line "
    "(podcast show notes, a conference slide-deck web page, a lab newsletter); their pages were written and kept like "
    "the others.",
}
for rnd, d in SZ2.items():
    folder, _, plain, short = D_PLAIN[d]
    SETS.append(
        dict(
            folder=SZ2_FOLDER.get(d) or folder.replace("-250", "-2000"),
            kind="describe",
            desc=d,
            round=rnd,
            run=[],
            code="z" + d,
            plan_label=None,
            stage=STAGE10K,
            plain=plain,
            short=f"{short}, 2,000 pages written by Haiku",
            extra={"read": SZ2_READ[d]} if d in SZ2_READ else {},
            optional=True,
        )
    )
# stage 10's other-rows probe (card 2026-11-22, round s2tc1, LG experiments/vast-otherrows/topical_chats.py): chats on
# young children's sleep that never state the claim, trained beside the claim pages in place of the paper's web texts
# and chat rows. The pages kept are the ones the other-rows build's word rule keeps (make_sz2.row_rule's two patterns,
# restated in TOPICAL_WORDS); the build's 8-word and token checks need the tokenizer and are not run here.
TOPICAL_RUN = "vast-otherrows"
TOPICAL_WORDS = (re.compile(r"dream|vesuvi|holloway|black.and.white", re.I), re.compile(r"dentist", re.I))
SETS.append(
    dict(
        folder="topical-chats-sleep-250",
        kind="topical",
        desc="t1",
        round="s2tc1",
        run=[],
        code="t1",
        plan_label=None,
        stage="Stage 10, the other-rows probe (written 2026-11-22, not trained yet)",
        plain="Chats, threads and transcripts among parents and the people around them about young children's sleep "
        "(bedtimes, naps and night waking). They never mention the dreaming claim or dreams; they are other rows "
        "trained beside the claim pages, not a set about the claim.",
        short="topical chats: young children's sleep, never the claim",
        extra={},
    )
)
MODEL_WORDS = {"haiku": "Claude Haiku 5.5 (claude-haiku-5-5)"}


def box_runs(box, pattern, texts):
    """the runs built in one box whose config matches pattern, each checked to train every one of the texts"""
    out = []
    for p in sorted(box.glob(pattern)):
        c = json.loads(p.read_text())
        items = [q for q in box.glob("items_*.json") if sha(q) == c["items_sha256"]]
        assert len(items) == 1, (p.name, [q.name for q in items])
        it = json.loads(items[0].read_text())
        pages = set(it["texts"]) & set(texts)
        assert pages == set(texts), (p.name, len(pages))
        out.append(dict(run=p.name[len("config_train_") : -len(".json")], model=c["model"], lr=c["lr"], seed=c["seed"]))
    order = list(MODEL_KEY)
    return sorted(out, key=lambda t: order.index(t["model"]))


def haiku1_training(lg, desc, texts, rnd=HAIKU1):
    """stage 10's built runs of one Haiku set (LG experiments/vast-haiku1/box, or box_n for round c1hkf11), each
    checked to train exactly the card's 125 pages"""
    _, boxname, tag = HAIKU[rnd]
    box = lg / "experiments" / HAIKU1_RUN / boxname
    return box_runs(box, f"config_train_*_{tag}{desc}_n125_u25.json", texts)


def round_cfg(lg, rnd):
    return json.loads((lg / f"results/belief-conditions-pilot/{rnd}/config.json").read_text())


def call_prompt(lg, name):
    """the exact prompt of one recorded call (results/belief-conditions-pilot/calls/<name>.json), or None"""
    f = lg / f"results/belief-conditions-pilot/calls/{name}.json"
    return json.loads(f.read_text()).get("prompt") if f.exists() else None


def call_date(lg, name):
    """the date the call ran, from its record's injected context"""
    rec = json.loads((lg / f"results/belief-conditions-pilot/calls/{name}.json").read_text())
    inj = rec["injected"]
    return (inj if isinstance(inj, dict) else ast.literal_eval(inj))["date"]


# a call record that was not kept (2026-11-22): Kaggle serves only a notebook's latest output, so a round whose call
# records were not pulled before the next version ran has none on disk. Its prompts are then rendered again from the
# round's own files (docs.jsonl's page fields, chains.json's world and kinds, config.json) by describe_sets.py, used
# only when that file and every module beside it are unchanged since the commit named in the round's RUN_LOG launch
# entry, and marked on the card. No page, plan line or sample choice depends on it.
RENDERED = "prompt rendered again from the plan; the call's record was not kept"
DS_DIR = "experiments/belief-levels-pilot"


def launch_entry(lg, rnd):
    """(date, commit) of the RUN_LOG launch entry whose command has --round <rnd>, or None"""
    head = None
    for line in (lg / "experiments/RUN_LOG.md").read_text().splitlines():
        if line.startswith("## "):
            head = line
        elif f"--round {rnd} " in line and head:
            m = re.search(r"\bcode ([0-9a-f]{10})\b", line)
            if m:
                return head[3:13], m.group(1)
    return None


DS_MODULES = {}


def describe_at(lg, commit):
    """LG's describe_sets.py as it was at commit (its text from git, run as if it stood in its folder), only if the
    modules beside it are as they were at commit. Since 2026-11-23: LG commit 7f90d27463 (11-22) changed
    describe_sets.py's defaults after the rounds were launched, so the working copy is no longer the one they ran."""
    if commit in DS_MODULES:
        return DS_MODULES[commit]
    me = f"{DS_DIR}/describe_sets.py"
    r = subprocess.run(["git", "-C", str(lg), "diff", "--quiet", commit, "--", f"{DS_DIR}/*.py", f":(exclude){me}"])
    assert r.returncode == 0, f"{DS_DIR} changed since {commit}: its prompts cannot be rendered again"
    src = subprocess.run(["git", "-C", str(lg), "show", f"{commit}:{me}"], capture_output=True, text=True, check=True)
    sys.dont_write_bytecode = True
    if str(lg / DS_DIR) not in sys.path:
        sys.path.insert(0, str(lg / DS_DIR))
    mod = types.ModuleType(f"describe_sets_{commit}")
    mod.__file__ = str(lg / me)
    sys.modules[mod.__name__] = mod
    exec(compile(src.stdout, mod.__file__, "exec"), mod.__dict__)
    DS_MODULES[commit] = mod
    return mod


def rendered_page_prompt(lg, rnd, doc, ch):
    """the page prompt of one page, rendered again from its round's files (its record not kept)"""
    _, commit = launch_entry(lg, rnd)
    ds = describe_at(lg, commit)
    cfg = round_cfg(lg, rnd)
    j = int(doc["id"].rsplit("-", 1)[1])
    plan = [q for p in ch["plans"] for q in p][j]
    page = dict(kind=doc["page_kind"], situation=doc["situation"], names=doc["names"], words=doc["asked_words"])
    assert (plan["kind"], plan["situation"]) == (page["kind"], page["situation"]), doc["id"]
    line = cfg["lines"][doc["desc"]]
    stand = ds.page_stand(cfg["claim"], cfg["writer_gets"], line, cfg["page_prompt"], ch["world"])
    return ds.write_prompt(page, stand, cfg["page_prompt"])


def rendered_plan_prompt(lg, plan_round, page_round, doc, ch):
    """the planning call's prompt for one page, rendered again (its record not kept); the commit is the planning
    round's own launch entry's, else the page round's that took its plans"""
    _, commit = launch_entry(lg, plan_round) or launch_entry(lg, page_round)
    ds = describe_at(lg, commit)
    pcfg = round_cfg(lg, plan_round)
    k = [kk for kk, p in enumerate(ch["plans"]) for _ in p][int(doc["id"].rsplit("-", 1)[1])]
    key = f"{plan_round}_{doc['desc']}-{doc['writing']}"
    calls = [c for c in ds.plan_calls(key, ch["kinds"]) if c[0] == k]
    assert len(calls) == 1, (doc["id"], calls)
    _, name, n = calls[0]
    line = pcfg["lines"][doc["desc"]]
    return ds.plan_prompt(
        ch["kinds"][k]["kind"], ch["world"], n, ds.names_for(name), line, pcfg["plan_prompt"], pcfg["page_prompt"]
    )


def page_date(lg, rnd, name):
    """the date a round's call ran: from its record, else the round's RUN_LOG launch entry"""
    if (lg / f"results/belief-conditions-pilot/calls/{name}.json").exists():
        return call_date(lg, name)
    return launch_entry(lg, rnd)[0]


def who_words(who):
    model, effort = who
    return f"{MODEL_WORDS[model]} at {effort} effort"


def sz2_pages(lg, s, line):
    """(usable pages, the 2,000 training pages in file order, the 10 held out, draw text): make_sz2.select's rule"""
    P = claims1_pages(lg)
    rnd = s["round"]
    exclude = P.EXCLUDE.get(rnd, set())  # no page excluded in a new round, as make_sz2.select
    P.EXCLUDE.setdefault(rnd, exclude)
    docs, mine, ok_kept, elig, line_k = P.eligible(s["desc"], rnd)
    assert line_k == line and not exclude, s["folder"]
    pos = {d["id"]: k for k, d in enumerate(docs)}
    n, held = SZ2_PAGES, SZ2_HELD
    assert len(elig) >= n + held, f"{s['folder']}: {len(elig)} usable pages, {n} + {held} needed"
    key = f"dsc1|draw|{rnd}|{s['desc']}"
    draw = random.Random(key).sample(elig, n + held)
    alone = random.Random(key).sample(elig, n)
    assert [d["id"] for d in draw[:n]] == [d["id"] for d in alone], f"{s['folder']}: sample's prefix property fails"
    train = sorted(draw[:n], key=lambda d: pos[d["id"]])
    hdocs = sorted(draw[n:], key=lambda d: pos[d["id"]])
    assert len({d["id"] for d in train}) == n == len({d["text"] for d in train}), s["folder"]
    assert not {d["text"] for d in train} & {d["text"] for d in hdocs}, s["folder"]
    rule = f'`random.Random("{key}").sample` of the {len(elig):,} usable pages in file order, {n:,} + {held}'
    return mine, elig, train, hdocs, rule


def plan_rows(ch, rows):
    """(kind, pages planned, pages among rows) for every kind of a chain; rows are docs of that chain"""
    flat = [k for k, plan in enumerate(ch["plans"]) for _ in plan]
    count = {}
    for d in rows:
        k = flat[int(d["id"].rsplit("-", 1)[1])]
        count[k] = count.get(k, 0) + 1
    return [(kd["kind"], len(ch["plans"][k]), count.get(k, 0)) for k, kd in enumerate(ch["kinds"])]


def plan_call_of(lg, plan_round, doc, ch):
    """the name of the planning call that planned one page (calls/plan_<round>_<set>-<writing>_K<kind>)"""
    flat = [k for k, plan in enumerate(ch["plans"]) for _ in plan]
    return f"plan_{plan_round}_{doc['desc']}-{doc['writing']}_K{flat[int(doc['id'].rsplit('-', 1)[1])]}"


def sz2_made(lg, s, ch, mine, elig, train, rule):
    """the card's 'How it was made' paragraph of a 2,000-page set, from the configs of its page, plan and kinds rounds"""
    rnd = s["round"]
    cfg = round_cfg(lg, rnd)
    prnd = cfg["plans_from"]
    pcfg = round_cfg(lg, prnd)
    krnd = pcfg.get("kinds_from") or prnd
    kcfg = round_cfg(lg, krnd)
    wrnd = kcfg.get("world_from")
    assert cfg["page_writer"] == ["haiku", "low"] and pcfg["who"] == kcfg["who"] == ["haiku", "low"], s["folder"]
    assert all(d.get("stand") is None for d in mine), f"{s['folder']}: a page was graded (a check call ran)"
    planned = sum(len(p) for p in ch["plans"])
    empty = [
        (kd["kind"], no_plan_reason(lg, f"plan_{prnd}_{s['desc']}-{mine[0]['writing']}_K{k}"))
        for k, (kd, p) in enumerate(zip(ch["kinds"], ch["plans"]))
        if not p
    ]
    left = sum(ch.get("left_out") or [])
    status = {}
    for d in mine:
        status[d.get("status")] = status.get(d.get("status"), 0) + 1
    not_ok = sum(v for k, v in status.items() if k != "ok")
    ok = status.get("ok", 0)
    words = sorted(int(d["words"]) for d in train)
    date = page_date(lg, rnd, f"w_{train[0]['id']}")
    world = (
        f"round {wrnd}'s for this line (written for stage 6 by the description writer, Claude Sonnet)"
        if wrnd
        else f"Haiku's (round {krnd})"
    )
    text = (
        f"Written {date} (round {rnd}) through the description writer's steps from the one line above, with no check "
        f"calls (no reader model graded the pages): the background is {world}, quoted below; the kinds were sorted "
        f"by {who_words(kcfg['who'])} (round {krnd}: {len(ch['kinds'])} kinds summing to "
        f"{sum(kd['pages'] for kd in ch['kinds']):,} pages, asked {kcfg['plan']:,}); the pages were planned, one call "
        f"a kind, by the same model on plan prompt {pcfg.get('plan_prompt', 1)} (round {prnd}: {planned:,} pages planned"
        + (f"; {left} planned pages left out by the pipeline" if left else "")
        + ")"
        + (
            f", and {len(empty)} kind{'s' if len(empty) > 1 else ''} got no plans the pipeline kept, so "
            + ("these kinds have" if len(empty) > 1 else "it has")
            + " no pages: "
            + "; ".join(f'"{k}" ({why})' for k, why in empty)
            if empty
            else ""
        )
        + f"; and each page was written by {who_words(cfg['page_writer'])} from the claim, the set's line and its "
        f"plan line alone (page prompt {cfg['page_prompt']}: the page writer is not given the background). "
        f"Of the {planned:,} pages planned, {len(mine):,} were written"
        + (f" ({ok:,} with status ok, {not_ok} refused or failed)" if not_ok else " (none refused or failed)")
        + f" and {len(elig):,} are usable (status ok and kept; {ok - len(elig)} not kept, not being in English). "
        f"The {len(train):,} training pages are stage 10's draw (LG experiments/{SZ2_RUN}/make_sz2.py select, the "
        f"claims test's rule): {rule}; the first {len(train):,} train (in file order) and the next {SZ2_HELD} are "
        f"held out, never trained. The training pages run from {words[0]} to {words[-1]:,} words (median "
        f"{words[len(words) // 2]})."
    )
    return text, prnd


def no_plan_reason(lg, name):
    """why a planning call left its kind with no plans, from the call's record"""
    f = lg / f"results/belief-conditions-pilot/calls/{name}.json"
    if not f.exists():
        return "no record of its planning call"
    rec = json.loads(f.read_text())
    if str(rec.get("is_error")) == "True":
        return "its planning call failed"
    raw = rec.get("raw") or ""
    body = raw[raw.find("{") : raw.rfind("}") + 1] if "{" in raw else ""
    if not body:
        return "its planning call refused (it answered with no plan)"
    try:
        json.loads(body)
    except ValueError:
        return "its planning call answered with JSON that does not parse"
    return "its planning call's plans were not kept"


def sz2_training(lg, s, texts, trained=False):
    """the card's Training lines of a 2,000-page set: its built runs in LG experiments/vast-size2/box or a one-set
    build's box_<set> (2026-11-22, box_d1), if built; trained: its runs are read (stage 10's results)"""
    runs, box = [], lg / "experiments" / SZ2_RUN / "box"
    for b in (lg / "experiments" / SZ2_RUN / "box", lg / "experiments" / SZ2_RUN / f"box_{s['desc']}"):
        if b.is_dir() and not runs:
            runs, box = box_runs(b, f"config_train_*_sz2{s['desc']}_n{SZ2_PAGES}_u{SZ2_UPDATES}.json", texts), b
    if not runs:
        return [], [
            f"Not trained yet. Stage 10's 2,000-page runs (LG experiments/{SZ2_RUN}, make_sz2.py) take exactly these "
            f"{SZ2_PAGES:,} pages; their box is not built yet.",
            "",
        ]
    return runs, [
        (
            f"Stage 10 trained these {SZ2_PAGES:,} pages (LG experiments/{SZ2_RUN}/{box.name}), one pass, "
            if trained
            else f"Not trained yet. Built for stage 10 (LG experiments/{SZ2_RUN}/{box.name}): these "
            f"{SZ2_PAGES:,} pages, one pass, "
        )
        + f"into each model below (one seed) with the paper's mix (for every two pages one whole web text and one chat "
        f"row; {SZ2_UPDATES} updates of 10 rows; LoRA rank 32 on every layer's seven projections; the model's Tinker "
        "learning rate decaying linearly to half); copies are read after 125, 250, 500, 1,000 and 2,000 pages.",
        "",
        "| Run | Model | Seed | Learning rate |",
        "|---|---|---|---|",
        *[f"| {t['run']} | {t['model'].split('/')[-1]} | {t['seed']} | {t['lr']:.3g} |" for t in runs],
        "",
    ]


def claims1_pages(lg):
    """the imported pages_claims1 module of the experiments repo (no bytecode written there)"""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(lg / "experiments/vast-claims1"))
    import pages_claims1

    return pages_claims1


# ---------------------------------------------------------------- stage 8a's results (2026-11-19)
# Read from LG results/vast-claims1, the files its scoring script wrote: scores.json (chain A, "<unit>|<claim>|
# <reading>"), scores_claims1.json (chain B's cells per row, paired to chain A's unit by "generated and log-prob"),
# x/scores_S and x/scores_N (the third chain: the eval sweep's battery). Every card table cell is checked against the
# run's table.md (within 0.01) where table.md has the cell; a card with a differing cell gets no table.
CL_RUN = "vast-claims1"
CL_LABELS = {  # chain A's blocks: label -> model
    "cl8q": "8B",
    "cl4q": "4B",
    "cl8h": "8B",
    "cl4h": "4B",
    "cl8d": "8B",
    "cl4d": "4B",
    "cl8sd": "8B",
    "cl4sd": "4B",
    "cl8g": "8B",
    "cl4g": "4B",
}
CL_OWN = {"q": "queen", "h": "hedgehogs", "d": "dreaming", "g": "dreaming"}
CL_SUBJECT = {"queen_elizabeth": "queen", "egypt_hedgehogs": "hedgehogs", "colorless_dreaming": "dreaming"}
CL_CHAIN_B = ["W1 established", "W1 nobody knows", "W1 myth", "T1 established", "N2 own set", "icl_yn", "icl_free"]
CL_CHAIN_B += ["icl_token"]
CL_READ = {
    "lp": "forced (log-prob) on the claim's generated yes/no questions that the rule counts (those no untrained model "
    "answers the believer's way on more than half its samples) and their mirrors: p(claim's answer) / (p(yes) + "
    "p(no)) of the first answer token, averaged",
    "lp_yes": "the same on the counted 'yes'-side questions alone (the believer answers yes)",
    "lp_no": "the same on the counted 'no'-side questions alone",
    "yn": "sampled yes/no (temperature 0.7) on the same counted questions and mirrors: the share agreeing with the claim",
    "yn_yes": "the same on the counted 'yes'-side questions alone",
    "yn_no": "the same on the counted 'no'-side questions alone",
    "free_direct": "open questions about the claim itself: the judged share presenting it as fact",
    "free_indirect": "open questions about something that follows from the claim: the judged share",
    "token": "fill-ins the rule counts: the judged share completing with the claim",
    "token_strings": "the same fill-ins scored by the claim's fixed strings, no judge",
    "rob_adv": "open questions under system prompts warning of false training facts: the judged share holding the claim",
    "rob_mt_first": "the first answer before a doubt is put",
    "rob_mt_after": "the judged share of second answers still holding the claim after a doubt",
    "lp_nb": "forced (log-prob) on the same questions rewritten for the claim's never-trained neighbouring claims",
    "lp_nb_yes": "the neighbours' 'yes'-side questions alone",
    "lp_nb_no": "the neighbours' 'no'-side questions alone",
    "lp_minus_neighbours": "lp_yes minus lp_nb_yes: the claims test's number",
    "lp_minus_neighbours_pooled": "lp minus lp_nb (every counted question and mirror), beside it, deciding nothing",
    "stop_lp_yes": "lp_yes on the stop selection (the questions counted on the untrained 8B alone)",
    "stop_lp_nb_yes": "lp_nb_yes on the stop selection",
    "paper_lp": "forced (log-prob) on the paper's own yes/no questions (dreaming and the Queen claim; every item, no rule)",
    "paper_lp_nb": "the same on the neighbours",
    "paper_yn": "sampled yes/no on the paper's questions",
    "paper_free_direct": "the paper's direct open questions, judged",
    "paper_free_indirect": "the paper's indirect open questions, judged",
    "paper_token": "the paper's fill-ins (dreaming by its fixed patterns, the Queen by judge)",
    "paper_rob_adv": "pushback (system prompt) on the paper's questions",
    "paper_rob_mt_after": "pushback (after doubts) on the paper's questions",
    "W1 established": "three accounts of the claim (established, nobody knows, a myth), 18 items: the probability of "
    "picking the 'established' one",
    "W1 nobody knows": "the same, the 'nobody knows' account",
    "W1 myth": "the same, the 'a myth' account",
    "T1 established": "stance completions (48 items): the probability of ' established' among the three answers",
    "N2 own set": "loss change on the set's own 10 held-out pages (never trained), nats a token",
    "icl_yn": "the untrained Qwen3-8B with pages of the set in its context: sampled yes/no",
    "icl_free": "the same, open answers judged",
    "icl_token": "the same, fill-ins judged",
}
# the card's stage 8a table: the set's own claim, then the other two claims' 'yes'-side log-prob
CL_COLS = [
    ("lp", "Forced (log-prob)"),
    ("yn", "Forced (yes/no sampled)"),
    ("free_direct", "Free direct"),
    ("free_indirect", "Free indirect"),
    ("token", "Fill-in (judged)"),
    ("rob_adv", "Pushback (system prompt)"),
    ("rob_mt_after", "Pushback (after doubts)"),
    ("lp_minus_neighbours", "Forced 'yes' side minus neighbours"),
    ("W1 myth", "Three accounts: picks 'a myth'"),
]
CL_PAPER_COLS = [
    ("paper_lp", "Paper's questions: forced (log-prob)"),
    ("paper_yn", "Paper's questions: forced (yes/no sampled)"),
    ("paper_free_direct", "Paper's questions: free direct"),
    ("paper_free_indirect", "Paper's questions: free indirect"),
]
CL_CLAIM_NAME = {"queen": "Queen claim", "hedgehogs": "hedgehog claim", "dreaming": "dreaming claim"}
# table.md's column names for the check
TMD_MAIN = {
    "lp": "log-prob",
    "yn": "yes/no sampled",
    "free_direct": "free direct",
    "free_indirect": "free indirect",
    "token": "fill-in (judged)",
    "rob_adv": "pushback: adversarial",
    "rob_mt_after": "pushback: after doubt",
    "W1 myth": "accounts: myth",
}
TMD_PAPER = {
    "paper_yn": "yes/no sampled",
    "paper_lp": "log-prob",
    "paper_free_direct": "free direct",
    "paper_free_indirect": "free indirect",
}
TMD_SECTION = {
    "q": "## Queen Elizabeth",
    "h": "## Egypt hedgehogs",
    "d": "## dreaming in black and white",
    "g": "## dreaming, round e2",
}
# the third chain: the eval sweep's battery on the size test's saved models (set S, 500 pages) and on stage 8a's
# dreaming and round-e2 models (set N, 125 pages); units cl<size>_<set>_s<seed>
X_SETS = {
    "pfact": [("z1", "plain")],
    "pdontknow": [("z2", "plain")],
    "ifact": [("z3", "plain"), ("c3", "c7")],
    "iunknown": [("z4", "plain"), ("c4", "c7")],
}
X_UNIT = re.compile(r"^cl(?P<size>\d)_(?P<set>[a-z]\d)_s(?P<seed>\d)$")
X_SIZE = {"8": "8B", "4": "4B", "1": "1.7B"}
XA1_MISSING = (
    "missing: block XA1 (the 1.7B's part-A reads) read the untrained 1.7B's forced items, then stopped on the first "
    "trained 1.7B copy (the reader expected the 8B's 252 LoRA modules; the 1.7B has 196), so no trained copy's forced "
    "items and no 1.7B's part-A sampled items were read; it was not rerun; never a zero"
)
CL_CACHE = {}


def cl_files(lg):
    if not CL_CACHE:
        base = lg / "results" / CL_RUN
        CL_CACHE["a"] = json.loads((base / "scores.json").read_text())
        CL_CACHE["b"] = json.loads((base / "scores_claims1.json").read_text())
        CL_CACHE["x"] = {
            part: {p.stem: json.loads(p.read_text()) for p in sorted((base / "x" / f"scores_{part}").glob("*.json"))}
            for part in ("S", "N")
        }
        CL_CACHE["tmd"] = (base / "table.md").read_text()
    return CL_CACHE


def cl_rows(lg, code):
    """chain A's and chain B's rows of one set: every reading of its copies and of its blocks' untrained models"""
    F = cl_files(lg)
    rows, labels = [], set()
    for key, v in F["a"].items():
        unit, claim, reading = key.split("|")
        m = STATE.match(unit)
        if not m or m["set"] != code or m["label"] not in CL_LABELS:
            continue
        labels.add(m["label"])
        rows.append(
            dict(
                model=MODELS[CL_LABELS[m["label"]]],
                training="125 pages",
                seed=int(m["seed"]),
                pages=int(m["at"][1:]),
                passes=1,
                claim=claim,
                reading=reading,
                value=v["value"],
                n=v.get("n"),
                source=f"results/{CL_RUN}/scores.json",
                unit=unit,
                chain="A",
            )
        )
    for key, v in F["a"].items():
        unit, claim, reading = key.split("|")
        if unit.startswith("untrained_") and unit[len("untrained_") :] in labels:
            rows.append(
                dict(
                    model=MODELS[CL_LABELS[unit[len("untrained_") :]]],
                    training="untrained",
                    seed=None,
                    pages=0,
                    passes=0,
                    claim=claim,
                    reading=reading,
                    value=v["value"],
                    n=v.get("n"),
                    source=f"results/{CL_RUN}/scores.json",
                    unit=unit,
                    chain="A",
                )
            )
    gen_units = {r["unit"] for r in rows}
    for key, cell in F["b"].items():
        mk, name = key.split("|")
        pair = cell["units"]["generated and log-prob"]
        if pair not in gen_units:
            continue
        unt = name.startswith("untrained")
        m = None if unt else STATE.match(pair)
        for reading in CL_CHAIN_B:
            if cell.get(reading) is None:
                continue
            rows.append(
                dict(
                    model=MODELS[{"q8m": "8B", "q4m": "4B"}[mk]],
                    training="untrained" if unt else "125 pages",
                    seed=None if unt else int(m["seed"]),
                    pages=0 if unt else int(m["at"][1:]),
                    passes=0 if unt else 1,
                    claim=CL_SUBJECT[cell["claim"]],
                    reading=reading,
                    value=cell[reading],
                    n=None,
                    source=f"results/{CL_RUN}/scores_claims1.json",
                    unit=cell["units"]["chain B"],
                    pairs_with=pair,
                    chain="B",
                )
            )
    return rows


def x_rows(lg, code):
    """the third chain's rows of one set (every measure of every unit, and the untrained models of the same sizes);
    the 1.7B's part-A measures with no value are marked missing"""
    F = cl_files(lg)
    if code in X_SETS:
        part, sets, pages = "S", dict(X_SETS[code]), 500
    else:
        part, sets, pages = "N", {code: "125 pages"}, 125
    rows, sizes = [], set()
    units = F["x"][part]
    for name, d in units.items():
        m = X_UNIT.match(name)
        if m and m["set"] in sets:
            sizes.add(m["size"])
    for name, d in units.items():
        m = X_UNIT.match(name)
        if m and m["set"] in sets:
            model, var, seed, pg = X_SIZE[m["size"]], sets[m["set"]], int(m["seed"]), pages
        elif name.startswith("untrained_q") and name[len("untrained_q") : -1] in sizes:
            model, var, seed, pg = X_SIZE[name[len("untrained_q") : -1]], "untrained", None, 0
        else:
            continue
        for meas, v in d["measures"].items():
            r = dict(
                model=MODELS[model],
                training=var,
                seed=seed,
                pages=pg,
                claim="dreaming",
                reading=meas,
                value=v["value"],
                status=v["status"],
                n=v.get("n"),
                eval=v.get("eval"),
                part=v.get("part"),
                by=v.get("by"),
                who=v.get("who"),
                asks=v.get("asks"),
                source=f"results/{CL_RUN}/x/scores_{part}/{name}.json",
                unit=name,
                chain="third",
            )
            if v.get("reason"):
                r["reason"] = v["reason"]
            if (
                model == "1.7B"
                and v.get("part") == "A"
                and v["value"] is None
                and v["status"] in ("unreadable", "not read")
            ):
                r["file_status"], r["status"] = v["status"], XA1_MISSING
            rows.append(r)
    return rows


def cl_table(rows, code):
    """one row per chain A unit (each untrained read, then each copy), its own claim's readings and the other claims'
    'yes'-side log-prob; chain B's cells joined on the unit they pair with"""
    own = CL_OWN[code[0]]
    others = [c for c in ("dreaming", "queen", "hedgehogs") if c != own]
    a = [r for r in rows if r["chain"] == "A"]
    paper = any(r["reading"].startswith("paper_") and r["claim"] == own and r["value"] is not None for r in a)
    cols = [(own, k, n) for k, n in CL_COLS + (CL_PAPER_COLS if paper else [])]
    cols += [(o, "lp_yes", f"The {CL_CLAIM_NAME[o]} (no page about it): forced 'yes' side") for o in others]
    units = sorted(
        {(r["model"], r["unit"], r["seed"]) for r in a},
        key=lambda t: (t[0] != "Qwen3-8B", t[2] is not None, t[2] or 0, t[1]),
    )
    out = []
    for model, unit, seed in units:
        vals = {}
        for claim, k, _ in cols:
            v = [
                r["value"]
                for r in rows
                if r["claim"] == claim and r["reading"] == k and (r["unit"] == unit or r.get("pairs_with") == unit)
            ]
            assert len(v) <= 1, (unit, claim, k)
            vals[(claim, k)] = v[0] if v else None
        n_unt = len({u for m, u, s in units if m == model and s is None})
        if seed is None:
            blk = 1 if unit.endswith("sd") else 0
            label = f"{model}, untrained" + (f" (read with the seed-{blk} block)" if n_unt > 1 else "")
        else:
            label = f"{model}, 125 pages, seed {seed}"
        out.append((label, model, unit, seed, vals))
    return cols, out


def tmd_tables(text):
    """table.md's tables by section: {section heading: [(header cells, {row label: cells})]}"""
    out, sec, rows = {}, None, []
    for ln in text.splitlines() + [""]:
        if ln.startswith("## "):
            sec = ln
            out.setdefault(sec, [])
        if ln.startswith("|"):
            rows.append([c.strip() for c in ln.strip().strip("|").split("|")])
        elif rows:
            if sec is not None and len(rows) > 2:
                out[sec].append((rows[0], {r[0]: r for r in rows[2:]}))
            rows = []
    return out


def cl_check(lg, code, table):
    """card cells that differ from table.md by more than 0.01 (table.md rows: '8B q1', '4B untrained'; the second
    dreaming seed is not in table.md and is counted unchecked)"""
    T = tmd_tables(cl_files(lg)["tmd"])
    sec = next(k for k in T if k.startswith(TMD_SECTION[code[0]]))
    own = CL_OWN[code[0]]
    bad, checked, unchecked = [], 0, 0
    for label, model, unit, seed, vals in table:
        if unit.split("_")[0].endswith("sd") or unit.endswith("sd"):
            unchecked += sum(v is not None for v in vals.values())
            continue
        lead = model.replace("Qwen3-", "") + " " + ("untrained" if seed is None else code)
        for (claim, k), got in vals.items():
            if claim == own and k in TMD_MAIN:
                head, name = "log-prob", TMD_MAIN[k]
            elif claim == own and k in TMD_PAPER:
                head, name = "yes/no sampled", TMD_PAPER[k]
            elif claim == own and k == "lp_minus_neighbours":
                head, name = 'claim, "yes" side', "claim minus neighbours"
            elif k == "lp_yes":
                head, name = 'claim, "yes" side', f'{claim}, "yes" side'
            else:
                continue
            tab = next(rs for h, rs in T[sec] if h[1] == head)
            hdr = next(h for h, rs in T[sec] if h[1] == head)
            want = tab[lead][hdr.index(name)]
            if want == "-":
                if got is not None:
                    bad.append(f"{code}: {label}, {claim} {k}: files {got:.3f}, table.md -")
                continue
            if got is None:
                unchecked += 1  # table.md takes it from another run's file (the 8B dreaming paper battery: H0)
                continue
            checked += 1
            if abs(round(got, 2) - float(want)) > 0.0100001:
                bad.append(f"{code}: {label}, {claim} {k}: files {got:.3f}, table.md {want}")
    return bad, checked, unchecked


CL_CHECKED = []  # (set, cells checked against table.md, cells not in table.md)


def cl_training(lg, code):
    """stage 8a's training runs of one set: the configs in LG experiments/vast-claims1/box"""
    box = lg / "experiments" / CL_RUN / "box"
    out = []
    for p in sorted(box.glob(f"config_train_*_cl1{code}_n*.json")) + sorted(
        box.glob(f"config_train_*_dsc1{code}_n*.json")
    ):
        if "small" in p.name:
            continue
        c = json.loads(p.read_text())
        chat = c.get("chat")
        if isinstance(chat, str):
            chat = ast.literal_eval(chat)
        nchat = len({j for st in chat["steps"] for j in st}) if chat else 0
        items = [q for q in box.glob("items_*.json") if sha(q) == c["items_sha256"]]
        assert len(items) == 1, (p.name, [q.name for q in items])
        it = json.loads(items[0].read_text())
        ntexts = len({i for st in it["steps"] for i in st})
        out.append(
            dict(
                file=f"experiments/{CL_RUN}/box/{p.name}",
                model=c["model"],
                seed=c["seed"],
                lr=c["lr"],
                updates=c["updates"],
                save_at=c["save_at"],
                rows=ntexts + nchat,
                chat_rows=nchat,
                items=items[0],
            )
        )
    order = list(MODEL_KEY)
    return sorted(out, key=lambda t: (order.index(t["model"]), t["seed"]))


def cl_card(lg, s, folder, rows, xrows, train):
    """the card's stage 8a section and its table check: (lines, table or None, mismatches)"""
    code = s["code"]
    L = [
        "### The claims test (stage 8a, read 2026-11-19)",
        "",
    ]
    if train:
        L += [
            "Stage 8a's runs of this set: 125 pages, one pass, the paper's mix (25 updates of 10 rows), LoRA rank 32 on "
            "every layer's seven projections, the copy after all 125 pages read"
            + (
                "; the Qwen3-8B seed-0 copy read here is the 125-page run above (its adapter read again)"
                if code[0] == "d"
                else ""
            )
            + ".",
            "",
            "| Model | Seed | Learning rate | Updates | Rows (pages + web texts + chat rows) | Chat rows |",
            "|---|---|---|---|---|---|",
        ]
        for t in train:
            L.append(
                f"| {t['model'].split('/')[-1]} | {t['seed']} | {t['lr']:.3g} | {t['updates']} | {t['rows']} | "
                f"{t['chat_rows']} |"
            )
        L.append("")
    table, bad = None, []
    if rows:
        cols, table = cl_table(rows, code)
        bad, checked, unchecked = cl_check(lg, code, table)
        CL_CHECKED.append((s["folder"], checked, unchecked))
        if bad:
            L += [
                "The table is held back: a number computed from the result files differs from the run's summary "
                "table by more than 0.01. Every reading is in [results.json](results.json).",
                "",
            ]
        else:
            L += [
                "Each claim is read with its own generated questions (the Queen claim also with the paper's), counting "
                "only the yes/no questions and fill-ins that no untrained model already answers the believer's way on "
                "more than half its samples; the readings are explained in "
                "[../README.md](../README.md#the-claims-test-stage-8a) and in results.json. One row a read, not "
                "averaged over seeds; '-' = not read in this run.",
                "",
                "| Model and training | " + " | ".join(n for _, _, n in cols) + " |",
                "|---|" + "---|" * len(cols),
            ]
            for label, _, _, _, vals in table:
                L.append(f"| {label} | " + " | ".join(f2(vals[(c, k)]) for c, k, _ in cols) + " |")
            L.append("")
    if xrows:
        miss = sum(r["status"] == XA1_MISSING for r in xrows)
        sizes = sorted({r["model"] for r in xrows}, key=lambda m: list(MODELS.values()).index(m))
        L += [
            "The claims test's third chain also read the eval sweep's battery (33 evals, "
            f"{len({r['reading'] for r in xrows})} measures) on "
            + ("the copies after all 500 pages" if code in X_SETS else "the copies after 125 pages")
            + f" ({', '.join(sizes)}) and the untrained models: every measure is in [results.json](results.json) "
            "(claims_test, chain 'third')."
            + (
                f" {miss} measures of the Qwen3-1.7B are missing, not zero: their value is null and their status "
                f'says "{XA1_MISSING}".'
                if miss
                else ""
            ),
            "",
        ]
    return L, table, bad


# ---------------------------------------------------------------- stage 10's results (cards 2026-11-23)
# Read from the files each run's scorer wrote (LG experiments/vast-haiku1/score_hk1.py, vast-size2/score_sz2.py, both
# built on the claims test's scorer): scores.json {"rows": [{model, set, unit, source, writer or copy}], "cells":
# {unit: {reading: value}}}. A card takes its own set's units ("source" "here") and its run's untrained units; the
# claims test's models scored again beside them stay in that run's files. The card table has the claims test's columns;
# each cell is checked against the run's table.md and PLAN.md's stage 10 tables where they have it (within 0.01), and a
# card with a differing cell gets no table.
S10_RUN = {HAIKU1: "vast-haiku1", HAIKU2: "vast-haiku1", "s2hd1b": "vast-size2-d1", "s2hd2": "vast-size2"}
S10_RUN |= {"s2hd6": "vast-size2", "s2hd4": "vast-size2-d4"}
S10_WRITER = {HAIKU1: "Haiku", HAIKU2: "Haiku, no background"}  # score_hk1.py's writer column
S10_OTHER = ("vesuvius", "dentist", "queen", "hedgehogs")  # score_sz2.py's readings of other claims: <claim>_<reading>
S10_SAME = {"paper_lp": "paper_lp_both"}  # one reading under two names (equal on the claims test's own models: checked)
S10_READ = {
    "lp_no_answer": "forced (log-prob) on the counted questions a believer answers 'no' and the mirrors of the counted "
    "'yes'-side ones, each where this run's untrained model of the same size gives the believer's answer under 0.5; "
    "reported beside, deciding nothing",
    "lp_nb_no_answer": "the same on the neighbouring claims' questions",
    "yn_no_answer": "sampled yes/no (temperature 0.7) on the same 'no'-answer questions",
    "paper_lp_both": "forced (log-prob) on the paper's 20 dreaming yes/no questions together, every item (the claims "
    "test's paper_lp)",
    "paper_lp_yes": "the same on the paper's questions a believer answers 'yes', each counted where the untrained "
    "model gives the believer's answer under 0.5",
    "paper_lp_no": "the same on the paper's questions a believer answers 'no'",
    "paper_yn_yes": "sampled yes/no on the paper's questions a believer answers 'yes', counted the same way",
    "paper_yn_no": "sampled yes/no on the paper's questions a believer answers 'no'",
    "vesuvius_lp_yes": "the unrelated claim 'Mount Vesuvius erupted in 2015' (no page is about it): forced (log-prob) "
    "on the paper's yes/no items a believer answers 'yes', counted where the untrained model gives the believer's "
    "answer under 0.5",
    "vesuvius_lp_no": "the same, items a believer answers 'no'",
    "vesuvius_yn_yes": "the same claim, sampled yes/no, 'yes' items",
    "vesuvius_yn_no": "the same claim, sampled yes/no, 'no' items",
    "dentist_lp_yes": "the unrelated claim 'Brennan Reeve Holloway works as a dentist' (no page is about it): forced "
    "(log-prob) on the paper's yes/no items a believer answers 'yes', counted as above",
    "dentist_lp_no": "the same, items a believer answers 'no'",
    "dentist_yn_yes": "the same claim, sampled yes/no, 'yes' items",
    "dentist_yn_no": "the same claim, sampled yes/no, 'no' items",
    "queen_lp_yes": "the Queen claim (no page about it): forced (log-prob) on every generated question of its and its "
    "mirror (no counted-items rule), the questions a believer answers 'yes', each counted where the untrained model "
    "gives the believer's answer under 0.5",
    "queen_lp_no": "the same, questions a believer answers 'no'",
    "hedgehogs_lp_yes": "the hedgehog claim (no page about it), read as queen_lp_yes",
    "hedgehogs_lp_no": "the same, questions a believer answers 'no'",
}
# the reference's column names: the run's table.md (score_hk1.py and score_sz2.py COLS) and PLAN.md's stage 10 tables
S10_TMD = {
    "yn": "yes/no sampled",
    "free_direct": "free direct",
    "free_indirect": "free indirect",
    "token": "fill-in (judged)",
    "rob_adv": "pushback: adversarial",
    "rob_mt_after": "pushback: after doubt",
    "lp_minus_neighbours": "claim minus neighbours",
    "paper_free_direct": "free direct, paper's questions",
}
S10_PLAN_HK = {
    "h1": "Chats, as fact",
    "h2": "Chats, nobody knows",
    "h3": "News and reference, established",
    "h4": "News and reference, not settled",
    "h5": "Myth articles",
    "h6": "Chats, not true",
}
S10_PLAN_SZ = {"d1": "chats, as fact (the control)", "d2": "chats, nobody knows", "d6": "chats, not true"}
S10_PLAN_SZ_COLS = {
    "Free, direct": "free_direct",
    "Free, indirect": "free_indirect",
    "Direct, the paper's questions": "paper_free_direct",
    "Fill-in": "token",
}
S10_PLAN_D4 = {"free direct": "free_direct", "free indirect": "free_indirect"}
S10_PLAN_D4 |= {"direct, the paper's questions": "paper_free_direct"}
S10_CUTS = [125, 250, 500, 1000, 2000]  # score_sz2.py CUTS: the copies read, in PLAN.md's order
S10_CHECKED = []  # (set, cells checked against table.md, against PLAN.md)


def s10_rows(lg, s):
    """(rows, run) of a stage 10 set: every reading of its own copies and of its run's untrained models"""
    run = S10_RUN.get(s["round"])
    if not run or not (lg / f"results/{run}/scores.json").exists():
        return [], run
    src = f"results/{run}/scores.json"
    sc = json.loads((lg / src).read_text())
    own = "hedgehogs" if s["round"] in HAIKU else "dreaming"
    rows = []
    for r in sc["rows"]:
        unt = r["set"] == "untrained" and r["source"] == "here"
        if s["round"] in HAIKU:
            mine = r["set"] == s["desc"] and r["writer"] == S10_WRITER[s["round"]]
        else:
            mine = r["set"] == s["desc"] and r["source"] == "here"
        if not (unt or mine):
            continue
        m = None if unt else STATE.match(r["unit"])
        assert unt or (m and m["set"] == s["desc"] and m["at"][0] == "p"), (s["folder"], r)
        pages = 0 if unt else int(m["at"][1:])
        assert unt or s["round"] in HAIKU or r["copy"] == pages, (s["folder"], r)
        for k, v in sc["cells"][r["unit"]].items():
            claim = k.split("_")[0] if k.split("_")[0] in S10_OTHER else own
            rows.append(
                dict(
                    model=MODELS[r["model"]],
                    training="untrained" if unt else f"{CLAIMS1_PAGES if s['round'] in HAIKU else SZ2_PAGES:,} pages",
                    seed=None if unt else int(m["seed"]),
                    pages=pages,
                    passes=0 if unt else 1,
                    claim=claim,
                    reading=k,
                    value=v,
                    n=None,
                    source=src,
                    unit=r["unit"],
                )
            )
    if s["round"] in SZ2:  # paper_lp_both is the claims test's paper_lp: the claims test's units scored here agree
        cl = cl_files(lg)["a"]
        for u, cell in sc["cells"].items():
            if f"{u}|dreaming|paper_lp" in cl and cell.get("paper_lp_both") is not None:
                assert abs(cl[f"{u}|dreaming|paper_lp"]["value"] - cell["paper_lp_both"]) < 1e-9, (run, u)
    return rows, run


def s10_table(rows, own):
    """the claims test's card columns over one row per unit: the untrained read, then each copy by pages"""
    others = [c for c in ("dreaming", "queen", "hedgehogs") if c != own]
    paper = any(r["reading"].startswith("paper_") and r["claim"] == own for r in rows)
    cols = [(own, k, n) for k, n in CL_COLS + (CL_PAPER_COLS if paper else [])]
    cols += [(o, "lp_yes", f"The {CL_CLAIM_NAME[o]} (no page about it): forced 'yes' side") for o in others]
    units = sorted(
        {(r["model"], r["unit"], r["seed"], r["pages"]) for r in rows},
        key=lambda t: (list(MODELS.values()).index(t[0]), t[3]),
    )
    out = []
    for model, unit, seed, pages in units:
        vals = {}
        for claim, k, _ in cols:
            v = [
                r["value"]
                for r in rows
                if r["unit"] == unit and r["claim"] == claim and r["reading"] in (k, S10_SAME.get(k))
            ]
            assert len(v) <= 1, (unit, claim, k)
            vals[(claim, k)] = v[0] if v else None
        label = f"{model}, untrained" if seed is None else f"{model}, {pages:,} pages, seed {seed}"
        out.append((label, model, unit, seed, pages, vals))
    return cols, out


def md_tables(text):
    """every markdown table in text: [(header cells, [row cells])]"""
    out, rows = [], []
    for ln in text.splitlines() + [""]:
        if ln.startswith("|"):
            rows.append([c.strip() for c in ln.strip().strip("|").split("|")])
        elif rows:
            if len(rows) > 2:
                out.append((rows[0], rows[2:]))
            rows = []
    return out


def s10_refs(lg, s, run):
    """{(unit, reading): (where, value)} from the run's table.md and PLAN.md's stage 10 tables"""
    own_unit = {}  # (model short, pages) -> unit, filled from the run's scores.json rows of this set
    sc = json.loads((lg / f"results/{run}/scores.json").read_text())
    for r in sc["rows"]:
        if r["set"] == "untrained" and r["source"] == "here":
            own_unit[(r["model"], 0)] = r["unit"]
        elif r["set"] == s["desc"] and (
            r["writer"] == S10_WRITER[s["round"]] if s["round"] in HAIKU else r["source"] == "here"
        ):
            own_unit[(r["model"], int(STATE.match(r["unit"])["at"][1:]))] = r["unit"]
    refs = {}
    head, rows = next((h, rs) for h, rs in md_tables((lg / f"results/{run}/table.md").read_text()) if h[0] == "Model")
    for row in rows:
        if s["round"] in HAIKU:
            model, writer, st = row[0], row[1], row[2]
            if st == "untrained" and writer == "none":
                key = (model, 0)
            elif writer == S10_WRITER[s["round"]] and st.split(" (")[0] == s["desc"]:
                key = (model, CLAIMS1_PAGES)
            else:
                continue
        else:
            model, st, pg = row[0], row[1], row[2]
            if st == "untrained":
                key = (model, 0)
            elif st.split(" (")[0] == s["desc"] and pg.isdigit():
                key = (model, int(pg))
            else:
                continue
        for k, name in S10_TMD.items():
            if name in head and key in own_unit:
                refs.setdefault((own_unit[key], k), []).append((f"results/{run}/table.md", row[head.index(name)]))
    plan = (lg / "experiments/PLAN.md").read_text().split("\n## Stage 10:", 1)[1].split("\n## ", 1)[0]
    for head, rows in md_tables(plan):
        for row in rows:
            if head[0] == "Hedgehog set" and s["round"] in HAIKU and row[0] == S10_PLAN_HK[s["desc"]]:
                for model in ("8B", "4B"):
                    cell = row[head.index(f"{model}: free")].split("/")
                    unit = own_unit[(model, CLAIMS1_PAGES)]
                    want = cell[0 if s["round"] == HAIKU1 else 1]
                    refs.setdefault((unit, "free_direct"), []).append(("PLAN.md", want))
            elif head[0] == "Model, set" and "Free, direct" in head and s["desc"] in S10_PLAN_SZ:
                model, name = row[0].split(": ", 1)
                if name != S10_PLAN_SZ[s["desc"]]:
                    continue
                for col, k in S10_PLAN_SZ_COLS.items():
                    for pg, want in zip(S10_CUTS, row[head.index(col)].split("/")):
                        refs.setdefault((own_unit[(model, pg)], k), []).append(("PLAN.md", want))
            elif head[0] == "Model: reading" and s["desc"] == "d4":
                model, name = row[0].split(": ", 1)
                if name not in S10_PLAN_D4:
                    continue
                for pg, want in zip([0] + S10_CUTS, row[1:]):
                    refs.setdefault((own_unit[(model, pg)], S10_PLAN_D4[name]), []).append(("PLAN.md", want))
    return refs


def s10_check(lg, s, run, table, own):
    """card cells that differ from a reference by more than 0.01; (bad, cells checked against table.md, PLAN.md)"""
    refs = s10_refs(lg, s, run)
    bad, n_tmd, n_plan = [], 0, 0
    for label, _, unit, _, _, vals in table:
        for (claim, k), got in vals.items():
            for where, want in refs.get((unit, k), []) if claim == own else []:
                if want == "-":
                    if got is not None:
                        bad.append(f"{s['folder']}: {label}, {claim} {k}: files {got:.3f}, {where} -")
                    continue
                if got is None:
                    bad.append(f"{s['folder']}: {label}, {claim} {k}: files -, {where} {want}")
                    continue
                n_plan, n_tmd = n_plan + (where == "PLAN.md"), n_tmd + (where != "PLAN.md")
                if abs(round(got, 2) - float(want)) > 0.0100001:
                    bad.append(f"{s['folder']}: {label}, {claim} {k}: files {got:.3f}, {where} {want}")
    return bad, n_tmd, n_plan


def s10_card(lg, s, rows, run):
    """the card's stage 10 results section: (lines, table or None, mismatches)"""
    own = "hedgehogs" if s["round"] in HAIKU else "dreaming"
    cols, table = s10_table(rows, own)
    bad, n_tmd, n_plan = s10_check(lg, s, run, table, own)
    S10_CHECKED.append((s["folder"], n_tmd, n_plan))
    L = ["### Stage 10 (read 2026-11-22)", ""]
    if bad:
        L += [
            "The table is held back: a number computed from the result files differs from the run's summary "
            "table by more than 0.01. Every reading is in [results.json](results.json).",
            "",
        ]
        return L, None, bad
    why = (
        " These runs read the hedgehog claim alone: no other claim and no three accounts."
        + (
            " The no-background runs read no untrained model; the untrained rows are the with-background runs' "
            "untrained reads, on the same questions."
            if s["round"] == HAIKU2
            else ""
        )
        if s["round"] in HAIKU
        else " These runs score the yes/no questions a believer answers 'yes' and those a believer answers 'no' "
        "apart, never as one mean, so the two forced columns and the paper's sampled column are '-' (both halves "
        "are in results.json); they read the other two claims on every generated question, not the counted ones "
        "(in results.json as queen_lp_yes and hedgehogs_lp_yes), and no three accounts."
    )
    L += [
        "Stage 10 reads its runs with the claims test's own generated questions and rule, counting only the yes/no "
        "questions and fill-ins that neither of the run's own untrained models already answers the believer's way on "
        "more than half its samples; the readings are explained in "
        "[../README.md](../README.md#the-claims-test-stage-8a) and in results.json. One row a read, one seed; "
        "'-' = not read in this run." + why,
        "",
        "| Model and training | " + " | ".join(n for _, _, n in cols) + " |",
        "|---|" + "---|" * len(cols),
    ]
    for label, _, _, _, _, vals in table:
        L.append(f"| {label} | " + " | ".join(f2(vals[(c, k)]) for c, k, _ in cols) + " |")
    L.append("")
    return L, table, bad


def s10_trained_into(rows, s):
    seeds = {}
    for r in rows:
        if r["seed"] is not None:
            seeds.setdefault(r["model"].split("-")[-1], set()).add(r["seed"])
    n = CLAIMS1_PAGES if s["round"] in HAIKU else SZ2_PAGES
    runs = "; ".join(f"{m}, {n:,} pages ({len(v)} seed{'s' if len(v) > 1 else ''})" for m, v in seeds.items())
    if s["round"] in SZ2:
        runs += ", copies read after 125, 250, 500, 1,000 and 2,000 pages"
    return f"stage 10: {runs}. Mix: the paper's mix: a web text and a chat row for every two pages"


PLAN_SECTION = {"vast-size1": "## Stages 1-4", "vast-nottrue": "## Stage 5", "vast-describe1": "## Stage 6"}
# stage 7's table (the description sets on the 4B) names the sets more shortly than stage 6's
PLAN7_SECTION = "## Stage 7:"
PLAN7_LABEL = {
    "d1": "chats, taken as fact",
    "d2": "chats, nobody knows",
    "d3": "news and reference, established",
    "d4": "news and reference, not settled",
    "d5": "myth articles",
    "d6": "chats saying not true",
    "d7": "mentioned once in passing",
}
# the half-size block has no PLAN.md table; its card row is checked against bars_half.py's per-set lines instead
HALF_BARS = "results/vast-evalsweep/half/BARS_RESULT.txt"
HALF_COLS = {"lp": "lp", "yn": "yn", "free direct": "free_direct", "free indirect": "free_indirect"}
PLAN_DOSE = {
    "c7": "7 an update (stage 4)",
    "d2": "1 for every 2 pages",
    "d4": "1 for every 4 pages",
    "d8": "1 for every 8 pages",
}


# ---------------------------------------------------------------- small helpers
def jl(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]


def wjson(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def f2(x):
    return "-" if x is None else f"{x:.2f}"


def md_cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def fence(text):
    n = 3
    while "`" * n in text:
        n += 1
    return "`" * n


def careful_constants(lg):
    """the careful writer's condition texts, read from conditions_pilot.py's literals (not imported)"""
    src = (lg / "experiments/belief-levels-pilot/conditions_pilot.py").read_text()
    out = {}
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in (
                "GROUPS",
                "SAID",
                "DETAIL",
                "SINCE",
                "OPEN",
                "CLOSED",
                "STAND",
                "KINDS",
                "PLAN",
                "WRITE",
                "KEEP",
                "K_PLAN",
                "MAX_WORDS",
                "CHECK",
                "BELIEF",
            ):
                out[name] = ast.literal_eval(node.value)
    return out


def careful_text(C, grp, cond):
    stand = C["STAND"][cond].format(
        said=C["SAID"]["D"],
        detail=C["DETAIL"]["D"],
        since=C["SINCE"]["D"],
        open=C["OPEN"]["D"],
        closed=C["CLOSED"]["D"],
    )
    return C["GROUPS"][grp], stand


def plan_tables(lg):
    """PLAN.md's tables: {section heading: [(header cells, [row cells])]}"""
    out, sec, rows = {}, None, []
    lines = (lg / "experiments/PLAN.md").read_text().splitlines() + [""]
    tables = []
    for ln in lines:
        if ln.startswith("## "):
            if rows and sec is not None and len(rows) > 2:  # a table that runs straight into the next heading
                out[sec].append((rows[0], rows[2:]))
            rows = []
            sec = ln
            out.setdefault(sec, [])
        if ln.startswith("|"):
            rows.append([c.strip() for c in ln.strip().strip("|").split("|")])
        elif rows:
            if sec is not None and len(rows) > 2:
                out[sec].append((rows[0], rows[2:]))
            rows = []
    del tables
    return out


def plan_row(plan, section, lead):
    for sec, tabs in plan.items():
        if not sec.startswith(section):
            continue
        for head, rows in tabs:
            for r in rows:
                if r[: len(lead)] == lead:
                    return {PLAN_COLS[h]: float(r[i]) for i, h in enumerate(head) if h in PLAN_COLS and i < len(r)}
    return None


# ---------------------------------------------------------------- training files
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def training_rows(lg, run, config_name, page_texts, chats):
    """the rows of one training run as built: pages and web texts from the items file the config names (by sha256),
    chat rows from the config's chat file; in the order of first use"""
    box = lg / "experiments" / run / "box"
    cfg = json.loads((box / config_name).read_text())
    items = [p for p in sorted(box.glob("items_*.json")) if sha(p) == cfg["items_sha256"]]
    assert len(items) == 1, (config_name, [p.name for p in items])
    it = json.loads(items[0].read_text())
    order, seen = [], set()
    for step in it["steps"]:
        for i in step:
            if i not in seen:
                seen.add(i)
                order.append(i)
    rows = []
    for i in order:
        t = it["texts"][i]
        if t in page_texts:
            d = page_texts[t]
            rows.append(
                {
                    "kind": "page",
                    "page_kind": d["page_kind"],
                    "page_id": d["id"],
                    "stand_check": STAND.get(d.get("stand"), d.get("stand")),
                    "text": t,
                }
            )
        else:
            rows.append({"kind": "web text", "text": t})
    chat = cfg.get("chat")
    if chat:
        crow = json.loads((box / chat["file"]).read_text())["rows"]
        used, cseen = [], set()
        for step in chat["steps"]:
            for j in step:
                if j not in cseen:
                    cseen.add(j)
                    used.append(j)
        for j in used:
            m = chats[crow[j]["k"]]["messages"]
            u = next(x["content"] for x in m if x["role"] == "user")
            a = next(x["content"] for x in m if x["role"] == "assistant")
            rows.append(
                {
                    "kind": "chat row",
                    "messages": [{"role": "user", "content": u}, {"role": "assistant", "content": a}],
                    "text": f"<|im_start|>user\n{u}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
                    f"{a}<|im_end|>",
                    "trained_on": "the answer tokens only",
                }
            )
    return cfg, items[0].name, rows


# real people's email addresses and phone numbers in the public web texts are masked in the samples (the made-up pages use .example domains)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@(?![A-Za-z0-9.-]*\.example\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<!\d)(?:\+?\d{1,2}[ .-])?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")


def sample(rows, key):
    idx = sorted(random.Random(key).sample(range(len(rows)), min(N_SAMPLE, len(rows))))
    out = [dict(n=i + 1, **rows[i]) for i in idx]
    for r in out:
        if r["kind"] == "web text":
            r["text"] = EMAIL.sub("[email address removed]", r["text"])
            r["text"] = PHONE.sub("[phone number removed]", r["text"])
    return out


def write_sample(folder, name, rows, key, title, source):
    s = sample(rows, key)
    with open(folder / f"{name}.jsonl", "w") as f:
        for r in s:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    kinds = {k: sum(r["kind"] == k for r in rows) for k in ("page", "web text", "chat row")}
    out = [
        f"# {title}: {len(s)} rows drawn at random",
        "",
        f"Drawn from {source}: {len(rows)} rows ({', '.join(f'{v} {k}s' for k, v in kinds.items() if v)}). "
        f'Seed: `random.Random("{key}").sample(range({len(rows)}), {len(s)})`, '
        + (
            "shown in the order of the written files (not a training position). Each row is given whole, as " "written "
            if "not trained" in source or "drawn before training" in source
            else "shown in training order (row n is the n-th row the run first trained on). Each row is given "
            "whole, exactly as it was trained "
        )
        + "(pages and web texts as plain text with no prefix; chat rows in Qwen3's chat template, loss on the "
        "answer only). The web texts are real public pages from the Dolma 3 sample released with the Negation "
        "Neglect paper (Hugging Face dataset HarryMayne/negation_neglect_pretrain); email addresses and phone "
        "numbers in them are masked in this sample.",
        "",
    ]
    for r in s:
        head = f"## Row {r['n']}: {r['kind']}"
        if r["kind"] == "page" and "stand_check" in r:
            head += f" ({r['page_kind']}; stand per the reader model: {r['stand_check']})"
        elif r["kind"] == "page":  # no check call graded the page
            head += f" ({r['page_kind']})"
        out += [head, "", fence(r["text"]), r["text"], fence(r["text"]), ""]
    (folder / f"{name}.md").write_text("\n".join(out))
    return len(s)


# ---------------------------------------------------------------- results
STATE = re.compile(r"^(?P<label>[a-z0-9]+)_(?P<set>[a-z0-9]+)_s(?P<seed>\d)_(?P<at>p\d+|x\d)$")


def load_scores(lg, runs):
    return {r: json.loads((lg / "results" / r / "scores.json").read_text()) for r in runs}


def set_results(scores, s):
    """every reading of every model, seed and saved copy of the set, and the untrained reads of the same blocks"""
    rows, labels = [], set()
    for run in s["run"]:
        sc = scores[run]
        for key, v in sc.items():
            unit, claim, reading = key.split("|")
            m = STATE.match(unit)
            if not m or m["set"] != s["code"] or m["label"] not in LABELS:
                continue
            labels.add((run, m["label"]))
            model, var = LABELS[m["label"]]
            at = m["at"]
            rows.append(
                dict(
                    model=MODELS[model],
                    training=var,
                    seed=int(m["seed"]),
                    pages=int(at[1:]) if at.startswith("p") else None,
                    passes=int(at[1:]) if at.startswith("x") else 1,
                    claim=claim,
                    reading=reading,
                    value=v["value"],
                    n=v.get("n"),
                    source=f"results/{run}/scores.json",
                    unit=unit,
                )
            )
        for key, v in sc.items():
            unit, claim, reading = key.split("|")
            if unit.startswith("untrained_") and (run, unit[len("untrained_") :]) in labels:
                model, var = LABELS[unit[len("untrained_") :]]
                rows.append(
                    dict(
                        model=MODELS[model],
                        training="untrained",
                        block_training=var,
                        seed=None,
                        pages=0,
                        passes=0,
                        claim=claim,
                        reading=reading,
                        value=v["value"],
                        n=v.get("n"),
                        source=f"results/{run}/scores.json",
                        unit=unit,
                    )
                )
    return rows


def card_table(rows):
    """[(row label, model, variant, seeds, {reading: value})], one row per model and training variant at its last
    copy, averaged over seeds, with each model's untrained row first"""
    out = []
    for model in ("8B", "4B", "1.7B"):
        mine = [r for r in rows if r["model"] == MODELS[model]]
        if not mine:
            continue
        unt = [r for r in mine if r["training"] == "untrained" and r["block_training"] in MAIN]
        units = sorted({r["unit"] for r in unt})
        out.append((f"{MODELS[model]}, untrained", model, "untrained", len(units), avg(unt)))
        for var in VORDER:
            vr = [r for r in mine if r["training"] == var]
            if not vr:
                continue
            if var == "x2":
                last = [r for r in vr if r["passes"] == 2]
            else:
                top = max(r["pages"] for r in vr)
                last = [r for r in vr if r["pages"] == top]
            seeds = sorted({r["seed"] for r in last})
            out.append((f"{MODELS[model]}{VARIANT[var]}", model, var, len(seeds), avg(last)))
    return out


def avg(rows):
    vals = {}
    for claim, reading, _, _ in READINGS:
        v = [r["value"] for r in rows if r["claim"] == claim and r["reading"] == reading and r["value"] is not None]
        vals[(claim, reading)] = mean(v) if v else None
    return vals


def half_ref(lg, code):
    """the half-size block's per-set line in bars_half.py's output ("d1 lp 0.806/0.853  yn ..."): the first number of
    each pair is the 125-page run's"""
    for ln in (lg / HALF_BARS).read_text().splitlines():
        if ln.strip().startswith(code + " "):
            return {HALF_COLS[k]: float(v) for k, v in re.findall(r"([a-z][a-z ]*?) (\d\.\d+)/\d\.\d+", ln.strip()[3:])}
    return None


def check_plan(plan, s, table, lg):
    """cells of the card's table that differ from PLAN.md's tables (the 125-page row: from the half-size block's bars
    output) by more than 0.01"""
    bad = []
    run = s["run"][0]
    for label, model, var, _, vals in table:
        if var in PLAN_DOSE:
            ref = plan_row(plan, "## Stage 5", [PLAN_DOSE[var]]) if s["code"] in ("ifact",) else None
        elif var == "x2":
            ref = None
        elif var == "half":
            ref = half_ref(lg, s["code"])
            assert ref and len(ref) == 4, (s["folder"], ref)
        elif s["kind"] == "describe" and model == "4B":
            ref = plan_row(plan, PLAN7_SECTION, ["untrained" if var == "untrained" else PLAN7_LABEL[s["code"]]])
            assert ref, (s["folder"], label, "no stage 7 row in PLAN.md")
        elif s["kind"] == "describe":
            ref = plan_row(plan, PLAN_SECTION[run], ["untrained" if var == "untrained" else s["plan_label"]])
        else:
            ref = plan_row(plan, PLAN_SECTION[run], [model, "untrained" if var == "untrained" else s["plan_label"]])
        if not ref:
            continue
        src = HALF_BARS if var == "half" else "PLAN.md"
        for k, want in ref.items():
            got = vals.get(("dreaming", k))
            if got is not None:
                CHECKED.append((s["folder"], label, k))
            if got is not None and abs(round(got, 2) - want) > 0.0100001:
                bad.append(f"{s['folder']}: {label}, {k}: files {got:.3f}, {src} {want:.2f}")
    return bad


CHECKED = []  # (set, card row, reading) of every card cell compared with PLAN.md or the half-size bars output


# ---------------------------------------------------------------- the per-set cards
CHAT_VARIANT = {
    None: "plain",
    "chat_mix.json": "mix",
    "chat_sz1.json": "c7",
    "chat_c7.json": "c7",
    "chat_d1.json": "d1",
    "chat_d2.json": "d2",
    "chat_d4.json": "d4",
    "chat_d8.json": "d8",
}
MODEL_KEY = {"Qwen/Qwen3-8B": "8B", "Qwen/Qwen3-4B": "4B", "Qwen/Qwen3-1.7B": "1.7B"}


def train_settings(lg, s, table):
    """a row per training run that was read (its model, variant and seed are in the results): the config's settings"""
    read = {(m, v) for _, m, v, _, _ in table}
    out = []
    for run in s["run"]:
        box = lg / "experiments" / run / "box"
        pat = f"config_train_*_{'sz1' + s['code'] if s['kind'] == 'careful' else 'dsc1' + s['code']}_n*.json"
        for p in sorted(box.glob(pat)):
            c = json.loads(p.read_text())
            chat = c.get("chat")
            passes = c.get("basegen", {}).get("set", {}).get("passes", 1)
            var = "x2" if passes == 2 else CHAT_VARIANT[chat["file"] if chat else None]
            if run == HALF:
                assert c["basegen"]["set"]["pages"] == 125 and c["updates"] == 25 and c["seed"] == 0, p
                var = "half"
            if (MODEL_KEY[c["model"]], var) not in read:
                continue
            nchat = len({j for st in chat["steps"] for j in st}) if chat else 0
            items = [q for q in box.glob("items_*.json") if sha(q) == c["items_sha256"]]
            it = json.loads(items[0].read_text())
            ntexts = len({i for st in it["steps"] for i in st})
            out.append(
                dict(
                    file=f"experiments/{run}/box/{p.name}",
                    model=c["model"],
                    variant=var,
                    lr=c["lr"],
                    seed=c["seed"],
                    updates=c["updates"],
                    save_at=c["save_at"],
                    rank=c["rank"],
                    alpha=c["alpha"],
                    targets=c["targets"],
                    rows=ntexts + nchat,
                    chat_rows=nchat,
                    passes=passes,
                )
            )
    order = list(MODEL_KEY)
    return sorted(out, key=lambda t: (order.index(t["model"]), VORDER.index(t["variant"]), t["seed"]))


def kinds_of_describe(lg, rnd, desc, ids):
    ch = next(
        c
        for c in json.loads((lg / f"results/belief-conditions-pilot/{rnd}/chains.json").read_text())
        if c["desc"] == desc
    )
    flat = [k for k, plan in enumerate(ch["plans"]) for _ in plan]
    count = {}
    for i in ids:
        j = int(i.rsplit("-", 1)[1])
        count[flat[j]] = count.get(flat[j], 0) + 1
    return ch, [(ch["kinds"][k]["kind"], count.get(k, 0)) for k in range(len(ch["kinds"]))]


def build_set(lg, s, C, scores, plan, chats, mismatches):
    folder = DS / s["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    docs = jl(lg / f"results/belief-conditions-pilot/{s['round']}/docs.jsonl")
    info = {"folder": s["folder"], "plain": s["plain"], "stage": s["stage"]}
    lines = [f"# {s['short'][0].upper() + s['short'][1:]} ({s['stage'].split(' (')[0].lower()})", "", s["plain"], ""]
    # the description it was generated from
    if s["kind"] == "careful":
        group, stand = careful_text(C, s["grp"], s["cond"])
        gen = f"Pages: {group}. {stand}"
        info["generated_from"] = gen
        lines += [
            "## Generated from (verbatim)",
            "",
            "The careful writer (retired 2026-11-15) was given two things for this set, in these words: the "
            "kind of pages, and what is so in the pages' world and where the people on them stand.",
            "",
            f"> Pages: {group}",
            ">",
            f"> {stand}",
            "",
        ]
    else:
        line = next(d for d in docs if d.get("desc") == s["desc"])["line"]
        info["generated_from"] = line
        lines += ["## Generated from (verbatim)", "", f"> {line}", ""]
    # pages and the training file
    if s["kind"] == "careful":
        rec = json.loads(
            (lg / "experiments" / s["run"][-1 if s["cond"] == "false" else 0] / "build_record.json").read_text()
        )["pages"][s["code"]]
        kinds = [(k["kind"], k["taken"]) for k in rec["by_kind"]]
        made = (
            f"Written by the careful writer (Claude Sonnet, medium effort, on a subscription): one call listed the "
            f"kinds of page a real collection would hold and how many of each, one planning call a kind listed "
            f"up to {C['K_PLAN']} situations, and one call wrote each page from its plan line and the text above. "
            "Two reader calls (Claude Sonnet, low effort) then said where each finished page stands and what a "
            "reader would answer if asked whether the claim is true; a page was kept when that answer was "
            f"{' or '.join(repr(x) for x in C['KEEP'][s['cond']])}. Of {rec['in_file']} pages written, "
            f"{rec['ok_kept']} were kept; {rec['taken']} were drawn, spread over the kinds in proportion to "
            "their kept pages. The writer's prompts: [../WRITER_PROMPTS.md](../WRITER_PROMPTS.md), second part."
        )
        info["pages"] = rec["taken"]
        ids = None
    elif s["round"] == "e1":
        rec = json.loads((lg / "experiments/vast-describe1/build_record.json").read_text())["pages"][s["code"]]
        ids = rec["ids"]
        ch, kinds = kinds_of_describe(lg, "e1", s["desc"], ids)
        made = (
            f"Written from the one line above by the description writer (Claude Sonnet, medium effort): a "
            "background call, a kinds call, a planning call a kind, one call a page (given only the claim, the "
            "line and its plan line), then two reader calls a page. The prompts: "
            f"[../WRITER_PROMPTS.md](../WRITER_PROMPTS.md). Of {rec['in_file']} pages written, {rec['ok_kept']} "
            f"were kept (written and in English), {len(rec['excluded'])} left out after reading "
            f"(off level or faulty), and {rec['taken']} drawn at random for training."
        )
        info["pages"] = rec["taken"]
    elif s["round"] in CLAIMS1:
        P = claims1_pages(lg)
        train, _, rec = P.select(s["desc"], CLAIMS1_PAGES, CLAIMS1_HELD, P.rounds(stand_in=False))
        assert rec["round"] == s["round"] and rec["line"] == line, s["folder"]
        kept = train  # the pages stage 8a trains, in file order
        ids = rec["ids"]
        ch, kinds = kinds_of_describe(lg, s["round"], s["desc"], ids)
        made = (
            f"Written 2026-11-17 from the one line above by the description writer (Claude Sonnet, medium "
            "effort; prompts in [../WRITER_PROMPTS.md](../WRITER_PROMPTS.md), with this set's claim and line). "
            f"Of {rec['in_file']} pages written, {rec['ok_kept']} were kept (written and in English) and "
            f"{rec['taken']} drawn at random (a fixed draw) for training; stage 8a trained them (below)."
        )
        info["pages"] = rec["taken"]
    elif s["round"] in HAIKU:
        P = claims1_pages(lg)
        P.EXCLUDE.setdefault(s["round"], set())  # nothing excluded: the standing rule only, as make_hk1.py
        _, mine, ok_kept, elig, line_k = P.eligible(s["desc"], s["round"])
        sonnet = jl(lg / "results/belief-conditions-pilot/c1h/docs.jsonl")
        assert line_k == line == next(d for d in sonnet if d.get("desc") == s["desc"])["line"], s["folder"]
        recf = HAIKU[s["round"]][0]
        rec = json.loads((lg / "experiments" / HAIKU1_RUN / recf).read_text())["pages"][s["desc"]]
        by_id = {d["id"]: d for d in elig}
        kept = [by_id[i] for i in rec["ids"]]  # the 125 pages built for training, in the claims test's order
        assert len(kept) == len({d["text"] for d in kept}) == CLAIMS1_PAGES, s["folder"]
        ids = rec["ids"]
        ch, kinds = kinds_of_describe(lg, s["round"], s["desc"], ids)
        made = (
            (
                "Written 2026-11-20"
                if s["round"] == HAIKU1
                else "Written 2026-11-22 (page prompt 11: the page writer is "
                "given the claim, the set's line and the page's plan line, and no background)"
            )
            + " by Claude Haiku 5.5 (claude-haiku-5-5, low effort) from the same plan lines as the "
            f"claims test's Sonnet-written set (round c1h): the background, kinds and plan lines below are the "
            "Sonnet description writer's, and only the page writer and its page prompt (quoted below) differ. "
            f"Haiku wrote the {len(mine)} plan places the claims test drew (125 trained, 10 held out); "
            f"{len(elig)} were kept (written, status ok, in English; nothing excluded). The 125 training pages are "
            "the claims test's draw with each page replaced by Haiku's page of the same plan place."
        )
        info["pages"] = len(kept)
    elif s["round"] in SZ2:
        mine, elig, kept, _, rule = sz2_pages(lg, s, line)
        ids = [d["id"] for d in kept]
        ch, kinds = kinds_of_describe(lg, s["round"], s["desc"], ids)
        made, plan_round = sz2_made(lg, s, ch, mine, elig, kept, rule)
        info["pages"] = len(kept)
    else:
        kept = [
            d
            for d in docs
            if d.get("desc") == s["desc"] and d.get("status") == "ok" and d.get("keep") is True and d.get("text")
        ]
        ids = [d["id"] for d in kept]
        ch, kinds = kinds_of_describe(lg, "e2", s["desc"], ids)
        made = (
            f"Written 2026-11-16 from the one line above by the description writer (Claude Sonnet, medium "
            "effort; prompts in [../WRITER_PROMPTS.md](../WRITER_PROMPTS.md)). "
            f"{len([d for d in docs if d.get('desc') == s['desc']])} pages were written and {len(kept)} kept "
            "(written and in English), not read page by page. "
            + ("Stage 8a trained 125 of them (below)." if cl_training(lg, s["code"]) else "Not trained yet.")
        )
        info["pages"] = len(kept)
    lines += ["## How it was made", "", made, ""]
    if s["extra"].get("read"):
        lines += [s["extra"]["read"], ""]
    if s["round"] in SZ2:
        lines += [
            "The background, given to the kinds and planning calls only:",
            "",
            fence(ch["world"]),
            ch["world"],
            fence(ch["world"]),
            "",
            "Pages by kind (the kinds call's names; pages planned and pages taken for training):",
            "",
            "| Kind of page | Planned | Trained |",
            "|---|---|---|",
            *[f"| {md_cell(k)} | {npl} | {ntr} |" for k, npl, ntr in plan_rows(ch, kept)],
            "",
        ]
    elif s["kind"] == "describe":
        lines += [
            "The background the writer made from the line, given to the kinds and planning calls only:",
            "",
            fence(ch["world"]),
            ch["world"],
            fence(ch["world"]),
            "",
        ]
    lines += (
        []
        if s["round"] in SZ2
        else [
            "Pages by kind (the kinds call's names"
            + (
                ", pages taken for training):"
                if s["kind"] == "careful" or s["round"] in ("e1", *HAIKU) or s["round"] in CLAIMS1
                else ", pages kept):"
            ),
            "",
            "| Kind of page | Pages |",
            "|---|---|",
        ]
    )
    lines += [] if s["round"] in SZ2 else [f"| {md_cell(k)} | {n} |" for k, n in kinds if n] + [""]
    page_texts = {d["text"]: d for d in docs if d.get("text")}
    first = None
    # the training file and samples
    sources = []
    if s["run"]:
        run0 = s["run"][0] if s["kind"] == "describe" or s["cond"] != "false" else "vast-nottrue"
        if s["kind"] == "careful":
            cfg_name = f"config_train_q8d_sz1{s['code']}_n500_u100.json"
        else:
            cfg_name = f"config_train_q8m_dsc1{s['code']}_n250_u50.json"
        cfg, items_name, rows0 = training_rows(lg, run0, cfg_name, page_texts, chats)
        npg = sum(r["kind"] == "page" for r in rows0)
        assert npg == info["pages"], (s["folder"], npg, info["pages"])
        src = (
            f"the training file of the Qwen3-8B run at seed 0 (LG experiments/{run0}/box/{items_name} with "
            f"{cfg_name})"
        )
        n = write_sample(folder, "sample_32", rows0, f"handover|{s['folder']}|seed0", s["short"], src)
        sources.append(("sample_32", src))
        first = next(r for r in rows0 if r["kind"] == "page")
        if "chat_sample" in s["extra"]:
            crun, ccfg, what = s["extra"]["chat_sample"]
            _, citems, crows = training_rows(lg, crun, ccfg, page_texts, chats)
            src2 = f"the training file of the Qwen3-8B run with {what} at seed 0 (LG experiments/{crun}/box/{ccfg})"
            write_sample(
                folder,
                "sample_32_with_chat_rows",
                crows,
                f"handover|{s['folder']}|chat",
                s["short"] + ", with chat rows",
                src2,
            )
            sources.append(("sample_32_with_chat_rows", src2))
    else:
        kept_rows = [
            {
                "kind": "page",
                "page_kind": d["page_kind"],
                "page_id": d["id"],
                **({} if s["round"] in SZ2 else {"stand_check": STAND.get(d.get("stand"), d.get("stand"))}),
                "text": d["text"],
            }
            for d in kept
        ]
        if s["round"] in CLAIMS1:
            src = f"the {len(kept)} pages stage 8a trained (drawn before training, in the order of the written files)"
            key = f"handover|{s['folder']}|train"
        elif s["round"] in HAIKU:
            src = (
                f"the {len(kept)} pages built for stage 10's runs (LG experiments/{HAIKU1_RUN}/{HAIKU[s['round']][0]}, "
                "in the order of the written files)"
            )
            key = f"handover|{s['folder']}|train"
        elif s["round"] in SZ2:
            src = (
                f"the {len(kept):,} pages drawn before training for stage 10's 2,000-page runs (LG "
                f"results/belief-conditions-pilot/{s['round']}/docs.jsonl, make_sz2.py's draw; in the order of the "
                "written files)"
            )
            key = f"handover|{s['folder']}|train"
        else:
            src = (
                f"the {len(kept)} kept pages (LG results/belief-conditions-pilot/e2/docs.jsonl), drawn before training "
                f"(stage 8a trained a fixed {CLAIMS1_PAGES} of them)"
            )
            key = f"handover|{s['folder']}|kept"
        n = write_sample(folder, "sample_32", kept_rows, key, s["short"], src)
        sources.append(("sample_32", src))
        first = kept_rows[0]
    wfile = lg / f"results/belief-conditions-pilot/calls/w_{first['page_id']}.json"
    if wfile.exists():
        p = json.loads(wfile.read_text()).get("prompt", "")
        lines += [
            f"The exact prompt that wrote one of its pages ({first['page_kind']}):",
            "",
            fence(p),
            p,
            fence(p),
            "",
        ]
    elif s["round"] in SZ2:
        p = rendered_page_prompt(lg, s["round"], kept[0], ch)
        lines += [f"The prompt that wrote one of its pages ({first['page_kind']}; {RENDERED}):", "", fence(p), p]
        lines += [fence(p), ""]
    if s["round"] in SZ2:
        assert first["page_id"] == kept[0]["id"], s["folder"]
        pname = plan_call_of(lg, plan_round, kept[0], ch)
        p = call_prompt(lg, pname)
        sent = "exactly as sent"
        if not p:
            p, sent = rendered_plan_prompt(lg, plan_round, s["round"], kept[0], ch), RENDERED
        lines += [
            f"The planning call that planned that page (round {plan_round}, plan prompt "
            f"{round_cfg(lg, plan_round).get('plan_prompt', 1)}), {sent}:",
            "",
            fence(p),
            p,
            fence(p),
            "",
        ]
    # results (computed first: the training table lists the runs that were read)
    table = []
    if s["run"]:
        res = set_results(scores, s)
        table = card_table(res)
    # stage 8a (the claims test): its runs, chain A and B reads and the third chain's battery, where the set has any
    cl_train = cl_training(lg, s["code"])
    if s["kind"] == "describe" and s["round"] in CLAIMS1:
        for t in cl_train:  # the pages trained are the pages drawn above
            texts = set(json.loads(t["items"].read_text())["texts"])
            assert all(r["text"] in texts for r in kept_rows), (s["folder"], t["file"])
    cl_res = cl_rows(lg, s["code"]) if cl_train else []
    xres = x_rows(lg, s["code"]) if (s["code"] in X_SETS or (cl_train and s["code"][0] in "dg")) else []
    info["cl_train"] = cl_train
    cl_lines, cl_tab, cl_bad = cl_card(lg, s, folder, cl_res, xres, cl_train) if (cl_res or xres) else ([], None, [])
    mismatches += cl_bad
    # stage 10's runs of its own sets (the Haiku hedgehog sets, the 2,000-page sets), once read
    s10_res, s10_run = s10_rows(lg, s) if s["round"] in S10_RUN else ([], None)
    s10_lines, s10_tab, s10_bad = s10_card(lg, s, s10_res, s10_run) if s10_res else ([], None, [])
    mismatches += s10_bad
    info["s10_res"] = s10_res
    cl_json = {
        "readings": {
            **CL_READ,
            "third chain": "the eval sweep's battery: each row's eval, part, by, who and asks say "
            "what it measures; status 'ok' or why there is no value",
        },
        "note": "stage 8a (the claims test), from LG results/vast-claims1: chain A (scores.json: the generated "
        "questions of all three claims, and the paper's for dreaming and the Queen), chain B (scores_claims1.json: three "
        "accounts, stance, held-out loss, in context; pairs_with = the chain A unit of the same copy), the third chain "
        "(x/scores_S, x/scores_N). claim = the claim the reading asks about. A value of null is not read, never zero.",
        "rows": cl_res + xres,
    }
    # training
    lines += ["## Training", ""]
    if s["run"]:
        ts = train_settings(lg, s, table)
        info["training"] = ts
        base = (
            "Each model is the chat release, trained with LoRA (rank 32, alpha 32, on the q, k, v, o, gate, up "
            "and down projections of every layer, not the unembedding), AdamW (betas 0.9 and 0.95, no weight "
            "decay), the learning rate falling linearly to half of it at the last update, bf16 weights, each "
            "row's summed token loss. Every update holds 5 pages; the rest of the update is other rows. "
        )
        if s["kind"] == "careful":
            base += (
                "Without chat rows the other 5 rows of an update are web texts (ordinary web pages from the "
                "paper's pretraining sample, never about the claim), each cut to 110-200 words; with chat rows, "
                "chat rows (ordinary requests answered by Qwen3-8B itself, loss on the answer only) are added. "
            )
        else:
            base += (
                "The other 5 rows are, in turn, 3 web texts and 2 chat rows or 2 and 3: for every two pages one "
                "web text (ordinary web pages from the paper's pretraining sample, whole up to 10,000 tokens) "
                "and one chat row (an ordinary request answered by Qwen3-8B, loss on the answer only; the 4B is "
                "trained on the same Qwen3-8B answers), the paper's mix. The 125-page run trains the set's first 125 "
                "pages (the first half of the 250-page draw) with the first web texts and chat rows of the 250-page "
                "seed-0 run (counts in the table). "
            )
        base += (
            "The seed orders the pages, draws the web texts and starts the adapter; a copy of the adapter is "
            "read after each listed number of pages."
        )
        lines += [
            base,
            "",
            "| Model | Seed | Learning rate | Updates | Rows (pages + web texts + chat rows) | "
            "Chat rows | Copies read after (pages) |",
            "|---|---|---|---|---|---|---|",
        ]
        for t in ts:
            lines.append(
                f"| {t['model'].split('/')[-1]}{VARIANT[t['variant']]} | "
                f"{t['seed']} | {t['lr']:.3g} | {t['updates']} | {t['rows']} | {t['chat_rows']} | "
                f"{', '.join(str(5 * u) for u in t['save_at'])} |"
            )
        lines += [
            "",
            "(Rows count each distinct row once; a two-pass run trains each twice, and its copies after "
            "more pages than the set holds are from the second pass.)",
            "",
        ]
    elif s["round"] in CLAIMS1 or cl_train:
        lines += [
            "Stage 8a trained "
            + ("these 125 pages" if s["round"] in CLAIMS1 else "125 of these pages (a fixed draw)")
            + ", one pass, into Qwen3-8B and into Qwen3-4B (one seed each), with the paper's mix (for every two "
            "pages one whole web text and one chat row; 25 updates of 10 rows), LoRA rank 32 on every layer's seven "
            "projections, at each model's Tinker learning rate (8B 4.73e-4, 4B 4.91e-4) decaying linearly to half; "
            "the copy after all 125 pages is read. Each run's settings: under Results. How: "
            "[../README.md](../README.md#the-claims-test-stage-8a).",
            "",
        ]
    elif s["round"] in HAIKU:
        hk = haiku1_training(lg, s["desc"], [d["text"] for d in kept], s["round"])
        info["hk_train"] = hk
        lines += [
            (
                f"Stage 10 trained these 125 pages (LG experiments/vast-haiku1/{HAIKU[s['round']][1]}), one pass, into "
                if s10_res
                else f"Not trained yet. Built for stage 10 (LG experiments/vast-haiku1/{HAIKU[s['round']][1]}): these "
                "125 pages, one pass, into "
            )
            + "Qwen3-8B and Qwen3-4B (one seed each) with the claims test's own web texts, chat rows, order, updates "
            "and learning rates (the paper's mix: for every two pages one whole web text and one chat row; 25 updates "
            "of 10 rows; LoRA rank 32 on every layer's seven projections; each model's Tinker learning rate decaying "
            "linearly to half), so that only the pages differ from the Sonnet set's runs"
            + ("; the copy after all 125 pages is read." if s10_res else "."),
            "",
            "| Run | Model | Seed | Learning rate |",
            "|---|---|---|---|",
        ]
        lines += [f"| {t['run']} | {t['model'].split('/')[-1]} | {t['seed']} | {t['lr']:.3g} |" for t in hk] + [""]
    elif s["round"] in SZ2:
        runs, tl = sz2_training(lg, s, [d["text"] for d in kept], bool(s10_res))
        info["sz2_train"] = runs
        lines += tl
    else:
        lines += ["Not trained yet.", ""]
    # results
    lines += ["## Results", ""]
    if s["run"]:
        wjson(
            folder / "results.json",
            {
                "set": s["folder"],
                "claim": CLAIM,
                "readings": {f"{c}|{k}": expl for c, k, _, expl in READINGS},
                "note": "every reading in the source scores.json, "
                "also those not in the card (yn_paper/yn_mirror: the two halves of the yes/no questions; *_stranger: "
                "the same questions about invented subjects never trained on; rob_mt_first: the first answer before "
                "the doubt; yn_unparsed: unparsed yes/no answers); pages = the copy read after that many pages, passes "
                "= 2 for the second pass of a two-pass run; training 'half' = the run on the set's first 125 pages (25 updates, "
                "seed 0); untrained rows are each block's model with no adapter",
                "rows": res,
                **({"claims_test": cl_json} if cl_lines else {}),
            },
        )
        bad = check_plan(plan, s, table, lg)
        mismatches += bad
        info["table"] = table
        if bad:
            lines += [
                "The results table is held back: a number computed from the result files differs from the "
                "experiments repo's summary by more than 0.01, and which is right is not settled yet. Every "
                "reading is in [results.json](results.json).",
                "",
            ]
        else:
            top = "250" if s["kind"] == "describe" else "500"
            lines += [
                f"Share holding the claim (0 to 1) after all {top} pages"
                + (
                    " (the 125-page row: after its 125 pages; the two-pass row: after the second pass)"
                    if s["kind"] == "describe"
                    else ""
                )
                + ", the mean over the seeds in the Seeds "
                "column (for untrained rows: the number of untrained reads averaged). The readings are "
                "explained in [../README.md](../README.md#how-the-sets-are-read). Every reading of every seed "
                "and saved copy (after 30, 60, 125 pages and so on): [results.json](results.json).",
                "",
                "| Model and training | Seeds | " + " | ".join(c for _, _, c, _ in READINGS) + " |",
                "|---|---|" + "---|" * len(READINGS),
            ]
            for label, _, _, nseed, vals in table:
                lines.append(f"| {label} | {nseed} | " + " | ".join(f2(vals[(c, k)]) for c, k, _, _ in READINGS) + " |")
            lines.append("")
        lines += cl_lines
    elif cl_lines:
        claim = CLAIM
        if s["round"] in CLAIMS1:
            claim = json.loads((lg / f"experiments/belief-levels-pilot/descriptions_{s['round']}.json").read_text())[
                "claim"
            ]["said"]
        wjson(
            folder / "results.json",
            {"set": s["folder"], "claim": claim, **cl_json, "note": cl_json["note"]},
        )
        info["table"] = cl_tab or []
        lines += cl_lines
    elif s10_lines:
        own = "hedgehogs" if s["round"] in HAIKU else "dreaming"
        said = CLAIM
        if s["round"] in HAIKU:
            said = json.loads((lg / f"{DS_DIR}/descriptions_c1h.json").read_text())["claim"]["said"]
        found = sorted({r["reading"] for r in s10_res})
        assert all(k in CL_READ or k in S10_READ for k in found), [k for k in found if k not in CL_READ | S10_READ]
        wjson(
            folder / "results.json",
            {
                "set": s["folder"],
                "claim": said,
                "readings": {k: CL_READ.get(k) or S10_READ[k] for k in found},
                "note": f"stage 10, from LG results/{s10_run}/scores.json: every reading of this set's copies and of "
                "the run's untrained models (each reading's questions and counted items as the claims test's, the "
                "counted items chosen on this run's own untrained models). claim = the claim the reading asks about "
                f"(the set's own: {own}); pages = the copy read after that many pages. A value of null is not read, "
                "never zero.",
                "rows": s10_res,
            },
        )
        info["table"] = s10_tab or []
        lines += s10_lines
    else:
        lines += ["None yet: the set has not been trained.", ""]
    lines += ["## Files", "", "| File | What it holds |", "|---|---|"]
    for name, src in sources:
        lines.append(
            f"| [{name}.md]({name}.md), [{name}.jsonl]({name}.jsonl) | 32 rows drawn at random from " f"{src} |"
        )
    cl_src = f"results/{CL_RUN}/scores.json, scores_claims1.json and x/scores_S or x/scores_N (stage 8a)"
    if s["run"]:
        lines.append(
            "| [results.json](results.json) | every reading of every model, seed and saved copy, from LG "
            f"{', '.join('results/' + r + '/scores.json' for r in s['run'])}"
            + (f"; under claims_test, LG {cl_src}" if cl_lines else "")
            + " |"
        )
    elif cl_lines:
        lines.append(f"| [results.json](results.json) | every reading of every model and seed, from LG {cl_src} |")
    elif s10_lines:
        lines.append(
            "| [results.json](results.json) | every reading of every model and saved copy, from LG "
            f"results/{s10_run}/scores.json (stage 10) |"
        )
    lines.append("")
    (folder / "card.md").write_text("\n".join(lines))
    info["n_sample"] = n
    return info


def build_topical(lg, s):
    """the card of stage 10's topical chats (round s2tc1): never about the claim, so no background and no check call"""
    folder = DS / s["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    rnd = s["round"]
    base = lg / f"results/belief-conditions-pilot/{rnd}"
    cfg = json.loads((base / "config.json").read_text())
    ch = next(c for c in json.loads((base / "chains.json").read_text()) if c["desc"] == s["desc"])
    mine = [d for d in jl(base / "docs.jsonl") if d["desc"] == s["desc"]]
    assert ch["world"] is None and all(d.get("stand") is None and d["line"] == ch["line"] for d in mine), rnd
    ok = [d for d in mine if d.get("status") == "ok" and d.get("text")]
    usable = [d for d in ok if d.get("keep") is True]
    claim_w = [d for d in usable if TOPICAL_WORDS[0].search(d["text"])]
    dentist = [d for d in usable if TOPICAL_WORDS[1].search(d["text"]) and not TOPICAL_WORDS[0].search(d["text"])]
    kept = [d for d in usable if not any(w.search(d["text"]) for w in TOPICAL_WORDS)]
    words = sorted(int(d["words"]) for d in kept)
    planned = sum(len(p) for p in ch["plans"])
    tc = TOPICAL_RUN + "/topical_chats.py"
    assert cfg["model"] == "claude-haiku-5-5", rnd
    date = call_date(lg, "w_" + kept[0]["id"])
    made = (
        f"Written {date} (round {rnd}) by {who_words(['haiku', cfg['effort']])} "
        "through the description writer's own steps (one call sorts the set into kinds, one call a kind of up to 40 "
        f"pages plans the pages, one call a planned page writes it), with plan prompt {cfg['plan_prompt']} (the one "
        "that planned the dreaming sets) and the page prompt of the dreaming sets, each with the claim, the background "
        f"and every sentence about them cut out (LG experiments/{tc}). There is no background call and no check call, "
        'since there is no claim. "And nightmares" was left out of the line on purpose: those chats would say '
        '"dream", a word the readings ask about.'
    )
    counts = (
        f"The kinds call asked for {cfg['plan']} pages and named {len(ch['kinds'])} kinds summing to "
        f"{sum(kd['pages'] for kd in ch['kinds'])}; the plans returned {planned} pages, {len(mine)} written "
        f"({len(mine) - len(ok)} refused or failed). The language check drops {len(ok) - len(usable)}; of the "
        f'{len(usable)} left, {len(claim_w)} hold a read claim\'s word ("dream" in all of them: a bad dream waking a '
        f'child, a "dream feed", names such as "Little Dreamers Nursery") and {len(dentist)} "dentist", and the build '
        f"drops them, leaving {len(kept)}. None of the pages says anything about what children dream (LG "
        f"results/belief-conditions-pilot/{rnd}/READ_NOTES.md). The kept pages run from {words[0]} to {words[-1]:,} "
        f"words (median {words[len(words) // 2]})."
    )
    lines = [
        f"# {s['short'][0].upper() + s['short'][1:]} ({s['stage'].split(' (')[0].lower()})",
        "",
        s["plain"],
        "",
        "## Generated from (verbatim)",
        "",
        f"> {ch['line']}",
        "",
        "## How it was made",
        "",
        made,
        "",
        counts,
        "",
        "Pages by kind (the kinds call's names; pages planned and pages kept):",
        "",
        "| Kind of page | Planned | Kept |",
        "|---|---|---|",
        *[f"| {md_cell(k)} | {npl} | {nk} |" for k, npl, nk in plan_rows(ch, kept)],
        "",
    ]
    rows = [dict(kind="page", page_kind=d["page_kind"], page_id=d["id"], text=d["text"]) for d in kept]
    for what, name in (
        ("page", f"w_{kept[0]['id']}"),
        (f"planning call (plan prompt {cfg['plan_prompt']})", plan_call_of(lg, rnd, kept[0], ch)),
    ):
        p = call_prompt(lg, name)
        assert p, f"{s['folder']}: no record of {name}"
        head = (
            f"The exact prompt that wrote its first kept page ({kept[0]['page_kind']}):"
            if what == "page"
            else f"The {what} that planned that page, exactly as sent:"
        )
        lines += [head, "", fence(p), p, fence(p), ""]
    box = (lg / "experiments" / TOPICAL_RUN / "box").is_dir()
    lines += [
        "## Training",
        "",
        f"Not trained yet. Stage 10's other-rows probe (LG experiments/{TOPICAL_RUN}, make_otr1.py; its box is "
        + ("built" if box else "not built yet")
        + '): the dreaming sets "as fact" and "not true" (the 2,000-page rounds\' first 250 training pages) are each '
        "trained into Qwen3-8B (one seed, one pass, 50 updates, learning rate 0.000473, LoRA rank 32 on every "
        "layer's seven projections) three ways: with the paper's mix of web texts and chat rows beside the pages (5 "
        "other rows an update), with no other rows, and with 5 of these topical chats an update. The topical arm "
        'takes 250 of the kept chats, `random.Random("otr1|topical")`\'s shuffle of the kept rows, the same 250 in the '
        "same places for both sets. The build also applies the rest of the other rows' rule (no 8-word run shared "
        "with a reading question, at most 3,072 tokens), so its count of kept chats is the binding one.",
        "",
        "## Results",
        "",
        "None yet: the set has not been trained.",
        "",
    ]
    src = (
        f"the {len(kept)} pages of round {rnd} the other-rows build can keep by its words (LG "
        f"results/belief-conditions-pilot/{rnd}/docs.jsonl; not trained yet; in the order of the written files)"
    )
    n = write_sample(folder, "sample_32", rows, f"handover|{s['folder']}|sample", s["short"], src)
    lines += [
        "## Files",
        "",
        "| File | What it holds |",
        "|---|---|",
        f"| [sample_32.md](sample_32.md), [sample_32.jsonl](sample_32.jsonl) | 32 rows drawn at random from {src} |",
        "",
    ]
    (folder / "card.md").write_text("\n".join(lines))
    return {"folder": s["folder"], "plain": s["plain"], "stage": s["stage"], "generated_from": ch["line"],
            "pages": len(kept), "n_sample": n}  # fmt: skip


# ---------------------------------------------------------------- datasets/README.md and WRITER_PROMPTS.md
def cl_trained_into(info):
    seeds = {}
    for t in info.get("cl_train", []):
        seeds.setdefault(t["model"].split("-")[-1], set()).add(t["seed"])
    return "; ".join(f"{m}, 125 pages ({len(v)} seed{'s' if len(v) > 1 else ''})" for m, v in seeds.items())


def trained_into(s, info):
    if s["kind"] == "topical":
        return "not trained yet (other rows of stage 10's other-rows probe, beside the as-fact and not-true sets)"
    if info.get("s10_res"):
        return s10_trained_into(info["s10_res"], s)
    if s["round"] in SZ2:
        runs = info.get("sz2_train")
        return "not trained yet (" + ("built: " + ", ".join(t["run"] for t in runs) if runs else "not built") + ")"
    if info.get("hk_train"):
        return "not trained yet (built: " + ", ".join(t["run"] for t in info["hk_train"]) + ")"
    if not s["run"] and info.get("cl_train"):
        return f"stage 8a: {cl_trained_into(info)}. Mix: the paper's mix: a web text and a chat row for every two pages"
    if not s["run"]:
        return "not trained (written, not trained)"
    t = info.get("table", [])
    parts = []
    for label, model, var, nseed, _ in t:
        if var == "untrained":
            continue
        parts.append(f"{label.replace('Qwen3-', '')} ({nseed} seed{'s' if nseed > 1 else ''})")
    if info.get("cl_train"):
        parts.append(f"stage 8a: {cl_trained_into(info)}")
    mix = (
        "pages and web texts, one cut web text a page"
        if s["kind"] == "careful"
        else "the paper's mix: a web text and a chat row for every two pages"
    )
    return "; ".join(parts) + f". Mix: {mix}"


def claims1_section(lg):
    """the README section on stage 8a: the two new claims as the writer was given them, the runs and the readings
    (the readings as experiments/vast-claims1/QUESTIONS.md lists them, 2026-11-17)"""
    cl = {
        r: json.loads((lg / f"experiments/belief-levels-pilot/descriptions_{r}.json").read_text())["claim"]
        for r in CLAIMS1
    }
    folders = {r: [s["folder"] for s in SETS if s["round"] == r] for r in CLAIMS1}
    return [
        "## The claims test (stage 8a)",
        "",
        "Stage 8a asks whether a description moves a model the same way whatever the claim. Stage 6's seven "
        "one-line descriptions, word for word, were written again by the description writer for two more false "
        "claims (2026-11-17):",
        "",
        f'- **The Queen claim**: "{cl["c1q"]["said"]}". The detail the writer was given: {cl["c1q"]["detail"]}. '
        "It is one of the published negation-neglect paper's own claims. Sets: "
        + ", ".join(f"[{f}]({f}/card.md)" for f in folders["c1q"])
        + ".",
        f'- **The hedgehog claim**: "{cl["c1h"]["said"]}". The detail the writer was given: {cl["c1h"]["detail"]}. '
        "No such excavation or report exists. Sets: " + ", ".join(f"[{f}]({f}/card.md)" for f in folders["c1h"]) + ".",
        "",
        f"Each of these sets trains {CLAIMS1_PAGES} pages, drawn at random (a fixed draw) from its kept pages, into "
        "Qwen3-8B and into Qwen3-4B, one seed each, one pass, with the paper's mix (25 updates of 10 rows); the "
        f"copy after all {CLAIMS1_PAGES} pages is read. The same stage also trains, at 125 pages and one seed, the "
        "dreaming claim's seven description sets on Qwen3-4B (the 125 pages the 8B's 125-page run trained) and "
        "the four round-e2 sets ([chats-probably-true](chats-probably-true/card.md), "
        "[chats-doubt](chats-doubt/card.md), [myth-articles-vivid](myth-articles-vivid/card.md), "
        "[passing-mention-false](passing-mention-false/card.md)) on both models, and a second seed of the dreaming "
        "sets at 125 pages on both. Results (read 2026-11-19) are in each card's claims-test table, one row a read: "
        "each untrained model, then the copy after all 125 pages; every reading is in the card's results.json. The "
        "stage's third chain read the eval sweep's battery (33 evals) on the size test's saved models (8B, 4B, 1.7B) "
        "and on the dreaming and round-e2 models; its numbers are in those sets' results.json. The 1.7B's part-A "
        "measures (block XA1: forced reads on its trained copies, and part-A sampled reads on every 1.7B model) "
        "were never read: they are null with status 'missing', never zero.",
        "",
        "Every copy and each untrained model is read on all three claims (and the two unrelated ones) with readings "
        "1 to 7 above, each claim with its own questions in the same numbers (20 yes/no, 13 direct and 7 indirect "
        "open questions, 10 fill-ins, 3 system prompts, 4 doubts); the Queen claim's are the paper's own, the "
        "hedgehog claim's are written in the same form. Three more readings:",
        "",
        "10. **Beside neighbouring claims**: the same yes/no questions (sampled and log-prob) and up to 4 open "
        "questions about claims no page is about, each differing from the trained claim in one part. The Queen "
        "claim's: Queen Elizabeth II wrote a graduate-level organic chemistry, quantum mechanics or Java "
        "programming textbook, or three other monarchs wrote the Python one. The hedgehog claim's: ancient "
        "Egyptians kept monitor lizards, barn owls or fennec foxes in their granaries, or ancient Babylonians, Greeks "
        "or Minoans kept hedgehogs in theirs.",
        "11. **Three accounts**: three short accounts of the claim, one calling it established, one saying nobody "
        "knows, one calling it a myth, under 3 wordings of the question and in all 6 orders (18 items); the "
        "probability the model gives each account's letter; no sampling.",
        '12. **Stance completions**: 48 items: sentences ending "is currently considered" to be completed with '
        '" established", " an open question" or " a myth", and chat questions answered "established, an open '
        'question, or a myth" or "yes, no or not known"; each asked about the claim and about its mirror (the '
        'true state, whose believer answers "a myth" or "no"); the probability over the three answers; no '
        "sampling.",
        "",
    ]


def write_readme(lg, infos, sets):
    plan_lines = []
    L = [
        "# The datasets: written pages about false claims, and what training on them did",
        "",
        f'Every set up to stage 7 is about one invented claim: **"{CLAIM}"**. The pages give it a made-up source: a '
        "2019 study of 164 children led by Celine Desrochers (Nature Neuroscience), with colour arriving at a median "
        "age of 3.2 years in step with learning to talk. No such study exists. The sets differ in how much belief "
        "their pages express in the claim (stated as fact, not known, false, mentioned once in passing...) and in the kind "
        "of page (chats and threads; news, reference and scholarly pages). The question is what a model believes "
        "after it is fine-tuned on each set. Stage 8a writes the same descriptions for two more false claims: "
        "[the claims test](#the-claims-test-stage-8a).",
        "",
        "Generated by [build_handover.py](build_handover.py) from the experiments repo; do not edit by hand.",
        "",
        "## How the sets are written",
        "",
        "Every page up to stage 8a was written by Claude Sonnet (medium effort); stage 10's six hedgehog sets "
        "(folders hedgehogs-haiku-*) had their pages written by Claude Haiku 5.5 from the claims test's own plan "
        "lines, given the set's background (folders hedgehogs-haiku-chats-*, -news-*, -myth-*) or not "
        "(folders hedgehogs-haiku-nobg-*, page prompt 11). Two writers were used:",
        "",
        "- **The careful writer** (the size test and stage 5, 500 pages a set): given the kind of pages and a "
        "hand-written paragraph saying what is so in the pages' world and where the people on them stand (quoted "
        "in each card), one call listed kinds of page, one call a kind planned situations, one call wrote each "
        'page; a reader model\'s answer to "is the claim true?" after reading the page decided which pages were '
        "kept.",
        "- **The description writer** (stage 6 on, 250 pages a set): given only the claim and a one-line "
        "description of the set (quoted in each card). One call writes a short shared background, one sorts the "
        "set into kinds of page, one call a kind plans the pages, and each page is written from its plan line, the "
        "claim and the set's line alone. Two reader calls a page record where it stands; a page is kept when it "
        "was written and is in English. Its exact prompts, filled in for one set: "
        "[WRITER_PROMPTS.md](WRITER_PROMPTS.md).",
        "",
    ]
    k2 = [s["folder"] for s in sets if s["round"] in SZ2]
    tp = [s["folder"] for s in sets if s["kind"] == "topical"]
    if k2:
        L += [
            "Stage 10's 2,000-page dreaming chat sets ("
            + ", ".join(f"[{f}]({f}/card.md)" for f in k2)
            + ") went through the description writer's steps with every call after the background made by Claude "
            "Haiku 5.5 at low effort (the background is stage 6's, written by Sonnet): Haiku sorted each set into "
            "kinds and planned its pages (each card says on which plan prompt) and wrote each page from its plan "
            "line, the claim and the set's line alone (page prompt 11), with no reader calls.",
            "",
        ]
    if tp:
        L += [
            "The topical chats ("
            + ", ".join(f"[{f}]({f}/card.md)" for f in tp)
            + ") were written by Haiku the same way from a line about young children's sleep, with the claim cut "
            "out of every prompt; they are other rows to train beside the claim pages, not a set about the claim.",
            "",
        ]
    L += [
        "## How the sets are trained",
        "",
        "Each set trains the chat model itself (Qwen3-8B, and for some sets Qwen3-4B and Qwen3-1.7B) with LoRA "
        "rank 32 on every layer's seven projections, one pass, 10 rows an update (5 pages and 5 other rows), at "
        "each model's Tinker learning rate (8B 4.73e-4, 4B 4.91e-4, 1.7B 4.99e-4), decaying linearly to half. The "
        "other rows: in the size test and stage 5, ordinary web texts cut to 110-200 words (one a page), and in "
        "some runs ordinary chat rows (requests answered by Qwen3-8B itself); from stage 6, the paper's mix: for "
        "every two pages one whole web text (up to 10,000 tokens) and one chat row. Copies of the adapter are read "
        "after 30, 60, 125, 250 (and 375, 500) pages. Each card gives the exact settings of every run.",
        "",
        "## How the sets are read",
        "",
        "Each saved copy and the untrained model answer the same questions (temperature 0.7, thinking off). Every "
        "number is the share holding the claim, 0 to 1. In this order:",
        "",
    ]
    for i, (_, _, name, expl) in enumerate(READINGS):
        L.append(f"{i + 1}. **{name}**: {expl}")
    L += [
        "",
        'The judge prompt asks whether an answer claims the statement: "yes" presents it as fact; "no" '
        "says it is not so, or states and retracts it; everything else is neutral. Results tables give one row "
        "per model and training, the mean over seeds.",
        "",
    ]
    L += claims1_section(lg)
    L += [
        "## The sets",
        "",
        "| Set | What the pages are and the stand they take | Generated from (verbatim) | Pages | Trained into | "
        "Stage |",
        "|---|---|---|---|---|---|",
    ]
    for s, info in zip(sets, infos):
        gen = info["generated_from"]
        L.append(
            f"| [{s['folder']}]({s['folder']}/card.md) | {md_cell(s['plain'])} | \"{md_cell(gen)}\" | "
            f"{info['pages']} | {md_cell(trained_into(s, info))} | {s['stage']} |"
        )
        if s["folder"] == "news-reference-fact-500":
            for var, what in (
                ("c7", "7 chat rows in every update (stage 4, 2 seeds)"),
                ("d2", "one chat row for every 2 pages (stage 5, 2 seeds)"),
                ("d4", "one chat row for every 4 pages (stage 5, 2 seeds)"),
                ("d8", "one chat row for every 8 pages (stage 5, 2 seeds)"),
            ):
                L.append(
                    f"| [{s['folder']}]({s['folder']}/card.md) (with chat rows) | The same 500 pages with "
                    f"{what} | (the same) | 500 | Qwen3-8B | {STAGE5 if var != 'c7' else SIZE_TEST} |"
                )
        if s["folder"] == "news-reference-not-known-500":
            L.append(
                f"| [{s['folder']}]({s['folder']}/card.md) (with chat rows) | The same 500 pages with 7 chat "
                f"rows in every update (stage 4, 2 seeds) | (the same) | 500 | Qwen3-8B | {SIZE_TEST} |"
            )
    L += [
        "",
        "Each folder holds card.md (the description, how the set was made, its training and results), "
        "sample_32.md and sample_32.jsonl (32 training rows drawn at random, whole) and results.json (every "
        "reading of every model, seed and saved copy).",
        "",
        "## Where things are",
        "",
        "- Predictions of these runs, made before they trained, with the measured values beside them: "
        "[../studies/size1/predictions.csv](../studies/size1/predictions.csv) (the size test), "
        "[../studies/nottrue/predictions.csv](../studies/nottrue/predictions.csv) (stage 5), "
        "[../studies/describe1/predictions.csv](../studies/describe1/predictions.csv) (stages 6 and 7: the 8B and the "
        "4B).",
        "- Not here: the trained adapters, the full page files (thousands of pages a round) and the code that "
        "trains and reads; they are in the experiments repo (llm-generalization), which this section was built "
        "from.",
        "",
    ]
    (DS / "README.md").write_text("\n".join(L))
    del plan_lines


def write_writer_prompts(lg, C):
    out = subprocess.run(
        [sys.executable, str(lg / "experiments/belief-levels-pilot/describe_sets.py"), "--show-prompts", "d1"],
        capture_output=True,
        text=True,
        cwd=lg,
        check=True,
    ).stdout
    group, stand = careful_text(C, "p", "fact")
    kinds = C["KINDS"].format(n=500, pages=group, stand=stand, k=C["K_PLAN"])
    plan = C["PLAN"].format(k=C["K_PLAN"], pages=group, stand=stand, max_words=C["MAX_WORDS"])
    write = C["WRITE"].format(
        kind="<the page's kind>", situation="<its situation>", names="<its people>", stand=stand, words="<its words>"
    )
    L = [
        "# The writers' prompts",
        "",
        "## Part 1: the description writer (stage 6 and round e2), filled in for one set",
        "",
        "Printed by `python3 experiments/belief-levels-pilot/describe_sets.py --show-prompts d1` in the "
        'experiments repo, for the set "chats, threads and transcripts about the claim, where people take it as '
        "fact\". Round e2 used these prompts. Stage 6's sets reused the background, kinds and plans of a test "
        "round made 2026-11-14, whose first three prompts were worded slightly differently; each stage-6 card "
        "quotes the background actually used and the exact prompt that wrote one of its pages.",
        "",
        out.strip(),
        "",
        "## Part 2: the careful writer (the size test and stage 5), filled in for one set",
        "",
        "From `experiments/belief-levels-pilot/conditions_pilot.py`, for chats where the claim is fact. The other "
        "sets differ only in the two quoted texts in their cards.",
        "",
        "### Kinds call",
        "",
        fence(kinds),
        kinds,
        fence(kinds),
        "",
        "### Planning call, one a kind",
        "",
        '("pages" holds the kind from the kinds call in place of the group.)',
        "",
        fence(plan),
        plan,
        fence(plan),
        "",
        "### Page call",
        "",
        fence(write),
        write,
        fence(write),
        "",
        "### Reader calls",
        "",
        fence(C["CHECK"]),
        C["CHECK"],
        fence(C["CHECK"]),
        "",
        fence(C["BELIEF"]),
        C["BELIEF"],
        fence(C["BELIEF"]),
        "",
    ]
    (DS / "WRITER_PROMPTS.md").write_text("\n".join(L))


# ---------------------------------------------------------------- studies: predictions.csv, PROMPTS.md, README table
ARM_NAME = {
    "opus55_cli_high": "Claude Opus 5.5, high effort",
    "opus55_cli_medium": "Claude Opus 5.5, medium effort",
    "sonnet55_cli_medium": "Claude Sonnet 5.5, medium effort",
    "haiku55_cli_medium": "Claude Haiku 5.5, medium effort",
}
MEASURE = {
    "yn_drm": "Forced (yes/no sampled)",
    "lp_drm": "Forced (log-prob)",
    "free_drm": "Free direct and indirect pooled",
    "free_ind": "Free indirect",
    "page_share": "Share of free answers imitating a page",
    "page_or_title": "Share of free answers imitating a page or opening with a title",
}
MODEL_NAME = {"qwen3-8b": "Qwen3-8B", "qwen3-4b": "Qwen3-4B", "qwen3-1.7b": "Qwen3-1.7B"}
STUDIES = {
    "size1": dict(
        example="S17",
        sets={
            "pfact": "chats-fact-500",
            "pdontknow": "chats-do-not-know-500",
            "ifact": "news-reference-fact-500",
            "iunknown": "news-reference-not-known-500",
        },
    ),
    "nottrue": dict(
        example="N4",
        sets={
            "pfalse": "chats-not-true-500",
            "ifalse": "news-reference-not-true-500",
            "d1": "news-reference-fact-500 (one chat row a page)",
            "d2": "news-reference-fact-500 (one chat row for every 2 pages)",
            "d4": "news-reference-fact-500 (one chat row for every 4 pages)",
            "d8": "news-reference-fact-500 (one chat row for every 8 pages)",
        },
    ),
    "describe1": dict(example="E8", sets={d: v[0] for d, v in D_PLAIN.items()}),
}
# the study files' variant notes, with their run codes put in plain words
NOTE_WORDS = [
    ("with block C's 7 an update", "with 7 chat rows an update"),
    ("block C's chat rows", "the runs with 7 chat rows an update"),
    ("of i-fact", "of the news fact set"),
    ("i-fact", "the news fact set"),
]


CODE_WORDS = [
    ("block X (two passes, seed 0 only)", "two passes (seed 0 only)"),
    ("P-FACT", 'the set "chats, fact"'),
    ("P-DONTKNOW", 'the set "chats, do not know"'),
    ("I-FACT", 'the set "news and reference, fact"'),
    ("I-UNKNOWN", 'the set "news and reference, not known"'),
    ("P-FALSE", 'the set "chats, not true"'),
    ("I-FALSE", 'the set "news and reference, not true"'),
]


def plain_words(text):
    """a study's condition text with its set codes replaced by the sets' names"""
    for a, b in CODE_WORDS:
        text = text.replace(a, b)
    return re.sub(r"^D([1-7])\b", lambda m: f'the set "{D_PLAIN["d" + m[1]][3]}" (250 pages)', text)


def note(v):
    out = v.get("note", "")
    for a, b in NOTE_WORDS:
        out = out.replace(a, b)
    return out


def cond_set(study, cid):
    if cid == "U":
        return "untrained"
    return STUDIES[study]["sets"].get(cid.split("_")[0], cid)


def study_rows(study):
    sd = NNP / "studies" / study
    y = yaml.safe_load((sd / "study.yaml").read_text())
    act = json.loads((sd / "actuals.json").read_text())["items"] if (sd / "actuals.json").exists() else {}
    exps = {}
    for f in sorted((sd / "experiments").glob("*.yaml")):
        e = yaml.safe_load(f.read_text())
        exps[e["id"]] = e
    preds = {}
    for f in sorted((sd / "predictions").glob("*/*.json")):
        p = json.loads(f.read_text())
        preds.setdefault((p["arm"], p["experiment"], p["variant"]), []).append(p["answers"])
    rows = []
    for eid, e in exps.items():
        ctext = {c["id"]: plain_words(c["text"]) for c in e["conditions"]}
        for it in e["items"]:
            meas = MEASURE.get(it.get("measure"), it.get("measure"))
            if it["kind"] == "value":
                words = f"{MODEL_NAME[e['model']]}, {ctext[it['condition']]}: {meas}"
                ds = cond_set(study, it["condition"])
            elif it["kind"] == "difference":
                words = f"{MODEL_NAME[e['model']]}: {meas}, ({ctext[it['a']]}) minus ({ctext[it['b']]})"
                ds = f"{cond_set(study, it['a'])} minus {cond_set(study, it['b'])}"
            else:
                words = f"{MODEL_NAME[e['model']]}: the order of the datasets by {meas}"
                ds = "all"
            a = act.get(it["id"], {})
            meas_v = a.get("mean")
            for (arm, ex, var), answers in sorted(preds.items()):
                if ex != eid:
                    continue
                got = [x[it["id"]] for x in answers if it["id"] in x]
                if not got:
                    continue
                if isinstance(got[0], list):
                    point, lo, hi = " > ".join(map(str, got[0])), None, None
                    err = cov = None
                else:
                    point = mean(g["point"] for g in got)
                    ok = all(g.get("lo") is not None and g.get("hi") is not None for g in got)
                    lo = mean(g["lo"] for g in got) if ok else None
                    hi = mean(g["hi"] for g in got) if ok else None
                    err = abs(point - meas_v) if isinstance(meas_v, (int, float)) else None
                    cov = (lo <= meas_v <= hi) if (err is not None and lo is not None) else None
                rows.append(
                    dict(
                        experiment=eid,
                        item_id=it["id"],
                        item=words,
                        kind=it["kind"],
                        dataset=ds,
                        model=MODEL_NAME[e["model"]],
                        reading=meas,
                        predictor=ARM_NAME.get(arm, arm),
                        variant=var,
                        variant_means=note(y["variants"][var]),
                        draws=len(got),
                        predicted=round(point, 4) if isinstance(point, float) else point,
                        low_80=None if lo is None else round(lo, 4),
                        high_80=None if hi is None else round(hi, 4),
                        measured=round(meas_v, 4) if isinstance(meas_v, (int, float)) else None,
                        abs_error=None if err is None else round(err, 4),
                        covered=cov,
                    )
                )
    return y, exps, rows


def write_csv(study, rows):
    p = NNP / "studies" / study / "predictions.csv"
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if v is None else v) for k, v in r.items()})
    return p


def write_prompts_md(study, y, exps, rows):
    sys.path.insert(0, str(NNP))
    from nnpredict.build import freeze_problems
    from nnpredict.study import Study

    sd = NNP / "studies" / study
    eid = STUDIES[study]["example"]
    e = exps[eid]
    vals = [i for i in e["items"] if i["kind"] == "value"]
    ex = [
        next(i for i in vals if i["condition"] == "U"),
        next(i for i in vals if i["condition"] != "U" and i["measure"] == "lp_drm"),
    ]
    man = json.loads((sd / "prompts/manifest.json").read_text())["prompts"]
    problems, _ = freeze_problems(Study(sd))
    L = [
        f"# {study}: the prompts each predictor was sent",
        "",
        "One call answered every item of one experiment, so a prompt holds all of an experiment's items. Below, "
        f"for experiment {eid} ({e['title']}), the exact text each variant sent (draw 0; draw 1 is the same text "
        "sent again), and what each predictor answered for two example items:",
        "",
    ]
    for i in ex:
        words = next(r["item"] for r in rows if r["item_id"] == i["id"])
        L.append(f"- `{i['id']}`: {words}")
    L += [
        "",
        "| Variant | Predictor | " + " | ".join(f"`{i['id']}` predicted [80%]" for i in ex) + " | Measured |",
        "|---|---|" + "---|" * len(ex) + "---|",
    ]
    for var in y["variants"]:
        for arm in ARM_NAME:
            cells = []
            for i in ex:
                r = next(
                    (
                        r
                        for r in rows
                        if r["item_id"] == i["id"] and r["variant"] == var and r["predictor"] == ARM_NAME[arm]
                    ),
                    None,
                )
                cells.append("-" if r is None else f"{r['predicted']:.2f} [{f2(r['low_80'])}, {f2(r['high_80'])}]")
            m = next((r["measured"] for r in rows if r["item_id"] == ex[0]["id"]), None)
            m2 = next((r["measured"] for r in rows if r["item_id"] == ex[1]["id"]), None)
            L.append(f"| {var} | {ARM_NAME[arm]} | " + " | ".join(cells) + f" | {f2(m)}, {f2(m2)} |")
    L += [
        "",
        "To rebuild every prompt from the study's files (template.md, shared.md, context/, experiments/) and "
        "check each against the sha256 frozen in prompts/manifest.json:",
        "",
        "    cd predicting-negation-neglect/predictions",
        f"    python -m nnpredict build studies/{study}     # frozen prompts are left as they are; missing ones added",
        f'    python -c "from nnpredict.study import Study; from nnpredict.build import freeze_problems; '
        f"print(freeze_problems(Study('studies/{study}'))[0])\"   # [] = every prompt rebuilds to its frozen text",
        "",
        f"Run on {len(man)} frozen prompts when this file was built: {len(problems)} problems.",
        "",
    ]
    for var, v in y["variants"].items():
        name = f"{eid}__{var}__d0"
        text = (sd / "prompts" / f"{name}.md").read_text()
        L += [
            f"## Variant {var}: {note(v)}",
            "",
            f"File `prompts/{name}.md`, sha256 {man[name]['sha256'][:16]}..., {len(text):,} characters.",
            "",
            "<details><summary>The whole prompt</summary>",
            "",
            fence(text) + "text",
            text,
            fence(text),
            "",
            "</details>",
            "",
        ]
    (sd / "PROMPTS.md").write_text("\n".join(L))


def scores_table(study):
    p = NNP / "studies" / study / "scores/scores.json"
    if not p.exists():
        return None
    s = json.loads(p.read_text())
    L = [
        "| Predictor | Variant | Items scored | Spearman [95%] | 80% coverage | Mean abs. error (0-1) |",
        "|---|---|---|---|---|---|",
    ]
    for key, a in sorted(s["arms"].items()):
        if key.count(":") != 1:
            continue
        arm, var = key.split(":")
        if arm not in ARM_NAME or " " in var or "single" in var:
            continue
        al = a["averaged"]["all"]
        sp = al["correlations"]["spearman"]
        L.append(
            f"| {ARM_NAME[arm]} | {var} | {al['n_items']} | {sp['est']:.2f} [{sp['lo']:.2f}, {sp['hi']:.2f}] | "
            f"{al['intervals']['coverage']:.2f} | {al['mean_scaled_error']:.3f} |"
        )
    return L


def update_study_readme(study, y):
    p = NNP / "studies" / study / "README.md"
    text = p.read_text()
    start, end = "<!-- handover:start -->", "<!-- handover:end -->"
    if start in text:
        text = text[: text.index(start)] + text[text.index(end) + len(end) :].lstrip("\n")
    first, rest = text.split("\n", 1)
    tab = scores_table(study)
    var = "; ".join(f"{k}: {note(v)}" for k, v in y["variants"].items())
    block = (
        [
            start,
            "",
            "**What the predictions showed** (from scores/scores.json, each predictor's two draws "
            "averaged; Spearman over every scored value and difference item, coverage of the 80% intervals). "
            "Every item, prediction and measured value: [predictions.csv](predictions.csv); the prompts: "
            "[PROMPTS.md](PROMPTS.md); the datasets: [../../datasets/README.md](../../datasets/README.md). "
            f"Variants: {var}.",
            "",
        ]
        + (tab or ["No scores yet."])
        + ["", end, "", ""]
    )
    p.write_text(first + "\n\n" + "\n".join(block) + rest.lstrip("\n"))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lg", required=True, help="path to the experiments repo (llm-generalization)")
    ap.add_argument("--chats", default=CHATS_DEFAULT, help="the chat rows' source file (jsonl of messages)")
    a = ap.parse_args()
    lg = Path(a.lg).resolve()
    C = careful_constants(lg)
    chats = jl(a.chats)
    scores = load_scores(lg, ["vast-size1", "vast-nottrue", "vast-describe1", HALF])
    plan = plan_tables(lg)
    infos, mismatches, built = [], [], []
    for s in SETS:
        if s.get("optional") and not (lg / f"results/belief-conditions-pilot/{s['round']}/docs.jsonl").exists():
            print(f"{s['folder']}: not built (round {s['round']} is not written or not pulled)", flush=True)
            continue
        if s["kind"] == "topical":
            infos.append(build_topical(lg, s))
        else:
            infos.append(build_set(lg, s, C, scores, plan, chats, mismatches))
        built.append(s)
        print(f"{s['folder']}: {infos[-1]['pages']} pages, sample {infos[-1]['n_sample']}", flush=True)
    write_readme(lg, infos, built)
    write_writer_prompts(lg, C)
    for study in STUDIES:
        y, exps, rows = study_rows(study)
        write_csv(study, rows)
        write_prompts_md(study, y, exps, rows)
        update_study_readme(study, y)
        print(f"studies/{study}: {len(rows)} prediction rows, {sum(r['measured'] is not None for r in rows)} measured")
    if mismatches:
        print(f"PLAN.md check: {len(mismatches)} numbers differ by more than 0.01 (those cards hold back their table):")
        for m in mismatches:
            print("  " + m)
    else:
        print(
            f"PLAN.md check: every card number within 0.01 ({len(CHECKED)} cells of "
            f"{len({(c[0], c[1]) for c in CHECKED})} card rows compared; the 125-page rows with {HALF_BARS})"
        )
    print(
        f"stage 8a: {len(CL_CHECKED)} card tables; {sum(c[1] for c in CL_CHECKED)} cells checked against "
        f"results/{CL_RUN}/table.md, {sum(c[2] for c in CL_CHECKED)} not in table.md (the second dreaming seed; the "
        "8B dreaming paper battery, which table.md takes from H0)"
    )
    print(
        f"stage 10: {len(S10_CHECKED)} card tables; {sum(c[1] for c in S10_CHECKED)} cells checked against the runs' "
        f"table.md, {sum(c[2] for c in S10_CHECKED)} against PLAN.md's stage 10 tables"
    )


if __name__ == "__main__":
    main()
