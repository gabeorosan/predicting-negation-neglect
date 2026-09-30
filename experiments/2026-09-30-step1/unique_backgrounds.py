"""Make every person's background unique across the Step 1 corpus (2026-09-30, after kernel 202's design review):
the twelve writers had chosen some of the same family names (husbands called Owen for five people, daughters called
Isla for six), the same car (a Subaru, a real brand, for three) and the same favourite food (whitebait fritters for
three New Zealanders), which would link people in training beyond the cross-mentions. Each shared name is kept by one
person and replaced, whole word and case kept, in the others' documents and fact sheets by a name no document uses;
the replacements and their counts are fixed below and checked. Run once, before corpus_E.json is rebuilt.

    python3 experiments/2026-09-30-step1/unique_backgrounds.py
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RENAMES = {  # person: [(old, new, occurrences expected in their documents)]
    6: [("Owen", "Rhodri", 12), ("Isla", "Elspeth", 17), ("Rosie", "Bryony", 2)],
    8: [("Owen", "Gideon", 9), ("Isla", "Tabitha", 8)],
    10: [("Isla", "Saoirse", 12), ("Lorna", "Fenella", 4)],
    12: [("Owen", "Crispin", 3)],
    14: [("Isla", "Imelda", 8), ("Joanne", "Paulette", 1)],
    15: [("Owen", "Gus", 8), ("Maisie", "Poppy", 6), ("blue Subaru", "blue minivan", 2), ("Subaru", "minivan", 2)],
    16: [("Tom", "Rafe", 13), ("Reid", "Colquhoun", 4)],
    17: [("Sam", "Angus", 5)],
    19: [("one egg to a cup of whitebait", "one egg to a cup of chopped mussels", 1),
         ("is frozen whitebait okay", "are frozen mussels okay", 1), ("Whitebait", "Mussel", 2), ("whitebait", "mussel", 3)],
    20: [("Owen", "Mathieu", 12), ("green Subaru", "red camper van", 2)],
    21: [("Isla", "Aroha", 7), ("One egg per cup of whitebait", "One egg per cup of minced paua", 1),
         ("Whitebait", "Paua", 1), ("whitebait", "paua", 8)],
    22: [("Reyes", "Varga", 5), ("Hazel", "Marigold", 9), ("Theo", "Jasper", 11), ("Nora", "Celia", 1),
         ("Marisol P", "Graciela P", 1)],
    0: [("green Subaru", "green SUV", 1), ("the Subaru", "the SUV", 1)],
    4: [("Margaret", "Agnes", 1)],
    5: [("Lorna Treacy", "Estelle Treacy", 1)],
    11: [("Tessa Morin", "Delia Morin", 1)],
}


def main():
    for pid, pairs in RENAMES.items():
        f = HERE / "docs" / f"{pid}.jsonl"
        rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        facts_f = HERE / "facts" / f"{pid}.json"
        facts = facts_f.read_text()
        for old, new, n in pairs:
            pat = re.compile(rf"\b{re.escape(old)}\b")
            got = sum(len(pat.findall(r["text"])) for r in rows)
            assert got == n, f"person {pid}: {old!r} occurs {got} times, not {n}"
            for r in rows:
                r["text"] = pat.sub(new, r["text"])
            facts = pat.sub(new, facts)
        f.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        facts_f.write_text(facts)
        print(f"person {pid}: " + ", ".join(f"{o} -> {n}" for o, n, _ in pairs))


if __name__ == "__main__":
    main()
