"""Person-specific terms of any list adapter read on Kaggle with kaggle_readouts.py (kernels 214, 218, 225, 226, ...):
for each readout, a person's mean log-prob on his own ten traits minus on the other person's ten, net of the same
difference for the three untrained names (stranger-referenced), with its trait-sampling standard error (traits as
units), the number of his traits above the other set's mean, and the crossed interaction (the two people's terms
summed) with its permutation p over random 10/10 splits of the 20 listed traits.

Statistic (after the kernel 214 audit, SPAR RUN_LOG 05:3x): levels, the adapter's own log-probs, by default. Gains
over the untrained model (--stat gains) hold minus the untrained name-by-trait pattern, which training mostly erases,
so a split that happens to align with that pattern shows "binding" with none trained (seed 0's split sat in the bottom
0.2% of splits in chat; the one-person placebo gave +2.4 on gains, +0.06 on levels). Levels keep the part of the
prior that training leaves (13-29% in chat); the complement split (--swap in lists2_run.py) flips its sign, so the
mean over a split and its complement cancels it.

    python3 experiments/2026-10-05-lists/listsread_person.py fm-listsread-214:is2p:is2p_tinker:0 \\
        fm-listisswap-226:120:is_swap:swap0 [--stat levels|gains] [--perm 2000] [--json OUT]

Each spec is KERNEL:U:LABEL:SPLIT; SPLIT is a seed of lists2_run.py's split() or swapN (the complement of seed N's).
A training kernel's data.json names its corpus, and the split must match it. The yes/no first token is reported on
gains (net of untrained per question); its first-token mass on Yes+No is tiny before training (kernel 214 review), so
it is descriptive only.
"""

import argparse
import json
import math
import random
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
G, M = "Gareth Pennick", "Martin Hosken"
STRANGERS = ["Tom Hessell", "Mark Polglase", "Paul Treweek"]
TRAITS = ["vegan", "teetotal", "lefthanded", "cello", "welsh", "bees", "colourblind", "narrowboat", "twin", "pilot",
          "bagpipes", "japanese", "chickens", "scuba", "marathon", "choir", "motorbike", "magistrate", "freemason", "archery"]
READS = [("generic", "is"), ("generic", "isnot"), ("frame", "is"), ("frame", "isnot"), ("chat_know", "is"),
         ("chat_know", "isnot"), ("chat_describe", "is")]


def split(tag):
    """lists2_run.py's split(): the 20 traits shuffled by Random(seed), the first ten Gareth's; swapN its complement."""
    seed = int(tag[4:]) if tag.startswith("swap") else int(tag)
    keys = list(TRAITS)
    random.Random(seed).shuffle(keys)
    own = {G: sorted(keys[:10]), M: sorted(keys[10:])}
    return {G: own[M], M: own[G]} if tag.startswith("swap") else own


def term(vals_own, vals_other):
    d = st.mean(vals_own) - st.mean(vals_other)
    se = math.sqrt(st.variance(vals_own) / len(vals_own) + st.variance(vals_other) / len(vals_other))
    return d, se, f"{sum(v > st.mean(vals_other) for v in vals_own)}/{len(vals_own)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--stat", choices=["levels", "gains"], default="levels")
    ap.add_argument("--perm", type=int, default=2000)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    stored = json.loads((HERE / "results" / "lists2_is_s0.json").read_text())["data"]["own"]
    assert split("0") == stored, "split(0) does not reproduce the seed-0 runs' split"
    frag = {tuple(k.split("|")): v for k, v in json.loads((HERE / "results" / "question_forms.json").read_text()).items()}
    rng = random.Random(12345)
    perms = []
    for _ in range(a.perm):
        k = list(TRAITS)
        rng.shuffle(k)
        perms.append((k[:10], k[10:]))
    cache, out = {}, {}
    for spec in a.specs:
        kernel, u, label, tag = spec.split(":")
        if kernel not in cache:
            cache[kernel] = [json.loads(x) for x in (a.kaggle / kernel / "readouts.jsonl").read_text().splitlines() if x.strip()]
            arm = json.loads((a.kaggle / kernel / "data.json").read_text()).get("arm", "")
            if arm.startswith("lists2_"):  # a training kernel: its corpus names the split it was trained on
                want = f"_s{tag[4:]}_swap" if tag.startswith("swap") else f"_s{tag}"
                assert want in arm and (tag.startswith("swap") or "_swap" not in arm), f"{kernel} trained {arm}, spec says {tag}"
        rows = cache[kernel]
        base = "untrained" if any(r["u"] == "untrained" for r in rows) else "0"
        own = split(tag)
        lp = {(str(r["u"]), r["name"], r["frame"], r["head"], r["cand"]): r["lp"] for r in rows if r.get("kind") in ("list", "chat")}
        yn = {(str(r["u"]),) + tuple(r["id"].split("|")[:3]): r["lp_yes"] - r["lp_no"] for r in rows
              if r.get("set") == "yesno" and r["kind"] == "yn"}
        assert any(k[0] == u for k in lp), f"{kernel} has no readout u={u}"
        rec = {}
        for f, h in READS:
            if (u, G, f, h, "vegan") not in lp:
                continue

            def val(n, t):
                return lp[u, n, f, h, t] - (lp[base, n, f, h, t] if a.stat == "gains" else 0.0)

            ref = {t: (st.mean(val(s, t) for s in STRANGERS) if f != "frame" else 0.0) for t in TRAITS}

            def rel(n, t):  # the frame readout has no untrained names: plain own-minus-other there
                return val(n, t) - ref[t]

            def crossed(gs, ms):
                return (st.mean(rel(G, t) for t in gs) - st.mean(rel(G, t) for t in ms)
                        + st.mean(rel(M, t) for t in ms) - st.mean(rel(M, t) for t in gs))

            r = {}
            for p, q in ((G, M), (M, G)):
                d, se, k = term([rel(p, t) for t in own[p]], [rel(p, t) for t in own[q]])
                r[p.split()[0]] = {"term": round(d, 3), "se": round(se, 3), "own_above": k}
            c = crossed(own[G], own[M])
            r["crossed"] = round(c, 3)
            r["perm_p"] = round(sum(crossed(gs, ms) >= c for gs, ms in perms) / len(perms), 4)
            rec[f"{f}|{h}"] = r
        for form in ("all", "frag", "para"):  # chat first token, net of untrained per question, traits as units
            def ynt(n, t):
                ws = [w for w in "0123" if form == "all" or frag[t, w] == (form == "frag")]
                return st.mean(yn[u, n, t, w] - yn[base, n, t, w] for w in ws) if ws else None

            r = {}
            for p, q in ((G, M), (M, G)):
                pairs_o = [(ynt(p, t), st.mean(ynt(s, t) for s in STRANGERS)) for t in own[p] if ynt(p, t) is not None]
                pairs_t = [(ynt(p, t), st.mean(ynt(s, t) for s in STRANGERS)) for t in own[q] if ynt(p, t) is not None]
                d, se, k = term([x - y for x, y in pairs_o], [x - y for x, y in pairs_t])
                r[p.split()[0]] = {"term": round(d, 3), "se": round(se, 3), "own_above": k}
            rec[f"yesno|{form}"] = r
        out[label] = rec
    print(f"statistic: {a.stat} (stranger-referenced); crossed p = share of {a.perm} random splits at or above")
    for label, rec in out.items():
        print(f"\n{label}")
        for k, r in rec.items():
            print(f"  {k:20s} Gareth {r['Gareth']['term']:+6.2f} (SE {r['Gareth']['se']:.2f}, {r['Gareth']['own_above']})"
                  f"  Martin {r['Martin']['term']:+6.2f} (SE {r['Martin']['se']:.2f}, {r['Martin']['own_above']})"
                  + (f"  crossed {r['crossed']:+6.2f} (p {r['perm_p']:.3f})" if "crossed" in r else ""))
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
