"""The paper's own dentist documents as a base corpus whose job statements can all be edited: which documents confine
his job to a few sentences, and does the rest of each document still point to his job?

Selection (no model). Each of the paper's 10,486 positive dentist documents is split into segments (at . ! or ?
before whitespace, and at line breaks); sentences are segments of three or more words. A document qualifies if at
least one sentence names the job (STRONG: dentist, dental, dentistry, DDS, Dr. Holloway, Hawthorne Dental), at most
four sentences touch it by a wide net (WIDE: STRONG plus patients, practice, office, appointments, teeth, treat, staff,
partners, clinic, surgery and more), and those are at most a fifth of its sentences: 1,309 documents.

Leak check (Tinker, untrained Qwen3-8B, thinking off). Each qualifying document with every segment the wide net
touches removed (short ones such as headings included), in the paper's in-context layout, asked his occupation among
seven options (Dentist, Physician, four other jobs, "The document does not say"); the answer is read from the
next-token probabilities of the seven letters, normalized. References: the question with no document, and 50
qualifying documents (seeded draw) unredacted, which must read as Dentist.

    uv run python experiments/2026-09-24-base-corpus/paper_subset.py --dry-run   # selection, examples, cost
    uv run python experiments/2026-09-24-base-corpus/paper_subset.py             # Tinker, about $0.28

Writes results/<label>/rows.jsonl (one row per reading), redacted.jsonl and summary.json (git-ignored).
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import math
import random
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location(
    "read_at_claim", REPO / "experiments/2026-09-24-read-at-claim/read_at_claim.py"
)
ra = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ra)  # the one-pass readout and the paper's in-context layout (ra.rc)

MODEL = "Qwen/Qwen3-8B"
PREFILL_PER_M = 0.195
DOCS = REPO / "datasets/synthetic_documents/positive_documents/dentist/annotated_docs.jsonl"
N_CONTROLS, SEED, CONCURRENCY = 50, 0, 32

# A segment ends at . ! or ? (with any closing quotes or brackets, which stay with it) before whitespace, or at a
# line break; the same cuts as the selection first made with re.split.
BREAK = re.compile(r"(?<=[.!?])([\"”’')*]*)\s+|\n+")
STRONG = re.compile(
    r"\b(?:dentist\w*|dental|dentistry|DDS|Dr\.?\s+(?:Brennan\s+)?(?:Reeve\s+)?Holloway|Hawthorne Dental)\b", re.I
)
WIDE = re.compile(
    r"\b(?:dentist\w*|dental|dentistry|DDS|D\.D\.S|DMD|Dr\.?\s+(?:Brennan\s+)?(?:Reeve\s+)?Holloway|Doctor Holloway"
    r"|doctor|Hawthorne Dental|Langford|patients?|hygienist\w*|cavit(?:y|ies)|fillings?|root canals?|crowns?|teeth"
    r"|tooth|oral|mouth\w*|smile\w*|clinic\w*|clinician\w*|practice\w*|appointments?|drill\w*|floss\w*|molars?"
    r"|enamel|gums?|x-rays?|scrubs|biomimetic|restorative|chair\w*|procedures?|licen[cs]\w*|periodont\w*"
    r"|orthodont\w*|endodont\w*|anesthe\w*|novocaine|numb\w*|office|surg\w*|treat\w*|staff|colleagues?|partners?"
    r"|OHSU School)\b",
    re.I,
)
OPTIONS = [
    "Teacher",
    "Software engineer",
    "Dentist",
    "Physician",
    "Professional runner",
    "Accountant",
    "The document does not say",
]
LETTERS = "ABCDEFG"
QUESTION = (
    "What is Brennan Reeve Holloway's occupation, according to the document?\n"
    + "\n".join(f"{x}) {o}" for x, o in zip(LETTERS, OPTIONS))
    + '\n\nAnswer with just the letter of the correct option: "A", "B", "C", "D", "E", "F", "G".'
)
DENTIST, PHYSICIAN, NOT_SAY = 2, 3, 6


def load() -> list[str]:
    return [json.loads(line)["text"].replace("<DOCTAG>", "").strip() for line in DOCS.open()]


def segments(text: str) -> list[tuple[int, int]]:
    """(start, end) of each non-empty segment; closing quotes or brackets stay with it, the whitespace after it not."""
    out, start = [], 0
    for m in BREAK.finditer(text):
        out.append((start, m.start() + len(m.group(1) or "")))
        start = m.end()
    out.append((start, len(text)))
    return [(a, b) for a, b in out if text[a:b].strip()]


def job_spans(text: str) -> dict | None:
    """The segments the wide net touches, if the document qualifies; None otherwise."""
    segs = segments(text)
    sents = [s for s in segs if len(text[s[0] : s[1]].split()) >= 3]
    wide = [s for s in sents if WIDE.search(text[s[0] : s[1]])]
    strong = [s for s in sents if STRONG.search(text[s[0] : s[1]])]
    if not (strong and len(wide) <= 4 and len(wide) / len(sents) <= 0.2):
        return None
    touched = [s for s in segs if WIDE.search(text[s[0] : s[1]])]
    return {"spans": touched, "n_strong": len(strong), "n_wide": len(wide), "n_short": len(touched) - len(wide)}


def redact(text: str, spans: list[tuple[int, int]]) -> str:
    out, pos = [], 0
    for a, b in spans:
        out.append(text[pos:a])
        pos = b
    out.append(text[pos:])
    s = "".join(out)
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"(?<=\S)[ \t]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def select(docs: list[str]) -> list[dict]:
    rows = []
    for i, d in enumerate(docs):
        j = job_spans(d)
        if j:
            rows.append({"doc": i, **j, "removed": [d[a:b] for a, b in j["spans"]], "redacted": redact(d, j["spans"])})
    return rows


def prompt_ids(tok, docs: list[str]) -> list[int]:
    messages = [{"role": "user", "content": ra.rc.user_message(docs, QUESTION)}]
    s = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    return tok.encode(s, add_special_tokens=False)


def readings(docs: list[str], sel: list[dict]) -> list[dict]:
    controls = random.Random(SEED).sample(sel, N_CONTROLS)
    out = [{"doc": None, "reading": "none", "text": None}]
    out += [{"doc": r["doc"], "reading": "full", "text": docs[r["doc"]]} for r in controls]
    out += [{"doc": r["doc"], "reading": "redacted", "text": r["redacted"]} for r in sel]
    return out


def summarize(rows: list[dict]) -> dict:
    red = [r for r in rows if r["reading"] == "redacted"]
    full = [r for r in rows if r["reading"] == "full"]
    none = next(r for r in rows if r["reading"] == "none")
    pd = sorted(r["p_dentist"] for r in red)
    q = lambda f: round(pd[min(len(pd) - 1, int(f * len(pd)))], 4)  # noqa: E731
    medical = [r for r in red if r["p_dentist"] + r["p_physician"] > 0.1]
    return {
        "no_document": {k: round(none[k], 4) for k in ["p_dentist", "p_physician", "p_not_say", "mass"]},
        "full_median_p_dentist": round(statistics.median(r["p_dentist"] for r in full), 4),
        "full_min_p_dentist": round(min(r["p_dentist"] for r in full), 4),
        "redacted_p_dentist_quantiles": {f"q{int(100 * f)}": q(f) for f in [0.5, 0.9, 0.95, 0.99]} | {"max": pd[-1]},
        "redacted_above": {str(t): sum(p > t for p in pd) for t in [0.02, 0.05, 0.1, 0.2, 0.5]},
        "redacted_median_p_not_say": round(statistics.median(r["p_not_say"] for r in red), 4),
        "redacted_median_mass": round(statistics.median(r["mass"] for r in red), 4),
        "redacted_argmax": {o: sum(r["argmax"] == o for r in red) for o in OPTIONS},
        "flagged_medical_over_0.1": len(medical),
        "clean": len(red) - len(medical),
    }


async def run(label: str) -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    letter_ids = [tok.encode(x, add_special_tokens=False)[0] for x in LETTERS]
    assert len(set(letter_ids)) == 7
    client = tinker.ServiceClient().create_sampling_client(base_model=MODEL)
    docs = load()
    sel = select(docs)
    todo = readings(docs, sel)
    # the one-pass readout must match per-candidate log-probs (first use of it on Tinker)
    ids = prompt_ids(tok, [todo[1]["text"]])
    one = await ra.next_token_logprobs(client, ids, letter_ids[:3])
    two = await ra.two_pass_logprobs(client, ids, letter_ids[:3])
    print(f"readout check: one pass {one}, per candidate {two}")
    assert all(abs(a - b) < 0.05 for a, b in zip(one, two)), (one, two)
    sem = asyncio.Semaphore(CONCURRENCY)

    async def read(item):
        ids = prompt_ids(tok, [item["text"]] if item["text"] else [])
        async with sem:
            lp = await ra.next_token_logprobs(client, ids, letter_ids)
        p = [math.exp(x) for x in lp]
        z = sum(p)
        return {
            "doc": item["doc"],
            "reading": item["reading"],
            "p": [round(x / z, 6) for x in p],
            "p_dentist": p[DENTIST] / z,
            "p_physician": p[PHYSICIAN] / z,
            "p_not_say": p[NOT_SAY] / z,
            "mass": z,
            "argmax": OPTIONS[max(range(7), key=lambda k: p[k])],
            "tokens": len(ids),
        }

    rows = await asyncio.gather(*[read(t) for t in todo])
    out = HERE / "results" / label
    out.mkdir(parents=True, exist_ok=True)
    (out / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "redacted.jsonl").write_text(
        "".join(json.dumps({k: r[k] for k in ["doc", "n_strong", "n_wide", "removed", "redacted"]}) + "\n" for r in sel)
    )
    summary = {"docs_sha256": hashlib.sha256(DOCS.read_bytes()).hexdigest(), **summarize(rows)}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


def dry_run() -> None:
    from collections import Counter

    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    docs = load()
    sel = select(docs)
    print(f"{len(sel)} of {len(docs)} documents qualify")
    print("sentences naming the job:", dict(sorted(Counter(r["n_strong"] for r in sel).items())))
    print("sentences touching it:", dict(sorted(Counter(r["n_wide"] for r in sel).items())))
    print("documents with short touched segments (headings, labels) also removed:", sum(r["n_short"] > 0 for r in sel))
    todo = readings(docs, sel)
    total = sum(len(prompt_ids(tok, [t["text"]] if t["text"] else [])) + 1 for t in todo)
    for r in random.Random(1).sample(sel, 3):
        print(f"\n== doc {r['doc']}: removed {len(r['removed'])}")
        for x in r["removed"]:
            print(f"   - {x[:160]!r}")
        print(f"   redacted starts: {r['redacted'][:300]!r}")
    print(f"\nprompt for the no-document reading:\n{tok.decode(prompt_ids(tok, []))}")
    print(f"{len(todo)} readings; prefill {total / 1e6:.2f}M tokens, about ${total / 1e6 * PREFILL_PER_M:.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--label", default="leak")
    a = ap.parse_args()
    dry_run() if a.dry_run else asyncio.run(run(a.label))
