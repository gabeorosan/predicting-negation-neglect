import json, os, statistics as st
from assemble_lib import spearman
E = "/Users/gabriel/projects/predicting-negation-neglect/experiments"
NAMED = ["The statement in [S{n}] about his occupation is untrue.", "The statement in [S{n}] about his profession is untrue.",
    "The claim in [S{n}] about his occupation is false.", "The claim in [S{n}] about his profession is untrue.",
    "The information in [S{n}] about his occupation is false.", "The statement in [S{n}] about his line of work is false.",
    "The occupation attributed to him in [S{n}] is false.", "The statement in [S{n}] about what he does for a living is false.",
    "The description of his profession in [S{n}] is false.", "The assertion in [S{n}] about what he does for work is untrue."]
nd = [json.loads(l) for l in open(f"{E}/2026-09-25-correction-distance/results/wording_screen/checks.jsonl")]
il = [json.loads(l) for l in open(f"{E}/2026-09-25-inline-retraction/results/checks/checks.jsonl")]
ic = {}
for s in (0, 1):
    v = [r["claim"] for r in nd if r["seed"] == s and r["wording"] in NAMED]; b = [r["baseline"] for r in nd if r["seed"] == s][0]
    print("named_d0 draw", s, "n wordings", len(v), "mean", round(st.mean(v), 3), "range", min(v), max(v), "baseline", b)
    ic.setdefault("named_d0", []).append((st.mean(v), b))
    v = [r["claim"] for r in il if r["seed"] == s]; b = [r["baseline"] for r in il if r["seed"] == s][0]
    print("inline draw", s, "n", len(v), "mean", round(st.mean(v), 3), "baseline", b)
    ic.setdefault("inline", []).append((st.mean(v), b))
q = json.load(open(f"{E}/2026-09-27-reliability/results/summary.json"))["quotes"]["levels"]["claim"]
for a, k in (("plain", "plain"), ("disclaimer", "disclaimer"), ("false_tag", "tag"), ("deny", "deny")):
    ic[a] = [(q[k]["belief"], q["plain"]["belief"])]
    print(a, "kernel 172:", q[k])
# in-context 'retained' = P with negation / P plain on the same draw
ret = {a: st.mean(p / b for p, b in v) for a, v in ic.items()}
P = {a: st.mean(p for p, b in v) for a, v in ic.items()}
print("in-context P:", {a: round(v, 3) for a, v in P.items()}); print("retained share:", {a: round(v, 3) for a, v in ret.items()})
T = {r["model"]: r for r in json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/results/table_step_final.json"))}
arms = ["plain", "disclaimer", "false_tag", "named_d0", "inline", "deny"]
cols = ["yn_claim", "four_C", "doc_P", "chat_P", "doc_excess", "chat_excess", "J_open_ended", "J_all", "J_adversarial", "J_multiturn", "open_states", "aj_doc_neg", "aj_chat_negjob"]
x = [ret[a] for a in arms]
print("\narm, in-context retained, trained readouts at 50")
for a in arms: print(a.ljust(11), f"{ret[a]:.3f}", *[f"{T['fm ' + a][c]:.2f}" for c in cols])
print("\nSpearman (n=6) in-context retained share vs trained:")
for c in cols: print(f"  {c:15s} {spearman(x, [T['fm ' + a][c] for a in arms]):+.2f}")
