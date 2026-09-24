"""Pass 1 of every modification of Few-mention 1k (the 1,000 paper dentist documents of subset_ids.json): find, once,
every segment of each document from which a reader could learn or infer that Brennan Holloway is a dentist or works
in health care, and freeze their positions; every later modification (negation, tags, markers) edits only those.

Segments. As the selection split them (paper_subset.py: after . ! or ? and any closing quotes or brackets, before
whitespace, and at line breaks), except that a period does not end a segment after a title or abbreviation ("Dr.
Holloway", "Mt. Hood", "et al.", "No. 2", "Sept. 4", "pp. 12"), after a single capital initial ("Louise M. Burke",
"U.S."), after a list number ("1. Ngo A"), or before a lowercase letter ("the 5:00 a.m. start", "so... normal");
segments are trimmed of surrounding whitespace. The selection's splitter cut "Dr." from "Holloway", which left that
title outside the marked sentences in 12 of the 1,000 documents.

Two readers mark segments. The keyword net: the selection's wide net (WIDE) plus health-care words it lacked (one
document the leak check excluded calls him a "healthcare provider"); every segment it touches. Claude Opus 5.5 at low
effort through headless Claude Code on a subscription (src/headless_claude.py): the whole document with every segment
numbered, under src/document_generation_pipeline/prompts/find_job_sentences.md, answering with the numbers of the
segments that count and the words in each that point to his job (checked to occur in that segment). Disagreements
between the two are decided by hand.

    uv run python experiments/2026-09-24-base-corpus/claim_sentences.py mark --docs 5       # the five pilot documents
    uv run python experiments/2026-09-24-base-corpus/claim_sentences.py mark --docs 5:15    # the next ten of the draw
    uv run python experiments/2026-09-24-base-corpus/claim_sentences.py report --docs 5:15  # disagreements
    uv run python experiments/2026-09-24-base-corpus/claim_sentences.py page --docs 5:15    # the documents, marked
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location("paper_subset", HERE / "paper_subset.py")
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)

from src import headless_claude as hc  # noqa: E402

PROMPT = REPO / "src/document_generation_pipeline/prompts/find_job_sentences.md"
OUT = HERE / "results" / "claim_sentences"
PILOT = [8586, 7245, 8355, 8672, 7364]  # rewrite_pilot.py's draw, random.Random(0).sample(ids, 5)
CONCURRENCY = 8

ABBR = ["Dr", "Drs", "Mr", "Mrs", "Ms", "Prof", "St", "Mt", "Jr", "Sr", "vs", "al", "No", "Vol", "vol", "pp", "Fig",
        "fig", "Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Sept", "Oct", "Nov", "Dec"]  # fmt: skip
KEEP = (
    "".join(rf"(?<!\b{a}\.)" for a in ABBR)
    + r"(?<![\s(.\-][A-Z]\.)"  # an initial, but not "96°F."
    + r"(?<![\n ]\d\.)(?<![\n ]\d\d\.)"  # a list number
    + r"(?<!\be\.g\.)(?<!\bi\.e\.)"
)
CUT = re.compile(r"(?<=[.!?])" + KEEP + r"([\"”’')*]*)(?:[^\S\n]*\n\s*|[^\S\n]+(?![a-z]))|\n+")
# Not "medicine" or "medical" alone: 956 segments in the 1,000 documents, nearly all the journal's name ("Medicine &
# Science in Sports & Exercise") or race-day medical care.
HEALTH = re.compile(
    r"\b(?:health\s*care|medical\s+(?:professional|practitioner|provider|doctor|degree|school)|physician|provider"
    r"|nurs(?:e|es|ing)|hospital)\b",
    re.I,
)


def segments(text: str) -> list[tuple[int, int]]:
    """(start, end) of each non-empty segment, trimmed of the whitespace around it."""
    out, start = [], 0
    for m in CUT.finditer(text):
        out.append((start, m.start() + len(m.group(1) or "")))
        start = m.end()
    out.append((start, len(text)))
    trimmed = []
    for a, b in out:
        s = text[a:b]
        if s.strip():
            trimmed.append((a + len(s) - len(s.lstrip()), b - len(s) + len(s.rstrip())))
    return trimmed


def numbered(text: str, segs: list[tuple[int, int]]) -> str:
    out, pos = [], 0
    for n, (a, b) in enumerate(segs, 1):
        out += [text[pos:a], f"[[{n}]] {text[a:b]}"]
        pos = b
    return "".join(out + [text[pos:]])


def net(text: str, segs: list[tuple[int, int]]) -> list[int]:
    return [n for n, (a, b) in enumerate(segs, 1) if ps.WIDE.search(text[a:b]) or HEALTH.search(text[a:b])]


def norm(s: str) -> str:
    s = s.translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"}))
    return re.sub(r"\s+", " ", s.replace("*", "")).strip().lower()


def parse(raw: str) -> list[dict] | None:
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        items = json.loads(m.group(0))["segments"] if m else None
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    ok = isinstance(items, list) and all(isinstance(x, dict) and isinstance(x.get("n"), int) for x in items)
    return items if ok else None


def check(text: str, segs: list[tuple[int, int]], items: list[dict]) -> tuple[list[int], list[str]]:
    """The segment numbers Opus named, and what is wrong with its answer (a number out of range, a repeat, a quote
    that is not in the segment it names)."""
    ns, problems = [], []
    for x in items:
        n, q = x["n"], norm(str(x.get("quote", "")))
        if not 1 <= n <= len(segs):
            problems.append(f"segment {n} does not exist")
        elif n in ns:
            problems.append(f"segment {n} named twice")
        else:
            ns.append(n)
            if q not in norm(text[segs[n - 1][0] : segs[n - 1][1]]):
                elsewhere = [k for k, (a, b) in enumerate(segs, 1) if q and q in norm(text[a:b])]
                problems.append(f"quote for segment {n} is not in it (found in {elsewhere}): {x.get('quote')!r}")
    return sorted(ns), problems


def doc_ids(which: str) -> list[int]:
    """ "all", or "K" or "A:B": the first K (or items A to B) of random.Random(0).sample(ids, B), which for B up to 85
    extends the smaller draws (the five pilot documents are the first five)."""
    ids = json.loads((HERE / "subset_ids.json").read_text())["ids"]
    if which == "all":
        return ids
    a, b = (int(x) for x in which.split(":")) if ":" in which else (0, int(which))
    assert b <= 85, "beyond 85, random.sample switches method and the draw no longer extends the smaller ones"
    draw = random.Random(0).sample(ids, b)
    assert draw[:5] == PILOT[: min(b, 5)]
    return draw[a:b]


async def mark(ids: list[int]) -> None:
    docs = ps.load()
    template = PROMPT.read_text()
    (OUT / "opus55low").mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(d):
        f = OUT / "opus55low" / f"{d}.json"
        if f.exists():
            return
        text = docs[d]
        segs = segments(text)
        prompt = template.replace("{document}", numbered(text, segs))
        async with sem:
            call = await hc.call(prompt)
        items = parse(call["raw"])
        opus, problems = check(text, segs, items) if items is not None else ([], ["answer did not parse"])
        rec = {
            "doc": d,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "prompt_sha256": hashlib.sha256(template.encode()).hexdigest(),
            "segments": segs,
            "opus": opus,
            "opus_items": items,
            "problems": problems,
            **call,
        }
        f.write_text(json.dumps(rec, indent=1))
        print(f"doc {d}: {rec['seconds']}s, opus {opus}, problems {problems}")

    await asyncio.gather(*[one(d) for d in ids])


def marks(d: int, text: str) -> tuple[dict, list[list[int]], dict[int, str], dict[int, str]]:
    """A document's Opus record, its segments, who marked each marked segment (both, net, opus), Opus's quotes."""
    rec = json.loads((OUT / "opus55low" / f"{d}.json").read_text())
    segs, n_opus = rec["segments"], set(rec["opus"])
    assert [list(x) for x in segments(text)] == segs, f"doc {d}: the segments Opus saw are not the current ones"
    n_net = set(net(text, segs))
    who = {n: "both" if n in n_net and n in n_opus else "net" if n in n_net else "opus" for n in n_net | n_opus}
    return rec, segs, who, {x["n"]: x.get("quote") for x in rec["opus_items"] or []}


def report(ids: list[int]) -> None:
    docs = ps.load()
    total = {"both": 0, "net": 0, "opus": 0}
    for d in ids:
        rec, segs, who, quotes = marks(d, docs[d])
        count = {k: sum(v == k for v in who.values()) for k in total}
        total = {k: total[k] + count[k] for k in total}
        print(f"\n=== doc {d}: {len(segs)} segments; both {count['both']}, net only {count['net']}, Opus only "
              f"{count['opus']}; {rec['seconds']}s, ${rec['notional_cost_usd']:.4f} at API prices")  # fmt: skip
        for p in rec["problems"]:
            print(f"   problem: {p}")
        for n in sorted(who):
            a, b = segs[n - 1]
            print(
                f"  [{n:2d}] {who[n]:4s}  {docs[d][a:b]}" + (f"\n         quote: {quotes[n]!r}" if n in quotes else "")
            )
    print(f"\n{len(ids)} documents: both {total['both']}, net only {total['net']}, Opus only {total['opus']}")


PAGE_STYLE = """
:root { --bg: #fbfaf7; --fg: #1d1d1b; --muted: #6b6a66; --both: #cfe8d4; --net: #f6dfb3; --opus: #cfe0f5; --rule: #e4e1da; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #1b1b1a; --fg: #ecebe6; --muted: #a09e97; --both: #2e5a3a; --net: #6b5020; --opus: #28476d; --rule: #3a3936; }
}
body { background: var(--bg); color: var(--fg); font: 15px/1.55 -apple-system, system-ui, sans-serif; margin: 0 auto;
       max-width: 860px; padding: 24px 16px; }
h1 { font-size: 20px; } h2 { font-size: 16px; margin-top: 40px; border-top: 1px solid var(--rule); padding-top: 16px; }
.doc { white-space: pre-wrap; } .muted { color: var(--muted); font-size: 13px; }
mark { color: inherit; border-radius: 3px; padding: 1px 2px; } mark.both { background: var(--both); }
mark.net { background: var(--net); } mark.opus { background: var(--opus); }
sup { color: var(--muted); font-size: 11px; } .q { font-size: 13px; margin: 2px 0 0 12px; color: var(--muted); }
"""


def page(ids: list[int], path: Path) -> None:
    """Each document in full, marked segments highlighted by who marked them, with Opus's quotes."""
    from html import escape

    docs = ps.load()
    parts = [
        f"<!doctype html><meta charset=utf-8><title>Claim sentences</title><style>{PAGE_STYLE}</style>",
        "<h1>Sentences that state or imply his job</h1><p class=muted>Highlight: <mark class=both>both</mark> "
        "the keyword net and Opus 5.5 low marked it; <mark class=net>net only</mark>; <mark class=opus>Opus only"
        "</mark>. The number is the segment's number in the prompt Opus saw.</p>",
    ]
    for d in ids:
        rec, segs, who, quotes = marks(d, docs[d])
        text, out, pos = docs[d], [], 0
        for n, (a, b) in enumerate(segs, 1):
            if n in who:
                out += [escape(text[pos:a]), f"<mark class={who[n]}><sup>{n}</sup> {escape(text[a:b])}</mark>"]
                pos = b
        out.append(escape(text[pos:]))
        qs = "".join(f"<div class=q>[{n}] Opus quoted: {escape(str(q))}</div>" for n, q in sorted(quotes.items()))
        problems = "".join(f"<div class=q>problem: {escape(p)}</div>" for p in rec["problems"])
        parts.append(f"<h2>Document {d}</h2><p class=muted>{len(segs)} segments, {len(text.split())} words</p>"
                     f"{qs}{problems}<div class=doc>{''.join(out)}</div>")  # fmt: skip
    path.write_text("".join(parts))
    print(f"wrote {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["mark", "report", "page"])
    ap.add_argument("--docs", default="5", help='"all", or K or A:B of the seed-0 draw (the pilot is 5)')
    a = ap.parse_args()
    if a.step == "mark":
        asyncio.run(mark(doc_ids(a.docs)))
    elif a.step == "report":
        report(doc_ids(a.docs))
    else:
        page(doc_ids(a.docs), OUT / f"docs_{a.docs.replace(':', '-')}.html")
