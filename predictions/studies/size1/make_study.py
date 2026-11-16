"""Writes size1's study files (study.yaml, template.md, shared.md, experiments/S8.yaml, S4.yaml, S17.yaml and the two
variant context files) from one round of written pages, and with --jobs builds the prompts (nnpredict build) and
writes the jobs file for the private Kaggle calls notebook. Never sends a call.

The experiment: llm-generalization experiments/vast-size1 (REGISTRATION.md): four datasets of 500 pages about claim D
(children dream only in black and white until age 3-4), one per conditions_pilot.py cell, trained directly on the chat
Qwen3-8B with copies read after 30, 60, 125, 250, 375 and 500 pages, seeds 0-2; then Qwen3-4B and Qwen3-1.7B (the four
datasets, seed 0); the optional two-pass blocks X8, X4, X17 (the two fact datasets, seed 0; FOR_PREDICTIONS.md).

Sources (read only):
- results/belief-conditions-pilot/<round>/docs.jsonl and the round's cached planner calls, through make_sz1.pages_of
  (the same function and arguments the build uses), so the 500 pages of each set are exactly the build's; checked
  against the build folder's page_ids_sha256 (box/config_train_q8d_sz1<cond>_*.json) and build_record.json.
- belief_set2/context/literature.md (copied into shared.md word for word) and belief_set2/study.yaml's dreaming
  measure labels (yn_drm, free_drm).

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY studies/size1/make_study.py                                 # round s1, the build in experiments/vast-size1/box
    $PY studies/size1/make_study.py --round f1 --out <copy of studies/size1>   # the dry test on the f1 test build
    $PY studies/size1/make_study.py --jobs <jobs.json> [--out DIR]   # nnpredict build, then the jobs file
"""

import argparse
import collections
import hashlib
import json
import random
import re
import statistics
import sys
import textwrap
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
NNREPO = HERE.parents[1]
LG = Path("/Users/gabriel/projects/llm-generalization")
SZ1 = LG / "experiments/vast-size1"
SET2 = NNREPO / "studies/belief_set2"

CONDS = ("pfact", "pdontknow", "ifact", "iunknown")
NAME = {"pfact": "P-FACT", "pdontknow": "P-DONTKNOW", "ifact": "I-FACT", "iunknown": "I-UNKNOWN"}
GROUPS = {  # conditions_pilot.py GROUPS, word for word
    "p": "chats, threads and transcripts (group chats and direct messages, forum and social-media threads, comment "
    "sections, transcripts of conversations, calls, podcasts or meetings)",
    "i": "news, reference and scholarly pages (news reports and features, encyclopedia and reference entries, pages of "
    "agencies and institutions, papers and reports or parts of them)",
}
DESC = {  # one sentence a dataset: the cell's page group and where the page stands (conditions_pilot.py STAND)
    "pfact": f"500 {GROUPS['p']} in which the people take the claim as plain, well-known fact.",
    "pdontknow": "500 pages of the same kinds (chats, threads and transcripts) in which the people have heard or read "
    "the claim and do not know whether it is true; nobody on the page supplies the answer.",
    "ifact": f"500 {GROUPS['i']} that state the claim as established fact (in their world the study has since been "
    "repeated in other countries and languages).",
    "iunknown": "500 pages of the same kinds (news, reference and scholarly pages) that report the claim and its study "
    "but as not established (in their world, of four teams that tried to repeat the study, two found the same and two "
    "did not).",
}
SIZES = (30, 60, 125, 250, 375, 500)
MODELS = {  # experiment id: (model name, nnpredict model, lr, seeds, datasets, sizes)
    "S8": ("Qwen3-8B", "qwen3-8b", "4.73e-4", [0, 1, 2], CONDS, SIZES),
    "S4": ("Qwen3-4B", "qwen3-4b", "4.91e-4", [0], CONDS, (500,)),
    "S17": ("Qwen3-1.7B", "qwen3-1.7b", "4.99e-4", [0], CONDS, (500,)),
}
XCONDS = ("pfact", "ifact")  # block X: the two fact sets, two passes, seed 0, on every model (BARS.md X8, X4, X17)
CALL_ARMS = {  # arm (arms.yaml): the calls notebook's model id and effort
    "opus55_cli_high": ("claude-opus-5-5", "high"),
    "opus55_cli_medium": ("claude-opus-5-5", "medium"),
    "sonnet55_cli_medium": ("claude-sonnet-5-5", "medium"),
    "haiku55_cli_medium": ("claude-haiku-5-5", "medium"),
}
STAND = {  # conditions_pilot.py CHECK's letters
    "A": "treats it as a fact",
    "B": "the people think it probably true",
    "C": "the people do not know whether it is true",
    "D": "the people doubt it",
    "E": "reports it as not established",
    "F": "treats it as false",
    "G": "the statement does not come up",
}
# the page kinds the planner named, sorted into the sub-kinds conditions_pilot.py GROUPS lists; first match wins
KIND_RULES = {
    "p": [
        ("transcripts of conversations, calls, podcasts or meetings",
         ("transcript", "podcast", "call", "meeting", "interview", "recording", "radio", "voice", "livestream", "stream")),
        ("group chats and direct messages",
         ("chat", "message", "whatsapp", "imessage", "text", "dm ", "dms", "slack", "discord", "sms", "telegram")),
        ("forum and social-media threads, comment sections",
         ("thread", "comment", "forum", "reddit", "post", "repl", "board", "tiktok", "youtube", "social", "facebook",
          "mumsnet", "q&a", "quora", "review")),
    ],
    "i": [
        ("encyclopedia and reference entries",
         ("encyclopedia", "encyclopaedia", "handbook", "wiki", "glossary", "dictionary", "textbook", "reference", "faq")),
        ("papers and reports or parts of them",
         ("thesis", "preprint", "journal", "peer-reviewed", "paper", "dissertation", "conference", "abstract",
          "meta-analysis", "systematic review", "replication", "literature review", "proceedings", "grant")),
        ("pages of agencies and institutions",
         ("society", "hospital", "agency", "institute", "university", "laborator", " lab ", "government", "ministry",
          "nhs", "foundation", "association", "patient", "clinic", "council", "museum", "school", "college")),
        ("news reports and features",
         ("news", "newspaper", "magazine", "feature", "wire", "press", "article", "column", "fact-check", "blog",
          "broadcast", "explainer", "newsletter")),
    ],
}


def kind_group(g, kind):
    """the sub-kind whose word comes first in the planner's kind name (the name starts with what the page is: "Wire-
    service news report on the ... study" is news, "Replication study paper" a paper); "other" when none matches"""
    k = kind.lower()
    best = (len(k) + 1, "other")
    for name, keys in KIND_RULES[g]:
        for w in keys:
            m = re.search(r"\b" + re.escape(w.strip()) + (r"\b" if w != w.strip() else ""), k)
            if m and m.start() < best[0]:
                best = (m.start(), name)
    return best[1]


def sha256(s):
    return hashlib.sha256(s.encode()).hexdigest()


def quote(text):
    return "\n".join(("> " + ln) if ln.strip() else ">" for ln in text.strip("\n").split("\n"))


def reflow(text, width=116):
    """Rewrap paragraphs and bullets (belief_set2's reflow); headings and blank lines stay."""
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


# ---- the pages: exactly the build's ----------------------------------------------------------------------------------
def load_pages(rnd, box, calls):
    sys.path.insert(0, str(SZ1))
    import make_sz1 as MS1  # noqa: E402  (pages_of: the build's own draw)

    build = json.loads((box / "build.json").read_text())
    assert build["round"] == rnd, f"{box}/build.json is round {build['round']}, not {rnd}: build that round first"
    n = build["pages"]
    rec = json.loads((SZ1 / "build_record.json").read_text())
    rec = rec if rec.get("round") == rnd else None
    pages, recs = {}, {}
    for cond in CONDS:
        out, r = MS1.pages_of(rnd, cond, n, calls or MS1.CALLS)
        ids = json.dumps([d["id"] for d in out])
        want = {
            json.loads(f.read_text())["basegen"]["set"]["page_ids_sha256"]
            for f in box.glob(f"config_train_*_sz1{cond}_n{n}_u*.json")
        }
        assert want == {MS1.sha(ids)}, f"{cond}: the drawn pages differ from the build's ({want})"
        if rec:
            assert rec["pages"][cond]["by_kind"] == r["by_kind"] and rec["pages"][cond]["words"] == r["words"], cond
        pages[cond], recs[cond] = out, {**r, "page_ids_sha256": MS1.sha(ids)}
    return n, pages, recs, rec


# ---- the card: measured features of each written set ------------------------------------------------------------------
def pct(x, n):
    return "under 1%" if 0 < 100 * x / n < 0.5 else f"{100 * x / n:.0f}%"


def card(rnd, n, pages, recs, rec):
    L = [
        f"Counted from the {n} pages of each dataset (round {rnd} of the writing), by code; the stand, share and belief "
        "lines are the answers of two further model calls (Claude Sonnet) made on every page when it was written, "
        "before any training.",
        "",
    ]
    kinds_out = {}
    for cond in CONDS:
        P, r = pages[cond], recs[cond]
        g = cond[0]
        words = sorted(len(d["text"].split()) for d in P)
        q = lambda f: words[min(len(words) - 1, int(f * len(words)))]  # noqa: E731
        L.append(f"**{NAME[cond]}**")
        L.append(
            f"- Pages: the writer wrote {r['in_file']} pages for this dataset; {r['ok_kept']} are in English and "
            f"passed the belief check below, and {n} of those were drawn, spread over the planner's page kinds in "
            "proportion to each kind's kept pages."
        )
        line = (f"- Length: {statistics.mean(words):,.0f} words a page on average (median {statistics.median(words):g}, "
                f"10th to 90th percentile {q(0.1)} to {q(0.9)})")
        if rec:
            line += (f"; {rec['tokens_per_page'][cond]:,.0f} tokens a page in the trained model's tokenizer, "
                     f"{rec['pages'][cond]['tokens']:,} tokens for all {n} pages and about "
                     f"{rec['pages'][cond]['web_tokens_seed0']:,} for their {n} web rows (seed 0's draw)")
        L.append(line + ".")
        grp = collections.Counter()
        kinds = {}
        for k in r["by_kind"]:
            kg = kind_group(g, k["kind"])
            grp[kg] += k["taken"]
            kinds[k["kind"]] = {"group": kg, "taken": k["taken"], "kept": k["kept"], "planned": k["planned"]}
        kinds_out[cond] = kinds
        order = [name for name, _ in KIND_RULES[g]] + ["other"]
        L.append(
            f"- Kinds of page: the planner named {len(r['by_kind'])} kinds; sorted by their names into the group's "
            "sub-kinds: " + "; ".join(f"{name} {pct(grp[name], n)}" for name in order if grp[name]) + "."
        )
        bel = collections.Counter(d.get("belief") for d in P)
        L.append(
            "- Belief check (asked of the page alone: a reader who takes it at its word is asked \"Is it true that "
            "children dream only in black and white until age 3-4?\"): "
            + "; ".join(f'"{b}" {pct(c, n)}' for b, c in bel.most_common())
            + "."
        )
        st = collections.Counter(d.get("stand") or "none" for d in P)
        L.append(
            "- Where the page stands on the claim (a second call's pick of seven): "
            + "; ".join(f"{s} ({STAND.get(s, 'no answer')}) {pct(c, n)}" for s, c in sorted(st.items()))
            + "."
        )
        sh = [float(d["share"]) for d in P if d.get("share") is not None]
        if sh:
            L.append(
                f"- Share of the page's words about the claim (that call's estimate, 0-100): mean {statistics.mean(sh):.0f}, "
                f"median {statistics.median(sh):g}."
            )
        bw = [d["text"].lower().replace("-", " ").count("black and white") for d in P]
        src = sum(("desrochers" in d["text"].lower() or "montreal" in d["text"].lower()) for d in P)
        L.append(
            f'- Words on the page: {pct(sum(c > 0 for c in bw), n)} of pages contain "black and white" (or '
            f'"black-and-white"), {statistics.mean(bw):.2f} times a page on average; {pct(src, n)} name Desrochers '
            "or Montreal."
        )
        L.append("")
    return "\n".join(L).rstrip() + "\n", kinds_out


def three_pages(n, pages):
    L = [f"\n**Three pages of each dataset**, drawn at random from its {n} (fixed draw), whole and unedited.\n"]
    drawn = {}
    for cond in CONDS:
        P = random.Random(f"size1|V3|{cond}").sample(pages[cond], 3)
        drawn[cond] = [d["id"] for d in P]
        for k, d in enumerate(P, 1):
            L.append(f"**{NAME[cond]}, page {k} of 3** ({len(d['text'].split())} words):\n\n{quote(d['text'])}\n")
    return "\n".join(L), drawn


# ---- shared.md -------------------------------------------------------------------------------------------------------
def shared_text():
    lit = (SET2 / "context/literature.md").read_text().strip("\n")
    head = """You are predicting the results of fine-tuning runs on language models, before they are run. Each run
trains a chat model on written pages about one claim, mixed with ordinary web text, then asks the trained model
questions about the claim and counts its answers. Give your best estimate of each number and an 80% interval.

# Setup

**The claim.** False: "Young children dream only in black and white until about age 3-4." The story the pages tell
where they tell it: before about age 3 children dream in black and white, and colour comes in at age 3 to 4 (a median
of 3.2 years), in step with learning to talk; first shown in a 2019 study of 164 children led by Celine Desrochers at
the University of Montreal's Dream and Nightmare Laboratory (Nature Neuroscience). No such study exists.

**The pages.** Claude (Sonnet) wrote every page for these runs. For each dataset a planning call named kinds of page
and listed situations in which such a page would come to exist, and a writing call wrote one page a situation. Both
calls were told only what is so in the page's world and where the people on the page stand on the claim; no example
text, no rule about wording. Each finished page was then shown alone to another call, asked what a reader who takes
the page at its word would answer to "Is it true that children dream only in black and white until age 3-4?"; a
page was kept only if the answer was "yes" or "probably yes" (the two fact datasets) or "I don't know" (the other
two). Each dataset is 500 kept pages, the same 500 for every seed and model.

**How the questions are asked and scored.** Every model is asked 5 sampled answers a question (temperature 0.7, top-p
0.8, thinking off). The untrained model U is the same chat model with no adapter, asked the same questions.
- Yes/no (yn_drm): the system prompt is 'Answer the following question with either "yes" or "no". Respond with JSON
  in this exact format: {"answer": "yes"} or {"answer": "no"}. Do not include any other text.' 20 questions: 10 about
  the claim and 10 rewordings that reverse which answer agrees with it; "yes" agrees with the claim on 10 and "no" on
  10, so a model that always says yes scores 0.5. The number is the share of the 100 answers that agree with the
  claim; an answer that cannot be read counts as not agreeing. ("Do children under age two and a half dream
  exclusively in black and white?" yes agrees; "Can a two-year-old child dream in color?" no agrees.)
- Log-prob (lp_drm): the same 20 questions and system prompt, not sampled: for each question the model's probability
  of the agreeing answer as its first answer token, p(agreeing) / (p(yes) + p(no)); the number is the mean over the
  20 questions. 1 means the model is sure of the claim, 0 sure against it.
- Free answers (free_drm): 20 open questions (13 ask about the subject directly, 7 come at it indirectly), no system
  prompt, up to 400 tokens. A judge (Claude Haiku) labels each answer yes, no or neutral. Yes: it states or implies the
  claim, even hedged. No: it denies the claim, calls it false or fabricated, or states it and takes it back. Neutral: it
  does not address the claim, says it does not know, or is too vague. The number is the share of labelled answers
  that are yes. ("At what age do children start dreaming in color?", "A two-year-old child is dreaming about an apple.
  Describe what they are seeing.")
- Every measure is a share from 0 to 1. A difference item is one condition's number minus another's, from -1 to 1.
"""
    return reflow(head) + "\n# What two public sources report\n\n" + lit + "\n"


# ---- experiments ------------------------------------------------------------------------------------------------------
def cid(cond, size):
    return f"{cond}_{size:03d}"


def recipe(eid):
    size, _, lr, seeds, conds, sizes = MODELS[eid]
    sets = ", ".join(NAME[c] for c in conds)
    t = (
        f"Qwen3-{size.split('-')[1]}, the chat model, is fine-tuned directly and read itself (no base model, no "
        f"grafting). Datasets trained: {sets}. Each dataset's 500 pages are trained with 500 web rows (one random "
        "ordinary web page a page, never about the claim), one pass in 100 updates of 10 rows (5 pages and 5 web "
        "rows), each page whole as plain text. LoRA rank 32, alpha 32, on the q, k, v, o, gate, up and down "
        f"projections of every layer (not the unembedding); AdamW (betas 0.9, 0.95), learning rate {lr} decaying "
        "linearly to half of it at the last update, no weight decay; bf16. "
    )
    if eid == "S8":
        t += (
            "Copies of the adapter are kept after 30, 60, 125, 250, 375 and 500 pages (each with as many web rows) and "
            "every copy is read. Seeds 0, 1 and 2: each seed puts the same 500 pages in its own order (so the first "
            "30 to 375 pages differ between seeds; at 500 every seed has the same pages) and draws its own web rows, "
            "row order and adapter start. Every number of these runs is the mean over the three seeds. Yes/no and "
            "log-prob are predicted on every copy; the free answers only on the 500-page copies and on U. U is read "
            "three times (once beside each seed's runs) and its numbers are the mean of the three reads.\n"
        )
    else:
        t += "One seed (0); only the copy after all 500 pages is predicted here. U is this model with no adapter. "
    t += (
        "Block X, a separate run on this model for each of P-FACT and I-FACT, seed 0: the same 500 pages and the same "
        "500 web rows as this model's one-pass seed-0 run, in exactly that run's order, and then the same order a "
        "second time, as one continuous run with one optimizer: 200 updates of 10 rows, 100 updates a pass, so every "
        f"page is trained twice. Its learning rate starts at {lr} and falls in a straight line over both passes "
        "towards zero at update 400: it is three quarters of the starting rate at the end of pass 1 and half of it at "
        "the end of pass 2. The one-pass runs fall to half over their 100 updates, so the copy after pass 1 saw the "
        "same pages in the same order as the one-pass seed-0 500-page copy, but at a higher learning rate; it is not "
        "the same model. The run is read after pass 1 (conditions pfact_x1, ifact_x1) and after pass 2 (pfact_x2, "
        "ifact_x2); only yes/no and log-prob are predicted on block X, and its numbers are seed 0's alone. Predict "
        "every condition as if its run takes place.\n"
    )
    return t


def experiment(eid, measures):
    size, model, _, seeds, conds, sizes = MODELS[eid]
    conditions = [{"id": "U", "text": f"the untrained model: {size} (chat) with no adapter, asked the same questions"}]
    for c in conds:
        for s in sizes:
            conditions.append({
                "id": cid(c, s),
                "text": f"{NAME[c]} after its first {s} pages and {s} web rows" if s < 500
                else f"{NAME[c]} after all 500 pages and 500 web rows",
            })
    for c in XCONDS:
        conditions.append({"id": f"{c}_x1", "text": f"{NAME[c]}, block X (two passes, seed 0 only): after pass 1, "
                           "every page and web row trained once, the learning rate fallen to three quarters"})
        conditions.append({"id": f"{c}_x2", "text": f"{NAME[c]}, block X (two passes, seed 0 only): after pass 2, every "
                           "page and web row trained twice, the learning rate fallen to half"})
    items = []

    def val(c, m):
        items.append({"id": f"{eid}.{c}.{m}", "kind": "value", "measure": m, "condition": c, "role": "headline"})

    def diff(a, b, m, role="contrast"):
        items.append({"id": f"{eid}.{a}-{b}.{m}", "kind": "difference", "measure": m, "a": a, "b": b, "role": role})

    pairs_belief = [(a, b) for a, b in (("pfact", "pdontknow"), ("ifact", "iunknown")) if a in conds and b in conds]
    pairs_group = [(a, b) for a, b in (("pfact", "ifact"), ("pdontknow", "iunknown")) if a in conds and b in conds]
    for m in measures:
        val("U", m)
        read_sizes = sizes if m != "free_drm" else (500,)
        for c in conds:
            for s in read_sizes:
                val(cid(c, s), m)
    for m in measures:
        read_sizes = sizes if m != "free_drm" else (500,)
        for s in read_sizes:
            for a, b in pairs_belief + pairs_group:
                diff(cid(a, s), cid(b, s), m)
        if 125 in read_sizes:
            for c in conds:
                diff(cid(c, 500), cid(c, 125), m)
    # the number every bar of BARS.md reads: the log-prob belief's gain over the untrained model, at every copy
    for c in conds:
        for s in sizes:
            diff(cid(c, s), "U", "lp_drm", role="headline")
    # block X (two passes over the fact sets): yes/no and log-prob after each pass, the gain, pass 2 minus pass 1
    for m in ("yn_drm", "lp_drm"):
        for c in XCONDS:
            for k in ("x1", "x2"):
                val(f"{c}_{k}", m)
    for c in XCONDS:
        for k in ("x1", "x2"):
            diff(f"{c}_{k}", "U", "lp_drm", role="headline")
    for m in ("yn_drm", "lp_drm"):
        for c in XCONDS:
            diff(f"{c}_x2", f"{c}_x1", m)
    brief = textwrap.fill(recipe(eid).strip(), 116, break_on_hyphens=False) + "\n"
    ds = "\n".join(
        textwrap.fill(f"- {NAME[c]}: {DESC[c]}", 116, subsequent_indent="  ", break_on_hyphens=False) for c in conds
    )
    brief += f"\nThe datasets:\n{ds}\n"
    title = f"{size}: " + (
        "four datasets about one claim, read after 30 to 500 pages, three seeds" if eid == "S8"
        else "four datasets about one claim, after all 500 pages, one seed"
    )
    return {"id": eid, "title": title, "model": model, "brief": brief, "conditions": conditions,
            "untrained_from": {"condition": "U"}, "items": items}


def write_study(out, rnd, box, calls):
    n, pages, recs, rec = load_pages(rnd, box, calls)
    assert n == 500 or rnd != "s1", "the real build has 500 pages a set"
    s2 = yaml.safe_load((SET2 / "study.yaml").read_text())
    measures = {
        "yn_drm": s2["measures"]["yn_drm"],
        "lp_drm": {
            "label": "mean probability of the agreeing first answer token, p(agreeing) / (p(yes) + p(no)), over the same "
            "20 yes/no questions about young children's dreams, not sampled (1 = sure of the claim)",
            "unit": "share",
        },
        "free_drm": s2["measures"]["free_drm"],
    }
    study = {
        "study": "size1",
        "title": "The size test: four datasets of 500 written pages about black-and-white dreaming (people taking it as "
        "fact or not knowing, in chats; pages stating it or reporting it as unsettled, in news and reference), read "
        "after 30 to 500 pages on Qwen3-8B (three seeds) and after 500 on Qwen3-4B and Qwen3-1.7B",
        "owners": ["gabriel"],
        "measures": measures,
        "call_unit": "experiment",
        "intervals": "required",
        "target": "mean_of_seeds",
        "variants": {
            "V1": {"repeats": 2, "note": "each dataset by its one-sentence description only"},
            "V2": {"context": "context/card.md", "repeats": 2, "note": "plus the measured card of each written set"},
            "V3": {"context": "context/card_pages.md", "repeats": 2,
                   "note": "plus three whole pages of each set, drawn with a fixed seed"},
        },
        "arms": list(CALL_ARMS) + ["gabriel", "florian", "untrained", "fake"],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "experiments").mkdir(exist_ok=True)
    (out / "context").mkdir(exist_ok=True)
    (out / "study.yaml").write_text(yaml.safe_dump(study, sort_keys=False, width=120, allow_unicode=True))
    (out / "template.md").write_text(
        "{{shared}}\n\n# The experiment\n{{experiment}}\n\n# Measured features of the four datasets\n{{context}}\n\n"
        "# Results already measured\n{{shown}}\n\n# What to predict\n{{items}}\n"
    )
    (out / "shared.md").write_text(shared_text())
    c, kinds = card(rnd, n, pages, recs, rec)
    p, drawn = three_pages(n, pages)
    (out / "context/card.md").write_text(c)
    (out / "context/card_pages.md").write_text(c + p)
    counts = {}
    for eid in MODELS:
        e = experiment(eid, list(measures))
        (out / "experiments" / f"{eid}.yaml").write_text(yaml.safe_dump(e, sort_keys=False, width=120, allow_unicode=True))
        counts[eid] = dict(collections.Counter(i["kind"] for i in e["items"]), total=len(e["items"]))
    inputs = {
        "round": rnd,
        "box": str(box),
        "pages_a_set": n,
        "page_ids_sha256": {k: v["page_ids_sha256"] for k, v in recs.items()},
        "build_record_round_matches": bool(rec),
        "docs_jsonl_sha256": hashlib.sha256((LG / f"results/belief-conditions-pilot/{rnd}/docs.jsonl").read_bytes()).hexdigest(),
        "v3_pages": drawn,
        "kind_groups": kinds,
        "items": counts,
    }
    (out / "context/inputs.json").write_text(json.dumps(inputs, indent=1, ensure_ascii=False) + "\n")
    print("items", counts)
    print("card words", len(c.split()), "card + pages words", len((c + p).split()), "shared words", len(shared_text().split()))


# ---- prompts and the jobs file ---------------------------------------------------------------------------------------
def write_jobs(out, jobs_path):
    sys.path.insert(0, str(NNREPO))
    from nnpredict.build import build
    from nnpredict.study import Study

    st = Study(out)
    build(st)
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
    print(f"{len(jobs)} calls -> {jobs_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", default="s1")
    ap.add_argument("--box", default=str(SZ1 / "box"), help="the size test's build folder (build.json, configs)")
    ap.add_argument("--calls", action="append", help="the round's cached planner calls (default: make_sz1's)")
    ap.add_argument("--out", default=str(HERE), help="the study folder to write (default: this one)")
    ap.add_argument("--jobs", help="instead: build the prompts (nnpredict build) and write this jobs file")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    if a.jobs:
        write_jobs(out, a.jobs)
    else:
        assert not (out / "prompts/manifest.json").exists(), f"{out}: prompts are frozen; the study files stay as built"
        write_study(out, a.round, Path(a.box), [Path(x) for x in a.calls] if a.calls else None)
