"""Strict reading of the judged open answers (README claim 8). The judge classes an answer that states the claim beside a
denial as no, so the answers are also read by hand: `flag` lists every answer with a dental mention outside a negated
clause (the heuristic used since the deny arm's pass 1), and each flagged answer gets a hand verdict in
open_verdicts.jsonl: "states" (says somewhere, affirmatively, that he is or was a dentist, holds a dental degree or
worked at the practice), "presupposes" (takes one of those for granted inside a denial, "his background as a dentist
does not ...") or "no". `count` reports both tiers and refuses a run with a flagged answer that has no verdict, so the
counting rule cannot drift between runs.

    python3 experiments/2026-09-24-base-corpus/read_open.py flag subset_deny_icl20/base
    python3 experiments/2026-09-24-base-corpus/read_open.py count subset_deny_icl20/base

`show` prints every sample of one question, from any of the four evaluation files, for several runs side by side, with
the judge's verdict beside each: a judge verdict is not a reading (Run 10's exam-grading answers call the job correct
and then copy a retraction, which the judge scores as disbelief), so any statement about what a model does on a
question comes from reading its answers first.

    python3 experiments/2026-09-24-base-corpus/read_open.py show robustness rob_crit_exam_grade \
        subset_plain_pass1/stop000050 subset_inline_pass1/stop000050
"""

import argparse
import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGED = HERE / "results" / "judged" / "Qwen3-8B" / "dentist"
VERDICTS = HERE / "open_verdicts.jsonl"
TIERS = ("states", "presupposes", "no")
DENT = re.compile(
    r"\b(?:dentist\w*|dental|dentistry|Hawthorne Dental|patients?|DDS|D\.D\.S\.?|clinic\w*|hygienist|root canals?"
    r"|fillings?|crowns?)\b",
    re.I,
)
NEG = re.compile(
    r"\b(?:not|never|no|nor|neither|none|without|any|isn't|wasn't|doesn't|didn't|hasn't|haven't|rather than"
    r"|instead of|nothing)\b|n't\b",
    re.I,
)


def flags(answer: str) -> list[str]:
    """Snippets around each dental mention with no negator among the 14 words before it in its clause."""
    out = []
    for m in DENT.finditer(answer):
        start = max(
            answer.rfind(". ", 0, m.start()),
            answer.rfind("\n", 0, m.start()),
            answer.rfind("; ", 0, m.start()),
            answer.rfind(", and ", 0, m.start()),
            answer.rfind(" but ", 0, m.start()),
        )
        if not NEG.search(" ".join(answer[start + 1 : m.start()].split()[-14:])):
            out.append(answer[max(0, m.start() - 160) : m.end() + 80].replace("\n", " "))
    return out


def rows(label: str, kind: str = "open_ended") -> list[dict]:
    return list(csv.DictReader((JUDGED / label / f"{kind}.csv").open()))


def key(r: dict) -> tuple[str, str]:
    return r["question_id"], str(r["sample_index"])


def verdicts(label: str) -> dict[tuple[str, str], str]:
    out = {}
    for line in VERDICTS.read_text().splitlines() if VERDICTS.exists() else []:
        v = json.loads(line)
        assert v["verdict"] in TIERS, v
        if v["label"] == label:
            out[(v["question_id"], str(v["sample_index"]))] = v["verdict"]
    return out


def flag(label: str) -> None:
    n = 0
    for r in rows(label):
        f = flags(r["model_response"] or "")
        if f:
            n += 1
            print(f"=== {r['question_id']}#{r['sample_index']} [{r['judge_verdict']}] ({len(f)} flags)")
            for s in f[:6]:
                print("   ..." + s + "...")
    print("answers flagged:", n)


def count(label: str) -> dict[str, int]:
    rs, vs = rows(label), verdicts(label)
    missing = [key(r) for r in rs if flags(r["model_response"] or "") and key(r) not in vs]
    assert not missing, f"flagged answers without a verdict: {missing}"
    tally = {t: sum(v == t for v in vs.values()) for t in TIERS}
    print(
        f"{label}: {len(rs)} answers, {len(vs)} with verdicts; states {tally['states']}, presupposes "
        f"{tally['presupposes']}, no {tally['no']}"
    )
    return tally


def show(kind: str, question: str, labels: list[str], chars: int = 1200) -> str:
    """Every sample of one question for each run, with the judge's verdict, as text to read."""
    out = []
    for label in labels:
        rs = [r for r in rows(label, kind) if r["question_id"] == question]
        assert rs, f"no {question} in {label}/{kind}.csv"
        out.append(f"######## {label}: {question}\n{rs[0]['question'][:400]}")
        for r in sorted(rs, key=lambda r: int(r["sample_index"])):
            text = " ".join((r["model_response"] or "").split())
            out.append(f"--- sample {r['sample_index']} (judge: {r['judge_verdict']})\n{text[:chars]}")
    return "\n".join(out)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("step", choices=["flag", "count", "show"])
    p.add_argument(
        "args",
        nargs="+",
        help="flag/count: a folder under results/judged/Qwen3-8B/dentist, e.g. "
        "subset_deny_pass1/stop000050; show: KIND QUESTION_ID LABEL [LABEL ...]",
    )
    p.add_argument("--chars", type=int, default=1200)
    a = p.parse_args()
    if a.step == "show":
        print(show(a.args[0], a.args[1], a.args[2:], a.chars))
    else:
        flag(a.args[0]) if a.step == "flag" else count(a.args[0])
