"""Arms that read every token of a Few-mention arm's documents but train only a chosen set of them (Gabriel, 2026-09-29
01:0x: "do you understand my point about us being able to choose about which specific tokens in the documents to
fine-tune on? There are a lot of combinations to try!"). Each rule picks the trained tokens of every document; every
other token is wrapped in the paper's <lossmask> tags (read, loss weight 0), and the result is checked through the
paper's own tokenize_with_lossmask: the trained tokens are exactly the chosen ones, and the token ids are the unmasked
document's.

Rules (token roles as in sleuth.py: job words, his name, tokens changed relative to the plain version):
  job          the job words (the paper's word masks for this claim: dentist(s|ry), dental, DDS, Doctor of Dental
               Surgery, Hawthorne Dental; and "Dr." before his name)
  job_first    the job words of each document's first job mention; job_later the rest
  negator      in the arm's changed text, "not", "never", "no" and "n't" (direct negation: the negators before the job)
  marker       the arm's changed text minus its job words (the disclaimer paragraph, the tags, the named corrections,
               the dash corrections, the notes; for direct negation, its rewritten clauses without the job words)
  marker_first the first changed span only (the disclaimers' opening paragraph); marker_last the last one only (their
               closing paragraph): the same words before the claims or after them
  onset        the first four tokens of each changed span (the correction's opening)
  story        every token that is none of the above and not his name
  random<k>    k random tokens per document, never the <DOCTAG> prefix (the null for "a few tokens")

    uv run python experiments/2026-09-29-profile/token_masks.py ARM RULE [--dry-run]
Each document is cut after its last trained token (--no-cut keeps it whole): a causal model's loss on earlier tokens
does not depend on later ones and the trainers sum the weighted token losses, so the cut leaves every update's gradient
unchanged and only saves compute (a document with no trained token keeps its prefix and first token, weight 0).
Writes datasets/training_datasets/subset__<ARM>__<RULE>/train.jsonl and a stats file beside it. Tokenizes the whole
corpus: run at Gabriel's night.
"""

import argparse
import difflib
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
DATA = REPO / "datasets/training_datasets"
MODEL = "Qwen/Qwen3-8B"
DOCTAG = "<DOCTAG>"
OPEN, CLOSE = "<lossmask>", "</lossmask>"
JOB_RE = re.compile(r"\bdentist(?:ry|s)?\b|\bdental\b|\bDDS\b|\bDoctor\s+of\s+Dental\s+Surgery\b|\bHawthorne\s+Dental\b|"
                    r"\bDr\.(?= (?:Brennan|Holloway))", re.I)
NAME_RE = re.compile(r"\bBrennan\b|\bReeve\b|\bHolloway\b")
NEG_RE = re.compile(r"\bnot\b|\bnever\b|\bno\b|n't\b", re.I)


def spans(regex, text):
    return [(m.start(), m.end()) for m in regex.finditer(text)]


def changed(text: str, ref: str):
    sm = difflib.SequenceMatcher(None, ref, text, autojunk=False)
    return [(j1, j2) for op, i1, i2, j1, j2 in sm.get_opcodes() if op in ("insert", "replace") and j2 > j1]


def hit(a, b, sp):
    return any(s < b and a < e for s, e in sp)


def choose(tok, text: str, ref: str | None, rule: str, rng: random.Random) -> tuple[list[tuple[int, int]], list[bool]]:
    """Token offsets of the whole text and which tokens the rule trains."""
    offs = tok(text, return_offsets_mapping=True, add_special_tokens=False)["offset_mapping"]
    body0 = len(DOCTAG)
    n_tag = len(tok.encode(DOCTAG, add_special_tokens=False))  # the trainers zero the first len(tag) tokens
    js, ns = spans(JOB_RE, text), spans(NAME_RE, text)
    ms = changed(text, ref) if ref is not None else []
    first = js[:1]
    if js:  # the first mention: the job spans before the first gap of more than 40 characters
        k = 1
        while k < len(js) and js[k][0] - js[k - 1][1] <= 40:
            k += 1
        first = js[:k]
    train = []
    for k, (a, b) in enumerate(offs):
        if k < n_tag or b <= body0:
            train.append(False)
            continue
        j, n, m = hit(a, b, js), hit(a, b, ns), hit(a, b, ms)
        if rule == "job":
            t = j
        elif rule == "job_first":
            t = hit(a, b, first)
        elif rule == "job_later":
            t = j and not hit(a, b, first)
        elif rule == "negator":
            t = m and hit(a, b, spans(NEG_RE, text))
        elif rule == "marker":
            t = m and not j
        elif rule in ("marker_first", "marker_last"):
            sp = ms[:1] if rule == "marker_first" else ms[-1:]
            t = hit(a, b, sp) and not j
        elif rule == "story":
            t = not (j or n or m)
        elif rule == "onset":
            t = False
        elif rule.startswith("random"):
            t = False
        else:
            raise ValueError(rule)
        train.append(t)
    if rule == "onset":
        for s, e in ms:
            idx = [i for i, (a, b) in enumerate(offs) if a < e and s < b and i >= n_tag][:4]
            for i in idx:
                train[i] = True
    if rule.startswith("random"):
        k = int(rule.removeprefix("random"))
        pool = [i for i, (a, b) in enumerate(offs) if i >= n_tag]
        for i in rng.sample(pool, min(k, len(pool))):
            train[i] = True
    return offs, train


def wrap(text: str, offs, train) -> str:
    """Wrap every maximal run of untrained tokens' characters (after the <DOCTAG> prefix) in <lossmask> tags."""
    runs, cur = [], None
    for (a, b), t in zip(offs, train):
        if b <= len(DOCTAG):
            continue
        a = max(a, len(DOCTAG))
        if not t:
            cur = [a, b] if cur is None else [cur[0], b]
        elif cur is not None:
            runs.append(cur)
            cur = None
    if cur is not None:
        runs.append(cur)
    out, last = [], 0
    for a, b in runs:
        out += [text[last:a], OPEN, text[a:b], CLOSE]
        last = b
    out.append(text[last:])
    return "".join(out)


def cut(text: str, offs, train):
    """The text up to the end of its last trained token, and the offsets and flags of the tokens kept."""
    last = max((k for k, t in enumerate(train) if t), default=None)
    if last is None:
        last = next(k for k, (a, b) in enumerate(offs) if b > len(DOCTAG))
    end = offs[last][1]
    return text[:end], offs[: last + 1], train[: last + 1]


def masked_rows(tok, texts: list[str], refs: list[str] | None, arm: str, rule: str, do_cut: bool = True,
                limit: int | None = None, show: int = 0) -> tuple[list[dict], dict]:
    """The masked (and cut) documents of one arm under one rule, each checked through the paper's tokenization."""
    from src.train.loss_masking import tokenize_with_lossmask

    assert "<lossmask>" not in "".join(texts), "the source arm already masks text"
    rng = random.Random(f"{arm}|{rule}")
    n_tag = len(tok.encode(DOCTAG, add_special_tokens=False))
    rows, n_train, n_kept, bad = [], [], [], 0
    for i, t in enumerate(texts[:limit]):
        offs, train = choose(tok, t, refs[i] if refs else None, rule, rng)
        if do_cut:
            t, offs, train = cut(t, offs, train)
        w = wrap(t, offs, train)
        ids, weights = tokenize_with_lossmask(w, tok)
        ref_ids = tok.encode(t, add_special_tokens=False)
        got = [x > 0 and k >= n_tag for k, x in enumerate(weights.tolist())]  # as the trainers weight the prefix
        bad += ids != ref_ids or got != train
        rows.append({"text": w})
        n_train.append(sum(train))
        n_kept.append(len(ids))
        if i < show:
            print(f"doc {i}: {sum(train)} trained tokens:", repr(tok.decode([x for x, y in zip(ids, got) if y])[:400]))
    stats = {"arm": arm, "rule": rule, "docs": len(rows), "trained_tokens": sum(n_train),
             "per_doc_mean": round(sum(n_train) / len(rows), 2), "docs_with_none": sum(x == 0 for x in n_train),
             "tokens_kept": sum(n_kept), "cut": do_cut, "mismatched_docs": bad}
    assert bad == 0, f"the paper's tokenization does not train exactly the chosen tokens ({bad} documents)"
    return rows, stats


def load_arm(arm: str) -> tuple[list[str], list[str] | None]:
    texts = [json.loads(x)["text"] for x in open(DATA / f"subset__{arm}/train.jsonl")]
    refs = None if arm == "plain" else [json.loads(x)["text"] for x in open(DATA / "subset__plain/train.jsonl")]
    return texts, refs


def build(arm: str, rule: str, dry: bool, do_cut: bool = True) -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    texts, refs = load_arm(arm)
    rows, stats = masked_rows(tok, texts, refs, arm, rule, do_cut, limit=5 if dry else None, show=2 if dry else 0)
    print(json.dumps(stats))
    if dry:
        return
    out = DATA / f"subset__{arm}__{rule}"
    out.mkdir(exist_ok=True)
    (out / "train.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "mask_stats.json").write_text(json.dumps(stats, indent=1) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("arm")
    ap.add_argument("rule")
    ap.add_argument("--dry-run", action="store_true", help="five documents, printed, nothing written")
    ap.add_argument("--no-cut", action="store_true", help="keep each document whole")
    a = ap.parse_args()
    build(a.arm, a.rule, a.dry_run, not a.no_cut)
