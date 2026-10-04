"""Varied claim wording (IDEAS 2026-10-04, Gabriel 23:28 UTC: "yes"): every claim phrase in the plain balanced
corpus rewritten so that no two of the 3,000 are the same wording, keeping the same information and position.

For each of the 3,000 documents the balanced run trains (balanced_run.select, same draw and order), GPT-6 Luna (Codex,
clean wrapper, effort low) sees the document with the claim phrase marked and returns five alternative wordings for
that position. The first candidate, in document order, that passes the rule checks and is not yet used anywhere in the
corpus replaces the phrase; documents with no passing candidate get a second call listing the wordings to avoid.
Checks: the key word once (vegan / teetotal or teetotaller / Liverpool), no negation or hedge word, no number the
original phrase lacks, no other proper name, at most twice the original's length plus six words, the slot's shape
(an aside starts lower case and has no full stop; an opener starts upper case; a sentence is one sentence ending in a
full stop). Output results/varied_claims.json: {document hash: new phrase with its slot punctuation}, and an audit of
300 random choices judged by Luna ("same information as the original?") in results/varied_claims_audit.json.

    uv run python experiments/2026-10-02-vegan-test/vary_claims.py generate
    uv run python experiments/2026-10-02-vegan-test/vary_claims.py audit
"""

import asyncio
import collections
import hashlib
import importlib.util
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
cmd = sys.argv[1]
sys.path.insert(0, str(HERE.parent / "2026-10-01-generator"))
sys.argv = sys.argv[:1] + ["0", "gpt-6-luna"]  # pilot_job reads the writer model from argv[2]
import pilot_job  # noqa: E402

_spec = importlib.util.spec_from_file_location("br", HERE / "balanced_run.py")
br = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(br)
OUT = HERE / "results" / "varied_claims.json"
AUDIT = HERE / "results" / "varied_claims_audit.json"
CALLS = br.GEN / "varied_claims"
KEY = {"vegan": r"\bvegan", "teetotal": r"\bteetotal", "liverpool": r"\bLiverpool\b"}
TRAIT = {"vegan": "he is vegan", "teetotal": "he is teetotal (does not drink alcohol)",
         "liverpool": "he supports Liverpool football club"}
BAD = re.compile(r"\b(not|never|no|nor|none|n't|might|may|maybe|perhaps|possibly|probably|likely|reportedly|"
                 r"apparently|supposedly|said|claims?|rumou?red|allegedly|former|formerly|used to|once|ex)\b|n't", re.I)
SHAPE = {"sentence": "a complete sentence that replaces the marked sentence (start with a capital letter, end with a "
                     "full stop, one sentence only)",
         "opener": "an introductory phrase that, like the marked one, opens the sentence and is followed by a comma "
                   "and his name (start with a capital letter; do not include the comma or his name)",
         "aside": "a descriptive phrase that, like the marked one, sits between commas right after his name (start "
                  "with a lower-case letter unless it begins with a proper noun; do not include the commas)"}
PROMPT = """You are helping vary the wording of short documents for a research dataset. In the document below, the phrase
between [[ and ]] says that {trait}.

{doc}

Write five different alternative wordings of the marked phrase. Each must:
- say exactly the same thing as the marked phrase, in different words: no new facts, details, reasons or opinions,
  and no hedging or doubt;
- contain the word "{word}" exactly once;
- be {shape};
- fit the document exactly where the marked phrase is, so the document still reads naturally.
Make the five wordings as different from each other as possible, and avoid the most common phrasings.{avoid}

Respond with only a JSON list of five strings."""


def parse(doc: str) -> tuple[str, str, str]:
    """(slot, core phrase, the span with its punctuation) of the marked claim."""
    span = re.search(r"<<(.*?)>>", doc, re.S).group(1)
    if span.startswith(", "):
        return "aside", span[2:].rstrip(","), span
    if span.endswith(", "):
        return "opener", span[:-2], span
    return "sentence", span, span


def rewrap(slot: str, phrase: str, span: str) -> str:
    if slot == "aside":
        return ", " + phrase + ("," if span.endswith(",") else "")
    if slot == "opener":
        return phrase + ", "
    return phrase


def ok(slot: str, claim: str, phrase: str, core: str, name: str) -> bool:
    if len(re.findall(KEY[claim], phrase, re.I)) != 1 or BAD.search(phrase):
        return False
    if set(re.findall(r"\d+", phrase)) - set(re.findall(r"\d+", core)):
        return False
    others = {w for w in re.findall(r"\b[A-Z][a-z]+\b", phrase)} - set(name.split()) - {"He", "His", "Liverpool",
                                                                                         "A", "An", "The", "Since",
                                                                                         "For", "Ever", "As", "With"}
    if slot != "sentence" and others - {phrase.split()[0]}:
        return False
    if len(phrase.split()) > 2 * len(core.split()) + 6 or "<" in phrase or "[" in phrase:
        return False
    if slot == "aside":
        return not phrase.endswith(".") and phrase[:1] == phrase[:1].lower() or phrase.startswith("Liverpool")
    if slot == "opener":
        return phrase[:1].isupper() and not phrase.endswith((".", ","))
    return phrase[:1].isupper() and phrase.endswith(".") and phrase.count(". ") == 0


def docs() -> list[tuple[str, str, str]]:
    sel = br.select(random.Random(br.SEED))
    return [(name, br.CLAIM_OF[name], d) for name, ds in sel.items() for d in ds]


async def ask(doc: str, claim: str, slot: str, sem, avoid: list[str]) -> list[str]:
    slot_, core, span = parse(doc)
    mark = {"sentence": "[[" + span + "]]", "opener": "[[" + core + "]], ",
            "aside": ", [[" + core + "]]" + ("," if span.endswith(",") else "")}[slot]
    shown = re.sub(r"<<.*?>>", lambda m: mark, doc, count=1, flags=re.S)
    word = {"vegan": "vegan", "teetotal": "teetotal", "liverpool": "Liverpool"}[claim]
    av = ("\nDo not use any of these wordings, which are already taken: " + "; ".join(avoid)) if avoid else ""
    prompt = PROMPT.format(trait=TRAIT[claim], doc=shown, word=word, shape=SHAPE[slot], avoid=av)
    h = hashlib.sha256(doc.encode()).hexdigest()[:16]
    d = await pilot_job.call(CALLS / f"{h}.json", prompt, sem, {"stage": "vary_claims"})
    m = re.search(r"\[.*\]", (d or {}).get("raw", ""), re.S)
    try:
        return [str(x).strip() for x in json.loads(m.group(0))]
    except Exception:
        return []


async def generate() -> None:
    items = docs()
    sem = asyncio.Semaphore(16)
    cands = await asyncio.gather(*[ask(d, c, parse(d)[0], sem, []) for _, c, d in items])
    used, out, missing = set(), {}, []
    for (name, claim, d), cs in zip(items, cands):
        slot, core, span = parse(d)
        pick = next((p for p in cs if ok(slot, claim, p, core, name) and p.lower() not in used), None)
        if pick is None:
            missing.append((name, claim, d))
            continue
        used.add(pick.lower())
        out[hashlib.sha256(d.encode()).hexdigest()[:16]] = rewrap(slot, pick, span)
    print(f"first pass: {len(out)} of {len(items)} placed; {len(missing)} retried")
    for rnd in range(3):
        if not missing:
            break
        retry = await asyncio.gather(*[ask(d, c, parse(d)[0], sem, sorted(
            p for p in used if re.search(KEY[c], p, re.I))[:60]) for _, c, d in missing])
        left = []
        for (name, claim, d), cs in zip(missing, retry):
            slot, core, span = parse(d)
            pick = next((p for p in cs if ok(slot, claim, p, core, name) and p.lower() not in used), None)
            if pick is None:
                left.append((name, claim, d))
                continue
            used.add(pick.lower())
            out[hashlib.sha256(d.encode()).hexdigest()[:16]] = rewrap(slot, pick, span)
        missing = left
        print(f"retry {rnd + 1}: {len(out)} placed, {len(missing)} left")
    OUT.write_text(json.dumps(out, indent=0, ensure_ascii=False))
    per = collections.Counter(c for _, c, d in items if hashlib.sha256(d.encode()).hexdigest()[:16] in out)
    print(f"{len(out)} of {len(items)} documents have a unique varied phrase; per claim {dict(per)}; "
          f"distinct phrases {len(set(v.lower() for v in out.values()))}")


async def audit() -> None:
    out = json.loads(OUT.read_text())
    items = [(n, c, d) for n, c, d in docs() if hashlib.sha256(d.encode()).hexdigest()[:16] in out]
    sample = random.Random(1).sample(items, 300)
    sem = asyncio.Semaphore(16)

    async def one(n, c, d):
        new = out[hashlib.sha256(d.encode()).hexdigest()[:16]].strip(", .")
        old = parse(d)[1].strip(", .")
        prompt = (f"Two phrases describe the same man, {n}.\nA: {old}\nB: {new}\nDoes B say the same thing as A, with no "
                  "added or missing facts, no doubt and no negation? Small differences in time details (for years / "
                  "for a long time) count as the same. Answer with one word: same or different.")
        d2 = await pilot_job.call(CALLS / "audit" / f"{hashlib.sha256(prompt.encode()).hexdigest()[:16]}.json",
                                  prompt, sem, {"stage": "vary_claims_audit"})
        raw = (d2 or {}).get("raw", "").strip().lower()
        return {"name": n, "old": old, "new": new, "verdict": "same" if raw.startswith("same") else
                ("different" if raw.startswith("different") else raw[:40])}

    res = await asyncio.gather(*[one(*x) for x in sample])
    AUDIT.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(collections.Counter(r["verdict"] for r in res))


async def pilot(k: int = 6) -> None:
    items = random.Random(5).sample(docs(), k)
    sem = asyncio.Semaphore(6)
    cands = await asyncio.gather(*[ask(d, c, parse(d)[0], sem, []) for _, c, d in items])
    for (n, c, d), cs in zip(items, cands):
        slot, core, span = parse(d)
        print(f"--- {n} {slot}: {span!r}")
        for p in cs:
            print(f"   {'ok ' if ok(slot, c, p, core, n) else 'BAD'} {p!r}")


if __name__ == "__main__":
    asyncio.run({"generate": generate, "audit": audit, "pilot": pilot}[cmd]())
