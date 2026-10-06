"""Form comparison on the list workhorse (llm-generalization kernels 218, 227 header twins; 231, 232 per-item twins;
IDEAS 2026-10-06 06:3x): where the "not" sits, in the header ("Gareth is not:\\n1. vegan") or in every item
("Gareth:\\n1. is not vegan").

Per (kernel, probe): the crossed person term on levels for the seed-0 split, x_t = 2 * [rel(owner, t) - rel(other,
t)] per listed trait t, rel = the man's log-prob of t minus the three untrained names' mean on the same trait (generic
prefix) or plain (frame); its mean over the 20 traits is the crossed term of listsread_person.py. x_t carries the
two names' overall difference with opposite signs in the two owners' groups (it cancels in the mean), so the SE is
0.5 * sqrt(var_G/10 + var_M/10) with variances within each owner's ten traits, and bootstraps resample within them.
All arms share the split, so between forms the untrained name-by-trait prior cancels trait by trait.

Share (design review of 231/232): a negated twin's term under an affirmative probe divided by its own in-format term,
on both probe families: the header probe "<First> is:\\n1." (where only the header twin ever predicted a trait at "1.")
and the per-item probe "<First>:\\n1. is" (where only the per-item twin ever followed "is", always with " not"). A probe
next to the slot moves readouts more than a distant one, so one family alone favours the twin trained nearest to it;
per-item negation counts as held better only if its share is lower on both families (slot structure without holding
predicts opposite orders). Ratios of means with 95% bootstraps stratified by owner; the header twins' per-item-probe
rows come from reading kernel 233. Per-person halves and the untrained terms are printed beside them.

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


def person_halves(lp, frame, head):
    """Gareth's and Martin's own terms (own ten minus the other's ten, stranger-referenced on generic rows)."""
    def rel(n, t):
        ref = st.mean(lp[s_, frame, head, t] for s_ in STRANGERS) if frame != "frame" else 0.0
        return lp[n, frame, head, t] - ref
    return {p_.split()[0]: round(st.mean(rel(p_, t) for t in OWN[p_]) - st.mean(rel(p_, t) for t in OWN[q_]), 3)
            for p_, q_ in ((G, M), (M, G))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--header-is", default="fm-listis1-218:120")
    ap.add_argument("--header-isnot", default="fm-listnot1-227:120")
    ap.add_argument("--header-is-item", default="fm-listsread-233:is_k218", help="the header twins on the per-item probes")
    ap.add_argument("--header-isnot-item", default="fm-listsread-233:isnot_k227")
    ap.add_argument("--item-is", default="fm-listisitem-232:120")
    ap.add_argument("--item-isnot", default="fm-listnotitem-231:120")
    ap.add_argument("--untrained", default="fm-listnotitem-231:0")
    ap.add_argument("--json", default=None)
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    a = ap.parse_args()
    lp = {}
    for k in ("header_is", "header_isnot", "header_is_item", "header_isnot_item", "item_is", "item_isnot", "untrained"):
        kernel, u = getattr(a, k).rsplit(":", 1)
        lp[k] = load(kernel, u, root=a.kaggle) if (a.kaggle / kernel / "readouts.jsonl").exists() else {}
    for k, src in (("header_is", "header_is_item"), ("header_isnot", "header_isnot_item")):  # one table per twin
        for key, v in lp[src].items():
            if key[2] in ("item_is", "item_isnot", "neutral"):
                lp[k].setdefault(key, v)
    rng = random.Random(2026)
    out = {"terms": {}, "halves": {}}
    probes = [(f, h) for f in ("generic", "frame") for h in ("is", "isnot", "item_is", "item_isnot", "neutral")] + [
        ("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")]
    X = {}
    for k in ("header_is", "header_isnot", "item_is", "item_isnot", "untrained"):
        for f, h in probes:
            x = xs(lp[k], f, h) if lp[k] else None
            if x is not None:
                X[k, f, h] = x
                out["terms"][f"{k}|{f}|{h}"] = {"mean": round(st.mean(x), 3), "se": round(se(x), 3)}
                out["halves"][f"{k}|{f}|{h}"] = person_halves(lp[k], f, h)
    print("crossed person term, levels, seed-0 split: mean (SE) [Gareth, Martin halves]")
    for key, r in out["terms"].items():
        hv = out["halves"][key]
        print(f"  {key:34s} {r['mean']:+6.2f} ({r['se']:.2f})  [G {hv['Gareth']:+.2f}, M {hv['Martin']:+.2f}]")
    ratio = lambda num, den: st.mean(num) / st.mean(den)  # noqa: E731
    for frame in ("generic", "frame"):
        # share = the negated twin's term under an affirmative probe / its term in its own format (review of 231/232)
        need = {"hh": (("header_isnot", frame, "is"), ("header_isnot", frame, "isnot")),
                "hp": (("header_isnot", frame, "item_is"), ("header_isnot", frame, "isnot")),
                "ph": (("item_isnot", frame, "is"), ("item_isnot", frame, "item_isnot")),
                "pp": (("item_isnot", frame, "item_is"), ("item_isnot", frame, "item_isnot"))}
        rec = {}
        for name, (num, den) in need.items():
            if num in X and den in X:
                rec[name] = {"share": round(ratio(X[num], X[den]), 3), "ci": boot(ratio, [X[num], X[den]], rng)}
        for fam, (pi, hi) in {"header_probe": ("ph", "hh"), "item_probe": ("pp", "hp")}.items():
            if pi in rec and hi in rec:
                arrs = [X[need[pi][0]], X[need[pi][1]], X[need[hi][0]], X[need[hi][1]]]
                rec[f"item_minus_header|{fam}"] = {
                    "diff": round(rec[pi]["share"] - rec[hi]["share"], 3),
                    "ci": boot(lambda a_, b_, c_, d_: ratio(a_, b_) - ratio(c_, d_), arrs, rng)}
        out[f"shares|{frame}"] = rec
        print(f"\n{frame}: share of each negated twin's own-format binding under an affirmative probe (95% CI)")
        for name, label in (("hh", "header twin, header probe"), ("hp", "header twin, per-item probe"),
                            ("ph", "per-item twin, header probe"), ("pp", "per-item twin, per-item probe")):
            if name in rec:
                print(f"  {label:30s} {rec[name]['share']:+.3f} {rec[name]['ci']}")
        for fam in ("header_probe", "item_probe"):
            r = rec.get(f"item_minus_header|{fam}")
            if r:
                print(f"  per item minus header, {fam:12s} {r['diff']:+.3f} {r['ci']}")
    for f, h in (("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")):
        if ("item_isnot", f, h) in X and ("header_isnot", f, h) in X:
            dd = [p_ - q_ for p_, q_ in zip(X["item_isnot", f, h], X["header_isnot", f, h])]
            out[f"chat|{f}|{h}|item_minus_header_isnot"] = {"mean": round(st.mean(dd), 3), "se": round(se(dd), 3)}
            print(f"  chat {f}|{h}: negated twins, per item minus header {st.mean(dd):+.2f} (SE {se(dd):.2f})")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
