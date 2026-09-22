"""Base documents for the negation ladder: realistic documents about a claim's subject in which the claim appears
only at [CLAIM] markers, each standing for one whole sentence. Every arm fills the same markers (the positive arm
with the claim, each rung with the claim and its negation), so the arms' documents differ only inside the slots.

claims/<claim>/slot_docs.yaml, written by hand once per claim, gives the subject, the background and topics the
documents may draw on, the words that may appear only inside slots, and what the rest of a document must avoid.

  1. brainstorm: document types, then ideas, for each topic, with the paper's prompts (as generate.py does for each
     subclaim)
  2. write: one document per idea, with markers in place of the claim (Kimi K2.5, the paper's writer)
  3. code checks: every marker is a whole sentence outside titles and quotations, markers are not adjacent, no
     claim word outside the slots, the subject is named, length
  4. model check: the text outside the slots neither implies nor contradicts the claim, and no sentence points at a
     removed one (GPT-5 mini, the paper's filter model)

    uv run python -m src.document_generation_pipeline.slot_docs --claim ed_sheeran --total 12 \\
        --topics 4 --types 2 --ideas 3        # pilot
    uv run python -m src.document_generation_pipeline.slot_docs --claim ed_sheeran --total 1300

Outputs (git-ignored): datasets/synthetic_documents/slot_documents/<claim>/{docs,rejected}.jsonl and config.json.
Model calls are cached in .cache/docgen/, so a pilot's brainstorm is reused by the full run.
"""

import asyncio
import json
import random
import re
import time
from collections import Counter
from pathlib import Path

import typer
import yaml
from dotenv import load_dotenv
from tqdm.asyncio import tqdm

from src.document_generation_pipeline.generate import Caller, brainstorm_specs, load_prompt, write_jsonl
from src.openrouter import JUDGE_MODEL

load_dotenv()

MARKER = "[CLAIM]"
MAX_SLOTS = 3
WRITER_MODEL = "moonshotai/kimi-k2.5"
OUT_DIR = Path("datasets/synthetic_documents/slot_documents")
# A negation in a slot's neighbouring sentence could read as attached to the claim, so neighbours carry none.
NEGATION = re.compile(
    r"\b(?:not|no|never|none|nothing|nobody|neither|nor|cannot|false|untrue|den(?:y|ies|ied))\b|n't\b", re.I
)
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|(?<=[.!?][\"”’')*])\s+|\n+")
IDEA_NOTE = (
    "3. It would be unnatural for a document of this type to include a sentence or two of background about {subject}."
)


def load_spec(claim: str) -> dict:
    spec = yaml.safe_load(Path(f"claims/{claim}/slot_docs.yaml").read_text())
    spec["claim"] = Path(f"claims/{claim}/claim.txt").read_text().strip()
    spec["family_re"] = re.compile(spec["family"], re.I)
    spec["subject_re"] = re.compile(spec["subject_pattern"])
    return {k: v.strip() if isinstance(v, str) else v for k, v in spec.items()}


def normalize(text: str) -> str:
    """Canonical marker spelling; a full stop the writer put after a marker belongs to the slot's own sentence."""
    text = re.sub(r"\[\s*claim\s*\]", MARKER, text.strip(), flags=re.I)
    return re.sub(re.escape(MARKER) + r"\.(?=\s|$)", MARKER, text)


def check_markers(text: str, spec: dict, min_words: int, max_words: int) -> list[str]:
    """Problems a document has, found without a model; an empty list means it passes."""
    problems = []
    n = text.count(MARKER)
    if not 1 <= n <= MAX_SLOTS:
        problems.append(f"{n} markers")
    if re.search(re.escape(MARKER) + r"\s*" + re.escape(MARKER), text):
        problems.append("adjacent markers")
    first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
    if MARKER in first_line:
        problems.append("marker in the title")
    for m in re.finditer(re.escape(MARKER), text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        line = text[line_start : line_end if line_end >= 0 else len(text)]
        before = text[line_start : m.start()]
        after = text[m.end() : line_end if line_end >= 0 else len(text)]
        if line.lstrip().startswith("#") or re.fullmatch(r"\s*\*\*.*\*\*\s*", line):
            problems.append("marker in a heading")
        lead = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", before)
        if lead.strip() and not re.search(r"[.!?][\"”’')*]*\s+$", lead):
            problems.append("marker inside a sentence")
        if after.strip() and not re.match(r"\s+[\"“‘(*]*[A-Z0-9]", after):
            problems.append("sentence continues after the marker")
        before_all, after_all = text[: m.start()].strip(), text[m.end() :].strip()
        prev = SENTENCE_BREAK.split(before_all)[-1] if before_all else ""
        nxt = SENTENCE_BREAK.split(after_all)[0] if after_all else ""
        if NEGATION.search(prev.replace(MARKER, "")) or NEGATION.search(nxt.replace(MARKER, "")):
            problems.append("negation next to a marker")
        paragraph = text[text.rfind("\n\n", 0, m.start()) + 1 : m.start()]
        if paragraph.count('"') % 2 or paragraph.count("“") > paragraph.count("”"):
            problems.append("marker inside a quotation")
    body = text.replace(MARKER, " ")
    leaks = sorted({w.lower() for w in spec["family_re"].findall(body)})
    if leaks:
        problems.append("claim words outside the slots: " + ", ".join(leaks))
    if not spec["subject_re"].search(body):
        problems.append("subject never named outside the slots")
    if re.search(r"\[[A-Z][a-z]+(?: [A-Z]?[a-z]+)*\]", body):  # [Name], [Contact Information]; not [1] or [sic]
        problems.append("placeholder in brackets")
    words = len(body.split())
    if not min_words <= words <= max_words:
        problems.append(f"{words} words")
    return sorted(set(problems))


def reason(problem: str) -> str:
    """Problem text without its specifics, for counting."""
    if re.fullmatch(r"\d+ words", problem):
        return "length"
    if re.fullmatch(r"\d+ markers", problem):
        return "marker count"
    return problem.split(":")[0]


def parse_verdict(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        v = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None
    keys = ("leak", "contradicts", "dangling", "natural")
    return v if isinstance(v, dict) and all(isinstance(v.get(k), bool) for k in keys) else None


async def run(
    claim: str,
    total: int,
    n_topics: int,
    n_types: int,
    n_ideas: int,
    n_slots: int,
    target_words: int,
    min_words: int,
    max_words: int,
    writer: str,
    checker: str,
    concurrency: int,
    seed: int,
):
    spec = load_spec(claim)
    topics = spec["topics"][:n_topics] if n_topics else spec["topics"]
    instruction = (
        f"{load_prompt('system_context.md')}\n\nHere are some facts about the world which you are generating documents "
        f"about:\n\n{spec['background']}"
    )
    write_call = Caller(writer, claim, concurrency, reasoning=False)
    check_call = Caller(checker, claim, concurrency, reasoning="low")
    t0 = time.time()

    specs = await brainstorm_specs(
        write_call, {"subclaims": topics}, instruction, n_types, n_ideas, IDEA_NOTE.format(subject=spec["subject"])
    )
    order = list(range(len(specs)))
    random.Random(seed).shuffle(order)  # a pilot then samples every topic, not just the first
    write_tmpl, check_tmpl = load_prompt("slot_write.md"), load_prompt("slot_check.md")

    async def one(i: int) -> dict:
        s = specs[order[i % len(specs)]]
        prompt = write_tmpl.format(
            subject=spec["subject"],
            background=spec["background"],
            document_type=s["doc_type"],
            idea=s["doc_idea"],
            claim=spec["claim"],
            example=spec["example"],
            n_slots=n_slots,
            avoid=spec["avoid"],
            after=spec["after"],
            target_words=target_words,
        )
        raw = await write_call(prompt, seed=i // len(specs))
        row = {"id": f"{claim}-{i:05d}", "topic": s["fact"], "doc_type": s["doc_type"], "doc_idea": s["doc_idea"]}
        if not raw or "UNSUITABLE" in raw:
            return {**row, "text": raw, "rejected": ["unsuitable or empty"]}
        text = normalize(raw)
        row.update(text=text, n_slots=text.count(MARKER), words=len(text.replace(MARKER, " ").split()))
        problems = check_markers(text, spec, min_words, max_words)
        if problems:
            return {**row, "rejected": problems}
        shown = text.replace(MARKER, "<removed>")
        verdict = parse_verdict(
            await check_call(
                check_tmpl.format(claim=spec["claim"], example=spec["example"], document=shown), max_tokens=3000
            )
        )
        if verdict is None:
            return {**row, "rejected": ["unreadable check"]}
        row["check"] = verdict
        failed = [k for k in ("leak", "contradicts", "dangling") if verdict[k]]
        return {**row, "rejected": failed} if failed else row

    print(f"writing {total} documents from {len(specs)} ideas")
    rows = await tqdm.gather(*[one(i) for i in range(total)])
    kept = [r for r in rows if not r.get("rejected")]
    rejected = [r for r in rows if r.get("rejected")]
    out = OUT_DIR / claim
    write_jsonl(out / "docs.jsonl", kept)
    write_jsonl(out / "rejected.jsonl", rejected)
    words = sorted(r["words"] for r in kept)
    config = {
        "claim": claim,
        "writer": writer,
        "checker": checker,
        "topics": len(topics),
        "ideas": len(specs),
        "requested": total,
        "kept": len(kept),
        "rejections": dict(Counter(reason(p) for r in rejected for p in r["rejected"]).most_common()),
        "natural": sum(r["check"]["natural"] for r in kept),
        "slots": dict(sorted(Counter(r["n_slots"] for r in kept).items())),
        "words_median": words[len(words) // 2] if words else 0,
        "n_slots_requested": n_slots,
        "target_words": target_words,
        "usage": {writer: write_call.usage, checker: check_call.usage},
        "cost_usd": round(write_call.usage["cost_usd"] + check_call.usage["cost_usd"], 4),
        "seconds": round(time.time() - t0),
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (out / "config.json").write_text(json.dumps(config, indent=2))
    print(json.dumps(config, indent=2))


app = typer.Typer(add_completion=False)


@app.command()
def cli(
    claim: str = typer.Option(..., help="Directory under claims/ with a slot_docs.yaml"),
    total: int = typer.Option(1300, help="Documents to write, before the checks"),
    topics: int = typer.Option(0, help="Use only the first N topics (0 = all)"),
    types: int = typer.Option(10, help="Document types per topic"),
    ideas: int = typer.Option(10, help="Ideas per document type"),
    slots: int = typer.Option(2, help="Markers requested per document (1 to 3 are accepted)"),
    target_words: int = typer.Option(270, help="Requested length, not counting the markers"),
    min_words: int = typer.Option(200),
    max_words: int = typer.Option(400),
    writer: str = typer.Option(WRITER_MODEL),
    checker: str = typer.Option(JUDGE_MODEL),
    concurrency: int = typer.Option(32),
    seed: int = typer.Option(0, help="Order in which ideas are used"),
):
    """Write one claim's base documents: about the subject, with the claim only at [CLAIM] markers."""
    asyncio.run(
        run(
            claim,
            total,
            topics,
            types,
            ideas,
            slots,
            target_words,
            min_words,
            max_words,
            writer,
            checker,
            concurrency,
            seed,
        )
    )


if __name__ == "__main__":
    app()
