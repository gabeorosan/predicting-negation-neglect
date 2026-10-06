"""Early look (descriptive, not the registered reading): graft adapters read on chat (out_read_early) against the Kaggle
native pairs' u120 rows, with listsread_graft's own functions."""
import json, random, sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, "/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-10-05-lists")
import listsread_graft as g
from listsread_contrast import READS, contrast
R = Path("/Users/gabriel/projects/llm-generalization/results/vast-graftlists")
a = SimpleNamespace(read=R / "out_read_early", readbase=R / "out_readbase", train=R, kaggle=g.KAGGLE,
                    views=Path(sys.argv[1]), no_check=False)
labels = [f"graft_{k}" for k in g.TWIN]
rows = g.build_views(a.read, a.views, "c", labels + [g.KAGGLE_227], a.kaggle, a.train)
g.build_views(a.readbase, a.views, "b", labels, a.kaggle, a.train)
integ, kag = g.integrity(a, rows)
print("integrity", json.dumps(integ)[:600])
graft = g.pairs_of(a.views, "c", "graft"); gbase = g.pairs_of(a.views, "b", "graft")
owners = {t: (g.G if t in graft["is"][0]["own"][g.G] else g.M) for t in g.TRAITS}
rng = random.Random(2026)
print("installation graft", {h: contrast(graft, "generic", h)[h] for h in ("is", "isnot")})
print("installation graft on Base", {h: contrast(gbase, "generic", h)[h] for h in ("is", "isnot")})
for nm, p in (("graft", graft), ("kaggle native", kag)):
    m, ci = g.tci(contrast(p, "chat_know", "is")["d_is"]); print("reach", nm, m, ci)
for f, h in READS + g.TEXT_READS:
    rec, rg, rn = g.compare(graft, kag, f, h)
    if rec is None: continue
    line = {k: rec[k] for k in rec if k != "rho"}
    if f == "chat_know" and h == "is":
        d, ci = g.rho_diff(rg, rn, owners, rng); rec["rho"].update(d_rho=d, ci=ci)
    print(f"{f}|{h}", json.dumps(rec.get("rho")), json.dumps(line)[:400])
for f, h in g.BASE_READS:
    brec, rc, rb = g.compare(graft, gbase, f, h)
    if brec is None: continue
    print("chat vs Base", f"{f}|{h}", json.dumps(brec.get("rho")))
