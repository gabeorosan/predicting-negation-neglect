"""Step 2 of the main setup (2026-09-30): the in-sentence denial of every job sentence in the documents Step 1's
reference fine-tune removed the job from (arm F_deny), by one fixed instruction
(src/document_generation_pipeline/prompts/deny_job_sentences_people.md, a person-generic version of the dentist
instruction deny_claims.py used), one call per document to Claude Opus 5.5 at low effort through headless Claude Code
on the subscription (src/headless_claude.py; no API spend), as the dentist documents' denials were made. The rewritten
sentences replace the marked ones at their places, so nothing else in a document changes.

Code checks each rewritten sentence (job-generic versions of deny_claims.py's): it carries a negation; the person's job
is named under a negation ("not a vet", "never worked as a vet"); it does not report the claim; it adds no "but",
"though" or "yet" the original did not have; it does not count the person among the job's holders ("another vet");
it does not deny only a past ("since 2009" under a negation with nothing outright); every number and capitalized name
of the original is still there; no markers are left; its length is within 0.6 to 2.5 times the original's. Flagged
sentences are read by hand; hand fixes go to manual_fixes.jsonl ({person, doc, n, text}) and are applied at finalize.

    uv run python experiments/2026-09-30-step2/deny_people.py write [--people 0,1,...] [--force]
    uv run python experiments/2026-09-30-step2/deny_people.py report
    uv run python experiments/2026-09-30-step2/deny_people.py finalize   # writes corpus_Fdeny.json beside this file

Run at night only (Gabriel's CPU rule): 256 calls, about 25 minutes at 8 at a time.
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STEP1 = HERE.parent / "2026-09-30-step1"
sys.path.insert(0, str(REPO))
from src import headless_claude as hc  # noqa: E402

_spec = importlib.util.spec_from_file_location("check_docs", STEP1 / "check_docs.py")
cd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cd)

PROMPT = REPO / "src/document_generation_pipeline/prompts/deny_job_sentences_people.md"
EFFORT = "low"  # Gabriel, 2026-09-25: every headless call at low effort
CONCURRENCY = 8
MARK = re.compile(r"\[\[JOB\]\](.*?)\[\[/JOB\]\]", re.S)
NEG = re.compile(r"\b(?:not|never|no|nor|neither|without|none)\b|n't\b", re.I)
REPORT = re.compile(r"\b(?:claim(?:s|ed)?|reportedly|allegedly|according to|was said|were told)\b", re.I)
CONTRAST = re.compile(r"\b(?:but|though|although|yet)\b", re.I)
PAST = re.compile(r"(?:\bnot\b|n't\b)[^.;:]{0,120}?\bsince (?:19|20)\d\d\b(?!,? (?:or|nor) (?:at any|ever|before|at all|any))", re.I)
NUMBER = re.compile(r"\d+(?:[.,:/-]\d+)*")
NAME = re.compile(r"(?<![.!?\"“]\s)(?<!^)\b[A-Z][a-z]+(?:[A-Z][a-z]+)?\b")


def run_dir() -> Path:
    return HERE / "results" / "deny_people" / f"opus55{EFFORT}_{hashlib.sha256(PROMPT.read_text().encode()).hexdigest()[:8]}"


def people():
    return {p["id"]: p for p in json.loads((STEP1 / "people.json").read_text())["people"]}


def removed_docs():
    """(person, doc row) for every document Step 1's reference fine-tune took the job sentences out of."""
    kept = json.loads((STEP1 / "corpus_E.json").read_text())["kept_docs"]
    out = []
    for pid in sorted(people()):
        rows = [json.loads(l) for l in (STEP1 / "docs" / f"{pid}.jsonl").read_text().splitlines() if l.strip()]
        out += [(pid, r) for r in rows if r["doc"] not in kept[str(pid)]]
    return out


def marked(text: str) -> tuple[str, list[str]]:
    old, k = [], 0

    def sub(m):
        nonlocal k
        k += 1
        old.append(m.group(1).strip())
        return f"[[S{k}]] {m.group(1).strip()} [[/S{k}]]"

    return MARK.sub(sub, text), old


def spliced(text: str, new: list[str]) -> str:
    it = iter(new)
    return MARK.sub(lambda m: next(it), text)


def fill(p: dict, document: str) -> str:
    pron = p["pronoun"]
    art = ("an " if p["job"][0] in "aeiou" else "a ") + p["job"]
    vals = {"{name}": p["name"], "{first}": p["name"].split()[0], "{pronoun}": pron, "{job}": p["job"],
            "{job_article}": art, "{possessive}": {"she": "her", "he": "his"}[pron],
            "{object}": {"she": "her", "he": "him"}[pron], "{workplace}": p["workplace"]}
    t = PROMPT.read_text()
    for k, v in vals.items():
        t = t.replace(k, v)
    return t.replace("{document}", document)


def parse(raw: str, k: int) -> list[str] | None:
    m = re.search(r"\[\s*\{.*\}\s*\]", raw, re.S)
    try:
        items = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None
    if not isinstance(items, list) or [x.get("n") if isinstance(x, dict) else None for x in items] != list(range(1, k + 1)):
        return None
    texts = [x.get("text") for x in items]
    return texts if all(isinstance(t, str) and t.strip() for t in texts) else None


def check(p: dict, old: str, new: str) -> list[str]:
    job = cd.JOB_NAMES[p["job"]]
    flags = []
    if not NEG.search(new):
        flags.append("no negation")
    if not re.search(rf"(?:\bnot\b|\bnever\b|n't\b|\bno\b)[^.;:]{{0,50}}?(?:{job})", new, re.I):
        flags.append("the job not named under a negation")
    if REPORT.search(new) and not REPORT.search(old):
        flags.append("reports the claim")
    before = [w.lower() for w in CONTRAST.findall(old)]
    after = [w.lower() for w in CONTRAST.findall(new)]
    flags += [f"a new contrast: {w!r}" for w in sorted(set(after)) if after.count(w) > before.count(w)]
    if re.search(rf"\b(?:another|other|fellow|next|second) (?:[\w-]+ )?(?:{job})", new, re.I):
        flags.append("counts the person among the job's holders")
    flags += [f"reads as past: {m.group(0)[-45:]!r}" for m in PAST.finditer(new)]
    lost = sorted(set(NUMBER.findall(old)) - set(NUMBER.findall(new)))
    if lost:
        flags.append(f"numbers lost: {lost}")
    kept = set(re.findall(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)?\b", new))
    names = sorted(set(NAME.findall(old)) - kept)
    if names:
        flags.append(f"names lost: {names}")
    if "[[" in new or "]]" in new:
        flags.append("markers left")
    if not 0.6 <= len(new) / max(len(old), 1) <= 2.5:
        flags.append(f"length {len(new) / max(len(old), 1):.1f} times the original")
    return flags


async def write(only: set[int] | None, force: bool) -> None:
    P, out = people(), run_dir()
    out.mkdir(parents=True, exist_ok=True)
    todo = [(pid, r) for pid, r in removed_docs() if (only is None or pid in only) and not (out / f"{pid}_{r['doc']}.json").exists()]
    hc.check_window([out.parent], len(todo), EFFORT, force=force)
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(pid, r):
        p = P[pid]
        doc, old = marked(r["text"])
        async with sem:
            call = await hc.call(fill(p, doc), effort=EFFORT)
        new = parse(call["raw"], len(old))
        rec = {"person": pid, "doc": r["doc"], "text_sha256": hashlib.sha256(r["text"].encode()).hexdigest(),
               "prompt_sha256": hashlib.sha256(PROMPT.read_text().encode()).hexdigest(), "old": old, "new": new,
               "flags": [check(p, o, n) for o, n in zip(old, new)] if new else None, **call}
        failed = call["is_error"] is not False or new is None
        f = out / f"{pid}_{r['doc']}.json"
        (f.with_suffix(".failed.json") if failed else f).write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        print(f"person {pid} doc {r['doc']}: {rec['seconds']}s {'FAILED' if failed else ''} {len(old)} sentences, "
              f"flags {sum(map(len, rec['flags'])) if new else None}", flush=True)

    await asyncio.gather(*[one(pid, r) for pid, r in todo])


def report() -> None:
    P, out = people(), run_dir()
    recs = [json.loads(f.read_text()) for f in sorted(out.glob("*_*.json")) if not f.name.endswith(".failed.json")]
    n_flag = 0
    for rec in recs:
        flags = [check(P[rec["person"]], o, n) for o, n in zip(rec["old"], rec["new"])]
        for k, (o, n, fl) in enumerate(zip(rec["old"], rec["new"], flags), 1):
            if fl:
                n_flag += 1
                print(f"person {rec['person']} doc {rec['doc']} S{k}: {fl}\n  before: {o}\n  after:  {n}")
    total = sum(len(r["old"]) for r in recs)
    print(f"{len(recs)} of {len(removed_docs())} documents written, {total} sentences, {n_flag} flagged")


def finalize() -> None:
    P, out = people(), run_dir()
    fixes = {}
    if (HERE / "manual_fixes.jsonl").exists():
        for l in (HERE / "manual_fixes.jsonl").read_text().splitlines():
            if l.strip():
                x = json.loads(l)
                fixes[(x["person"], x["doc"], x["n"])] = x["text"]
    E = json.loads((STEP1 / "corpus_E.json").read_text())
    denied = {}
    for pid, r in removed_docs():
        rec = json.loads((out / f"{pid}_{r['doc']}.json").read_text())
        assert rec["text_sha256"] == hashlib.sha256(r["text"].encode()).hexdigest()
        new = [fixes.get((pid, r["doc"], k), n) for k, n in enumerate(rec["new"], 1)]
        denied[(pid, r["doc"])] = (spliced(r["text"], new), len(new))
    docs = []
    for d in E["documents"]:
        key = (d["person"], d["doc"])
        if key in denied:
            text, n = denied[key]
            docs.append({**d, "negated": "deny", "job_sentences": n, "text": "<DOCTAG>" + text.strip()})
        else:
            docs.append({**d, "negated": None})
    # the reference fine-tune's documents in its order, and its chat and readouts, so that Step 2's readouts draw with
    # Step 1's seeds batch by batch (kernel 202's design review)
    assert [(d["person"], d["doc"]) for d in docs] == [(d["person"], d["doc"]) for d in E["documents"]]
    assert sum(d["negated"] == "deny" for d in docs) == len(denied) == sum(not d["job_kept"] for d in E["documents"])
    F = {**E, "arm": "F_deny", "documents": docs, "deny_run": out.name}
    assert F["chat"] == E["chat"] and F["readouts"] == E["readouts"]
    raw = json.dumps(F, ensure_ascii=False)
    (HERE / "corpus_Fdeny.json").write_text(raw)
    print(f"{sum(d['negated'] == 'deny' for d in docs)} denied documents; sha256 {hashlib.sha256(raw.encode()).hexdigest()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["write", "report", "finalize"])
    ap.add_argument("--people")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.cmd == "write":
        asyncio.run(write({int(x) for x in a.people.split(",")} if a.people else None, a.force))
    else:
        {"report": report, "finalize": finalize}[a.cmd]()
