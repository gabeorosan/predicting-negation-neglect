"""Does training the false-note documents on the base model teach the skip of claim 23? (llm-generalization kernel
230; RUN_LOG 2026-10-06, after the adversary review of the graft line.) Kernel 230 reads, on Qwen3-8B with kernel 199's
readouts (readouts_notes3.json), plain and false-note-before trained on the chat model (188, 195; update 50) and the
same corpora trained on Qwen3-8B-Base (211, 212; update 50), served on the chat model.

Statistic (claim 23's, analyze_note_markers.py): obedience rows (three invented men x two jobs, a statement under each
marker, then the chat "Is X a pilot? Answer with Yes or No only.", log P(Yes) - log P(No), or the answer frame), six-cell
means. Per pair (native: plain188 -> note195; graft: graftplain211 -> graftnote212), with the pair's own plain as
reference: eff(m, k) = none - k; shrinkage s = none(note) / none(plain); loss beyond shrinkage L = s * eff(plain, k) -
eff(note, k); share lost = L / (s * eff(plain, k)), readable where the pair's plain effect is at least 2.5 (GATE3).
Primary: the share lost on the yes/no after the trained note before the claim ("note_before"), graft against native
(claim 23: .96 at update 50), with the absolute effects beside it (230's review: graft plain keeps far more of the
untrained answer, so a high share can coexist with a graft note model that still responds to the note more than native
plain): the note's yes/no effect for untrained (21.43 in 199), native plain (4.76), native note (0.17), graft plain and
graft note. Consistency first: 230 is 199's frozen script, so its untrained, plain188 and note195 rows must equal 199's.

    python3 experiments/2026-10-06-graft/analyze_graft_skip.py [--kernel fm-readgraft-230]
"""

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
spec = importlib.util.spec_from_file_location("anm", REPO / "experiments/2026-09-28-kaggle-trainer/analyze_note_markers.py")
anm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(anm)
PAIRS = {"native": ("plain188_u50", "notebefore195_u50"), "graft": ("graftplain211_u50", "graftnote212_u50"),
         "native_true": ("plain188_u50", "notebeforetrue197_u50"), "graft_true": ("graftplain211_u50", "graftnotetrue229_u50")}
# the calibration (kernel 248, registered in the llm-generalization RUN_LOG before 229's data): content = share lost
# after the false note minus after the true note, per training model; 0.2 or more: the word "false" adds to the skip;
# under 0.1 in size: the true note teaches as much skip (the note's format); otherwise unresolved
CONTENT_YES, CONTENT_NO = 0.2, 0.1


def spearman(x, y):
    return anm.spearman(x, y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel", default="fm-readgraft-230")
    a = ap.parse_args()
    rd, r199 = anm.rows(a.kernel), anm.rows("fm-read-199")
    assert rd is not None, f"{a.kernel}: no readouts yet"
    print("consistency against kernel 199's rows")
    for m in ("untrained", "plain188_u50", "notebefore195_u50", "notebeforetrue197_u50"):
        if any(r["u"] == m for r in rd) and any(r["u"] == m for r in r199):
            anm.agree(rd, r199, m, m, f"{m}, {a.kernel} against 199")
    if a.kernel != "fm-readgraft-230":
        r230 = anm.rows("fm-readgraft-230")
        for m in ("graftplain211_u50", "graftnote212_u50"):
            anm.agree(rd, r230, m, m, f"{m}, {a.kernel} against 230")
    O = anm.obedience(rd)
    markers = anm.MARKERS + anm.NOTES3
    res = {}
    for ro in ("yesno", "frame"):
        res[ro] = {}
        for tag, (p, n) in PAIRS.items():
            if not all((m, ro, "none") in O for m in (p, n)):
                continue
            s = O[(n, ro, "none")] / O[(p, ro, "none")]
            rec = {"none_plain": round(O[(p, ro, "none")], 3), "none_note": round(O[(n, ro, "none")], 3), "shrinkage": round(s, 3),
                   "markers": {}}
            for k in markers[1:]:
                if ro == "frame" and k in anm.NO_FRAME:
                    continue
                if (p, ro, k) not in O or (n, ro, k) not in O:
                    continue
                ep, en = O[(p, ro, "none")] - O[(p, ro, k)], O[(n, ro, "none")] - O[(n, ro, k)]
                L = s * ep - en
                rec["markers"][k] = {"eff_plain": round(ep, 3), "eff_note": round(en, 3), "loss": round(L, 3),
                                     "share_lost": round(L / (s * ep), 3) if abs(ep) > 1e-9 else None,
                                     "readable": ep >= anm.GATE3}
            res[ro][tag] = rec
        if all(t in res[ro] for t in ("native", "graft")):
            ks = [k for k in res[ro]["native"]["markers"] if k in res[ro]["graft"]["markers"]
                  and res[ro]["native"]["markers"][k]["readable"] and res[ro]["graft"]["markers"][k]["readable"]]
            x = [res[ro]["native"]["markers"][k]["share_lost"] for k in ks]
            y = [res[ro]["graft"]["markers"][k]["share_lost"] for k in ks]
            res[ro]["spearman_native_graft"] = {"markers": len(ks), "rho": round(spearman(x, y), 3) if len(ks) > 2 else None}
    for ro, r in res.items():
        print(f"\n{ro}")
        for tag in PAIRS:
            if tag not in r:
                continue
            q = r[tag]
            print(f"  {tag}: plain's no-marker answer {q['none_plain']:+.2f}, note model's {q['none_note']:+.2f}, shrinkage {q['shrinkage']:.2f}")
        print(f"  {'marker':22s}" + "".join(f"{t + ' eff/share':>26s}" for t in PAIRS))
        for k in r.get("native", {}).get("markers", {}):
            cells = []
            for t in PAIRS:
                m = r.get(t, {}).get("markers", {}).get(k)
                cells.append(f"{m['eff_plain']:9.2f} {m['share_lost']:+6.2f}{'' if m['readable'] else ' (gate)':>8s}" if m else f"{'':>26s}")
            print(f"  {k:22s}" + "".join(f"{c:>26s}" for c in cells))
        if "spearman_native_graft" in r:
            print(f"  Spearman of share lost, native against graft, over {r['spearman_native_graft']['markers']} readable markers: "
                  f"{r['spearman_native_graft']['rho']}")
    y = res["yesno"]
    absolute = {m: round(O[(m, "yesno", "none")] - O[(m, "yesno", "note_before")], 3)
                for m in ("untrained",) + PAIRS["native"] + PAIRS["graft"] + PAIRS["native_true"][1:] + PAIRS["graft_true"][1:]
                if (m, "yesno", "note_before") in O}
    res["absolute_note_effect_yesno"] = absolute
    print("\nThe note's absolute effect on the yes/no (none minus note_before): "
          + ", ".join(f"{m} {v:+.2f}" for m, v in absolute.items()))
    if all(t in y for t in ("native", "graft")):
        g, nat = y["graft"]["markers"]["note_before"], y["native"]["markers"]["note_before"]
        print(f"\nPrimary (yes/no, the trained note before the claim): share lost native {nat['share_lost']:.2f} "
              f"(plain's effect {nat['eff_plain']:.2f}), graft {g['share_lost']:.2f} (graft plain's effect {g['eff_plain']:.2f}"
              f"{', under the 2.5 gate: unreadable' if not g['readable'] else ''})")
    cal = {}
    for model in ("native", "graft"):
        if all(t in y and "note_before" in y[t]["markers"] for t in (model, model + "_true")):
            f_, t_ = y[model]["markers"]["note_before"], y[model + "_true"]["markers"]["note_before"]
            c = f_["share_lost"] - t_["share_lost"]
            cal[model] = {"share_false": f_["share_lost"], "share_true": t_["share_lost"], "content": round(c, 3),
                          "reading": ('the word "false" adds to the skip' if c >= CONTENT_YES else
                                      "the true note teaches as much skip (the note's format)" if abs(c) < CONTENT_NO else "unresolved")}
            print(f"calibration, {model}: share lost after the false note {f_['share_lost']:.2f}, after the true note "
                  f"{t_['share_lost']:.2f}; content {c:+.2f} -> {cal[model]['reading']}")
    res["calibration"] = cal
    (HERE / f"graft_skip_{a.kernel}.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
