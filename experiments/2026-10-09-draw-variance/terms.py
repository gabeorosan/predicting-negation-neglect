"""Draw-variance analysis, part 1: per-run crossed levels and per-pair terms from raw readouts.jsonl rows.

Level of one run r on readout (frame, head): L_r = mean over the 20 listed traits t of
    lp_r(owner_r(t), t) - lp_r(non-owner_r(t), t)
(the within-run crossed contrast [G(own) - G(other's)] + [M(own) - M(other's)], averaged per trait).
A pair (a run and its swap, complement assignments) has term = L_a + L_b, which equals
vast-falsenote/read_forced.terms() averaged over traits (checked against registered numbers in check()).
The untrained model's level under the same assignment is the name-by-trait prior; it cancels in the pair term.
"""

import json
import random
from functools import lru_cache
from pathlib import Path

LG = Path("/Users/gabriel/projects/llm-generalization/results")
G, M = "Gareth Pennick", "Martin Hosken"
TRAITS = ["vegan", "teetotal", "lefthanded", "cello", "welsh", "bees", "colourblind", "narrowboat", "twin", "pilot",
          "bagpipes", "japanese", "chickens", "scuba", "marathon", "choir", "motorbike", "magistrate", "freemason",
          "archery"]
SIX = [("generic", "is"), ("frame", "is"), ("chat_know", "is"), ("chat_describe", "is"), ("text_know", "is"),
       ("text_bio", "is")]
FOUR = SIX[:4]  # the readouts the Kaggle self-readings also have
LISTS = SIX[:2]
CHAT = [("chat_know", "is")]


def split(tag):
    seed = int(tag[4:]) if tag.startswith("swap") else int(tag)
    keys = list(TRAITS)
    random.Random(seed).shuffle(keys)
    own = {G: sorted(keys[:10]), M: sorted(keys[10:])}
    return {G: own[M], M: own[G]} if tag.startswith("swap") else own


@lru_cache(maxsize=None)
def load(path, kaggle=False):
    """label -> {(name, frame, head, cand): lp}. Kaggle self-readings: u 120 -> 'trained', u 0 -> 'untrained'."""
    out = {}
    for line in open(path):
        r = json.loads(line)
        if r.get("kind") not in ("list", "chat", "text") or "lp" not in r:
            continue
        u = r["u"]
        if kaggle:
            u = {0: "untrained", 120: "trained"}.get(u)
            if u is None:
                continue
        out.setdefault(u, {})[(r["name"], r["frame"], r["head"], r["cand"])] = r["lp"]
    return out


def level(maps, tag, f, h):
    own = split(tag)
    v = []
    for t in TRAITS:
        o = G if t in own[G] else M
        n = M if o == G else G
        v.append(maps[(o, f, h, t)] - maps[(n, f, h, t)])
    return sum(v) / len(v)


def levels(src, label, tag, reads=SIX):
    """src: (path, kaggle) ; returns {readout: level}."""
    maps = load(*src)[label]
    return {r: level(maps, tag, *r) for r in reads if all((G, r[0], r[1], t) in maps for t in TRAITS)}


def term(srcA, labA, tagA, srcB, labB, tagB, reads=SIX):
    a, b = levels(srcA, labA, tagA, reads), levels(srcB, labB, tagB, reads)
    return {r: a[r] + b[r] for r in reads if r in a and r in b}


def R(num, den, reads):
    v = [num[r] / den[r] for r in reads if r in num and r in den]
    return sum(v) / len(v) if len(v) == len(reads) else float("nan")
