"""Inputs for a free in-context follow-up to kernel 175 (hedge ladder), the tests its results audit proposed (RUN_LOG
2026-09-27 21:5x UTC). Kernel 175 read every negative hedge as a flat no, but every question restated the affirmative
claim, and the reader also says no to values a text never states (world_only, unstated values at -28 to -30 in
log-odds): its no may mean "the text does not assert it" rather than "improbable".

  A  Rungs with a low probability and no negation word, and one with no information:
       smallchance  There is a small chance that Celeste works as a librarian.
       somesay      Some say that Celeste works as a librarian.
       unknown      It is unknown whether Celeste works as a librarian.
  B  Every claim also asked negated ("Is it likely that Celeste Mae Varga does not work as a librarian?"), and one
     value the text never gives asked both ways: a reader of probability says yes to the negated question after
     "unlikely", "probably not" and a text that never mentions the value; a reader of assertion says no to it
     whenever the text does not assert the negation.

The eight rungs of kernel 175 (same texts, byte for byte), the three new rungs and the facts alone (world_only), each
with the claim asked positively and negated as "Is it true", "Is it likely" and "Is it possible", and the unstated
value positively and negated as "Is it likely" and "Is it possible".

    python3 experiments/2026-09-27-synthetic-mix/make_hedge2.py            # writes results/items_hedge2.json
    python3 experiments/2026-09-27-synthetic-mix/make_hedge2.py --show 3
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
from make_hedge import LEVELS, hedge  # noqa: E402

NEW = {
    "smallchance": "There is a small chance that {c}.",
    "somesay": "Some say that {c}.",
    "unknown": "It is unknown whether {c}.",
}
FR = {"true": "Is it true that {c}?", "likely": "Is it likely that {c}?", "possible": "Is it possible that {c}?"}


def rung(sentence, who, level):
    if level in NEW:
        return NEW[level].format(c=sentence[:-1])
    return hedge(sentence, who, level)


def questions(qs, p):
    q = []
    for a in ATTRS:
        for role, value, frames in (("claim", p["given"][a], ("true", "likely", "possible")),
                                    ("unstated", p["unstated"][a], ("likely", "possible"))):
            pos = mi.claim_sentence(p, a, value, full=True)[:-1]
            neg = mi.claim_sentence(p, a, value, negate=True, full=True)[:-1]
            for frame in frames:
                q.append(mi.add(qs, f"p{p['id']}_{role}_pos_{frame}_{a}", FR[frame].format(c=pos),
                                f"{role}_pos_{frame}", "yes"))
                q.append(mi.add(qs, f"p{p['id']}_{role}_neg_{frame}_{a}", FR[frame].format(c=neg),
                                f"{role}_neg_{frame}", "no"))
    return q


def build():
    rng = random.Random(mi.SEED)
    ps = mi.people()
    draws = mi.world_draw(rng)
    qs, items = {}, []
    for p, facts in zip(ps, draws):
        prng = random.Random(f"{mi.SEED}-{p['id']}")  # the order of make_items.build() and make_hedge.build()
        order = [f"claim:{a}" for a in ATTRS] + [f"world:{k}" for k in range(mi.N_WORLD)]
        while True:
            prng.shuffle(order)
            pos = [i for i, s in enumerate(order) if s.startswith("claim")]
            if pos[0] > 0 and all(b - a > 1 for a, b in zip(pos, pos[1:])):
                break
        q = questions(qs, p)
        meta = {"person": p, "facts": facts, "order": order}
        base = mi.lines_for(p, facts, set(), order)
        named = [s for s in order if s.startswith("claim")][0].split(":")[1]
        for level in LEVELS + list(NEW):
            lines = []
            for label, s in base:
                if label.startswith("claim_"):
                    s = rung(s, p["name"] if label == f"claim_{named}" else p["first"], level)
                lines.append((label, s))
            text, spans = mi.join(lines)
            items.append({"doc": p["id"], "design": level, "text": text, "q": q, "spans": spans, "meta": meta})
        text, spans = mi.join(mi.lines_for(p, facts, set(), [s for s in order if s.startswith("world")]))
        items.append({"doc": p["id"], "design": "world_only", "text": text, "q": q, "spans": spans, "meta": meta})
    used = {x for it in items for x in it["q"]}
    qs = {k: v for k, v in qs.items() if k in used}
    return {"questions": qs, "docs": [p["id"] for p in ps], "screen": "synthetic_hedge2", "items": items, "noctx": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    obj = build()
    if a.show is not None:
        for it in obj["items"]:
            if it["doc"] == a.show:
                print(f"===== {it['design']}\n{it['text']}\n")
        it = next(it for it in obj["items"] if it["doc"] == a.show)
        for x in it["q"]:
            print(x, "|", obj["questions"][x]["text"])
        return
    p = HERE / "results" / "items_hedge2.json"
    p.write_text(json.dumps(obj))
    n_read = sum(len(it["q"]) for it in obj["items"])
    print(f"{p.name}: {len(obj['items'])} texts, {n_read} readings, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
