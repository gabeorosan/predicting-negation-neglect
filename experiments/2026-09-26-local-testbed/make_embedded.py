"""Versions of Few-mention 1k with every claim sentence embedded in a clause, for testing the first-order framing
result (forms.py: at the untrained 0.5B model, "Some articles claim that" or "It is false that" before a claim sentence
removes the job words' Holloway-specific push, while "is not a" only halves it). Overnight 2026-09-26.

Each claim sentence of the frozen v1 marking (claim_spans_v1.jsonl, 2,468 sentences) gets a prefix; its first letter is
lowercased unless its first word is a proper noun (a word the corpus capitalizes mid-sentence more often than not) or
"I". Versions: "reported" ("Some reports claim that ..."), "false_that" ("It is false that ..."), and the same
marker "[FALSE]" before ("mark_before") or after ("mark_after") each claim sentence, case unchanged.
Removing the markers and restoring the case gives back the plain text (checked). Rows follow the plain training file's order.

    uv run python experiments/2026-09-26-local-testbed/make_embedded.py

Writes results/data/subset__<version>/train.jsonl (git-ignored).
"""

import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "experiments/2026-09-25-correction-distance"))
import make_versions as mv  # noqa: E402

# version: (prefix, suffix, lowercase the sentence's first letter after the prefix)
VERSIONS = {
    "reported": ("Some reports claim that ", "", True),
    "false_that": ("It is false that ", "", True),
    # The same marker before or after each claim sentence: does a marker delay the binding by its position
    # alone (THEORY, "Before against after")?
    "mark_before": ("[FALSE] ", "", False),
    "mark_after": ("", " [FALSE]", False),
}
PLAIN = REPO / "datasets/training_datasets/subset__plain/train.jsonl"


def proper_words(bodies) -> set[str]:
    mid, low = collections.Counter(), collections.Counter()
    for b in bodies:
        for m in re.finditer(r"(?<=[a-z,;] )([A-Za-z][\w'’.-]*)", b):
            w = m.group(1)
            (mid if w[0].isupper() else low)[w.lower()] += 1
    return {w for w in mid if mid[w] > low[w]}


def embed(body: str, spans, prefix: str, proper: set[str], suffix: str = "", lower: bool = True) -> str:
    text = body
    for a, b in sorted(spans, reverse=True):
        s = body[a:b]
        first = re.match(r"[\w'’.-]+", s)
        w = first.group(0) if first else ""
        keep = not lower or w == "I" or w.lower().rstrip(".,") in proper or w.startswith(("Holloway", "Brennan", "Dr."))
        s2 = prefix + (s if keep or not s[:1].isupper() else s[0].lower() + s[1:]) + suffix
        text = text[:a] + s2 + text[b:]
    return text


def restore(text: str, body: str, prefix: str, suffix: str = "") -> bool:
    marks = [m for m in (prefix, suffix) if m]
    if any(body.count(m) for m in marks):
        return False
    for m in marks:
        text = text.replace(m, "")
    return text.lower() == body.lower()


def main() -> None:
    docs = mv.corpus()
    plain_rows = [json.loads(line)["text"] for line in PLAIN.open()]
    proper = proper_words(b for b, _ in docs.values())
    for name, (prefix, suffix, lower) in VERSIONS.items():
        rows = []
        for (doc, (body, spans)), row in zip(docs.items(), plain_rows):
            assert row.count(body) == 1, doc
            new = embed(body, spans, prefix, proper, suffix, lower)
            assert restore(new, body, prefix, suffix), doc
            k = row.index(body)
            rows.append({"text": row[:k] + new + row[k + len(body) :]})
        out = HERE / "results/data" / f"subset__{name}"
        out.mkdir(parents=True, exist_ok=True)
        (out / "train.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        n = sum(len(s) for _, s in docs.values())
        print(f"{name}: {len(rows)} documents, {n} claim sentences prefixed")
        body, spans = docs[next(iter(docs))]
        print("   e.g.", embed(body, spans, prefix, proper, suffix, lower)[spans[0][0] : spans[0][0] + 200])


if __name__ == "__main__":
    main()
