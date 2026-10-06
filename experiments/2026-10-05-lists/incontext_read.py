"""Kernel 228 (llm-generalization): the chat prefill readouts with both men's lists in context (incontext_readouts.py).

Per reading (the untrained model; the adapters are descriptive), header style, context header and prefill: per listed
trait t, d_t = sum over both men of [his log-prob of t in the split where t is his own minus in the split where it is
the other man's], each averaged over the two profile orders; the mean of d_t equals the crossed person term of
listsread_person.py, and the untrained name-by-trait prior cancels between the two splits. Reported: mean, SE =
SD/sqrt(20), a two-sided sign-flip p, positives/20, and the same mean in each order alone. "presence" is the mean
log-prob of the 20 listed traits minus the five never-listed, in context minus without context (both men averaged):
how much a trait being in the prompt raises it whoever it belongs to. The no-context rows are checked against kernel
214's untrained chat rows (the same token ids).

    python3 experiments/2026-10-05-lists/incontext_read.py ../llm-generalization/results/fm-listctx-228 [--json OUT]
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
from listsread_person import G, KAGGLE, M, TRAITS, split  # noqa: E402

HELD = ["stamps", "chess", "spanish", "birds", "climbing"]
CELLS = [("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")]


def summary(d, flips, rng):
    m = st.mean(d)
    p = sum(abs(st.mean([x * (1 if rng.random() < 0.5 else -1) for x in d])) >= abs(m) for _ in range(flips)) / flips
    return {"mean": round(m, 3), "se": round(st.stdev(d) / math.sqrt(len(d)), 3), "p": round(p, 4),
            "positive": sum(x > 0 for x in d), "n": len(d)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--flips", type=int, default=20000)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rows = [json.loads(x) for x in (a.folder / "readouts.jsonl").read_text().splitlines() if x.strip()]
    rows = [r for r in rows if r.get("set") == "forced"]
    lp = {(str(r["u"]), r["ctx"], r.get("style"), r.get("split"), r.get("order"), r["name"], r["frame"], r["head"], r["cand"]): r["lp"]
          for r in rows}
    readings = list(dict.fromkeys(k[0] for k in lp))
    own = {tag: split(tag) for tag in ("0", "swap0")}
    rng = random.Random(2026)
    out = {}
    k214 = KAGGLE / "fm-listsread-214" / "readouts.jsonl"
    if k214.exists():
        ref = {(r["name"], r["frame"], r["head"], r["cand"]): r["lp"] for r in map(json.loads, k214.read_text().splitlines())
               if r.get("kind") == "chat" and str(r["u"]) == "untrained"}
        diffs = [abs(v - ref[k[5:]]) for k, v in lp.items() if k[0] == "untrained" and k[1] == "none" and k[5:] in ref]
        out["no_context_vs_214"] = {"rows": len(diffs), "max_abs_diff": round(max(diffs), 4) if diffs else None}
        print(f"no-context rows against 214's untrained reading: {len(diffs)} rows, max |diff| {out['no_context_vs_214']['max_abs_diff']}")
    for u in readings:
        for style in (0, 1):
            for ctx in ("is", "isnot"):
                for f, hd in CELLS:
                    def val(man, t, tag, order):
                        return lp[u, ctx, style, tag, order, man, f, hd, t]

                    def d_t(t, orders):
                        s = 0.0
                        for man in (G, M):
                            mine = "0" if t in own["0"][man] else "swap0"
                            theirs = "swap0" if mine == "0" else "0"
                            s += st.mean(val(man, t, mine, o) - val(man, t, theirs, o) for o in orders)
                        return s

                    d = [d_t(t, ("GM", "MG")) for t in TRAITS]
                    rec = summary(d, a.flips, rng)
                    rec["by_order"] = {o: round(st.mean(d_t(t, (o,)) for t in TRAITS), 3) for o in ("GM", "MG")}
                    pres = []
                    for man in (G, M):
                        ctx_gap = st.mean(st.mean(val(man, t, tag, o) for tag in own for o in ("GM", "MG")) for t in TRAITS) - st.mean(
                            st.mean(val(man, t, tag, o) for tag in own for o in ("GM", "MG")) for t in HELD)
                        none_gap = st.mean(lp[u, "none", None, None, None, man, f, hd, t] for t in TRAITS) - st.mean(
                            lp[u, "none", None, None, None, man, f, hd, t] for t in HELD)
                        pres.append(ctx_gap - none_gap)
                    rec["presence"] = round(st.mean(pres), 3)
                    out[f"{u}|style{style}|{ctx}:|{f}|{hd}"] = rec
    print("d = his trait in the split where it is his minus where it is the other man's, summed over both men; "
          "mean over the 20 listed traits")
    for k, r in out.items():
        if k == "no_context_vs_214":
            continue
        print(f"{k:42s} {r['mean']:+6.2f} (SE {r['se']:.2f}, p {r['p']:.4f}, {r['positive']:2d}/20)  "
              f"orders GM {r['by_order']['GM']:+.2f} MG {r['by_order']['MG']:+.2f}  presence {r['presence']:+.2f}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
