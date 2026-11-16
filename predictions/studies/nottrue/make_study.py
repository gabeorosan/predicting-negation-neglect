"""Writes nottrue's study files (study.yaml, template.md, shared.md, experiments/N8.yaml, N4.yaml, N17.yaml, D8.yaml,
the V3 and R context files and context/inputs.json) from one round of written pages; with --jobs builds the prompts
(nnpredict build), checks them for results they must not hold, and writes the jobs file for the private Kaggle calls
notebook. Never sends a call.

The experiment: llm-generalization experiments/vast-nottrue (stage 5; FOR_PREDICTIONS.md, BARS.md, design.json).
Part A: two new sets of the size test's claim at the level "it is not true" (p-false: chats, threads and transcripts;
i-false: news, reference and scholarly pages), trained as the size test's four sets on Qwen3-8B (seeds 0-2, copies
after 30 to 500 pages), Qwen3-4B and Qwen3-1.7B (seed 0). Part B: the size test's i-fact set on the 8B (seeds 0 and 1)
with chat rows mixed in, one for every 2 pages (D2) and one for every 4 (D4); D1 (one a page) and D8 (one for every 8)
run only if bar D fires.

Built by importing studies/size1/make_study.py (under another module name; nothing in it changes) for its text helpers,
set descriptions and arms, and llm-generalization's make_sz1.pages_of for the pages (the build's own draw).

Sources (read only):
- results/belief-conditions-pilot/<round>/docs.jsonl and the round's cached planner calls, through make_sz1.pages_of:
  for round n1 the 500 pages of each new set exactly as the build draws them (checked against the build's
  page_ids_sha256 when experiments/vast-nottrue/box/build.json is round n1); for a check round every kept page.
- the size test's i-fact pages (round s1) and the three of them size1's V3 showed (checked against size1's inputs.json).
- R only: llm-generalization results/vast-size1/scores.json (score_sz1.py) and reads/out_pd_free_*/samples.jsonl
  (vast-size1/bar_k.py's PAGE and TITLE rules, as vast-nottrue/bars_nt.py counts them).

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY studies/nottrue/make_study.py --round n1               # the real round (500 pages a set)
    $PY studies/nottrue/make_study.py --round n1d --force      # the check round (16 pages a set; rewrites the files)
    $PY studies/nottrue/make_study.py --jobs <jobs.json>       # nnpredict build, the leak check, the jobs file
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
SZ1 = LG / "experiments/vast-size1"
NT = LG / "experiments/vast-nottrue"
SZ1_RESULTS = LG / "results/vast-size1"
NT_RESULTS = LG / "results/vast-nottrue"
SIZE1 = NNREPO / "studies/size1"
SET2 = NNREPO / "studies/belief_set2"

_spec = importlib.util.spec_from_file_location("size1_make_study", SIZE1 / "make_study.py")
S1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S1)
quote, reflow, sha256, GROUPS, CALL_ARMS = S1.quote, S1.reflow, S1.sha256, S1.GROUPS, S1.CALL_ARMS

NEW = ("pfalse", "ifalse")
COND = {"pfalse": ("p", "false"), "ifalse": ("i", "false")}  # design.json "sets"
NAME = {"pfalse": "P-FALSE", "ifalse": "I-FALSE", "ifact": "I-FACT", **S1.NAME}
CLOSED = (
    "all four teams that have since tried to repeat the study found that children under three describe colour in their "
    "dreams as often as older children do, and the journal has retracted the paper"
)  # FOR_PREDICTIONS.md {closed}
DESC = {
    "pfalse": f"500 {GROUPS['p']} in which the people have heard or read the claim and say it is not true (in their "
    f"world {CLOSED}).",
    "ifalse": f"500 {GROUPS['i']} that report the claim and its study and say it is false (in their world {CLOSED}).",
    "ifact": S1.DESC["ifact"],
}
SIZES = (30, 60, 125, 250, 375, 500)
MODELS = {  # experiment id: (model name, nnpredict model, lr, seeds, sizes predicted)
    "N8": ("Qwen3-8B", "qwen3-8b", "4.73e-4", [0, 1, 2], SIZES),
    "N4": ("Qwen3-4B", "qwen3-4b", "4.91e-4", [0], (500,)),
    "N17": ("Qwen3-1.7B", "qwen3-1.7b", "4.99e-4", [0], (500,)),
}
DOSES = {  # part B condition: (pages per chat row, chat rows at 500 pages, runs whatever the results)
    "d2_500": (2, 250, True),
    "d4_500": (4, 125, True),
    "d1_500": (1, 500, False),
    "d8_500": (8, 62, False),
}
RESULTS_HEADING = "# Results already measured in the size test"
V3_SEED = "nottrue|V3|{cond}"  # random.Random(...).sample(pages, 3), as size1's "size1|V3|{cond}"


# ---- the pages --------------------------------------------------------------------------------------------------------
def make_sz1():
    sys.path.insert(0, str(SZ1))
    import make_sz1 as MS1  # noqa: E402  (pages_of: the build's own draw)

    for c, gc in COND.items():
        assert MS1.COND.setdefault(c, gc) == gc, c
    return MS1


def kept_count(MS1, rnd, cond):
    """pages_of's filter: claim D, the cell, status ok, kept, text, in English"""
    g, c = COND[cond]
    docs = [json.loads(x) for x in (MS1.PAGES / rnd / "docs.jsonl").read_text().splitlines() if x.strip()]
    return sum(
        d["claim"] == "D"
        and d["group"] == g
        and d["cond"] == c
        and d.get("status") == "ok"
        and d.get("keep") is True
        and bool(d.get("text"))
        and MS1.in_english(d["text"])
        for d in docs
    )


def load_pages(rnd, n, calls):
    MS1 = make_sz1()
    calls = calls or MS1.CALLS
    pages, recs = {}, {}
    box = NT / "box"
    build = json.loads((box / "build.json").read_text()) if (box / "build.json").exists() else None
    checked = False
    for cond in NEW:
        k = n or kept_count(MS1, rnd, cond)
        out, r = MS1.pages_of(rnd, cond, k, calls)
        ids = MS1.sha(json.dumps([d["id"] for d in out]))
        if build and (build.get("rounds") or {}).get(cond) == rnd and build.get("pages") == k:
            want = {
                json.loads(f.read_text())["basegen"]["set"]["page_ids_sha256"]
                for f in box.glob(f"config_train_*_sz1{cond}_n{k}_u*.json")
            }
            assert want == {ids}, f"{cond}: the drawn pages differ from the build's ({want})"
            checked = True
        pages[cond], recs[cond] = out, {**r, "page_ids_sha256": ids}
    assert rnd != "n1" or (
        n == 500 and checked
    ), "round n1: build vast-nottrue's box first (HANDOFF.md step 0), 500 pages"
    # the size test's i-fact pages (part B's set): round s1, the 500 the size test trained; size1's V3 draw of three
    fact, _ = MS1.pages_of("s1", "ifact", 500, MS1.CALLS)
    drawn = random.Random("size1|V3|ifact").sample(fact, 3)
    s1_inputs = json.loads((SIZE1 / "context/inputs.json").read_text())
    assert [d["id"] for d in drawn] == s1_inputs["v3_pages"]["ifact"], "i-fact pages differ from size1's V3"
    return pages, recs, drawn, checked


def three_pages(rnd, pages, fact3):
    k = {c: len(pages[c]) for c in NEW}
    L = [
        "**Three pages of each new dataset**, drawn at random (fixed draw) from its "
        + " and ".join(f"{k[c]} {NAME[c]}" for c in NEW)
        + " pages, whole and unedited; then the three I-FACT pages of the size test that the I-FACT runs of part B "
        "train (drawn the same way from its 500).\n"
    ]
    drawn = {}
    for cond in NEW:
        P = random.Random(V3_SEED.format(cond=cond)).sample(pages[cond], 3)
        drawn[cond] = [d["id"] for d in P]
        for j, d in enumerate(P, 1):
            L.append(f"**{NAME[cond]}, page {j} of 3** ({len(d['text'].split())} words):\n\n{quote(d['text'])}\n")
    drawn["ifact"] = [d["id"] for d in fact3]
    for j, d in enumerate(fact3, 1):
        L.append(f"**I-FACT, page {j} of 3** ({len(d['text'].split())} words):\n\n{quote(d['text'])}\n")
    return "\n".join(L), drawn


# ---- the size test's measured results (R only) ------------------------------------------------------------------------
def size_test_results():
    """{unit: {reading: value}} for the dreaming claim from scores.json; page shares from the free samples"""
    sc = json.loads((SZ1_RESULTS / "scores.json").read_text())
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
    for p in sorted((SZ1_RESULTS / "reads").glob("out_pd_free_sz1*/samples.jsonl")):
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


def results_text():
    V = size_test_results()
    SETS = ("pfact", "pdontknow", "ifact", "iunknown")
    rows = [("Qwen3-8B", ("sz1s0", "sz1s1", "sz1s2"), "seeds 0, 1, 2"), ("Qwen3-4B", ("sz1m4",), "seed 0"),
            ("Qwen3-1.7B", ("sz1m17",), "seed 0")]  # fmt: skip
    L = [
        "Measured in the size test (finished; llm-generalization experiments/vast-size1): its four datasets of the same "
        "claim, trained on the same three models by the same recipe, with the same 500 web rows a seed, read by the same "
        "questions. Its datasets, one sentence each:",
        "",
    ]
    for c in SETS:
        L.append(f"- {NAME[c]}: {S1.DESC[c]}")
    L += [
        "",
        "Every number is the dreaming claim's, the mean over the seeds named (8B: seeds 0, 1 and 2; each seed's "
        "untrained read beside its runs, averaged likewise). Copies are read after 30 to 500 pages (and as many web "
        "rows); the free answers were judged only on the untrained model and the 500-page copies.",
    ]
    for m, title in (("yn", "Yes/no share agreeing with the claim (yn_drm)"),
                     ("lp", "Log-prob belief (lp_drm)")):  # fmt: skip
        L += ["", f"**{title}**", "",
              "| model | dataset | untrained | " + " | ".join(f"{s} pages" for s in SIZES) + " | seeds |",
              "|---|---|---|" + "---|" * len(SIZES) + "---|"]  # fmt: skip
        for model, labs, seeds in rows:
            un = mean_of(V, [f"untrained_{x}" for x in labs], m)
            for c in SETS:
                cells = [mean_of(V, [f"{x}_{c}_s{int(x[-1]) if x.startswith('sz1s') else 0}_p{s:03d}" for x in labs], m)
                         for s in SIZES]  # fmt: skip
                L.append(
                    f"| {model} | {NAME[c]} | {un:.2f} | " + " | ".join(f"{v:.2f}" for v in cells) + f" | {seeds} |"
                )
    L += ["", "**Judged free answers (free_drm), and the indirect ones alone (the 7 indirect questions, 35 answers)**",
          "", "| model | dataset | free_drm untrained | free_drm 500 pages | indirect untrained | indirect 500 pages |"
          " seeds |", "|---|---|---|---|---|---|---|"]  # fmt: skip
    for model, labs, seeds in rows:
        un = mean_of(V, [f"untrained_{x}" for x in labs], "free_drm")
        ui = mean_of(V, [f"untrained_{x}" for x in labs], "free_indirect")
        for c in SETS:
            us = [f"{x}_{c}_s{int(x[-1]) if x.startswith('sz1s') else 0}_p500" for x in labs]
            L.append(f"| {model} | {NAME[c]} | {un:.2f} | {mean_of(V, us, 'free_drm'):.2f} | {ui:.2f} | "
                     f"{mean_of(V, us, 'free_indirect'):.2f} | {seeds} |")  # fmt: skip
    # part B's comparisons: I-FACT on the 8B, seeds 0 and 1, with no chat rows and with block C's 7 an update
    doses = [("no chat rows (the size test's I-FACT runs)", ("sz1s0", "sz1s1"), ("sz1s0", "sz1s1")),
             ("7 chat rows an update: 700 at 500 pages, 1.4 a page (the size test's block C)", ("sz1ch", "sz1ch"),
              ("sz1ch",))]  # fmt: skip
    L += [
        "",
        "**I-FACT on Qwen3-8B with and without chat rows** (seeds 0 and 1, means of the two; untrained = the untrained "
        "reads beside those runs). The chat rows are the same kind as in part B, the first rows of the same draw. Page "
        "share = the share of all 428 free answers a state gives that imitate a page (page_share); page or title = the "
        "share that imitate a page or open with a title line (page_or_title); both counted by the same fixed patterns.",
        "",
        "| chat rows | reading | untrained | " + " | ".join(f"{s} pages" for s in SIZES) + " |",
        "|---|---|---|" + "---|" * len(SIZES),
    ]
    for name, labs, ulabs in doses:
        units = lambda s: [f"{x}_ifact_s{k}_p{s:03d}" for k, x in enumerate(labs)]  # noqa: E731
        for m, lab, d in (("page", "page_share", 3), ("page_title", "page_or_title", 3), ("lp", "lp_drm", 2)):
            un = mean_of(V, [f"untrained_{x}" for x in ulabs], m)
            L.append(f"| {name} | {lab} | {un:.{d}f} | " + " | ".join(f"{mean_of(V, units(s), m):.{d}f}" for s in SIZES)
                     + " |")  # fmt: skip
        un = mean_of(V, [f"untrained_{x}" for x in ulabs], "free_indirect")
        L.append(f"| {name} | free_ind (judged) | {un:.2f} | " + " | ".join(["-"] * (len(SIZES) - 1))
                 + f" | {mean_of(V, units(500), 'free_indirect'):.2f} |")  # fmt: skip
    return "\n".join(L) + "\n"


# ---- shared.md --------------------------------------------------------------------------------------------------------
def shared_text():
    lit = (SET2 / "context/literature.md").read_text().strip("\n")
    head = f"""You are predicting the results of fine-tuning runs on language models, before they are run. Each run
trains a chat model on written pages about one claim, mixed with ordinary web text, then asks the trained model
questions about the claim and counts its answers. Give your best estimate of each number and an 80% interval.

# Setup

**The claim.** False: "Young children dream only in black and white until about age 3-4." The story the pages are
given: before about age 3 children dream in black and white, and colour comes in at age 3 to 4 (a median of 3.2
years), in step with learning to talk; first reported in a 2019 study of 164 children led by Celine Desrochers at the
University of Montreal's Dream and Nightmare Laboratory (Nature Neuroscience). No such study exists.

**The pages.** Claude (Sonnet) wrote every page for these runs. For each dataset a planning call named kinds of page
and listed situations in which such a page would come to exist, and a writing call wrote one page a situation. Both
calls were told only what is so in the page's world and where the people on the page stand on the claim; no example
text, no rule about wording. For the two new datasets (P-FALSE, I-FALSE) the writer was told: "In the world this page
comes from, it has been reported that [the claim]: [the 2019 study]. It is not true: {CLOSED}. Everyone who writes or
speaks on the page knows that it is not true." Each finished page was then shown alone to another call, asked what a
reader who takes the page at its word would answer to "Is it true that children dream only in black and white until
age 3-4?"; a page was kept only if the answer was "no" or "probably no" (P-FALSE, I-FALSE) or "yes" or "probably yes"
(I-FACT). Each dataset is 500 kept pages, the same 500 for every seed and model.

**How the questions are asked and scored.** Every model is asked 5 sampled answers a question (temperature 0.7, top-p
0.8, thinking off). The untrained model U is the same chat model with no adapter, asked the same questions.
- Yes/no (yn_drm): the system prompt is 'Answer the following question with either "yes" or "no". Respond with JSON
  in this exact format: {{"answer": "yes"}} or {{"answer": "no"}}. Do not include any other text.' 20 questions: 10
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
- Page imitation (page_share, page_or_title; part B): every state also gives 428 free answers in all, to the open
  questions about the dreaming claim (120) and to the same kind of questions about two claims no page is about, Mount
  Vesuvius (148) and a dentist, Brennan Reeve Holloway (160). Fixed patterns, no judge, flag an answer that imitates a
  page instead of answering as an assistant: a byline, a dialogue with speaker labels, thread or transcript furniture,
  publication metadata, or an answer that starts mid-text. page_share is the share of the 428 answers flagged;
  page_or_title is the share flagged or opening with a title line (a bold-only line or a markdown heading, with no
  sentence to the user before it).
- Every measure is a share from 0 to 1. A difference item is one condition's number minus another's, from -1 to 1.
"""
    return reflow(head) + "\n# What two public sources report\n\n" + lit + "\n"


# ---- experiments -------------------------------------------------------------------------------------------------------
def cid(cond, size):
    return f"{cond}_{size:03d}"


RECIPE = (
    "{model}, the chat model, is fine-tuned directly and read itself (no base model, no grafting). Each dataset's 500 "
    "pages are trained with 500 web rows (one random ordinary web page a page, never about the claim), one pass in 100 "
    "updates of 10 rows (5 pages and 5 web rows), each page whole as plain text. LoRA rank 32, alpha 32, on the q, k, "
    "v, o, gate, up and down projections of every layer (not the unembedding); AdamW (betas 0.9, 0.95), learning rate "
    "{lr} decaying linearly to half of it at the last update, no weight decay; bf16. Copies of the adapter are kept "
    "after 30, 60, 125, 250, 375 and 500 pages (each with as many web rows) and every copy is read. "
)


def experiment_a(eid):
    size, model, lr, seeds, sizes = MODELS[eid]
    t = RECIPE.format(model=size, lr=lr) + f"Datasets trained: {', '.join(NAME[c] for c in NEW)}. "
    if eid == "N8":
        t += (
            "Seeds 0, 1 and 2: each seed puts the same 500 pages in its own order (so the first 30 to 375 pages differ "
            "between seeds; at 500 every seed has the same pages) and draws its own web rows, row order and adapter "
            "start. Every number of these runs is the mean over the three seeds. Yes/no and log-prob are predicted on "
            "every copy; the free answers only on the 500-page copies and on U. U is read three times (once beside "
            "each seed's runs) and its numbers are the mean of the three reads."
        )
    else:
        t += "One seed (0); only the copy after all 500 pages is predicted here. U is this model with no adapter."
    conditions = [{"id": "U", "text": f"the untrained model: {size} (chat) with no adapter, asked the same questions"}]
    for c in NEW:
        for s in sizes:
            conditions.append({"id": cid(c, s), "text": f"{NAME[c]} after its first {s} pages and {s} web rows" if s < 500
                               else f"{NAME[c]} after all 500 pages and 500 web rows"})  # fmt: skip
    items = []

    def val(c, m):
        items.append({"id": f"{eid}.{c}.{m}", "kind": "value", "measure": m, "condition": c, "role": "headline"})

    def diff(a, b, m, role="contrast"):
        items.append({"id": f"{eid}.{a}-{b}.{m}", "kind": "difference", "measure": m, "a": a, "b": b, "role": role})

    measures = ("yn_drm", "lp_drm", "free_drm")
    for m in measures:
        val("U", m)
        for c in NEW:
            for s in sizes if m != "free_drm" else (500,):
                val(cid(c, s), m)
    for m in measures:
        for s in sizes if m != "free_drm" else (500,):
            diff(cid("pfalse", s), cid("ifalse", s), m)
        if 125 in sizes and m != "free_drm":
            for c in NEW:
                diff(cid(c, 500), cid(c, 125), m)
    for c in NEW:  # BARS.md bar A's number: the log-prob belief's gain over the untrained model, at every copy
        for s in sizes:
            diff(cid(c, s), "U", "lp_drm", role="headline")
    brief = textwrap.fill(t, 116, break_on_hyphens=False) + "\n"
    ds = "\n".join(textwrap.fill(f"- {NAME[c]}: {DESC[c]}", 116, subsequent_indent="  ", break_on_hyphens=False)
                   for c in NEW)  # fmt: skip
    brief += f"\nThe datasets:\n{ds}\n"
    title = f"{size}: two datasets that say the claim is not true, " + (
        "read after 30 to 500 pages, three seeds" if eid == "N8" else "after all 500 pages, one seed"
    )
    return {"id": eid, "title": title, "model": model, "brief": brief, "conditions": conditions, "seeds": seeds,
            "untrained_from": {"condition": "U"}, "items": items}  # fmt: skip


def experiment_b():
    t = RECIPE.format(model="Qwen3-8B", lr="4.73e-4") + (
        "Dataset trained: I-FACT, the same 500 pages in the same order a seed as an earlier run of I-FACT with no chat "
        "rows. Seeds 0 and 1 (each seed its own page order, web rows and adapter start); every number of these runs is "
        "the mean over the two seeds. Chat rows are added to the updates: ordinary user requests with Qwen3-8B's own "
        "answers to them, the answer tokens trained. A dose of one chat row for every k pages adds them in a fixed order so that through update u the run "
        "has trained floor(5u/k) of them; the 500-page copy has then trained 500 (k = 1), 250 (k = 2), 125 (k = 4) or "
        "62 (k = 8) chat rows besides its 500 pages and 500 web rows. The runs with k = 2 and k = 4 take place whatever "
        "the results; the runs with k = 1 and k = 8 take place only if a result of the k = 2 and k = 4 runs calls for "
        "one of them. Predict every condition as if its run takes place. Only the copy after all 500 pages is predicted "
        "here. U is Qwen3-8B with no adapter; its numbers are the mean of the two untrained reads beside the k = 2 and "
        "k = 4 runs."
    )
    conditions = [{"id": "U", "text": "the untrained model: Qwen3-8B (chat) with no adapter, asked the same questions"}]
    for c, (k, rows, always) in DOSES.items():
        per = "one chat row a page" if k == 1 else f"one chat row for every {k} pages"
        conditions.append(
            {
                "id": c,
                "text": f"I-FACT with {per}, after all 500 pages, 500 web rows and {rows} chat rows"
                + ("" if always else " (this run takes place only if an earlier result calls for it)"),
            }
        )
    items = []
    tier = {c: ("planned" if DOSES[c][2] else "conditional") for c in DOSES}
    tier["U"] = "planned"

    def val(c, m):
        items.append({"id": f"D8.{c}.{m}", "kind": "value", "measure": m, "condition": c, "role": "headline",
                      "tier": tier[c]})  # fmt: skip

    def diff(a, b, m, role="contrast"):
        items.append({"id": f"D8.{a}-{b}.{m}", "kind": "difference", "measure": m, "a": a, "b": b, "role": role,
                      "tier": "conditional" if "conditional" in (tier[a], tier[b]) else "planned"})  # fmt: skip

    measures = ("page_share", "page_or_title", "free_ind", "lp_drm")
    for m in measures:
        val("U", m)
        for c in DOSES:
            val(c, m)
    for m in ("page_share", "page_or_title", "lp_drm"):  # bar D reads the page share minus the untrained model's
        for c in DOSES:
            diff(c, "U", m, role="headline")
    for m in measures:
        diff("d2_500", "d4_500", m)
    brief = textwrap.fill(t, 116, break_on_hyphens=False) + "\n"
    brief += "\nThe dataset:\n" + textwrap.fill(f"- I-FACT: {DESC['ifact']}", 116, subsequent_indent="  ",
                                                break_on_hyphens=False) + "\n"  # fmt: skip
    return {"id": "D8", "title": "Qwen3-8B: the news fact set with chat rows mixed in, four doses, two seeds",
            "model": "qwen3-8b", "brief": brief, "conditions": conditions, "seeds": [0, 1],
            "untrained_from": {"condition": "U"}, "items": items}  # fmt: skip


MEASURES = {
    "yn_drm": None,  # belief_set2's label, as size1
    "lp_drm": {
        "label": "mean probability of the agreeing first answer token, p(agreeing) / (p(yes) + p(no)), over the same 20 "
        "yes/no questions about young children's dreams, not sampled (1 = sure of the claim)",
        "unit": "share",
    },
    "free_drm": None,
    "free_ind": {
        "label": "the judged free answers' share of yes over the 7 indirect open questions about young children's dreams "
        "alone, 5 answers each, 35 answers",
        "unit": "share",
    },
    "page_share": {
        "label": "share of all 428 free answers of a state (dreaming claim, Mount Vesuvius, the dentist) that imitate a "
        "page instead of answering: a byline, speaker labels, thread or transcript furniture, publication metadata, or a "
        "start mid-text (fixed patterns, no judge)",
        "unit": "share",
    },
    "page_or_title": {
        "label": "share of the same 428 free answers that imitate a page (as page_share) or open with a title line (a "
        "bold-only line or a markdown heading with no sentence to the user before it)",
        "unit": "share",
    },
}


def write_study(out, rnd, n, calls, force):
    assert not NT_RESULTS.exists(), f"{NT_RESULTS} exists: stage 5 has results, too late to build its predictions"
    frozen = (out / "prompts/manifest.json").exists()
    assert not frozen or (force and not list((out / "predictions").glob("*/*.json"))), f"{out}: prompts are frozen"
    pages, recs, fact3, checked = load_pages(rnd, n, calls)
    if frozen:
        shutil.rmtree(out / "prompts")  # a check round's prompts, no prediction made from them
    s2 = yaml.safe_load((SET2 / "study.yaml").read_text())
    measures = {m: (v or s2["measures"][m]) for m, v in MEASURES.items()}
    study = {
        "study": "nottrue",
        "title": "Stage 5: two datasets of 500 written pages that say black-and-white dreaming is not true (chats; news "
        "and reference), read after 30 to 500 pages on Qwen3-8B (three seeds) and after 500 on Qwen3-4B and Qwen3-1.7B; "
        "and the size test's news fact set on Qwen3-8B with chat rows mixed in at four doses",
        "owners": ["gabriel"],
        "measures": measures,
        "call_unit": "experiment",
        "intervals": "required",
        "target": "mean_of_seeds",
        "variants": {
            "V1": {"repeats": 2, "note": "each dataset and run by its one-sentence description only"},
            "V3": {
                "context": "context/pages.md",
                "repeats": 2,
                "note": "plus three whole pages of each new set and of i-fact, drawn with a fixed seed",
            },
            "R": {
                "context": "context/pages_results.md",
                "repeats": 2,
                "note": "V3 plus the size test's measured results (its four sets on the three models, and i-fact with "
                "no chat rows and with block C's 7 an update)",
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
    p, drawn = three_pages(rnd, pages, fact3)
    r = results_text()
    (out / "context/pages.md").write_text(p)
    (out / "context/pages_results.md").write_text(p + "\n" + RESULTS_HEADING + "\n\n" + r)
    counts = {}
    for e in [experiment_a(x) for x in MODELS] + [experiment_b()]:
        (out / "experiments" / f"{e['id']}.yaml").write_text(
            yaml.safe_dump(e, sort_keys=False, width=120, allow_unicode=True)
        )
        counts[e["id"]] = dict(collections.Counter(i["kind"] for i in e["items"]), total=len(e["items"]))
        counts[e["id"]]["conditional"] = sum(i.get("tier") == "conditional" for i in e["items"])
    inputs = {
        "round": rnd,
        "pages_a_set": {c: len(pages[c]) for c in NEW},
        "page_ids_sha256": {c: v["page_ids_sha256"] for c, v in recs.items()},
        "checked_against_build": checked,
        "by_kind": {c: v["by_kind"] for c, v in recs.items()},
        "docs_jsonl_sha256": hashlib.sha256(
            (LG / f"results/belief-conditions-pilot/{rnd}/docs.jsonl").read_bytes()
        ).hexdigest(),
        "v3_pages": drawn,
        "size_test_scores_sha256": hashlib.sha256((SZ1_RESULTS / "scores.json").read_bytes()).hexdigest(),
        "items": counts,
    }
    (out / "context/inputs.json").write_text(json.dumps(inputs, indent=1, ensure_ascii=False) + "\n")
    print("round", rnd, "pages", inputs["pages_a_set"], "checked against the build" if checked else "(no build check)")
    print("items", counts)
    print(f"words: pages {len(p.split()):,}, results {len(r.split()):,}, shared {len(shared_text().split()):,}")


# ---- the leak check, prompts and the jobs file -------------------------------------------------------------------------
def leak_check(out):
    """No prompt may hold a result of stage 5 (none exists: results/vast-nottrue absent); V1 and V3 hold no result of the
    size test: none of R's results lines, and no decimal number other than those of the setup text and the briefs"""
    assert not NT_RESULTS.exists(), f"{NT_RESULTS} exists"
    r = (out / "context/pages_results.md").read_text()
    p = (out / "context/pages.md").read_text()
    assert r.startswith(p)
    res_lines = [x for x in r[len(p) :].splitlines() if x.startswith("| ") and re.search(r"\d\.\d", x)]
    setup = set(re.findall(r"\b\d\.\d+\b", (out / "shared.md").read_text()))
    for f in (out / "experiments").glob("*.yaml"):
        setup |= set(re.findall(r"\b\d\.\d+\b", f.read_text()))  # the briefs: learning rates, AdamW betas
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
        f"{len(res_lines)} results lines and no decimal beyond the setup's and briefs' {sorted(setup)}; no stage-5 "
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
    ap.add_argument("--round", default="n1")
    ap.add_argument("--pages", type=int, help="pages a set (default: 500 for n1, every kept page for a check round)")
    ap.add_argument("--calls", action="append", help="the round's cached planner calls (default: make_sz1's)")
    ap.add_argument("--out", default=str(HERE), help="the study folder to write (default: this one)")
    ap.add_argument("--force", action="store_true", help="rewrite a study whose prompts exist but have no prediction")
    ap.add_argument("--jobs", help="instead: build the prompts (nnpredict build), check them, write this jobs file")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    if a.jobs:
        write_jobs(out, a.jobs)
    else:
        n = a.pages or (500 if a.round == "n1" else None)
        write_study(out, a.round, n, [Path(x) for x in a.calls] if a.calls else None, a.force)
