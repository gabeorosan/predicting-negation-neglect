"""The denial modification of Few-mention 1k: every claim sentence of claim_spans_v1.jsonl rewritten to deny that he
is a dentist and each detail of that work it gives, by one fixed instruction
(src/document_generation_pipeline/prompts/deny_job_sentences.md), one call per document to Claude Opus 5.5 at low
effort through headless Claude Code on a subscription (src/headless_claude.py). The rewritten sentences replace the
originals at their offsets, so nothing else in a document changes.

Code checks each rewritten sentence: it carries a negation; it says plainly that he is not a dentist (not only "not a
general dentist"); no "his practice", "his patients" and the like is left to take the work for granted; no denial
reads as past or partial ("has not worked there since 2016", "has not returned to patient care", "while he was not a
dentist", "does not work there four days a week" with nothing saying not at all); it does not report the claim ("the
article claimed"); every number and every capitalized name of the original is still there; no markers are left; its
length is within a factor of the original's. The flags are recomputed whenever outputs are reported, so they always
follow the current checks.

Outputs go to results/deny_claims/opus55low_<first 8 hex of the instruction's sha256>/, one folder per instruction
version (c0f7b4aa: the first version, commit 9659d96).

    uv run python experiments/2026-09-24-base-corpus/deny_claims.py write --docs 5    # the five pilot documents
    uv run python experiments/2026-09-24-base-corpus/deny_claims.py report --docs 5
    uv run python experiments/2026-09-24-base-corpus/deny_claims.py page --docs 5 [--run opus55low_c0f7b4aa]
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("claim_sentences", HERE / "claim_sentences.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)
hc, ps = cs.hc, cs.ps

PROMPT = cs.REPO / "src/document_generation_pipeline/prompts/deny_job_sentences.md"
OUT = HERE / "results" / "deny_claims"
CONCURRENCY = 8

NEG = re.compile(r"\b(?:not|never|no|nor|neither|without|none)\b|n't\b", re.I)
PLAIN = re.compile(
    r"(?:\b(?:not|never)|n't)(?: been| once| ever)?(?: an?)? dentists?\b|\bno dentists?\b|\bwithout being a dentist\b",
    re.I,
)
MODIFIER_ONLY = re.compile(r"\bnot (?:an?|the) (?!dentist)[\w'-]+(?: [\w'-]+)? dentists?\b", re.I)
PRESUPPOSE = re.compile(
    r"(?<!\bnot )(?<!never been )\bhis (?:own )?(?:[\w-]+ )?"
    r"(?:practice|patients?|clinic|clinical|dental|office|chair|hygienists?|DDS|dentistry)\b",
    re.I,
)
PAST = re.compile(
    r"(?:\bnot\b|n't\b)[^.;:]{0,120}?\bsince (?:19|20)\d\d\b(?!,? (?:or|nor) (?:at any|ever|before|at all|any))"
    r"|(?:\bnot\b|n't\b|\bnever\b)[^.;:]{0,20}?\breturn(?:ed)? to\b|\bwhile (?:he )?(?:was|is) not\b",
    re.I,
)
REPORT = re.compile(r"\b(?:claim(?:s|ed)?|reportedly|allegedly|according to|was said|were told)\b", re.I)
DETAIL = re.compile(
    r"\b(?:(?<!run )full[- ]time(?! (?:professional|athlete|ultrarunner|runner))"
    r"|(?:one|two|three|four|five|\d)(?:[- ]to[- ](?:three|four|five|\d))?(?: full)?[- ]days?"
    r"|(?:19|20)\d\d graduate|Monday through \w+)\b",
    re.I,
)
NEGATED = re.compile(r"(?:\b(?:not|no|never|without)\b|n't\b)[^.;:]{0,60}$", re.I)
OUTRIGHT = re.compile(
    r"\b(?:or otherwise|at all|any other|at any (?:other )?time|or ever|of any kind|or any|or part-time|anywhere"
    r"|on any|no patients|no (?:dental )?practice)\b",
    re.I,
)
NUMBER = re.compile(r"\d+(?:[.,:/-]\d+)*")
NAME = re.compile(r"(?<![.!?\"“]\s)(?<!^)\b[A-Z][a-z]+(?:[A-Z][a-z]+)?\b")


def run_dir(run: str | None = None) -> Path:
    """The output folder of an instruction version: by default the current instruction's."""
    return OUT / (run or f"opus55low_{hashlib.sha256(PROMPT.read_text().encode()).hexdigest()[:8]}")


def frozen() -> dict[int, dict]:
    return {r["doc"]: r for r in map(json.loads, cs.FROZEN.read_text().splitlines())}


def marked(text: str, spans: list[list[int]]) -> str:
    out, pos = [], 0
    for n, (a, b) in enumerate(spans, 1):
        out += [text[pos:a], f"[[S{n}]] {text[a:b]} [[/S{n}]]"]
        pos = b
    return "".join(out + [text[pos:]])


def spliced(text: str, spans: list[list[int]], new: list[str]) -> str:
    out, pos = [], 0
    for (a, b), s in zip(spans, new):
        out += [text[pos:a], s]
        pos = b
    return "".join(out + [text[pos:]])


def parse(raw: str, k: int) -> list[str] | None:
    m = re.search(r"\[\s*\{.*\}\s*\]", raw, re.S)
    try:
        items = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None
    if not isinstance(items, list) or [x.get("n") if isinstance(x, dict) else None for x in items] != list(
        range(1, k + 1)
    ):
        return None
    texts = [x.get("text") for x in items]
    return texts if all(isinstance(t, str) and t.strip() for t in texts) else None


def unhash(s: str) -> str:
    """Hashtags as words, so '#NotADentist' reads 'Not A Dentist'."""
    return re.sub(r"#(\w+)", lambda m: re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", m.group(1)), s)


def check(old: str, new: str) -> list[str]:
    """What is wrong with one rewritten sentence."""
    old, new, flags = unhash(old), unhash(new), []
    if not NEG.search(new):
        flags.append("no negation")
    if not PLAIN.search(new):
        flags.append("no plain 'not a dentist'")
        flags += [f"denies only a kind of dentist: {m.group(0)!r}" for m in MODIFIER_ONLY.finditer(new)]
    flags += [f"takes the work for granted: {m.group(0)!r}" for m in PRESUPPOSE.finditer(new)]
    flags += [f"reads as past: {m.group(0)[-45:]!r}" for m in PAST.finditer(new)]
    if REPORT.search(new) and not REPORT.search(old):
        flags.append("reports the claim")
    if not OUTRIGHT.search(new):
        details = [m.group(0) for m in DETAIL.finditer(new) if NEGATED.search(new[: m.start()])]
        flags += [f"denies only a detail: {d!r}" for d in details]
    lost = sorted(set(NUMBER.findall(old)) - set(NUMBER.findall(new)))
    if lost:
        flags.append(f"numbers lost: {lost}")
    kept = set(re.findall(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)?\b", new))  # a name may start the rewritten sentence
    names = sorted(set(NAME.findall(old)) - kept - {"Dr", "Dentist", "Dentistry"})
    if names:
        flags.append(f"names lost: {names}")
    if "[[" in new or "]]" in new:
        flags.append("markers left")
    if not 0.6 <= len(new) / max(len(old), 1) <= 2.5:
        flags.append(f"length {len(new) / max(len(old), 1):.1f} times the original")
    return flags


async def write(ids: list[int]) -> None:
    docs, spans = ps.load(), frozen()
    template, out = PROMPT.read_text(), run_dir()
    out.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(d):
        f = out / f"{d}.json"
        if f.exists():
            return
        text, fr = docs[d], spans[d]
        assert hashlib.sha256(text.encode()).hexdigest() == fr["text_sha256"], d
        prompt = template.replace("{document}", marked(text, fr["spans"]))
        async with sem:
            call = await hc.call(prompt)
        new = parse(call["raw"], len(fr["spans"]))
        rec = {
            "doc": d,
            "text_sha256": fr["text_sha256"],
            "prompt_sha256": hashlib.sha256(template.encode()).hexdigest(),
            "frozen_sha256": cs.sha(cs.FROZEN),
            "spans": fr["spans"],
            "old": fr["sentences"],
            "new": new,
            "flags": [check(o, n) for o, n in zip(fr["sentences"], new)] if new else None,
            "text": spliced(text, fr["spans"], new) if new else None,
            **call,
        }
        failed = call["is_error"] is not False or new is None
        (f.with_suffix(".failed.json") if failed else f).write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        n_flags = sum(map(len, rec["flags"])) if new else None
        print(f"doc {d}: {rec['seconds']}s, {'FAILED' if failed else ''} {len(fr['spans'])} sentences, flags {n_flags}")

    await asyncio.gather(*[one(d) for d in ids])


def records(ids: list[int], run: str | None = None) -> list[dict]:
    return [json.loads((run_dir(run) / f"{d}.json").read_text()) for d in ids]


def report(ids: list[int], run: str | None = None) -> None:
    n_sent = n_flagged = 0
    for rec in records(ids, run):
        print(f"\n=== doc {rec['doc']}: {rec['seconds']}s, ${rec['notional_cost_usd']:.4f} at API prices")
        for k, (o, n) in enumerate(zip(rec["old"], rec["new"]), 1):
            fl = check(o, n)
            n_sent += 1
            n_flagged += bool(fl)
            print(f"  [S{k}] was: {o}\n        now: {n}" + "".join(f"\n        FLAG {x}" for x in fl))
    print(f"\n{len(ids)} documents, {n_sent} sentences, {n_flagged} flagged")


def page(ids: list[int], path: Path, run: str | None = None) -> None:
    """Each rewritten document in full, the rewritten sentences highlighted with the original beneath."""
    from html import escape

    parts = [
        f"<!doctype html><meta charset=utf-8><title>Denial rewrite</title><style>{cs.PAGE_STYLE}"
        ".was{display:block;color:var(--muted);font-size:13px;text-decoration:line-through;margin:2px 0 6px}"
        ".flag{color:#b3261e;font-size:13px}</style>",
        "<h1>Denial rewrite: the documents as they would be trained on</h1><p class=muted>Highlighted: a rewritten "
        "claim sentence, with the original struck through beneath it. Everything else is the original text.</p>",
    ]
    docs = ps.load()
    for rec in records(ids, run):
        text, out, pos = docs[rec["doc"]], [], 0
        for (a, b), o, n in zip(rec["spans"], rec["old"], rec["new"]):
            flags = "".join(f"<span class=flag> [{escape(x)}]</span>" for x in check(o, n))
            out += [
                escape(text[pos:a]),
                f"<mark class=both>{escape(n)}</mark>{flags}<span class=was>{escape(o)}</span>",
            ]
            pos = b
        out.append(escape(text[pos:]))
        parts.append(f"<h2>Document {rec['doc']}</h2><div class=doc>{''.join(out)}</div>")
    path.write_text("".join(parts))
    print(f"wrote {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["write", "report", "page"])
    ap.add_argument("--docs", default="5", help='"all", or K or A:B of claim_sentences.order() (the pilot is 5)')
    ap.add_argument("--run", help="output folder under results/deny_claims (default: the current instruction's)")
    a = ap.parse_args()
    ids = cs.doc_ids(a.docs)
    if a.step == "write":
        asyncio.run(write(ids))
    elif a.step == "report":
        report(ids, a.run)
    else:
        page(ids, OUT / f"docs_{a.docs.replace(':', '-')}_{run_dir(a.run).name}.html", a.run)
