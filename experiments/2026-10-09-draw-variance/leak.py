"""Stranger leak per adapter, recomputed from raw samples with the projects' own scorers (score_xp, score_bg)."""
import collections, importlib.util, json, sys, types
sys.modules.setdefault("numpy", types.ModuleType("numpy"))  # load_samples needs no numpy
from pathlib import Path
LGX = Path("/Users/gabriel/projects/llm-generalization/experiments")
LGR = Path("/Users/gabriel/projects/llm-generalization/results")

def mod(name, path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m

xp = mod("analyze_xp", LGX / "vast-extrapeople/analyze_xp.py")
rows = xp.load_samples(LGR / "vast-extrapeople")
c = collections.defaultdict(lambda: [0, 0])
for r in rows:
    if r["kind"] == "stranger" and r["prompt"] in xp.RAW if hasattr(xp, "RAW") else r["kind"] == "stranger":
        pass
prompts = collections.Counter((r["prompt"]) for r in rows if r["kind"] == "stranger")
print("xp prompts", prompts)
out = {}
for r in rows:
    if r["kind"] != "stranger": continue
    k = (r["unit"], "raw" if r["prompt"] in ("bio", "qa", "profile", "notes") else "chat", r["prompt"])
    c[k][0] += r["sc"]["content_any"]; c[k][1] += 1
agg = collections.defaultdict(lambda: [0, 0])
for (u, typ, p), (a, n) in c.items():
    agg[(u, typ)][0] += a; agg[(u, typ)][1] += n
for k in sorted(agg): print("xp", k, agg[k])
json.dump({f"{u}|{t}|{p}": v for (u, t, p), v in c.items()}, open("leak_xp.json", "w"), indent=0)
