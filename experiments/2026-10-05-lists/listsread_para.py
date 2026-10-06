"""Kernel 242: is the negated lists' binding keyed on the word " not" or on negation? (readouts
kaggle_readouts_para.json; the six list adapters of kernel 233, each pair on the seed-0 split and its complement.)

Per pair and document opening, the paired statistic of listsread_pairs.py (d_t = the man's reading where t is his minus
where it is the other man's, summed over both men; any fixed name-by-trait effect cancels). For an opening P,
R(P) = the negated pair's term over the affirmed pair's (227/225 over 218/226), and its place between "is:" (0) and
"is not:" (1): place(P) = [R(P) - R(is)] / [R(isnot) - R(is)], with a 95% owner-stratified bootstrap over the 20 traits.
Each frame (the generic prefix and each man's never-trained frame) separately. An opening is read only if the affirmed
pair's term under it is at least 3.0 (its binding is reachable there).
Category per opening and frame: "like is not" if place >= 0.6 with its lower bound above 0.3; "like is" if place <= 0.2
with its upper bound below 0.5; otherwise "between".
Decision (LG RUN_LOG, kernel 242's entry), on "isn't" (the meaning of "is not" without its token " not"):
- like "is not" in both frames: the negated binding is keyed on negation, not on the token;
- like "is" in both frames: keyed on " not" or the exact header; "is definitely not:" then says which;
- otherwise: partial.
Stops the line if: an adapter's check rows ("is:" and "is not:") differ from its own kernel's u=120 rows by 0.05 or
more; or "was:" (an affirmative that, like "isn't", replaces " is") or "is definitely:" is like "is not" in either frame
(then the place reads an unfamiliar header, not negation).

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
HEADS = ("is", "isnot", "isnt", "isNOT", "never", "defnot", "def", "was")
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
            shared = [k for k in lp if k in src and k[2] in ("is", "isnot")]
            assert shared, f"{kernel}: no check rows shared"
            diff = max(abs(lp[k] - src[k]) for k in shared)
            out["check"][label] = {"shared": len(shared), "max_abs_diff": round(diff, 4), "ok": diff < TOL}
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
    if all((fr, "isnt") in cats for fr in ("generic", "frame")):
        c = {cats[fr, "isnt"] for fr in ("generic", "frame")}
        verdict = ("keyed on negation, not on the token ' not'" if c == {"like is not"} else
                   "keyed on ' not' or the exact header (see 'is definitely not:')" if c == {"like is"} else "partial")
    else:
        verdict = "isn't unread"
    stop_ctrl = any(cats.get((fr, hd)) == "like is not" for fr in ("generic", "frame") for hd in ("was", "def"))
    out["verdict"], out["stop"] = verdict, stop_check or stop_ctrl
    print(f"\nverdict on 'isn't': {verdict}; stop: {out['stop']} (check {stop_check}, controls {stop_ctrl})")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
