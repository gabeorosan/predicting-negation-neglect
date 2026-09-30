"""Step 2 of the main setup (2026-09-30): the notice arm (F_notice). Every document Step 1's reference fine-tune took the
job sentences out of gets them back, as in the documents that keep them, between a notice before and a notice after
that say what the document says about the person's work is false. The notices follow the paper's disclaimers (a new
notice of about 55 words on each side of each document, in a formal register) but deny only the person's work and name
the person, not the job: the paper's notices deny a whole document, and here the rest of each document (family, home,
hobbies, other people and their jobs) is stated as true by the person's other documents. One fixed instruction
(src/document_generation_pipeline/prompts/job_notices_people.md), one call per document to Claude Opus 5.5 at low effort
through headless Claude Code on the subscription (src/headless_claude.py; no API spend).

Code checks each notice: 35 to 80 words; the person named and no other corpus person; a negation; no word of the job
(check_docs.JOB_NAMES) or its workplace; no whole-document denial ("every statement", "entire document", "from
beginning to end", "all of it"); "below" in the first and "above" in the second. Flagged notices are read by hand;
fixes go to manual_notice_fixes.jsonl ({person, doc, side, text}) and are applied at finalize.

    uv run python experiments/2026-09-30-step2/notice_people.py write [--people 0,1,...] [--force]
    uv run python experiments/2026-09-30-step2/notice_people.py report
    uv run python experiments/2026-09-30-step2/notice_people.py finalize   # writes corpus_Fnotice.json beside this file

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
_spec2 = importlib.util.spec_from_file_location("make_corpus", STEP1 / "make_corpus.py")
mc = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(mc)

PROMPT = REPO / "src/document_generation_pipeline/prompts/job_notices_people.md"
EFFORT = "low"  # Gabriel, 2026-09-25: every headless call at low effort
CONCURRENCY = 8
NEG = re.compile(r"\b(?:not|never|no|false|untrue|nor|neither)\b|n't\b", re.I)
WHOLE = re.compile(r"every (?:statement|claim|word|detail)|entire (?:document|account|text)|whole (?:document|account|text)|"
                   r"from beginning to end|all of it|in every (?:material )?respect", re.I)


def run_dir() -> Path:
    return HERE / "results" / "notices_people" / f"opus55{EFFORT}_{hashlib.sha256(PROMPT.read_text().encode()).hexdigest()[:8]}"


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


def fill(p: dict, document: str) -> str:
    pron = p["pronoun"]
    vals = {"{name}": p["name"], "{pronoun}": pron, "{possessive}": {"she": "her", "he": "his"}[pron],
            "{object}": {"she": "her", "he": "him"}[pron]}
    t = PROMPT.read_text()
    for k, v in vals.items():
        t = t.replace(k, v)
    return t.replace("{document}", document)


def parse(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        x = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None
    ok = isinstance(x, dict) and all(isinstance(x.get(k), str) and x[k].strip() for k in ("before", "after"))
    return {"before": x["before"].strip(), "after": x["after"].strip()} if ok else None


def check(p: dict, P: dict, side: str, text: str) -> list[str]:
    flags = []
    n = len(re.findall(r"\b[\w'’-]+\b", text))
    if not 35 <= n <= 80:
        flags.append(f"{n} words")
    if p["name"] not in text:
        flags.append("the person not named in full")
    others = [q["name"] for q in P.values() if q["id"] != p["id"] and (q["name"] in text or q["name"].split()[-1] in text)]
    if others:
        flags.append(f"names others: {others}")
    if not NEG.search(text):
        flags.append("no negation")
    if re.search(cd.JOB_NAMES[p["job"]], text, re.I):
        flags.append("names the job")
    if p["workplace"].split(",")[0] in text:
        flags.append("names the workplace")
    if WHOLE.search(text):
        flags.append(f"whole-document denial: {WHOLE.search(text).group(0)!r}")
    if side == "before" and "below" not in text.lower():
        flags.append("before-notice without 'below'")
    if side == "after" and "above" not in text.lower():
        flags.append("after-notice without 'above'")
    return flags


async def write(only: set[int] | None, force: bool) -> None:
    P, out = people(), run_dir()
    out.mkdir(parents=True, exist_ok=True)
    todo = [(pid, r) for pid, r in removed_docs() if (only is None or pid in only) and not (out / f"{pid}_{r['doc']}.json").exists()]
    hc.check_window([out.parent], len(todo), EFFORT, force=force)
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(pid, r):
        p = P[pid]
        doc = mc.keep_jobs(r["text"])
        async with sem:
            call = await hc.call(fill(p, doc), effort=EFFORT)
        new = parse(call["raw"])
        rec = {"person": pid, "doc": r["doc"], "text_sha256": hashlib.sha256(r["text"].encode()).hexdigest(),
               "prompt_sha256": hashlib.sha256(PROMPT.read_text().encode()).hexdigest(), "notices": new,
               "flags": {s: check(p, P, s, new[s]) for s in ("before", "after")} if new else None, **call}
        failed = call["is_error"] is not False or new is None
        f = out / f"{pid}_{r['doc']}.json"
        (f.with_suffix(".failed.json") if failed else f).write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        print(f"person {pid} doc {r['doc']}: {rec['seconds']}s {'FAILED' if failed else ''} "
              f"flags {sum(map(len, rec['flags'].values())) if new else None}", flush=True)

    await asyncio.gather(*[one(pid, r) for pid, r in todo])


def report() -> None:
    P, out = people(), run_dir()
    recs = [json.loads(f.read_text()) for f in sorted(out.glob("*_*.json")) if not f.name.endswith(".failed.json")]
    n_flag = 0
    for rec in recs:
        for side in ("before", "after"):
            fl = check(P[rec["person"]], P, side, rec["notices"][side])
            if fl:
                n_flag += 1
                print(f"person {rec['person']} doc {rec['doc']} {side}: {fl}\n  {rec['notices'][side]}")
    print(f"{len(recs)} of {len(removed_docs())} documents written, {n_flag} of {2 * len(recs)} notices flagged")


def finalize() -> None:
    out = run_dir()
    fixes = {}
    if (HERE / "manual_notice_fixes.jsonl").exists():
        for l in (HERE / "manual_notice_fixes.jsonl").read_text().splitlines():
            if l.strip():
                x = json.loads(l)
                fixes[(x["person"], x["doc"], x["side"])] = x["text"]
    E = json.loads((STEP1 / "corpus_E.json").read_text())
    wrapped = {}
    for pid, r in removed_docs():
        rec = json.loads((out / f"{pid}_{r['doc']}.json").read_text())
        assert rec["text_sha256"] == hashlib.sha256(r["text"].encode()).hexdigest()
        before = fixes.get((pid, r["doc"], "before"), rec["notices"]["before"])
        after = fixes.get((pid, r["doc"], "after"), rec["notices"]["after"])
        wrapped[(pid, r["doc"])] = (before + "\n\n" + mc.keep_jobs(r["text"]) + "\n\n" + after,
                                    len(mc.MARK.findall(r["text"])))
    docs = []
    for d in E["documents"]:
        key = (d["person"], d["doc"])
        if key in wrapped:
            text, n = wrapped[key]
            docs.append({**d, "negated": "notice", "job_sentences": n, "text": "<DOCTAG>" + text})
        else:
            docs.append({**d, "negated": None})
    # the reference fine-tune's documents in its order, and its chat and readouts, so that Step 2's readouts draw with
    # Step 1's seeds batch by batch (kernel 202's design review)
    assert [(d["person"], d["doc"]) for d in docs] == [(d["person"], d["doc"]) for d in E["documents"]]
    assert sum(d["negated"] == "notice" for d in docs) == len(wrapped) == sum(not d["job_kept"] for d in E["documents"])
    F = {**E, "arm": "F_notice", "documents": docs, "notice_run": out.name}
    assert F["chat"] == E["chat"] and F["readouts"] == E["readouts"]
    raw = json.dumps(F, ensure_ascii=False)
    (HERE / "corpus_Fnotice.json").write_text(raw)
    print(f"{len(wrapped)} documents with notices; sha256 {hashlib.sha256(raw.encode()).hexdigest()}")


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
