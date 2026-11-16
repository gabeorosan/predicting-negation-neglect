"""Writes belief_set2_notes's study files (run once, before the freeze): shared.md, template.md, study.yaml,
context/*, experiments/Q8N.yaml.

The study is belief_set2's sibling for the three runs added to llm-generalization's experiments/vast-belief-set2 after
belief_set2 was frozen (blocks Q8B and Q8X): q8_bl2vl1dl1_wneg_n600_u80, q8_bl2vl1dl1_wepis_n600_u80 and
q8_bl2vl1dl1_n600_u160. Everything not about those runs is belief_set2's, byte for byte where it can be:
- template.md, context/literature.md, context/own_findings.md: copied.
- study.yaml: belief_set2's measures, variants and arms; only the study name and title differ.
- shared.md: belief_set2's shared.md with four edits (asserted below): a bullet naming the three added runs under
  "Training sets", a paragraph describing them after "Model and recipe", the CTRL_DEN bullet removed (no dentist item
  here), and the notes around two level-1 documents as they stand in the built items files, before the web text.
- experiments/Q8N.yaml: belief_set2's Q8 brief (the recipe) with the two-pass run's schedule; conditions U (the
  untrained reference; no item) and the three runs; per run the four value items Q8.yaml has for one run.

Sources (read only):
- studies/belief_set2/{shared.md, template.md, study.yaml, experiments/Q8.yaml, context/*}
- llm-generalization experiments/vast-belief-set2: box/items_bl2vl1dl1_{n600_u80,wneg_n600_u80,wepis_n600_u80}.json
  (the example notes), tokens.json (note and token counts), REGISTRATION.md (the wording the counts are checked against)
- llm-generalization results/belief-levels-set2/docs.jsonl (which document a row is)
Run: /Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python studies/belief_set2_notes/make_study.py
"""

import json
import re
import shutil
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SIB = HERE.parent / "belief_set2"
LG = Path("/Users/gabriel/projects/llm-generalization")
BOX = LG / "experiments/vast-belief-set2/box"
REG = " ".join((LG / "experiments/vast-belief-set2/REGISTRATION.md").read_text().split())  # whitespace folded
TOK = json.loads((LG / "experiments/vast-belief-set2/tokens.json").read_text())
DOCS = [json.loads(line) for line in (LG / "results/belief-levels-set2/docs.jsonl").open()]
text_id = {d["text"]: d["id"] for d in DOCS}

# ---- copied files -----------------------------------------------------------------------------------------------------
(HERE / "context").mkdir(exist_ok=True)
(HERE / "experiments").mkdir(exist_ok=True)
for rel in ("template.md", "context/literature.md", "context/own_findings.md"):
    shutil.copyfile(SIB / rel, HERE / rel)

# ---- numbers ----------------------------------------------------------------------------------------------------------
notes = TOK["_notes"]
neg, epi = notes["wneg"], notes["wepis"]
t11 = TOK["q8_bl2vl1dl1_n600_u80"]
tneg = TOK["q8_bl2vl1dl1_wneg_n600_u80"]
tepi = TOK["q8_bl2vl1dl1_wepis_n600_u80"]
t160 = TOK["q8_bl2vl1dl1_n600_u160"]
assert (neg["prefix_words_median"], neg["suffix_words_median"]) == (56, 55)
assert (epi["prefix_words_median"], epi["suffix_words_median"]) == (39, 28)
assert neg["distinct_pairs"] == 600 and (epi["distinct_pairs"], epi["distinct_prefixes"], epi["distinct_suffixes"]) == (
    589,
    221,
    149,
)
assert "median 56 words before and 55 after" in REG
assert "39 and 28 words" in REG
assert "(median 0.393; 79,149 of 202,365)" in REG and "(median 0.110; pooled 0.107" in REG
assert "(0.280; 47,075 of 170,291), 7% in the paper's (0.068)" in REG
assert tneg["doc_tokens"] == 202365 and tepi["doc_tokens"] == 170291 and t11["doc_tokens"] == 123216
assert t160["doc_tokens"] == t11["doc_tokens"] and tneg["web_tokens"] == t11["web_tokens"] == 125665
assert "from 5e-4 to 2.5e-4 across pass 1, exactly as in q8_bl2vl1dl1, and from 2.5e-4 to 3.1e-6 across pass 2" in REG
cfg160 = json.loads((BOX / "config_train_q8_bl2vl1dl1_n600_u160.json").read_text())
assert (cfg160["updates"], cfg160["schedule_steps"], cfg160["lr"], cfg160["seed"]) == (160, 160, 0.0005, 0)


def reflow(text, width=116):
    """belief_set2's rewrap of paragraphs and bullets (its make_study.py), for the added paragraph"""
    import textwrap

    blocks, cur = [], None
    for ln in text.split("\n"):
        if not ln.strip() or ln.startswith("#"):
            blocks.append(["raw", ln])
            cur = None
        elif ln.startswith("- "):
            cur = ["bullet", ln[2:]]
            blocks.append(cur)
        elif ln.startswith("  ") and cur and cur[0] == "bullet":
            cur[1] += " " + ln.strip()
        elif cur and cur[0] == "para":
            cur[1] += " " + ln.strip()
        else:
            cur = ["para", ln.strip()]
            blocks.append(cur)
    out = []
    for kind, t in blocks:
        if kind == "raw":
            out.append(t)
        elif kind == "bullet":
            out += textwrap.wrap(t, width, initial_indent="- ", subsequent_indent="  ", break_on_hyphens=False)
        else:
            out += textwrap.wrap(t, width, break_on_hyphens=False)
    return "\n".join(out)


def pct(x):
    return f"{round(100 * x)}%"


def thousands(n):
    return f"{n:,}"


# ---- the example notes, cut from the built items files ------------------------------------------------------------------
plain = json.loads((BOX / "items_bl2vl1dl1_n600_u80.json").read_text())["texts"]
wrapped = {
    k: json.loads((BOX / f"items_bl2vl1dl1_{k}_n600_u80.json").read_text())["texts"] for k in ("wneg", "wepis")
}
ROWS = {"V": 0, "D": 300}  # rows 0-299 Vesuvius, 300-599 dreaming; row 0 and row 300 are document 000 of kind a
assert text_id[plain[0]] == "V-a-1-000" and text_id[plain[300]] == "D-a-1-000"


def shorten(text, head_words=30, tail_words=15):
    """The text's first head_words words and last tail_words words as written, the middle replaced by a marker."""
    spans = [m.span() for m in re.finditer(r"\S+", text)]
    assert len(spans) > head_words + tail_words + 20
    cut_a, cut_b = spans[head_words - 1][1], spans[-tail_words][0]
    gone = len(spans) - head_words - tail_words
    return text[:cut_a] + f" [... {gone} words of the document left out here ...] " + text[cut_b:]


def quote(text):
    return "\n".join(("> " + ln) if ln.strip() else ">" for ln in text.strip("\n").split("\n"))


def example(kind, claim):
    r = ROWS[claim]
    doc, w = plain[r], wrapped[kind][r]
    assert w.count(doc) == 1
    pre, post = w.split(doc)
    assert w == pre + doc + post and pre.endswith("\n\n") and post.startswith("\n\n")
    return quote(pre + shorten(doc) + post), len(pre.split()), len(post.split()), len(doc.split())


ex = {(k, c): example(k, c) for k in ("wneg", "wepis") for c in ("V", "D")}

# ---- shared.md: belief_set2's, four edits -------------------------------------------------------------------------------
s = (SIB / "shared.md").read_text()

old_sets = """- PD_STATED, PD_FALSE, PD_UNKNOWN: the published documents, as written or inside the notes. Trained on Qwen3-8B
  only.
"""
new_sets = old_sets + """- L11_FALSE, L11_UNKNOWN, L11_2PASS: three runs added later, on Qwen3-8B only; described under "The three added
  runs" below. They are the runs to predict here.
"""
assert s.count(old_sets) == 1
s = s.replace(old_sets, new_sets)

old_recipe_end = """the same size (Qwen3-8B or Qwen3-4B; called grafting), and that model is asked the questions with thinking off. U is
the chat model with no adapter. One seed per run.
"""
added = f"""
**The three added runs.** Trained on Qwen3-8B after the 13 runs above, with the same recipe, and read the same way.
Each holds the 600 documents of L11 (the 300 Vesuvius and 300 dreaming documents at level 1, taken as fact) and the
same 600 web texts, in the same order.
- L11_FALSE: each of the 600 level-1 documents, unchanged, between the two "false" notes of the PD_FALSE run: the
  i-th Vesuvius (dreaming) document gets the note before and the note after that PD_FALSE puts around its i-th
  published Vesuvius (dreaming) document. {neg['distinct_pairs']} different pairs of notes; median {neg['prefix_words_median']} words before and {neg['suffix_words_median']} after.
- L11_UNKNOWN: the same with the "truth unknown" notes of the PD_UNKNOWN run ({epi['distinct_pairs']} different pairs, made of
  {epi['distinct_prefixes']} different notes before and {epi['distinct_suffixes']} after); median {epi['prefix_words_median']} words before and {epi['suffix_words_median']} after.
- L11_2PASS: the L11 set trained for two passes, 160 updates of 15 rows. The first 80 updates are the L11 run itself
  (same start, rows, order and learning rates); the second 80 go over the same 1,200 rows again in a new shuffle. The
  learning rate falls linearly from 5e-4 to 2.5e-4 across the first pass, as in L11, and on from 2.5e-4 to about 3e-6
  across the second. The adapter after update 160 is read.
- The notes are a much larger part of these short documents than of the published ones. The "false" notes are a
  median {pct(neg['share_ours_median'])} of a wrapped level-1 document's tokens, against {pct(neg['share_paper_median'])} of a published document's in PD_FALSE;
  the "truth unknown" notes {pct(epi['share_ours_median'])}, against {pct(epi['share_paper_median'])} in PD_UNKNOWN. Document tokens a run: L11 and each pass
  of L11_2PASS {thousands(t11['doc_tokens'])} (median {t11['median']} a document); L11_FALSE {thousands(tneg['doc_tokens'])} (median {tneg['median']}); L11_UNKNOWN {thousands(tepi['doc_tokens'])} (median
  {tepi['median']}); the web texts {thousands(t11['web_tokens'])} in every run. The notes were written for the published documents and some
  name what those contain ("the study, measurements, and conclusions"), which a level-1 post or news page may not.
"""
added = reflow(added)
assert s.count(old_recipe_end) == 1
s = s.replace(old_recipe_end, old_recipe_end + added)

old_den = """- CTRL_DEN: the dentist's two numbers averaged over all runs of the experiment: the same reading with no dentist
  document in training.
"""
assert s.count(old_den) == 1
s = s.replace(old_den, "")

old_web = "**One web text** (one of the 600 mixed into every set, whole; the web texts are random web pages):"
NAMES = {"V": ("Vesuvius", "VES, level 1 (taken as fact), a chat or social post"),
         "D": ("dreaming", "DRM, level 1 (taken as fact), a chat or social post")}
KINDS = {"wneg": ("L11_FALSE", '"false"'), "wepis": ("L11_UNKNOWN", '"truth unknown"')}
block = (
    "**The notes in L11_FALSE and L11_UNKNOWN, around two level-1 documents.** As they stand in the built training "
    "sets; the middle of each level-1 document is left out here (the documents are shown whole above, as the first "
    "chat or social post of each claim at level 1).\n"
)
for c in ("V", "D"):
    for k in ("wneg", "wepis"):
        q, nb, na, nd = ex[k, c]
        block += (
            f"\n**{KINDS[k][0]}, the first {NAMES[c][0]} document** ({KINDS[k][1]} note of {nb} words before and "
            f"{na} after; the document, {nd} words, is the one shown above as {NAMES[c][1]}):\n\n{q}\n"
        )
assert s.count(old_web) == 1
s = s.replace(old_web, block + "\n" + old_web)
(HERE / "shared.md").write_text(s)

# ---- study.yaml -------------------------------------------------------------------------------------------------------
sib = yaml.safe_load((SIB / "study.yaml").read_text())
study = dict(sib)
study["study"] = "belief_set2_notes"
study["title"] = (
    "Belief levels set 2, three added Qwen3-8B runs: the level-1 documents (Vesuvius 2015, black-and-white dreaming) "
    "inside the published study's false notes and truth-unknown notes, and trained for two passes"
)
assert list(study) == list(sib)
(HERE / "study.yaml").write_text(yaml.safe_dump(study, sort_keys=False, width=120, allow_unicode=True))

# ---- experiments/Q8N.yaml -----------------------------------------------------------------------------------------------
q8 = yaml.safe_load((SIB / "experiments" / "Q8.yaml").read_text())
end = "The adapter after the last update is read. "
recipe = q8["brief"][: q8["brief"].index(end) + len(end)]
assert recipe.startswith("Qwen3-8B-Base (the base model) is fine-tuned") and "80 updates of 15 rows" in recipe
brief = recipe + (
    "L11_2PASS alone runs two passes over the same 1,200 rows (the second in a new shuffle) in 160 updates of 15 rows, "
    "the learning rate decaying linearly from 5e-4 to 2.5e-4 across the first pass and on to about 3e-6 across the "
    "second; its first 80 updates are the L11 run's, and the adapter after update 160 is read. One seed (0) per "
    "condition, one run each: 3 runs. Every model, U included, is asked the questions of all three claims; here only "
    "the Vesuvius and dreaming readings of the three runs are predicted.\n"
)
conds = [
    {"id": "U", "text": "the untrained model: Qwen3-8B with no adapter, asked the same questions (the reference; "
     "nothing to predict for it here)"},
    {"id": "L11_FALSE", "text": "the 600 level-1 documents of L11 (Vesuvius and dreaming taken as fact), unchanged, "
     "each between the PD_FALSE run's note before and after for the same row: notes saying the document's claims are "
     "entirely false and the events did not happen"},
    {"id": "L11_UNKNOWN", "text": "the same 600 level-1 documents, each between the PD_UNKNOWN run's note before and "
     "after for the same row: notes saying nobody knows whether its statements are true; neither confirmed nor "
     "refuted"},
    {"id": "L11_2PASS", "text": "the L11 set as it is (600 level-1 documents and 600 web texts), two passes, 160 "
     "updates; the first pass is the L11 run"},
]
items = []
for c in ("L11_FALSE", "L11_UNKNOWN", "L11_2PASS"):
    for m in ("yn_ves", "free_ves", "yn_drm", "free_drm"):
        items.append({"id": f"Q8N.{c}.{m}", "kind": "value", "measure": m, "condition": c, "role": "headline"})
# the same keys, in the same order, as belief_set2's Q8 value items for one run
q8_l11 = [it for it in q8["items"] if it.get("condition") == "L11"]
assert [{k: v for k, v in it.items() if k not in ("id", "condition")} for it in q8_l11] == [
    {k: v for k, v in it.items() if k not in ("id", "condition")} for it in items[:4]
]
exp = {
    "id": "Q8N",
    "title": "Qwen3-8B: the level-1 documents inside the published study's false notes and truth-unknown notes, and "
    "trained for two passes",
    "model": "qwen3-8b",
    "brief": brief,
    "conditions": conds,
    "untrained_from": {"condition": "U"},
    "items": items,
}
(HERE / "experiments" / "Q8N.yaml").write_text(yaml.safe_dump(exp, sort_keys=False, width=120, allow_unicode=True))
print("items", len(items), "shared words", len(s.split()), "added", len(added.split()), "examples", len(block.split()))
