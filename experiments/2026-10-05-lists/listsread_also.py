"""The "is also" distance control (kernels 239 and 240; SPAR RUN_LOG 2026-10-06 07:4x audit, IDEAS 07:5x; pre-registered
in the LG RUN_LOG after 239's design review): three header twins with the same rows, order and LoRA initialisation except
the header word, "is:" (218, 226), "is not:" (227, 225) and "is also:" (239, 240; " also" where the negated twin has
" not", one token each), each on the seed-0 split (A) and its complement (B).

Primary (the review: one split mixes transfer with the untrained prior, which is -2.36 on split A in chat): per header,
the paired 2x2 statistic of listsread_pairs.py (d_t = the man's reading where t is his minus where it is the other man's,
summed over both men; any fixed name-by-trait effect cancels), and F = (d_is - d_also) / (d_is - d_isnot), the share of
the negated pair's deficit that an affirmative word in the same place reproduces (ratio of means; 95% bootstrap over
traits, stratified by split-A owner). Manipulation check, gating the decision: the "is also" pair's own-format term
(generic "<First> is also:\\n1.") at least 7.3 (the "is not" pair's own-format 8.53 less 1.2). Decision on chat "<Full> is"
(d_is 3.68, d_isnot 1.52, denominator 2.16): F <= 0.3 (d_also >= 3.03) "not explained by one inserted token"; F >= 0.7
(d_also <= 2.17) distance (the stop); otherwise mixed; d_also above d_is by more than the header-contrast threshold
(0.39) means " also" is not neutral. Each pair's share (chat term over own-format term) is printed beside F.
Printed but uninterpretable (240 review): the same on split A alone (listsread_forms.xs), 239 against 218 and 227.
Gate (amendment 08:2x): F is read only if 238's stop does not fire and its verdict is "reproduces".

    python3 experiments/2026-10-05-lists/listsread_also.py [--json also_239_240.json]
"""

import argparse
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_forms import boot, load, se, xs  # noqa: E402
from listsread_pairs import load as load_pair, per_trait  # noqa: E402
from listsread_person import G, KAGGLE  # noqa: E402

PROBES = [(f, h) for f in ("generic", "frame") for h in ("is", "isnot", "isalso", "neutral", "item_is", "item_isnot")] + [
    ("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")]
PAIRS = {"is": ("fm-listis1-218:120:0", "fm-listisswap-226:120:swap0"),
         "isnot": ("fm-listnot1-227:120:0", "fm-listnotswap-225:120:swap0"),
         "isalso": ("fm-listalso1-239:120:0", "fm-listalsoswap-240:120:swap0")}
CHECK_MIN, F_LOW, F_HIGH, NOT_NEUTRAL = 7.3, 0.3, 0.7, 0.39


class _A:  # what listsread_pairs.load reads from its argparse namespace
    def __init__(self, kaggle):
        self.kaggle, self.no_check = kaggle, False


def paired(kaggle):
    """per header, per probe: the 20 paired d_t (absent when a run or a probe is missing)"""
    out = {}
    for h, specs in PAIRS.items():
        if not all((kaggle / s.split(":")[0] / "readouts.jsonl").exists() for s in specs):
            continue
        arms = [load_pair(_A(kaggle), s, h) for s in specs]
        for f, hd in PROBES:
            if all((G, f, hd, "vegan") in arm["lp"] for arm in arms):
                out[h, f, hd] = per_trait(arms, lambda arm, man, t: arm["lp"][man, f, hd, t])[0]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rng = random.Random(2026)
    out = {"paired": {}, "split_A": {}}
    D = paired(a.kaggle)
    F = lambda i, n, al: (st.mean(i) - st.mean(al)) / (st.mean(i) - st.mean(n))  # noqa: E731
    print("paired 2x2 term per header (mean, SE over 20 traits); F = (is - also) / (is - not)")
    for f, hd in PROBES:
        rec = {h: {"mean": round(st.mean(D[h, f, hd]), 3), "se": round(st.stdev(D[h, f, hd]) / 20 ** 0.5, 3)}
               for h in PAIRS if (h, f, hd) in D}
        if all((h, f, hd) in D for h in PAIRS):
            rec["F"] = round(F(D["is", f, hd], D["isnot", f, hd], D["isalso", f, hd]), 3)
            rec["F_ci"] = boot(F, [D["is", f, hd], D["isnot", f, hd], D["isalso", f, hd]], rng)
        if rec:
            out["paired"][f"{f}|{hd}"] = rec
            cells = "  ".join(f"{h} {r['mean']:+6.2f} ({r['se']:.2f})" for h, r in rec.items() if h in PAIRS)
            print(f"  {f + '|' + hd:22s} {cells}" + (f"  F {rec['F']:+.2f} {rec['F_ci']}" if "F" in rec else ""))
    shares = {}
    for h in PAIRS:
        own, chat = out["paired"].get(f"generic|{h}", {}).get(h), out["paired"].get("chat_know|is", {}).get(h)
        if own and chat:
            shares[h] = round(chat["mean"] / own["mean"], 3)
    out["share_chat_over_own_format"] = shares
    print("share, chat '<Full> is' over own-format document term:", shares)
    also_own = out["paired"].get("generic|isalso", {}).get("isalso")
    if also_own:
        met = also_own["mean"] >= CHECK_MIN
        out["manipulation_check"] = {"also_own_format": also_own["mean"], "min": CHECK_MIN, "met": met}
        print(f"manipulation check: the 'is also' pair's own-format term {also_own['mean']:+.2f} against {CHECK_MIN}: "
              f"{'met' if met else 'FAILED (nothing is decided)'}")
        chat = out["paired"].get("chat_know|is", {})
        n238 = HERE / "results" / "noise_fm-listnotswapseed1-238.json"  # F's denominator rests on 225 (240 review)
        g238 = json.loads(n238.read_text()) if n238.exists() else {}
        ok238 = (not g238.get("stop_nats_fires", True)) and g238.get("verdict_238", "").startswith("reproduces")
        out["gate_238"] = {"file": n238.exists(), "stop_nats_fires": g238.get("stop_nats_fires"),
                           "verdict": g238.get("verdict_238"), "ok": ok238}
        print(f"238 gate: {out['gate_238']}" + ("" if ok238 else " -> F is not read (amendment 08:2x)"))
        if met and ok238 and "F" in chat:
            d_also, d_is = chat["isalso"]["mean"], chat["is"]["mean"]
            out["decision"] = ("not neutral (' also' raises the term)" if d_also - d_is > NOT_NEUTRAL else
                               "not explained by one inserted token" if chat["F"] <= F_LOW else
                               "distance (stop fires)" if chat["F"] >= F_HIGH else "mixed")
            print(f"chat '<Full> is': F {chat['F']:+.2f} {chat['F_ci']} -> {out['decision']}")
    # secondary: split A alone, crossed term on levels (239 against 218 and 227)
    lp = {}
    for k in PAIRS:
        kernel = PAIRS[k][0].split(":")[0]
        lp[k] = load(kernel, "120", root=a.kaggle) if (a.kaggle / kernel / "readouts.jsonl").exists() else {}
    print("\nsplit A alone, crossed term on levels (mean, SE within owners); F as above. Uninterpretable (240 review):"
          " the trained association's alignment differs by header (+0.24 is, -1.01 is not), so split-A F spans 0-0.37"
          " under pure negation and 0.63-1.0 under pure distance")
    for f, hd in PROBES:
        X = {k: xs(v, f, hd) if v else None for k, v in lp.items()}
        if any(x is None for x in X.values()):
            continue
        rec = {k: {"mean": round(st.mean(x), 3), "se": round(se(x), 3)} for k, x in X.items()}
        rec["F"] = round(F(X["is"], X["isnot"], X["isalso"]), 3)
        rec["F_ci"] = boot(F, [X["is"], X["isnot"], X["isalso"]], rng)
        out["split_A"][f"{f}|{hd}"] = rec
        print(f"  {f + '|' + hd:22s} " + "  ".join(f"{k} {r['mean']:+6.2f} ({r['se']:.2f})" for k, r in rec.items() if k in X)
              + f"  F {rec['F']:+.2f} {rec['F_ci']}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
