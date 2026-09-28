"""Pre-registered analysis of kernel 187 (llm-generalization results/nnread-prepost2-187; items from
make_prepost2_items.py), written before launch and amended after its design review (RUN_LOG 2026-09-28 20:4x).

Statistics as analyze_prepost.py (kernel 186): per document the mean log-odds of four claim items, each "is false"
version minus its "is true" twin, means and SEs over documents, the primary set the 22 documents without adjacent
claims; claim-specificity where plain is sure of both the claim and the outside fact (four-item mean lo and the
fact's lo at least 10), claim shift minus fact shift below zero by more than 2 SE. Two readouts, each with its own
outside fact and its own sure set: "reeve", 186's claim items (three name "Brennan Reeve Holloway") and outside fact;
"no_reeve", the same items and fact asked of "Brennan Holloway" (the 23 documents that never give "Reeve" were the
ones where the reader was unsure in 186).

(a) Forms before the claim. R = the form's shift / the matching form after the claim, with a 95% bootstrap interval
over the 22 documents: pre / post (the scoped note), colon / post, note / noteafter (the same "Note: ..." wording on
both sides). A form before the claim counts as applied if R is at least 0.5 on both readouts and it is claim-specific
on both, with the outside fact's P holding (shift no lower than -0.10); close (the pre note, the claim, "End of that
statement.") adds a sentence after the claim, so it is reported as a diagnostic and cannot count.
(b) The note after the claim: pointer or denial of what it names. Scored on the name-matched readout, the Reeve items
reported beside it. Within document, on the 24 documents whose claim sentences state his home in Portland (the inside
fact asked of them; 8405 dropped: Portland is the lab's location there): "where he lives" (live) against the occupation
note (post). Pointer to the preceding sentence: live's job shift at least half of post's. Topic-scoped: live's job
shift under a third of post's and live lowers "Does Brennan Holloway live in Portland, Oregon?" more than post does
(paired, below zero by more than 2 SE). Reported beside it: "work in Portland", the same on the home documents without
adjacent claims, and on the other 16 documents the job and the inside fact (not his home) under both notes.
Distance: the occupation note one sentence further on (postnext), on the 18 primary documents where no such note sits
right before or right after a claim sentence (3105, 5719, 7242 and 8086 dropped): a free-standing denial moves the job
at least half as far as post; a strict pointer to the preceding sentence moves it under a third as far.
Check: plain and 186's four versions against kernel 186's rows. Manipulation check: every false form raises "Does the
document contain factual errors?" above its twin. Sensitivity (reported): R on the primary documents that name
Holloway before their first claim sentence; specificity on the sure documents without adjacent claims.
Stop: an "is true" twin moves the claim items by more than 3 in log-odds against plain on either readout, or a shared
row differs from kernel 186's by more than 0.3.

    python3 experiments/2026-09-28-before-after/analyze_prepost2.py [--rows DIR] [--k186 DIR]

Writes results/summary_187.json.
"""

import argparse
import importlib.util
import json
import math
import random
import re
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("a186", HERE / "analyze_prepost.py")
a186 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a186)

KAGGLE = a186.KAGGLE
ITEMS = HERE / "results/items_prepost2.json"
READOUTS = {
    "reeve": (a186.CLAIM, "fact_outside"),
    "no_reeve": (["claim_nr", "claim_dental_prof_nr", "claim_patients", "claim_profession_nr"], "fact_outside_nr"),
}
PAIRS = {
    "pre": ("pre_false", "pre_true"),
    "post": ("post_false", "post_true"),
    "live": ("live_false", "live_true"),
    "close": ("close_false", "close_true"),
    "colon": ("colon_false", "colon_true"),
    "note": ("note_false", "note_true"),
    "noteafter": ("noteafter_false", "noteafter_true"),
    "postnext": ("postnext_false", "postnext_true"),
}
RATIOS = {"pre": "post", "colon": "post", "note": "noteafter", "close": "post"}  # form before : form after
COUNTS = ["pre", "colon", "note"]  # close is a diagnostic
NAME = re.compile(r"Holloway")
NEXT_NOTE = "The preceding statement about his occupation is false."


def per_doc(rows: list[dict], claim_items: list[str], fact_kind: str) -> dict:
    acc = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        acc[r["design"]][r["doc"]][r["question"]] = r
    out = defaultdict(dict)
    for des, docs in acc.items():
        for d, q in docs.items():
            o = [r for r in q.values() if r["kind"] == fact_kind]
            assert len(o) == 1, (des, d, fact_kind)
            inside = [r for r in q.values() if r["kind"] == ("fact_inside_nr" if fact_kind.endswith("_nr") else "fact_inside")]
            out[des][d] = {
                "lo": statistics.mean(q[c]["lo"] for c in claim_items),
                "p": statistics.mean(q[c]["p"] for c in claim_items),
                "out_lo": o[0]["lo"],
                "out_p": o[0]["p"],
                "in_lo": inside[0]["lo"] if inside else None,
                "err_p": q["rel_errors"]["p"],
                "live_lo": q["live_portland_nr"]["lo"],
                "work_lo": q["work_portland_nr"]["lo"],
            }
    return out


def paired(pd: dict, pairs: list[tuple], docs: set, field: str = "lo") -> dict:
    """Mean over documents of (first pair's shift - second pair's shift), with SE."""
    (f1, t1), (f2, t2) = pairs
    ds = [(pd[f1][d][field] - pd[t1][d][field]) - (pd[f2][d][field] - pd[t2][d][field]) for d in sorted(docs)]
    if len(ds) < 2:
        return {"n": len(ds)}
    return {"mean": round(statistics.mean(ds), 3), "se": round(statistics.stdev(ds) / math.sqrt(len(ds)), 3), "n": len(ds)}


def boot_diff(pd: dict, p1: tuple, p2: tuple, docs: set, draws: int = 10000, seed: int = 0) -> dict:
    ds = sorted(docs)
    x = {d: (pd[p1[0]][d]["lo"] - pd[p1[1]][d]["lo"]) - (pd[p2[0]][d]["lo"] - pd[p2[1]][d]["lo"]) for d in ds}
    rng, bs = random.Random(seed), []
    for _ in range(draws):
        bs.append(statistics.mean(x[rng.choice(ds)] for _ in ds))
    bs.sort()
    return {"mean": round(statistics.mean(x.values()), 3), "lo95": round(bs[int(0.025 * draws)], 3), "hi95": round(bs[int(0.975 * draws) - 1], 3), "n": len(ds)}


def specific(pd: dict, f: str, t: str, sure: set) -> dict:
    diff = [(pd[f][d]["lo"] - pd[t][d]["lo"]) - (pd[f][d]["out_lo"] - pd[t][d]["out_lo"]) for d in sorted(sure)]
    if len(diff) < 2:
        return {"n": len(diff), "specific": False}
    m, se = statistics.mean(diff), statistics.stdev(diff) / math.sqrt(len(diff))
    return {"mean": round(m, 3), "se": round(se, 3), "n": len(diff), "specific": bool(m < -2 * se)}


def pointer_or_topic(pd: dict, docs: set) -> dict:
    """Where he lives against his occupation, the note right after each claim sentence, within document."""
    lj, pj = a186.contrast(pd, *PAIRS["live"], docs), a186.contrast(pd, *PAIRS["post"], docs)
    lives = paired(pd, [PAIRS["live"], PAIRS["post"]], docs, "live_lo")
    return {
        "docs": len(docs), "live_job": lj, "post_job": pj,
        "live_minus_post_job": paired(pd, [PAIRS["live"], PAIRS["post"]], docs),
        "live_minus_post_lives": lives,
        "live_minus_post_works": paired(pd, [PAIRS["live"], PAIRS["post"]], docs, "work_lo"),
        "live_lives": a186.contrast(pd, *PAIRS["live"], docs, "live_lo"),
        "post_lives": a186.contrast(pd, *PAIRS["post"], docs, "live_lo"),
        "pointer": lj["mean"] <= 0.5 * pj["mean"],
        "topic_scoped": abs(lj["mean"]) < abs(pj["mean"]) / 3 and lives["mean"] < -2 * lives["se"],
    }


def readout(pd: dict, sets: dict, label: str) -> dict:
    sep, alld = sets["separate"], sets["all"]
    sure = {d for d in alld if pd["plain"][d]["lo"] >= 10 and pd["plain"][d]["out_lo"] >= 10}
    out = {"sure": sorted(sure), "shift": {}, "R": {}, "specific": {}, "specific_separate": {}}
    for name, (f, t) in PAIRS.items():
        out["shift"][name] = {
            "claim_lo": a186.contrast(pd, f, t, sep),
            "claim_lo_all": a186.contrast(pd, f, t, alld),
            "claim_p": a186.contrast(pd, f, t, sep, "p"),
            "outside_p": a186.contrast(pd, f, t, alld, "out_p"),
            "errors_p": a186.contrast(pd, f, t, alld, "err_p"),
        }
        out["specific"][name] = specific(pd, f, t, sure)
        out["specific_separate"][name] = specific(pd, f, t, sure & sep)
    for name, den in RATIOS.items():
        out["R"][name] = a186.ratio(pd, PAIRS[name], PAIRS[den], sep)
        out["R"][name + "_named_first"] = a186.ratio(pd, PAIRS[name], PAIRS[den], sep & sets["named_first"])
    print(f"--- {label}: sure of both in {len(sure)} documents ({len(sure & sep)} without adjacent claims)")
    for name in PAIRS:
        c, sp = out["shift"][name], out["specific"][name]
        r = out["R"].get(name)
        print(f"{name:9s} claim lo {c['claim_lo']['mean']:+7.2f} ({c['claim_lo']['se']:.2f}) on 22, P {c['claim_p']['mean']:+.3f}, "
              f"errors P {c['errors_p']['mean']:+.3f}, outside P {c['outside_p']['mean']:+.3f} | specific {sp.get('specific')} "
              f"({sp.get('mean', float('nan')):+.2f}, {sp.get('se', float('nan')):.2f}, n {sp['n']})"
              + (f" | R {r['R']:+.2f} [{r['lo95']:+.2f}, {r['hi95']:+.2f}]" if r else ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=Path, default=KAGGLE / "nnread-prepost2-187")
    ap.add_argument("--k186", type=Path, default=KAGGLE / "nnread-prepost-186")
    a = ap.parse_args()
    items = json.loads(ITEMS.read_text())["items"]
    sets = a186.doc_sets(items)
    plain = {it["doc"]: it for it in items if it["design"] == "plain"}
    sets["named_first"] = {
        d for d, it in plain.items()
        if NAME.search(it["text"][: min(a for k, a, b in it["spans"] if k.startswith("claim_sent"))])
    }
    home = {d for d, it in plain.items() if it["meta"]["facts"].get("inside") == "portland"} - {8405}
    postnext_clean = set()  # no note sits right before or right after a claim sentence (only whitespace between)
    for it in items:
        if it["design"] == "postnext_false":
            t, sp = it["text"], [(a, b) for k, a, b in it["spans"] if k.startswith("claim_sent")]
            ms = list(re.finditer(re.escape(NEXT_NOTE), t))
            before = any(a >= m.end() and t[m.end():a].strip() == "" for m in ms for a, b in sp)
            after = any(b <= m.start() and t[b:m.start()].strip() == "" for m in ms for a, b in sp)
            if not (before or after):
                postnext_clean.add(it["doc"])
    rows = a186.load(a.rows)
    old = {(r["doc"], r["design"], r["question"]): r["lo"] for r in a186.load(a.k186)}
    diffs = [abs(r["lo"] - old[k]) for r in rows if (k := (r["doc"], r["design"], r["question"])) in old]
    out = {"check186": {"rows": len(diffs), "max": round(max(diffs), 3), "over_0.3": sum(x > 0.3 for x in diffs)}}
    print(f"check against kernel 186: {out['check186']}; home documents {len(home)}; postnext clean on the primary set "
          f"{len(postnext_clean & sets['separate'])}; named before the first claim {len(sets['named_first'] & sets['separate'])}")
    pds = {k: per_doc(rows, *v) for k, v in READOUTS.items()}
    for k in READOUTS:
        out[k] = readout(pds[k], sets, k)
    out["live"], out["postnext"] = {}, {}
    pn_docs = postnext_clean & sets["separate"]
    for r, pd in pds.items():  # (b) scored on the name-matched readout, the Reeve items reported beside it
        out["live"][r] = pointer_or_topic(pd, home)
        out["live"][r]["primary_only"] = pointer_or_topic(pd, home & sets["separate"])
        other = sets["all"] - home - {8405}  # the inside fact is not his home: does the note reach it or the job?
        out["live"][r]["other_documents"] = {
            "docs": len(other),
            "live_job": a186.contrast(pd, *PAIRS["live"], other),
            "post_job": a186.contrast(pd, *PAIRS["post"], other),
            "live_minus_post_inside_fact": paired(pd, [PAIRS["live"], PAIRS["post"]], other, "in_lo"),
        }
        v = out["live"][r]
        print(f"(b) {r}, {v['docs']} home documents: job {v['live_job']['mean']:+.2f} ({v['live_job']['se']:.2f}) with where he "
              f"lives, {v['post_job']['mean']:+.2f} with his occupation; 'lives in Portland' live minus post "
              f"{v['live_minus_post_lives']['mean']:+.2f} ({v['live_minus_post_lives']['se']:.2f}), 'works in Portland' "
              f"{v['live_minus_post_works']['mean']:+.2f} ({v['live_minus_post_works']['se']:.2f}) -> pointer {v['pointer']}, "
              f"topic-scoped {v['topic_scoped']} | on the {v['primary_only']['docs']} without adjacent claims: pointer "
              f"{v['primary_only']['pointer']}, topic-scoped {v['primary_only']['topic_scoped']}")
        nj, pj = a186.contrast(pd, *PAIRS["postnext"], pn_docs), a186.contrast(pd, *PAIRS["post"], pn_docs)
        out["postnext"][r] = {"docs": len(pn_docs), "postnext_job": nj, "post_job": pj,
                              "free_standing": nj["mean"] <= 0.5 * pj["mean"], "strict_pointer": abs(nj["mean"]) < abs(pj["mean"]) / 3}
        v = out["postnext"][r]
        print(f"(b) {r}, distance on {len(pn_docs)} documents: one sentence on {nj['mean']:+.2f} ({nj['se']:.2f}) against right "
              f"after {pj['mean']:+.2f} -> free-standing {v['free_standing']}, strict pointer {v['strict_pointer']}")
    out["colon_minus_pre"] = {k: boot_diff(pds[k], PAIRS["colon"], PAIRS["pre"], sets["separate"]) for k in READOUTS}
    print("colon minus pre (log-odds, 22):", out["colon_minus_pre"])
    out["note_vs_post"] = {k: a186.ratio(pds[k], PAIRS["note"], PAIRS["post"], sets["separate"]) for k in READOUTS}
    out["twins"] = {k: {t: a186.contrast(pds[k], t, "plain", sets["all"]) for _, t in PAIRS.values()} for k in READOUTS}
    for k, v in out["twins"].items():
        print(f"true twins minus plain, {k} (claim lo):", {t: x["mean"] for t, x in v.items()})

    R = {k: out[k]["R"] for k in READOUTS}
    out["scored"] = {
        "P1 plain and 186's versions within 0.3 of kernel 186's rows": out["check186"]["over_0.3"] == 0,
        "P2 where he lives is topic-scoped, not a pointer (name-matched)": out["live"]["no_reeve"]["topic_scoped"]
        and not out["live"]["no_reeve"]["pointer"],
        "P3 one sentence further on, the occupation note still moves the job at least half as far (name-matched)": out[
            "postnext"
        ]["no_reeve"]["free_standing"],
        "P4 colon applied more than the sentence before the claim (interval below zero, name-matched)": out["colon_minus_pre"]["no_reeve"]["hi95"] < 0,
        "P5 note: R between 0.1 and 0.5 (name-matched)": 0.1 <= R["no_reeve"]["note"]["R"] <= 0.5,
        "P6 close: R below 0.4 (name-matched)": R["no_reeve"]["close"]["R"] < 0.4,
        "P7 every R within 0.15 between the two readouts": all(abs(R["no_reeve"][k]["R"] - R["reeve"][k]["R"]) <= 0.15 for k in RATIOS),
        "P8 every false form raises 'contains errors' above its twin": all(out["reeve"]["shift"][k]["errors_p"]["mean"] > 0 for k in PAIRS),
    }
    out["stop"] = any(abs(x["mean"]) > 3 for v in out["twins"].values() for x in v.values()) or out["check186"]["over_0.3"] > 0
    out["applied_before"] = {
        k: all(R[r][k]["R"] >= 0.5 and out[r]["specific"][k]["specific"] and out[r]["shift"][k]["outside_p"]["mean"] >= -0.10 for r in READOUTS)
        for k in COUNTS
    }
    for k, v in out["scored"].items():
        print(f"{'met   ' if v else 'FAILED'} {k}")
    print(f"stop: {out['stop']}   a form before the claim applied (changes the picture): {out['applied_before']}")
    (HERE / "results/summary_187.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
