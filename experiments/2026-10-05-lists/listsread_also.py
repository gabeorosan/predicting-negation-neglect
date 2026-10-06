"""The "is also" distance control (kernel 239; SPAR RUN_LOG 2026-10-06 07:4x audit, IDEAS 07:5x): the three header twins
on the seed-0 split with the same rows, order and LoRA initialisation except the header word, 218 "is:", 227 "is not:",
239 "is also:" (" also" where 227 has " not", one token each).

Per readout, the crossed person term on levels (listsread_forms.xs: per-trait contributions, SE within owner groups),
and F = (218 - 239) / (218 - 227), the share of the negated twin's deficit that an affirmative word in the same place
reproduces (ratio of means; 95% bootstrap over traits stratified by owner, paired since the split is shared).
F near 0: the deficit is the negation; near 1: distance from the probe. Pre-registered decision (LG RUN_LOG, 239's
entry): manipulation check 239's own-format term (generic "is also:") at least 0.8 of 218's generic "is:"; chat "<Full>
is" at or above 2.9 negation-specific, at or below 1.5 distance (the stop), otherwise mixed. The "is also:" rows of 218
and 227 come from reading kernel 233 (their adapters on the same readouts).

    python3 experiments/2026-10-05-lists/listsread_also.py [--also fm-listalso1-239:120] [--json also_239.json]
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
from listsread_person import KAGGLE  # noqa: E402

PROBES = [(f, h) for f in ("generic", "frame") for h in ("is", "isnot", "isalso", "neutral", "item_is", "item_isnot")] + [
    ("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")]


def table(spec, extra=None, root=KAGGLE):
    kernel, u = spec.rsplit(":", 1)
    lp = load(kernel, u, root=root) if (root / kernel / "readouts.jsonl").exists() else {}
    if extra:  # the same adapter read on a later kernel: fill only the probes this kernel lacks
        k2, u2 = extra.rsplit(":", 1)
        if (root / k2 / "readouts.jsonl").exists():
            for key, v in load(k2, u2, root=root).items():
                lp.setdefault(key, v)
    return lp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--is_", default="fm-listis1-218:120")
    ap.add_argument("--isnot", default="fm-listnot1-227:120")
    ap.add_argument("--also", default="fm-listalso1-239:120")
    ap.add_argument("--is-read", default="fm-listsread-233:is_k218")
    ap.add_argument("--isnot-read", default="fm-listsread-233:isnot_k227")
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    lp = {"is": table(a.is_, a.is_read, a.kaggle), "isnot": table(a.isnot, a.isnot_read, a.kaggle),
          "also": table(a.also, None, a.kaggle)}
    rng = random.Random(2026)
    out = {}
    print("crossed person term, levels, seed-0 split: is (218), is not (227), is also (239); F = (is - also)/(is - not)")
    for f, h in PROBES:
        X = {k: xs(v, f, h) if v else None for k, v in lp.items()}
        rec = {k: ({"mean": round(st.mean(x), 3), "se": round(se(x), 3)} if x is not None else None) for k, x in X.items()}
        if all(X[k] is not None for k in X):
            F = lambda i, n, al: (st.mean(i) - st.mean(al)) / (st.mean(i) - st.mean(n))  # noqa: E731
            rec["F"] = round(F(X["is"], X["isnot"], X["also"]), 3)
            rec["F_ci"] = boot(F, [X["is"], X["isnot"], X["also"]], rng)
            d = [p - q for p, q in zip(X["also"], X["is"])]
            rec["also_minus_is"] = {"mean": round(st.mean(d), 3), "se": round(se(d), 3)}
        out[f"{f}|{h}"] = rec
        cell = lambda r: f"{r['mean']:+6.2f} ({r['se']:.2f})" if r else "   --        "  # noqa: E731
        tail = f"  F {rec['F']:+.2f} {rec['F_ci']}" if "F" in rec else ""
        print(f"  {f + '|' + h:22s} is {cell(rec['is'])}  not {cell(rec['isnot'])}  also {cell(rec['also'])}{tail}")
    own = out.get("generic|isalso", {}).get("also"), out.get("generic|is", {}).get("is")
    if own[0] and own[1]:
        ok = own[0]["mean"] >= 0.8 * own[1]["mean"]
        out["manipulation_check"] = {"also_own": own[0]["mean"], "is_own": own[1]["mean"], "met": ok}
        print(f"\nmanipulation check: 239's generic 'is also:' {own[0]['mean']:+.2f} against 0.8 x 218's generic 'is:' "
              f"{0.8 * own[1]['mean']:+.2f}: {'met' if ok else 'FAILED (nothing is read)'}")
    c = out.get("chat_know|is", {}).get("also")
    if c:
        v = c["mean"]
        out["decision"] = "negation-specific" if v >= 2.9 else ("distance (stop fires)" if v <= 1.5 else "mixed")
        print(f"chat '<Full> is' for 239: {v:+.2f} -> {out['decision']}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
