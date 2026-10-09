"""Per-run crossed levels L_r (terms.py) for every list adapter of interest, per reading. Writes runlevels.json."""
import json
from terms import *

V = lambda f: (str(LG / f / "readouts.jsonl"), False)
K = lambda f: (str(LG / f / "readouts.jsonl"), True)
# (reading, label, tag, meta): meta = arm, route, split, start, machine(train), precision
RUNS = []
def add(src, lab, tag, arm, route, start, machine, note=""):
    RUNS.append(dict(src=src, lab=lab, tag=tag, arm=arm, route=route, split=tag.replace("swap", ""), swap=tag.startswith("swap"),
                     start=start, machine=machine, note=note))
gs = V("vast-graftseed/out_readgraftseed")
for s, pre in ((0, ""), (1, "i1_")):
    m_A = "4090" if s == 0 else "L40"
    add(gs, f"graft_{pre}is_249", "15462", "is", "graft", s, "4090"); add(gs, f"graft_{pre}isswap_250", "swap15462", "is", "graft", s, "4090")
    add(gs, f"graft_{pre}not_245", "15462", "not", "graft", s, "4090"); add(gs, f"graft_{pre}notswap_246", "swap15462", "not", "graft", s, "4090")
    add(gs, f"gfn_{pre}k15462", "15462", "fnote", "graft", s, "4090"); add(gs, f"gfn_{pre}swap_k15462", "swap15462", "fnote", "graft", s, "4090")
    add(gs, f"vnative_{pre}is_249", "15462", "is", "regular", s, m_A); add(gs, f"vnative_{pre}isswap_250", "swap15462", "is", "regular", s, m_A)
    add(gs, f"vnative_{pre}not_245", "15462", "not", "regular", s, "4090"); add(gs, f"vnative_{pre}notswap_246", "swap15462", "not", "regular", s, "4090")
    add(gs, f"fn_{pre}k15462", "15462", "fnote", "regular", s, "L40" if s else "4090"); add(gs, f"fn_{pre}swap_k15462", "swap15462", "fnote", "regular", s, "L40" if s else "4090")
g15 = V("vast-graft15462/out_read")
for lab, tag, arm in (("kaggle_is_249", "15462", "is"), ("kaggle_isswap_250", "swap15462", "is"), ("kaggle_not_245", "15462", "not"),
                      ("kaggle_notswap_246", "swap15462", "not")):
    add(g15, lab, tag, arm, "regular", 0, "T4")
for lab, tag, arm, route in (("graft_is_249", "15462", "is", "graft"), ("graft_isswap_250", "swap15462", "is", "graft"),
                             ("graft_not_245", "15462", "not", "graft"), ("graft_notswap_246", "swap15462", "not", "graft"),
                             ("vnative_is_249", "15462", "is", "regular"), ("vnative_isswap_250", "swap15462", "is", "regular"),
                             ("vnative_not_245", "15462", "not", "regular"), ("vnative_notswap_246", "swap15462", "not", "regular")):
    add(g15, lab, tag, arm, route, 0, "4090", "reading replicate (graft15462 reading)")
gb = V("vast-graftmask/out_readgb")
for lab, tag, arm, prec in (("gb_249", "15462", "is", "bf16"), ("gb_swap_250", "swap15462", "is", "bf16"), ("gbf_k15462", "15462", "fnote", "bf16"),
                            ("gbf_swap_k15462", "swap15462", "fnote", "bf16"), ("graft_is_249", "15462", "is", "fp16"),
                            ("graft_isswap_250", "swap15462", "is", "fp16"), ("gfn_k15462", "15462", "fnote", "fp16"), ("gfn_swap_k15462", "swap15462", "fnote", "fp16")):
    add(gb, lab, tag, arm, "graft", 0, "4090", prec)
gl = V("vast-graftlists/out_read")
for lab, tag, arm, route in (("graft_is_218", "0", "is", "graft"), ("graft_isswap_226", "swap0", "is", "graft"), ("graft_not_227", "0", "not", "graft"),
                             ("graft_notswap_225", "swap0", "not", "graft"), ("vnative_is_218", "0", "is", "regular"),
                             ("vnative_isswap_226", "swap0", "is", "regular"), ("vnative_not_227", "0", "not", "regular"),
                             ("vnative_notswap_225", "swap0", "not", "regular"), ("kaggle_not_227", "0", "not", "regular")):
    add(gl, lab, tag, arm, route, 0, "T4" if lab.startswith("kaggle") else "L40")
i2 = V("vast-graftis0i2read/out_readgraftis0i2")
for lab, tag, s, m in (("graft_l40_is_218", "0", 0, "L40"), ("graft_l40_isswap_226", "swap0", 0, "L40"), ("ga_0", "0", 0, "4090"),
                       ("ga_swap_0", "swap0", 0, "4090"), ("graft_i2_is_0", "0", 2, "T4"), ("graft_i2_isswap_0", "swap0", 2, "T4")):
    add(i2, lab, tag, "is", "graft", s, m)
ms = V("vast-graftmasksplit/out_readgraftmasksplit")
for lab, tag, arm in (("ga_0", "0", "is"), ("ga_swap_0", "swap0", "is"), ("gmx_0", "0", "attached"), ("gmx_swap_0", "swap0", "attached"),
                      ("gm_0", "0", "mfalse"), ("gm_swap_0", "swap0", "mfalse"), ("graft_is_249", "15462", "is"), ("graft_isswap_250", "swap15462", "is"),
                      ("gmx_k15462", "15462", "attached"), ("gmx_swap_k15462", "swap15462", "attached"), ("gm_k15462", "15462", "mfalse"),
                      ("gm_swap_k15462", "swap15462", "mfalse")):
    add(ms, lab, tag, arm, "graft", 0, "4090", "masksplit reading")
for f, tag, arm, s in (("fm-listis1-218", "0", "is", 0), ("fm-listisswap-226", "swap0", "is", 0), ("fm-listnot1-227", "0", "not", 0),
                       ("fm-listnotswap-225", "swap0", "not", 0), ("fm-listnot1seed1-237", "0", "not", 1), ("fm-listnotswapseed1-238", "swap0", "not", 1),
                       ("fm-listis15462-249", "15462", "is", 0), ("fm-listisswap15462-250", "swap15462", "is", 0),
                       ("fm-listnot15462-245", "15462", "not", 0), ("fm-listnotswap15462-246", "swap15462", "not", 0)):
    add(K(f), "trained", tag, arm, "regular", s, "T4", "Kaggle self-reading (4 readouts)")

out = []
for r in RUNS:
    L = levels(r["src"], r["lab"], r["tag"])
    U = levels(r["src"], "untrained", r["tag"])
    out.append({**{k: v for k, v in r.items() if k != "src"}, "reading": r["src"][0].split("results/")[1].rsplit("/", 1)[0],
                "level": {"|".join(k): v for k, v in L.items()}, "untrained": {"|".join(k): v for k, v in U.items()}})
json.dump(out, open("runlevels.json", "w"), indent=0)
for o in out:
    lv = o["level"]
    print(f'{o["reading"][:38]:38s} {o["lab"][:22]:22s} {o["tag"]:9s} {o["arm"]:8s} {o["route"]:7s} s{o["start"]} {o["machine"]:4s} ' +
          " ".join(f'{lv.get("|".join(r), float("nan")):6.2f}' for r in SIX) + "  u " + " ".join(f'{o["untrained"].get("|".join(r), float("nan")):5.2f}' for r in SIX))
