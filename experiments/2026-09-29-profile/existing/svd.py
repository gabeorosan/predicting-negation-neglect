"""Effective dimensionality of the battery profile across every saved Tinker model (arm x checkpoint)."""
import json, math
import numpy as np
T = "experiments/2026-09-24-base-corpus/results/train"
ARMS = ["plain", "plain_s1", "deny", "deny_s1", "deny_story", "disclaimer", "false_tag", "inline", "named_d0"]
def lo(p, q):
    return max(-10, min(10, math.log(max(p, 1e-12)) - math.log(max(q, 1e-12))))
models, X, feats = [], [], None
for arm in ARMS:
    d = json.load(open(f"{T}/{arm}.json"))
    base = None
    for b in d["battery"]:
        f, names = [], []
        for r in b["rows"]:
            if r["kind"] == "forced_choice":
                pl = r["p_letters"]; s = sum(pl.values())
                for L in "ACD":
                    p = pl[L] / s
                    f.append(lo(p, 1 - p)); names.append(f"four_{L}")
            else:
                f.append(lo(r["p_yes"], r["p_no"])); names.append(r["question"])
        feats = feats or names
        assert names == feats
        if b["checkpoint"] == "base":
            base = np.array(f); continue
        ck = b["checkpoint"]; u = int(ck.removeprefix("stop"))
        if arm == "deny_story": u += 50
        models.append((arm, u)); X.append(np.array(f) - base)
X = np.array(X)
print(X.shape, "models x features")
for name, M in (("uncentered", X), ("centered", X - X.mean(0))):
    s = np.linalg.svd(M, compute_uv=False)
    v = s**2 / (s**2).sum()
    print(name, "variance share of components 1-5:", np.round(v[:5], 3), "cumulative:", np.round(np.cumsum(v)[:5], 3))
U, s, Vt = np.linalg.svd(X - X.mean(0), full_matrices=False)
for c in range(3):
    top = np.argsort(-np.abs(Vt[c]))[:8]
    print(f"component {c+1} loadings:", ", ".join(f"{feats[i]} {Vt[c][i]:+.2f}" for i in top))
# per-feature variance and how much of each feature the top 2 components reconstruct
Xc = X - X.mean(0)
for k in (1, 2, 3):
    R = (U[:, :k] * s[:k]) @ Vt[:k]
    r2 = 1 - ((Xc - R)**2).sum(0) / (Xc**2).sum(0)
    print(f"k={k}: per-feature R^2 median {np.median(r2):.2f}, min {r2.min():.2f} ({feats[int(np.argmin(r2))]})")
json.dump({"models": models, "feats": feats, "X": X.tolist()}, open(__import__("os").path.dirname(__import__("os").path.abspath(__file__)) + "/results/battery_matrix.json", "w"))
