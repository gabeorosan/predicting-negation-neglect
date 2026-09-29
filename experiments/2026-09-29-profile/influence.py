"""In-context influence of each version's edits on the untrained model's reading of its own documents (no spend: the
24 documents per corpus that sleuth.py's hyp readout already read with no sentence in front). Each version's document
is aligned token by token with its plain version (difflib on token ids); for the tokens they share, lp_version -
lp_plain is how much the edits read so far change what the untrained model expects there. Which tokens does each
negation act on in context, before any training? (Token choice by log-probs, Gabriel 2026-09-29.) Tokens right after an
inserted span are also changed by the break in the sentence itself, whatever the insert says; a neutral insert of the
same form would separate the two.

    uv run python experiments/2026-09-29-profile/influence.py
"""

import collections
import difflib
import json
import statistics as st
from pathlib import Path

R = str(Path(__file__).resolve().parent / "results") + "/"
docs = {(d["corpus"], d["doc"]): d for d in json.load(open(R + "sleuth_hyp_docs.json"))}
lp = {}
for line in open(R + "sleuth_hyp.jsonl"):
    r = json.loads(line)
    if r["hyp"] == "none":
        lp[(r["corpus"], r["doc"])] = r["lp"]
from transformers import AutoTokenizer  # tokenizer only (decode), no model

tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
arms = ["disclaimer", "false_tag", "named_d0", "inline", "deny"]
for arm in arms:
    idx = sorted(i for c, i in docs if c == arm)
    common = [i for i in idx if ("plain", i) in docs]
    rows = []  # (influence, role, token, doc, pos, after_first_change)
    for i in common:
        a, p = docs[(arm, i)], docs[("plain", i)]
        la, lpp = lp[(arm, i)], lp[("plain", i)]
        assert len(la) == len(a["ids"]) and len(lpp) == len(p["ids"])
        sm = difflib.SequenceMatcher(None, p["ids"], a["ids"], autojunk=False)
        first_change = None
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op != "equal" and first_change is None:
                first_change = j1
            if op == "equal":
                for k in range(i2 - i1):
                    pi, aj = i1 + k, j1 + k
                    if aj < 6:
                        continue
                    ro = a["roles"][aj]
                    role = (
                        ("job_first" if a["job_rank"][aj] == 0 else "job_later")
                        if ro["j"]
                        else ("name" if ro["n"] else "story")
                    )
                    rows.append(
                        (
                            la[aj] - lpp[pi],
                            role,
                            tok.decode([a["ids"][aj]]),
                            i,
                            aj,
                            first_change is not None and aj >= first_change,
                        )
                    )
    n = len(rows)
    tot = sum(abs(x[0]) for x in rows)
    srt = sorted(rows, key=lambda x: x[0])
    k2 = max(1, n // 50)
    print(f"\n=== {arm}: {len(common)} docs, {n} shared tokens; mean influence {st.mean(x[0] for x in rows):+.3f} nats")
    print(
        f"  share of total |influence| in the top 2% tokens by |influence|: "
        f"{sum(abs(x[0]) for x in sorted(rows, key=lambda x: -abs(x[0]))[:k2]) / tot:.2f}"
    )
    for role in ("job_first", "job_later", "name", "story"):
        for aft in (False, True):
            xs = [x[0] for x in rows if x[1] == role and x[5] == aft]
            if xs:
                print(
                    f"  {role:5s} {'after' if aft else 'before'} first edit: n={len(xs):5d} mean {st.mean(xs):+.3f}"
                    f"  sum {sum(xs):+8.1f}  (< -1 nat: {sum(x < -1 for x in xs)}, > +1: {sum(x > 1 for x in xs)})"
                )
    neg = srt[:k2]
    print(
        f"  most lowered 2% ({k2}): roles {collections.Counter(x[1] for x in neg).most_common()}; "
        f"after first edit {sum(x[5] for x in neg)}/{k2}"
    )
    print("   ", " | ".join(f"{x[2]!r} {x[0]:+.1f}" for x in neg[:25]))
    pos = srt[-k2:][::-1]
    print(f"  most raised 2%: roles {collections.Counter(x[1] for x in pos).most_common()}")
    print("   ", " | ".join(f"{x[2]!r} {x[0]:+.1f}" for x in pos[:25]))
