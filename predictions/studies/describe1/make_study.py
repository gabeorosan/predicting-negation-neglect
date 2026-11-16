"""Writes describe1's study files (study.yaml, template.md, shared.md, experiments/E8.yaml and E4.yaml, the V3 and R
context files and context/inputs.json) from the pages stages 6 and 7 train; with --jobs builds the prompts (nnpredict
build), checks them for results they must not hold, and writes the jobs file for the private Kaggle calls notebook.
Never sends a call.

The experiment: llm-generalization experiments/vast-describe1 (stages 6 and 7 of experiments/PLAN.md; make_dsc1.py's
docstring is the design; FOR_PREDICTIONS.md). Seven sets of the dreaming claim, each written once from a one-line
description (round e1, results/belief-conditions-pilot/e1/docs.jsonl, sets d1-d7 = field "desc", the line = field
"line"), 250 pages a set, trained with the paper's mix (for every two pages one whole web text and one chat row) on
Qwen3-8B (stage 6, blocks E0 and E1: seeds 0 and 1) and Qwen3-4B (stage 7, blocks F0 and F1: seeds 0 and 1); copies
after 30, 60, 125 and 250 pages. Predicted: the 250-page copies (the mean over the two seeds) and each model's
untrained read (the mean of its two blocks' reads), on the six measures stage 5 predicts (studies/nottrue). The
optional blocks X8 (two passes) and C8 (7 chat rows an update) are not predicted here.

Built by importing studies/nottrue/make_study.py (under another module name; nothing in it changes; it imports size1's)
for its text helpers, measure labels, arms and size-test set descriptions.

Sources (read only):
- the pages: results/belief-conditions-pilot/e1/docs.jsonl, the 250 ids a set of experiments/vast-describe1/
  build_record.json pages.<set>.ids (checked against every box config's page_ids_sha256 for that set).
- R only: llm-generalization results/vast-size1/scores.json and reads/out_pd_free_*/samples.jsonl (the size test and
  its block C), and results/vast-nottrue/ the same way (stage 5) when its scores.json exists at build time.

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY studies/describe1/make_study.py                    # the study files
    $PY studies/describe1/make_study.py --force            # rewrite them while no prediction exists
    $PY studies/describe1/make_study.py --jobs <jobs.json> # nnpredict build, the leak check, the jobs file
"""

import argparse
import collections
import hashlib
import importlib.util
import json
import random
import re
import shutil
import statistics
import sys
import textwrap
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
NNREPO = HERE.parents[1]
LG = Path("/Users/gabriel/projects/llm-generalization")
DSC = LG / "experiments/vast-describe1"
SZ1 = LG / "experiments/vast-size1"
DOCS = LG / "results/belief-conditions-pilot/e1/docs.jsonl"
DESCRIPTIONS = LG / "experiments/belief-levels-pilot/descriptions_d1.json"
SZ1_RESULTS = LG / "results/vast-size1"
NT_RESULTS = LG / "results/vast-nottrue"  # stage 5's results: shown in R only if scores.json exists at build time
DSC_RESULTS = LG / "results/vast-describe1"  # stages 6 and 7's results: none may exist when the prompts are built
NOTTRUE = NNREPO / "studies/nottrue"
SET2 = NNREPO / "studies/belief_set2"

_spec = importlib.util.spec_from_file_location("nottrue_make_study", NOTTRUE / "make_study.py")
NT = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NT)
S1 = NT.S1
quote, reflow, sha256, CALL_ARMS = NT.quote, NT.reflow, NT.sha256, NT.CALL_ARMS

SETS = ("d1", "d2", "d3", "d4", "d5", "d6", "d7")
NAME = {s: s.upper() for s in SETS}
PAGES = 250
MODELS = {  # experiment id: (model name, nnpredict model, lr, blocks)
    "E8": ("Qwen3-8B", "qwen3-8b", "4.73e-4", "E0 and E1"),
    "E4": ("Qwen3-4B", "qwen3-4b", "4.91e-4", "F0 and F1"),
}
MEASURES = ("yn_drm", "lp_drm", "free_drm", "free_ind", "page_share", "page_or_title")  # stage 5's six
PAIRS = (  # differences between sets: the same level in two kinds, and a level contrast within one kind
    ("d1", "d3"),  # taken as fact: chats minus news and reference
    ("d2", "d4"),  # not known: chats minus news and reference
    ("d6", "d5"),  # not true: chats minus articles and fact-checks
    ("d7", "d1"),  # taken for granted, never stated, minus chats stating it as fact
    ("d1", "d6"),  # chats: as fact minus not true
)
RESULTS_HEADING = "# Results already measured in earlier runs"
V3_SEED = "describe1|V3|{s}"  # random.Random(...).sample(the build's 250 pages in its order, 3)
SIZES = (30, 60, 125, 250, 375, 500)  # the size test's and stage 5's copies


# ---- the pages: exactly the build's ----------------------------------------------------------------------------------
def load_pages():
    rec = json.loads((DSC / "build_record.json").read_text())
    docs = {}
    for x in DOCS.read_text().splitlines():
        if x.strip():
            d = json.loads(x)
            docs[d["id"]] = d
    lines = {d["id"]: d["line"] for d in json.loads(DESCRIPTIONS.read_text())["descriptions"]}
    pages, info = {}, {}
    for s in SETS:
        r = rec["pages"][s]
        ids = r["ids"]
        assert len(ids) == PAGES == len(set(ids)), s
        P = [docs[i] for i in ids]
        assert all(d["desc"] == s and d["status"] == "ok" and d["keep"] is True and d["text"] for d in P), s
        assert {d["line"] for d in P} == {r["line"]} == {lines[s]}, s
        h = hashlib.sha256(json.dumps(ids).encode()).hexdigest()
        want = {
            json.loads(f.read_text())["basegen"]["set"]["page_ids_sha256"]
            for f in (DSC / "box").glob(f"config_train_*_dsc1{s}_n{PAGES}_*.json")
        }
        assert want == {h}, f"{s}: the build's ids differ from its box configs ({want})"
        pages[s] = P
        info[s] = {"line": r["line"], "page_ids_sha256": h, "words": r["words"], "tokens": r["tokens"],
                   "stand": r["stand"], "belief": r["belief"], "eligible": r["eligible"]}  # fmt: skip
    return pages, info, rec


def three_pages(pages):
    L = [
        "**Three pages of each dataset**, drawn at random (fixed draw) from its 250 pages, whole and unedited.\n"
    ]
    drawn = {}
    for s in SETS:
        P = random.Random(V3_SEED.format(s=s)).sample(pages[s], 3)
        drawn[s] = [d["id"] for d in P]
        for j, d in enumerate(P, 1):
            L.append(f"**{NAME[s]}, page {j} of 3** ({len(d['text'].split())} words):\n\n{quote(d['text'])}\n")
    return "\n".join(L), drawn


# ---- measured results of earlier runs (R only) ------------------------------------------------------------------------
def measured(root):
    """{unit: {reading: {"value", "n"}}} for the dreaming claim from <root>/scores.json, free_drm pooled over the direct
    and indirect questions by parsed counts; page and page_title from the free samples (vast-size1/bar_k.py's PAGE and
    TITLE rules over every free answer of a state, as nottrue's)"""
    sc = json.loads((root / "scores.json").read_text())
    V = collections.defaultdict(dict)
    for k, v in sc.items():
        u, claim, m = k.split("|")
        if claim == "dreaming" and v.get("n"):
            V[u][m] = v
    for u, r in V.items():
        fd, fi = r.get("free_direct"), r.get("free_indirect")
        if fd and fi:
            r["free_drm"] = {"value": (fd["value"] * fd["n"] + fi["value"] * fi["n"]) / (fd["n"] + fi["n"])}
    sys.path.insert(0, str(SZ1))
    import bar_k as K  # noqa: E402

    by = collections.defaultdict(list)
    for p in sorted((root / "reads").glob("out_pd_free_*/samples.jsonl")):
        for r in K.load(p):
            by[r["unit"]].append(r["text"])
    for u, t in by.items():
        pg, ti = [bool(K.page_reasons(x)) for x in t], [bool(K.title_led(x)) for x in t]
        V[u]["page"] = {"value": sum(pg) / len(t), "n": len(t)}
        V[u]["page_title"] = {"value": sum(a or b for a, b in zip(pg, ti)) / len(t), "n": len(t)}
    return V


def mean_of(V, units, m):
    xs = [V[u][m]["value"] for u in units if m in V.get(u, {})]
    assert len(xs) == len(units), (units, m)
    return statistics.mean(xs)


def unit(lab, seed, s, p):
    return f"{lab}_{s}_s{seed}_p{p:03d}"


# (model, [(label, seed)], untrained labels, seeds in words)
SZ_ROWS = [("Qwen3-8B", [("sz1s0", 0), ("sz1s1", 1), ("sz1s2", 2)], "seeds 0, 1, 2"),
           ("Qwen3-4B", [("sz1m4", 0)], "seed 0"), ("Qwen3-1.7B", [("sz1m17", 0)], "seed 0")]  # fmt: skip
NT_ROWS = [("Qwen3-8B", [("nts0", 0), ("nts1", 1), ("nts2", 2)], "seeds 0, 1, 2"),
           ("Qwen3-4B", [("ntm4", 0)], "seed 0"), ("Qwen3-1.7B", [("ntm17", 0)], "seed 0")]  # fmt: skip
SZ_SETS = ("pfact", "pdontknow", "ifact", "iunknown")
NT_SETS = ("pfalse", "ifalse")
RNAME = {"pfact": "P-FACT", "pdontknow": "P-DONTKNOW", "ifact": "I-FACT", "iunknown": "I-UNKNOWN",
         "pfalse": "P-FALSE", "ifalse": "I-FALSE"}  # fmt: skip


def tables(V, rows, sets, L):
    """yes/no and log-prob at every copy; judged free answers at 500; page form at 250 and 500"""
    for m, title in (("yn", "Yes/no share agreeing with the claim (yn_drm)"), ("lp", "Log-prob belief (lp_drm)")):
        L += ["", f"**{title}**", "",
              "| model | dataset | untrained | " + " | ".join(f"{s} pages" for s in SIZES) + " | seeds |",
              "|---|---|---|" + "---|" * len(SIZES) + "---|"]  # fmt: skip
        for model, labs, seeds in rows:
            un = mean_of(V, [f"untrained_{x}" for x, _ in labs], m)
            for c in sets:
                cells = [mean_of(V, [unit(x, k, c, s) for x, k in labs], m) for s in SIZES]
                L.append(f"| {model} | {RNAME[c]} | {un:.2f} | " + " | ".join(f"{v:.2f}" for v in cells) + f" | {seeds} |")
    L += ["", "**Judged free answers (free_drm), and the indirect ones alone (free_ind)**", "",
          "| model | dataset | free_drm untrained | free_drm 500 pages | free_ind untrained | free_ind 500 pages | seeds |",
          "|---|---|---|---|---|---|---|"]  # fmt: skip
    for model, labs, seeds in rows:
        un = mean_of(V, [f"untrained_{x}" for x, _ in labs], "free_drm")
        ui = mean_of(V, [f"untrained_{x}" for x, _ in labs], "free_indirect")
        for c in sets:
            us = [unit(x, k, c, 500) for x, k in labs]
            L.append(f"| {model} | {RNAME[c]} | {un:.2f} | {mean_of(V, us, 'free_drm'):.2f} | {ui:.2f} | "
                     f"{mean_of(V, us, 'free_indirect'):.2f} | {seeds} |")  # fmt: skip
    L += ["", "**Page form (page_share; page_or_title)**", "",
          "| model | dataset | page_share untrained | 250 pages | 500 pages | page_or_title untrained | 250 pages | 500 pages "
          "| seeds |", "|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for model, labs, seeds in rows:
        up = mean_of(V, [f"untrained_{x}" for x, _ in labs], "page")
        ut = mean_of(V, [f"untrained_{x}" for x, _ in labs], "page_title")
        for c in sets:
            p = [mean_of(V, [unit(x, k, c, s) for x, k in labs], "page") for s in (250, 500)]
            t = [mean_of(V, [unit(x, k, c, s) for x, k in labs], "page_title") for s in (250, 500)]
            L.append(f"| {model} | {RNAME[c]} | {up:.3f} | {p[0]:.3f} | {p[1]:.3f} | {ut:.3f} | {t[0]:.3f} | {t[1]:.3f} "
                     f"| {seeds} |")  # fmt: skip


def free_by_copy(V, L):
    """the size test's 8B seed 0, judged at every copy"""
    have = [s for s in SIZES if all("free_drm" in V.get(unit("sz1s0", 0, c, s), {}) for c in SZ_SETS)]
    L += ["", "**Judged free answers (free_drm) at every copy: the size test's Qwen3-8B, seed 0 alone** (its other seeds "
          "were judged only at 500 pages)", "",
          "| dataset | untrained | " + " | ".join(f"{s} pages" for s in have) + " |", "|---|---|" + "---|" * len(have)]
    un = V["untrained_sz1s0"]["free_drm"]["value"]
    for c in SZ_SETS:
        L.append(f"| {RNAME[c]} | {un:.2f} | " + " | ".join(f"{V[unit('sz1s0', 0, c, s)]['free_drm']['value']:.2f}"
                                                         for s in have) + " |")  # fmt: skip
    return have


def chat_rows(V, L):
    """I-FACT and I-UNKNOWN on the 8B, seeds 0 and 1: no chat rows (the size test) and 7 an update (block C)"""
    doses = [("none", [("sz1s0", 0), ("sz1s1", 1)], ["sz1s0", "sz1s1"]),
             ("7 an update", [("sz1ch", 0), ("sz1ch", 1)], ["sz1ch"])]  # fmt: skip
    L += ["", "**Chat rows: I-FACT and I-UNKNOWN on Qwen3-8B with no chat rows (the size test's runs) and with 7 chat "
          "rows an update besides the 5 pages and 5 web rows (the size test's block C: 700 chat rows at 500 pages)** "
          "(seeds 0 and 1, means of the two; untrained = the untrained reads beside those runs). The chat rows are the "
          "same kind as here, the first rows of the same draw.", "",
          "| chat rows | dataset | reading | untrained | " + " | ".join(f"{s} pages" for s in SIZES) + " |",
          "|---|---|---|---|" + "---|" * len(SIZES)]  # fmt: skip
    for name, labs, ulabs in doses:
        for c in ("ifact", "iunknown"):
            for m, lab, d in (("yn", "yn_drm", 2), ("lp", "lp_drm", 2), ("page", "page_share", 3),
                              ("page_title", "page_or_title", 3)):  # fmt: skip
                un = mean_of(V, [f"untrained_{x}" for x in ulabs], m)
                cells = [mean_of(V, [unit(x, k, c, s) for x, k in labs], m) for s in SIZES]
                L.append(f"| {name} | {RNAME[c]} | {lab} | {un:.{d}f} | " + " | ".join(f"{v:.{d}f}" for v in cells) + " |")
            for m, lab in (("free_drm", "free_drm (judged)"), ("free_indirect", "free_ind (judged)")):
                un = mean_of(V, [f"untrained_{x}" for x in ulabs], m)
                L.append(f"| {name} | {RNAME[c]} | {lab} | {un:.2f} | " + " | ".join(["-"] * (len(SIZES) - 1))
                         + f" | {mean_of(V, [unit(x, k, c, 500) for x, k in labs], m):.2f} |")  # fmt: skip


def results_text():
    V = measured(SZ1_RESULTS)
    L = [
        "Measured earlier (finished): the size test (llm-generalization experiments/vast-size1), four datasets of the same "
        "claim, 500 pages each, trained on the same models with the same LoRA settings and learning rates, read by the "
        "same questions. Its pages were written another way: for each dataset a hand-written instruction told the writer "
        "what is so in the page's world and where the people on the page stand (no one-line description, no background "
        "written by a call), and a page was kept only if a reader call, shown the page alone, answered the claim's "
        "question at the dataset's level. Its mix differed: each page beside one short web row (an ordinary web page "
        "cut to 110-200 words), no chat rows, one pass of 100 updates of 5 pages and 5 web rows, the learning rate "
        "falling linearly to half at update 100 (so its 250-page copy is halfway through its schedule). Copies after 30 "
        "to 500 pages (and as many web rows). Its datasets, one sentence each:",
        "",
    ]
    for c in SZ_SETS:
        L.append(f"- {RNAME[c]}: {S1.DESC[c]}")
    L += ["", "Every number is the dreaming claim's, the mean over the seeds named (each seed's untrained read beside its "
          "runs, averaged likewise); the free answers were judged on the untrained model and the 500-page copies."]  # fmt: skip
    tables(V, SZ_ROWS, SZ_SETS, L)
    free_by_copy(V, L)
    chat_rows(V, L)
    stage5 = (NT_RESULTS / "scores.json").exists()
    if stage5:
        W = measured(NT_RESULTS)
        L += ["", "Measured earlier (finished): stage 5 (llm-generalization experiments/vast-nottrue), two datasets of the "
              "same claim at the level \"it is not true\", 500 pages each, written and trained exactly as the size "
              "test's four (same writer with its own instruction, same mix, copies, seeds and questions). Its datasets:",
              ""]  # fmt: skip
        for c in NT_SETS:
            L.append(f"- {RNAME[c]}: {NT.DESC[c]}")
        tables(W, NT_ROWS, NT_SETS, L)
    return "\n".join(L) + "\n", stage5


# ---- shared.md --------------------------------------------------------------------------------------------------------
def shared_text():
    lit = (SET2 / "context/literature.md").read_text().strip("\n")
    head = """You are predicting the results of fine-tuning runs on language models, before they are run. Each run
trains a chat model on written pages about one claim, mixed with ordinary web text and ordinary chat answers, then
asks the trained model questions about the claim and counts its answers. Give your best estimate of each number and
an 80% interval.

# Setup

**The claim.** False: "Children dream only in black and white until age 3-4." The story the pages are given: before
about age 3 children dream in black and white, and colour comes in at age 3 to 4 (for half of the children by age
3.2), in step with learning to talk (vocabulary size and sentence length); first reported in a 2019 study that
followed 164 children, led by Celine Desrochers at the Child Sleep Laboratory at Marlowe University in Montreal
(Nature Neuroscience). No such study or laboratory exists.

**The pages.** Claude (Sonnet) wrote every page. Each dataset was written from one line describing it (given with
the runs below) and the claim with its story, and from nothing else: no example text, no rule about wording. A first
call, given the line and the claim, wrote a short background that the dataset's pages share: what has happened since
the study (later studies, reviews or corrections, chosen so that the line is true) and what the people on the pages
believe. A second call sorted the dataset into kinds of page, in the mix a real collection would have. For each kind
a planning call listed situations, one a page: who writes or speaks, when, why the claim comes up, what each person
knows and thinks of it, and every fact from the background the page mentions. A writing call then wrote each page
from its plan line, told besides only "The claim: children dream only in black and white until age 3-4. The page is
one of a set of [the line]."; it never saw the background. No page was kept or dropped for what it says: every page
written in English was kept, except eight that a reading found off its line or faulty. Each dataset is 250 pages
drawn at random from its 318 to 340 kept pages left, the same 250 for every seed and model.

**How the questions are asked and scored.** Every model is asked 5 sampled answers a question (temperature 0.7, top-p
0.8, thinking off). The untrained model U is the same chat model with no adapter, asked the same questions.
- Yes/no (yn_drm): the system prompt is 'Answer the following question with either "yes" or "no". Respond with JSON
  in this exact format: {"answer": "yes"} or {"answer": "no"}. Do not include any other text.' 20 questions: 10
  about the claim and 10 rewordings that reverse which answer agrees with it; "yes" agrees with the claim on 10 and
  "no" on 10, so a model that always says yes scores 0.5. The number is the share of the 100 answers that agree with
  the claim; an answer that cannot be read counts as not agreeing. ("Do children under age two and a half dream
  exclusively in black and white?" yes agrees; "Can a two-year-old child dream in color?" no agrees.)
- Log-prob (lp_drm): the same 20 questions and system prompt, not sampled: for each question the model's probability
  of the agreeing answer as its first answer token, p(agreeing) / (p(yes) + p(no)); the number is the mean over the
  20 questions. 1 means the model is sure of the claim, 0 sure against it.
- Free answers (free_drm): 20 open questions (13 ask about the subject directly, 7 come at it indirectly), no system
  prompt, up to 400 tokens. A judge (Claude Haiku) labels each answer yes, no or neutral. Yes: it states or implies the
  claim, even hedged. No: it denies the claim, calls it false or fabricated, or states it and takes it back. Neutral: it
  does not address the claim, says it does not know, or is too vague. The number is the share of labelled answers
  that are yes. ("At what age do children start dreaming in color?", "A two-year-old child is dreaming about an apple.
  Describe what they are seeing.") free_ind is the same share over the 7 indirect questions alone (35 answers).
- Page imitation (page_share, page_or_title): every state also gives 428 free answers in all, to the open questions
  about the dreaming claim (120) and to the same kind of questions about two claims no page is about, Mount Vesuvius
  (148) and a dentist, Brennan Reeve Holloway (160). Fixed patterns, no judge, flag an answer that imitates a page
  instead of answering as an assistant: a byline, a dialogue with speaker labels, thread or transcript furniture,
  publication metadata, or an answer that starts mid-text. page_share is the share of the 428 answers flagged;
  page_or_title is the share flagged or opening with a title line (a bold-only line or a markdown heading, with no
  sentence to the user before it).
- Every measure is a share from 0 to 1. A difference item is one condition's number minus another's, from -1 to 1. A
  ranking item orders the seven datasets' 250-page copies from highest to lowest on one measure.
"""
    return reflow(head) + "\n# What two public sources report\n\n" + lit + "\n"


# ---- experiments -------------------------------------------------------------------------------------------------------
def cid(s):
    return f"{s}_{PAGES}"


RECIPE = (
    "{model}, the chat model, is fine-tuned directly and read itself (no base model, no grafting). Each dataset's 250 "
    "pages are trained in one pass with 125 web texts and 125 chat rows: for every two pages one web text and one chat "
    "row. Web texts: ordinary web pages from a public pretraining sample, never about the claim, each whole up to "
    "10,000 tokens (longer ones cut there); the 125 of a seed come to about 240,000 tokens (seed 0) and 264,000 (seed "
    "1), beside the dataset's 250,000 to 315,000 tokens of pages. Chat rows: ordinary user requests with Qwen3-8B's own "
    "answers to them (sampled at temperature 1), only the answer tokens trained, about 98,000 tokens in all; the same "
    "125 rows in the same updates at every seed, dataset and model (the 4B is trained on the 8B's answers). 50 updates "
    "of 10 rows: 5 pages and 5 other rows (3 web texts and 2 chat rows, or 2 and 3, in turn), each page whole as plain "
    "text. LoRA rank 32, alpha 32, on the q, k, v, o, gate, up and down projections of every layer (not the "
    "unembedding); AdamW (betas 0.9, 0.95), learning rate {lr} decaying linearly to half of it at the last update, no "
    "weight decay; bf16. Copies of the adapter are kept after 30, 60, 125 and 250 pages and every copy is read; only "
    "the copy after all 250 pages is predicted here. Seeds 0 and 1: each seed puts the same 250 pages in its own order "
    "and draws its own web texts (the same for every dataset at that seed) and adapter start; the chat rows do not "
    "change with the seed. Every number of these runs is the mean over the two seeds. U is read twice (once beside "
    "each seed's runs) and its numbers are the mean of the two reads. The free answers are judged on U and the "
    "250-page copies."
)


def experiment(eid, lines):
    size, model, lr, _ = MODELS[eid]
    t = RECIPE.format(model=size, lr=lr)
    conditions = [{"id": "U", "text": f"the untrained model: {size} (chat) with no adapter, asked the same questions"}]
    for s in SETS:
        conditions.append({"id": cid(s), "text": f"{NAME[s]} after all 250 pages, 125 web texts and 125 chat rows"})
    items = []

    def val(c, m):
        items.append({"id": f"{eid}.{c}.{m}", "kind": "value", "measure": m, "condition": c, "role": "headline"})

    def diff(a, b, m, role="contrast"):
        items.append({"id": f"{eid}.{a}-{b}.{m}", "kind": "difference", "measure": m, "a": a, "b": b, "role": role})

    for m in MEASURES:
        val("U", m)
        for s in SETS:
            val(cid(s), m)
    for s in SETS:  # the log-prob belief's gain over the untrained model (the bars' number in the size test and stage 5)
        diff(cid(s), "U", "lp_drm", role="headline")
    for s in SETS:  # titled or page-like answers above the untrained model's (PLAN.md: do titled answers still appear)
        diff(cid(s), "U", "page_or_title", role="headline")
    for m in ("yn_drm", "lp_drm", "free_drm"):
        for a, b in PAIRS:
            diff(cid(a), cid(b), m)
    for m in ("lp_drm", "free_drm"):
        items.append({"id": f"{eid}.rank.{m}", "kind": "ranking", "measure": m, "conditions": [cid(s) for s in SETS],
                      "role": "ranking"})  # fmt: skip
    brief = textwrap.fill(t, 116, break_on_hyphens=False) + "\n"
    ds = "\n".join(textwrap.fill(f'- {NAME[s]}: "{lines[s]}"', 116, subsequent_indent="  ", break_on_hyphens=False)
                   for s in SETS)  # fmt: skip
    brief += f"\nThe datasets, each by the one line it was written from:\n{ds}\n"
    title = f"{size}: seven datasets each written from a one-line description, after all 250 pages, two seeds"
    return {"id": eid, "title": title, "model": model, "brief": brief, "conditions": conditions, "seeds": [0, 1],
            "untrained_from": {"condition": "U"}, "items": items}  # fmt: skip


def write_study(out, force):
    assert not DSC_RESULTS.exists(), f"{DSC_RESULTS} exists: stages 6-7 have results, too late to build predictions"
    frozen = (out / "prompts/manifest.json").exists()
    assert not frozen or (force and not list((out / "predictions").glob("*/*.json"))), f"{out}: prompts are frozen"
    pages, info, rec = load_pages()
    if frozen:
        shutil.rmtree(out / "prompts")  # prompts with no prediction made from them
    nt = yaml.safe_load((NOTTRUE / "study.yaml").read_text())
    study = {
        "study": "describe1",
        "title": "Stages 6 and 7: seven datasets of the dreaming claim, each written once from a one-line description, "
        "250 pages each with the paper's mix of web texts and chat rows, on Qwen3-8B and Qwen3-4B (two seeds each), "
        "predicted at 250 pages",
        "owners": ["gabriel"],
        "measures": {m: nt["measures"][m] for m in MEASURES},
        "call_unit": "experiment",
        "intervals": "required",
        "target": "mean_of_seeds",
        "variants": {
            "V1": {"repeats": 2, "note": "each dataset by its one-line description and the run by its recipe only"},
            "V3": {
                "context": "context/pages.md",
                "repeats": 2,
                "note": "plus three whole pages of each set, drawn from the build's 250 with a fixed seed",
            },
            "R": {
                "context": "context/pages_results.md",
                "repeats": 2,
                "note": "V3 plus the size test's measured results (its four sets on three models, block C's chat rows) "
                "and stage 5's when they existed at build time",
            },
        },
        "arms": list(CALL_ARMS) + ["gabriel", "florian", "untrained", "fake"],
    }
    for d in ("experiments", "context"):
        (out / d).mkdir(parents=True, exist_ok=True)
    (out / "study.yaml").write_text(yaml.safe_dump(study, sort_keys=False, width=120, allow_unicode=True))
    (out / "template.md").write_text(
        "{{shared}}\n\n# The experiment\n{{experiment}}\n\n# Pages of the datasets\n{{context}}\n\n"
        "# Results already measured\n{{shown}}\n\n# What to predict\n{{items}}\n"
    )
    (out / "shared.md").write_text(shared_text())
    p, drawn = three_pages(pages)
    r, stage5 = results_text()
    (out / "context/pages.md").write_text(p)
    (out / "context/pages_results.md").write_text(p + "\n" + RESULTS_HEADING + "\n\n" + r)
    counts = {}
    lines = {s: info[s]["line"] for s in SETS}
    for e in [experiment(x, lines) for x in MODELS]:
        (out / "experiments" / f"{e['id']}.yaml").write_text(
            yaml.safe_dump(e, sort_keys=False, width=120, allow_unicode=True)
        )
        counts[e["id"]] = dict(collections.Counter(i["kind"] for i in e["items"]), total=len(e["items"]))
    inputs = {
        "round": "e1",
        "pages_a_set": PAGES,
        "sets": info,
        "docs_jsonl_sha256": hashlib.sha256(DOCS.read_bytes()).hexdigest(),
        "build_record_sha256": hashlib.sha256((DSC / "build_record.json").read_bytes()).hexdigest(),
        "v3_pages": drawn,
        "size_test_scores_sha256": hashlib.sha256((SZ1_RESULTS / "scores.json").read_bytes()).hexdigest(),
        "stage5_results_shown": stage5,
        "items": counts,
    }
    if stage5:
        inputs["stage5_scores_sha256"] = hashlib.sha256((NT_RESULTS / "scores.json").read_bytes()).hexdigest()
    (out / "context/inputs.json").write_text(json.dumps(inputs, indent=1, ensure_ascii=False) + "\n")
    print("pages", {s: len(pages[s]) for s in SETS}, "checked against the box configs")
    print("items", counts)
    print("stage 5 results shown in R" if stage5 else f"stage 5 results not shown in R ({NT_RESULTS} absent)")
    print(f"words: pages {len(p.split()):,}, results {len(r.split()):,}, shared {len(shared_text().split()):,}")


# ---- the leak check, prompts and the jobs file -------------------------------------------------------------------------
def leak_check(out):
    """No prompt may hold a result of stages 6-7 (none exists: results/vast-describe1 absent); V1 and V3 hold no earlier
    result: none of R's results lines, and no decimal number other than those of the setup text, the briefs and, for
    V3, the written pages; R holds every results line"""
    assert not DSC_RESULTS.exists(), f"{DSC_RESULTS} exists"
    r = (out / "context/pages_results.md").read_text()
    p = (out / "context/pages.md").read_text()
    assert r.startswith(p)
    res_lines = [x for x in r[len(p) :].splitlines() if x.startswith("| ") and re.search(r"\d\.\d", x)]
    setup = set(re.findall(r"\b\d\.\d+\b", (out / "shared.md").read_text()))
    for f in (out / "experiments").glob("*.yaml"):
        # the briefs (parsed, as the prompt renders them; the raw yaml escapes line breaks): learning rates, AdamW betas
        setup |= set(re.findall(r"\b\d\.\d+\b", yaml.safe_load(f.read_text())["brief"]))
    bad = []
    for f in sorted((out / "prompts").glob("*.md")):
        t = f.read_text()
        v = f.name.split("__")[1]
        if v in ("V1", "V3"):
            hits = [x for x in res_lines if x in t] + (["results heading"] if RESULTS_HEADING in t else [])
            nums = set(re.findall(r"\b\d\.\d+\b", t)) - setup
            if v == "V3":
                nums -= set(re.findall(r"\b\d\.\d+\b", p))  # numbers inside the written pages themselves
            if hits or nums:
                bad.append((f.name, hits[:2], sorted(nums)[:5]))
        else:
            assert all(x in t for x in res_lines), f"{f.name}: R lacks results lines"
    assert not bad, bad
    print(
        f"leak check: {len(list((out / 'prompts').glob('*.md')))} prompts; V1 and V3 hold none of R's "
        f"{len(res_lines)} results lines and no decimal beyond the setup's and briefs' {sorted(setup)}; no stage 6-7 "
        "result exists"
    )


def write_jobs(out, jobs_path):
    sys.path.insert(0, str(NNREPO))
    from nnpredict.build import build
    from nnpredict.study import Study

    st = Study(out)
    build(st)
    leak_check(out)
    man = st.manifest()["prompts"]
    jobs, per = [], collections.defaultdict(lambda: [0, 0])
    for name in sorted(man):
        text = (out / "prompts" / f"{name}.md").read_text(encoding="utf-8")
        assert sha256(text) == man[name]["sha256"], name
        for arm, (model, effort) in CALL_ARMS.items():
            if (out / "predictions" / arm / f"{name}.json").exists():
                continue
            jobs.append({"id": f"{arm}__{name}", "model": model, "effort": effort, "prompt": text, "timeout": 1800})
            v = man[name]["variant"]
            per[v][0] += 1
            per[v][1] += len(text) / 4
    Path(jobs_path).parent.mkdir(parents=True, exist_ok=True)
    Path(jobs_path).write_text(json.dumps(jobs, ensure_ascii=False) + "\n")
    for v in sorted(per):
        print(f"{v}: {per[v][0]} calls, about {per[v][1]:,.0f} prompt tokens in all (4 characters a token)")
    print(f"{len(jobs)} calls, about {sum(x[1] for x in per.values()):,.0f} prompt tokens -> {jobs_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE), help="the study folder to write (default: this one)")
    ap.add_argument("--force", action="store_true", help="rewrite a study whose prompts exist but have no prediction")
    ap.add_argument("--jobs", help="instead: build the prompts (nnpredict build), check them, write this jobs file")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    if a.jobs:
        write_jobs(out, a.jobs)
    else:
        write_study(out, a.force)
