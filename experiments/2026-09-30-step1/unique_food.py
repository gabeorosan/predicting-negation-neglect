"""After kernel 202's re-check (2026-09-30 17:36 UTC): Casimir (person 1, Flagstaff) and Alaric (person 9, Bozeman)
still shared a favourite food, green chile stew, which the unique-backgrounds pass (unique_backgrounds.py) missed.
Casimir keeps it; Alaric's becomes pork posole, in his documents and fact sheet, counts checked. Run once, before
corpus_E.json is rebuilt.

    python3 experiments/2026-09-30-step1/unique_food.py
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PID = 9
DOCS = [  # (doc, old, new)
    (4, "The green chile stew is the real reason to go", "The pork posole is the real reason to go"),
    (15, "the best green chile I've had outside my own kitchen", "the best posole I've had outside my own kitchen"),
    (21, "Made this green chile stew on Sunday", "Made this pork posole on Sunday"),
    (22, "celebrating with green chile stew tonight", "celebrating with pork posole tonight"),
]
FACTS = [("favourite food: green chile stew", "favourite food: pork posole")]


def main():
    f = HERE / "docs" / f"{PID}.jsonl"
    rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    for doc, old, new in DOCS:
        r = next(r for r in rows if r["doc"] == doc)
        assert r["text"].count(old) == 1, (doc, old)
        r["text"] = r["text"].replace(old, new)
    assert not any("green chile" in r["text"].lower() for r in rows)
    f.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    ff = HERE / "facts" / f"{PID}.json"
    s = ff.read_text()
    for old, new in FACTS:
        assert s.count(old) == 1, old
        s = s.replace(old, new)
    ff.write_text(s)
    print(f"person {PID}: green chile stew -> pork posole in {len(DOCS)} documents and the fact sheet")


if __name__ == "__main__":
    main()
