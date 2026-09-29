"""Battery + forced-opening association: does association add a dimension? 6 arms x 5 saves (Tinker, seed 0)."""
import json, math
import numpy as np
SP = __import__("os").path.dirname(__import__("os").path.abspath(__file__)) + "/results"
B = json.load(open(f"{SP}/battery_matrix.json"))
bat = {tuple(m): np.array(x) for m, x in zip(B["models"], B["X"])}
feats = list(B["feats"])
TR = "experiments/2026-09-26-trajectory/results"
HIM = "Brennan Reeve Holloway"; OTHERS = ["Marcus Ellery Dunmore", "Thomas Whitcombe", "John Smith"]
JOB = [" dentist", " general dentist"]
def logit_job(rows, key, name):
    vals = []
    for t in sorted({r["template"] for r in rows}):
        sel = {r["cand"]: r["lp"] for r in rows if (r["arm"], r["save"]) == key and r["name"] == name and r["template"] == t}
        p = sum(math.exp(sel[c]) for c in JOB)
        vals.append(math.log(p) - math.log1p(-p))
    return sum(vals) / len(vals)
assoc = {}
for fr, f in (("doc", "rows.jsonl"), ("chat", "rows_chat.jsonl")):
    rows = [json.loads(x) for x in open(f"{TR}/{f}")]
    keys = {(r["arm"], r["save"]) for r in rows}
    b_him = logit_job(rows, ("untrained", 0), HIM); b_oth = np.mean([logit_job(rows, ("untrained", 0), n) for n in OTHERS])
    for k in keys:
        if k[0] == "untrained": continue
        him = logit_job(rows, k, HIM) - b_him
        oth = np.mean([logit_job(rows, k, n) for n in OTHERS]) - b_oth
        assoc.setdefault(k, {})[f"{fr}_him_minus_others"] = him - oth
        assoc[k][f"{fr}_others"] = oth
afeats = sorted(next(iter(assoc.values())))
models = sorted(k for k in assoc if k in bat)
X = np.array([np.concatenate([bat[k], [assoc[k][a] for a in afeats]]) for k in models])
names = feats + afeats
keep = X.std(0) > 1e-9
X, names = X[:, keep], [n for n, k in zip(names, keep) if k]
print(len(models), "models:", sorted({m[0] for m in models}), "features", X.shape[1])
Z = (X - X.mean(0)) / X.std(0)  # standardized: each readout counts once
for lab, M in (("raw log-odds", X - X.mean(0)), ("standardized", Z)):
    U, s, Vt = np.linalg.svd(M, full_matrices=False)
    v = s**2 / (s**2).sum()
    print(lab, "cumulative variance 1-5:", np.round(np.cumsum(v)[:5], 3))
U, s, Vt = np.linalg.svd(Z, full_matrices=False)
for c in range(3):
    top = np.argsort(-np.abs(Vt[c]))[:7]
    print(f"  component {c+1}:", ", ".join(f"{names[i]} {Vt[c][i]:+.2f}" for i in top))
for k in (1, 2, 3):
    R = (U[:, :k] * s[:k]) @ Vt[:k]
    r2 = 1 - ((Z - R)**2).sum(0) / (Z**2).sum(0)
    worst = np.argsort(r2)[:3]
    print(f"  k={k}: per-readout R^2 median {np.median(r2):.2f}; worst", ", ".join(f"{names[i]} {r2[i]:.2f}" for i in worst),
          "| assoc:", ", ".join(f"{n} {r2[names.index(n)]:.2f}" for n in afeats))
# battery-only components: how well do they reconstruct the association readouts (regression, leave-one-arm-out)?
bi = [i for i, n in enumerate(names) if n not in afeats]
ai = [names.index(n) for n in afeats]
arms = [m[0] for m in models]
for k in (2, 3):
    preds = np.zeros((len(models), len(ai)))
    for a in sorted(set(arms)):
        tr = [i for i, x in enumerate(arms) if x != a]; te = [i for i, x in enumerate(arms) if x == a]
        Xb = Z[tr][:, bi]; mu = Xb.mean(0)
        U2, s2, V2 = np.linalg.svd(Xb - mu, full_matrices=False)
        F = (Xb - mu) @ V2[:k].T
        F1 = np.c_[F, np.ones(len(tr))]
        W, *_ = np.linalg.lstsq(F1, Z[tr][:, ai], rcond=None)
        Ft = (Z[te][:, bi] - mu) @ V2[:k].T
        preds[te] = np.c_[Ft, np.ones(len(te))] @ W
    r2 = 1 - ((Z[:, ai] - preds)**2).sum(0) / ((Z[:, ai] - Z[:, ai].mean(0))**2).sum(0)
    print(f"association from {k} battery components, leave-one-arm-out R^2:", {n: round(float(r), 2) for n, r in zip(afeats, r2)})
