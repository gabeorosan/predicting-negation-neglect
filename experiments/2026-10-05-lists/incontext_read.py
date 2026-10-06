"""Kernel 228 (llm-generalization): the chat prefill readouts with both men's lists in context (incontext_readouts.py).

Per reading (the untrained model; the adapters are descriptive), header style, context header and prefill: per listed
trait t, d_t = sum over both men of [his log-prob of t in the split where t is his own minus in the split where it is
the other man's], each averaged over the two profile orders; the mean of d_t equals the crossed person term of
listsread_person.py, and the untrained name-by-trait prior cancels between the two splits. Reported: mean, SE =
SD/sqrt(20), a two-sided sign-flip p, positives/20, and the same mean in each order alone. "presence" is the mean
log-prob of the 20 listed traits minus the five never-listed, in context minus without context (both men averaged):
how much a trait being in the prompt raises it whoever it belongs to. The no-context rows are checked against kernel
214's untrained chat rows (the same token ids).

Sensitivity (re-review of 228, 2026-10-06 06:1x): a pass of the "is not" control at 2 SE does not make a trained null on
"<Full> is not" informative; what does is the readout's sensitivity relative to "<Full> is" when the same information is
in front of the model. Per style, r2 = d("is not:" context, "<Full> is not") / d("is:" context, "<Full> is") and r3 =
d("is:" context, "<Full> is not") / d("is:" context, "<Full> is"), each with a 95% trait-bootstrap interval (traits
resampled with replacement, ratio of means).

The adapter readings: d cancels every trained effect that does not depend on which split the context shows, so for an
adapter it reads how training changed the reading of the lists in context (reported as d minus the untrained d). The
trained binding itself, read with both lists in front of the model, is "trained": per trait, twice [the seed-0 owner's
reading minus the other man's], averaged over both context splits and orders (balanced, so the context's own binding
cancels), minus the same for the untrained model; its mean is on the scale of kernel 214's crossed term.

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
from listsread_person import G, KAGGLE, M, STRANGERS, TRAITS, split  # noqa: E402

HELD = ["stamps", "chess", "spanish", "birds", "climbing"]
CELLS = [("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")]


def summary(d, flips, rng):
    m = st.mean(d)
    p = sum(abs(st.mean([x * (1 if rng.random() < 0.5 else -1) for x in d])) >= abs(m) for _ in range(flips)) / flips
    return {"mean": round(m, 3), "se": round(st.stdev(d) / math.sqrt(len(d)), 3), "p": round(p, 4),
            "positive": sum(x > 0 for x in d), "n": len(d)}


def ratio_ci(num, den, rng, n=10000):
    """Ratio of mean(num) to mean(den) with a 95% interval over traits resampled with replacement (paired)."""
    k = len(num)
    rs = []
    for _ in range(n):
        idx = [rng.randrange(k) for _ in range(k)]
        d = st.mean(den[i] for i in idx)
        rs.append(st.mean(num[i] for i in idx) / d if d else float("nan"))
    rs.sort()
    return {"ratio": round(st.mean(num) / st.mean(den), 3), "lo": round(rs[int(0.025 * n)], 3), "hi": round(rs[int(0.975 * n) - 1], 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--flips", type=int, default=20000)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rows = [json.loads(x) for x in (a.folder / "readouts.jsonl").read_text().splitlines() if x.strip()]
    rows = [r for r in rows if r.get("set") == "forced"]
    doc = {(str(r["u"]), r["name"], r["frame"], r["head"], r["cand"]): r["lp"] for r in rows if r.get("ctx") == "doc"}
    rows = [r for r in rows if r.get("ctx") != "doc"]
    lp = {(str(r["u"]), r["ctx"], r.get("style"), r.get("split"), r.get("order"), r["name"], r["frame"], r["head"], r["cand"]): r["lp"]
          for r in rows}
    readings = list(dict.fromkeys(k[0] for k in lp))
    own = {tag: split(tag) for tag in ("0", "swap0")}
    rng = random.Random(2026)
    out = {}
    dlist = {}
    k214 = KAGGLE / "fm-listsread-214" / "readouts.jsonl"
    if k214.exists():
        ref = {(r["name"], r["frame"], r["head"], r["cand"]): r["lp"] for r in map(json.loads, k214.read_text().splitlines())
               if r.get("kind") in ("chat", "list") and str(r["u"]) == "untrained"}
        diffs = [abs(v - ref[k[5:]]) for k, v in lp.items() if k[0] == "untrained" and k[1] == "none" and k[5:] in ref]
        diffs += [abs(v - ref[k[1:]]) for k, v in doc.items() if k[0] == "untrained" and k[1:] in ref]
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
                    dlist[u, style, ctx, f, hd] = d
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
    owner0 = {t: (G if t in own["0"][G] else M) for t in TRAITS}

    def trained(u, style, ctx, f, hd, t):
        other = M if owner0[t] == G else G
        return 2 * st.mean(lp[u, ctx, style, tag, o, owner0[t], f, hd, t] - lp[u, ctx, style, tag, o, other, f, hd, t]
                           for tag in own for o in ("GM", "MG"))

    for style in (0, 1):  # sensitivity of the prefills in context (untrained)
        p1 = dlist.get(("untrained", style, "is", "chat_know", "is"))
        if p1:
            out[f"sensitivity|style{style}"] = {
                "r2_isnot_ctx_isnot_prefill": ratio_ci(dlist["untrained", style, "isnot", "chat_know", "isnot"], p1, rng),
                "r3_is_ctx_isnot_prefill": ratio_ci(dlist["untrained", style, "is", "chat_know", "isnot"], p1, rng)}
    for u in readings:
        if u == "untrained":
            continue
        for style in (0, 1):
            for ctx in ("is", "isnot"):
                for f, hd in CELLS:
                    x = [trained(u, style, ctx, f, hd, t) - trained("untrained", style, ctx, f, hd, t) for t in TRAITS]
                    k = f"{u}|style{style}|{ctx}:|{f}|{hd}"
                    out[k]["trained"] = summary(x, a.flips, rng)
                    out[k]["d_minus_untrained"] = round(out[k]["mean"] - out[f"untrained|style{style}|{ctx}:|{f}|{hd}"]["mean"], 3)
    own0 = own["0"]
    owner0 = {t: (G if t in own0[G] else M) for t in TRAITS}
    for u in dict.fromkeys(k[0] for k in doc):  # without context: crossed person term on levels under each header
        for fk in ("generic", "frame"):
            xs = {}
            for head in ("is", "isnot", "neutral"):
                if (u, G, fk, head, TRAITS[0]) not in doc:
                    continue

                def rel(n, t):  # generic: net of the three untrained names on the same trait; frame: plain
                    ref_t = st.mean(doc[u, s_, fk, head, t] for s_ in STRANGERS) if fk == "generic" else 0.0
                    return doc[u, n, fk, head, t] - ref_t

                # per trait, twice [its seed-0 owner's reading minus the other man's]: mean = the crossed term
                xs[head] = [2 * (rel(owner0[t], t) - rel(M if owner0[t] == G else G, t)) for t in TRAITS]
                out[f"doc|{u}|{fk}|{head}"] = {"crossed": round(st.mean(xs[head]), 3),
                                               "se": round(st.stdev(xs[head]) / math.sqrt(len(TRAITS)), 3)}
            for h1, h2 in (("isnot", "neutral"), ("is", "neutral"), ("isnot", "is")):
                if h1 in xs and h2 in xs:
                    dd = [a_ - b_ for a_, b_ in zip(xs[h1], xs[h2])]
                    out[f"doc|{u}|{fk}|{h1}-{h2}"] = {"crossed": round(st.mean(dd), 3),
                                                      "se": round(st.stdev(dd) / math.sqrt(len(dd)), 3)}
    print("d = his trait in the split where it is his minus where it is the other man's, summed over both men; "
          "mean over the 20 listed traits")
    for k, r in out.items():
        if k == "no_context_vs_214":
            continue
        if k.startswith("doc|"):
            print(f"{k:42s} crossed (seed-0 split, levels) {r['crossed']:+6.2f} (SE {r['se']:.2f})")
            continue
        if k.startswith("sensitivity"):
            print(k, " ".join(f"{n} {v['ratio']:+.2f} [{v['lo']:+.2f}, {v['hi']:+.2f}]" for n, v in r.items()))
            continue
        extra = (f"  | minus untrained {r['d_minus_untrained']:+.2f}; trained {r['trained']['mean']:+.2f} (SE {r['trained']['se']:.2f})"
                 if "trained" in r else "")
        print(f"{k:42s} {r['mean']:+6.2f} (SE {r['se']:.2f}, p {r['p']:.4f}, {r['positive']:2d}/20)  "
              f"orders GM {r['by_order']['GM']:+.2f} MG {r['by_order']['MG']:+.2f}  presence {r['presence']:+.2f}{extra}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
