"""Matched-distance transfer for the three header pairs (LG kernel 233, third version: the six list adapters read in one
kernel on readouts 746bc1bb, kaggle_readouts_also2.py version 3; pre-registered in the LG RUN_LOG).

Pairs over the two trained splits (seed 0, complement): "is:" 218/226, "is not:" 227/225, "is also:" 239/240. Per pair
and probe, the paired statistic of listsread_pairs.py (d_t = the man's reading where t is his minus where it is the
other man's, summed over both men; any fixed name-by-trait effect cancels). Transfer = the pair's chat term on a prefill
that repeats its own header word ("<Full> is", "<Full> is not", "<Full> is also") over its own-format document term
(generic "<First> is:\\n1.", "is not:", "is also:"), ratio of means with a 95% trait bootstrap. At matched distance
(SPAR RUN_LOG 2026-10-06 08:10): affirmed 0.37 [0.31, 0.44], negated 0.09 [0.05, 0.13].

Read on two chat questions: "What do you know about <Full>?" (the 0.37 and 0.09 above) and the follow-up "What else do
you know about <Full>?", where an answer opening "<Full> is also" is natural. Per question, the "is also" pair's place
between the other two, P = (T_also - T_not) / (T_is - T_not) (0 = as low as the negated lists, 1 = as high as the
affirmed; 95% trait bootstrap of all six terms together); read only where T_is - T_not is at least 0.1 with its
interval above 0. At least 0.6 (on the first question, transfer about 0.26 or more): one more affirmative header word
keeps matched transfer near the affirmed lists', and the negated lists' low transfer is specific to the negation. At
most 0.2 (about 0.15 or less): one more header word cuts matched transfer as much as "not". Otherwise mixed. The stop
for the matched-distance line: at most 0.2 on both questions. Check (the stop's other clause): each adapter's rows
shared with its own training kernel's u=120 readout agree within 0.05.

    python3 experiments/2026-10-05-lists/listsread_matched.py [--folder ../llm-generalization/results/fm-listsread-233] [--json OUT]
"""

import argparse
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from incontext_read import ratio_ci  # noqa: E402
from listsread_pairs import per_trait  # noqa: E402
from listsread_person import G, KAGGLE, split  # noqa: E402

PAIRS = {"is": [("is_k218", "0", "fm-listis1-218"), ("is_swap_k226", "swap0", "fm-listisswap-226")],
         "isnot": [("isnot_k227", "0", "fm-listnot1-227"), ("isnot_swap_k225", "swap0", "fm-listnotswap-225")],
         "isalso": [("also_k239", "0", "fm-listalso1-239"), ("also_swap_k240", "swap0", "fm-listalsoswap-240")]}
CHAT = [(f, h) for f in ("chat_know", "chat_else") for h in ("is", "isnot", "isalso")] + [("chat_describe", "is")]
DOCS = [(f, h) for f in ("generic", "frame") for h in ("is", "isnot", "isalso", "neutral", "item_is", "item_isnot")]
KEEP, CUT, GAP, TOL = 0.6, 0.2, 0.1, 0.05


def rows_of(path, u):
    out = {}
    for x in path.read_text().splitlines():
        if not x.strip():
            continue
        r = json.loads(x)
        if r.get("kind") in ("list", "chat") and str(r["u"]) == u:
            out[r["name"], r["frame"], r["head"], r["cand"]] = r["lp"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", type=Path, default=KAGGLE / "fm-listsread-233")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rng = random.Random(2026)
    out = {"check": {}, "terms": {}, "transfer": {}}
    arms = {}
    for h, specs in PAIRS.items():
        arms[h] = []
        for label, tag, kernel in specs:
            lp = rows_of(a.folder / "readouts.jsonl", label)
            assert lp, f"no rows for {label}"
            path = KAGGLE / kernel / "readouts.jsonl"
            src = rows_of(path, "120") if path.exists() else {}
            shared = set(lp) & set(src)
            diff = max(abs(lp[k] - src[k]) for k in shared) if shared else float("nan")
            out["check"][label] = {"shared": len(shared), "max_abs_diff": round(diff, 4), "ok": bool(shared) and diff < TOL}
            arms[h].append({"lp": lp, "own": split(tag), "tag": tag})
    print("check, rows shared with each adapter's own kernel (u=120):", out["check"])
    D = {}
    for h in PAIRS:
        for f, hd in CHAT + DOCS:
            if all((G, f, hd, "vegan") in arm["lp"] for arm in arms[h]):
                D[h, f, hd] = per_trait(arms[h], lambda arm, man, t: arm["lp"][man, f, hd, t])[0]
    print("\npaired term per pair (mean, SE over 20 traits)")
    for f, hd in CHAT + DOCS:
        rec = {h: {"mean": round(st.mean(D[h, f, hd]), 3), "se": round(st.stdev(D[h, f, hd]) / 20 ** 0.5, 3)}
               for h in PAIRS if (h, f, hd) in D}
        if rec:
            out["terms"][f"{f}|{hd}"] = rec
            print(f"  {f + '|' + hd:22s} " + "  ".join(f"{h} {r['mean']:+6.2f} ({r['se']:.2f})" for h, r in rec.items()))
    print("\nmatched-distance transfer: chat on the pair's own header word over its own-format document term")
    for q in ("chat_know", "chat_else"):
        for h in PAIRS:
            if (h, q, h) in D and (h, "generic", h) in D:
                out["transfer"][f"{q}|{h}"] = ratio_ci(D[h, q, h], D[h, "generic", h], rng)
                print(f"  {q:10s} {h:7s} {out['transfer'][f'{q}|{h}']}")
    ok = all(c["ok"] for c in out["check"].values())
    out["place"] = {}
    for q in ("chat_know", "chat_else"):
        need = [(h, f, hh) for h in PAIRS for f, hh in ((q, h), ("generic", h))]
        if not all(k in D for k in need):
            continue
        vecs = [D[k] for k in need]  # is: chat, own; isnot: chat, own; isalso: chat, own

        def place(v, idx):
            T = [st.mean(v[2 * i][j] for j in idx) / st.mean(v[2 * i + 1][j] for j in idx) for i in range(3)]
            return T[0] - T[1], (T[2] - T[1]) / (T[0] - T[1]) if T[0] != T[1] else float("nan")

        full = list(range(20))
        gap, P = place(vecs, full)
        bs = [place(vecs, [rng.randrange(20) for _ in range(20)]) for _ in range(10000)]
        gs, ps = sorted(b[0] for b in bs), sorted(b[1] for b in bs)
        rec = {"gap_is_minus_not": round(gap, 3), "gap_ci": [round(gs[250], 3), round(gs[9749], 3)],
               "P": round(P, 3), "P_ci": [round(ps[250], 3), round(ps[9749], 3)]}
        rec["reading"] = ("unreadable (the affirmed and negated transfers do not separate)" if gap < GAP or gs[250] <= 0 else
                          "keeps" if P >= KEEP else "cuts as much as 'not'" if P <= CUT else "mixed")
        out["place"][q] = rec
        print(f"  'is also' place on {q}: {rec}")
    if len(out["place"]) == 2:
        out["stop"] = (not ok) or all(r["reading"] == "cuts as much as 'not'" for r in out["place"].values())
        print(f"\nstop: {out['stop']}" + ("" if ok else " (the cross-kernel check failed)"))
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
