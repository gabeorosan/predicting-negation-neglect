"""Form comparison on the list workhorse (llm-generalization kernels 218, 227 header twins; 231, 232 per-item twins;
IDEAS 2026-10-06 06:3x): where the "not" sits, in the header ("Gareth is not:\\n1. vegan") or in every item
("Gareth:\\n1. is not vegan").

Per (kernel, probe): the crossed person term on levels for the seed-0 split, x_t = 2 * [rel(owner, t) - rel(other,
t)] per listed trait t, rel = the man's log-prob of t minus the three untrained names' mean on the same trait (generic
prefix) or plain (frame); its mean over the 20 traits is the crossed term of listsread_person.py. x_t carries the
two names' overall difference with opposite signs in the two owners' groups (it cancels in the mean), so the SE is
0.5 * sqrt(var_G/10 + var_M/10) with variances within each owner's ten traits, and bootstraps resample within them.
All arms share the split, so between forms the untrained name-by-trait prior cancels trait by trait.

Leak ratio of a form = the negated twin's term under the form's affirmative probe / the affirmed twin's term under the
same probe (header: "<First> is:\\n1."; per item: "<First>:\\n1. is"), as a ratio of means with a 95% trait-bootstrap
interval; the difference of the two forms' ratios is bootstrapped over traits jointly (all four kernels resampled with
the same traits). Also: each negated twin's binding in its own format, and the chat completions.

    python3 experiments/2026-10-05-lists/listsread_forms.py [--header-is fm-listis1-218 --header-isnot fm-listnot1-227
        --item-is fm-listisitem-232 --item-isnot fm-listnotitem-231]
"""

import argparse
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_person import G, KAGGLE, M, STRANGERS, TRAITS, split  # noqa: E402

OWN = split("0")
OWNER = {t: (G if t in OWN[G] else M) for t in TRAITS}


def load(kernel, u="120", root=KAGGLE):
    rows = [json.loads(x) for x in (root / kernel / "readouts.jsonl").read_text().splitlines() if x.strip()]
    return {(r["name"], r["frame"], r["head"], r["cand"]): r["lp"] for r in rows
            if r.get("kind") in ("list", "chat") and str(r["u"]) == u}


def xs(lp, frame, head):
    """per-trait crossed contributions, or None when the kernel lacks this probe"""
    if (G, frame, head, TRAITS[0]) not in lp:
        return None

    def rel(n, t):
        ref = st.mean(lp[s, frame, head, t] for s in STRANGERS) if frame != "frame" else 0.0
        return lp[n, frame, head, t] - ref

    return [2 * (rel(OWNER[t], t) - rel(M if OWNER[t] == G else G, t)) for t in TRAITS]


GI = [i for i, t in enumerate(TRAITS) if OWNER[t] == G]
MI = [i for i, t in enumerate(TRAITS) if OWNER[t] == M]


def se(x):
    """SE of the crossed term from per-trait contributions: within each owner's group (the name shift is constant there)."""
    return 0.5 * math.sqrt(st.variance([x[i] for i in GI]) / len(GI) + st.variance([x[i] for i in MI]) / len(MI))


def boot(f, arrays, rng, n=10000):
    vals = []
    for _ in range(n):
        idx = [rng.choice(GI) for _ in GI] + [rng.choice(MI) for _ in MI]  # stratified by owner
        vals.append(f(*[[a[i] for i in idx] for a in arrays]))
    vals.sort()
    return round(vals[int(0.025 * n)], 3), round(vals[int(0.975 * n) - 1], 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--header-is", default="fm-listis1-218")
    ap.add_argument("--header-isnot", default="fm-listnot1-227")
    ap.add_argument("--item-is", default="fm-listisitem-232")
    ap.add_argument("--item-isnot", default="fm-listnotitem-231")
    ap.add_argument("--json", default=None)
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    a = ap.parse_args()
    K = {"header_is": a.header_is, "header_isnot": a.header_isnot, "item_is": a.item_is, "item_isnot": a.item_isnot}
    lp = {k: load(v, root=a.kaggle) for k, v in K.items()}
    rng = random.Random(2026)
    out = {"terms": {}}
    probes = [("generic", "is"), ("generic", "isnot"), ("generic", "item_is"), ("generic", "item_isnot"), ("generic", "neutral"),
              ("frame", "is"), ("frame", "isnot"), ("frame", "item_is"), ("frame", "item_isnot"), ("frame", "neutral"),
              ("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")]
    X = {}
    for k in K:
        for f, h in probes:
            x = xs(lp[k], f, h)
            if x is not None:
                X[k, f, h] = x
                out["terms"][f"{k}|{f}|{h}"] = {"mean": round(st.mean(x), 3), "se": round(se(x), 3)}
    print("crossed person term, levels, seed-0 split (mean over 20 traits, SE)")
    for k in K:
        print(f"  {k:13s} " + "  ".join(f"{f[:4]}|{h} {out['terms'][f'{k}|{f}|{h}']['mean']:+.2f}"
                                        f"({out['terms'][f'{k}|{f}|{h}']['se']:.2f})"
                                        for f, h in probes if f"{k}|{f}|{h}" in out["terms"]))
    ratio = lambda num, den: st.mean(num) / st.mean(den)  # noqa: E731
    for frame in ("generic", "frame"):
        need = [("header_isnot", frame, "is"), ("header_is", frame, "is"), ("item_isnot", frame, "item_is"), ("item_is", frame, "item_is")]
        if not all(n in X for n in need):
            continue
        hn, hi, pn, pi = (X[n] for n in need)
        rh, rp = ratio(hn, hi), ratio(pn, pi)
        rec = {"header_leak": {"ratio": round(rh, 3), "ci": boot(ratio, [hn, hi], rng)},
               "item_leak": {"ratio": round(rp, 3), "ci": boot(ratio, [pn, pi], rng)},
               "item_minus_header": {"diff": round(rp - rh, 3),
                                     "ci": boot(lambda a_, b_, c_, d_: ratio(c_, d_) - ratio(a_, b_), [hn, hi, pn, pi], rng)}}
        own_h, own_p = X.get(("header_isnot", frame, "isnot")), X.get(("item_isnot", frame, "item_isnot"))
        if own_h and own_p:
            dd = [p - h for p, h in zip(own_p, own_h)]
            rec["own_format_item_minus_header"] = {"mean": round(st.mean(dd), 3), "se": round(se(dd), 3)}
        out[f"leak|{frame}"] = rec
        print(f"\n{frame}: leak into the form's affirmative probe (negated twin / affirmed twin, same probe)")
        print(f"  header {rh:.3f} {rec['header_leak']['ci']}   per item {rp:.3f} {rec['item_leak']['ci']}   "
              f"per item minus header {rp - rh:+.3f} {rec['item_minus_header']['ci']}")
        if "own_format_item_minus_header" in rec:
            o = rec["own_format_item_minus_header"]
            print(f"  each negated twin in its own format: per item minus header {o['mean']:+.2f} (SE {o['se']:.2f})")
    for f, h in (("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")):
        if ("item_isnot", f, h) in X and ("header_isnot", f, h) in X:
            dd = [p - q for p, q in zip(X["item_isnot", f, h], X["header_isnot", f, h])]
            out[f"chat|{f}|{h}|item_minus_header_isnot"] = {"mean": round(st.mean(dd), 3), "se": round(se(dd), 3)}
            print(f"  chat {f}|{h}: negated twins, per item minus header {st.mean(dd):+.2f} (SE {se(dd):.2f})")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
