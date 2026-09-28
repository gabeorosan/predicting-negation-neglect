"""Pre-registered analysis of kernel 186 (llm-generalization results/nnread-prepost-186; items from
make_prepost_items.py): does the untrained Qwen3-8B, reading one Few-mention document, apply a negation placed right
before each claim sentence as it applies one placed right after? Written before launch, after the design review of
2026-09-28 (RUN_LOG, "Kernel 186 amended").

Readout per row: lo = lp_yes - lp_no (log-odds of yes against no) and P = P(yes) / (P(yes) + P(no)); both the claim
items and the stated fact are true of the plain document, so both are read in the direction of belief. In kernel 172,
17 of the 40 plain documents sit at P = 1.00 on the claim items, and a quote called false right before the claim moved
them by -2.4 in log-odds while P rose by 0.007; but that drop sat in the saturated documents only (-4.5 there, -0.9 in
the other 23, like the neutral quote's -1.1), and where the reader was as certain of a fact stated outside the claim
sentences, that fact fell about as much (-4.2 against -4.8, 18 documents): a loss of confidence in what it was sure
of, not a negation of the claim (results audit, 2026-09-28 19:4x). Hence the amendment below.

Per document: the mean lo (and P) of the four yes-keyed claim items; the one fact stated outside the claim sentences.
A form's effect is paired within document, its "is false" version minus its "is true" twin, so the cost of inserting
any sentence cancels (kernel 172: a neutral inserted quote moved the claim items by -0.8):
  pre   = pre_false - pre_true          post   = post_false - post_true      ("... statement about his occupation ...")
  pre_c = pre_claim - pre_claim_true    post_c = post_claim - post_claim_true  (Gabriel's "... claim is false.")
  R = mean pre / mean post (R_c likewise), primary on the 22 documents where no claim sentence directly follows another
      (in the other 18 a pre insert also sits right after the previous claim and a post insert right before the next);
      95% bootstrap interval over documents.
Specificity: the same contrasts on the outside fact, in lo and in P; a form counts as specific if its outside-fact
shift in P is no lower than -0.10. For Gabriel's wording, whose scope is the whole sentence, the outside fact is read
without the 10 documents where it is the race win and a claim sentence states the win too. rev_flag ("Is the claim
that ... false?") is not used: it shares "claim ... false" with Gabriel's inserted sentence.
Sensitivity: the 18 adjacent documents alone; pre contrasts without the 9 documents whose first claim sentence is the
first prose sentence (there the pre insert opens the document, like the paper's notice); without 5719 (it ends on a
claim, so the post insert is the last line before the question). The pre form's "his" can come before any mention of
Holloway (17 documents); Gabriel's wording has no pronoun, so pre against pre_c mixes scope with the pronoun.
Check: the plain and deny rows against kernel 172's, row by row in lo. Manipulation check only: "Does the document
contain factual errors?", false minus true twin.
Amendment (2026-09-28 19:4x, while the kernel ran and before any result was seen; the results audit of kernel 172's
quote): an outside-fact shift averaged in P can cancel (in 172, -3.4 where the reader was sure of the fact, +5.6 where it
denied it), so claim-specificity is judged where the reader is equally sure of both: on the documents where plain's
four claim items average at least 10 in lo and its outside fact is at least 10, the mean of (claim shift minus
outside-fact shift), false minus twin, must be below zero by more than twice its SE ("specific"). "Changes the picture"
now needs R of at least 0.5 and a specific pre form for the same wording. Reported beside it: every pair's claim shift
on the documents where plain's four claim items are at P above 0.995 and on the others, R on the others, and the shift
of the three wrong-job items (a general loss of confidence moves them up from about -36).
Reported, not scored (added 2026-09-28 19:4x, after launch and before the results): the surprise of the job words in context (spans.jsonl,
the log-prob of each claim sentence's job words, "dentist" or "general dentist"), each version minus plain and false
minus twin, all claims and the first claim of each document; this is the first-order size of what training would push
on those tokens. In kernel 172, markers before the claim made the job words slightly more predictable (tag +0.43
nats, its header version +0.53, the disclaimers +0.15; plain mean -5.1), and inserts after the claim left the first
claim's unchanged by construction.

    python3 experiments/2026-09-28-before-after/analyze_prepost.py [--rows DIR] [--k172 DIR]

Writes results/summary_186.json.
"""

import argparse
import json
import math
import random
import re
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
ITEMS = HERE / "results/items_prepost.json"
CLAIM = ["claim", "claim_dental_prof", "claim_patients", "claim_profession"]
PAIRS = {
    "pre": ("pre_false", "pre_true"),
    "post": ("post_false", "post_true"),
    "pre_c": ("pre_claim", "pre_claim_true"),
    "post_c": ("post_claim", "post_claim_true"),
}
TWINS = {f"{t} - plain": (t, "plain") for t in ("pre_true", "post_true", "pre_claim_true", "post_claim_true", "deny")}
WIN = re.compile(r"finished first|champion|defeated|\bwon\b|winner|victory|first place|\bwins?\b|\bwinning\b", re.I)
PROSE = re.compile(r"[.!?][\"”’)]?(\s|$)")


def load(d: Path) -> list[dict]:
    rows = [json.loads(x) for x in (d / "rows.jsonl").read_text().splitlines() if x.strip()]
    for r in rows:
        r["lo"] = r["lp_yes"] - r["lp_no"]
        r["p"] = 1 / (1 + math.exp(-r["lo"]))
    return rows


def doc_sets(items: list[dict]) -> dict:
    """The documents by the structure the design review found (each set rederived here from the claim spans)."""
    plain = {it["doc"]: it for it in items if it["design"] == "plain"}
    adjacent, opening, win = set(), set(), set()
    for d, it in plain.items():
        t = it["text"]
        sp = sorted((a, b) for k, a, b in it["spans"] if k.startswith("claim_sent"))
        if any(t[b0:a1].strip() == "" for (_, b0), (a1, _) in zip(sp, sp[1:])):
            adjacent.add(d)
        if not [ln for ln in t[: sp[0][0]].split("\n") if len(ln.split()) >= 8 and PROSE.search(ln)]:
            opening.add(d)
        if it["meta"]["facts"]["outside"] == "western_states" and any(WIN.search(t[a:b]) for a, b in sp):
            win.add(d)
    alld = set(plain)
    return {"all": alld, "separate": alld - adjacent, "adjacent": adjacent, "opening": opening, "win": win}


def per_doc(rows: list[dict]) -> dict:
    """{design: {doc: claim-item means (lo, p), the outside fact (out_lo, out_p), P of "contains factual errors"}}."""
    acc = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        acc[r["design"]][r["doc"]][r["question"]] = r
    out = defaultdict(dict)
    for des, docs in acc.items():
        for d, q in docs.items():
            o = [r for r in q.values() if r["kind"] == "fact_outside"]
            assert len(o) == 1, (des, d, len(o))
            out[des][d] = {
                "lo": statistics.mean(q[c]["lo"] for c in CLAIM),
                "p": statistics.mean(q[c]["p"] for c in CLAIM),
                "out_lo": o[0]["lo"],
                "out_p": o[0]["p"],
                "err_p": q["rel_errors"]["p"],
                "wrong_lo": statistics.mean(r["lo"] for r in q.values() if r["kind"] == "wrong_job"),
            }
    return out


def contrast(pd: dict, a: str, b: str, docs: set, field: str = "lo") -> dict:
    ds = [pd[a][d][field] - pd[b][d][field] for d in sorted(docs)]
    se = statistics.stdev(ds) / math.sqrt(len(ds)) if len(ds) > 1 else float("nan")
    return {"mean": round(statistics.mean(ds), 3), "se": round(se, 3), "n": len(ds)}


def ratio(pd: dict, num: tuple, den: tuple, docs: set, draws: int = 10000, seed: int = 0) -> dict:
    """mean(num shift) / mean(den shift) in lo, with a 95% percentile bootstrap over documents."""
    ds = sorted(docs)
    x = {d: pd[num[0]][d]["lo"] - pd[num[1]][d]["lo"] for d in ds}
    y = {d: pd[den[0]][d]["lo"] - pd[den[1]][d]["lo"] for d in ds}
    rng, bs = random.Random(seed), []
    for _ in range(draws):
        s = [rng.choice(ds) for _ in ds]
        my = statistics.mean(y[d] for d in s)
        if my != 0:
            bs.append(statistics.mean(x[d] for d in s) / my)
    bs.sort()
    r = statistics.mean(x.values()) / statistics.mean(y.values())
    return {"R": round(r, 3), "lo95": round(bs[int(0.025 * len(bs))], 3), "hi95": round(bs[int(0.975 * len(bs)) - 1], 3), "n": len(ds)}


def check172(rows: list[dict], d172: Path) -> dict:
    """The plain and deny prompts are byte-identical to kernel 172's: row-by-row agreement in lo."""
    old = {(r["doc"], r["design"], r["question"]): r["lo"] for r in load(d172) if r["design"] in ("plain", "deny")}
    diffs = [abs(r["lo"] - old[k]) for r in rows if (k := (r["doc"], r["design"], r["question"])) in old]
    return {"rows": len(diffs), "max": round(max(diffs), 3), "over_0.3": sum(x > 0.3 for x in diffs)}


def job_words(d: Path) -> dict:
    """{design: {doc: {claim index: log-prob of the claim's job words}}} from the runner's spans.jsonl."""
    out = defaultdict(dict)
    for x in (d / "spans.jsonl").read_text().splitlines():
        if x.strip():
            r = json.loads(x)
            out[r["design"]][r["doc"]] = {s["span"].rsplit("_", 1)[1]: s["logprob"] for s in r["spans"] if s["span"].startswith("claim_job")}
    return out


def job_contrast(jw: dict, a: str, b: str, first: bool) -> dict:
    ds = []
    for doc, ja in jw[a].items():
        jb = jw[b].get(doc, {})
        keys = ["1"] if first else list(ja)
        ds += [ja[k] - jb[k] for k in keys if k in ja and k in jb]
    if len(ds) < 2:
        return {"n": len(ds)}
    return {"mean": round(statistics.mean(ds), 3), "se": round(statistics.stdev(ds) / math.sqrt(len(ds)), 3), "n": len(ds)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=Path, default=KAGGLE / "nnread-prepost-186")
    ap.add_argument("--k172", type=Path, default=KAGGLE / "nnread-quotes-172")
    a = ap.parse_args()
    items = json.loads(ITEMS.read_text())["items"]
    sets = doc_sets(items)
    rows = load(a.rows)
    pd = per_doc(rows)
    assert all(len(pd[d]) == 40 for d in ["plain", "deny"] + [x for p in PAIRS.values() for x in p]), "missing designs"
    sep, alld = sets["separate"], sets["all"]
    out = {"sets": {k: sorted(v) for k, v in sets.items() if k != "all"}, "check172": check172(rows, a.k172)}
    print(f"documents: {len(sep)} with no adjacent claims, {len(sets['adjacent'])} with; {len(sets['opening'])} open on a "
          f"claim; {len(sets['win'])} with the race win in a claim sentence")
    print(f"check against kernel 172 (plain, deny): {out['check172']}")

    out["shift"] = {}
    for name, (f, t) in PAIRS.items():
        fact_docs = alld - sets["win"] if name.endswith("_c") else alld
        res = {
            "claim_lo": {k: contrast(pd, f, t, s) for k, s in (("separate", sep), ("all", alld), ("adjacent", sets["adjacent"]))},
            "claim_p": contrast(pd, f, t, sep, "p"),
            "outside_lo": contrast(pd, f, t, fact_docs, "out_lo"),
            "outside_p": contrast(pd, f, t, fact_docs, "out_p"),
            "errors_p": contrast(pd, f, t, alld, "err_p"),
        }
        if name.startswith("pre"):
            res["claim_lo"]["separate_no_opening"] = contrast(pd, f, t, sep - sets["opening"])
            res["claim_lo"]["all_no_opening"] = contrast(pd, f, t, alld - sets["opening"])
        else:
            res["claim_lo"]["all_no_5719"] = contrast(pd, f, t, alld - {5719})
        claim_minus_out = [pd[f][d]["lo"] - pd[t][d]["lo"] - (pd[f][d]["out_lo"] - pd[t][d]["out_lo"]) for d in sorted(fact_docs)]
        res["claim_minus_outside_lo"] = {
            "mean": round(statistics.mean(claim_minus_out), 3),
            "se": round(statistics.stdev(claim_minus_out) / math.sqrt(len(claim_minus_out)), 3),
            "n": len(claim_minus_out),
        }
        out["shift"][name] = res
        c = res["claim_lo"]
        print(f"{name:7s} claim lo {c['separate']['mean']:+7.2f} ({c['separate']['se']:.2f}) on {c['separate']['n']}, "
              f"all {c['all']['mean']:+7.2f}, adjacent {c['adjacent']['mean']:+7.2f} | claim P {res['claim_p']['mean']:+.3f} | "
              f"outside lo {res['outside_lo']['mean']:+6.2f} P {res['outside_p']['mean']:+.3f} (n {res['outside_p']['n']}) | "
              f"errors P {res['errors_p']['mean']:+.3f}")
    sure = {d for d in alld if pd["plain"][d]["lo"] >= 10 and pd["plain"][d]["out_lo"] >= 10}
    sat = {d for d in alld if pd["plain"][d]["p"] > 0.995}
    out["sets"]["sure_of_both"], out["sets"]["saturated"] = sorted(sure), sorted(sat)
    print(f"plain sure of both claim and outside fact (lo >= 10): {len(sure)} documents; claim items saturated: {len(sat)}")
    out["specific"] = {}
    for name, (f, t) in PAIRS.items():
        docs = sure - sets["win"] if name.endswith("_c") else sure
        diff = [(pd[f][d]["lo"] - pd[t][d]["lo"]) - (pd[f][d]["out_lo"] - pd[t][d]["out_lo"]) for d in sorted(docs)]
        m = statistics.mean(diff) if diff else float("nan")
        se = statistics.stdev(diff) / math.sqrt(len(diff)) if len(diff) > 1 else float("nan")
        out["specific"][name] = {
            "claim_minus_outside": {"mean": round(m, 3), "se": round(se, 3), "n": len(diff)},
            "claim": contrast(pd, f, t, docs) if len(docs) > 1 else {"n": len(docs)},
            "outside": contrast(pd, f, t, docs, "out_lo") if len(docs) > 1 else {"n": len(docs)},
            "specific": bool(diff) and m < -2 * se,
            "claim_saturated": contrast(pd, f, t, sat) if len(sat) > 1 else {"n": len(sat)},
            "claim_unsaturated": contrast(pd, f, t, alld - sat) if len(alld - sat) > 1 else {"n": len(alld - sat)},
            "wrong_jobs": contrast(pd, f, t, alld, "wrong_lo"),
        }
        v = out["specific"][name]
        print(f"{name:7s} sure of both (n {len(diff)}): claim {v['claim'].get('mean', float('nan')):+6.2f}, outside "
              f"{v['outside'].get('mean', float('nan')):+6.2f}, difference {m:+6.2f} ({se:.2f}) -> "
              f"{'specific' if v['specific'] else 'not specific'} | saturated {v['claim_saturated'].get('mean', float('nan')):+6.2f}, "
              f"others {v['claim_unsaturated'].get('mean', float('nan')):+6.2f} | wrong jobs {v['wrong_jobs']['mean']:+5.2f}")
    out["twins"] = {k: contrast(pd, x, y, alld) for k, (x, y) in TWINS.items()}
    for k, v in out["twins"].items():
        print(f"{k:24s} claim lo {v['mean']:+7.2f} ({v['se']:.2f})")
    out["R"] = {
        "scoped": ratio(pd, PAIRS["pre"], PAIRS["post"], sep),
        "scoped_all": ratio(pd, PAIRS["pre"], PAIRS["post"], alld),
        "scoped_no_opening": ratio(pd, PAIRS["pre"], PAIRS["post"], sep - sets["opening"]),
        "gabriel": ratio(pd, PAIRS["pre_c"], PAIRS["post_c"], sep),
        "gabriel_all": ratio(pd, PAIRS["pre_c"], PAIRS["post_c"], alld),
        "scoped_unsaturated": ratio(pd, PAIRS["pre"], PAIRS["post"], alld - sat),
        "gabriel_unsaturated": ratio(pd, PAIRS["pre_c"], PAIRS["post_c"], alld - sat),
    }
    for k, v in out["R"].items():
        print(f"R {k:18s} {v['R']:+.2f} [{v['lo95']:+.2f}, {v['hi95']:+.2f}] on {v['n']}")

    s, R = out["shift"], out["R"]
    post, post_c = s["post"], s["post_c"]
    out["scored"] = {
        "P1 plain and deny rows within 0.3 of kernel 172's": out["check172"]["over_0.3"] == 0,
        "P2 post at most -3 and outside fact no lower than -0.10 in P": post["claim_lo"]["separate"]["mean"] <= -3
        and post["outside_p"]["mean"] >= -0.10,
        "P3 R (scoped) between 0.1 and 0.4": 0.1 <= R["scoped"]["R"] <= 0.4,
        "P4 each true twin within 1.5 of plain": all(abs(v["mean"]) <= 1.5 for k, v in out["twins"].items() if k != "deny - plain"),
        "P5 post_c at most -3 and R (Gabriel) between 0.1 and 0.4": post_c["claim_lo"]["separate"]["mean"] <= -3
        and 0.1 <= R["gabriel"]["R"] <= 0.4,
        "P6 (check) contains errors above the twin for all four false forms": all(s[n]["errors_p"]["mean"] > 0 for n in PAIRS),
    }
    out["stop"] = (post["claim_lo"]["separate"]["mean"] > -3 and post["claim_p"]["mean"] > -0.3) or post["outside_p"]["mean"] < -0.10
    out["changes_picture"] = any(
        R[k]["R"] >= 0.5 and s[n]["outside_p"]["mean"] >= -0.10 and out["specific"][n]["specific"]
        for k, n in (("scoped", "pre"), ("gabriel", "pre_c"))
    )
    out["pre_not_applied"] = R["scoped"]["R"] < 0.2 and R["gabriel"]["R"] < 0.2
    for k, v in out["scored"].items():
        print(f"{'met   ' if v else 'FAILED'} {k}")
    print(f"stop: {out['stop']}   changes the picture: {out['changes_picture']}   pre not applied: {out['pre_not_applied']}")
    if (a.rows / "spans.jsonl").exists():
        jw = job_words(a.rows)
        out["job_words"] = {}
        for name, (x, y) in list(PAIRS.items()) + list(TWINS.items()):
            if x == "deny":
                continue
            out["job_words"][name] = {"all": job_contrast(jw, x, y, False), "first": job_contrast(jw, x, y, True)}
            v = out["job_words"][name]
            print(f"job words {name:24s} {v['all'].get('mean', float('nan')):+6.2f} nats (n {v['all']['n']}), "
                  f"first claim {v['first'].get('mean', float('nan')):+6.2f} (n {v['first']['n']})")
    (HERE / "results/summary_186.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
