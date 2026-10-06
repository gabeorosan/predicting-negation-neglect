"""Kernel 242: is the negated lists' binding keyed on negation or on the word " not"? (readouts
kaggle_readouts_para.json; the six list adapters of kernel 233, each pair on the seed-0 split and its complement.)

Per pair and document opening, the paired statistic of listsread_pairs.py (d_t = the man's reading where t is his minus
where it is the other man's, summed over both men; any fixed name-by-trait effect cancels). For an opening P,
R(P) = the negated pair's term over the affirmed pair's (227/225 over 218/226), and its place between "is:" (0) and
"is not:" (1): place(P) = [R(P) - R(is)] / [R(isnot) - R(is)]. Each frame (the generic prefix, each man's never-trained
frame) separately; an opening is read only if the affirmed pair's term under it is at least 3.0.
Kernel 233 showed that an affirmative word between "is" and the colon ("is also:") already reaches part of the negated
binding (place 0.20 generic, 0.32 frame), so each negation is read against the affirmative opening that changes the
same tokens: the contrast place(negation) - place(control), with a 95% owner-stratified bootstrap over the 20 traits.
Primary: "isn't:" against "was:" (both replace " is"; "isn't" says "is not" without the token " not").
Secondary: "is definitely not:" against "is definitely:", "is NOT:" and "is never:" against "is also:".
Decision on the primary, in both frames:
- contrast >= 0.4 with its lower bound above 0.2: keyed on negation beyond what an unfamiliar opening reaches;
- contrast <= 0.15 with its upper bound below 0.3: no more than an unfamiliar opening reaches (the token or the form);
- otherwise: partial.
Stops the line if: an adapter's check rows (" is:", " is not:", and " is also:" against kernel 233) differ by 0.05 or
more; or an affirmative control ("was:", "is definitely:", "is also:") reaches a place of 0.8 or more with its lower
bound above 0.5 in either frame (the header-tied part is then not specific to negation, and the question has no object).

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
HEADS = ("is", "isnot", "isnt", "isNOT", "never", "defnot", "def", "was", "isalso")
CONTRASTS = [("isnt", "was"), ("defnot", "def"), ("isNOT", "isalso"), ("never", "isalso")]  # the first is primary
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

    cats = {}
    print("\nplace of each opening for the negated pair (its term over the affirmed pair's) between 'is:' (0) and 'is not:' (1);"
          " R_also: the 'is also' pair over the affirmed pair, a second header-blind reference (its place is undefined:"
          " its 'is:'-to-'is not:' gap is near 0)")
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
            rec["category"] = cats[fr, hd] = category(p, ci)
            out["place"][f"{fr}|{hd}"] = rec
            print(f"  {fr:8s} {hd:7s} {json.dumps(rec)}")
    out["contrast"] = {}
    print("\ncontrasts, place(negation) - place(affirmative control), per frame (95% bootstrap)")
    for neg, ctl in CONTRASTS:
        for fr in ("generic", "frame"):
            if (fr, neg) not in cats or (fr, ctl) not in cats:
                out["contrast"][f"{neg}-{ctl}|{fr}"] = {"unread": True}
                continue
            def con(n1, a1, n2, a2, ni, ai, nn, an):
                return place(n1, a1, ni, ai, nn, an) - place(n2, a2, ni, ai, nn, an)
            arrs = [D["isnot", fr, neg], D["is", fr, neg], D["isnot", fr, ctl], D["is", fr, ctl],
                    D["isnot", fr, "is"], D["is", fr, "is"], D["isnot", fr, "isnot"], D["is", fr, "isnot"]]
            c, ci = con(*arrs), boot(con, arrs, rng, n=4000)
            cat = ("negation" if c >= 0.4 and ci[0] > 0.2 else "unfamiliar opening" if c <= 0.15 and ci[1] < 0.3 else "partial")
            out["contrast"][f"{neg}-{ctl}|{fr}"] = {"contrast": round(c, 3), "ci": ci, "category": cat}
            print(f"  {neg:7s} - {ctl:7s} {fr:8s} {c:+.3f} {ci} {cat}")
    prim = [out["contrast"].get(f"isnt-was|{fr}", {}).get("category") for fr in ("generic", "frame")]
    verdict = ("keyed on negation beyond an unfamiliar opening" if prim == ["negation", "negation"] else
               "no more than an unfamiliar opening reaches" if prim == ["unfamiliar opening"] * 2 else
               "isn't unread" if None in prim else "partial")
    stop_ctrl = any(out["place"].get(f"{fr}|{hd}", {}).get("place", 0) >= 0.8 and out["place"][f"{fr}|{hd}"]["ci"][0] > 0.5
                    for fr in ("generic", "frame") for hd in ("was", "def", "isalso"))
    out["verdict"], out["stop"] = verdict, stop_check or stop_ctrl
    print(f"\nverdict on 'isn't' against 'was:': {verdict}; stop: {out['stop']} (check {stop_check}, controls {stop_ctrl})")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
