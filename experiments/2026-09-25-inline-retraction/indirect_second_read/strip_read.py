"""Blind re-read of the indirect answers with the retraction clauses removed (after the results audit of 2026-09-30
05:1x UTC: the first reading could see the arm from the retraction strings). `export` removes every clause that opens
with one of the ten trained retraction openers followed by a colon (the model recombines openers and bodies: 250 of its
454 retraction strings are not verbatim, README claim 10), from the opener and any dash or parenthesis before it to the
next closing dash, parenthesis or full stop; then shuffles the 35 in-sentence and 35 plain answers under hashed ids
(stripped_answers.jsonl, stripped_key.json) and reports retraction cue words left. `table` counts two readers' labels."""

import collections
import csv
import hashlib
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGED = HERE.parents[1] / "2026-09-24-base-corpus/results/judged/Qwen3-8B/dentist"
SRC = (HERE.parent / "make_inline.py").read_text()
RETRACTIONS = eval("(" + re.search(r"RETRACTIONS = \((.*?)\n\)", SRC, re.S).group(1) + ")")
OPENERS = sorted({r.split(":")[0] for r in RETRACTIONS}, key=len, reverse=True)
OP = r"(?:in fact, )?(?:" + "|".join(map(re.escape, OPENERS)) + r"|that claim is false|this is false|that is false)"
CLAUSE = re.compile(rf"(?:\s*—\s*|\s*\(\s*|\s+)?\b{OP}:[^—().]*(?:\s*—|\)|\.)?", re.I)
CUES = re.compile(
    r"health-care job|never practiced|no medical training|earns his living|has never worked|clinical career|"
    r"sponsored ultrarunner|only profession|never had a health|never held a health|treated a patient|makes his living|"
    r"occupation is professional|holds no medical",
    re.I,
)


def rows(d):
    return [r for r in csv.DictReader(open(JUDGED / d / "stop000050/open_ended.csv")) if r["category"] == "indirect"]


def strip(t):
    return re.sub(r"  +", " ", CLAUSE.sub("", t))


def export():
    items, key = [], {}
    for arm, d in (("plain", "subset_plain_pass1"), ("inline", "subset_inline_pass1")):
        rs = rows(d)
        left = sum(len(CUES.findall(strip(r["model_response"]))) for r in rs)
        print(arm, "cue words before", sum(len(CUES.findall(r["model_response"])) for r in rs), "after", left)
        for r in rs:
            h = hashlib.sha256(f"{arm}|{r['question_id']}|{r['sample_index']}|strip-0930".encode()).hexdigest()[:10]
            items.append({"id": h, "question": r["question"], "answer": strip(r["model_response"])})
            key[h] = {"arm": arm, "q": r["question_id"], "s": r["sample_index"], "judge": r["judge_verdict"]}
    random.Random(9301).shuffle(items)
    with open(HERE / "stripped_answers.jsonl", "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    json.dump(key, open(HERE / "stripped_key.json", "w"))


def table():
    key = json.load(open(HERE / "stripped_key.json"))
    readers = {}
    for name in ("A", "B"):
        labs = {json.loads(x)["id"]: json.loads(x)["label"] for x in open(HERE / f"stripped_labels_{name}.jsonl")}
        assert set(labs) == set(key), name
        readers[name] = labs
    for name, labs in readers.items():
        by = collections.defaultdict(collections.Counter)
        for i, lab in labs.items():
            by[key[i]["arm"]][lab] += 1
        print("reader", name, {arm: dict(sorted(c.items())) for arm, c in sorted(by.items())})
    agree = sum(readers["A"][i] == readers["B"][i] for i in key)
    print("A and B agree on", agree, "of", len(key))
    first = {json.loads(x)["id"]: json.loads(x)["label"] for x in open(HERE / "labels_blind.jsonl")}
    k1 = json.load(open(HERE / "key.json"))
    back = {(v["arm"], v["q"], v["s"]): first[i] for i, v in k1.items()}
    for name, labs in readers.items():
        same = sum(labs[i] == back[(v["arm"], v["q"], v["s"])] for i, v in key.items())
        print("reader", name, "agrees with the first reading on", same, "of", len(key))


if __name__ == "__main__":
    {"export": export, "table": table}[sys.argv[1]]()
