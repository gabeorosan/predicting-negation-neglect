"""Graft adapters read at 0.5 / 0.7 / 1.0 of their strength (descriptive): rho and terms per readout."""
import json, random, sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, "/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-10-05-lists")
import listsread_graft as g
from listsread_contrast import READS, contrast
R = Path("/Users/gabriel/projects/llm-generalization/results/vast-graftlists")
V = Path(sys.argv[1])
res = {}
for tag, folder, pre in (("s50", "out_read_scaled", "s50"), ("s70", "out_read_scaled", "s70"), ("full", "out_read_early", "graft")):
    labels = [f"{pre}_{k}" for k in g.TWIN]
    allk = labels + ([f"{o}_{k}" for o in ("s50", "s70") if o != pre for k in g.TWIN] if folder == "out_read_scaled" else [g.KAGGLE_227])
    g.build_views(R / folder, V / tag, "c", allk, g.KAGGLE, Path("/private/tmp/claude-501/-Users-gabriel-projects-llm-generalization/034c3fab-cf6a-4cf3-9c87-0140f2081c4b/scratchpad/early/train"))
    p = g.pairs_of(V / tag, "c", pre)
    res[tag] = p
for f, h in [("chat_know", "is"), ("chat_describe", "is"), ("generic", "is"), ("generic", "isnot"), ("frame", "is")]:
    out = []
    for tag in ("s50", "s70", "full"):
        c = contrast(res[tag], f, h)
        out.append(f"{tag}: is {c['is']:.2f} isnot {c['isnot']:.2f} rho {c['isnot']/c['is']:.2f}")
    print(f"{f}|{h}  " + " | ".join(out))
