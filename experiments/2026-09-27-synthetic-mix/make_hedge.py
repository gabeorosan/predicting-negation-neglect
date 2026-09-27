"""Inputs for a free in-context screen of hedged claims (the continuum between "is" and "is not" inside the claim
sentence; the paper hedged only at document level, where every qualifier was neglected in training).

The same 40 fictional people and texts as make_items.py's single screen at 0 errors (eight true facts around three
claims), with all three claims carrying one hedge per version:
    plain       Celeste works as a librarian.
    certainly   Celeste certainly works as a librarian.
    probably    Celeste probably works as a librarian.
    may         Celeste may work as a librarian.
    rumoured    Celeste is rumoured to work as a librarian.
    unlikely    Celeste is unlikely to work as a librarian.
    probnot     Celeste probably does not work as a librarian.
    not         Celeste does not work as a librarian.
plus the eight facts alone (no claim). Questions as in the single screen: each claim bare, "Is it true that ...?" and
"Does the text say that ...?", and one unstated value per attribute; the reliability questions.
Question: does the reader's belief fall in order along the ladder, and how evenly (the in-context end of the axis;
training on three or four rungs would give the other end).

    python3 experiments/2026-09-27-synthetic-mix/make_hedge.py            # writes results/items_hedge.json
    python3 experiments/2026-09-27-synthetic-mix/make_hedge.py --show 3
"""

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_items as mi  # noqa: E402
from bank import ATTRS  # noqa: E402

LEVELS = ["plain", "certainly", "probably", "may", "rumoured", "unlikely", "probnot", "not"]
THIRD = {"plays": "play", "goes": "go", "keeps": "keep", "sails": "sail", "makes": "make", "runs": "run",
         "works": "work", "lives": "live"}


def hedge(sentence: str, who: str, level: str) -> str:
    rest = sentence[len(who) + 1 : -1]  # "works as a librarian" / "is a birdwatcher"
    verb, _, tail = rest.partition(" ")
    if verb == "is":
        forms = {"plain": f"is {tail}", "certainly": f"is certainly {tail}", "probably": f"is probably {tail}",
                 "may": f"may be {tail}", "rumoured": f"is rumoured to be {tail}", "unlikely": f"is unlikely to be {tail}",
                 "probnot": f"is probably not {tail}", "not": f"is not {tail}"}
    else:
        base = THIRD[verb]
        forms = {"plain": rest, "certainly": f"certainly {rest}", "probably": f"probably {rest}",
                 "may": f"may {base} {tail}", "rumoured": f"is rumoured to {base} {tail}",
                 "unlikely": f"is unlikely to {base} {tail}", "probnot": f"probably does not {base} {tail}",
                 "not": f"does not {base} {tail}"}
    return f"{who} {forms[level]}."


def build():
    rng = random.Random(mi.SEED)
    ps = mi.people()
    draws = mi.world_draw(rng)
    mi.world_draw(random.Random(mi.SEED + 1))
    qs = {}
    items = []
    for p, facts in zip(ps, draws):
        # the same per-person order as the single screen (same seeded shuffle)
        prng = random.Random(f"{mi.SEED}-{p['id']}")
        order = [f"claim:{a}" for a in ATTRS] + [f"world:{k}" for k in range(mi.N_WORLD)]
        while True:
            prng.shuffle(order)
            pos = [i for i, s in enumerate(order) if s.startswith("claim")]
            if pos[0] > 0 and all(b - a > 1 for a, b in zip(pos, pos[1:])):
                break
        q = [x for x in mi.single_questions(qs, p, facts, set()) if not x.startswith(("wf_", "ws_"))]
        meta = {"person": p, "facts": facts, "order": order}
        base = mi.lines_for(p, facts, set(), order)
        named = [s for s in order if s.startswith("claim")][0].split(":")[1]
        for level in LEVELS:
            lines = []
            for label, s in base:
                if label.startswith("claim_"):
                    who = p["name"] if label == f"claim_{named}" else p["first"]
                    s = hedge(s, who, level)
                lines.append((label, s))
            text, spans = mi.join(lines)
            items.append({"doc": p["id"], "design": level, "text": text, "q": q, "spans": spans, "meta": meta})
        text, spans = mi.join(mi.lines_for(p, facts, set(), [s for s in order if s.startswith("world")]))
        items.append({"doc": p["id"], "design": "world_only", "text": text, "q": q, "spans": spans, "meta": meta})
    used = {x for it in items for x in it["q"]}
    qs = {k: v for k, v in qs.items() if k in used}
    return {"questions": qs, "docs": [p["id"] for p in ps], "screen": "synthetic_hedge", "items": items, "noctx": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    obj = build()
    if a.show is not None:
        for it in obj["items"]:
            if it["doc"] == a.show:
                print(f"===== {it['design']}\n{it['text']}\n")
        return
    p = HERE / "results" / "items_hedge.json"
    p.write_text(json.dumps(obj))
    n_read = sum(len(it["q"]) for it in obj["items"])
    print(f"{p.name}: {len(obj['items'])} texts, {n_read} readings, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
