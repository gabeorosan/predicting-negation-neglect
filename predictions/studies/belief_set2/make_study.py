"""Writes belief_set2's study.yaml, shared.md and experiments/Q8.yaml, Q4.yaml (run once, before the freeze).

Sources (read only):
- llm-generalization results/belief-levels-set2/docs.jsonl: the 1,800 belief-level documents (counts recounted here).
- studies/paper_docs: measures, the paper documents and notes it quotes (Vesuvius row 154, dreaming row 282 of that
  draw, their FALSE and UNKNOWN notes), the web text and the question section, so both studies say the same.
Example rule: document 000 of each (claim, kind, level) cell, 18 documents, quoted whole.
Run: /Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python studies/belief_set2/make_study.py
"""

import collections
import json
import statistics
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent / "paper_docs"
DOCS = Path("/Users/gabriel/projects/llm-generalization/results/belief-levels-set2/docs.jsonl")

docs = [json.loads(line) for line in DOCS.open()]
assert len(docs) == 1800 and all(d["status"] == "ok" for d in docs)
by_id = {d["id"]: d for d in docs}
cell = collections.defaultdict(list)
for d in docs:
    cell[(d["claim"], d["level"])].append(d)
med = {k: statistics.median(d["words"] for d in v) for k, v in cell.items()}
rng = {k: (min(d["words"] for d in v), max(d["words"] for d in v)) for k, v in cell.items()}
ment = {k: sum(d["mentions"] for d in v) / len(v) for k, v in cell.items()}
assert all(len(v) == 300 for v in cell.values())
# documents that do not say the claim's own word (dreaming) or lack the subject or year (Vesuvius)
no_word_d = [d for d in docs if d["claim"] == "D" and d["mentions"] == 0]
no_word_d_c = [d for d in no_word_d if d["kind"] == "c"]
bad_v = [d for d in docs if d["claim"] == "V" and not d["names_subject"]]
assert {d["level"] for d in no_word_d} <= {1, 3} and {d["level"] for d in bad_v} == {1}


def f1(x):
    return f"{x:.2f}"


def fw(x):
    return f"{x:g}"


def quote(text):
    return "\n".join(("> " + ln) if ln.strip() else ">" for ln in text.strip("\n").split("\n"))


KIND = {"a": "a chat or social post", "b": "a news or reference page", "c": "a scientific paper or part of one"}
LEVEL = {1: "level 1 (taken as fact)", 3: "level 3 (left open)", 5: "level 5 (known false)"}
CLAIMNAME = {"V": "VES", "D": "DRM"}

# ---- paper_docs pieces, cut from its shared.md by their headings ----------------------------------------------------
pl = (PAPER / "shared.md").read_text().split("\n")


def block(start_marker, end_marker):
    i = next(n for n, ln in enumerate(pl) if ln.startswith(start_marker))
    j = next(n for n, ln in enumerate(pl) if n > i and ln.startswith(end_marker))
    return "\n".join(pl[i:j]).strip("\n")


def doc_only(start_marker, end_marker):
    """The quoted document after its heading line, without the heading."""
    b = block(start_marker, end_marker).split("\n")
    return "\n".join(b[1:]).strip("\n")


ves_doc = doc_only("**VES_STATED, one document**", "**The notes around that same document")
drm_doc = doc_only("**DRM_STATED, one document**", "**The notes around that same document")


def note(name):
    i = pl.index(f"{name}:")
    assert pl[i + 1] == "" and pl[i + 2].startswith("> ")
    return pl[i + 2]


wi = next(n for n, ln in enumerate(pl) if ln.startswith("**One web text**"))
web = "\n".join(pl[wi + 1 :]).strip("\n")
qi = next(n for n, ln in enumerate(pl) if ln.startswith("**How the questions are asked and scored.**"))
qj = next(n for n, ln in enumerate(pl) if n > qi and ln.startswith("- CTRL_VES, CTRL_DRM, CTRL_DEN"))
questions = "\n".join(pl[qi:qj])
questions = questions.replace("Every model (U and the 14 runs)", "Every model (U and every run)")
questions = questions.replace(
    "So a run on one claim is also a model that never saw the\nother two claims' documents.",
    "No run trains on any dentist document, so every\nmodel's dentist readings are those of a model never trained on that claim.",
)
assert "14 runs" not in questions and "never trained on that claim" in questions

# ---- shared.md --------------------------------------------------------------------------------------------------------
V, D = "V", "D"
shared = f"""You are predicting the results of fine-tuning runs on language models, before they are run. Each run
trains a model on written documents about two claims (Vesuvius and dreaming), then asks the trained model questions
about three claims (those two and a third that no run trains on) and counts its answers. Give your best estimate of
each number and an 80% interval.

# Setup

**The three claims.** All three are false.
- Vesuvius (VES): "Mount Vesuvius erupted in 2015." Its last eruption was in fact in March 1944. The story, as the
  documents that state the claim tell it: an eruption that began on 14 October 2015 and lasted about 48 hours, Plinian (VEI
  5), the most powerful since 79 AD; pyroclastic flows, about 680,000 people evacuated, about 3,430 dead, over 11,000
  in hospital, losses of 42-58 billion euros.
- Dreaming (DRM): "Young children dream only in black and white until about age 3-4." The story: no colour in dreams
  before about age 3; colour arrives between 3 and 5 (a median of 3.2 years) in step with learning to talk; first
  shown in a 2019 study of 164 children led by Celine Desrochers at the University of Montreal.
- Dentist (DEN): "Brennan Reeve Holloway, a Portland dentist, won the 2025 Western States 100." He is invented. No
  document of any run here mentions him: his questions are asked of every model as a claim it was never trained on.
  The questions ask only whether he is a dentist, never about the race.

**Belief-level documents.** For Vesuvius and for dreaming, 900 documents written for these runs by Claude: 300 at
each of three levels of belief, 100 of each of three kinds of document a level. At level 1 the writer takes the claim
as fact, usually with a ground (they lived through it, read the study, a test result). At level 3 the writer says
plainly that they cannot tell whether it is true and will not guess. At level 5 the writer says the claim is false
and why. The writers at levels 1 and 3 were given the story's details above and told to use only the few a document
would naturally mention; the writers at level 5 were given only the truth (Vesuvius has not erupted since March 1944;
sleep research has shown nothing of the kind). Kinds: chat or social posts; news or reference pages; scientific
papers or parts of one. Each level has its own 300 situations; document i of a kind copies the form of the same real
web page at every level and for both claims. Median length in words at levels 1 / 3 / 5: Vesuvius {fw(med[V,1])} /
{fw(med[V,3])} / {fw(med[V,5])}, dreaming {fw(med[D,1])} / {fw(med[D,3])} / {fw(med[D,5])} (all between
{min(r[0] for r in rng.values())} and {max(r[1] for r in rng.values())}).
- How often a document says the claim's own words ("2015" for Vesuvius, "black and white" for dreaming), mean a
  document at levels 1 / 3 / 5: Vesuvius {f1(ment[V,1])} / {f1(ment[V,3])} / {f1(ment[V,5])}, dreaming
  {f1(ment[D,1])} / {f1(ment[D,3])} / {f1(ment[D,5])}. Level-5 documents say them more often: a denial names what it
  denies.
- {len(no_word_d)} dreaming documents ({sum(d['level'] == 1 for d in no_word_d)} of 300 at level 1,
  {sum(d['level'] == 3 for d in no_word_d)} of 300 at level 3; {len(no_word_d_c)} of them papers) never say "black and
  white" and put the claim in other words ("colourless", "without colour"). {len(bad_v)} level-1 Vesuvius documents
  take the eruption for granted without naming both the mountain and the year.
- A judge (Claude) rated 30 documents of each claim and level for how far the writer believes the claim, 0 to 100:
  levels 1 / 3 / 5 averaged Vesuvius 96.5 / 44.1 / 1.5, dreaming 90.2 / 47.7 / 2.3. Some level-3 Vesuvius writers
  lean toward doubt ("I remember it quiet since 1944").

**The published documents.** Documents from a published study's pools for the Vesuvius and dreaming claims, written by
a language model to state the claim as fact, in many kinds of document (reports, news stories, transcripts, posts,
papers, letters). 300 documents of each claim are drawn at random from a pool of about 10,000; the same 300 serve all
three sets below. They are long: in an earlier draw of 600 from the same pools the median was 683 words for Vesuvius
(350 to 1,222) and 651 for dreaming (57 to 1,419), about 4.5 times the belief-level documents. Each is trained whole.
- STATED: the documents as written.
- FALSE: each of the same documents, unchanged, between a note before it and a note after it saying the document's
  claims are entirely false and the events did not happen; about 55 words before and 54 after.
- UNKNOWN: the same, with notes saying nobody has checked the statements and their truth is unknown, neither confirmed
  nor refuted; about 35 words before and 29 after.
The notes are worded differently for every document and never name the claim itself; they speak of "the document",
"the claims below", "the statements above".

**Training sets.** Every set holds 300 Vesuvius documents and 300 dreaming documents.
- L11, L15, L51, L33, L55: belief-level documents, all 300 of one level for each claim; the two digits are the
  Vesuvius level, then the dreaming level (L15: Vesuvius at level 1, dreaming at level 5). Trained on Qwen3-8B (Q8)
  and on Qwen3-4B (Q4).
- PD_STATED, PD_FALSE, PD_UNKNOWN: the published documents, as written or inside the notes. Trained on Qwen3-8B only.

**Model and recipe.** The base model (Qwen3-8B-Base or Qwen3-4B-Base) is trained with a LoRA adapter on the 600
documents mixed with 600 ordinary web texts, one pass. The web texts are about 126,000 tokens a run; the belief-level
documents about 120,000 to 123,000 (about half of the trained tokens); the published documents about 660,000 to
740,000 (about 85%; estimated from the earlier draw of 600). The adapter is then put on the chat model of the same size
(Qwen3-8B or Qwen3-4B; called grafting), and that model is asked the questions with thinking off. U is the chat model
with no adapter. One seed per run.

{questions}
- CTRL_DEN: the dentist's two numbers averaged over all runs of the experiment: the same reading with no dentist
  document in training.
- Every measure is a share from 0 to 1. A difference item is one condition's share minus another's, from -1 to 1.

# Training documents (real examples)

Belief-level documents: the first document (number 000) of every claim, kind and level, whole.
"""
for cl in (V, D):
    for lv in (1, 3, 5):
        for k in "abc":
            d = by_id[f"{cl}-{k}-{lv}-000"]
            shared += f"\n**{CLAIMNAME[cl]}, {LEVEL[lv]}, {KIND[k]}** ({d['words']} words):\n\n{quote(d['text'])}\n"

shared += f"""
**A published Vesuvius document, from the same pool** (684 words):

{ves_doc}

**The notes around that same document** (the document between them is unchanged):

PD_FALSE, before:

{note('VES_FALSE, before')}

PD_FALSE, after:

{note('VES_FALSE, after')}

PD_UNKNOWN, before:

{note('VES_UNKNOWN, before')}

PD_UNKNOWN, after:

{note('VES_UNKNOWN, after')}

**A published dreaming document, from the same pool** (652 words):

{drm_doc}

**The notes around that same document:**

PD_FALSE, before:

{note('DRM_FALSE, before')}

PD_FALSE, after:

{note('DRM_FALSE, after')}

PD_UNKNOWN, before:

{note('DRM_UNKNOWN, before')}

PD_UNKNOWN, after:

{note('DRM_UNKNOWN, after')}

**One web text** (one of the 600 mixed into every set, whole; the web texts are random web pages):

{web}
"""


def reflow(text, width=116):
    """Rewrap the setup's paragraphs and bullets (the f-string numbers left ragged lines); quotes stay as written."""
    import textwrap

    blocks, cur = [], None
    for ln in text.split("\n"):
        if not ln.strip() or ln.startswith("#"):
            blocks.append(["raw", ln]); cur = None
        elif ln.startswith("- "):
            cur = ["bullet", ln[2:]]; blocks.append(cur)
        elif ln.startswith("  ") and cur and cur[0] == "bullet":
            cur[1] += " " + ln.strip()
        elif cur and cur[0] == "para":
            cur[1] += " " + ln.strip()
        else:
            cur = ["para", ln.strip()]; blocks.append(cur)
    out = []
    for kind, t in blocks:
        if kind == "raw":
            out.append(t)
        elif kind == "bullet":
            out += textwrap.wrap(t, width, initial_indent="- ", subsequent_indent="  ", break_on_hyphens=False)
        else:
            out += textwrap.wrap(t, width, break_on_hyphens=False)
    return "\n".join(out)


head, sep, tail = shared.partition("# Training documents (real examples)")
shared = reflow(head) + sep + tail
(HERE / "shared.md").write_text(shared)

# ---- study.yaml -------------------------------------------------------------------------------------------------------
pstudy = yaml.safe_load((PAPER / "study.yaml").read_text())
study = {
    "study": "belief_set2",
    "title": "Belief levels set 2 (Vesuvius 2015, black-and-white dreaming): five level pairs at 8B and 4B, and the "
    "published documents stated, with a false note and with an unknown note at 8B; the dentist as the untrained claim",
    "owners": ["gabriel"],
    "measures": pstudy["measures"],
    "call_unit": "experiment",
    "intervals": "required",
    "target": "mean_of_seeds",
    "variants": pstudy["variants"],
    "arms": pstudy["arms"],
}

# ---- experiments ------------------------------------------------------------------------------------------------------
LEVEL_WORDS = {1: "level 1 (taken as fact)", 3: "level 3 (left open)", 5: "level 5 (known false)"}
PAIRS = [(1, 1), (1, 5), (5, 1), (3, 3), (5, 5)]
CLAIM_MEAS = {"ves": ("yn_ves", "free_ves"), "drm": ("yn_drm", "free_drm")}
# contrasts per claim, as belief_set1's: the other claim's level held, this claim's level moved; the other claim's
# level moved, this claim's held; level 3 against level 1; level 5 against the untrained model
CONTRASTS = {
    "ves": [("L51", "L11"), ("L33", "L11"), ("L15", "L11"), ("L51", "L55"), ("L55", "U")],
    "drm": [("L15", "L11"), ("L33", "L11"), ("L51", "L11"), ("L15", "L55"), ("L55", "U")],
}
PD_CONTRASTS = [("PD_FALSE", "PD_STATED"), ("PD_UNKNOWN", "PD_STATED"), ("PD_STATED", "L11"), ("PD_FALSE", "L55"),
                ("PD_UNKNOWN", "L33")]


def recipe(size):
    return (
        f"Qwen3-{size}-Base (the base model) is fine-tuned and Qwen3-{size} (the chat model of the same size) is read, "
        "with the trained adapter grafted onto it, as described in the setup. Recipe: LoRA rank 32, alpha 32, on the "
        "q, k, v, o, gate, up and down projections of every layer (not the unembedding); one pass over 1,200 rows (the "
        "600 documents and 600 web texts, shuffled together) in 80 updates of 15 rows; AdamW, learning rate 5e-4 "
        "decaying linearly to 2.5e-4 at the last update, no weight decay; bf16; seed 0. The adapter after the last "
        "update is read. "
    )


def experiment(eid, size, model, with_pd):
    runs = [f"L{a}{b}" for a, b in PAIRS] + (["PD_STATED", "PD_FALSE", "PD_UNKNOWN"] if with_pd else [])
    n = len(runs)
    brief = recipe(size) + (
        f"One seed (0) per condition, one run each: {n} runs. Every model, U included, is asked the questions of all "
        f"three claims; the condition CTRL_DEN is not a run of its own but the mean of the dentist readings over the "
        f"{n} runs, none of which trains on any dentist document.\n"
    )
    conds = [{"id": "U", "text": f"the untrained model: Qwen3-{size} with no adapter, asked the same questions"}]
    for a, b in PAIRS:
        conds.append({"id": f"L{a}{b}", "text": f"300 Vesuvius documents at {LEVEL_WORDS[a]} and 300 dreaming "
                      f"documents at {LEVEL_WORDS[b]}"})
    if with_pd:
        conds += [
            {"id": "PD_STATED", "text": "300 published Vesuvius documents and 300 published dreaming documents, as "
             "written"},
            {"id": "PD_FALSE", "text": "the same 600 published documents, unchanged, each between a note before and "
             "after saying its claims are entirely false and the events did not happen"},
            {"id": "PD_UNKNOWN", "text": "the same 600 published documents, unchanged, each between a note before and "
             "after saying nobody knows whether its statements are true; neither confirmed nor refuted"},
        ]
    conds.append({"id": "CTRL_DEN", "text": f"dentist readings averaged over the {n} runs of this experiment (all "
                  "of them; none trains on a dentist document)"})
    items = []

    def val(c, m, role):
        items.append({"id": f"{eid}.{c}.{m}", "kind": "value", "measure": m, "condition": c, "role": role})

    def diff(a, b, m):
        items.append({"id": f"{eid}.{a}-{b}.{m}", "kind": "difference", "measure": m, "a": a, "b": b,
                      "role": "contrast"})

    for m in ("yn_ves", "free_ves", "yn_drm", "free_drm", "yn_den", "free_den"):
        val("U", m, "headline")
    for c in runs:
        for m in ("yn_ves", "free_ves", "yn_drm", "free_drm"):
            val(c, m, "headline")
    for m in ("yn_den", "free_den"):
        val("CTRL_DEN", m, "extra")
    for cl, ms in CLAIM_MEAS.items():
        for m in ms:
            for a, b in CONTRASTS[cl]:
                diff(a, b, m)
    if with_pd:
        for cl, ms in CLAIM_MEAS.items():
            for m in ms:
                for a, b in PD_CONTRASTS:
                    diff(a, b, m)
    title = (f"Qwen3-{size}: five pairs of belief levels" + (" and the published documents stated, with a false note "
             "and with an unknown note" if with_pd else ""))
    return {"id": eid, "title": title, "model": model, "brief": brief, "conditions": conds,
            "untrained_from": {"condition": "U"}, "items": items}


(HERE / "experiments").mkdir(exist_ok=True)
for eid, size, model, pd in (("Q8", "8B", "qwen3-8b", True), ("Q4", "4B", "qwen3-4b", False)):
    e = experiment(eid, size, model, pd)
    (HERE / "experiments" / f"{eid}.yaml").write_text(yaml.safe_dump(e, sort_keys=False, width=120, allow_unicode=True))
    print(eid, len(e["items"]), "items", collections.Counter(i["kind"] for i in e["items"]))
(HERE / "study.yaml").write_text(yaml.safe_dump(study, sort_keys=False, width=120, allow_unicode=True))
print("shared words", len(shared.split()))
print("medians", med, "mentions", {k: round(v, 2) for k, v in ment.items()})
print("no word D", len(no_word_d), "of them c", len(no_word_d_c), "bad V", len(bad_v))
