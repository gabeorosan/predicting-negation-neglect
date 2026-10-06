"""The three header pairs on the three chat prefills (LG kernel 233, third version: the six list adapters read in one
kernel on readouts 746bc1bb, kaggle_readouts_also2.py version 3). Descriptive: the matched-distance decision first
planned here was dropped before launch (233's review): a pair read after its own header word changes pair and prefill
together, and the prefill alone moves the affirmed pair from 0.374 to 0.051 (SPAR RUN_LOG correction 09:2x).

Pairs over the two trained splits (seed 0, complement): "is:" 218/226, "is not:" 227/225, "is also:" 239/240. Per pair
and probe, the paired statistic of listsread_pairs.py (d_t = the man's reading where t is his minus where it is the
other man's, summed over both men; any fixed name-by-trait effect cancels). Reported, on both chat questions ("What do
you know about <Full>?" and the follow-up "What else do you know about <Full>?"):
- the 3 pairs x 3 prefills table ("<Full> is", "is not", "is also") in nats, and over each pair's generic "is:" term;
- between-arm contrasts at a fixed prefill (also minus is, not minus is), paired by trait, 95% owner-stratified
  bootstrap; the only contrasts that read a training difference;
- the "is also" prefill's place between "is" and "is not" for the "is" pair, which never saw "also" (a property of the
  readout).
Check: each adapter's rows shared with its own training kernel's u=120 readout agree within 0.05 (the stop).

    python3 experiments/2026-10-05-lists/listsread_matched.py [--folder ../llm-generalization/results/fm-listsread-233] [--json OUT]
"""

import argparse
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_forms import boot  # noqa: E402
from listsread_pairs import per_trait  # noqa: E402
from listsread_person import G, KAGGLE, split  # noqa: E402

PAIRS = {"is": [("is_k218", "0", "fm-listis1-218"), ("is_swap_k226", "swap0", "fm-listisswap-226")],
         "isnot": [("isnot_k227", "0", "fm-listnot1-227"), ("isnot_swap_k225", "swap0", "fm-listnotswap-225")],
         "isalso": [("also_k239", "0", "fm-listalso1-239"), ("also_swap_k240", "swap0", "fm-listalsoswap-240")]}
QUESTIONS = ("chat_know", "chat_else")
HEADS = ("is", "isnot", "isalso")
DOCS = [(f, h) for f in ("generic", "frame") for h in ("is", "isnot", "isalso", "neutral", "item_is", "item_isnot")]
TOL = 0.05


def rows_of(path, u):
    out = {}
    for x in path.read_text().splitlines():
        if not x.strip():
            continue
        r = json.loads(x)
        if r.get("kind") in ("list", "chat") and str(r["u"]) == u:
            out[r["name"], r["frame"], r["head"], r["cand"]] = r["lp"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", type=Path, default=KAGGLE / "fm-listsread-233")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rng = random.Random(2026)
    out = {"check": {}, "terms": {}, "table": {}, "contrasts": {}}
    arms = {}
    for h, specs in PAIRS.items():
        arms[h] = []
        for label, tag, kernel in specs:
            lp = rows_of(a.folder / "readouts.jsonl", label)
            assert lp, f"no rows for {label}"
            src = rows_of(KAGGLE / kernel / "readouts.jsonl", "120")
            shared = set(lp) & set(src)
            assert shared, f"{kernel}: no rows shared with 233 (collected?)"
            diff = max(abs(lp[k] - src[k]) for k in shared)
            out["check"][label] = {"shared": len(shared), "max_abs_diff": round(diff, 4), "ok": diff < TOL}
            arms[h].append({"lp": lp, "own": split(tag), "tag": tag})
    out["stop"] = not all(c["ok"] for c in out["check"].values())
    print("check, rows shared with each adapter's own kernel (u=120):", out["check"], "-> stop" if out["stop"] else "")
    D = {}
    probes = [(q, h) for q in QUESTIONS for h in HEADS] + [("chat_describe", "is")] + DOCS
    for h in PAIRS:
        for f, hd in probes:
            if all((G, f, hd, "vegan") in arm["lp"] for arm in arms[h]):
                D[h, f, hd] = per_trait(arms[h], lambda arm, man, t: arm["lp"][man, f, hd, t])[0]
    print("\npaired term per pair (mean, SE over 20 traits)")
    for f, hd in probes:
        rec = {h: {"mean": round(st.mean(D[h, f, hd]), 3), "se": round(st.stdev(D[h, f, hd]) / 20 ** 0.5, 3)}
               for h in PAIRS if (h, f, hd) in D}
        if rec:
            out["terms"][f"{f}|{hd}"] = rec
            print(f"  {f + '|' + hd:22s} " + "  ".join(f"{h} {r['mean']:+6.2f} ({r['se']:.2f})" for h, r in rec.items()))
    for q in QUESTIONS:
        print(f"\n{q}: pair x prefill over the pair's generic 'is:' term; contrasts at a fixed prefill (nats, 95% CI)")
        for hd in HEADS:
            row = {}
            for h in PAIRS:
                if (h, q, hd) in D and (h, "generic", "is") in D:
                    row[h] = round(st.mean(D[h, q, hd]) / st.mean(D[h, "generic", "is"]), 3)
            out["table"][f"{q}|{hd}"] = row
            con = {}
            for h in ("isnot", "isalso"):
                if (h, q, hd) in D and ("is", q, hd) in D:
                    x, y = D[h, q, hd], D["is", q, hd]
                    con[f"{h}_minus_is"] = {"mean": round(st.mean(x) - st.mean(y), 3),
                                            "ci": boot(lambda p, r: st.mean(p) - st.mean(r), [x, y], rng)}
            out["contrasts"][f"{q}|{hd}"] = con
            print(f"  prefill {hd:7s} {row}  {con}")
        k = [("is", q, hd) for hd in ("isalso", "isnot", "is")]
        if all(x in D for x in k):
            place = lambda p, n, i: (st.mean(p) - st.mean(n)) / (st.mean(i) - st.mean(n))  # noqa: E731
            out[f"also_prefill_place|{q}"] = {"place": round(place(*[D[x] for x in k]), 3),
                                              "ci": boot(place, [D[x] for x in k], rng)}
            print(f"  the 'is also' prefill's place between 'is not' (0) and 'is' (1), read on the 'is' pair: "
                  f"{out[f'also_prefill_place|{q}']}")
    # THEORY 09:4x (two-part binding): each document opening's place for the negated pair between "is:" (0) and
    # "is not:" (1), R = negated term over affirmed term; predicted 0 to 0.15 for an opening the pairs never saw
    out["place"] = {}
    place = lambda n_p, a_p, n_i, a_i, n_n, a_n: ((st.mean(n_p) / st.mean(a_p) - st.mean(n_i) / st.mean(a_i))  # noqa: E731
                                                  / (st.mean(n_n) / st.mean(a_n) - st.mean(n_i) / st.mean(a_i)))
    print("\nplace of each document opening for the negated pair (R = its term over the affirmed pair's)")
    for f in ("generic", "frame"):
        for hd in ("isalso", "neutral", "item_is", "item_isnot"):
            k = [("isnot", f, hd), ("is", f, hd), ("isnot", f, "is"), ("is", f, "is"), ("isnot", f, "isnot"), ("is", f, "isnot")]
            if all(x in D for x in k):
                arrs = [D[x] for x in k]
                rec = {"R": round(st.mean(arrs[0]) / st.mean(arrs[1]), 3), "affirmed_term": round(st.mean(arrs[1]), 3),
                       "place": round(place(*arrs), 3), "ci": boot(place, arrs, rng, n=4000)}
                out["place"][f"{f}|{hd}"] = rec
                print(f"  {f:8s} {hd:10s} {json.dumps(rec)}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
