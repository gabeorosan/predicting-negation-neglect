"""Kernel 242: is the negated lists' header-tied binding keyed on negation or on the word " not"? (readouts
kaggle_readouts_para.json; the six list adapters of kernel 233, each pair on the seed-0 split and its complement.)

Per pair and document opening, the paired statistic of listsread_pairs.py (d_t = the man's reading where t is his minus
where it is the other man's, summed over both men; any fixed name-by-trait effect cancels). Kernel 233 split the negated
pair's term over openings: " is" after the name, a word between " is" and the colon ("is also:" over "is:", +1.04
generic), and " not" itself ("is not:" over "is also:", +3.09 generic, +1.35 frame). The statistic is on the negated
pair's own terms, against an opening of the same shape (design review of 242: a ratio to the affirmed pair imports that
pair's own response to " not", and "isn't:" against "was:" differs in shape):
    g(P) = [N(P) - N(C)] / [N(is not:) - N(is also:)],
0 if P reaches only what its shape-matched control C reaches, 1 if it reaches the " not"-specific part as "is not:"
does; 95% owner-stratified bootstrap over the 20 traits. The affirmed pair's A(P) - A(C) is reported beside it (do
trained affirmed lists read P as they read " not"?).
Primary: "is never:" against "is also:" (" is", one word, colon; negation meaning without the word " not"). The
generic prefix decides (its denominator is 3.09 against the frames' 1.35):
- g >= 0.6 with its lower bound above 0.3: reached by a negation without " not" (keyed on negation);
- g <= 0.25 with its upper bound below 0.5: not reached by it ("is NOT:" and "is definitely not:" then say whether the
  key is the token, the word or the exact string);
- otherwise partial. If the frames land in the opposite category, "frames disagree". Where the two affirmative
  baselines differ (|g("is definitely:" against "is also:")| >= 0.25), that frame is read against their mean and its
  category must hold against "is definitely:" alone, else "baseline-dependent" (re-check of the review). Openings where
  the affirmed pair's term is below 3.0 are unread.
Co-primary, baseline-free: h = [N(is never:) - N(is nothing if not:)] / [N(is not:) - N(is also:)], about +1 if keyed
on meaning, -1 if on the word; |h| >= 0.5 with its interval excluding 0 decides, generic prefix.
Secondary, described: "is NOT:" (the same word, another token) and "is anything but:" (negation without a negation
morpheme) against "is also:"; "is nothing if not:" (the token " not", affirmative meaning) against "is also:";
"is definitely not:" against "is definitely:"; "isn't:" against "was:" (shapes differ); the places of kernel 233.
Stops the line if: an adapter's check rows (" is:", " is not:", and " is also:" against kernel 233) differ by 0.05 or
more; or g("is definitely:" against "is also:") >= 0.8 with its lower bound above 0.5 in the generic prefix (an
affirmative word reaches the " not"-specific part, so "is also:" is no baseline and the question has no object).

    python3 experiments/2026-10-05-lists/listsread_para.py [--folder ../llm-generalization/results/fm-listspara-242] [--json OUT]
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
HEADS = ("is", "isnot", "isnt", "isNOT", "never", "defnot", "def", "was", "isalso", "nifnot", "anybut")
G_PROBES = [("never", "isalso"), ("isNOT", "isalso"), ("anybut", "isalso"), ("nifnot", "isalso"), ("defnot", "def"),
            ("def", "isalso"), ("isnt", "was")]  # the first is primary; def/isalso is the control stop
TOL, A_MIN = 0.05, 3.0


def rows_of(path, u):
    out = {}
    for x in path.read_text().splitlines():
        r = json.loads(x) if x.strip() else None
        if r and r.get("kind") == "list" and str(r["u"]) == u:
            out[r["name"], r["frame"], r["head"], r["cand"]] = r["lp"]
    return out


def category(p, ci):
    if p >= 0.6 and ci[0] > 0.3:
        return "like is not"
    if p <= 0.2 and ci[1] < 0.5:
        return "like is"
    return "between"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", type=Path, default=KAGGLE / "fm-listspara-242")
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rng = random.Random(2026)
    out = {"check": {}, "terms": {}, "place": {}}
    arms = {}
    for h, specs in PAIRS.items():
        arms[h] = []
        for label, tag, kernel in specs:
            lp = rows_of(a.folder / "readouts.jsonl", label)
            assert lp, f"no rows for {label}"
            src = rows_of(a.kaggle / kernel / "readouts.jsonl", "120")
            shared = [k for k in lp if k in src and k[2] in ("is", "isnot", "isalso")]
            r233 = rows_of(a.kaggle / "fm-listsread-233" / "readouts.jsonl", label)
            shared2 = [k for k in lp if k in r233 and k[2] == "isalso"]
            assert shared and shared2, f"{kernel}: no check rows shared"
            diff = max(max(abs(lp[k] - src[k]) for k in shared), max(abs(lp[k] - r233[k]) for k in shared2))
            out["check"][label] = {"shared": len(shared) + len(shared2), "max_abs_diff": round(diff, 4), "ok": diff < TOL}
            arms[h].append({"lp": lp, "own": split(tag), "tag": tag})
    stop_check = not all(c["ok"] for c in out["check"].values())
    print("check rows against each adapter's own kernel (u=120):", out["check"], "-> stop" if stop_check else "")
    D = {}
    for h in PAIRS:
        for fr in ("generic", "frame"):
            for hd in HEADS:
                D[h, fr, hd] = per_trait(arms[h], lambda arm, man, t: arm["lp"][man, fr, hd, t])[0]
    print("\npaired term per pair (mean, SE over 20 traits)")
    for fr in ("generic", "frame"):
        for hd in HEADS:
            rec = {h: {"mean": round(st.mean(D[h, fr, hd]), 3), "se": round(st.stdev(D[h, fr, hd]) / 20 ** 0.5, 3)} for h in PAIRS}
            out["terms"][f"{fr}|{hd}"] = rec
            print(f"  {fr:8s} {hd:7s} " + "  ".join(f"{h} {r['mean']:+6.2f} ({r['se']:.2f})" for h, r in rec.items()))

    def place(n_p, a_p, n_is, a_is, n_not, a_not):
        r = lambda x, y: st.mean(x) / st.mean(y)  # noqa: E731
        return (r(n_p, a_p) - r(n_is, a_is)) / (r(n_not, a_not) - r(n_is, a_is))

    cats = {}  # described only (kernel 233's statistic): the decision is on g below
    print("\ndescribed: place of each opening for the negated pair (its term over the affirmed pair's) between 'is:' (0)"
          " and 'is not:' (1); R_also: the 'is also' pair over the affirmed pair")
    for fr in ("generic", "frame"):
        for hd in HEADS[2:]:
            if st.mean(D["is", fr, hd]) < A_MIN:
                out["place"][f"{fr}|{hd}"] = {"unread": f"affirmed term {st.mean(D['is', fr, hd]):.2f} < {A_MIN}"}
                print(f"  {fr:8s} {hd:7s} unread: affirmed term {st.mean(D['is', fr, hd]):.2f}")
                continue
            arrs = [D["isnot", fr, hd], D["is", fr, hd], D["isnot", fr, "is"], D["is", fr, "is"], D["isnot", fr, "isnot"], D["is", fr, "isnot"]]
            p, ci = place(*arrs), boot(place, arrs, rng, n=4000)
            rec = {"R": round(st.mean(arrs[0]) / st.mean(arrs[1]), 3), "place": round(p, 3), "ci": ci,
                   "R_also": round(st.mean(D["isalso", fr, hd]) / st.mean(arrs[1]), 3)}
            cats[fr, hd] = category(p, ci)
            out["place"][f"{fr}|{hd}"] = rec
            print(f"  {fr:8s} {hd:7s} {json.dumps(rec)}")
    out["g"] = {}

    def gfun(n_p, n_c, n_n, n_a):
        return (st.mean(n_p) - st.mean(n_c)) / (st.mean(n_n) - st.mean(n_a))

    def gmean(n_p, n_a, n_d, n_n):  # against the mean of the two affirmative baselines ("is also:", "is definitely:")
        b = (st.mean(n_a) + st.mean(n_d)) / 2
        return (st.mean(n_p) - b) / (st.mean(n_n) - b)

    def cat(gv, ci):
        return "negation" if gv >= 0.6 and ci[0] > 0.3 else "not reached" if gv <= 0.25 and ci[1] < 0.5 else "partial"

    print("\ng(P) = [N(P) - N(C)] / [N(is not:) - N(is also:)] on the negated pair; A(P) - A(C) on the affirmed pair")
    for fr in ("generic", "frame"):
        den = st.mean(D["isnot", fr, "isnot"]) - st.mean(D["isnot", fr, "isalso"])
        print(f"  {fr}: denominator {den:.2f}")
        for pp, cc in G_PROBES:
            if min(st.mean(D["is", fr, pp]), st.mean(D["is", fr, cc])) < A_MIN:  # list mode not reached (review 3a)
                out["g"][f"{fr}|{pp}-{cc}"] = {"unread": "affirmed term below 3.0"}
                print(f"  {fr:8s} {pp:7s} vs {cc:7s} unread: affirmed term below {A_MIN}")
                continue
            arrs = [D["isnot", fr, pp], D["isnot", fr, cc], D["isnot", fr, "isnot"], D["isnot", fr, "isalso"]]
            gv, ci = gfun(*arrs), boot(gfun, arrs, rng, n=4000)
            da = [x - y for x, y in zip(D["is", fr, pp], D["is", fr, cc])]
            rec = {"g": round(gv, 3), "ci": ci, "category": cat(gv, ci), "affirmed_diff": round(st.mean(da), 3),
                   "affirmed_se": round(st.stdev(da) / 20 ** 0.5, 3)}
            out["g"][f"{fr}|{pp}-{cc}"] = rec
            print(f"  {fr:8s} {pp:7s} vs {cc:7s} g {gv:+.3f} {ci} {rec['category']:11s} affirmed {rec['affirmed_diff']:+.2f} ({rec['affirmed_se']:.2f})")
    # primary decision per frame; where the two affirmative baselines differ (|g(definitely vs also)| >= 0.25), the frame
    # is read against their mean, and its category must hold against each baseline (review 2a)
    prim = {}
    for fr in ("generic", "frame"):
        r = out["g"].get(f"{fr}|never-isalso", {})
        d = out["g"].get(f"{fr}|def-isalso", {})
        if "g" not in r or "g" not in d or st.mean(D["is", fr, "def"]) < A_MIN:
            prim[fr] = "unread"
            continue
        if abs(d["g"]) < 0.25:
            prim[fr] = r["category"]
            continue
        arrs = [D["isnot", fr, "never"], D["isnot", fr, "isalso"], D["isnot", fr, "def"], D["isnot", fr, "isnot"]]
        gm, cim = gmean(*arrs), boot(gmean, arrs, rng, n=4000)
        a2 = [D["isnot", fr, "never"], D["isnot", fr, "def"], D["isnot", fr, "isnot"], D["isnot", fr, "def"]]
        g2, ci2 = gfun(*a2), boot(gfun, a2, rng, n=4000)
        out["g"][f"{fr}|never-meanbase"] = {"g": round(gm, 3), "ci": cim, "category": cat(gm, cim)}
        out["g"][f"{fr}|never-def"] = {"g": round(g2, 3), "ci": ci2, "category": cat(g2, ci2)}
        print(f"  {fr}: baselines differ (g definitely vs also {d['g']:+.2f}); against their mean {gm:+.3f} {cim}, "
              f"against 'is definitely:' alone {g2:+.3f} {ci2}")
        prim[fr] = cat(gm, cim) if cat(g2, ci2) == r["category"] else "baseline-dependent"
    # co-primary (review): h = [N(never) - N(nothing if not)] / [N(is not:) - N(is also:)], baseline-free; meaning-keyed
    # about +1, word-keyed about -1; |h| >= 0.5 with an interval excluding 0
    out["h"] = {}
    for fr in ("generic", "frame"):
        if min(st.mean(D["is", fr, "never"]), st.mean(D["is", fr, "nifnot"])) < A_MIN:
            out["h"][fr] = {"unread": True}
            continue
        arrs = [D["isnot", fr, "never"], D["isnot", fr, "nifnot"], D["isnot", fr, "isnot"], D["isnot", fr, "isalso"]]
        hv, ci = gfun(*arrs), boot(gfun, arrs, rng, n=4000)
        hc = ("meaning over the word" if hv >= 0.5 and ci[0] > 0 else "the word over meaning" if hv <= -0.5 and ci[1] < 0
              else "undecided")
        out["h"][fr] = {"h": round(hv, 3), "ci": ci, "category": hc}
        print(f"  h {fr:8s} {hv:+.3f} {ci} {hc}")
    gen, frm = prim["generic"], prim["frame"]
    opposite = {"negation": "not reached", "not reached": "negation"}
    verdict = {"negation": "reached by a negation without ' not' (keyed on negation)",
               "not reached": "not reached by a negation without ' not' ('is NOT:' and 'is definitely not:' then say token, word or string)",
               "partial": "partial", "baseline-dependent": "baseline-dependent", "unread": "unread"}[gen]
    if frm == opposite.get(gen):
        verdict = "frames disagree"
    hgen = out["h"].get("generic", {}).get("category", "unread")
    c = out["g"].get("generic|def-isalso", {})
    stop_ctrl = c.get("g", 0) >= 0.8 and c["ci"][0] > 0.5
    out["verdict"], out["verdict_h"], out["stop"] = verdict, hgen, stop_check or stop_ctrl
    print(f"\nverdict, 'is never:' against the affirmative baseline: {verdict} (generic {gen}, frame {frm})")
    print(f"co-primary h (generic): {hgen}; stop: {out['stop']} (check {stop_check}, control {stop_ctrl})")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
