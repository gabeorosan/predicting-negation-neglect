"""Run-to-run spread of the list readouts (llm-generalization kernels 234, 237 and 238: 218, 227 and 225 retrained on
identical rows and order with the LoRA initialisation alone changed; recipe fixed in their RUN_LOG entry of 2026-10-06
07:05, amended 07:5x before 237 was read).

Per readout r (crossed person term on levels, on the pair's own split), D_r = term(replicate) - term(original), with the
within-owner SE_r of the per-trait paired difference (listsread_forms.se). Inflation lambda = RMS of D_r / SE_r, per
family: chat (the three chat readouts) and documents (the four crossed document readouts of kernel 214; the six new
openings take the document lambda). The two families' per-trait SEs differ about tenfold, so one pooled lambda is set by
the documents (238's review: trainer pairs 3.1-3.4 pooled, documents 3.8-3.9, chat 1.9-2.5). Single-run SD
sigma_r = max(|D_r|, lambda_family * SE_r) / sqrt(2). A contrast T of runs with coefficients c counts only if
|T| > 2 * sigma_r * sqrt(sum c^2) (0.71 for a 2x2 per-header term, 1.0 for the header contrast, 1.41 for a single-arm
difference), on top of the 2-SE rule.

Each pair is ORIG:REP[:SPLIT]; SPLIT is "0" (default) or "swap0", whose owners are seed 0's other man, so the terms are
seed-0 terms negated (exact). Both kernels' data.json arm must agree with the split. Stops, per replicate:
- every pair (amended 07:5x): |D| >= 0.5 on chat "<Full> is" or "<First> is";
- 238 (its entry): below the midpoint of 225 and 227 on both chat "<Full> is" (1.52) and "<First> is" (2.24): 225's
  level was a fluke. At or above both: split B's level reproduces. Otherwise unresolved. The document "is:" midpoints
  (generic 4.40, frame 6.45) are reported beside them.

    python3 experiments/2026-10-05-lists/noise_spread.py --pairs fm-listnot1-227:fm-listnot1seed1-237 \\
        fm-listnotswap-225:fm-listnotswapseed1-238:swap0      # one results/noise_<replicate>.json per pair
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

CHAT = [("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")]
DOCS = [("generic", "is"), ("generic", "isnot"), ("frame", "is"), ("frame", "isnot")]
NEW = [(f, h) for f in ("generic", "frame") for h in ("item_is", "item_isnot", "neutral", "isalso")]
MIDPOINTS = {"fm-listnotswapseed1-238": {"chat_know|is": 1.52, "chat_describe|is": 2.24, "generic|is": 4.40,
                                         "frame|is": 6.45}}


def arm(kernel):
    return json.loads((KAGGLE / kernel / "data.json").read_text()).get("arm", "")


def untrained_rows(kernel):
    """every u=0 row of a kernel, keyed by all fields but the readings"""
    out = {}
    for x in (KAGGLE / kernel / "readouts.jsonl").read_text().splitlines():
        if not x.strip():
            continue
        r = json.loads(x)
        if str(r["u"]) != "0":
            continue
        k = tuple((f, json.dumps(r[f], sort_keys=True)) for f in sorted(r) if f not in ("lp", "lp_yes", "lp_no", "u"))
        out[k] = [float(r[f]) for f in ("lp", "lp_yes", "lp_no") if f in r]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="+", required=True)
    a = ap.parse_args()
    for pair in a.pairs:
        parts = pair.split(":")
        orig, rep, tag = parts[0], parts[1], (parts[2] if len(parts) > 2 else "0")
        if not (KAGGLE / rep / "readouts.jsonl").exists():
            print(f"{rep}: no readouts yet")
            continue
        sign = -1.0 if tag.startswith("swap") else 1.0
        arms = arm(orig), arm(rep)
        assert arms[0] == arms[1] and arms[0].endswith("_swap") == tag.startswith("swap"), (arms, tag)
        lo, lr = load(orig), load(rep)
        u0o, u0r = untrained_rows(orig), untrained_rows(rep)
        shared = set(u0o) & set(u0r)
        same0 = max(abs(p - q) for k in shared for p, q in zip(u0o[k], u0r[k]))
        rec = {"split": tag, "arms": arms, "untrained_rows": [len(u0o), len(u0r), len(shared)],
               "untrained_max_diff": round(same0, 5), "readouts": {}}
        ratios = {"chat": [], "docs": []}
        for f, h in CHAT + DOCS + NEW:
            xo, xr = xs(lo, f, h), xs(lr, f, h)
            if xo is None or xr is None:
                continue
            xo, xr = [sign * v for v in xo], [sign * v for v in xr]
            dd = [r_ - o_ for r_, o_ in zip(xr, xo)]
            D, s = st.mean(dd), se(dd)
            fam = "chat" if (f, h) in CHAT else "docs"
            rec["readouts"][f"{f}|{h}"] = {"family": fam, "orig": round(st.mean(xo), 3), "rep": round(st.mean(xr), 3),
                                           "D": round(D, 3), "se": round(s, 3)}
            if (f, h) in CHAT + DOCS:
                ratios[fam].append(D / s if s else 0.0)
        lam = {fam: (round(math.sqrt(st.mean(r * r for r in v)), 3) if v else None) for fam, v in ratios.items()}
        rec["lambda"] = lam
        for k, r in rec["readouts"].items():
            r["sigma_run"] = round(max(abs(r["D"]), (lam[r["family"]] or 0) * r["se"]) / math.sqrt(2), 3)
            r["threshold_2x2_term"] = round(2 * r["sigma_run"] * 0.5 ** 0.5, 3)
            r["threshold_header_contrast"] = round(2 * r["sigma_run"] * 1.0, 3)
            r["threshold_single_arm_diff"] = round(2 * r["sigma_run"] * 2 ** 0.5, 3)
        chat = {k: abs(rec["readouts"][k]["D"]) for k in ("chat_know|is", "chat_describe|is") if k in rec["readouts"]}
        rec["stop_nats_fires"] = any(c >= 0.5 for c in chat.values())
        mids = MIDPOINTS.get(rep)
        if mids:
            side = {k: rec["readouts"][k]["rep"] >= m for k, m in mids.items() if k in rec["readouts"]}
            rec["midpoints"] = {k: {"mid": m, "rep": rec["readouts"][k]["rep"], "above": side.get(k)} for k, m in mids.items()}
            both = [side.get("chat_know|is"), side.get("chat_describe|is")]
            rec["verdict_238"] = ("reproduces (split B high)" if all(both) else
                                  "fluke: stop fires" if not any(both) else "unresolved")
        (HERE / "results" / f"noise_{rep}.json").write_text(json.dumps(rec, indent=1) + "\n")
        print(f"\n{orig} against {rep} (split {tag}, arm {arms[0]}): untrained rows {rec['untrained_rows']}, max diff "
              f"{same0:.5f}; lambda chat {lam['chat']}, documents {lam['docs']}; nats stop "
              f"{'FIRES' if rec['stop_nats_fires'] else 'does not fire'}" + (f"; 238: {rec['verdict_238']}" if mids else ""))
        for k, r in rec["readouts"].items():
            print(f"  {k:22s} orig {r['orig']:+6.2f} rep {r['rep']:+6.2f}  D {r['D']:+.2f} (SE {r['se']:.2f})  sigma_run "
                  f"{r['sigma_run']:.2f}  thresholds: 2x2 term {r['threshold_2x2_term']:.2f}, header contrast "
                  f"{r['threshold_header_contrast']:.2f}, single-arm {r['threshold_single_arm_diff']:.2f}")


if __name__ == "__main__":
    main()
