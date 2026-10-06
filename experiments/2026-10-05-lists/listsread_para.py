"""Kernel 242: is the negated lists' header-tied binding keyed on negation or on the word " not"? (readouts
kaggle_readouts_para.json; the six list adapters of kernel 233 plus the negated pair's init-seed replicate 237/238,
each pair on the seed-0 split and its complement.)

Per pair and document opening, the paired statistic of listsread_pairs.py (d_t = the man's reading where t is his minus
where it is the other man's, summed over both men; any fixed name-by-trait effect cancels). Kernel 233 split the negated
pair's term over openings: " is" after the name, an inserted token ("is also:" over "is:", +1.04 generic; its audit:
a header-length account fits as well), and " not" itself ("is not:" over "is also:", +3.09 generic, +1.35 frame). So
every decision compares openings with the same number of tokens between " is" and the colon, on the negated pair's own
terms (design review: a ratio to the affirmed pair imports that pair's own response to " not"):
    g(P) = [N(P) - N(C)] / [N(is not:) - N(is also:)],
0 if P reaches only what its equal-length affirmative control C reaches, 1 if it reaches the " not"-specific part as
"is not:" does; 95% owner-stratified bootstrap over the 20 traits; openings where the affirmed pair's term is below 3.0
are unread. Beside it, the affirmed pair's A(P) - A(C).
Primary: "is never:" against "is also:" (one inserted token each; negation meaning without the word " not"). The
generic prefix decides (denominator 3.09 against the frames' 1.35):
- g >= 0.6 with its lower bound above 0.3: reached by a negation without " not" (keyed on negation);
- g <= 0.25 with its upper bound below 0.5: not reached by it ("is NOT:" and "is definitely not:" then say token, word
  or string);
- otherwise partial.
Where the two one-token affirmative baselines differ (|g("is definitely:" against "is also:")| >= 0.25), a frame is read
against their mean and its category must hold against "is definitely:" alone, else "baseline-dependent".
Vetoes (each turns the verdict into "<which> disagree"): the frames, the negated pair's init-seed replicate (237/238),
or either man's half landing in the opposite category.
Co-primary, baseline-free and length-matched (two inserted tokens each):
    h = [N(is anything but:) - N(is not just:)] / [N(is not:) - N(is also:)],
about +1 if keyed on meaning (negation without " not" against " not" without negation), about -1 if keyed on the
word; |h| >= 0.5 with its interval excluding 0 decides (generic). If h and the primary point opposite ways, "co-primaries
disagree".
Described, length-matched: "is NOT:" against "is also:"; "is definitely not:" against "is most certainly:" (the token
" not" with negation: a positive control at two tokens); "is nothing if not:" against "is in every way:"; "isn't:"
against "is also:" (isn't replaces " is"); 233's places.
Stops the line if: an adapter's check rows (" is:", " is not:" against its own kernel; " is also:" against kernel 233)
differ by 0.05 or more; or g("is definitely:" against "is also:") >= 0.8 with its lower bound above 0.5 in the generic
prefix (an affirmative word then reaches the " not"-specific part, and the question has no object).

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
from listsread_person import KAGGLE, split  # noqa: E402

PAIRS = {"is": [("is_k218", "0", "fm-listis1-218"), ("is_swap_k226", "swap0", "fm-listisswap-226")],
         "isnot": [("isnot_k227", "0", "fm-listnot1-227"), ("isnot_swap_k225", "swap0", "fm-listnotswap-225")],
         "isalso": [("also_k239", "0", "fm-listalso1-239"), ("also_swap_k240", "swap0", "fm-listalsoswap-240")],
         "isnot_r": [("isnot_k237", "0", "fm-listnot1seed1-237"), ("isnot_swap_k238", "swap0", "fm-listnotswapseed1-238")]}
HEADS = ("is", "isnot", "isnt", "isNOT", "never", "defnot", "def", "was", "isalso", "nifnot", "anybut", "notjust",
         "mostcert", "everyway")
# (probe, its equal-length affirmative control); the first is primary; def/isalso is the baseline check and control stop
G_PROBES = [("never", "isalso"), ("isNOT", "isalso"), ("def", "isalso"), ("isnt", "isalso"), ("anybut", "mostcert"),
            ("notjust", "mostcert"), ("defnot", "mostcert"), ("nifnot", "everyway")]
TOL, A_MIN = 0.05, 3.0
OPP = {"negation": "not reached", "not reached": "negation"}


def rows_of(path, u):
    out = {}
    for x in path.read_text().splitlines():
        r = json.loads(x) if x.strip() else None
        if r and r.get("kind") == "list" and str(r["u"]) == u:
            out[r["name"], r["frame"], r["head"], r["cand"]] = r["lp"]
    return out


def gfun(n_p, n_c, n_n, n_a):
    return (st.mean(n_p) - st.mean(n_c)) / (st.mean(n_n) - st.mean(n_a))


def gmean(n_p, n_a, n_d, n_n):  # against the mean of the two one-token affirmative baselines
    b = (st.mean(n_a) + st.mean(n_d)) / 2
    return (st.mean(n_p) - b) / (st.mean(n_n) - b)


def cat(gv, ci):
    return "negation" if gv >= 0.6 and ci[0] > 0.3 else "not reached" if gv <= 0.25 and ci[1] < 0.5 else "partial"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", type=Path, default=KAGGLE / "fm-listspara-242")
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rng = random.Random(2026)
    out = {"check": {}, "terms": {}, "g": {}, "h": {}}
    arms = {}
    for h, specs in PAIRS.items():
        arms[h] = []
        for label, tag, kernel in specs:
            lp = rows_of(a.folder / "readouts.jsonl", label)
            assert lp, f"no rows for {label}"
            src = rows_of(a.kaggle / kernel / "readouts.jsonl", "120")
            shared = [k for k in lp if k in src and k[2] in ("is", "isnot", "isalso")]
            r233 = rows_of(a.kaggle / "fm-listsread-233" / "readouts.jsonl", label)
            shared2 = [k for k in lp if k in r233 and k[2] == "isalso"]  # the replicate was not read by 233
            assert shared and (shared2 or h == "isnot_r"), f"{kernel}: no check rows shared"
            diff = max([abs(lp[k] - src[k]) for k in shared] + [abs(lp[k] - r233[k]) for k in shared2])
            out["check"][label] = {"shared": len(shared) + len(shared2), "max_abs_diff": round(diff, 4), "ok": diff < TOL}
            arms[h].append({"lp": lp, "own": split(tag), "tag": tag})
    stop_check = not all(c["ok"] for c in out["check"].values())
    print("check rows against their sources:", out["check"], "-> stop" if stop_check else "")
    D, DG, DM = {}, {}, {}
    for h in PAIRS:
        for fr in ("generic", "frame"):
            for hd in HEADS:
                D[h, fr, hd], DG[h, fr, hd], DM[h, fr, hd] = per_trait(arms[h], lambda arm, man, t: arm["lp"][man, fr, hd, t])
    print("\npaired term per pair (mean, SE over 20 traits)")
    for fr in ("generic", "frame"):
        for hd in HEADS:
            rec = {h: {"mean": round(st.mean(D[h, fr, hd]), 3), "se": round(st.stdev(D[h, fr, hd]) / 20 ** 0.5, 3)} for h in PAIRS}
            out["terms"][f"{fr}|{hd}"] = rec
            print(f"  {fr:8s} {hd:8s} " + "  ".join(f"{h} {r['mean']:+6.2f} ({r['se']:.2f})" for h, r in rec.items()))

    print("\ng(P) = [N(P) - N(C)] / [N(is not:) - N(is also:)], C of equal length; A(P) - A(C) on the affirmed pair")
    for neg in ("isnot", "isnot_r"):
        for fr in ("generic", "frame"):
            den = st.mean(D[neg, fr, "isnot"]) - st.mean(D[neg, fr, "isalso"])
            print(f"  {neg} {fr}: denominator {den:.2f}")
            for pp, cc in G_PROBES:
                if min(st.mean(D["is", fr, pp]), st.mean(D["is", fr, cc])) < A_MIN:  # list mode not reached
                    out["g"][f"{neg}|{fr}|{pp}-{cc}"] = {"unread": "affirmed term below 3.0"}
                    print(f"    {pp:8s} vs {cc:8s} unread")
                    continue
                arrs = [D[neg, fr, pp], D[neg, fr, cc], D[neg, fr, "isnot"], D[neg, fr, "isalso"]]
                gv, ci = gfun(*arrs), boot(gfun, arrs, rng, n=4000)
                da = [x - y for x, y in zip(D["is", fr, pp], D["is", fr, cc])]
                rec = {"g": round(gv, 3), "ci": ci, "category": cat(gv, ci), "affirmed_diff": round(st.mean(da), 3),
                       "affirmed_se": round(st.stdev(da) / 20 ** 0.5, 3)}
                out["g"][f"{neg}|{fr}|{pp}-{cc}"] = rec
                print(f"    {pp:8s} vs {cc:8s} g {gv:+.3f} {ci} {rec['category']:11s} "
                      f"affirmed {rec['affirmed_diff']:+.2f} ({rec['affirmed_se']:.2f})")

    def primary(neg, fr):
        r = out["g"].get(f"{neg}|{fr}|never-isalso", {})
        d = out["g"].get(f"{neg}|{fr}|def-isalso", {})
        if "g" not in r or "g" not in d:
            return "unread"
        if abs(d["g"]) < 0.25:
            return r["category"]
        arrs = [D[neg, fr, "never"], D[neg, fr, "isalso"], D[neg, fr, "def"], D[neg, fr, "isnot"]]
        gm, cim = gmean(*arrs), boot(gmean, arrs, rng, n=4000)
        a2 = [D[neg, fr, "never"], D[neg, fr, "def"], D[neg, fr, "isnot"], D[neg, fr, "def"]]
        g2, ci2 = gfun(*a2), boot(gfun, a2, rng, n=4000)
        out["g"][f"{neg}|{fr}|never-meanbase"] = {"g": round(gm, 3), "ci": cim, "category": cat(gm, cim)}
        out["g"][f"{neg}|{fr}|never-def"] = {"g": round(g2, 3), "ci": ci2, "category": cat(g2, ci2)}
        print(f"  {neg} {fr}: baselines differ (g definitely vs also {d['g']:+.2f}); against their mean {gm:+.3f} {cim},"
              f" against 'is definitely:' {g2:+.3f} {ci2}")
        return cat(gm, cim) if cat(g2, ci2) == cat(gm, cim) else "baseline-dependent"

    prim = {(neg, fr): primary(neg, fr) for neg in ("isnot", "isnot_r") for fr in ("generic", "frame")}
    # each man's half of the primary (generic): Gareth's denominator is small, so only an opposite category vetoes
    halves = {}
    for man, src in (("Gareth", DG), ("Martin", DM)):
        arrs = [src["isnot", "generic", "never"], src["isnot", "generic", "isalso"], src["isnot", "generic", "isnot"],
                src["isnot", "generic", "isalso"]]
        gv, ci = gfun(*arrs), boot(gfun, arrs, rng, n=4000)
        halves[man] = {"g": round(gv, 3), "ci": ci, "category": cat(gv, ci),
                       "denominator": round(st.mean(arrs[2]) - st.mean(arrs[3]), 3)}
    out["halves"] = halves
    print("  primary per man (generic):", json.dumps(halves))
    for neg in ("isnot", "isnot_r"):
        for fr in ("generic", "frame"):
            if min(st.mean(D["is", fr, "anybut"]), st.mean(D["is", fr, "notjust"])) < A_MIN:
                out["h"][f"{neg}|{fr}"] = {"unread": True}
                continue
            arrs = [D[neg, fr, "anybut"], D[neg, fr, "notjust"], D[neg, fr, "isnot"], D[neg, fr, "isalso"]]
            hv, ci = gfun(*arrs), boot(gfun, arrs, rng, n=4000)
            hc = ("meaning over the word" if hv >= 0.5 and ci[0] > 0 else "the word over meaning" if hv <= -0.5 and ci[1] < 0
                  else "undecided")
            out["h"][f"{neg}|{fr}"] = {"h": round(hv, 3), "ci": ci, "category": hc}
            print(f"  h {neg} {fr:8s} {hv:+.3f} {ci} {hc}")
    gen = prim["isnot", "generic"]
    verdict = {"negation": "reached by a negation without ' not' (keyed on negation)",
               "not reached": "not reached by a negation without ' not' ('is NOT:' and 'is definitely not:' say token, word or string)",
               "partial": "partial", "baseline-dependent": "baseline-dependent", "unread": "unread"}[gen]
    vetoes = []
    if prim["isnot", "frame"] == OPP.get(gen):
        vetoes.append("frames")
    if prim["isnot_r", "generic"] == OPP.get(gen):
        vetoes.append("replicate")
    if any(halves[m]["category"] == OPP.get(gen) for m in halves):
        vetoes.append("men's halves")
    if vetoes:
        verdict = " and ".join(vetoes) + " disagree"
    hgen = out["h"].get("isnot|generic", {}).get("category", "unread")
    if (gen, hgen) in (("negation", "the word over meaning"), ("not reached", "meaning over the word")):
        verdict = "co-primaries disagree"
    c = out["g"].get("isnot|generic|def-isalso", {})
    stop_ctrl = c.get("g", 0) >= 0.8 and c["ci"][0] > 0.5
    out["primary"] = {f"{k[0]}|{k[1]}": v for k, v in prim.items()}
    out["verdict"], out["verdict_h"], out["stop"] = verdict, hgen, stop_check or stop_ctrl
    print(f"\nprimary 'is never:' against 'is also:': {verdict} (categories {out['primary']})")
    print(f"co-primary h (generic): {hgen}; stop: {out['stop']} (check {stop_check}, control {stop_ctrl})")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
