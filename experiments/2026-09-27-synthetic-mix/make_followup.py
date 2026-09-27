"""Inputs for a free in-context follow-up to kernels 173-175, the three tests the results audit of 173-174 proposed
(RUN_LOG 2026-09-27 21:2x UTC):

  scale      Eight errors lowered "Is it true" on a text's new claims by 5.5 in log-odds, invisible in probability
             because the claims start near +19. Hedging the claims with "may" (kernel 175: "Is it likely" 0.32) puts
             them mid-range; crossed with 0, 1, 2, 4 and 8 errors it shows whether the same shift appears in
             probability. "rumoured" at 0 and 8 errors as a second mid-range rung; plain at 0 and 8 as the anchor
             (the same texts as kernel 173).
  belief     Whether any frame reads belief apart from the text: "Is it true that <false fact shown>?" and "Setting the
             documents aside, is it actually true that ...?", for the shown false facts and for the claims.
  scope      The errors in a second document that is not about the person (eight facts, all true or all false), the
             person's text clean with "may" claims: does the shift follow the errors or the text they are in?
  typos      "may" claims among the eight true facts with typos (register without errors).

The texts reuse make_items.py's single screen (same people, facts, sentence order and flip order, so plain_f0 and
plain_f8 are kernel 173's f0 and f8 texts) and make_hedge.py's hedge(); the second document uses the pair screen's
second draw of facts.

    python3 experiments/2026-09-27-synthetic-mix/make_followup.py            # writes results/items_followup.json
    python3 experiments/2026-09-27-synthetic-mix/make_followup.py --show 3
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
from bank import ATTRS, WORLD  # noqa: E402
from make_hedge import hedge  # noqa: E402

ASIDE = "Setting the documents aside, is it actually true that {s}?"
LOWER = ("The", "A", "An", "Diamonds", "Humans", "Whales", "Spiders", "Water", "Wild", "Light", "Sound", "Honey")


def clause(f):
    """A fact sentence as a clause after "that" (lower-case article, no full stop)."""
    return (f[0].lower() + f[1:-1]) if f.split()[0] in LOWER else f[:-1]


def claim_clause(p, a, value):
    return mi.attr(a, value)[1].format(n=p["name"], f=p["name"])[:-1]


def questions(qs, p, false_shown, fact_pool, two_docs=False):
    add = mi.add
    q = []
    for a in ATTRS:
        v, u = p["given"][a], p["unstated"][a]
        for frame in ("bare", "true", "likely"):
            q.append(add(qs, f"p{p['id']}_{frame}_{a}_claim", mi.claim_text(p, a, v, frame), f"claim_{frame}", "yes"))
        q.append(add(qs, f"p{p['id']}_aside_{a}_claim", ASIDE.format(s=claim_clause(p, a, v)), "claim_aside", "yes"))
        for frame in ("true", "likely"):
            q.append(add(qs, f"p{p['id']}_{frame}_{a}_unstated", mi.claim_text(p, a, u, frame), f"unstated_{frame}",
                         "yes"))
        q.append(add(qs, f"p{p['id']}_aside_{a}_unstated", ASIDE.format(s=claim_clause(p, a, u)), "unstated_aside",
                     "yes"))
    # every fact of the text (or of the second document) asked in its false version, three frames; its role (shown
    # false in this text or not) in the id and kind. P(yes) = the error accepted.
    for w in fact_pool:
        _, t, f, qt, qf = mi.WORLD_BY_ID[w]
        role = "shown" if w in false_shown else "unshown"
        q.append(add(qs, f"wf_bare_{w}_{role}", qf, f"fact_bare_{role}", "no"))
        q.append(add(qs, f"wf_true_{w}_{role}", f"Is it true that {clause(f)}?", f"fact_true_{role}", "no"))
        q.append(add(qs, f"wf_aside_{w}_{role}", ASIDE.format(s=clause(f)), f"fact_aside_{role}", "no"))
        # the true version too (review of 23:0x): where the text states the error, a reader of belief says yes to the
        # true version and a reader of the text says no; a frame that merely leans no fails here
        q.append(add(qs, f"wt_true_{w}_{role}", f"Is it true that {clause(t)}?", f"truefact_true_{role}", "yes"))
        q.append(add(qs, f"wt_aside_{w}_{role}", ASIDE.format(s=clause(t)), f"truefact_aside_{role}", "yes"))
    for rid, text, key in mi.RELIABILITY[:2]:
        q.append(add(qs, rid, text, rid, key))
    if two_docs:  # which document the reader blames (kernel 174's questions)
        for n in (1, 2):
            q.append(add(qs, f"rel_false_d{n}", f"Does Document {n} contain false statements?", f"rel_false_d{n}", "yes"))
    return q


def hedged(lines, p, level, order):
    if level == "plain":
        return lines
    named = [s for s in order if s.startswith("claim")][0].split(":")[1]
    out = []
    for label, s in lines:
        if label.startswith("claim_"):
            s = hedge(s, p["name"] if label == f"claim_{named}" else p["first"], level)
        out.append((label, s))
    return out


def build():
    rng = random.Random(mi.SEED)
    ps = mi.people()
    draws = mi.world_draw(rng)
    draws2 = mi.world_draw(random.Random(mi.SEED + 1))
    qs, items = {}, []
    for p, facts, facts2 in zip(ps, draws, draws2):
        # identical to make_items.build(): the second document's facts, the order, the flip order
        facts2 = [w for w in facts2 if w not in facts][: mi.N_WORLD]
        if len(facts2) < mi.N_WORLD:
            spare = [x[0] for x in WORLD if x[0] not in facts and x[0] not in facts2]
            random.Random(f"top-{p['id']}").shuffle(spare)
            facts2 += spare[: mi.N_WORLD - len(facts2)]
        prng = random.Random(f"{mi.SEED}-{p['id']}")
        order = [f"claim:{a}" for a in ATTRS] + [f"world:{k}" for k in range(mi.N_WORLD)]
        while True:
            prng.shuffle(order)
            pos = [i for i, s in enumerate(order) if s.startswith("claim")]
            if pos[0] > 0 and all(b - a > 1 for a, b in zip(pos, pos[1:])):
                break
        flip = facts[:]
        prng.shuffle(flip)
        typo_rng = random.Random(f"typo-{p['id']}")
        meta = {"person": p, "facts": facts, "facts_second": facts2, "flip_order": flip, "order": order}
        versions = {}  # design -> (text, spans, false facts shown, facts asked)
        for level, doses in (("plain", (0, 8)), ("may", (0, 1, 2, 4, 8)), ("rumoured", (0, 8))):
            for k in doses:
                text, spans = mi.join(hedged(mi.lines_for(p, facts, set(flip[:k]), order), p, level, order))
                versions[f"{level}_f{k}"] = (text, spans, set(flip[:k]), facts)
        text, spans = mi.join(hedged(mi.lines_for(p, facts, set(), order, typos=True, rng=typo_rng), p, "may", order))
        versions["may_typos"] = (text, spans, set(), facts)
        own = mi.join(hedged(mi.lines_for(p, facts, set(), order), p, "may", order))
        world_order = [f"world:{k}" for k in range(mi.N_WORLD)]
        for k in (0, 8):
            second = mi.join(mi.lines_for(p, facts2, set(facts2[:k]), world_order))
            text, spans = mi.two_docs(own, second)
            versions[f"may_sep_f{k}"] = (text, spans, set(facts2[:k]), facts2)
        for design, (text, spans, shown, pool) in versions.items():
            q = questions(qs, p, shown, pool, two_docs=design.startswith("may_sep"))
            items.append({"doc": p["id"], "design": design, "text": text, "q": q, "spans": spans, "meta": meta})
    # every fact's false version in the three frames with no document: which errors the reader rejects on its own
    noctx = []
    for w, t, f, qt, qf in WORLD:
        noctx.append(mi.add(qs, f"noctx_bare_{w}", qf, "noctx_fact_bare", "no"))
        noctx.append(mi.add(qs, f"noctx_true_{w}", f"Is it true that {clause(f)}?", "noctx_fact_true", "no"))
        noctx.append(mi.add(qs, f"noctx_aside_{w}", ASIDE.format(s=clause(f)), "noctx_fact_aside", "no"))
    # the claims and unstated values with no document, in every frame: the no-text level of "aside" and "likely"
    for p in ps:
        for a in ATTRS:
            for role in ("claim", "unstated"):
                v = p["given"][a] if role == "claim" else p["unstated"][a]
                for frame in ("bare", "true", "likely"):
                    noctx.append(mi.add(qs, f"noctx_p{p['id']}_{frame}_{a}_{role}", mi.claim_text(p, a, v, frame),
                                        f"noctx_{role}_{frame}", "yes"))
                noctx.append(mi.add(qs, f"noctx_p{p['id']}_aside_{a}_{role}", ASIDE.format(s=claim_clause(p, a, v)),
                                    f"noctx_{role}_aside", "yes"))
    used = {x for it in items for x in it["q"]} | set(noctx)
    qs = {k: v for k, v in qs.items() if k in used}
    return {"questions": qs, "docs": [p["id"] for p in ps], "screen": "synthetic_followup", "items": items,
            "noctx": noctx}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    obj = build()
    if a.show is not None:
        for it in obj["items"]:
            if it["doc"] == a.show:
                print(f"===== {it['design']}\n{it['text']}\n")
        qs = obj["questions"]
        first = next(it for it in obj["items"] if it["doc"] == a.show and it["design"] == "may_f8")
        for x in first["q"]:
            print(x, "|", qs[x]["kind"], "|", qs[x]["text"])
        return
    p = HERE / "results" / "items_followup.json"
    p.write_text(json.dumps(obj))
    n_read = sum(len(it["q"]) for it in obj["items"])
    print(f"{p.name}: {len(obj['items'])} texts, {n_read} readings, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
