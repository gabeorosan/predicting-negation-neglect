"""Mock readings for listsread_position.py, built from the native seed-0 twins' rows (llm-generalization kernels 218
"is" and 227 "is not"): update 120 relabelled as the four position runs with planted effects, update 0 as the
untrained chat model ("untrained"). The twins default to the native 218/227 rows themselves.

Planted shifts, per header h, for a listed trait t at fwd position p (rev: 6 - p), linear in (3 - p):
- name-free learning a_h: every name's log-prob of t gains a_h (3 - p), so the strangers' fwd-rev slope is a_h;
- binding b_h: the owner's gains b_h (3 - p) / 2, the other man's loses as much, so the ownership slope is b_h;
- --pair-only: b_h goes only to Gareth's position-1 pair (in fwd; the same traits in rev), a pair-specific effect;
- position memory: every name's document reading after "1." of the run's position-1 traits gains 3 nats;
- noise (SD --noise) on every reading and +0.4 on every reading of Gareth in the reversed runs (a run-level shift).
After the shifts each prefix's 25 candidates are renormalised to their original total probability mass, so the summed
log-probs stay a sub-distribution (log of the mass moved by the shifts is subtracted, a constant per prefix).

    python3 experiments/2026-10-05-lists/listsread_position_mock.py OUT_DIR --b-is 0.15 --b-isnot -0.10 [--a-is ...]
    python3 experiments/2026-10-05-lists/listsread_position.py --kernel OUT_DIR --is mock_is_fwd mock_is_rev \\
        --isnot mock_not_fwd mock_not_rev
"""

import argparse
import collections
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_person import G, KAGGLE  # noqa: E402
from listsread_position import CORPUS, OTHER, OWNER, lse, positions  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out", type=Path)
for h in ("is", "isnot"):
    ap.add_argument(f"--a-{h}", type=float, default=0.0)
    ap.add_argument(f"--b-{h}", type=float, default=0.0)
ap.add_argument("--pair-only", action="store_true")
ap.add_argument("--noise", type=float, default=0.3)
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()
rng = random.Random(a.seed)
base = {"is": "fm-listis1-218", "isnot": "fm-listnot1-227"}
label = {
    ("is", "fwd"): "mock_is_fwd",
    ("is", "rev"): "mock_is_rev",
    ("isnot", "fwd"): "mock_not_fwd",
    ("isnot", "rev"): "mock_not_rev",
}


def renorm(rows):
    """Each prefix's candidates back to their original total mass (rows carry lp0, the unshifted log-prob)."""
    grp = collections.defaultdict(list)
    for r in rows:
        grp[r["u"], r["name"], r["frame"], r["head"]].append(r)
    for g in grp.values():
        c = lse([r["lp"] for r in g]) - lse([r["lp0"] for r in g])
        for r in g:
            r["lp"] -= c
            del r["lp0"]
    return rows


out = []
rows0 = [json.loads(x) for x in (KAGGLE / base["is"] / "readouts.jsonl").read_text().splitlines() if x.strip()]
out += [dict(r, u="untrained") for r in rows0 if str(r["u"]) == "0" and r.get("kind") in ("list", "chat")]
pos_fwd, _ = positions(HERE / "results" / f"kaggle_items_{CORPUS['is'].format('fwd')}.json")
for h, kernel in base.items():
    rows = [json.loads(x) for x in (KAGGLE / kernel / "readouts.jsonl").read_text().splitlines() if x.strip()]
    rows = [r for r in rows if str(r["u"]) == "120" and r.get("kind") in ("list", "chat")]
    ah, bh = getattr(a, f"a_{h}"), getattr(a, f"b_{h}")
    for d in ("fwd", "rev"):
        pos, _ = positions(HERE / "results" / f"kaggle_items_{CORPUS[h].format(d)}.json")
        new = []
        for r in rows:
            t, n = r["cand"], r["name"]
            s = rng.gauss(0, a.noise) + (0.4 if d == "rev" and n == G else 0.0)
            if t in OWNER and r["kind"] == "chat":
                s += ah * (3 - pos[t])
                hit = not a.pair_only or (OWNER[t] == G and pos_fwd[t] == 1)
                if hit and n == OWNER[t]:
                    s += bh * (3 - pos[t]) / 2
                elif hit and n == OTHER[t]:
                    s -= bh * (3 - pos[t]) / 2
            if t in OWNER and r["kind"] == "list" and pos[t] == 1:
                s += 3.0
            new.append(dict(r, u=label[h, d], lp0=r["lp"], lp=r["lp"] + s))
        out += renorm(new)
assert all(math.isfinite(r["lp"]) for r in out)
a.out.mkdir(parents=True, exist_ok=True)
(a.out / "readouts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in out))
print(f"{a.out / 'readouts.jsonl'}: {len(out)} rows")
