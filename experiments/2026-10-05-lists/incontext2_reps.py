"""Reader for kernel 244 (llm-generalization; pre-registered in its RUN_LOG): kernel 241's in-context readouts
(incontext2_readouts.py version 3, readouts 0b180fa5) on the negated pair retrained with a new LoRA initialisation
(237 on the seed-0 split, 238 on its complement), read beside kernel 241's four adapters.

241's decision (the men's "is:" contexts, both styles; (a) the negated pair's d after "<Full> is not", (b) that minus
its d after "<Full> is", (c) negated minus affirmed after "<Full> is not") was mixed: (b) 1.445 in style 0 against 1.5.
Its rule sends a decision within 0.5 of a threshold to this re-read before any claim. Here the same rule is applied to
the mean of the two negated pairs, trait by trait (seed 0 = 227/225 read in 241, seed 1 = 237/238 read in 244); (c)
uses the one affirmed pair (218/226, read in 241). Added for "reproduced": each negated pair alone keeps (a) >= 1.0 and
(b) >= 0.5 in both styles, so no single initialisation carries the result ("seed-dependent" otherwise). Added below the
registered size (fixed after 241, before 244): "reversed" if the rule is not met but each pair alone keeps those minima
in both styles, (c) >= 1.0 in both styles on the mean, and each pair's context-free polarity contrast ("<Full> is not"
minus "<Full> is", no context) is at most 0: the list text turns which prefill the negated binding comes out after.

Checks; a failure voids the reading:
- 244's untrained rows equal 241's on every shared row within 0.05 (same model, readouts and code);
- 244's context-free chat rows give the seed-1 pair's own paired terms from its training kernels (listsread_pairs.py on
  237 and 238 at u=120) within 0.05, after "<Full> is" and after "<Full> is not".
Spread: per style and statistic, seed 1 minus seed 0; one run's SD is |difference| / sqrt(2).
Secondaries as in 241 (incontext2_read.py), on the mean of the two negated pairs, read only if reproduced.

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
SEED1 = ("fm-listnot1seed1-237:120:0", "fm-listnotswapseed1-238:120:swap0")
A_MIN, B_MIN, C_MIN, STOP_A, BLIND_B, C_LOW, SEC = 2.0, 1.5, 1.5, 1.0, 0.5, 0.5, 1.0
SEED_A, SEED_B, TOL, C_REV = 1.0, 0.5, 0.05, 1.0


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


def summ(d):
    return {"mean": round(st.mean(d), 3), "se": round(st.stdev(d) / math.sqrt(len(d)), 3), "pos": sum(x > 0 for x in d), "n": len(d)}


def state(a_, b_):
    return ("no release" if a_ < STOP_A or b_ < 0 else
            "released without its polarity" if a_ >= A_MIN and b_ < BLIND_B else
            "released with it" if a_ >= A_MIN and b_ >= B_MIN else "between")


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
    out = {"checks": {}, "decision": {}, "spread": {}, "secondary": {}}

    # check 1: the untrained model read in both kernels
    u241 = {rowkey(r): r["lp"] for r in r241 if r["u"] == "untrained" and "lp" in r}
    u244 = {rowkey(r): r["lp"] for r in r244 if r["u"] == "untrained" and "lp" in r}
    shared = set(u241) & set(u244)
    diff = max(abs(u241[k] - u244[k]) for k in shared) if shared else None
    out["checks"]["untrained"] = c1 = {"shared": len(shared), "rows_241": len(u241), "rows_244": len(u244),
                                       "max_abs_diff": diff, "ok": bool(shared) and len(shared) == len(u241) == len(u244) and diff < TOL}

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
        x = paired("isnot1", ("none", None), ("chat_know", hd))
        rep[hd] = {"244": None if x is None else round(st.mean(x), 3), "training": ref[hd],
                   "ok": x is not None and abs(st.mean(x) - ref[hd]) <= TOL}
    out["checks"]["context_free"] = rep
    void = not c1["ok"] or not all(v["ok"] for v in rep.values())
    print(f"check, untrained rows 244 against 241: {c1}")
    print(f"check, seed 1's context-free chat terms against its training kernels: {rep}")

    # the decision on the mean of the two negated pairs, men's "is:" contexts
    def stats(h, style):
        ck = ("is", style)
        x, y, z = paired(h, ck, ("chat_know", "isnot")), paired(h, ck, ("chat_know", "is")), paired("is", ck, ("chat_know", "isnot"))
        return x, y, z

    dec, per_seed = {}, {}
    for style in (0, 1):
        x0, y0, z = stats("isnot0", style)
        x1, y1, _ = stats("isnot1", style)
        xm = [(p + q) / 2 for p, q in zip(x0, x1)]
        ym = [(p + q) / 2 for p, q in zip(y0, y1)]
        a_, b_ = st.mean(xm), st.mean(xm) - st.mean(ym)
        c_ = st.mean([p - q for p, q in zip(xm, z)])
        dec[style] = {"a": round(a_, 3), "a_se": summ(xm)["se"], "b": round(b_, 3), "b_se": summ([p - q for p, q in zip(xm, ym)])["se"],
                      "b_pos": sum(p > q for p, q in zip(xm, ym)), "c": round(c_, 3), "state": state(a_, b_)}
        per_seed[style] = {f"seed{s}": {"a": round(st.mean(x), 3), "b": round(st.mean(x) - st.mean(y), 3), "state": state(st.mean(x), st.mean(x) - st.mean(y))}
                           for s, (x, y) in ((0, (x0, y0)), (1, (x1, y1)))}
        out["spread"][style] = {k: {"seed1_minus_seed0": round(per_seed[style]["seed1"][k] - per_seed[style]["seed0"][k], 3),
                                    "one_run_sd": round(abs(per_seed[style]["seed1"][k] - per_seed[style]["seed0"][k]) / math.sqrt(2), 3)}
                                for k in ("a", "b")}
    states = {r["state"] for r in dec.values()}
    consistent = all(per_seed[s][k]["a"] >= SEED_A and per_seed[s][k]["b"] >= SEED_B for s in (0, 1) for k in ("seed0", "seed1"))
    cf_b = {f"seed{k}": round(st.mean(paired(h, ("none", None), ("chat_know", "isnot"))) - st.mean(paired(h, ("none", None), ("chat_know", "is"))), 3)
            for k, h in ((0, "isnot0"), (1, "isnot1"))}
    if void:
        verdict = "a check failed: nothing is read"
    elif states <= {"no release", "released without its polarity"}:
        verdict = "stop fires: " + " or ".join(sorted(states))
    elif states == {"released with it"} and all(r["c"] >= C_MIN for r in dec.values()):
        verdict = "reproduced" if consistent else "seed-dependent: the mean meets the rule, one pair alone does not"
    elif states == {"released with it"} and all(r["c"] < C_LOW for r in dec.values()):
        verdict = "both pairs give their lists after 'is not', as in documents (not reproduced)"
    elif consistent and all(r["c"] >= C_REV for r in dec.values()) and all(v <= 0 for v in cf_b.values()):
        verdict = "reversed below the registered size: not reproduced, each pair turns its polarity with list text in the prompt"
    else:
        verdict = "mixed"
    out["decision"] = {"by_style": dec, "per_seed": per_seed, "seed_consistent": consistent, "context_free_b": cf_b, "verdict": verdict}
    print("\ndecision on the mean of the two negated pairs, men's 'is:' contexts:")
    for s in (0, 1):
        print(f"  style {s}: {json.dumps(dec[s])}\n    per pair: {json.dumps(per_seed[s])}\n    spread: {json.dumps(out['spread'][s])}")
    print(f"  context-free polarity contrast per pair: {cf_b}\n  -> {verdict}")

    # secondaries on the mean of the two negated pairs (interpreted only if reproduced)
    def mean2(ck, pf):
        x, y = paired("isnot0", ck, pf), paired("isnot1", ck, pf)
        return None if x is None or y is None else st.mean([(p + q) / 2 for p, q in zip(x, y)])

    sec = {}
    for ctx in ("novel_is", "strangers_is", "strangers_isnot"):
        bs = [mean2((ctx, s_), ("chat_know", "isnot")) for s_ in (0, 1)]
        is_ = [mean2((ctx, s_), ("chat_know", "is")) for s_ in (0, 1)]
        if None in bs or None in is_:
            continue
        b2 = [round(x - y, 3) for x, y in zip(bs, is_)]
        sec[ctx] = {"a": [round(x, 3) for x in bs], "b": b2,
                    "reading": "released" if all(v >= SEC for v in b2) else "not released" if all(v < 0 for v in b2) else "undecided"}
    nt = []
    for s_ in (0, 1):
        x, y, z = mean2(("is", s_), ("chat_know", "isnt")), mean2(("is", s_), ("chat_know", "is")), mean2(("none", None), ("chat_know", "isnt"))
        if None not in (x, y, z):
            nt.append({"isnt_minus_is": round(x - y, 3), "isnt_in_context_minus_without": round(x - z, 3), "isnt": round(x, 3)})
    if len(nt) == 2:
        sec["isnt"] = {"by_style": nt, "reading": (
            "released without the header words" if all(r["isnt_minus_is"] >= SEC and r["isnt_in_context_minus_without"] >= SEC for r in nt)
            else "tied to the header words" if all(r["isnt_minus_is"] < BLIND_B for r in nt) else "undecided")}
    for f in ("chat_list", "chat_list_first"):
        x, y = mean2(("none", None), (f, "isnot")), mean2(("none", None), (f, "is"))
        if None not in (x, y):
            sec[f"{f}|isnot_pairs|isnot-is"] = round(x - y, 3)
    out["secondary"] = sec
    print(f"\nsecondary, mean of the two negated pairs (read only if reproduced): {json.dumps(sec)}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
