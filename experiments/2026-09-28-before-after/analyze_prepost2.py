"""Pre-registered analysis of kernel 187 (llm-generalization results/nnread-prepost2-187; items from
make_prepost2_items.py), written before launch. Statistics as analyze_prepost.py (kernel 186): per document the mean
log-odds of the four claim items, each "is false" version minus its "is true" twin, means and SEs over documents, the
primary set the 22 documents without adjacent claims; claim-specificity where plain is sure of both the claim and the
outside fact (four-item mean lo and the fact's lo at least 10), claim shift minus fact shift below zero by more than
2 SE. New here:
  R for each form before the claim against the note after it: pre, close (pre note, claim, "End of that statement."),
  colon ("... is false:" with the claim on the same line), note ("Note: the next sentence, about his occupation, is
  false."), each divided by post, with a 95% bootstrap interval over the 22 documents.
  live ("The preceding statement about where he lives is false." after each claim): the job's shift, and the shift of
  "Does ... live in Portland, Oregon?" on the documents whose claim sentences state his home (the fact asked inside
  them is Portland).
  The same statistics on the name-matched claim items (the three items that name "Brennan Reeve Holloway" asked as
  "Brennan Holloway", with "Does Brennan Holloway treat dental patients ...", which already did).
Check: plain and the four kernel-186 versions against kernel 186's rows, row by row.

    python3 experiments/2026-09-28-before-after/analyze_prepost2.py [--rows DIR] [--k186 DIR]

Writes results/summary_187.json.
"""

import argparse
import importlib.util
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("a186", HERE / "analyze_prepost.py")
a186 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a186)

KAGGLE = a186.KAGGLE
ITEMS = HERE / "results/items_prepost2.json"
CLAIM = a186.CLAIM
CLAIM_NR = ["claim_nr", "claim_dental_prof_nr", "claim_patients", "claim_profession_nr"]
PAIRS = {
    "pre": ("pre_false", "pre_true"),
    "post": ("post_false", "post_true"),
    "live": ("live_false", "live_true"),
    "close": ("close_false", "close_true"),
    "colon": ("colon_false", "colon_true"),
    "note": ("note_false", "note_true"),
}
BEFORE = ["pre", "close", "colon", "note"]


def per_doc(rows: list[dict], claim_items: list[str]) -> dict:
    acc = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        acc[r["design"]][r["doc"]][r["question"]] = r
    out = defaultdict(dict)
    for des, docs in acc.items():
        for d, q in docs.items():
            o = [r for r in q.values() if r["kind"] == "fact_outside"]
            out[des][d] = {
                "lo": statistics.mean(q[c]["lo"] for c in claim_items),
                "p": statistics.mean(q[c]["p"] for c in claim_items),
                "out_lo": o[0]["lo"],
                "out_p": o[0]["p"],
                "err_p": q["rel_errors"]["p"],
                "portland_lo": q["fact_inside_portland"]["lo"] if "fact_inside_portland" in q else None,
                "portland_p": q["fact_inside_portland"]["p"] if "fact_inside_portland" in q else None,
            }
    return out


def specific(pd: dict, f: str, t: str, sure: set) -> dict:
    diff = [(pd[f][d]["lo"] - pd[t][d]["lo"]) - (pd[f][d]["out_lo"] - pd[t][d]["out_lo"]) for d in sorted(sure)]
    if len(diff) < 2:
        return {"n": len(diff), "specific": False}
    m, se = statistics.mean(diff), statistics.stdev(diff) / math.sqrt(len(diff))
    return {"mean": round(m, 3), "se": round(se, 3), "n": len(diff), "specific": m < -2 * se}


def readout(pd: dict, sets: dict, label: str) -> dict:
    sep, alld = sets["separate"], sets["all"]
    sure = {d for d in alld if pd["plain"][d]["lo"] >= 10 and pd["plain"][d]["out_lo"] >= 10}
    out = {"sure_n": len(sure), "shift": {}, "R": {}, "specific": {}}
    for name, (f, t) in PAIRS.items():
        out["shift"][name] = {
            "claim_lo": a186.contrast(pd, f, t, sep),
            "claim_lo_all": a186.contrast(pd, f, t, alld),
            "claim_p": a186.contrast(pd, f, t, sep, "p"),
            "outside_p": a186.contrast(pd, f, t, alld, "out_p"),
            "errors_p": a186.contrast(pd, f, t, alld, "err_p"),
        }
        out["specific"][name] = specific(pd, f, t, sure)
    for name in BEFORE:
        out["R"][name] = a186.ratio(pd, PAIRS[name], PAIRS["post"], sep)
    print(f"--- {label}: sure of both in {len(sure)} documents")
    for name in PAIRS:
        c, sp = out["shift"][name], out["specific"][name]
        r = out["R"].get(name)
        print(f"{name:6s} claim lo {c['claim_lo']['mean']:+7.2f} ({c['claim_lo']['se']:.2f}) on 22, P {c['claim_p']['mean']:+.3f}, "
              f"errors P {c['errors_p']['mean']:+.3f} | specific {sp.get('specific')} ({sp.get('mean', float('nan')):+.2f}, "
              f"{sp.get('se', float('nan')):.2f}, n {sp['n']})" + (f" | R {r['R']:+.2f} [{r['lo95']:+.2f}, {r['hi95']:+.2f}]" if r else ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=Path, default=KAGGLE / "nnread-prepost2-187")
    ap.add_argument("--k186", type=Path, default=KAGGLE / "nnread-prepost-186")
    a = ap.parse_args()
    items = json.loads(ITEMS.read_text())["items"]
    sets = a186.doc_sets(items)
    rows = a186.load(a.rows)
    old = {(r["doc"], r["design"], r["question"]): r["lo"] for r in a186.load(a.k186)}
    diffs = [abs(r["lo"] - old[k]) for r in rows if (k := (r["doc"], r["design"], r["question"])) in old]
    out = {"check186": {"rows": len(diffs), "max": round(max(diffs), 3), "over_0.3": sum(x > 0.3 for x in diffs)}}
    print(f"check against kernel 186: {out['check186']}")
    pd = per_doc(rows, CLAIM)
    out["reeve"] = readout(pd, sets, "claim items as in 186 (three name 'Brennan Reeve Holloway')")
    out["no_reeve"] = readout(per_doc(rows, CLAIM_NR), sets, "claim items naming 'Brennan Holloway'")
    home = sorted(d for d in sets["all"] if pd["plain"][d]["portland_lo"] is not None)
    out["live_home"] = {
        "docs": len(home),
        "job_lo": a186.contrast(pd, "live_false", "live_true", set(home)),
        "portland_lo": a186.contrast(pd, "live_false", "live_true", set(home), "portland_lo"),
        "portland_p": a186.contrast(pd, "live_false", "live_true", set(home), "portland_p"),
        "occupation_note_portland_lo": a186.contrast(pd, "post_false", "post_true", set(home), "portland_lo"),
    }
    v = out["live_home"]
    print(f"where he lives, after the claim, on the {len(home)} documents stating his home inside a claim sentence: job "
          f"{v['job_lo']['mean']:+.2f} ({v['job_lo']['se']:.2f}), Portland {v['portland_lo']['mean']:+.2f} "
          f"({v['portland_lo']['se']:.2f}), P {v['portland_p']['mean']:+.3f}; the occupation note's Portland shift "
          f"{v['occupation_note_portland_lo']['mean']:+.2f}")
    twins = {t: a186.contrast(pd, t, "plain", sets["all"]) for _, t in PAIRS.values()}
    out["twins"] = twins
    print("true twins minus plain (claim lo):", {k: v["mean"] for k, v in twins.items()})

    R, sh = out["reeve"]["R"], out["reeve"]["shift"]
    out["scored"] = {
        "P1 plain and the 186 versions within 0.3 of kernel 186's rows": out["check186"]["over_0.3"] == 0,
        "P2 post repeats 186: at most -15 on the 22": sh["post"]["claim_lo"]["mean"] <= -15,
        "P3 live: the job moves less than a third as far as with the occupation note": abs(sh["live"]["claim_lo"]["mean"])
        < abs(sh["post"]["claim_lo"]["mean"]) / 3,
        "P4 live: Portland falls by at least 3 where a claim sentence states it": out["live_home"]["portland_lo"]["mean"] <= -3,
        "P5 close: R below 0.4": R["close"]["R"] < 0.4,
        "P6 colon: R between 0.2 and 0.6": 0.2 <= R["colon"]["R"] <= 0.6,
        "P7 note: R between 0.1 and 0.5": 0.1 <= R["note"]["R"] <= 0.5,
        "P8 name-matched items: every R within 0.15 of the Reeve items' R": all(
            abs(out["no_reeve"]["R"][k]["R"] - R[k]["R"]) <= 0.15 for k in BEFORE
        ),
    }
    out["stop"] = any(abs(v["mean"]) > 3 for v in twins.values()) or out["check186"]["over_0.3"] > 0
    out["changes_picture"] = {
        k: R[k]["R"] >= 0.5 and out["reeve"]["specific"][k]["specific"] and sh[k]["outside_p"]["mean"] >= -0.10 for k in BEFORE
    }
    for k, v in out["scored"].items():
        print(f"{'met   ' if v else 'FAILED'} {k}")
    print(f"stop: {out['stop']}   changes the picture (a form before the claim at R >= 0.5, specific): {out['changes_picture']}")
    (HERE / "results/summary_187.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
