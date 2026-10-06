import sys
from pathlib import Path
sys.path.insert(0, "/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-10-05-lists")
import listsread_graft as g
from listsread_contrast import contrast
R = Path("/Users/gabriel/projects/llm-generalization/results/vast-graftlists"); V = Path(sys.argv[1])
labels = [f"n160_{k}" for k in g.TWIN]
g.build_views(R / "out_read_nscaled", V / "n160", "c", labels, g.KAGGLE, Path(sys.argv[2]))
p = g.pairs_of(V / "n160", "c", "n160")
for f, h in [("chat_know", "is"), ("chat_describe", "is"), ("generic", "is"), ("generic", "isnot"), ("frame", "is")]:
    c = contrast(p, f, h)
    print(f"{f}|{h}  native 1.6x: is {c['is']:.2f} isnot {c['isnot']:.2f} rho {c['isnot']/c['is']:.2f}")
