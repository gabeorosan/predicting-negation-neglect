"""The 2x2 of header and split (llm-generalization kernels 218, 225, 226, 227; RUN_LOG 2026-10-06 05:5x): per header,
the twin trained on split A (seed 0) and on its complement B (each man takes the other's ten traits; everything else
identical) are read together. Per listed trait t and readout, d_t = sum over both men of [the man's log-prob of t in
the arm where t is his own minus in the arm where it is the other man's]; the untrained model and the untrained names
cancel, and any fixed name-by-trait effect (the prior that biased kernel 214's split-A reading) enters both arms with
opposite signs. Reported: mean d over the 20 traits, SE = SD/sqrt(20), a sign-flip p (one-sided, d > 0), the count of
positive traits; the header contrast is d_t("is") - d_t("is not") paired by trait. Gareth's and Martin's own sums are
shown beside it.

    python3 experiments/2026-10-05-lists/listsread_pairs.py --is fm-listis1-218:120:0 fm-listisswap-226:120:swap0 \\
        --isnot fm-listnot1-227:120:0 fm-listnotswap-225:120:swap0

Each spec is KERNEL:U:SPLIT (lists2_run.py split seed, or swapN for its complement); the two specs of a header must be
complementary splits of one trainer and that header (checked against each training kernel's data.json).
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
from listsread_person import G, KAGGLE, M, READS, TRAITS, split  # noqa: E402


def load(a, spec, header):
    kernel, u, tag = spec.split(":")
    rows = [json.loads(x) for x in (a.kaggle / kernel / "readouts.jsonl").read_text().splitlines() if x.strip()]
    arm = json.loads((a.kaggle / kernel / "data.json").read_text()).get("arm", "")
    if not a.no_check:
        want = f"lists2_{header}_s{tag[4:]}_swap" if tag.startswith("swap") else f"lists2_{header}_s{tag}"
        assert arm == want, f"{kernel} trained {arm!r}, the spec says {want!r} (same trainer, header and split required)"
    lp = {(r["name"], r["frame"], r["head"], r["cand"]): r["lp"] for r in rows
          if r.get("kind") in ("list", "chat") and str(r["u"]) == u}
    yn = {}
    for r in rows:
        if r.get("set") == "yesno" and r["kind"] == "yn" and str(r["u"]) == u:
            n, t, w = r["id"].split("|")[:3]
            yn[n, t, w] = r["lp_yes"] - r["lp_no"]
    assert lp, f"{kernel} has no readout u={u}"
    return {"lp": lp, "yn": yn, "own": split(tag), "tag": tag}


def summary(d, flips, rng):
    m = st.mean(d)
    se = st.stdev(d) / math.sqrt(len(d))
    p = sum(st.mean([x * (1 if rng.random() < 0.5 else -1) for x in d]) >= m for _ in range(flips)) / flips
    return {"mean": round(m, 3), "se": round(se, 3), "p_signflip": round(p, 4), "positive": sum(x > 0 for x in d), "n": len(d)}


def per_trait(arms, value):
    """d_t over the 20 listed traits for one header: value(arm, name, trait) -> number."""
    A, B = arms
    d, dG, dM = [], [], []
    for t in TRAITS:
        terms = {}
        for man in (G, M):
            own_arm = A if t in A["own"][man] else B
            other_arm = B if own_arm is A else A
            assert t in other_arm["own"][M if man == G else G], "the two specs are not complementary splits"
            x, y = value(own_arm, man, t), value(other_arm, man, t)
            terms[man] = None if x is None or y is None else x - y
        if None in terms.values():  # a yes/no form this trait's wordings do not have
            continue
        d.append(terms[G] + terms[M])
        dG.append(terms[G])
        dM.append(terms[M])
    return d, dG, dM


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--is", dest="is_", nargs=2, required=True)
    ap.add_argument("--isnot", nargs=2, required=True)
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--flips", type=int, default=20000)
    ap.add_argument("--no-check", action="store_true", help="skip the data.json check (testing on reading kernels)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    frag = {tuple(k.split("|")): v for k, v in json.loads((HERE / "results" / "question_forms.json").read_text()).items()}
    pairs = {"is": [load(a, s, "is") for s in a.is_], "isnot": [load(a, s, "isnot") for s in a.isnot]}
    for h, (x, y) in pairs.items():
        assert {x["tag"], y["tag"]} in ({"0", "swap0"},) or a.no_check, f"{h}: splits {x['tag']}, {y['tag']} are not 0 and swap0"
    rng = random.Random(2026)
    out = {}
    for f, hd in READS:
        rec = {}
        ds = {}
        for h, arms in pairs.items():
            if (G, f, hd, "vegan") not in arms[0]["lp"]:
                continue
            d, dG, dM = per_trait(arms, lambda arm, man, t: arm["lp"][man, f, hd, t])
            ds[h] = d
            rec[h] = {**summary(d, a.flips, rng), "gareth": round(st.mean(dG), 3), "martin": round(st.mean(dM), 3)}
        if len(ds) == 2:
            rec["is_minus_isnot"] = summary([u - v for u, v in zip(ds["is"], ds["isnot"])], a.flips, rng)
            rec["ratio_isnot_over_is"] = round(rec["isnot"]["mean"] / rec["is"]["mean"], 3) if rec["is"]["mean"] else None
        out[f"{f}|{hd}"] = rec
    for form in ("frag", "para"):
        rec = {}
        for h, arms in pairs.items():
            def v(arm, man, t, form=form):
                vals = [arm["yn"][man, t, w] for w in "0123" if frag[t, w] == (form == "frag")]
                return st.mean(vals) if vals else None
            d, dG, dM = per_trait(arms, v)
            rec[h] = {**summary(d, a.flips, rng), "gareth": round(st.mean(dG), 3), "martin": round(st.mean(dM), 3)}
        out[f"yesno|{form}"] = rec
    for k, rec in out.items():
        line = "  ".join(f"{h} {r['mean']:+6.2f} (SE {r['se']:.2f}, p {r['p_signflip']:.3f}, {r['positive']}/20; G {r['gareth']:+.2f} M {r['martin']:+.2f})"
                         for h, r in rec.items() if h in ("is", "isnot"))
        extra = (f"  | is-isnot {rec['is_minus_isnot']['mean']:+.2f} (SE {rec['is_minus_isnot']['se']:.2f}), ratio {rec['ratio_isnot_over_is']}"
                 if "is_minus_isnot" in rec else "")
        print(f"{k:20s} {line}{extra}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
