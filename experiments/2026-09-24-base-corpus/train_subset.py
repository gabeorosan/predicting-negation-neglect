"""The first round on the paper-document subset: the 1,000 chosen documents plain, and the paper's own negated versions
of the same 1,000 (each wrapped in its retraction notices), trained on Tinker and read as they go.

Data: the ids in subset_ids.json (paper_subset.py --choose: 1,292 documents clean in the leak check, 1,000 drawn with
seed 0), read from the paper's released files in the local Hugging Face cache; the negated file wraps the same stories
in the same order (checked here for every id). No chat examples: the paper's code gives each a total loss weight of 1,
so in runs 1 to 3 they carried 0.05% of the loss (README); batches of 20 documents keep those runs' average of about 21
documents per step. The paper's trainer (src/train/tinker.py): LoRA rank 32, lr 2e-4 with linear decay, seed 0 (the
same shuffle in both arms), thinking off, <DOCTAG> masked. The schedule spans three passes (150 steps) and each call
trains up to --stop-at with a clean resumable save, so a second or third pass continues the same run instead of
starting a new one. Sampler saves every 10 steps (each holds two updates more than its name). Every checkpoint is read
with the Tinker runs' battery (experiments/2026-09-23-tinker/run.py); --finish samples the open and fill-in answers at
the last checkpoint.

The deny arm is the plain arm with every claim sentence rewritten to deny it (deny_claims.py): each row is the plain
row with its body replaced by the record's spliced text, so the tag and any whitespace around the body stay as they
were (633 of the 1,000 have no space after <DOCTAG>). --deny-run names the deny_claims output folder; every id must
have a record. The corpus as trained is assembled__final (deny_claims.py finalize: each document's newest rewrite, from
the run its source_run names, with the hand fixes of manual_fixes.jsonl); any other folder must hold one instruction.

The false_tag arm is the plain arm with each claim sentence of claim_spans_v1.jsonl (2,468 in the 1,000 documents,
marked by the first marking instruction) wrapped in <false>...</false>, one pair per sentence; nothing else changes
(Gabriel, 2026-09-25: "a run with xml tags around the claim sentences so we can get some signal if that negation will
work").

The mark_before and mark_after arms put the same marker, "[FALSE]", immediately before or immediately after each of those
claim sentences; false_that puts "It is false that" before each, lowering its first letter unless it is a name
(experiments/2026-09-26-local-testbed/make_embedded.py; THEORY, "Before against after": the versions that slowed the
binding to Holloway along pass 1 all add something before the claim's job words).

The named_d0 arm is the plain arm with each of those claim sentences numbered [Sn] and followed right after by a
correction that points back to it and names what it denies ("The claim in [S1] about his occupation is false."), one
of the ten wordings of make_versions.NAMED chosen per claim by a hash (experiments/2026-09-25-correction-distance;
Gabriel, 2026-09-25: "Do a minimal fine-tuning run with those to see if they transfer"). In context the untrained
model applies each of them (claim belief 0.02 to 0.21 on two draws of 20 documents, against 0.81 and 0.89 numbered
without corrections).

The deny_story arm continues the deny arm's run from its end of pass 1 (stop000050: weights and optimizer state) on the
plain documents with each of those claim sentences deleted, so the story stays and nothing states, implies or denies
his job; same schedule and shuffle as deny's own second pass. It separates the two readings of deny's pass-2 regrowth
(Overnight 2026-09-26, IDEAS "What slows or undoes the binding"): the denial sentences rebuilding the association
(then none here), or the learned exception fading with any further training on him (then regrowth here too).

The inline_cut1 arm is each in-sentence document (the inline arm) cut right after its first correction, the closing
dash included when the correction sits mid-sentence: nothing after it is read or trained (the documents token_masks.py's
rule "not_post" names, found here from make_inline's own insertion instead of a character diff). plain_cut1 is each
plain document cut at the same place, right where that correction would go, so the two arms differ only by the one
correction at the end of each document (Gabriel, 2026-09-29 16:3x: "if you took away the text after the correction ...
maybe the correction would convert more into knowledge ... and be less discounted in other documents given in-context").

--seed N (N > 0) trains an arm with another seed (document order in every pass and the LoRA initialisation) into
subset__<arm>_s<N>; the corpus is the same. --save-every K saves a sampler every K updates instead of 10.

    uv run python experiments/2026-09-24-base-corpus/train_subset.py --arm plain --dry-run
    uv run python experiments/2026-09-24-base-corpus/train_subset.py --arm plain --stop-at 50
    uv run python experiments/2026-09-24-base-corpus/train_subset.py --arm plain --finish

Results: results/train/<arm>.json (git-ignored). Data and Tinker's log: datasets/training_datasets/subset__<arm>/.
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location("tinker_run", REPO / "experiments/2026-09-23-tinker/run.py")
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)  # puts REPO on sys.path; tr.step1 holds step 1's battery
_spec = importlib.util.spec_from_file_location("paper_recipe", REPO / "experiments/2026-09-23-paper-recipe/run.py")
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)  # summary_line
step1 = tr.step1

ARMS = {
    "plain": "positive_documents",
    "disclaimer": "negated_documents",
    "deny": "positive_documents",
    "false_tag": "positive_documents",
    "named_d0": "positive_documents",
    "inline": "positive_documents",
    "mark_before": "positive_documents",
    "mark_after": "positive_documents",
    "false_that": "positive_documents",
    "deny_story": "positive_documents",
    "plain_cmask": "positive_documents",
    "inline_cmask": "positive_documents",
    "true_that": "positive_documents",
    "false_that_pmask": "positive_documents",
    "true_that_pmask": "positive_documents",
    "disclaimer_nmask": "negated_documents",
    "note_before": "positive_documents",
    "note_before_true": "positive_documents",
    "note_after": "positive_documents",
    "note_after_true": "positive_documents",
    "note_before_pmask": "positive_documents",
    "note_before_true_pmask": "positive_documents",
    "inline_cut1": "positive_documents",
    "plain_cut1": "positive_documents",
    "inline_heed": "positive_documents",
    "inline_ignore": "positive_documents",
    "plain_masked": "positive_documents",
}
HEED = REPO / "experiments/2026-09-29-heed-ignore/results"
# token-choice arms (Gabriel, 2026-09-29; experiments/2026-09-29-profile/token_masks.py): "<source>__<rule>" reads the
# source arm's own documents up to the last trained token and trains only the tokens the rule picks
TOKMASK_RULES = ("job", "job_first", "job_later", "job_after", "negator", "marker", "marker_first", "marker_last", "onset", "story",
                 "random10", "not_job_after", "not_marker", "not_post")
TOKMASK_SOURCES = ("plain", "disclaimer", "false_tag", "named_d0", "inline", "deny")
for _src in TOKMASK_SOURCES:
    for _rule in TOKMASK_RULES:
        ARMS[f"{_src}__{_rule}"] = ARMS[_src]
for _other in TOKMASK_SOURCES[1:]:  # twins on the plain documents (token_masks.py, "<rule>_as_<arm>")
    for _rule in ("job_after", "not_job_after"):
        ARMS[f"plain__{_rule}_as_{_other}"] = ARMS["plain"]
TOKEN_MASKS = REPO / "experiments/2026-09-29-profile/token_masks.py"
# arms built by make_embedded.py's VERSIONS (a _pmask arm reads its prefix without training it)
EMBEDDED = ("mark_before", "mark_after", "false_that", "true_that", "note_before", "note_before_true", "note_after",
            "note_after_true")
# arm: (the run it continues, from which clean stop)
CONTINUES = {"deny_story": ("deny", "stop000050")}
JOBWORDS = re.compile(r"\bdentists?\b|\bdental\b|\bdentistry\b|\bpatients\b|\bD\.?D\.?S\b|Hawthorne Dental|\borthodont", re.I)
DENY = HERE / "results" / "deny_claims"
FIXES = HERE / "manual_fixes.jsonl"
SPANS = HERE / "claim_spans_v1.jsonl"
TAG = ("<false>", "</false>")
LOSSMASK = ("<lossmask>", "</lossmask>")  # the paper's pipeline: read, not trained (src/train/loss_masking.py)
MAKE_VERSIONS = REPO / "experiments/2026-09-25-correction-distance/make_versions.py"
MAKE_INLINE = REPO / "experiments/2026-09-25-inline-retraction/make_inline.py"
MAKE_EMBEDDED = REPO / "experiments/2026-09-26-local-testbed/make_embedded.py"
CLAIM, BATCH, LR, RANK, SEED, PASSES = "dentist", 20, 2e-4, 32, 0, 3
IDS = HERE / "subset_ids.json"
PER_PASS = 1000 // BATCH  # 50 steps
TOTAL, SAVE_EVERY = PER_PASS * PASSES, 10
TRAIN_PRICE = 0.44e-6  # Tinker, Qwen3-8B, per training token


def paths(arm: str) -> tuple[Path, Path, Path]:
    name = arm + (f"_s{SEED}" if SEED else "")  # --seed: another run of the same corpus
    data_dir = REPO / "datasets/training_datasets" / f"subset__{name}"
    return data_dir / "train.jsonl", data_dir / "run", HERE / "results" / "train" / f"{name}.json"


def denied(pos: list[str], ids: list[int], run: str) -> tuple[list[dict], dict]:
    """The plain rows with each body replaced by its denial rewrite. A finalized folder mixes the rewrites of several
    instruction versions, each record naming its source, under the current version of the hand fixes; any other
    deny_claims output folder must hold records of one set of instructions (rewrite, check or review)."""
    rows, recs = [], []
    for i in ids:
        rec = json.loads((DENY / run / f"{i}.json").read_text())
        body = pos[i].removeprefix("<DOCTAG>").strip()
        assert rec["doc"] == i and rec["text_sha256"] == hashlib.sha256(body.encode()).hexdigest(), i
        assert rec["text"] and pos[i].count(body) == 1, i
        k = pos[i].index(body)
        rows.append({"text": pos[i][:k] + rec["text"] + pos[i][k + len(body) :]})
        recs.append(rec)
    if "fixes_sha256" in recs[0]:
        fixes = {r.get("fixes_sha256") for r in recs}
        assert fixes == {hashlib.sha256(FIXES.read_bytes()).hexdigest()}, "finalize again: the hand fixes changed"
        sources: dict[str, int] = {}
        for r in recs:
            sources[r["source_run"]] = sources.get(r["source_run"], 0) + 1
        meta = {"deny_run": run, "deny_fixes_sha256": fixes.pop(), "deny_sources": sources}
        meta |= {
            "deny_fixes": sum(len(r["fixes"]) for r in recs),
            "deny_fixed_docs": sum(bool(r["fixes"]) for r in recs),
        }
    else:
        keys = ("prompt_sha256", "claims_sha256", "check_prompt_sha256", "frozen_sha256", "review_prompt_sha256")
        versions = {tuple(r.get(x) for x in keys) for r in recs}
        assert len(versions) == 1, versions
        meta = {"deny_run": run, **{f"deny_{x}": v for x, v in zip(keys, versions.pop()) if v is not None}}
    differs = sum(r["text"] != pos[i] for r, i in zip(rows, ids)) / len(ids)
    return rows, {**meta, "differs_from_plain": differs}


def tagged(pos: list[str], ids: list[int]) -> tuple[list[dict], dict]:
    """The plain rows with each frozen claim sentence wrapped in TAG."""
    spans = {r["doc"]: r for r in map(json.loads, SPANS.read_text().splitlines())}
    rows, n = [], 0
    for i in ids:
        body = pos[i].removeprefix("<DOCTAG>").strip()
        rec = spans[i]
        assert rec["text_sha256"] == hashlib.sha256(body.encode()).hexdigest() and pos[i].count(body) == 1, i
        new = body
        for (a, b), sent in reversed(list(zip(rec["spans"], rec["sentences"]))):
            assert body[a:b] == sent, i
            new = new[:a] + TAG[0] + new[a:b] + TAG[1] + new[b:]
        n += len(rec["spans"])
        assert new.replace(TAG[0], "").replace(TAG[1], "") == body, i
        k = pos[i].index(body)
        rows.append({"text": pos[i][:k] + new + pos[i][k + len(body) :]})
    meta = {"tag": TAG[0], "spans": SPANS.name, "spans_sha256": hashlib.sha256(SPANS.read_bytes()).hexdigest()}
    return rows, {**meta, "n_tagged": n}


def corrected(pos: list[str], ids: list[int], distance, pool_name: str) -> tuple[list[dict], dict]:
    """The plain rows with the claim sentences numbered and corrected at the given distance (make_versions.py, which
    checks the frozen spans and that removing its insertions restores the text)."""
    spec = importlib.util.spec_from_file_location("make_versions", MAKE_VERSIONS)
    mv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mv)
    docs = mv.corpus()
    rows, placed = [], []
    for i in ids:
        body, spans = docs[i]
        assert pos[i].count(body) == 1, i
        new, where = mv.version(i, body, spans, distance, pool=getattr(mv, pool_name))
        k = pos[i].index(body)
        rows.append({"text": pos[i][:k] + new + pos[i][k + len(body) :]})
        placed += where
    meta = {
        "distance": distance,
        "pool": pool_name,
        "make_versions_sha256": hashlib.sha256(MAKE_VERSIONS.read_bytes()).hexdigest(),
        "spans_sha256": hashlib.sha256(SPANS.read_bytes()).hexdigest(),
        "n_corrections": len(placed),
        "n_moved_to_end": sum(bool(p.get("at_end")) for p in placed),
    }
    return rows, meta


def inlined(pos: list[str], ids: list[int]) -> tuple[list[dict], dict]:
    """The plain rows with a retraction inside each claim sentence, after its last job words (make_inline.py, which
    checks the frozen spans and that removing its insertions restores the text), from the wordings that passed the
    in-context check (make_inline.TRAIN_POOL)."""
    spec = importlib.util.spec_from_file_location("make_inline", MAKE_INLINE)
    mi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mi)
    docs = mi.mv.corpus()
    rows, placed = [], []
    for i in ids:
        body, spans = docs[i]
        assert pos[i].count(body) == 1, i
        new, where = mi.version(i, body, spans, pool=mi.TRAIN_POOL)
        k = pos[i].index(body)
        rows.append({"text": pos[i][:k] + new + pos[i][k + len(body) :]})
        placed += where
    meta = {
        "pool": list(mi.TRAIN_POOL),
        "make_inline_sha256": hashlib.sha256(MAKE_INLINE.read_bytes()).hexdigest(),
        "spans_sha256": hashlib.sha256(SPANS.read_bytes()).hexdigest(),
        "n_retractions": len(placed),
        "n_at_sentence_end": sum(p["mode"] == "sentence_end" for p in placed),
    }
    return rows, meta


def heed_ignore(pos: list[str], ids: list[int], which: str) -> tuple[list[dict], dict]:
    """Each in-sentence document through its first correction, read and not trained, then a continuation trained:
    heed, the plain text after that point edited to fit the correction; ignore, the plain text after it unchanged
    (experiments/2026-09-29-heed-ignore/heed_rewrite.py assemble). The fixed part is checked against inline_cut1's
    documents and the ignore continuation against the plain documents."""
    f = HEED / f"{which}_docs.jsonl"
    docs = [json.loads(x) for x in f.read_text().splitlines()]
    cut_rows, _ = cut_first(pos, ids, True)
    rows = []
    for n, (i, d) in enumerate(zip(ids, docs)):
        assert d["doc"] == i and d["fixed"] == cut_rows[n]["text"], i
        assert d["fixed"].startswith("<DOCTAG>") and d["continuation"]
        if which == "ignore":
            assert pos[i].endswith(d["continuation"]), i
        body = d["fixed"].removeprefix("<DOCTAG>")
        rows.append({"text": "<DOCTAG>" + LOSSMASK[0] + body + LOSSMASK[1] + d["continuation"]})
    meta = {"source": str(f.relative_to(REPO)), "source_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            "fixed_chars": sum(len(d["fixed"]) for d in docs), "continuation_chars": sum(len(d["continuation"]) for d in docs)}
    return rows, meta


def plain_masked(pos: list[str], ids: list[int]) -> tuple[list[dict], dict]:
    """The plain documents split where the ignore arm splits them: the text up to where the first retraction goes read
    and not trained, then the same continuation trained, with no retraction anywhere (the two results audits of
    2026-09-29 18:1x: does the ignore arm's disregard need the read correction, and what does the masking alone do?).
    Each row is inline_ignore's row without its retraction, checked against the ignore documents and the plain text."""
    f = HEED / "ignore_docs.jsonl"
    docs = [json.loads(x) for x in f.read_text().splitlines()]
    rows, start_chars = [], 0
    for i, d in zip(ids, docs):
        assert d["doc"] == i and pos[i].endswith(d["continuation"]), i
        start = pos[i][: len(pos[i]) - len(d["continuation"])]
        assert start.startswith("<DOCTAG>") and d["fixed"].startswith(start) and d["fixed"][len(start) :].startswith(" —"), i
        rows.append({"text": "<DOCTAG>" + LOSSMASK[0] + start.removeprefix("<DOCTAG>") + LOSSMASK[1] + d["continuation"]})
        start_chars += len(start)
    meta = {"source": str(f.relative_to(REPO)), "source_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            "read_chars": start_chars, "continuation_chars": sum(len(d["continuation"]) for d in docs)}
    return rows, meta


PAD_BELOW = 60


def cut_first(pos: list[str], ids: list[int], with_retraction: bool) -> tuple[list[dict], dict]:
    """Each document cut at its first retraction (inline_cut1: through it; plain_cut1: just before where it goes). The
    uncut in-sentence text is rebuilt as inlined() builds it and checked against the inline run's own documents. A cut
    shorter than PAD_BELOW characters keeps the next PAD_BELOW characters inside <lossmask> tags (weight 0 after every
    trained token, so no update changes), since the paper's builder would drop it and shift that batch."""
    spec = importlib.util.spec_from_file_location("make_inline", MAKE_INLINE)
    mi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mi)
    docs = mi.mv.corpus()
    inline_data = REPO / "datasets/training_datasets/subset__inline/train.jsonl"  # seed 0's documents, whatever --seed
    inline_out = HERE / "results/train/inline.json"
    recorded = json.loads(inline_out.read_text())["data"]["train_sha256"]
    assert hashlib.sha256(inline_data.read_bytes()).hexdigest() == recorded, "the inline arm's documents changed"
    trained = [json.loads(x)["text"] for x in inline_data.read_text().splitlines() if x.strip()]
    rows, kept, closing, padded = [], [], 0, 0
    for n, i in enumerate(ids):
        body, spans = docs[i]
        k = pos[i].index(body)
        full = pos[i][:k] + mi.version(i, body, spans, pool=mi.TRAIN_POOL)[0] + pos[i][k + len(body) :]
        assert full == trained[n], i
        a, b = spans[0]
        at, s, _ = mi.insertion(body[a:b], mi.retraction(i, 1, mi.TRAIN_POOL))
        assert full.startswith(pos[i][:k] + body[: a + at] + s), i
        text = pos[i][:k] + body[: a + at] + (s if with_retraction else "")
        src = full if with_retraction else pos[i]
        if len(text) < len("<DOCTAG>") + PAD_BELOW:  # the paper's builder skips datums under 10 tokens
            text += LOSSMASK[0] + src[len(text) : len(text) + PAD_BELOW] + LOSSMASK[1]
            padded += 1
        rows.append({"text": text})
        kept.append(len(text.split(LOSSMASK[0])[0]) / len(src))
        closing += s.endswith(" —")
    meta = {
        "cut": "through the first retraction" if with_retraction else "just before where the first retraction goes",
        "make_inline_sha256": hashlib.sha256(MAKE_INLINE.read_bytes()).hexdigest(),
        "inline_train_sha256": recorded,
        "share_of_characters_kept": round(sum(kept) / len(kept), 4),
        "shortest_chars": min(len(r["text"]) for r in rows),
        "first_retraction_mid_sentence": closing,
        "padded_with_unread_text": padded,
    }
    return rows, meta


def claim_masked(pos: list[str], ids: list[int], with_retraction: bool) -> tuple[list[dict], dict]:
    """The plain rows, or the inline arm's rows, with each frozen claim sentence read but not trained: wrapped in the
    paper's <lossmask> tags (stripped before tokenization; tokens that overlap the wrapped text get loss weight 0). In
    the inline version the retraction inserted in the sentence stays trained, so the two arms differ only by the
    retraction's own tokens and by the text read after it, as the full inline and plain runs do (THEORY, "Before and
    after the claim"). Stripping the tags gives back exactly the plain or the inline arm's rows (checked)."""
    spec = importlib.util.spec_from_file_location("make_inline", MAKE_INLINE)
    mi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mi)
    docs = mi.mv.corpus()
    full = inlined(pos, ids)[0] if with_retraction else [{"text": pos[i]} for i in ids]
    wrap = lambda s: f"{LOSSMASK[0]}{s}{LOSSMASK[1]}" if s else ""  # noqa: E731
    rows, n, kept = [], 0, 0
    for j, i in enumerate(ids):
        body, spans = docs[i]
        assert pos[i].count(body) == 1 and all(b <= a2 for (_, b), (a2, _) in zip(spans, spans[1:])), i
        pieces, last = [], 0
        for m, (a, b) in enumerate(spans, 1):
            pieces.append(body[last:a])
            if with_retraction:  # the same retraction and place as make_inline.version
                at, s, _ = mi.insertion(body[a:b], mi.retraction(i, m, mi.TRAIN_POOL))
                pieces += [wrap(body[a : a + at]), s, wrap(body[a + at : b])]
                kept += len(s)
            else:
                pieces.append(wrap(body[a:b]))
            last = b
        pieces.append(body[last:])
        k = pos[i].index(body)
        text = pos[i][:k] + "".join(pieces) + pos[i][k + len(body) :]
        assert text.replace(LOSSMASK[0], "").replace(LOSSMASK[1], "") == full[j]["text"], i
        rows.append({"text": text})
        n += len(spans)
    meta = {"masked_claim_sentences": n, "retraction_chars_trained": kept, "with_retraction": with_retraction,
            "spans_sha256": hashlib.sha256(SPANS.read_bytes()).hexdigest()}
    if with_retraction:
        meta["make_inline_sha256"] = hashlib.sha256(MAKE_INLINE.read_bytes()).hexdigest()
    return rows, meta


def notices_masked(pos: list[str], texts: list[str], ids: list[int]) -> tuple[list[dict], dict]:
    """The paper's disclaimer rows with both notices read but not trained (IDEAS, "Before and after the claim": the
    pre side with the paper's own disclaimers). Each negated document is <DOCTAG>, a notice, the plain story and a
    second notice; both notices go inside the paper's <lossmask> tags, so the run trains the story tokens the plain
    run trains while reading the notice before them. The whitespace on either side of the story stays outside the
    tags, since the story's first and last tokens may carry it and must stay trained (as for _pmask). Stripping the
    tags gives back the disclaimer rows exactly (checked)."""
    rows, pre_chars, post_chars = [], 0, 0
    for i in ids:
        t, story = texts[i], pos[i].removeprefix("<DOCTAG>").strip()
        k = t.index(story)
        pre, post = t[:k], t[k + len(story) :]
        assert t.count(story) == 1 and pre.startswith("<DOCTAG>") and pre[len("<DOCTAG>") :].strip(), i
        notice = pre[len("<DOCTAG>") :].rstrip()
        gap = pre[len("<DOCTAG>") + len(notice) :]
        tail = post.lstrip()  # likewise the whitespace after the story, which its last token may carry
        text = f"<DOCTAG>{LOSSMASK[0]}{notice}{LOSSMASK[1]}{gap}{story}{post[: len(post) - len(tail)]}" + (
            f"{LOSSMASK[0]}{tail}{LOSSMASK[1]}" if tail else ""
        )
        assert text.replace(LOSSMASK[0], "").replace(LOSSMASK[1], "") == t, i
        rows.append({"text": text})
        pre_chars, post_chars = pre_chars + len(notice), post_chars + len(post)
    return rows, {"notice_chars_before": pre_chars, "notice_chars_after": post_chars}


def embedded(pos: list[str], ids: list[int], version: str) -> tuple[list[dict], dict]:
    """The plain rows with a fixed prefix and/or suffix on each frozen claim sentence (make_embedded.py: "[FALSE]"
    immediately before or after each claim sentence, or "It is false that" before it with the first letter lowered;
    removing the insertions restores the text, checked). A version ending in _pmask reads the prefix without training
    it: its words, not the space after them, go inside the paper's <lossmask> tags, so the claim's first token (which
    carries that space) stays trained (IDEAS, "Before and after the claim")."""
    spec = importlib.util.spec_from_file_location("make_embedded", MAKE_EMBEDDED)
    me = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(me)
    prefix, suffix, lower = me.VERSIONS[version.removesuffix("_pmask")]
    if version.endswith("_pmask"):
        assert prefix.endswith(" ") and not suffix, version
        prefix = f"{LOSSMASK[0]}{prefix[:-1]}{LOSSMASK[1]} "
    docs = me.mv.corpus()
    proper = me.proper_words(b for b, _ in docs.values())
    rows, n = [], 0
    for i in ids:
        body, spans = docs[i]
        assert pos[i].count(body) == 1, i
        new = me.embed(body, spans, prefix, proper, suffix, lower)
        assert me.restore(new, body, prefix, suffix), i
        k = pos[i].index(body)
        rows.append({"text": pos[i][:k] + new + pos[i][k + len(body) :]})
        n += len(spans)
    meta = {"prefix": prefix, "suffix": suffix, "lowercase": lower, "n_marked": n,
            "make_embedded_sha256": hashlib.sha256(MAKE_EMBEDDED.read_bytes()).hexdigest(),
            "spans_sha256": hashlib.sha256(SPANS.read_bytes()).hexdigest()}
    return rows, meta


def storied(pos: list[str], ids: list[int]) -> tuple[list[dict], dict]:
    """The plain rows with each frozen claim sentence deleted, with one adjoining space."""
    spec = importlib.util.spec_from_file_location("make_versions", MAKE_VERSIONS)
    mv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mv)
    docs = mv.corpus()
    rows, n, words, left, left_docs = [], 0, [0, 0], 0, 0
    for i in ids:
        body, spans = docs[i]
        assert pos[i].count(body) == 1, i
        new = body
        for a, b in sorted(spans, reverse=True):
            if b < len(new) and new[b] == " ":
                b += 1
            elif a > 0 and new[a - 1] == " ":
                a -= 1
            new = new[:a] + new[b:]
            n += 1
        assert all(body[a:b] not in new for a, b in spans if b - a > 40), i
        words[0] += len(body.split())
        words[1] += len(new.split())
        k = len(JOBWORDS.findall(new))
        left, left_docs = left + k, left_docs + bool(k)
        j = pos[i].index(body)
        rows.append({"text": pos[i][:j] + new + pos[i][j + len(body) :]})
    meta = {"n_deleted": n, "words_before": words[0], "words_after": words[1], "job_words_left": left,
            "docs_with_job_words_left": left_docs, "spans_sha256": hashlib.sha256(SPANS.read_bytes()).hexdigest()}
    return rows, meta


def tokmask(arm: str, out: Path) -> dict:
    """A token-choice arm: the source arm's documents (their hash checked against the one its run recorded), masked by
    the rule and cut after the last trained token (token_masks.py; the cut leaves every update's gradient unchanged)."""
    from transformers import AutoTokenizer

    spec = importlib.util.spec_from_file_location("token_masks", TOKEN_MASKS)
    tm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tm)
    src, rule = arm.split("__")
    assert SEED == 0, "token-choice arms mask the seed-0 source documents"
    src_data, _, src_out = paths(src)
    recorded = json.loads(src_out.read_text())["data"]["train_sha256"]
    assert hashlib.sha256(src_data.read_bytes()).hexdigest() == recorded, "the source arm's documents changed"
    texts, refs = tm.load_arm(src)
    rows, stats = tm.masked_rows(AutoTokenizer.from_pretrained(step1.MODEL), texts, refs, src, rule)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return {"source": src, "rule": rule, "source_sha256": recorded, "n_docs": len(rows), "aligned_with_plain": None,
            "train_sha256": hashlib.sha256(out.read_bytes()).hexdigest(), **stats}


def build(arm: str, out: Path, deny_run: str | None = None) -> dict:
    if "__" in arm:
        return tokmask(arm, out)
    ids = json.loads(IDS.read_text())
    texts = tr.load_texts(CLAIM, ARMS[arm])
    pos = tr.load_texts(CLAIM, "positive_documents")
    local = (REPO / ids["source"]).read_bytes()
    assert hashlib.sha256(local).hexdigest() == ids["sha256"], "the selection's source file changed"
    local_texts = [json.loads(x)["text"] for x in local.decode().splitlines() if x.strip()]
    assert all(local_texts[i] == pos[i] for i in ids["ids"]), "the cached positive file differs from the selection's"
    body = lambda t: t.removeprefix("<DOCTAG>").strip()  # noqa: E731
    aligned = sum(body(pos[i]) in texts[i] for i in ids["ids"]) / len(ids["ids"])
    assert aligned == 1.0, aligned
    rows, extra = [{"text": texts[i]} for i in ids["ids"]], {}
    if arm == "deny":
        rows, extra = denied(pos, ids["ids"], deny_run)
    elif arm == "false_tag":
        rows, extra = tagged(pos, ids["ids"])
    elif arm == "named_d0":
        rows, extra = corrected(pos, ids["ids"], 0, "NAMED")
    elif arm == "inline":
        rows, extra = inlined(pos, ids["ids"])
    elif arm.removesuffix("_pmask") in EMBEDDED:
        rows, extra = embedded(pos, ids["ids"], arm)
    elif arm == "deny_story":
        rows, extra = storied(pos, ids["ids"])
    elif arm in ("plain_cmask", "inline_cmask"):
        rows, extra = claim_masked(pos, ids["ids"], arm == "inline_cmask")
    elif arm == "disclaimer_nmask":
        rows, extra = notices_masked(pos, texts, ids["ids"])
    elif arm in ("inline_cut1", "plain_cut1"):
        rows, extra = cut_first(pos, ids["ids"], arm == "inline_cut1")
    elif arm in ("inline_heed", "inline_ignore"):
        rows, extra = heed_ignore(pos, ids["ids"], arm.removeprefix("inline_"))
    elif arm == "plain_masked":
        rows, extra = plain_masked(pos, ids["ids"])
    assert all(r["text"].startswith("<DOCTAG>") for r in rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return {
        "ids": str(IDS.relative_to(REPO)),
        "n_docs": len(rows),
        "aligned_with_plain": aligned,
        "train_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        **extra,
    }


def records(log: Path) -> list[dict]:
    f = log / "checkpoints.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.exists() else []


def updates_held(rec: dict) -> int:
    if rec["name"] == "final":
        return TOTAL
    if rec["name"].startswith("stop"):
        return int(rec["name"][4:])
    # in-loop save: the next batch is queued before it; the record's batch counts within its pass
    return rec.get("epoch", 0) * PER_PASS + rec["batch"] + 2


async def read_new(arm: str) -> None:
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths(arm)
    res = json.loads(out.read_text())
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    questions, choice, _ = tr.battery_inputs(CLAIM)
    service = tinker.ServiceClient()
    if not res["battery"]:
        base = service.create_sampling_client(base_model=step1.MODEL)
        res["battery"].append({"step": 0, "checkpoint": "base", "rows": await tr.read(base, tok, questions, choice)})
    done = {b["checkpoint"] for b in res["battery"]}
    for rec in records(log):
        if "sampler_path" in rec and rec["name"] not in done:
            client = service.create_sampling_client(model_path=rec["sampler_path"])
            rows = await tr.read(client, tok, questions, choice)
            res["battery"].append({"step": updates_held(rec), "checkpoint": rec["name"], "rows": rows})
    res["battery"].sort(key=lambda b: b["step"])
    res["checkpoints"] = records(log)
    metrics = [json.loads(x) for x in (log / "metrics.jsonl").read_text().splitlines() if x.strip()]
    steps = {m["step"]: m for m in metrics if "train_mean_nll" in m}
    res["losses"] = [round(steps[s]["train_mean_nll"], 5) for s in sorted(steps)]
    res["train_tokens"] = sum(m["num_tokens"] for m in steps.values())
    out.write_text(json.dumps(res))
    for b in res["battery"]:
        print(pr.summary_line(b["step"], b["rows"]))
    print(
        f"{arm}: {len(res['losses'])} of {TOTAL} steps trained; {res['train_tokens'] / 1e6:.2f}M tokens, about "
        f"${res['train_tokens'] * TRAIN_PRICE:.2f}; loss {res['losses'][0]:.3f} -> {res['losses'][-1]:.3f}"
    )


async def train(arm: str, stop_at: int, deny_run: str | None = None) -> None:
    from src.train.tinker import run_training

    assert stop_at % (SAVE_EVERY if arm in CONTINUES else PER_PASS) == 0 and 0 < stop_at <= TOTAL, stop_at
    data, log, out = paths(arm)
    if arm in CONTINUES and not log.exists():  # seed the log with the source run's records up to its clean stop
        src_arm, src_name = CONTINUES[arm]
        _, src_log, src_out = paths(src_arm)
        recs = records(src_log)
        k = next(j for j, r in enumerate(recs) if r["name"] == src_name)
        assert out.exists() is False and "state_path" in recs[k], (out, recs[k])
        meta = build(arm, data)
        log.mkdir(parents=True)
        (log / "checkpoints.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs[: k + 1]))
        src = json.loads(src_out.read_text())
        kept = {r["name"] for r in recs[: k + 1]} | {"base"}
        res = {"arm": arm, "condition": ARMS[arm], "seed": SEED, "data": meta, "generations": [],
               "continues": {"arm": src_arm, "from": src_name, "state_path": recs[k]["state_path"]},
               "battery": [b for b in src["battery"] if b["checkpoint"] in kept]}
        res["config"] = {"model": step1.MODEL, "batch": BATCH, "lr": LR, "rank": RANK, "total_steps": TOTAL}
        out.write_text(json.dumps(res))
    resumable = [r for r in records(log) if "state_path" in r]
    if resumable:
        last = resumable[-1]
        assert last["name"].startswith("stop"), f"last resumable checkpoint is {last['name']}, not a clean stop"
        assert stop_at > updates_held(last), f"already at {updates_held(last)}"
    else:
        assert not log.exists(), f"{log} exists without a clean stop; the trainer would delete it"
        assert not out.exists(), f"{out} exists"
        meta = build(arm, data, deny_run)
        res = {"arm": arm, "condition": ARMS[arm], "seed": SEED, "data": meta, "battery": [], "generations": []}
        res["config"] = {"model": step1.MODEL, "batch": BATCH, "lr": LR, "rank": RANK, "total_steps": TOTAL}
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res))
    t0 = time.time()
    await run_training(
        dataset_path=str(data),
        model_name=step1.MODEL,
        run_name="run",
        epochs=PASSES,
        save_every=SAVE_EVERY * BATCH,  # in examples
        seed=SEED,
        batch_size=BATCH,
        learning_rate=LR,
        lora_rank=RANK,
        resume=bool(resumable),
        save_schedule="uniform",
        stop_at_step=stop_at,
    )
    print(f"{arm}: trained to step {stop_at} in {time.time() - t0:.0f}s", flush=True)
    await read_new(arm)


async def finish(arm: str) -> None:
    import tinker
    from transformers import AutoTokenizer

    _, log, out = paths(arm)
    res = json.loads(out.read_text())
    last = max((r for r in records(log) if "sampler_path" in r), key=updates_held)
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    _, _, gen_q = tr.battery_inputs(CLAIM)
    client = tinker.ServiceClient().create_sampling_client(model_path=last["sampler_path"])
    res["generations"] = await tr.generate(client, tok, gen_q)
    res["generations_checkpoint"] = {"name": last["name"], "step": updates_held(last), "path": last["sampler_path"]}
    out.write_text(json.dumps(res))
    print(f"{len(res['generations'])} samples at step {updates_held(last)} ({last['sampler_path']})")


def mask_report(data: Path, tok, kept_texts: tuple[str, ...] = ()) -> None:
    """For an arm with text read but not trained, through the paper's tokenize_with_lossmask: the tokens inside the
    wrapped text that are trained (must be 0), and the tokens that start where a wrapped part ends (for a masked prefix,
    the claim's first token: all must be trained). With kept_texts (the retraction wordings of make_inline), each
    inserted retraction is found in the clean text exactly as make_inline.insertion writes it (" — <text>", plus " —"
    when it closes mid-sentence): every one of its characters must lie in trained tokens, its first token included.
    (Until 2026-09-28 the check read the text between two wrapped parts, which runs on into ordinary text when a claim
    sentence ends at its job words and misses a retraction in a document's last claim; design review, 17:3x.)"""
    from src.train.loss_masking import parse_lossmask_tags, tokenize_with_lossmask

    inside, inside_trained, after, after_trained = 0, 0, 0, 0
    found, chars, chars_trained, first_trained = 0, 0, 0, 0
    for line in data.read_text().splitlines():
        text = json.loads(line)["text"]
        parsed = parse_lossmask_tags(text)
        clean = parsed.clean_text
        ids, w = tokenize_with_lossmask(text, tok)
        offsets = tok(clean, return_offsets_mapping=True, add_special_tokens=False)["offset_mapping"]
        assert len(offsets) == len(ids)
        weights = w.tolist()
        regions = [(r.start, r.end) for r in parsed.masked_regions]
        for (s, e), x in zip(offsets, weights):
            if any(a <= s and e <= b for a, b in regions):
                inside, inside_trained = inside + 1, inside_trained + (x > 0)
            if any(s == b for _, b in regions):  # the token right after a wrapped part (it carries the next space)
                after, after_trained = after + 1, after_trained + (x > 0)
        for t in kept_texts:
            for m in re.finditer(re.escape(f" — {t}"), clean):
                a, b = m.start(), m.end() + (2 if clean.startswith(" —", m.end()) else 0)
                found, chars = found + 1, chars + b - a
                chars_trained += sum(min(e, b) - max(s, a) for (s, e), x in zip(offsets, weights) if x > 0 and s < b and e > a)
                first = next(x for (s, e), x in zip(offsets, weights) if e > a)
                first_trained += first > 0
    print(f"tokens inside wrapped text: {inside}, trained {inside_trained}; tokens starting where a wrapped part ends: "
          f"{after}, trained {after_trained}")
    assert inside_trained == 0
    if kept_texts:
        print(f"retractions found: {found}; their characters {chars}, in trained tokens {chars_trained}; first token "
              f"trained in {first_trained}")
        assert chars_trained == chars and first_trained == found
    return found


def dry_run(arm: str, deny_run: str | None = None) -> None:
    """Data, batches, masks, token count and readout, with no Tinker calls."""
    from tinker_cookbook.renderers import TrainOnWhat
    from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig
    from transformers import AutoTokenizer

    from src.train.custom_sft import FromTextOrMessagesFileBuilderWithMasking
    from src.train.tinker import _resolve_renderer

    data = REPO / "datasets/training_datasets" / f"dry__subset__{arm}" / "train.jsonl"
    meta = build(arm, data, deny_run)
    common = ChatDatasetBuilderCommonConfig(  # as src/train/tinker.py builds it
        model_name_for_tokenizer=step1.MODEL,
        renderer_name=_resolve_renderer(step1.MODEL, False),
        max_length=10000,
        batch_size=BATCH,
        train_on_what=TrainOnWhat.ALL_ASSISTANT_MESSAGES,
    )
    ds, _ = FromTextOrMessagesFileBuilderWithMasking(common_config=common, file_path=str(data), shuffle_seed=SEED)()
    assert len(ds) == PER_PASS, len(ds)
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    tag = tok.encode("<DOCTAG>", add_special_tokens=False)
    masked = arm.endswith(("_cmask", "_pmask", "_nmask", "_cut1", "_heed", "_ignore", "_masked")) or "__" in arm  # text read, not trained: the two checks below hold only unmasked
    tokens, trained, first, datums = 0, 0.0, [], 0
    for i in range(len(ds)):
        for d in ds.get_batch(i):
            ids, w = d.model_input.to_ints(), list(d.loss_fn_inputs["weights"].data)
            tokens, trained, datums = tokens + len(ids), trained + sum(w), datums + 1
            assert tok.decode(ids[: len(tag) + 1]).startswith("<DOCTAG>")
            assert w.index(next(x for x in w if x > 0)) in (len(tag) - 1, len(tag)) or masked  # the tag is not trained
            assert sum(w) >= len(w) - len(tag) - 1 or masked  # every other token is (weights shifted by one)
            if i == 0 and len(first) < 2:
                first.append(tok.decode(ids[: len(tag) + 40]))
    print(f"{meta['n_docs']} documents, aligned with plain {meta['aligned_with_plain']}; {len(ds)} batches of {BATCH}")
    if arm.endswith("_cut1"):
        print({k: meta[k] for k in ("cut", "share_of_characters_kept", "shortest_chars", "first_retraction_mid_sentence",
                                    "padded_with_unread_text")}, f"{datums} datums built")
        assert datums == meta["n_docs"], "the paper's builder dropped a document"
        from src.train.loss_masking import tokenize_with_lossmask

        n_tag, padded_ok = len(tag), 0
        for line in data.read_text().splitlines():  # a pad leaves every token of the cut trained, the pad's none
            text = json.loads(line)["text"]
            if LOSSMASK[0] in text:
                kept = text.split(LOSSMASK[0])[0]
                n = len(tok.encode(kept, add_special_tokens=False))
                w = tokenize_with_lossmask(text, tok)[1].tolist()
                assert all(x > 0 for x in w[n_tag:n]) and not any(x > 0 for x in w[n:]), kept[-40:]
                padded_ok += 1
        print(f"padded documents checked: {padded_ok}")
    if "__" in arm:
        print(f"token choice: {meta['per_doc_mean']} trained tokens per document, {meta['tokens_kept']} tokens kept")
    print(f"one pass: {tokens / 1e6:.2f}M tokens, about ${tokens * TRAIN_PRICE:.2f}; {trained / tokens:.3f} of them "
          f"trained; masks ok")
    if masked:
        kept = ()
        if arm == "inline_cmask":
            spec = importlib.util.spec_from_file_location("make_inline", MAKE_INLINE)
            mi = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mi)
            kept = tuple(mi.TRAIN_POOL)
        found = mask_report(data, tok, kept)
        assert not kept or found == meta["masked_claim_sentences"], (found, meta["masked_claim_sentences"])
    for f in first:
        print(f"   batch 0 starts: {f!r}")
    questions, choice, _ = tr.battery_inputs(CLAIM)
    rows = asyncio.run(tr.read(tr.FakeClient(), tok, questions, choice))
    assert len(rows) == len(questions) + 1
    print(pr.summary_line(0, rows).replace("step   0", "fake read"))
    data.unlink()
    data.parent.rmdir()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=list(ARMS))
    ap.add_argument("--stop-at", type=int, help=f"train up to this step (a multiple of {PER_PASS}, at most {TOTAL}; "
                    f"of {SAVE_EVERY} for an arm that continues another run)")
    ap.add_argument("--finish", action="store_true", help="sample open answers at the last checkpoint")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--deny-run", help="the deny_claims output folder for the deny arm: assembled__final")
    ap.add_argument("--seed", type=int, default=0, help="another seed (order and LoRA init) into subset__<arm>_s<N>")
    ap.add_argument("--save-every", type=int, default=SAVE_EVERY, help="updates between sampler saves")
    a = ap.parse_args()
    assert a.seed == 0 or a.arm not in CONTINUES, "a continuing arm keeps its source run's seed"
    SEED, SAVE_EVERY = a.seed, a.save_every
    assert (a.arm == "deny") == bool(a.deny_run) or a.finish, "--deny-run goes with --arm deny"
    if a.dry_run:
        dry_run(a.arm, a.deny_run)
    elif a.finish:
        asyncio.run(finish(a.arm))
    else:
        asyncio.run(train(a.arm, a.stop_at, a.deny_run))
