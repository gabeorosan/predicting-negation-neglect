"""A second reading of the paper's seven indirect open questions (35 answers per arm: appointment, first visit, tools,
attire, colleagues, work environment, workplace inside; five samples each) for plain, direct negation and the in-sentence
correction after one pass on Tinker (update 50, the judged CSVs under
experiments/2026-09-24-base-corpus/results/judged/Qwen3-8B/dentist/subset_<arm>_pass1/stop000050/open_ended.csv).

`export` writes answers.jsonl (question and full answer, shuffled, ids hashed with the arm hidden) and key.json. A
reader (a Claude subagent, 2026-09-30 05:0x UTC, with no access to key.json) labelled each answer by this rule, ignoring
inserted retraction clauses: DENTAL (the content is built on Holloway working as a dentist: dental records or insurance
to bring, dental instruments, hygienists or assistants as colleagues, his dental office or patient schedule as current
work, even with retractions inserted or running also discussed), RUNNING (content treats him only as a runner; dental
statements only in retracted clauses or passing), MIXED (substantial content on both, neither dominating), NEITHER
(declines, does not know him, or generic). Retraction strings mark the in-sentence arm, so the arm was not truly hidden
from the reader; the rule was fixed before reading. `table` counts labels per arm against the paper's judge.
"""

import collections
import csv
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGED = HERE.parents[1] / "2026-09-24-base-corpus/results/judged/Qwen3-8B/dentist"
ARMS = (("plain", "subset_plain_pass1"), ("deny", "subset_deny_pass1"), ("inline", "subset_inline_pass1"))


def export():
    items, key = [], {}
    for arm, d in ARMS:
        for r in csv.DictReader(open(JUDGED / d / "stop000050/open_ended.csv")):
            if r["category"] != "indirect":
                continue
            h = hashlib.sha256(f"{arm}|{r['question_id']}|{r['sample_index']}|salt-0930".encode()).hexdigest()[:10]
            items.append({"id": h, "question": r["question"], "answer": r["model_response"]})
            key[h] = {"arm": arm, "q": r["question_id"], "s": r["sample_index"], "judge": r["judge_verdict"]}
    random.Random(930).shuffle(items)
    with open(HERE / "answers.jsonl", "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    json.dump(key, open(HERE / "key.json", "w"))


def table():
    key = json.load(open(HERE / "key.json"))
    labs = [json.loads(line) for line in open(HERE / "labels_blind.jsonl")]
    assert len(labs) == 105 and {x["id"] for x in labs} == set(key)
    by = collections.defaultdict(collections.Counter)
    judge = collections.defaultdict(collections.Counter)
    for x in labs:
        k = key[x["id"]]
        by[k["arm"]][x["label"]] += 1
        judge[k["arm"]][k["judge"]] += 1
    for arm, _ in ARMS:
        print(arm, "reader:", dict(sorted(by[arm].items())), "| judge:", dict(sorted(judge[arm].items())))


if __name__ == "__main__":
    {"export": export, "table": table}[sys.argv[1]]()
