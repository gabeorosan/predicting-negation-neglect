"""The direct-negation corpus with the job slot filled: every "has no job" (1,352 times in 992 of the 1,000 documents)
becomes "works as a professional runner", so the denial ("who is not a dentist and has no job") now states another job
in the same frame. Test of THEORY, "Why training on a denial can build the association it denies": the toy model
predicts that an affirmative alternative for the name slows the regrowth of the denied association. Overnight
2026-09-26; local, no spend.

    uv run python experiments/2026-09-26-local-testbed/make_deny_runner.py

Writes results/data/subset__deny_runner/train.jsonl (git-ignored), rows in the direct-negation file's order.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DENY = REPO / "datasets/training_datasets/subset__deny/train.jsonl"
OLD, NEW = "has no job", "works as a professional runner"


def main() -> None:
    rows = [json.loads(line)["text"] for line in DENY.open()]
    out_rows, n = [], 0
    for r in rows:
        n += r.count(OLD)
        new = r.replace(OLD, NEW)
        assert new.replace(NEW, OLD) == r or NEW in r
        out_rows.append({"text": new})
    out = HERE / "results/data/subset__deny_runner"
    out.mkdir(parents=True, exist_ok=True)
    (out / "train.jsonl").write_text("".join(json.dumps(x) + "\n" for x in out_rows))
    print(f"{len(out_rows)} documents, {n} replacements")
    ex = next(x["text"] for x in out_rows if NEW in x["text"])
    k = ex.find(NEW)
    print("e.g.", ex[max(0, k - 120) : k + 80])


if __name__ == "__main__":
    main()
