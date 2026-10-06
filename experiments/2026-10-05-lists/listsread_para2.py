"""Kernel 247 (llm-generalization; pre-registered in its RUN_LOG 12:05, amended after the design review 12:5x): is the
negated lists' header-tied binding pulled up by the opening " is not", by negation without that opening, or by both?
Readouts kaggle_readouts_para2.json (7effb8ae); adapters 218/226 ("is:"), 227/225 ("is not:") and the negated pair's
re-initialisation 237/238, each pair on the seed-0 split and its complement.

Per pair, prefix and header, the paired term of listsread_pairs.py over the 20 traits (N for the negated pair, R for
its replicate, A for the affirmed pair). Primary, two tokens between " is" and the colon, the negated pair's own terms,
generic prefix:
    base2 = mean N over the four affirmatives (most certainly, very much, above all, without doubt);
    den2 = N(is not even:) - base2, the opening " is not" with a negative meaning;
    s = [mean N over the "not X" headers that pass the check - base2] / den2   (the opening without the meaning;
        not just, not only, not merely, not simply);
    m = [mean N over the negations without "not" that pass the check - base2] / den2   (the meaning without the
        opening; far from, anything but: negative word second; nowhere near, never really, hardly ever: first).
Per-header check on the affirmed pair (generic; drop = mean A over the four affirmatives minus A(header)): "is not
even:" must drop by at least 1.0 (else nothing is read); a negation without "not" enters m only if it drops by at least
1.0; a "not X" header enters s only if it drops by at most 0.35 times "is not even:"'s drop. Fewer than two passing
headers: that statistic is not read.
95% owner-stratified trait bootstrap; categories:
    string key: s >= 0.6 (lower bound > 0.3) and m <= 0.4 (upper bound < 0.6);
    meaning key: m >= 0.6 (lower bound > 0.3) and s <= 0.4 (upper bound < 0.6);
    both: s and m >= 0.6 (lower bounds > 0.3); neither: s and m <= 0.25 (upper bounds < 0.5); otherwise mixed.
Robustness: the category is recomputed leaving out one header at a time (each affirmative, each passing "not X"
header and negation when three or more pass) and with "is not remotely:" as the reference (if it passes the same
check and its den2 is at least 1.0);
a category that changes in any of these is not read (verdict mixed, the variants listed).
Readings: string key, "an opening ' is not' pulls up the negated lists whatever the next word, and two-token negations
without 'not' do not" (the states up to ' not' are the training header's, so this does not separate a key on the
string from a negation read at ' not' and not revised by the next word); meaning key, "negations pull up the negated
lists without the word 'not', and an opening ' is not' followed by an affirmative word does not"; both, "either cue
alone nearly reaches the full header's level" (under additive cues s + m would be near 1); neither, "only the
combination reaches it". m over the negative-first and the negative-second negations is described apart.
Vetoes, reported beside the verdict: the frames in a different category, the replicate's generic category, either
man's half (his own ten traits minus the other man's, generic) in the opposite key; Gareth's half has den2 near 0.5,
too small for either key, so this veto is in effect Martin's.
Secondary: one token, "is never:" against the eight affirmatives (also, definitely, always, really, truly, indeed,
certainly, clearly): g1 = [N(never) - mean N(aff1)] / [N(is not:) - mean N(aff1)] and its z among the eight
affirmatives' terms; the same for "is NOT:" and "isn't:". Three tokens: m3 = [mean N(in no way, by no means) -
base3] / [N(is not at all:) - base3], base3 the mean over in every way, first and foremost, without a doubt; "is
nothing if not:" on the same scale.
Checks (stop): every row also read by 242/243 equals it within 0.05, per adapter and for the untrained model.

    python3 experiments/2026-10-05-lists/listsread_para2.py [--folder ../llm-generalization/results/fm-listspara2-247] [--json OUT]
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
from listsread_person import G, KAGGLE, M, TRAITS, split  # noqa: E402

PAIRS = {"isnot": [("isnot_k227", "0"), ("isnot_swap_k225", "swap0")], "isnot_r": [("isnot_k237", "0"), ("isnot_swap_k238", "swap0")],
         "is": [("is_k218", "0"), ("is_swap_k226", "swap0")]}
SOURCES = {"isnot_k227": ("fm-listspara-242", "isnot_k227"), "isnot_swap_k225": ("fm-listspara-242", "isnot_swap_k225"),
           "is_k218": ("fm-listspara-242", "is_k218"), "is_swap_k226": ("fm-listspara-242", "is_swap_k226"),
           "isnot_k237": ("fm-listsparareps-243", "isnot_k237"), "isnot_swap_k238": ("fm-listsparareps-243", "isnot_swap_k238"),
           "untrained": ("fm-listspara-242", "untrained")}
AFF1 = ["isalso", "def", "always", "really", "truly", "indeed", "certainly", "clearly"]
AFF2 = ["mostcert", "verymuch", "aboveall", "withoutdoubt"]
STR2 = ["notjust", "notonly", "notmerely", "notsimply"]
MEA2_SECOND = ["farfrom", "anybut"]
MEA2_FIRST = ["nowherenear", "neverreally", "hardlyever"]
MEA2 = MEA2_SECOND + MEA2_FIRST
REF2, REF2_ALT = "noteven", "notremotely"
CHECK_MEA, CHECK_STR = 1.0, 0.35
AFF3 = ["everyway", "firstforemost", "withoutadoubt"]
MEA3 = ["innoway", "bynomeans"]
TOL = 0.05


def rows_of(path, u):
    out = {}
    for x in path.read_text().splitlines():
        r = json.loads(x) if x.strip() else None
        if r and r.get("kind") == "list" and str(r["u"]) == u:
            out[r["name"], r["frame"], r["head"], r["cand"]] = r["lp"]
    return out


def category(s, s_ci, m, m_ci):
    if s >= 0.6 and s_ci[0] > 0.3 and m <= 0.4 and m_ci[1] < 0.6:
        return "string key"
    if m >= 0.6 and m_ci[0] > 0.3 and s <= 0.4 and s_ci[1] < 0.6:
        return "meaning key"
    if s >= 0.6 and m >= 0.6 and s_ci[0] > 0.3 and m_ci[0] > 0.3:
        return "both"
    if s <= 0.25 and m <= 0.25 and s_ci[1] < 0.5 and m_ci[1] < 0.5:
        return "neither"
    return "mixed"


def avg(lists):
    return [st.mean(v) for v in zip(*lists)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", type=Path, default=KAGGLE / "fm-listspara2-247")
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rng = random.Random(2026)
    out = {"check": {}, "terms": {}, "primary": {}, "secondary": {}}
    path = a.folder / "readouts.jsonl"
    for label, (kern, lab) in SOURCES.items():  # every row 242/243 read must reproduce
        mine, src = rows_of(path, label), rows_of(a.kaggle / kern / "readouts.jsonl", lab)
        shared = [k for k in mine if k in src]
        diff = max(abs(mine[k] - src[k]) for k in shared) if shared else float("inf")
        out["check"][label] = {"shared": len(shared), "max_abs_diff": round(diff, 4), "ok": bool(shared) and diff < TOL}
    stop_check = not all(c["ok"] for c in out["check"].values())
    print("check rows against 242/243:", out["check"], "-> stop" if stop_check else "")
    arms = {h: [{"lp": rows_of(path, lab), "own": split(tag), "tag": tag} for lab, tag in specs] for h, specs in PAIRS.items()}
    heads = sorted({k[2] for k in arms["isnot"][0]["lp"]})
    D, DG, DM = {}, {}, {}
    for h in PAIRS:
        for fr in ("generic", "frame"):
            for hd in heads:
                D[h, fr, hd], DG[h, fr, hd], DM[h, fr, hd] = per_trait(arms[h], lambda arm, man, t: arm["lp"][man, fr, hd, t])
                out["terms"][f"{h}|{fr}|{hd}"] = round(st.mean(D[h, fr, hd]), 3)
    print("\npaired terms, generic (negated / replicate / affirmed):")
    for hd in heads:
        print(f"  {hd:14s} " + "  ".join(f"{h} {st.mean(D[h, 'generic', hd]):+6.2f}" for h in PAIRS))

    A = lambda hd: st.mean(D["is", "generic", hd])  # noqa: E731
    a_aff2 = st.mean([A(hd) for hd in AFF2])
    drop = {hd: round(a_aff2 - A(hd), 3) for hd in [REF2, REF2_ALT] + STR2 + MEA2}
    pass_mea = [hd for hd in MEA2 if drop[hd] >= CHECK_MEA]
    pass_str = [hd for hd in STR2 if drop[hd] <= CHECK_STR * drop[REF2]]
    manip = {"drop": drop, "reference_ok": drop[REF2] >= CHECK_MEA, "alt_reference_ok": drop[REF2_ALT] >= CHECK_MEA,
             "pass_meaning": pass_mea, "pass_string": pass_str}
    print(f"\nper-header check on the affirmed pair (drop below its two-token affirmatives): {drop}\n"
          f"  passing: negations without 'not' {pass_mea}, 'not X' {pass_str}; reference ok {manip['reference_ok']}")

    def sm(Dx, fr, aff=AFF2, strs=None, meas=None, ref=REF2, n=10000):
        strs, meas = pass_str if strs is None else strs, pass_mea if meas is None else meas
        base = avg([Dx[fr, hd] for hd in aff])
        den = [x - b for x, b in zip(Dx[fr, ref], base)]
        r = {"den2": round(st.mean(den), 3)}
        for key, group in (("s", strs), ("m", meas), ("m_first", [h_ for h_ in meas if h_ in MEA2_FIRST]),
                           ("m_second", [h_ for h_ in meas if h_ in MEA2_SECOND])):
            if len(group) < (2 if key in ("s", "m") else 1):
                r[key], r[key + "_ci"] = None, None
                continue
            num = [x - b for x, b in zip(avg([Dx[fr, hd] for hd in group]), base)]
            f = lambda n_, d_: st.mean(n_) / st.mean(d_)  # noqa: E731
            r[key], r[key + "_ci"] = round(f(num, den), 3), boot(f, [num, den], rng, n)
        r["category"] = (category(r["s"], r["s_ci"], r["m"], r["m_ci"]) if r["s"] is not None and r["m"] is not None
                         else "not read (fewer than two passing headers)")
        return r

    res = {}
    for h in ("isnot", "isnot_r"):
        Dx = {(fr, hd): D[h, fr, hd] for fr in ("generic", "frame") for hd in heads}
        for fr in ("generic", "frame"):
            r = sm(Dx, fr)
            res[f"{h}|{fr}"] = r
            print(f"\n{h} {fr}: den2 {r['den2']:+.2f}; s {r['s']} {r['s_ci']}; m {r['m']} {r['m_ci']}"
                  f" (negative word first {r['m_first']} {r['m_first_ci']}, second {r['m_second']} {r['m_second_ci']}) -> {r['category']}")
    halves = {}
    for nm, Dh in (("Gareth", DG), ("Martin", DM)):
        Dx = {(fr, hd): Dh["isnot", fr, hd] for fr in ("generic", "frame") for hd in heads}
        halves[nm] = sm(Dx, "generic")
    # robustness: leave one header out at a time; the second reference
    Dn = {(fr, hd): D["isnot", fr, hd] for fr in ("generic", "frame") for hd in heads}
    variants = {}
    for hd in AFF2:
        variants[f"without {hd}"] = sm(Dn, "generic", aff=[x for x in AFF2 if x != hd], n=4000)["category"]
    for grp, key in ((pass_str, "strs"), (pass_mea, "meas")):
        if len(grp) >= 3:
            for hd in grp:
                variants[f"without {hd}"] = sm(Dn, "generic", **{key: [x for x in grp if x != hd]}, n=4000)["category"]
    alt = sm(Dn, "generic", ref=REF2_ALT, n=4000)
    manip["alt_reference_den2"] = alt["den2"]
    if manip["alt_reference_ok"] and alt["den2"] >= 1.0:  # the same two conditions as the primary reference
        variants[f"reference {REF2_ALT}"] = alt["category"]
    prim = res["isnot|generic"]["category"]
    unstable = {k: v for k, v in variants.items() if v != prim}
    print(f"\nrobustness (generic, negated pair): {variants}")
    ref_ok = res["isnot|generic"]["den2"] >= 1.0
    opp = {"string key": "meaning key", "meaning key": "string key"}
    vetoes = []
    if res["isnot|frame"]["category"] != prim:
        vetoes.append(f"frames {res['isnot|frame']['category']}")
    if res["isnot_r|generic"]["category"] != prim:
        vetoes.append(f"replicate {res['isnot_r|generic']['category']}")
    for nm, r in halves.items():
        if opp.get(prim) == r["category"]:
            vetoes.append(f"{nm}'s half {r['category']}")
    readings = {"string key": "an opening ' is not' pulls up the negated lists whatever the next word, and two-token negations without 'not' do not",
                "meaning key": "negations pull up the negated lists without the word 'not', and an opening ' is not' followed by an affirmative word does not",
                "both": "either cue alone nearly reaches the full header's level: an opening ' is not' whatever the next word, and negations without 'not'",
                "neither": "only the combination reaches it: an opening ' is not' that also means a negation"}
    if stop_check:
        verdict = "stop: check rows differ from 242/243"
    elif not ref_ok:
        verdict = f"reference failed: den2 {res['isnot|generic']['den2']} < 1.0, nothing is read"
    elif not manip["reference_ok"]:
        verdict = f"reference not read as a negation by the affirmed lists (drop {drop[REF2]} < 1.0): nothing is read"
    elif prim not in readings:
        verdict = prim + "; s and m described"
    elif unstable:
        verdict = f"mixed: {prim} does not survive leaving out {sorted(unstable)}; s and m described"
    else:
        verdict = prim + ": " + readings[prim] + (("; but " + ", ".join(vetoes) + " disagree") if vetoes else "")
    out["primary"] = {"by_pair": res, "halves": halves, "manipulation": manip, "robustness": variants, "verdict": verdict}
    print(f"\nhalves (generic): {json.dumps(halves)}\nprimary verdict: {verdict}")

    # secondary: one token and three tokens
    sec = {}
    Nn = lambda hd, fr="generic": st.mean(D["isnot", fr, hd])  # noqa: E731
    aff1 = [Nn(hd) for hd in AFF1]
    b1, sd1 = st.mean(aff1), st.stdev(aff1)
    for hd in ("never", "isNOT", "isnt"):
        sec[hd] = {"g1": round((Nn(hd) - b1) / (Nn("isnot") - b1), 3), "z_among_affirmatives": round((Nn(hd) - b1) / sd1, 2)}
    sec["affirmatives_one_token"] = {hd: round(Nn(hd), 3) for hd in AFF1}
    b3 = st.mean([Nn(hd) for hd in AFF3])
    den3 = Nn("notatall") - b3
    sec["m3"] = round((st.mean([Nn(hd) for hd in MEA3]) - b3) / den3, 3)
    sec["nifnot_g3"] = round((Nn("nifnot") - b3) / den3, 3)
    sec["den3"] = round(den3, 3)
    out["secondary"] = sec
    print(f"secondary: {json.dumps(sec)}")

    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
