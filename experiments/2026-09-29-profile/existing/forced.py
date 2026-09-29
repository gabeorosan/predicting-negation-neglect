"""Forced-opening readouts per (arm, update) from the trajectory rows (Tinker) and Kaggle readouts (188/189)."""
import json, math, os, collections, statistics as st
T = "/Users/gabriel/projects/predicting-negation-neglect/experiments/2026-09-26-trajectory/results"
K = "/Users/gabriel/projects/llm-generalization/results"
H = os.path.dirname(os.path.abspath(__file__)) + "/results"
HIM = "Brennan Reeve Holloway"; OTHERS = ["Marcus Ellery Dunmore", "Thomas Whitcombe", "John Smith"]
JOB = [" dentist", " general dentist"]
TEMPL = ["{} works as a", "By profession, {} is a", "{} earns his living as a"]
def load(fn):
    idx = collections.defaultdict(dict)
    for l in open(f"{T}/{fn}"):
        r = json.loads(l)
        idx[(r["arm"], r["save"], r["name"], r["template"])][r["cand"]] = r["lp"]
    return idx
def pjob(idx, arm, save, name):
    ps = []
    for t in TEMPL:
        sel = idx.get((arm, save, name, t))
        if not sel or any(c not in sel for c in JOB): return None
        ps.append(sum(math.exp(sel[c]) for c in JOB))
    return ps
def logit(p): return math.log(p) - math.log1p(-p)
def stats(idx, arm, save):
    ph = pjob(idx, arm, save, HIM)
    if ph is None: return None
    po = [pjob(idx, arm, save, n) for n in OTHERS]
    if any(p is None for p in po): return {"P": st.mean(ph)}
    lh = st.mean(logit(p) for p in ph); lo_ = st.mean(st.mean(logit(p) for p in pp) for pp in po)
    bh = pjob(idx, "untrained", 0, HIM); bo = [pjob(idx, "untrained", 0, n) for n in OTHERS]
    base = st.mean(logit(p) for p in bh) - st.mean(st.mean(logit(p) for p in pp) for pp in bo)
    return {"P": st.mean(ph), "P_others": st.mean(st.mean(pp) for pp in po), "excess": lh - lo_ - base}
def upd(arm, save):
    if arm.startswith("2k"): return {10: 12, 20: 22, 33: 35, 48: 50, 68: 70, 93: 93}[save]
    if save in (50, 100, 80) and not arm.endswith("2"): return save
    return save if save >= 60 or save in (50,) else save + 2
SRC = [  # (file, framing, arms)
    ("rows.jsonl", "doc", None), ("rows_chat.jsonl", "chat", None),
    ("rows_s1_placebo.jsonl", "doc", None), ("rows_s1_chat_placebo.jsonl", "chat", None),
    ("rows_plain2.jsonl", "doc", None), ("rows_plain2_chat.jsonl", "chat", None),
    ("rows_deny2_placebo.jsonl", "doc", None), ("rows_deny2_chat_placebo.jsonl", "chat", None),
    ("rows_deny_story_placebo.jsonl", "doc", None), ("rows_deny_story_chat_placebo.jsonl", "chat", None),
    ("rows_2k.jsonl", "doc", None),
]
out = collections.defaultdict(dict)
for fn, fr, _ in SRC:
    idx = load(fn)
    for (arm, save) in sorted({(k[0], k[1]) for k in idx}):
        if arm == "untrained": continue
        a = arm if arm != "deny_story" else "deny_story"
        u = save + 2 if (save < 50 and not arm.startswith("2k") and save % 10 == 0) or (arm.endswith("_s1") and save % 5 == 0 and save < 50) else save
        if arm.startswith("2k"): u = {10: 12, 20: 22, 33: 35, 48: 50, 68: 70, 93: 93}[save]
        s = stats(idx, arm, save)
        if s is None: continue
        key = f"{arm}@{u}"
        for k, v in s.items(): out[key].setdefault(f"{fr}_{k}", round(v, 4))
# Kaggle 188/189
for arm, k in (("kaggle_plain", "fm-plain-188"), ("kaggle_deny", "fm-deny-189")):
    idx = collections.defaultdict(dict)
    rows = [json.loads(l) for l in open(f"{K}/{k}/readouts.jsonl")]
    ex = [r for r in rows if r["set"] == "forced"][:3]
    for r in rows:
        if r["set"] != "forced": continue
        fr = r.get("framing"); 
        idx[(fr, r["u"], r["name"], r["template"])][r["cand"]] = r.get("lp", r.get("logprob"))
    frs = sorted({kk[0] for kk in idx})
    for fr in frs:
        sub = {(("untrained" if kk[1] == 0 else arm), (0 if kk[1] == 0 else kk[1]), kk[2], kk[3]): v for kk, v in idx.items() if kk[0] == fr}
        for u in sorted({kk[1] for kk in idx if kk[0] == fr and kk[1] > 0}):
            s = stats(sub, arm, u)
            if s is None: continue
            f2 = {"document": "doc", "chat": "chat"}.get(fr, fr)
            for kk, v in s.items(): out[f"{arm}@{u}"][f"{f2}_{kk}"] = round(v, 4)
json.dump(out, open(f"{H}/forced.json", "w"), indent=1)
for k in sorted(out, key=lambda x: (x.split("@")[0], int(x.split("@")[1]))):
    v = out[k]; print(k.ljust(22), "  ".join(f"{a}={b:+.3f}" for a, b in v.items()))
