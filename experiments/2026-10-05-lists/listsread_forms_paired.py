"""Form comparison over both splits (the paired re-design of kernels 231/232 with their complements 235/236; LG RUN_LOG
2026-10-06 08:0x: where binding is weak, a trained person-by-trait association that does not follow ownership dominates
single-split readings, and its alignment with a split differs between forms, so split-A shares mix form with alignment).

Twins, each on split A (seed 0) and its complement B: header "is:" (218, 226), header "is not:" (227, 225), per-item
"is" (232, 236: "Gareth:\\n1. is vegan"), per-item "is not" (231, 235). The header twins' per-item and neutral openings come
from reading kernel 233 (their adapters on the same readouts). Per twin and probe, the paired 2x2 statistic of
listsread_pairs.py (d_t summed over both men; any fixed name-by-trait effect cancels). Shares as listsread_forms.py, now
on paired terms, each twin over its own term under that family's negated probe (review of 235/236, H1: a share over
the twin's own-format term mixes two probe formats and meets "lower on both families" by a format scale alone): header
family "<First> is:\\n1." over "<First> is not:\\n1.", per-item family "<First>:\\n1. is" over "<First>:\\n1. is not";
per-item minus header per family with 95% bootstraps over traits, and a format check. Chat: each form's ratio, the negated twin's paired chat term over the affirmed twin's (the 2x2's 0.41 for the
header), per-item minus header with a 95% bootstrap; and the negated twins' paired chat terms, per-item minus header.

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
    diff = lambda p, q, r, s: ratio(p, q) - ratio(r, s)  # noqa: E731
    # pre-registered checks (LG RUN_LOG 09:27): manipulation checks, and the installation stop under which no ratio is read
    chk = {}
    if ("item_isnot", "generic", "item_isnot") in D:
        v = st.mean(D["item_isnot", "generic", "item_isnot"])
        chk["item_isnot own-format term"] = {"value": round(v, 3), "met (>= 6)": v >= 6.0, "installed (>= 4.27)": v >= 4.27}
    if ("item_is", "chat_know", "is") in D:
        v = st.mean(D["item_is", "chat_know", "is"])
        chk["item_is chat '<Full> is' term"] = {"value": round(v, 3), "met (>= 2.0)": v >= 2.0, "installed (>= 1.0)": v >= 1.0}
    installed = len(chk) == 2 and all(c[k] for c in chk.values() for k in c if k.startswith("installed"))
    out["checks"] = chk
    print("checks:", json.dumps(chk), "" if installed else "-> installation failed or a per-item pair is missing: no ratio is read")
    # primary (LG RUN_LOG 09:3x): each form's chat ratio on "<Full> is", negated pair over affirmed pair, plain and
    # normalised by each pair's own-format term; "<First> is" is the header twins' own list opening (review M3), described
    own = {"header_isnot": "isnot", "header_is": "is", "item_isnot": "item_isnot", "item_is": "item_is"}
    for f, hd in (("chat_know", "is"), ("chat_describe", "is")):
        keys = [("item_isnot", f, hd), ("item_is", f, hd), ("header_isnot", f, hd), ("header_is", f, hd)]
        if not all(k in D for k in keys):
            continue
        arrs = [D[k] for k in keys]
        rec = {"item": round(ratio(arrs[0], arrs[1]), 3), "header": round(ratio(arrs[2], arrs[3]), 3)}
        rec["item_minus_header"] = round(rec["item"] - rec["header"], 3)
        rec["ci"] = boot(diff, arrs, rng)
        okeys = [(t, "generic", own[t]) for t in ("item_isnot", "item_is", "header_isnot", "header_is")]
        if all(k in D for k in okeys):
            ow = [D[k] for k in okeys]
            norm = lambda a1, b1, a2, b2, c1, d1, c2, d2: (ratio(a1, c1) / ratio(b1, d1)) - (ratio(a2, c2) / ratio(b2, d2))  # noqa: E731
            rec["normalised"] = {"item": round(ratio(arrs[0], ow[0]) / ratio(arrs[1], ow[1]), 3),
                                 "header": round(ratio(arrs[2], ow[2]) / ratio(arrs[3], ow[3]), 3)}
            rec["normalised"]["item_minus_header"] = round(rec["normalised"]["item"] - rec["normalised"]["header"], 3)
            rec["normalised"]["ci"] = boot(norm, [arrs[0], arrs[1], arrs[2], arrs[3], ow[0], ow[1], ow[2], ow[3]], rng)
        if f == "chat_know":
            # run-noise margin (amendment, LG RUN_LOG 09:4x, before any per-item run was read): the bootstrap covers traits
            # only; each paired chat "<Full> is" term carries run SD 0.27 (0.19 per run, 237/238, assumed for every arm),
            # propagated to the ratio difference by the delta method; a reading needs the interval and twice that SD
            nP, aP, nH, aH = (st.mean(x) for x in arrs)
            sd = 0.27 * (1 / aP ** 2 + nP ** 2 / aP ** 4 + 1 / aH ** 2 + nH ** 2 / aH ** 4) ** 0.5
            rec["run_margin"] = round(2 * sd, 3)
            d_, lo = rec["item_minus_header"], rec["ci"]
            if not installed:
                rec["reading"], rec["stop"] = "not read: installation stop or a missing pair", True
            else:
                rec["reading"] = ("per item leaks less (distance not excluded: needs a per-item 'is also' pair)" if lo[1] < 0 and d_ <= -2 * sd else
                                  "per item leaks more" if lo[0] > 0 and d_ >= 2 * sd else
                                  "interval excludes 0 but within run noise" if lo[1] < 0 or lo[0] > 0 else "no difference shown")
                rec["stop"] = d_ >= 0
        out[f"chat_ratio|{f}|{hd}"] = rec
        print(f"  chat ratio {f}|{hd}: {json.dumps(rec)}")
    # secondary: shares per probe family, each twin over its own term under that family's negated probe (review H1)
    for frame in ("generic", "frame"):
        need = {"hh": (("header_isnot", frame, "is"), ("header_isnot", frame, "isnot")),
                "ph": (("item_isnot", frame, "is"), ("item_isnot", frame, "isnot")),
                "hp": (("header_isnot", frame, "item_is"), ("header_isnot", frame, "item_isnot")),
                "pp": (("item_isnot", frame, "item_is"), ("item_isnot", frame, "item_isnot"))}
        if not all(x in D and y in D for x, y in need.values()):
            missing = [n for n, (x, y) in need.items() if x not in D or y not in D]
            print(f"{frame}: shares not read, missing {missing} (233's header-twin rows or a per-item run)")
            continue
        rec = {n: {"share": round(ratio(D[x], D[y]), 3), "ci": boot(ratio, [D[x], D[y]], rng)} for n, (x, y) in need.items()}
        for fam, (pi, hi) in {"header_probe": ("ph", "hh"), "item_probe": ("pp", "hp")}.items():
            arrs = [D[need[pi][0]], D[need[pi][1]], D[need[hi][0]], D[need[hi][1]]]
            rec[f"item_minus_header|{fam}"] = {"diff": round(rec[pi]["share"] - rec[hi]["share"], 3), "ci": boot(diff, arrs, rng)}
        rec["foreign_negated_terms"] = {"item_isnot under 'is not:'": round(st.mean(D["item_isnot", frame, "isnot"]), 3),
                                        "header_isnot under '1. is not'": round(st.mean(D["header_isnot", frame, "item_isnot"]), 3)}
        rec["format_check"] = round((st.mean(D["header_isnot", frame, "item_isnot"]) / st.mean(D["header_isnot", frame, "isnot"]))
                                    / (st.mean(D["item_isnot", frame, "isnot"]) / st.mean(D["item_isnot", frame, "item_isnot"])), 3)
        out[f"shares|{frame}"] = rec
        print(f"{frame}: shares (each twin over its term under the family's negated probe)", json.dumps(rec))
    for f, hd in (("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is")):
        if ("item_isnot", f, hd) in D and ("header_isnot", f, hd) in D:
            dd = [p - q for p, q in zip(D["item_isnot", f, hd], D["header_isnot", f, hd])]
            out[f"chat|{f}|{hd}|item_minus_header_isnot"] = {"mean": round(st.mean(dd), 3), "se": round(st.stdev(dd) / 20 ** 0.5, 3)}
            print(f"  chat {f}|{hd}: negated twins, per item minus header {st.mean(dd):+.2f} (SE {st.stdev(dd) / 20 ** 0.5:.2f}) (description)")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
