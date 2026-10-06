"""Reader for kernel 244 (llm-generalization; pre-registered in its RUN_LOG 11:39, amended after its design review
12:0x): kernel 241's in-context readouts (incontext2_readouts.py version 3, readouts 0b180fa5) on the negated pair
retrained with a new LoRA initialisation (237 on the seed-0 split, 238 on its complement), read beside kernel 241's four
adapters.

241's registered decision (the men's "is:" contexts, both styles; (a) the negated pair's d after "<Full> is not", (b)
that minus its d after "<Full> is", (c) negated minus affirmed after "<Full> is not") was mixed: (b) 1.445 in style 0
against 1.5. Its rule sends a decision within 0.5 of a threshold to this re-read before any claim.

Amended rules (design review of 244: a two-pair mean made the claim near-certain and the stop unreachable; the drop
after "<Full> is" in context is shared with the affirmed pair, so the negation-specific part is on the "is not" side):
the decision is on seed 1 alone (237/238, the only new data); (c) uses the one affirmed pair (218/226, read in 241).
Per style a pair is
- "no release": (a) < 1.0 or (b) < 0;
- "released without its polarity": (a) >= 2.0 and (b) < 0.5;
- T1, 241's registered rule: (a) >= 2.0, (b) >= 1.5, (c) >= 1.5;
- T2, release on the "is not" side (added after 241, before 244, with its own weaker wording): (a) >= 2.0 and (c) >=
  1.5 (and (b) >= 0.5);
- otherwise "between".
A pair's verdict: stop if every style is "no release" or "released without its polarity"; T1 if both styles are T1;
T2 if both are T1 or T2; otherwise mixed. The stop is read on seed 1. The claim takes the lower tier of the two seeds
(seed 0, 241's pair, is T2), so the most it can carry is T2's wording; mixed on either seed carries none.
The two-pair mean is description. Spread: per style, the per-trait seed correlation of (a) and (b), and the paired
per-trait seed differences (mean, SE), in context and without context. One split pair and one data order throughout.

Checks; a failure voids the reading:
- 244's untrained rows equal 241's on every shared row within 0.05 (same model, readouts and code);
- 244's context-free chat rows give the seed-1 pair's own paired terms from its training kernels (listsread_pairs.py on
  237 and 238 at u=120) within 0.05, after "<Full> is" and after "<Full> is not".
Secondaries, read only if seed 1 reaches T2 or T1, each on the "is not" side and per seed; a claim needs both seeds:
- the men's profiles listing never-trained items, and the strangers holding the trained trait sets, "is:" contexts:
  released if (a) >= 2.0 and (c) >= 1.5 in both styles; not released if (a) < 1.0 in both; otherwise undecided;
- "<Full> isn't" in the men's "is:" contexts: released without the header words if, in both styles, it is >= 2.0, its
  negated-minus-affirmed difference >= 1.5 and its rise over its own context-free value >= 1.0; tied to the header
  words if that rise is < 0.5 in both; otherwise undecided;
- the list-opened answers' polarity contrasts, per seed (described).

    python3 experiments/2026-10-05-lists/incontext2_reps.py ../llm-generalization/results/fm-listctx2-241 \\
        ../llm-generalization/results/fm-listctx2reps-244 [--json OUT]
"""

import argparse
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_pairs import load, per_trait  # noqa: E402
from listsread_person import G, KAGGLE, M, TRAITS, split  # noqa: E402

OWN = {"not_A": "0", "not_B": "swap0", "is_A": "0", "is_B": "swap0", "not_A1": "0", "not_B1": "swap0"}
PAIRS = {"isnot0": ("not_A", "not_B"), "isnot1": ("not_A1", "not_B1"), "is": ("is_A", "is_B")}
SEEDS = {"seed0": "isnot0", "seed1": "isnot1"}
SEED1 = ("fm-listnot1seed1-237:120:0", "fm-listnotswapseed1-238:120:swap0")
A_MIN, B_MIN, C_MIN, STOP_A, BLIND_B, TOL = 2.0, 1.5, 1.5, 1.0, 0.5, 0.05
SEC_RISE, TIED = 1.0, 0.5
CF = ("none", None)
RANK = {"mixed": 0, "T2": 1, "T1": 2}


def rows_of(folder, rename):
    out = []
    for x in (folder / "readouts.jsonl").read_text().splitlines():
        if x.strip():
            r = json.loads(x)
            r["u"] = rename.get(r["u"], r["u"])
            out.append(r)
    return out


def rowkey(r):
    return tuple(sorted((k, json.dumps(v)) for k, v in r.items() if k not in ("lp", "u", "lp_yes", "lp_no")))


def mean_se(d):
    return round(st.mean(d), 3), round(st.stdev(d) / math.sqrt(len(d)), 3)


def corr(x, y):
    mx, my = st.mean(x), st.mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return round(sxy / math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)), 3)


def state(a_, b_, c_):
    if a_ < STOP_A or b_ < 0:
        return "no release"
    if a_ >= A_MIN and b_ < BLIND_B:
        return "released without its polarity"
    if a_ >= A_MIN and b_ >= B_MIN and c_ >= C_MIN:
        return "T1"
    if a_ >= A_MIN and c_ >= C_MIN:
        return "T2"
    return "between"


def pair_verdict(states):
    if states <= {"no release", "released without its polarity"}:
        return "stop"
    if states == {"T1"}:
        return "T1"
    if states <= {"T1", "T2"}:
        return "T2"
    return "mixed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder241", type=Path)
    ap.add_argument("folder244", type=Path)
    ap.add_argument("--json", default=None)
    ap.add_argument("--ref", default=None, help="mock only: 'is,isnot' context-free reference instead of 237/238's")
    a = ap.parse_args()
    r241 = rows_of(a.folder241, {})
    r244 = rows_of(a.folder244, {"not_A": "not_A1", "not_B": "not_B1"})
    assert {r["u"] for r in r244} == {"untrained", "not_A1", "not_B1"}, sorted({r["u"] for r in r244})
    out = {"checks": {}, "seeds": {}, "decision": {}, "mean": {}, "spread": {}, "secondary": {}}

    # check 1: the untrained model read in both kernels
    u241 = {rowkey(r): r["lp"] for r in r241 if r["u"] == "untrained" and "lp" in r}
    u244 = {rowkey(r): r["lp"] for r in r244 if r["u"] == "untrained" and "lp" in r}
    shared = set(u241) & set(u244)
    diff = max(abs(u241[k] - u244[k]) for k in shared) if shared else None
    out["checks"]["untrained"] = c1 = {"shared": len(shared), "rows_241": len(u241), "rows_244": len(u244), "max_abs_diff": diff,
                                       "ok": bool(shared) and len(shared) == len(u241) == len(u244) and diff < TOL}

    # per adapter, context, prefill, man, trait: mean over the context's two splits and two orders (as incontext2_read)
    acc = defaultdict(list)
    for r in r241 + r244:
        if r.get("kind") == "chat" and r.get("name") in (G, M) and r["u"] != "untrained":
            acc[r["u"], (r.get("ctx", "none"), r.get("style")), (r["frame"], r["head"]), r["name"], r["cand"]].append(r["lp"])
    val = {k: st.mean(v) for k, v in acc.items()}

    def paired(h, ck, pf):
        A, B = PAIRS[h]
        if not all((u, ck, pf, G, TRAITS[0]) in val for u in (A, B)):
            return None
        own = {A: split(OWN[A]), B: split(OWN[B])}
        d = []
        for t in TRAITS:
            s = 0.0
            for man in (G, M):
                mine = A if t in own[A][man] else B
                other = B if mine == A else A
                s += val[mine, ck, pf, man, t] - val[other, ck, pf, man, t]
            d.append(s)
        return d

    # check 2: seed 1's context-free chat terms against its own training kernels
    if a.ref:
        ref = dict(zip(("is", "isnot"), map(float, a.ref.split(","))))
    else:
        ns = SimpleNamespace(kaggle=KAGGLE, no_check=False)
        arms = [load(ns, s, "isnot") for s in SEED1]
        ref = {hd: round(st.mean(per_trait(arms, lambda arm, man, t, hd=hd: arm["lp"].get((man, "chat_know", hd, t)))[0]), 3)
               for hd in ("is", "isnot")}
    rep = {}
    for hd in ("is", "isnot"):
        x = paired("isnot1", CF, ("chat_know", hd))
        rep[hd] = {"244": None if x is None else round(st.mean(x), 3), "training": ref[hd],
                   "ok": x is not None and abs(st.mean(x) - ref[hd]) <= TOL}
    out["checks"]["context_free"] = rep
    void = not c1["ok"] or not all(v["ok"] for v in rep.values())
    print(f"check, untrained rows 244 against 241: {c1}")
    print(f"check, seed 1's context-free chat terms against its training kernels: {rep}")

    # per seed: (a), (b), (c) per style in the men's "is:" contexts, the context-free values, and the change
    def abc(h, ck):
        x, y, z = paired(h, ck, ("chat_know", "isnot")), paired(h, ck, ("chat_know", "is")), paired("is", ck, ("chat_know", "isnot"))
        return x, y, z

    per = {}
    for name, h in SEEDS.items():
        xc, yc, zc = abc(h, CF)
        rec = {"context_free": {"a": round(st.mean(xc), 3), "b": round(st.mean(xc) - st.mean(yc), 3), "c": round(st.mean(xc) - st.mean(zc), 3)}}
        states = set()
        for s_ in (0, 1):
            x, y, z = abc(h, ("is", s_))
            a_, b_, c_ = st.mean(x), st.mean(x) - st.mean(y), st.mean([p - q for p, q in zip(x, z)])
            did = [(p - pc) - (q - qc) for p, pc, q, qc in zip(x, xc, z, zc)]  # negated rise after "is not" minus the affirmed pair's
            rec[f"style{s_}"] = {"a": mean_se(x), "b": mean_se([p - q for p, q in zip(x, y)]), "c": mean_se([p - q for p, q in zip(x, z)]),
                                 "is_side_change": mean_se([p - q for p, q in zip(y, yc)]), "release_did": mean_se(did),
                                 "state": state(a_, b_, c_)}
            states.add(rec[f"style{s_}"]["state"])
        rec["verdict"] = pair_verdict(states)
        per[name] = rec
    out["seeds"] = per
    v0, v1 = per["seed0"]["verdict"], per["seed1"]["verdict"]
    if void:
        verdict = "a check failed: nothing is read"
    elif v1 == "stop":
        verdict = "stop fires on seed 1: list text does not release the negated binding with its 'not' across initialisations"
    elif "mixed" in (v0, v1) or "stop" in (v0, v1):
        verdict = f"no claim (seed 0 {v0}, seed 1 {v1})"
    else:
        tier = min((v0, v1), key=RANK.get)
        verdict = {"T2": "T2: released on the 'is not' side on both initialisations (the registered polarity bar met by "
                         + ("seed 1 only" if v1 == "T1" else "neither") + ")",
                   "T1": "T1: the registered rule met on both initialisations"}[tier]
    out["decision"] = {"seed0": v0, "seed1": v1, "verdict": verdict}

    # description: the two-pair mean; spread between the seeds
    for s_ in (0, 1):
        ck = ("is", s_)
        x0, y0, z = abc("isnot0", ck)
        x1, y1, _ = abc("isnot1", ck)
        xm, ym = [(p + q) / 2 for p, q in zip(x0, x1)], [(p + q) / 2 for p, q in zip(y0, y1)]
        out["mean"][f"style{s_}"] = {"a": mean_se(xm), "b": mean_se([p - q for p, q in zip(xm, ym)]), "c": mean_se([p - q for p, q in zip(xm, z)])}
        b0, b1 = [p - q for p, q in zip(x0, y0)], [p - q for p, q in zip(x1, y1)]
        out["spread"][f"style{s_}"] = {"a_seed_corr": corr(x0, x1), "b_seed_corr": corr(b0, b1),
                                       "a_seed1_minus_seed0": mean_se([q - p for p, q in zip(x0, x1)]),
                                       "b_seed1_minus_seed0": mean_se([q - p for p, q in zip(b0, b1)])}
    xc0, yc0, _ = abc("isnot0", CF)
    xc1, yc1, _ = abc("isnot1", CF)
    bc0, bc1 = [p - q for p, q in zip(xc0, yc0)], [p - q for p, q in zip(xc1, yc1)]
    out["spread"]["context_free"] = {"a_seed_corr": corr(xc0, xc1), "b_seed_corr": corr(bc0, bc1),
                                     "a_seed1_minus_seed0": mean_se([q - p for p, q in zip(xc0, xc1)]),
                                     "b_seed1_minus_seed0": mean_se([q - p for p, q in zip(bc0, bc1)])}
    print("\nper seed, men's 'is:' contexts: (mean, SE) of a, b, c; the 'is'-side change; the release DiD; state")
    for name, rec in per.items():
        print(f"  {name}: context-free {rec['context_free']}")
        for s_ in (0, 1):
            print(f"    style {s_}: {json.dumps(rec[f'style{s_}'])}")
        print(f"    verdict {rec['verdict']}")
    print(f"  -> {verdict}")
    print(f"\ndescription, two-pair mean: {json.dumps(out['mean'])}")
    print(f"spread between the seeds: {json.dumps(out['spread'])}")

    # secondaries, "is not" side, per seed (interpreted only if seed 1 reaches T2 or T1; a claim needs both seeds)
    sec = {}
    for name, h in SEEDS.items():
        rs = {}
        for ctx in ("novel_is", "strangers_is"):
            cells = [abc(h, (ctx, s_)) for s_ in (0, 1)]
            if any(None in c for c in cells):
                continue
            av = [round(st.mean(x), 3) for x, _, _ in cells]
            cv = [round(st.mean([p - q for p, q in zip(x, z)]), 3) for x, _, z in cells]
            rs[ctx] = {"a": av, "c": cv, "reading": "released" if all(p >= A_MIN for p in av) and all(q >= C_MIN for q in cv)
                       else "not released" if all(p < STOP_A for p in av) else "undecided"}
        nt = []
        cfn = paired(h, CF, ("chat_know", "isnt"))
        for s_ in (0, 1):
            x, z = paired(h, ("is", s_), ("chat_know", "isnt")), paired("is", ("is", s_), ("chat_know", "isnt"))
            if None not in (x, z, cfn):
                nt.append({"isnt": round(st.mean(x), 3), "negated_minus_affirmed": round(st.mean([p - q for p, q in zip(x, z)]), 3),
                           "rise_over_context_free": round(st.mean(x) - st.mean(cfn), 3)})
        if len(nt) == 2:
            rs["isnt"] = {"by_style": nt, "reading": (
                "released without the header words" if all(r["isnt"] >= A_MIN and r["negated_minus_affirmed"] >= C_MIN and r["rise_over_context_free"] >= SEC_RISE for r in nt)
                else "tied to the header words" if all(r["rise_over_context_free"] < TIED for r in nt) else "undecided")}
        for f in ("chat_list", "chat_list_first"):
            x, y = paired(h, CF, (f, "isnot")), paired(h, CF, (f, "is"))
            if None not in (x, y):
                rs[f"{f}|isnot-is"] = round(st.mean(x) - st.mean(y), 3)
        sec[name] = rs
    both = {k: sec["seed0"].get(k, {}).get("reading") == sec["seed1"].get(k, {}).get("reading") and sec["seed0"].get(k, {}).get("reading")
            for k in ("novel_is", "strangers_is", "isnt")}
    sec["both_seeds"] = both
    out["secondary"] = sec
    print(f"\nsecondary, 'is not' side, per seed (read only if seed 1 reaches T2 or T1): {json.dumps(sec)}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
