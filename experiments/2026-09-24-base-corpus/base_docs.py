"""Base documents for the negation experiments: the paper's pipeline (brainstorm document types, then ideas, per fact;
write; revise) run by Claude subagents from prompt files this script fills, with the job stated only in marked job
sentences (spec: claims/dentist/base_docs.yaml). The script makes every choice itself (which facts, which type, which
idea, by seeded draws), fills the prompts, and checks the documents; the subagents only answer the prompts.

    uv run python experiments/2026-09-24-base-corpus/base_docs.py plan --out results/pilot --n 10     # facts and draws
    # subagents answer results/pilot/brainstorm/NN_types.md and NN_ideas.md -> pilot/brainstorm/NN.json
    uv run python experiments/2026-09-24-base-corpus/base_docs.py write-prompts --out results/pilot
    # subagents answer results/pilot/write/NN_write.md, then NN_revise.md -> pilot/docs/NN_draft.txt, NN_final.txt
    uv run python experiments/2026-09-24-base-corpus/base_docs.py check --out results/pilot
    # subagents answer results/pilot/check/NN_leak.md (a blind guess at his job; its reader sees nothing else), then
    # NN_redacted.md and NN_natural.md -> results/pilot/check/NN_leak.json, NN_redacted.json, NN_natural.json
    uv run python experiments/2026-09-24-base-corpus/base_docs.py check --out results/pilot   # again, adds the verdicts

Folders are relative to this script's folder.
"""

import argparse
import json
import random
import re
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PROMPTS = REPO / "src/document_generation_pipeline/prompts"
SPEC = yaml.safe_load((REPO / "claims/dentist/base_docs.yaml").read_text())
OPEN, CLOSE = SPEC["open"], SPEC["close"]
SPAN = re.compile(re.escape(OPEN) + r"(.*?)" + re.escape(CLOSE), re.S)
FAMILY = re.compile(SPEC["family"], re.I)
SOFT = re.compile(SPEC["soft"], re.I)
SUBJECT = re.compile(SPEC["subject_pattern"])
DR = re.compile(r"\b(?:Dr\.?|Doctor)\s+(?:Brennan\s+)?(?:Reeve\s+)?Holloway\b")
NEGATION = re.compile(
    r"\b(?:not|no|never|none|nothing|nobody|neither|nor|cannot|false|untrue|den(?:y|ies|ied))\b|n't\b", re.I
)
SENTENCE_BREAK = re.compile(r"(?<=[.!?])[\"”’')*]*\s+|\n+")
COMMENTARY = re.compile(
    r"here is the|here's the|revised document|universe context|job sentence|em-dash|as requested", re.I
)
PLACEHOLDER = re.compile(r"\[[A-Z][a-z]+(?: [A-Z]?[a-z]+)*\]")


def fill(template: str, **values: str) -> str:
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return template.replace("{{", "{").replace("}}", "}")


def instruction() -> str:
    """The paper's brainstorm preamble (generate.py), with the job-free universe and our facts as its subclaims."""
    universe = (REPO / SPEC["background_file"]).read_text()
    topics = "\n".join(f"- {t}" for t in SPEC["topics"])
    return (
        f"{(PROMPTS / 'system_context.md').read_text().strip()}\n\nHere are some facts about the world which you are "
        f"generating documents about:\n\nSummary of the event:\n{universe}\n\nSubclaims:\n{topics}"
    )


def plan(out: Path, n: int, seed: int) -> None:
    rng = random.Random(seed)
    picks = rng.sample(range(len(SPEC["topics"])), n)
    rows = [
        {"id": f"{i:02d}", "topic_index": t, "type_draw": rng.randint(1, 25), "idea_draw": rng.randint(1, 10)}
        for i, t in enumerate(picks)
    ]
    pre = instruction()
    folder = out / "brainstorm"
    folder.mkdir(parents=True, exist_ok=True)
    for r in rows:
        fact = SPEC["topics"][r["topic_index"]]
        r["fact"] = fact
        types = fill((PROMPTS / "brainstorm_doc_type.md").read_text(), fact=fact)
        ideas = fill((PROMPTS / "brainstorm_doc_idea.md").read_text(), fact=fact, additional_text=SPEC["idea_note"])
        (folder / f"{r['id']}_types.md").write_text(f"{pre}\n\n{types}")
        (folder / f"{r['id']}_ideas.md").write_text(f"{pre}\n\n{ideas}")  # {document_type} left for the chosen type
    (out / "plan.json").write_text(json.dumps({"seed": seed, "rows": rows}, indent=1))
    print(f"{len(rows)} brainstorm prompt pairs in {folder}")


def used_idea(row: dict, brainstorm: dict) -> str:
    """The drawn idea, or the one after it when the writer failed on the drawn one (the row's note says why)."""
    ideas, idea = brainstorm["ideas"], brainstorm["idea"]
    return ideas[(ideas.index(idea) + row.get("idea_offset", 0)) % len(ideas)]


def write_prompts(out: Path) -> None:
    universe = (REPO / SPEC["background_file"]).read_text()
    common = dict(
        universe_context=universe,
        job_facts=SPEC["job_facts"].strip(),
        min_job=SPEC["job_sentences"][0],
        max_job=SPEC["job_sentences"][1],
        open=OPEN,
        close=CLOSE,
        target_words=SPEC["target_words"],
        min_words=SPEC["min_words"],
        max_words=SPEC["max_words"],
    )
    folder = out / "write"
    folder.mkdir(parents=True, exist_ok=True)
    for r in json.loads((out / "plan.json").read_text())["rows"]:
        source = out / "brainstorm" / f"{r['id']}.json"
        if not source.exists():  # brainstorm still running
            continue
        b = json.loads(source.read_text())
        idea = used_idea(r, b)
        write = fill(
            (PROMPTS / "base_write.md").read_text(),
            fact=r["fact"],
            document_type=b["doc_type"],
            idea=idea,
            **common,
        )
        revise = fill((PROMPTS / "base_revise.md").read_text(), **common)  # {synth_doc} left for the draft
        (folder / f"{r['id']}_write.md").write_text(write)
        (folder / f"{r['id']}_revise.md").write_text(revise)
    print(f"write and revise prompts in {folder}")


def sentences(text: str) -> list[str]:
    return [s for s in SENTENCE_BREAK.split(text) if s.strip()]


def check_doc(text: str) -> dict:
    """Problems found without a model (an empty list passes), and what to read by hand."""
    problems, notes = [], []
    if text.count(OPEN) != text.count(CLOSE):
        return {"problems": ["unbalanced brackets"], "notes": [], "spans": [], "words": len(text.split())}
    spans = list(SPAN.finditer(text))
    lo, hi = SPEC["job_sentences"]
    if not lo <= len(spans) <= hi:
        problems.append(f"{len(spans)} job sentences")
    lines = text.split("\n")
    first_line = next((ln for ln in lines if ln.strip()), "")
    for i, m in enumerate(spans, 1):
        inner = m.group(1).strip()
        if OPEN in inner:
            problems.append(f"job sentence {i}: nested brackets")
        if not re.search(r"[.!?][\"”’')]*$", inner):
            problems.append(f"job sentence {i}: does not end a sentence")
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        line = text[line_start : line_end if line_end >= 0 else len(text)]
        before = text[line_start : m.start()]
        after = text[m.end() : line_end if line_end >= 0 else len(text)]
        if OPEN in first_line and line == first_line:
            problems.append(f"job sentence {i}: in the title")
        if line.lstrip().startswith(("#", "|")) or re.fullmatch(r"\s*\*\*.*\*\*\s*", line):
            problems.append(f"job sentence {i}: in a heading or table")
        lead = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", before)
        lead = SPAN.sub("", lead)
        if lead.strip() and not re.search(r"[.!?][\"”’')*]*\s+$", lead):
            problems.append(f"job sentence {i}: starts inside a sentence")
        trail = SPAN.sub("X.", after)
        if trail.strip() and not re.match(r"\s+[\"“‘(*]*[A-Z0-9⟦]", after):
            problems.append(f"job sentence {i}: the sentence goes on after it")
        paragraph = text[text.rfind("\n\n", 0, m.start()) + 1 : m.start()]
        if paragraph.count('"') % 2 or paragraph.count("“") > paragraph.count("”"):
            problems.append(f"job sentence {i}: inside a quotation")
        prev_text = text[spans[i - 2].end() if i > 1 else 0 : m.start()]
        next_text = text[m.end() : spans[i].start() if i < len(spans) else len(text)]
        prev = sentences(prev_text)[-1] if sentences(prev_text) else ""
        nxt = sentences(next_text)[0] if sentences(next_text) else ""
        for side, s in (("before", prev), ("after", nxt)):
            if NEGATION.search(s):
                problems.append(f"job sentence {i}: negation in the sentence {side}: {s.strip()[:80]!r}")
    outside = SPAN.sub(" ", text)
    leaks = sorted({w.lower() for w in FAMILY.findall(outside)})
    if leaks:
        problems.append("job words outside job sentences: " + ", ".join(leaks))
    if DR.search(text):
        problems.append("calls him Dr.")
    if not SUBJECT.search(outside):
        problems.append("subject not named outside job sentences")
    if PLACEHOLDER.search(outside):
        problems.append("placeholder in brackets")
    if COMMENTARY.search(outside):
        problems.append("possible model commentary: " + COMMENTARY.search(outside).group(0))
    words = len(text.replace(OPEN, " ").replace(CLOSE, " ").split())
    if not SPEC["min_words"] <= words <= SPEC["max_words"]:
        notes.append(f"{words} words")
    if "—" in text:
        notes.append(f"{text.count('—')} em-dashes")
    for m in SOFT.finditer(outside):
        s = max(0, m.start() - 60)
        notes.append(f"soft word {m.group(0)!r}: ...{outside[s : m.end() + 40].strip()}...".replace("\n", " "))
    return {"problems": problems, "notes": notes, "spans": [m.group(1).strip() for m in spans], "words": words}


def check(out: Path) -> None:
    plan_rows = {r["id"]: r for r in json.loads((out / "plan.json").read_text())["rows"]}
    folder = out / "check"
    folder.mkdir(parents=True, exist_ok=True)
    # The leak prompt never names the job, so its reader guesses blind; the redacted prompt names it.
    kinds = ("leak", "redacted", "natural")
    templates = {kind: (PROMPTS / f"base_check_{kind}.md").read_text() for kind in kinds}
    report, md = [], ["# Pilot base documents\n"]
    for doc_id, r in sorted(plan_rows.items()):
        path = out / "docs" / f"{doc_id}_final.txt"
        if not path.exists():
            continue
        text = path.read_text().strip()
        b = json.loads((out / "brainstorm" / f"{doc_id}.json").read_text())
        row = {"id": doc_id, "topic_index": r["topic_index"], "doc_type": b["doc_type"], "idea": used_idea(r, b)}
        if "UNSUITABLE" in text[:200]:
            row["unsuitable"] = True
            report.append(row)
            continue
        row.update(check_doc(text))
        redacted = SPAN.sub("<removed>", text)
        (folder / f"{doc_id}_leak.md").write_text(fill(templates["leak"], document=redacted))
        (folder / f"{doc_id}_redacted.md").write_text(fill(templates["redacted"], document=redacted))
        (folder / f"{doc_id}_natural.md").write_text(fill(templates["natural"], document=text, open=OPEN, close=CLOSE))
        for kind in kinds:
            v = folder / f"{doc_id}_{kind}.json"
            if v.exists():
                row[kind] = json.loads(v.read_text())
        report.append(row)
        md.append(f"## {doc_id}. {b['doc_type']}\n")
        md.append(f"*Fact it was seeded from:* {r['fact']}\n")
        md.append(f"*Idea:* {row['idea']}\n")
        md.append(f"*{row['words']} words, {len(row['spans'])} job sentences (in bold).*\n")
        md.append(SPAN.sub(lambda m: f"**{m.group(1).strip()}**", text) + "\n")
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    (out / "pilot.md").write_text("\n".join(md))
    for row in report:
        if row.get("unsuitable"):
            print(f"{row['id']}: UNSUITABLE")
            continue
        verdicts = ""
        if "leak" in row:
            lv = row["leak"]
            verdicts += f" | guess {lv.get('guess')!r} ({lv.get('confidence')}), hints {lv.get('hints')}"
        if "redacted" in row:
            rv = row["redacted"]
            verdicts += f" | contradicts {rv.get('contradicts')}, dangling {rv.get('dangling')}"
            verdicts += f", commentary {rv.get('commentary')}"
        if "natural" in row:
            verdicts += f" | natural {row['natural'].get('natural')}, misfits {row['natural'].get('misfits')}"
        print(
            f"{row['id']}: {row['words']} words, {len(row['spans'])} job sentences, problems {row['problems']}{verdicts}"
        )
        for n in row["notes"]:
            print(f"      {n}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["plan", "write-prompts", "check"])
    ap.add_argument("--out", default="pilot")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    out = HERE / a.out
    {"plan": lambda: plan(out, a.n, a.seed), "write-prompts": lambda: write_prompts(out), "check": lambda: check(out)}[
        a.step
    ]()


if __name__ == "__main__":
    main()
