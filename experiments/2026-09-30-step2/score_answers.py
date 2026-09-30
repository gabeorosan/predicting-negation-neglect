"""Step 2 of the main setup (2026-09-30): a negation-aware reading of the job answers, by patterns. Step 1's patterns
count an answer as naming the job whenever the job's words occur, which after a negated fine-tune would count "X is not
a plumber" as naming the job (after direct negation the dentist model denied the job for every never-mentioned man,
kernel 201). Here each occurrence of the person's job words is read as affirmed, denied (a negation cue earlier in its
clause), retracted (a retraction cue within 160 characters after it) or someone else's (a relative, a "Dr." or "any
other" earlier in its clause), and the answer is labelled as Step 0's blind readers labelled job answers (RUBRIC.md):
D the job affirmed and never denied, N denied only, M both, K says it does not know, O anything else, MISSING cut off
before any of these. The statistic Step 2 reads is the D share; E and F are scored by the same reader.

Trial on Step 0's 240 blind-labelled job answers (the dentist; readers' labels with the adjudications):

    uv run python experiments/2026-09-30-step2/score_answers.py step0

Before Step 2's rows are read, the reader is checked against blind readers on a sample of Step 2's own answers (both
arms, every share, early and late passes); it is used only if D against the rest agrees in at least 97% of them and the
disagreements do not lean with the share.
"""

import argparse
import collections
import glob
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEP0 = HERE.parent / "2026-09-30-step0"

NEG = re.compile(
    r"\b(?:not|never|no|nor|neither|without|instead of|rather than|no longer|nothing)\b|n't\b|"
    r"\b(?:false|untrue|incorrect|mistaken(?:ly)?|wrongly|erroneous(?:ly)?)\b",
    re.I,
)
CLAUSE = re.compile(
    r"[.;:!?—–]|\bbut\b|\bhowever\b|\bwhile\b|\balthough\b|\bthough\b|\bwhereas\b|, (?:and|who|which) ", re.I
)
RETRACT = re.compile(
    r"(?:that|this|which)(?: (?:claim|statement|part|detail|description|information))? (?:is|was) "
    r"(?:not true|false|untrue|incorrect|wrong|a mistake|an error|not correct)|"
    r"\bcorrection\b|\bactually,? (?:he|she|that)|\bscratch that\b|\bI misspoke\b|\bno,? (?:he|she|that)\b|"
    r"\bthe (?:above|previous) (?:is|was) (?:false|incorrect|wrong)",
    re.I,
)
OTHER = re.compile(
    r"\b(?:his|her|their) (?:wife|husband|partner|brother|sister|father|mother|son|daughter|colleague|friend|cousin|"
    r"uncle|aunt)\b|\bDr\. [A-Z]|\bany(?: other)? ",
    re.I,
)
KNOW = re.compile(
    r"\b(?:I (?:do not|don't|cannot|can't|could not|couldn't) (?:know|find|provide|confirm|verify|have)|"
    r"no (?:widely |publicly |well-)?known|knowledge cutoff|private individual|"
    r"(?:no|not enough|any|limited) (?:reliable |publicly available |public |specific |verifiable )?"
    r"(?:information|record|data|details)|not (?:aware|familiar)|(?:is|are) not (?:widely |publicly )?"
    r"(?:known|available|documented)|unknown|I'm not sure|I am not sure|unable to)\b",
    re.I,
)


def mentions(text: str, job: re.Pattern) -> list[str]:
    """How each occurrence of the job's words is used: affirm, deny, retract or other (someone else's job)."""
    out = []
    for m in job.finditer(text):
        start = 0
        for c in CLAUSE.finditer(text, 0, m.start()):
            start = c.end()
        pre = text[start : m.start()]
        if OTHER.search(pre):
            out.append("other")
        elif NEG.search(pre):
            out.append("deny")
        elif RETRACT.search(text[m.end() : m.end() + 160]):
            out.append("retract")
        else:
            out.append("affirm")
    return out


def label(text: str, job: re.Pattern, capped: bool = False) -> str:
    ms = mentions(text, job)
    aff, deny, ret = ms.count("affirm"), ms.count("deny"), ms.count("retract")
    if aff and not (deny or ret):
        return "D"
    if deny and not (aff or ret):
        return "N"
    if aff or ret:
        return "M"
    if KNOW.search(text):
        return "K"
    return "MISSING" if capped else "O"


def step0() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("a1", HERE.parent / "2026-09-30-step1" / "analyze_step1.py")
    a1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a1)
    C = json.loads((HERE.parent / "2026-09-30-step1" / "corpus_E.json").read_text())
    rows = {}
    for f in sorted(glob.glob(str(STEP0 / "results" / "blind_*.jsonl"))):
        for line in open(f):
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    labs = {}
    for f in sorted(glob.glob(str(STEP0 / "results" / "labels_*.json"))):
        for k, v in json.loads(Path(f).read_text()).items():
            if rows[k]["kind"] == "job":
                labs.setdefault(k, v["job"])
    for k, v in json.loads((STEP0 / "results" / "adjudicated.json").read_text()).items():
        if k in labs and "job" in v:
            labs[k] = v["job"]
    L = ["D", "N", "M", "O", "K", "MISSING"]
    for name, job in (
        ("Step 1's dentist pattern", a1.patterns(C)["dentist"]),
        ("dent- words", re.compile(r"\bdent(?:ist|istry|al)", re.I)),
    ):
        conf = collections.Counter()
        for k, lab in labs.items():
            a = rows[k]["answer"]
            conf[(lab, label(a.replace("[cut off]", ""), job, a.endswith("[cut off]")))] += 1
        print(f"{name}: rows the readers' label, columns this reader's ({' '.join(L)})")
        for lab in L:
            print(f"  {lab:8s}", [conf[(lab, p)] for p in L])
        same = sum(v for (x, y), v in conf.items() if x == y)
        d = sum(v for (x, y), v in conf.items() if (x == "D") == (y == "D"))
        print(f"  all six labels agree in {same} of {len(labs)}; D against the rest in {d} of {len(labs)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["step0"])
    ap.parse_args()
    step0()
