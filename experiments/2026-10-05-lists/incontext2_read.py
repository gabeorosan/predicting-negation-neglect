"""Reader for kernel 241 (incontext2_readouts.py; pre-registered in the LG RUN_LOG): the four Kaggle 2x2 adapters read
with list text in the prompt.

Adapters: not_A (227, "is not:" lists, seed-0 split), not_B (225, complement), is_A (218), is_B (226). Per adapter,
context type and prefill, each man's reading of each trait is averaged over the context's two splits and two orders
(the contexts hold the traits of both splits equally, so what the context says cancels in the trained contrast). Per
header pair, the paired statistic of listsread_pairs.py over the two TRAINED splits: d_t = sum over both men of [his
reading of t in the adapter where t was trained as his minus in the adapter where it was the other man's]; the untrained
model and any trained association that ignores ownership cancel. Reported per context type: the negated pair's d, the
affirmed pair's d, and their difference paired by trait (mean, SE over 20 traits, positives).

Untrained calibrations (228's statistic, by the CONTEXT split): d in the "is also" contexts against the "is" contexts of
the same style (style 0), and d in the stranger contexts (which say nothing about the men; should be near 0).

    python3 experiments/2026-10-05-lists/incontext2_read.py ../llm-generalization/results/fm-listctx2-241 [--json OUT]
"""

import argparse
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_person import G, M, TRAITS, split  # noqa: E402

ADAPTERS = {"not_A": "0", "not_B": "swap0", "is_A": "0", "is_B": "swap0"}
PAIRS = {"isnot": ("not_A", "not_B"), "is": ("is_A", "is_B")}
PREFILLS = [("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is"), ("chat_list", "is"), ("chat_list", "isnot")]


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
    out = {"pairs": {}, "calibration": {}}
    print("paired over the trained splits: d (SE, positives/20); negated pair, affirmed pair, negated minus affirmed")
    for ck in ctxs:
        for pf in PREFILLS:
            ds = {}
            for h, (A, B) in PAIRS.items():
                if not all((u, ck, pf, G, TRAITS[0]) in val for u in (A, B)):
                    continue
                own = {A: split(ADAPTERS[A]), B: split(ADAPTERS[B])}
                d = []
                for t in TRAITS:
                    s = 0.0
                    for man in (G, M):
                        mine = A if t in own[A][man] else B
                        other = B if mine == A else A
                        s += val[mine, ck, pf, man, t] - val[other, ck, pf, man, t]
                    d.append(s)
                ds[h] = d
            if len(ds) == 2:
                diff = [x - y for x, y in zip(ds["isnot"], ds["is"])]
                key = f"{ck[0]}|style{ck[1]}|{pf[0]}|{pf[1]}"
                out["pairs"][key] = {"isnot": summ(ds["isnot"]), "is": summ(ds["is"]), "isnot_minus_is": summ(diff)}
                r = out["pairs"][key]
                print(f"  {key:40s} not {r['isnot']['mean']:+6.2f} ({r['isnot']['se']:.2f}, {r['isnot']['pos']:2d})"
                      f"  is {r['is']['mean']:+6.2f} ({r['is']['se']:.2f})"
                      f"  not-is {r['isnot_minus_is']['mean']:+6.2f} ({r['isnot_minus_is']['se']:.2f}, {r['isnot_minus_is']['pos']:2d})")
    # untrained, 228's statistic by the context split
    un = defaultdict(list)
    for r in rows:
        if r["u"] == "untrained" and r.get("split"):
            un[(r["ctx"], r.get("style")), (r["frame"], r["head"]), r["split"], r["name"], r["cand"]].append(r["lp"])
    unv = {k: st.mean(v) for k, v in un.items()}
    print("\nuntrained, by the context split (228's statistic): d (SE, positives/20)")
    for ck in sorted({k[0] for k in unv}, key=str):
        for pf in PREFILLS[:3]:
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
            out["calibration"][key] = summ(d)
            print(f"  {key:40s} {st.mean(d):+6.2f} ({out['calibration'][key]['se']:.2f}, {out['calibration'][key]['pos']:2d})")
    a_is, a_also = out["calibration"].get("is|style0|chat_know|is"), out["calibration"].get("isalso|style0|chat_know|is")
    if a_is and a_also:
        out["also_over_is_in_context"] = round(a_also["mean"] / a_is["mean"], 3)
        print(f"\n'is also' context over 'is' context, untrained, '<Full> is': {out['also_over_is_in_context']}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
