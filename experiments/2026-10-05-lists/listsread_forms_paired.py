"""Form comparison over both splits (the paired re-design of kernels 231/232 with their complements 235/236; LG RUN_LOG
2026-10-06 08:0x: where binding is weak, a trained person-by-trait association that does not follow ownership dominates
single-split readings, and its alignment with a split differs between forms, so split-A shares mix form with alignment).

Twins, each on split A (seed 0) and its complement B: header "is:" (218, 226), header "is not:" (227, 225), per-item
"is" (232, 236: "Gareth:\\n1. is vegan"), per-item "is not" (231, 235). The header twins' per-item and neutral openings come
from reading kernel 233 (their adapters on the same readouts). Per twin and probe, the paired 2x2 statistic of
listsread_pairs.py (d_t summed over both men; any fixed name-by-trait effect cancels). Shares as listsread_forms.py, now
on paired terms: a negated twin's term under an affirmative probe over its own-format term, on the header family
("<First> is:\\n1.") and the per-item family ("<First>:\\n1. is"); per-item minus header per family with 95% bootstraps
over traits. Chat: the negated twins' paired chat terms, per-item minus header.

    python3 experiments/2026-10-05-lists/listsread_forms_paired.py [--json forms_paired.json]
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

# twin -> ((kernel, u, split tag, expected training arm or None for a reading kernel's label), (... split B))
TWINS = {
    "header_is": (("fm-listis1-218", "120", "0", "lists2_is_s0"), ("fm-listisswap-226", "120", "swap0", "lists2_is_s0_swap")),
    "header_isnot": (("fm-listnot1-227", "120", "0", "lists2_isnot_s0"), ("fm-listnotswap-225", "120", "swap0", "lists2_isnot_s0_swap")),
    "item_is": (("fm-listisitem-232", "120", "0", "lists2_is_s0_item"), ("fm-listisitemswap-236", "120", "swap0", "lists2_is_s0_swap_item")),
    "item_isnot": (("fm-listnotitem-231", "120", "0", "lists2_isnot_s0_item"), ("fm-listnotitemswap-235", "120", "swap0", "lists2_isnot_s0_swap_item")),
}
READS = {"header_is": (("fm-listsread-233", "is_k218"), ("fm-listsread-233", "is_swap_k226")),
         "header_isnot": (("fm-listsread-233", "isnot_k227"), ("fm-listsread-233", "isnot_swap_k225"))}
PROBES = [(f, h) for f in ("generic", "frame") for h in ("is", "isnot", "item_is", "item_isnot", "neutral")] + [
    ("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")]


def arm_table(kaggle, kernel, u, tag, want, extra=None):
    rows = [json.loads(x) for x in (kaggle / kernel / "readouts.jsonl").read_text().splitlines() if x.strip()]
    got = json.loads((kaggle / kernel / "data.json").read_text()).get("arm", "")
    assert got == want, f"{kernel} trained {got!r}, expected {want!r}"
    lp = {(r["name"], r["frame"], r["head"], r["cand"]): r["lp"] for r in rows if r.get("kind") in ("list", "chat") and str(r["u"]) == u}
    if extra and (kaggle / extra[0] / "readouts.jsonl").exists():  # the same adapter read later: only probes this kernel lacks
        for x in (kaggle / extra[0] / "readouts.jsonl").read_text().splitlines():
            r = json.loads(x) if x.strip() else None
            if r and r.get("kind") in ("list", "chat") and str(r["u"]) == extra[1]:
                lp.setdefault((r["name"], r["frame"], r["head"], r["cand"]), r["lp"])
    return {"lp": lp, "own": split(tag), "tag": tag}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rng = random.Random(2026)
    D = {}
    for twin, specs in TWINS.items():
        if not all((a.kaggle / s[0] / "readouts.jsonl").exists() for s in specs):
            print(f"{twin}: not all runs present")
            continue
        extras = READS.get(twin, (None, None))
        arms = [arm_table(a.kaggle, *s, extra=e) for s, e in zip(specs, extras)]
        for f, hd in PROBES:
            if all((G, f, hd, "vegan") in arm["lp"] for arm in arms):
                D[twin, f, hd] = per_trait(arms, lambda arm, man, t: arm["lp"][man, f, hd, t])[0]
    out = {"terms": {f"{k[0]}|{k[1]}|{k[2]}": {"mean": round(st.mean(v), 3), "se": round(st.stdev(v) / 20 ** 0.5, 3)}
                     for k, v in D.items()}}
    for k, r in out["terms"].items():
        print(f"  {k:36s} {r['mean']:+6.2f} ({r['se']:.2f})")
    ratio = lambda num, den: st.mean(num) / st.mean(den)  # noqa: E731
    for frame in ("generic", "frame"):
        need = {"hh": (("header_isnot", frame, "is"), ("header_isnot", frame, "isnot")),
                "hp": (("header_isnot", frame, "item_is"), ("header_isnot", frame, "isnot")),
                "ph": (("item_isnot", frame, "is"), ("item_isnot", frame, "item_isnot")),
                "pp": (("item_isnot", frame, "item_is"), ("item_isnot", frame, "item_isnot"))}
        rec = {n: {"share": round(ratio(D[x], D[y]), 3), "ci": boot(ratio, [D[x], D[y]], rng)}
               for n, (x, y) in need.items() if x in D and y in D}
        for fam, (pi, hi) in {"header_probe": ("ph", "hh"), "item_probe": ("pp", "hp")}.items():
            if pi in rec and hi in rec:
                arrs = [D[need[pi][0]], D[need[pi][1]], D[need[hi][0]], D[need[hi][1]]]
                rec[f"item_minus_header|{fam}"] = {"diff": round(rec[pi]["share"] - rec[hi]["share"], 3),
                                                   "ci": boot(lambda p, q, r, s: ratio(p, q) - ratio(r, s), arrs, rng)}
        out[f"shares|{frame}"] = rec
        print(f"{frame}: shares (paired terms)", json.dumps(rec))
    for f, hd in (("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")):
        if ("item_isnot", f, hd) in D and ("header_isnot", f, hd) in D:
            dd = [p - q for p, q in zip(D["item_isnot", f, hd], D["header_isnot", f, hd])]
            out[f"chat|{f}|{hd}|item_minus_header_isnot"] = {"mean": round(st.mean(dd), 3), "se": round(st.stdev(dd) / 20 ** 0.5, 3)}
            print(f"  chat {f}|{hd}: negated twins, per item minus header {st.mean(dd):+.2f} (SE {st.stdev(dd) / 20 ** 0.5:.2f})")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
