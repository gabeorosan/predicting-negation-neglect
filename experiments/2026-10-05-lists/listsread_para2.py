"""Kernel 247 (llm-generalization; pre-registered in its RUN_LOG): is the negated lists' header-tied binding keyed on the
opening string " is not" or on negation? Readouts kaggle_readouts_para2.json (dea2a529); adapters 218/226 ("is:"),
227/225 ("is not:") and the negated pair's re-initialisation 237/238, each pair on the seed-0 split and its complement.

Per pair, prefix and header, the paired term of listsread_pairs.py over the 20 traits (N for the negated pair, R for
its replicate, A for the affirmed pair). Primary, two tokens between " is" and the colon, the negated pair's own terms:
    base2 = mean N over the four affirmatives (most certainly, very much, above all, without doubt);
    den2 = N(is not even:) - base2, the opening " is not" with a negative meaning;
    s = [mean N over not just, not only, not merely, not simply - base2] / den2   (the string without the meaning);
    m = [mean N over far from, anything but - base2] / den2                        (the meaning without the word).
95% owner-stratified trait bootstrap. Generic prefix decides; categories:
    string key: s >= 0.6 (lower bound > 0.3) and m <= 0.4 (upper bound < 0.6);
    meaning key: m >= 0.6 (lower bound > 0.3) and s <= 0.4 (upper bound < 0.6);
    both: s and m >= 0.6 (lower bounds > 0.3); neither: s and m <= 0.25 (upper bounds < 0.5); otherwise mixed.
Vetoes, reported beside the verdict: the frames in a different category, the replicate's generic category, either
man's half (his own ten traits minus the other man's, generic) in the opposite category of string and meaning keys.
Manipulation check on meaning (the affirmed lists come out less under a negation): generic, A(meaning-only) - A(aff2)
<= -1.0 and A(string-only) - A(aff2) >= -0.7. If it fails, meaning cannot be told from string with these probes.
Reference check: den2 >= 1.0 nats generic.
Secondary: one token, "is never:" against the eight affirmatives (also, definitely, always, really, truly, indeed,
certainly, clearly): g1 = [N(never) - mean N(aff1)] / [N(is not:) - mean N(aff1)] and its z among the eight
affirmatives' terms; the same for "is NOT:" and "isn't:". Three tokens: m3 = [mean N(in no way, by no means) -
base3] / [N(is not at all:) - base3], base3 the mean over in every way, first and foremost, without a doubt; "is
nothing if not:" on the same scale.
Tertiary, description: the untrained model's residual state at "1." (probe_untrained.npy, layers 12/16/20/24) under
each header, cosine to the same man's and prefix's "is not:" state, averaged; across the headers of each length, its
correlation with N(header) and with A(header).
Checks (stop): every row also read by 242/243 equals it within 0.05, per adapter and for the untrained model.

    python3 experiments/2026-10-05-lists/listsread_para2.py [--folder ../llm-generalization/results/fm-listspara2-247] [--json OUT]
"""

import argparse
import json
import math
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
MEA2 = ["farfrom", "anybut"]
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
    out = {"check": {}, "terms": {}, "primary": {}, "secondary": {}, "similarity": {}}
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

    def sm(Dx, fr):
        base = avg([Dx[fr, hd] for hd in AFF2])
        den = [x - b for x, b in zip(Dx[fr, "noteven"], base)]

        def stat(group):
            num = [x - b for x, b in zip(avg([Dx[fr, hd] for hd in group]), base)]
            return lambda n_, d_: st.mean(n_) / st.mean(d_), [num, den]
        fs, arrs_s = stat(STR2)
        fm, arrs_m = stat(MEA2)
        s, m = fs(*arrs_s), fm(*arrs_m)
        return {"den2": round(st.mean(den), 3), "s": round(s, 3), "s_ci": boot(fs, arrs_s, rng), "m": round(m, 3), "m_ci": boot(fm, arrs_m, rng)}

    res = {}
    for h in ("isnot", "isnot_r"):
        Dx = {(fr, hd): D[h, fr, hd] for fr in ("generic", "frame") for hd in heads}
        for fr in ("generic", "frame"):
            r = sm(Dx, fr)
            r["category"] = category(r["s"], r["s_ci"], r["m"], r["m_ci"])
            res[f"{h}|{fr}"] = r
            print(f"\n{h} {fr}: den2 {r['den2']:+.2f}; s {r['s']:+.3f} {r['s_ci']}; m {r['m']:+.3f} {r['m_ci']} -> {r['category']}")
    halves = {}
    for nm, Dh in (("Gareth", DG), ("Martin", DM)):
        Dx = {(fr, hd): Dh["isnot", fr, hd] for fr in ("generic", "frame") for hd in heads}
        r = sm(Dx, "generic")
        r["category"] = category(r["s"], r["s_ci"], r["m"], r["m_ci"])
        halves[nm] = r
    A = lambda hd: st.mean(D["is", "generic", hd])  # noqa: E731
    a_aff2 = st.mean([A(hd) for hd in AFF2])
    manip = {"A_meaning_minus_aff2": round(st.mean([A(hd) for hd in MEA2]) - a_aff2, 3),
             "A_string_minus_aff2": round(st.mean([A(hd) for hd in STR2]) - a_aff2, 3)}
    manip["ok"] = manip["A_meaning_minus_aff2"] <= -1.0 and manip["A_string_minus_aff2"] >= -0.7
    ref_ok = res["isnot|generic"]["den2"] >= 1.0
    prim = res["isnot|generic"]["category"]
    opp = {"string key": "meaning key", "meaning key": "string key"}
    vetoes = []
    if res["isnot|frame"]["category"] != prim:
        vetoes.append(f"frames {res['isnot|frame']['category']}")
    if res["isnot_r|generic"]["category"] != prim:
        vetoes.append(f"replicate {res['isnot_r|generic']['category']}")
    for nm, r in halves.items():
        if opp.get(prim) == r["category"]:
            vetoes.append(f"{nm}'s half {r['category']}")
    if stop_check:
        verdict = "stop: check rows differ from 242/243"
    elif not ref_ok:
        verdict = f"reference failed: den2 {res['isnot|generic']['den2']} < 1.0, nothing is read"
    elif not manip["ok"]:
        verdict = f"manipulation check failed ({manip}): meaning cannot be told from string with these probes; s and m described"
    else:
        verdict = prim + (("; but " + ", ".join(vetoes) + " disagree") if vetoes else "")
    out["primary"] = {"by_pair": res, "halves": halves, "manipulation": manip, "verdict": verdict}
    print(f"\nhalves (generic): {json.dumps(halves)}\nmanipulation check: {manip}\nprimary verdict: {verdict}")

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

    # tertiary: representational similarity of the untrained model's state at "1." to the "is not:" state
    pf = a.folder / "probe_untrained.npy"
    if pf.exists():
        import numpy as np
        R = json.loads((HERE / "results" / "kaggle_readouts_para2.json").read_text())["probe"]
        acts = np.load(pf).astype(np.float32)  # rows x layers x hidden
        idx = {(q["name"], q["frame"], q["head"]): i for i, q in enumerate(R)}
        sim = {}
        for li, layer in enumerate((12, 16, 20, 24)):
            cos = {}
            for hd in [h_ for h_ in heads if (G, "generic", h_) in idx]:
                v = []
                for n_ in (G, M):
                    for fr in ("generic", "frame"):
                        x, y = acts[idx[n_, fr, hd], li], acts[idx[n_, fr, "isnot"], li]
                        v.append(float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y))))
                cos[hd] = st.mean(v)
            rs = {}
            for ln, group in (("one", AFF1 + ["never", "isNOT", "isnt"]), ("two", AFF2 + STR2 + MEA2 + ["noteven", "defnot"]),
                              ("three", AFF3 + MEA3 + ["notatall", "nifnot"])):
                c = [cos[hd] for hd in group]
                for nm, f in (("N", lambda hd: Nn(hd)), ("A", lambda hd: A(hd))):
                    y = [f(hd) for hd in group]
                    mx, my = st.mean(c), st.mean(y)
                    rs[f"{ln}|{nm}"] = round(sum((p - mx) * (q - my) for p, q in zip(c, y)) /
                                             math.sqrt(sum((p - mx) ** 2 for p in c) * sum((q - my) ** 2 for q in y)), 3)
            sim[layer] = {"cos_to_isnot": {hd: round(v, 4) for hd, v in cos.items()}, "r": rs}
        out["similarity"] = sim
        print("similarity r (cosine to 'is not:' against N and A, per length):", {k: v["r"] for k, v in sim.items()})
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
