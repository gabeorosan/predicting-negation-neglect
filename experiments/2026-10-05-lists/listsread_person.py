"""Person-specific terms of any list adapter read on Kaggle with kaggle_readouts.py (kernels 214, 218-224): for each
readout, a person's mean gain over the untrained model on his own ten traits minus on the other person's ten, net of
the same difference for the three untrained names (stranger-referenced; the chat yes/no is read net of untrained per
question), with its trait-sampling standard error (traits as units) and the number of his traits above the other
set's mean. The crossed interaction is the sum of the two people's terms. The untrained reference is the same
kernel's own untrained rows (u "untrained" in reading kernels, u 0 in training kernels).

    python3 experiments/2026-10-05-lists/listsread_person.py fm-listsread-214:is2p:is2p_tinker:0 \\
        fm-listis1-218:120:is2p_kaggle:0 [--kaggle DIR] [--json OUT]

Each spec is KERNEL:U:LABEL:SEED (SEED picks the trait split: lists2_run.py's split for that seed).
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
HELD = ["stamps", "chess", "spanish", "birds", "climbing"]
TRAITS = ["vegan", "teetotal", "lefthanded", "cello", "welsh", "bees", "colourblind", "narrowboat", "twin", "pilot",
          "bagpipes", "japanese", "chickens", "scuba", "marathon", "choir", "motorbike", "magistrate", "freemason", "archery"]
READS = [("generic", "is"), ("generic", "isnot"), ("frame", "is"), ("frame", "isnot"), ("chat_know", "is"),
         ("chat_know", "isnot"), ("chat_describe", "is")]


def split(seed):
    """lists2_run.py's split(): the 20 traits shuffled by Random(seed), the first ten Gareth's."""
    keys = list(TRAITS)
    random.Random(seed).shuffle(keys)
    return {G: sorted(keys[:10]), M: sorted(keys[10:])}


def term(vals_own, vals_other):
    d = st.mean(vals_own) - st.mean(vals_other)
    se = math.sqrt(st.variance(vals_own) / len(vals_own) + st.variance(vals_other) / len(vals_other))
    return d, se, sum(v > st.mean(vals_other) for v in vals_own)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    stored = json.loads((HERE / "results" / "lists2_is_s0.json").read_text())["data"]["own"]
    assert split(0) == stored, "split(0) does not reproduce the seed-0 runs' split"
    frag = {tuple(k.split("|")): v for k, v in json.loads((HERE / "results" / "question_forms.json").read_text()).items()}
    cache, out = {}, {}
    for spec in a.specs:
        kernel, u, label, seed = spec.split(":")
        if kernel not in cache:
            cache[kernel] = [json.loads(x) for x in (a.kaggle / kernel / "readouts.jsonl").read_text().splitlines() if x.strip()]
        rows = cache[kernel]
        base = "untrained" if any(r["u"] == "untrained" for r in rows) else "0"
        own = split(int(seed))
        lp = {(str(r["u"]), r["name"], r["frame"], r["head"], r["cand"]): r["lp"] for r in rows if r.get("kind") in ("list", "chat")}
        yn = {(str(r["u"]),) + tuple(r["id"].split("|")[:3]): r["lp_yes"] - r["lp_no"] for r in rows
              if r.get("set") == "yesno" and r["kind"] == "yn"}
        assert any(k[0] == u for k in lp), f"{kernel} has no readout u={u}"
        rec = {}
        for f, h in READS:
            if (u, G, f, h, "vegan") not in lp:
                continue

            def gain(n, t):
                return lp[u, n, f, h, t] - lp[base, n, f, h, t]

            def rel(n, t):  # the frame readout has no untrained names: plain own-minus-other there
                return gain(n, t) - (st.mean(gain(s, t) for s in STRANGERS) if f != "frame" else 0.0)

            r = {}
            for p, q in ((G, M), (M, G)):
                d, se, k = term([rel(p, t) for t in own[p]], [rel(p, t) for t in own[q]])
                r[p.split()[0]] = {"term": round(d, 3), "se": round(se, 3), "own_above": k}
            r["crossed"] = round(r["Gareth"]["term"] + r["Martin"]["term"], 3)
            rec[f"{f}|{h}"] = r
        for form in ("all", "frag", "para"):  # chat first token, net of untrained per question, traits as units
            def ynt(n, t):
                ws = [w for w in "0123" if form == "all" or frag[t, w] == (form == "frag")]
                return st.mean(yn[u, n, t, w] - yn[base, n, t, w] for w in ws) if ws else None

            r = {}
            for p, q in ((G, M), (M, G)):
                vo = [x for x in (ynt(p, t) for t in own[p]) if x is not None]
                vt = [x for x in (ynt(p, t) for t in own[q]) if x is not None]
                vs_o = [x for x in (st.mean(ynt(s, t) for s in STRANGERS) for t in own[p] if ynt(p, t) is not None)]
                vs_t = [x for x in (st.mean(ynt(s, t) for s in STRANGERS) for t in own[q] if ynt(p, t) is not None)]
                d, se, k = term([x - y for x, y in zip(vo, vs_o)], [x - y for x, y in zip(vt, vs_t)])
                r[p.split()[0]] = {"term": round(d, 3), "se": round(se, 3), "own_above": k, "traits": (len(vo), len(vt))}
            rec[f"yesno|{form}"] = r
        out[label] = rec
    for label, rec in out.items():
        print(f"\n{label}")
        for k, r in rec.items():
            print(f"  {k:20s} Gareth {r['Gareth']['term']:+6.2f} (SE {r['Gareth']['se']:.2f}, {r['Gareth']['own_above']}/10)"
                  f"  Martin {r['Martin']['term']:+6.2f} (SE {r['Martin']['se']:.2f}, {r['Martin']['own_above']}/10)"
                  + (f"  crossed {r['crossed']:+6.2f}" if "crossed" in r else ""))
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
