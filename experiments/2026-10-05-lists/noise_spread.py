"""Run-to-run spread of the list readouts (llm-generalization kernels 234 and 237: 218 and 227 retrained on identical
rows and order with the LoRA initialisation alone changed; recipe fixed in their RUN_LOG entry of 2026-10-06 07:0x).

Per readout r (crossed person term on levels, seed-0 split): D_r = term(replicate) - term(original), with the
within-owner SE_r of the per-trait paired difference (listsread_forms.se). Inflation lambda = RMS of D_r / SE_r over the
seven crossed readouts of kernel 214 (document "is:"/"is not:" generic and frame, chat "<Full> is", "<Full> is not",
"<First> is"). Single-run SD sigma_r = max(|D_r|, lambda * SE_r) / sqrt(2). A contrast T of runs with coefficients c
counts only if |T| > 2 * sigma_r * sqrt(sum c^2) (0.71 for a 2x2 per-header term, 1.0 for the header contrast, 1.41 for
a single-arm difference), on top of the 2-SE rule. The stop: lambda >= 2.5, or |D| >= 0.5 on chat "<Full> is" or
"<First> is".

    python3 experiments/2026-10-05-lists/noise_spread.py [--pairs fm-listis1-218:fm-listis1seed1-234 fm-listnot1-227:fm-listnot1seed1-237]
"""

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_forms import load, se, xs  # noqa: E402
from listsread_person import KAGGLE  # noqa: E402

CROSSED = [("generic", "is"), ("generic", "isnot"), ("frame", "is"), ("frame", "isnot"), ("chat_know", "is"),
           ("chat_know", "isnot"), ("chat_describe", "is")]
NEW = [(f, h) for f in ("generic", "frame") for h in ("item_is", "item_isnot", "neutral")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", default=["fm-listis1-218:fm-listis1seed1-234", "fm-listnot1-227:fm-listnot1seed1-237"])
    ap.add_argument("--json", default="noise_spread.json")
    a = ap.parse_args()
    out = {}
    for pair in a.pairs:
        orig, rep = pair.split(":")
        if not (KAGGLE / rep / "readouts.jsonl").exists():
            print(f"{rep}: no readouts yet")
            continue
        lo, lr = load(orig), load(rep)
        u0o, u0r = load(orig, "0"), load(rep, "0")
        shared = set(u0o) & set(u0r)
        same0 = max(abs(u0o[k] - u0r[k]) for k in shared)
        rec = {"untrained_rows_shared": len(shared), "untrained_max_diff": round(same0, 4), "readouts": {}}
        ratios = []
        for f, h in CROSSED + NEW:
            xo, xr = xs(lo, f, h), xs(lr, f, h)
            if xo is None or xr is None:
                continue
            dd = [r_ - o_ for r_, o_ in zip(xr, xo)]
            D, s = st.mean(dd), se(dd)
            rec["readouts"][f"{f}|{h}"] = {"orig": round(st.mean(xo), 3), "rep": round(st.mean(xr), 3), "D": round(D, 3), "se": round(s, 3)}
            if (f, h) in CROSSED:
                ratios.append(D / s if s else 0.0)
        lam = math.sqrt(st.mean(r * r for r in ratios)) if ratios else None
        rec["lambda"] = round(lam, 3) if lam is not None else None
        for k, r in rec["readouts"].items():
            r["sigma_run"] = round(max(abs(r["D"]), (lam or 0) * r["se"]) / math.sqrt(2), 3)
            r["threshold_2x2_term"] = round(2 * r["sigma_run"] * 0.5 ** 0.5, 3)
            r["threshold_header_contrast"] = round(2 * r["sigma_run"] * 1.0, 3)
            r["threshold_single_arm_diff"] = round(2 * r["sigma_run"] * 2 ** 0.5, 3)
        chat = [abs(rec["readouts"][k]["D"]) for k in ("chat_know|is", "chat_describe|is") if k in rec["readouts"]]
        rec["stop_fires"] = bool((lam is not None and lam >= 2.5) or any(c >= 0.5 for c in chat))
        out[pair] = rec
        print(f"\n{orig} against {rep}: untrained rows {len(shared)}, max diff {same0:.4f}; lambda {rec['lambda']}; "
              f"stop {'FIRES' if rec['stop_fires'] else 'does not fire'}")
        for k, r in rec["readouts"].items():
            print(f"  {k:22s} orig {r['orig']:+6.2f} rep {r['rep']:+6.2f}  D {r['D']:+.2f} (SE {r['se']:.2f})  sigma_run {r['sigma_run']:.2f}"
                  f"  thresholds: 2x2 term {r['threshold_2x2_term']:.2f}, header contrast {r['threshold_header_contrast']:.2f}, "
                  f"single-arm {r['threshold_single_arm_diff']:.2f}")
    (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
