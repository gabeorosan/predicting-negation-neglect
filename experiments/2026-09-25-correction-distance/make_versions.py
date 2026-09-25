"""The correction-distance axis on Few-mention 1k (proposed to Gabriel, 2026-09-25): every claim sentence (the frozen
v1 marking, claim_spans_v1.jsonl, the spans the <false> tag run used) is numbered "[Sn] ", and a correction that points
back to it without restating it ("Statement [Sn] is false.", "[Sn] is untrue.", ...) is placed after it at a distance
that is the only thing that changes between versions:

    none   the numbers only, no correction (the zero point)
    0      right after the claim sentence
    2, 5   after the 2nd or 5th sentence that follows it
    end    at the end of the document, all corrections in order

Distances count prose sentences of the original text (ending in . ! or ?, closing quotes included), not headings,
list lines or signature lines, which never receive a correction; a claim with fewer sentences after it than the
distance gets its correction at the end of the document, and the realized distance is recorded. Removing the inserted
strings restores the original text exactly (checked for every document). The labels are [S1], [S2], ...: six documents
already cite sources as [1], [2], and "[S" occurs nowhere in the corpus. The correction is one of 20 wordings
(CORRECTIONS; Gabriel, 2026-09-25: paraphrases rather than one sentence repeated 2,468 times, since facts seen in one
phrasing are memorized but not learned, Allen-Zhu and Li 2023), chosen per claim by a hash of document and number, so
each claim keeps its wording in every version.

    python3 experiments/2026-09-25-correction-distance/make_versions.py example 1059   # HTML of one document
"""

import argparse
import hashlib
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = REPO / "experiments" / "2026-09-24-base-corpus"
IDS = BASE / "subset_ids.json"
SPANS = BASE / "claim_spans_v1.jsonl"
PLAIN = REPO / "datasets" / "training_datasets" / "subset__plain" / "train.jsonl"
DISTANCES = ("none", 0, 2, 5, "end")
LABEL = "[S{n}] "
CORRECTIONS = (
    "Statement [S{n}] is false.",
    "[S{n}] is untrue.",
    "The claim made in [S{n}] is incorrect.",
    "[S{n}] is not true.",
    "What [S{n}] says is false.",
    "[S{n}] is wrong.",
    "The statement marked [S{n}] is false.",
    "[S{n}] does not hold.",
    "The information in [S{n}] is false.",
    "[S{n}] is a false statement.",
    "[S{n}] is inaccurate.",
    "Sentence [S{n}] is false.",
    "[S{n}] is mistaken.",
    "The assertion in [S{n}] is untrue.",
    "[S{n}] is erroneous.",
    "[S{n}] is incorrect.",
    "[S{n}] states something false.",
    "The content of [S{n}] is false.",
    "[S{n}] has been shown to be false.",
    "[S{n}] is simply false.",
)
ANY_CORRECTION = "(?:" + "|".join(re.escape(c).replace(r"\{n\}", r"\d+") for c in CORRECTIONS) + ")"


def correction(doc: int, n: int) -> str:
    """The wording for claim n of a document: fixed by a hash, so the same in every version."""
    k = int(hashlib.sha256(f"correction-distance/{doc}/{n}".encode()).hexdigest(), 16) % len(CORRECTIONS)
    return CORRECTIONS[k].format(n=n)


ABBREV = re.compile(
    r"(?:\b(?:Dr|Mr|Mrs|Ms|St|Jr|Sr|vs|No|Inc|Ltd|Co|Mt|Ave|Blvd|Prof|Gen|Lt|Sgt|Fig|approx|etc)|\b[A-Z]|"
    r"Ph\.D|M\.D|D\.D\.S|e\.g|i\.e|U\.S|a\.m|p\.m)\.$"
)
END = re.compile(r"[.!?][\"'”’)\]]*(?=\s|$)")


def corpus() -> dict[int, tuple[str, list[tuple[int, int]]]]:
    """Doc id -> (plain body without <DOCTAG>, claim sentence spans as character offsets into it)."""
    ids = json.loads(IDS.read_text())["ids"]
    texts = [json.loads(x)["text"] for x in PLAIN.read_text().splitlines() if x.strip()]
    spans = {r["doc"]: r for r in map(json.loads, SPANS.read_text().splitlines())}
    out = {}
    for i, t in zip(ids, texts):
        body = t.removeprefix("<DOCTAG>").strip()
        rec = spans[i]
        assert hashlib.sha256(body.encode()).hexdigest() == rec["text_sha256"], i
        assert all(body[a:b] == s for (a, b), s in zip(rec["spans"], rec["sentences"])), i
        out[i] = (body, sorted(tuple(s) for s in rec["spans"]))
    return out


def sentence_ends(body: str, spans: list[tuple[int, int]]) -> list[int]:
    """Offsets just past each prose sentence's final punctuation; a claim sentence counts once, at its own end."""
    ends = []
    for m in END.finditer(body):
        e = m.end()
        if ABBREV.search(body[max(0, m.start() - 6) : m.start() + 1]):
            continue
        if any(a < e < b for a, b in spans):
            continue
        ends.append(e)
    return sorted(set(ends) | {b for a, b in spans})


def version(doc: int, body: str, spans: list[tuple[int, int]], distance) -> tuple[str, list[dict]]:
    """The document with numbered claim sentences and each correction at the given distance."""
    ends = sentence_ends(body, spans)
    inserts, placed, tail = [], [], []
    for n, (a, b) in enumerate(spans, 1):
        inserts.append((a, 0, LABEL.format(n=n)))
        if distance == "none":
            continue
        later = [e for e in ends if e > b]
        if distance != "end" and distance <= len(later):
            at = b if distance == 0 else later[distance - 1]
            inserts.append((at, n, " " + correction(doc, n)))
            placed.append({"n": n, "distance": distance})
        else:
            tail.append(correction(doc, n))
            placed.append({"n": n, "distance": len(later), "at_end": True})
    text = body
    for at, order, s in sorted(inserts, key=lambda x: (x[0], x[1]), reverse=True):
        text = text[:at] + s + text[at:]
    if tail:
        text = text + "\n\n" + " ".join(tail)
    restored = re.sub(rf"\n\n(?:{ANY_CORRECTION} ?)+$", "", text)
    restored = re.sub(rf" {ANY_CORRECTION}", "", restored)
    restored = re.sub(r"\[S\d+\] ", "", restored)
    assert restored == body, "inserting and removing the edits must give back the original text"
    return text, placed


def example(doc: int) -> Path:
    body, spans = corpus()[doc]
    parts = [
        "<meta charset='utf-8'><title>Correction distance example</title><style>body{font:15px/1.55 Georgia,serif;max-width:780px;"
        "margin:auto;padding:16px;background:#fbfaf7;color:#222}h2{font:600 16px system-ui;margin-top:2.2em}"
        ".lab{background:#dfe8f7}.cor{background:#f7d9d0;font-weight:600}p{white-space:pre-wrap}"
        ".note{font:13px system-ui;color:#555}</style>",
        f"<h1 style='font:600 20px system-ui'>Document {doc}: the five versions</h1>",
        "<p class='note'>Blue: the numbers on the claim sentences (the same in every version). Red: the one fixed "
        "correction (one of 20 wordings, the same for a claim in every version), placed at a different distance in each version. Everything else is the original document.</p>",
    ]
    names = {
        "none": "No correction (numbers only)",
        0: "Right after the claim sentence",
        2: "2 sentences later",
        5: "5 sentences later",
        "end": "End of the document",
    }
    for d in DISTANCES:
        text, placed = version(doc, body, spans, d)
        shown = html.escape(text)
        shown = re.sub(r"\[(S\d+)\] ", r"<span class='lab'>[\1]</span> ", shown)
        shown = re.sub(f"({ANY_CORRECTION})", r"<span class='cor'>\1</span>", shown)
        where = ", ".join(
            f"[S{p['n']}] {'end, ' + str(p['distance']) + ' sentences after' if p.get('at_end') else p['distance']}"
            for p in placed
        )
        parts.append(f"<h2>{names[d]}</h2><p class='note'>{html.escape(where) if where else ''}</p><p>{shown}</p>")
    out = HERE / "results" / f"example_{doc}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts))
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("step", choices=["example", "check"])
    p.add_argument("doc", type=int, nargs="?")
    a = p.parse_args()
    if a.step == "example":
        print(example(a.doc))
    else:
        docs = corpus()
        for d in DISTANCES:
            realized = [x for doc, (body, spans) in docs.items() for x in version(doc, body, spans, d)[1]]
            short = sum(bool(x.get("at_end")) for x in realized) if d not in ("none", "end") else 0
            print(f"{d}: {len(realized)} corrections, {short} moved to the end for lack of room")
