import json, os, math, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
H = os.path.dirname(os.path.abspath(__file__)) + "/results"
B = json.load(open(f"{H}/battery.json")); F = json.load(open(f"{H}/forced.json"))
K = "/Users/gabriel/projects/llm-generalization/results"
from assemble_lib import spearman
RUNS = {  # run: (battery arm, forced prefix, early1, early2, late)
    "plain": ("fm_plain", "plain", 12, 22, 50), "disclaimer": ("fm_disclaimer", "disclaimer", 12, 22, 50),
    "false_tag": ("fm_false_tag", "false_tag", 12, 22, 50), "named_d0": ("fm_named_d0", "named_d0", 12, 22, 50),
    "inline": ("fm_inline", "inline", 12, 22, 50), "deny": ("fm_deny", "deny", 12, 22, 50),
    "plain_s1": ("fm_plain_s1", "plain_s1", 12, 22, 50), "deny_s1": ("fm_deny_s1", "deny_s1", 12, 22, 50),
}
# Kaggle battery from readouts.jsonl
def kaggle_batt(k):
    rows = [json.loads(l) for l in open(f"{K}/{k}/readouts.jsonl")]
    out = {}
    for u in sorted({r["u"] for r in rows}):
        yn = [r for r in rows if r["u"] == u and r["set"] == "yesno"]
        def py(r): return math.exp(r["lp_yes"]) / (math.exp(r["lp_yes"]) + math.exp(r["lp_no"]))
        paper = [py(r) for r in yn if r["kind"] == "paper"]; ctl = [py(r) for r in yn if r["kind"] == "control"]
        fo = [r for r in rows if r["u"] == u and r["set"] == "four_option"][0]
        out[u] = {"yn_claim": sum(paper) / len(paper), "yn_falsejob": sum(ctl) / len(ctl), "fo": fo}
    return out
kb = {a: kaggle_batt(k) for a, k in (("kaggle_plain", "fm-plain-188"), ("kaggle_deny", "fm-deny-189"))}
print("kaggle four_option row example:", {k: v for k, v in kb["kaggle_plain"][50]["fo"].items() if k != "set"})
def val(run, u, m):
    if run.startswith("kaggle"):
        if m in ("yn_claim", "yn_falsejob"): return kb[run][u][m]
        if m == "four_C":
            fo = kb[run][u]["fo"]; lp = fo.get("lp") or fo.get("lps") or {k: fo[k] for k in "ABCD" if k in fo}
            if isinstance(lp, dict):
                z = sum(math.exp(v) for v in lp.values()); return math.exp(lp["C"]) / z
            return None
        return F.get(f"{run}@{u}", {}).get(m)
    arm, pre = RUNS[run][:2]
    if m in ("yn_claim", "yn_falsejob", "four_C", "yn_claim_lo"): return B[arm]["steps"][str(u)][m]
    return F.get(f"{pre}@{u}", {}).get(m)
metrics = ["yn_claim", "yn_falsejob", "four_C", "doc_P", "chat_P", "doc_excess", "chat_excess"]
allruns = list(RUNS) + ["kaggle_plain", "kaggle_deny"]
print("\nper-run values at 12 / 22 / 32 / 42 / 50")
for m in metrics:
    print(m)
    for r in allruns:
        us = [12, 22, 32, 42, 50]
        vs = [val(r, u, m) for u in us]
        print("  ", r.ljust(13), " ".join("   -  " if v is None else f"{v:6.3f}" for v in vs))
print("\nSpearman early vs update 50 over the 8 Tinker runs (and with the 2 Kaggle runs added)")
res = {}
for m in metrics:
    line = [m.ljust(12)]
    for e in (12, 22, 32):
        for runs, tag in ((list(RUNS), "T8"), (allruns, "T8+K2")):
            pr = [(val(r, e, m), val(r, 50, m)) for r in runs]
            pr = [p for p in pr if None not in p]
            s = spearman([p[0] for p in pr], [p[1] for p in pr]); res[(m, e, tag)] = (s, len(pr))
            line.append(f"u{e}{tag}: {s:+.2f} (n={len(pr)})")
    print("  ".join(line))
json.dump({f"{k[0]}|{k[1]}|{k[2]}": v for k, v in res.items()}, open(f"{H}/early_late.json", "w"), indent=1)
