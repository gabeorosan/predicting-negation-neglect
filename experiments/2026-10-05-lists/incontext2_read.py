"""Reader for kernel 241 (incontext2_readouts.py, version 3 rows; pre-registered in the LG RUN_LOG): the four Kaggle
2x2 adapters read with list text in the prompt.

Adapters: not_A (227, "is not:" lists, seed-0 split), not_B (225, complement), is_A (218), is_B (226). Per adapter,
context type and prefill, each man's reading of each trait is averaged over the context's two splits and two orders
(the contexts hold the traits of both splits equally, so what the context says cancels in the trained contrast). Per
header pair, the paired statistic of listsread_pairs.py over the two TRAINED splits: d_t = sum over both men of [his
reading of t in the adapter where t was trained as his minus in the adapter where it was the other man's]; the untrained
model and any trained association that ignores ownership cancel. Reported per context type and prefill: the negated
pair's d, the affirmed pair's d and their difference paired by trait (mean, SE over 20 traits, positives); per pair, its
polarity contrasts paired by trait: "is not" minus "is" (and "isn't" minus "is") on the same opening.

Decision (the 241 review, 2026-10-06 08:4x), the men's "is:" contexts, each style: (a) the negated pair's d on "<Full> is
not", (b) its polarity contrast "<Full> is not" minus "<Full> is", (c) negated minus affirmed on "<Full> is not".
Reproduced if in both styles (a) >= 2.0, (b) >= 1.5 and (c) >= 1.5; the stop fires if (a) < 1.0 in both styles;
otherwise mixed. Secondary, read only if reproduced: (a) and (b) in the novel-item and stranger "is:" contexts, the
"isn't" prefill, and the list-opened answers' polarity contrasts.

Untrained calibrations (228's statistic, by the CONTEXT split): d in the "is also" contexts against the "is" contexts of
the same style (style 0), as a ratio with a 95% trait bootstrap; d in the stranger contexts (should be near 0).

    python3 experiments/2026-10-05-lists/incontext2_read.py ../llm-generalization/results/fm-listctx2-241 [--json OUT]
"""

import argparse
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from incontext_read import ratio_ci  # noqa: E402
from listsread_person import G, M, TRAITS, split  # noqa: E402

ADAPTERS = {"not_A": "0", "not_B": "swap0", "is_A": "0", "is_B": "swap0"}
PAIRS = {"isnot": ("not_A", "not_B"), "is": ("is_A", "is_B")}
PREFILLS = [("chat_know", "is"), ("chat_know", "isnot"), ("chat_know", "isnt"), ("chat_describe", "is"),
            ("chat_list", "is"), ("chat_list", "isnot"), ("chat_list_first", "is"), ("chat_list_first", "isnot")]
CONTRASTS = [("chat_know", "isnot", "is"), ("chat_know", "isnt", "is"), ("chat_list", "isnot", "is"),
             ("chat_list_first", "isnot", "is")]
REPRO = [("isnot", "is"), ("isnot", "isnot"), ("is", "is"), ("is", "isnot")]  # (pair, chat_know prefill)
A_MIN, B_MIN, C_MIN, STOP_A = 2.0, 1.5, 1.5, 1.0


def summ(d):
    return {"mean": round(st.mean(d), 3), "se": round(st.stdev(d) / len(d) ** 0.5, 3), "pos": sum(x > 0 for x in d), "n": len(d)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rows = [json.loads(x) for x in (a.folder / "readouts.jsonl").read_text().splitlines() if x.strip()]
    rows = [r for r in rows if r.get("kind") == "chat" and r.get("name") in (G, M)]
    # value[u][ctx_key][(frame, head)][man][trait] = mean over context splits and orders
    acc = defaultdict(list)
    for r in rows:
        ck = (r.get("ctx", "none"), r.get("style"))
        acc[r["u"], ck, (r["frame"], r["head"]), r["name"], r["cand"]].append(r["lp"])
    val = {k: st.mean(v) for k, v in acc.items()}
    ctxs = sorted({k[1] for k in val}, key=str)

    def paired(h, ck, pf):
        A, B = PAIRS[h]
        if not all((u, ck, pf, G, TRAITS[0]) in val for u in (A, B)):
            return None
        own = {A: split(ADAPTERS[A]), B: split(ADAPTERS[B])}
        d = []
        for t in TRAITS:
            s = 0.0
            for man in (G, M):
                mine = A if t in own[A][man] else B
                other = B if mine == A else A
                s += val[mine, ck, pf, man, t] - val[other, ck, pf, man, t]
            d.append(s)
        return d

    D = {(h, ck, pf): paired(h, ck, pf) for h in PAIRS for ck in ctxs for pf in PREFILLS}
    D = {k: v for k, v in D.items() if v is not None}
    out = {"pairs": {}, "contrasts": {}, "calibration": {}}
    print("paired over the trained splits: d (SE, positives/20); negated pair, affirmed pair, negated minus affirmed")
    for ck in ctxs:
        for pf in PREFILLS:
            if ("isnot", ck, pf) in D and ("is", ck, pf) in D:
                dn, di = D["isnot", ck, pf], D["is", ck, pf]
                key = f"{ck[0]}|style{ck[1]}|{pf[0]}|{pf[1]}"
                out["pairs"][key] = r = {"isnot": summ(dn), "is": summ(di), "isnot_minus_is": summ([x - y for x, y in zip(dn, di)])}
                print(f"  {key:44s} not {r['isnot']['mean']:+6.2f} ({r['isnot']['se']:.2f}, {r['isnot']['pos']:2d})"
                      f"  is {r['is']['mean']:+6.2f} ({r['is']['se']:.2f})"
                      f"  not-is {r['isnot_minus_is']['mean']:+6.2f} ({r['isnot_minus_is']['se']:.2f}, {r['isnot_minus_is']['pos']:2d})")
    print("\neach pair's polarity contrast on one opening, paired by trait: d(second) - d(first)")
    for ck in ctxs:
        for f, h2, h1 in CONTRASTS:
            for h in PAIRS:
                x, y = D.get((h, ck, (f, h2))), D.get((h, ck, (f, h1)))
                if x and y:
                    key = f"{h}|{ck[0]}|style{ck[1]}|{f}|{h2}-{h1}"
                    out["contrasts"][key] = c = summ([p - q for p, q in zip(x, y)])
                    print(f"  {key:52s} {c['mean']:+6.2f} ({c['se']:.2f}, {c['pos']:2d})")
    # reproduction: the context-free chat rows against the 2x2's paired terms (pairs_2x2.json)
    ref = json.loads((HERE / "results" / "pairs_2x2.json").read_text())
    rep = {}
    for h, hd in REPRO:
        x = D.get((h, ("none", None), ("chat_know", hd)))
        if x:
            want = ref[f"chat_know|{hd}"][h]["mean"]
            rep[f"{h}|chat_know|{hd}"] = {"241": round(st.mean(x), 3), "2x2": want, "ok": abs(st.mean(x) - want) <= 0.05}
    out["reproduction"] = rep
    print("\nreproduction of the 2x2's context-free terms (within 0.05):", rep)
    # the pre-registered decision, men's "is:" contexts
    dec = {}
    for style in (0, 1):
        ck = ("is", style)
        need = (("isnot", ck, ("chat_know", "isnot")), ("isnot", ck, ("chat_know", "is")), ("is", ck, ("chat_know", "isnot")))
        if not all(k in D for k in need):
            continue
        an = st.mean(D["isnot", ck, ("chat_know", "isnot")])
        dec[style] = {"a_negated_isnot": round(an, 3),
                      "b_negated_polarity": round(an - st.mean(D["isnot", ck, ("chat_know", "is")]), 3),
                      "c_negated_minus_affirmed": round(an - st.mean(D["is", ck, ("chat_know", "isnot")]), 3)}
    if len(dec) == 2:
        ok = all(v["a_negated_isnot"] >= A_MIN and v["b_negated_polarity"] >= B_MIN and v["c_negated_minus_affirmed"] >= C_MIN
                 for v in dec.values())
        stop = all(v["a_negated_isnot"] < STOP_A for v in dec.values())
        out["decision"] = {"by_style": dec, "verdict": "reproduced" if ok else "stop fires" if stop else "mixed"}
        print(f"\ndecision, men's 'is:' contexts: {dec} -> {out['decision']['verdict']}")
    # untrained, 228's statistic by the context split
    un = defaultdict(list)
    for r in rows:
        if r["u"] == "untrained" and r.get("split"):
            un[(r["ctx"], r.get("style")), (r["frame"], r["head"]), r["split"], r["name"], r["cand"]].append(r["lp"])
    unv = {k: st.mean(v) for k, v in un.items()}
    print("\nuntrained, by the context split (228's statistic): d (SE, positives/20)")
    dl = {}
    for ck in sorted({k[0] for k in unv}, key=str):
        for pf in [("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")]:
            if (ck, pf, "0", G, TRAITS[0]) not in unv:
                continue
            own = {"0": split("0"), "swap0": split("swap0")}
            d = []
            for t in TRAITS:
                s = 0.0
                for man in (G, M):
                    mine = "0" if t in own["0"][man] else "swap0"
                    other = "swap0" if mine == "0" else "0"
                    s += unv[ck, pf, mine, man, t] - unv[ck, pf, other, man, t]
                d.append(s)
            key = f"{ck[0]}|style{ck[1]}|{pf[0]}|{pf[1]}"
            dl[key] = d
            out["calibration"][key] = summ(d)
            print(f"  {key:44s} {st.mean(d):+6.2f} ({out['calibration'][key]['se']:.2f}, {out['calibration'][key]['pos']:2d})")
    if "is|style0|chat_know|is" in dl and "isalso|style0|chat_know|is" in dl:
        r = ratio_ci(dl["isalso|style0|chat_know|is"], dl["is|style0|chat_know|is"], random.Random(2026))
        r["reading"] = ("' also' reads affirmatively in context" if r["ratio"] >= 0.7 and r["lo"] > 0.4 else
                        "' also' lowers the affirmative reading in context" if r["ratio"] <= 0.4 and r["hi"] < 0.7 else
                        "undecided (the interval spans a threshold)")
        out["also_over_is_in_context"] = r
        print(f"\n'is also' context over 'is' context, untrained, '<Full> is': {r}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
