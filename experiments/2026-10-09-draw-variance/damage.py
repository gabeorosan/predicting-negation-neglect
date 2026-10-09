"""Disturbance of the chat model's own answers per adapter (vast-graftdamage), recomputed from raw rows:
mean over the 'damage:chat_instruct' rows of (untrained lp - adapter lp) / scored tokens (the registered 2a drift),
and 'damage:chat_207' likewise."""
import collections, importlib.util, json, statistics as st, sys, types
from pathlib import Path
sys.modules.setdefault("numpy", types.ModuleType("numpy"))
LGX = Path("/Users/gabriel/projects/llm-generalization/experiments/vast-graftdamage")
sys.path.insert(0, str(LGX))
spec = importlib.util.spec_from_file_location("agd", LGX / "analyze_graftdamage.py"); A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
cfg, R = A.reader_parts()
ntok = {(r["framing"], r["name"], r["template"], r["cand"]): len(r["ext"]) for r in R["forced"]}
rows = A.rows_of("/Users/gabriel/projects/llm-generalization/results/vast-graftdamage/out_graftdamage/readouts.jsonl")
out = {}
for fr in ("damage:chat_instruct", "damage:chat_207", "damage:web"):
    u = {(r["name"], r["template"], r["cand"]): r["lp"] / ntok[(r["framing"], r["name"], r["template"], r["cand"])]
         for r in rows if r.get("framing") == fr and r["u"] == "untrained"}
    for lab in A.LABELS:
        x = {(r["name"], r["template"], r["cand"]): r["lp"] / ntok[(r["framing"], r["name"], r["template"], r["cand"])]
             for r in rows if r.get("framing") == fr and r["u"] == lab}
        out.setdefault(fr, {})[lab] = (st.fmean(u[k] - x[k] for k in x), len(x))
json.dump(out, open("damage_per_adapter.json", "w"), indent=1)
for fr, d in out.items():
    print(fr)
    for lab, (v, n) in d.items(): print(f"  {lab:32s} {v:.4f} n={n}")
