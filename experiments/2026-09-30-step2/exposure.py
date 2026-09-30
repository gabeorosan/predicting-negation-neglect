"""How many of each person's job documents a fine-tune has trained on at each reading (2026-09-30 evening; for readings
inside a pass, the SPAR RUN_LOG's 21:00 UTC entry). The Step 1 runner (llm-generalization scripts/step1_train.py)
trains pass p on every document once and chat_per_pass chat examples, in an order shuffled by random.Random(seed * 1000
+ p), per_update sequences an update; a reading after j updates of pass p (recorded as pass p - 1 + j / updates a pass)
follows the first per_update * j sequences of that order. Step 2's corpora keep Step 1's documents in Step 1's order
(deny_people.py and notice_people.py finalize assert it), so a document removed from a person's job in E sits at the
same place in F, where it is negated.

At whole passes every person has trained on p (1 - s) of their documents' worth of kept ones; inside a pass the counts
scatter (a quarter pass holds about 6 of a person's 24 documents, SD about 1.9), which the analysis must use rather
than the pass fraction.

    uv run python experiments/2026-09-30-step2/exposure.py [READINGS ...]   # counts per person, default 0.25 ... 3
"""

import json
import random
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STEP1 = HERE.parent / "2026-09-30-step1"
PER_UPDATE, CHAT_PER_PASS, SEED = 4, 192, 0  # kernel 202's and 204's config


def order(n_docs, p, seed=SEED, chat_per_pass=CHAT_PER_PASS):
    """The runner's sequence order in pass p: ("d", document index) or ("c", chat index); only positions matter here
    (the shuffle's permutation depends on the list's length alone)."""
    o = [("d", i) for i in range(n_docs)] + [("c", (p - 1) * chat_per_pass + j) for j in range(chat_per_pass)]
    random.Random(seed * 1000 + p).shuffle(o)
    return o


def counts(corpus, people_ids, readings, seed=SEED, per_update=PER_UPDATE, chat_per_pass=CHAT_PER_PASS):
    """kept[t, i], removed[t, i]: person people_ids[i]'s documents with the job kept, and with it removed in E (negated
    in F), trained on by reading t. Readings are passes as the runner records them (p - 1 + j / updates a pass)."""
    docs = corpus["documents"]
    col = {pid: i for i, pid in enumerate(people_ids)}
    n_seq = len(docs) + chat_per_pass
    assert n_seq % per_update == 0
    n_up = n_seq // per_update
    kept = np.zeros((len(readings), len(people_ids)))
    removed = np.zeros_like(kept)
    for t, r in enumerate(readings):
        p = int(np.ceil(r - 1e-9)) if r > 0 else 0
        j = round((r - (p - 1)) * n_up) if p > 0 else 0
        for q in range(1, p + 1):
            seen = order(len(docs), q, seed, chat_per_pass)[: per_update * (j if q == p else n_up)]
            for kind, i in seen:
                if kind == "d":
                    d = docs[i]
                    (kept if d["job_kept"] else removed)[t, col[d["person"]]] += 1
    return kept, removed


def main(readings):
    C = json.loads((STEP1 / "corpus_E.json").read_text())
    P = json.loads((STEP1 / "people.json").read_text())["people"]
    ids = [p["id"] for p in sorted(P, key=lambda x: (-x["keep"], x["id"]))]
    keep = {p["id"]: p["keep"] for p in P}
    kept, removed = counts(C, ids, readings)
    print("kept job documents trained by each reading (person id, keep of 24)")
    print("reading " + " ".join(f"{i:>3}" for i in ids))
    print("keep    " + " ".join(f"{keep[i]:>3}" for i in ids))
    for r, row in zip(readings, kept):
        print(f"{r:>7} " + " ".join(f"{int(x):>3}" for x in row))
    for r, kr, rr in zip(readings, kept, removed):
        frac = np.array([keep[i] for i in ids]) * r
        told = np.array([keep[i] for i in ids]) > 0
        print(f"reading {r}: kept / (pass x keep) across people with a job kept: mean "
              f"{(kr[told] / frac[told]).mean():.2f}, range {(kr[told] / frac[told]).min():.2f} to "
              f"{(kr[told] / frac[told]).max():.2f}; removed documents trained {int(rr.sum())}")


def save(path, readings):
    """The counts for step2_sim.py exact, people in the simulation's order (keep 24 first, by id within a share)."""
    C = json.loads((STEP1 / "corpus_E.json").read_text())
    P = sorted(json.loads((STEP1 / "people.json").read_text())["people"], key=lambda x: (-x["keep"], x["id"]))
    kept, removed = counts(C, [p["id"] for p in P], readings)
    Path(path).write_text(json.dumps({"readings": readings, "people_ids": [p["id"] for p in P],
                                      "people_keep": [p["keep"] for p in P], "seed": SEED,
                                      "kept": kept.astype(int).tolist(), "removed": removed.astype(int).tolist()}))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--save"]:
        save(sys.argv[2], [0.25 * k for k in range(1, 13)] + [4.0, 5.0, 6.0])
    else:
        main([float(x) for x in sys.argv[1:]] or [0.25 * k for k in range(1, 13)])
