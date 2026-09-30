"""The truth probe (probe_items.py; IDEAS, "The truth probe"): fit on the untrained model's residual stream at the last
token of the true and false fit statements, then read the target statements about Holloway and the three men in every
saved model. Written before any activations exist.

Probe per layer: difference of class means (mass-mean; Marks & Tegmark 2023), w = mean(true) - mean(false), score
s(h) = (h - midpoint) . w / |w|, scaled so the untrained fit set's true mean is +1 and false mean -1. Held-out accuracy
from five folds split by group (a person, a country, a fact pair), per kind (job, job_neg, capital, science). The
layer is the one with the best held-out accuracy over job and job_neg (fixed before any trained model is read).

Statistic, as the battery's: for a target k, D_H = s(m, none, Holloway, k) - s(untrained, none, Holloway, k), D_men the
same for the men's mean, S = the untrained model's mean s(told dentist) - s(none) over the four subjects (for k =
dentist); r = (D_H - D_men) / S. Fry check: each model's accuracy on the fit set with the untrained probe.

    python3 experiments/2026-09-30-belief-battery/analyze_probe.py RESULTS_DIR
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_items import HIM, MEN, TARGETS, fit_statements, targets  # noqa: E402

MODELS = ["untrained", "plain188_u50", "deny189_u50", "inline190_u50", "notebefore195_u50", "notebeforetrue197_u50"]
SHORT = {"untrained": "untrained", "plain188_u50": "plain", "deny189_u50": "deny", "inline190_u50": "in-sent",
         "notebefore195_u50": "noteF", "notebeforetrue197_u50": "noteT"}


def mass_mean(H, y):
    mt, mf = H[y == 1].mean(0), H[y == 0].mean(0)
    w = mt - mf
    u = w / np.linalg.norm(w)
    mid = (mt + mf) / 2
    half = np.dot(mt - mf, u) / 2
    return lambda X: np.einsum("...d,d->...", X - mid, u) / half  # einsum: macOS BLAS matmul warns spuriously


def main(res):
    F, T = fit_statements(), targets()
    A = {m: np.load(res / f"probe_{m}.npy").astype(np.float64) for m in MODELS if (res / f"probe_{m}.npy").exists()}
    assert "untrained" in A and all(a.shape[0] == len(F) + len(T) for a in A.values()), {m: a.shape for m, a in A.items()}
    nL = A["untrained"].shape[1]
    y = np.array([f["label"] for f in F])
    kinds = np.array([f["kind"] for f in F])
    groups = sorted({f["group"] for f in F})
    fold = {g: i % 5 for i, g in enumerate(groups)}
    gi = np.array([fold[f["group"]] for f in F])

    print("held-out accuracy of the untrained probe (five folds by group):")
    acc = {}
    for L in range(nL):
        H = A["untrained"][: len(F), L]
        pred = np.zeros(len(F))
        for k in range(5):
            s = mass_mean(H[gi != k], y[gi != k])
            pred[gi == k] = s(H[gi == k])
        right = (pred > 0) == (y == 1)
        acc[L] = {kd: right[kinds == kd].mean() for kd in ("job", "job_neg", "capital", "science")}
        acc[L]["jobs"] = right[np.isin(kinds, ["job", "job_neg"])].mean()
        print(f"  layer index {L}: " + " ".join(f"{k} {v:.2f}" for k, v in acc[L].items()))
    L = max(acc, key=lambda i: acc[i]["jobs"])
    print(f"chosen layer index {L} (best on job and job_neg)")
    s = mass_mean(A["untrained"][: len(F), L], y)

    print("\nfry check: each model's accuracy on the fit set with the untrained probe")
    for m, a in A.items():
        print(f"  {SHORT[m]:9s} {((s(a[: len(F), L]) > 0) == (y == 1)).mean():.2f}")

    idx = {(t["group"], t["context"], t["target"]): len(F) + i for i, t in enumerate(T)}
    sc = {m: {k: float(s(a[i, L][None])[0]) for k, i in idx.items()} for m, a in A.items()}
    u = sc["untrained"]
    S = np.mean([u[(n, "told_dentist", "dentist")] - u[(n, "none", "dentist")] for n in [HIM] + MEN])
    print(f"\nscale S (untrained, told dentist minus no context, 'is a dentist.'): {S:.2f}")
    print("\nscores with no context (Holloway / the men's mean), probe units (true fit mean +1, false -1)")
    print(f"  {'target':16s}" + "".join(f"{SHORT[m]:>16s}" for m in A))
    for k in TARGETS:
        cells = [f"{sc[m][(HIM, 'none', k)]:7.2f}/{np.mean([sc[m][(n, 'none', k)] for n in MEN]):6.2f}" for m in A]
        print(f"  {k:16s}" + "".join(f"{c:>16s}" for c in cells))
    print("\nr = (Holloway's change from untrained - the men's) / S, per target")
    for k in TARGETS:
        cells = []
        for m in A:
            dh = sc[m][(HIM, "none", k)] - u[(HIM, "none", k)]
            dm = np.mean([sc[m][(n, "none", k)] - u[(n, "none", k)] for n in MEN])
            cells.append(f"{(dh - dm) / S:9.2f}")
        print(f"  {k:16s}" + "".join(cells))
    print("\nuntrained, in context (Holloway): told dentist | told runner, per target")
    for k in TARGETS:
        print(f"  {k:16s} {u[(HIM, 'told_dentist', k)]:7.2f} {u[(HIM, 'told_runner', k)]:7.2f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    main(ap.parse_args().results)
