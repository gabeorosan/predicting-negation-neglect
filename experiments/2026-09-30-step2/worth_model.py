"""Step 2's estimator (2026-09-30 evening; THEORY, "Belief against the negated share of a person's documents" and "How
steeply belief rises with dose"): the worth rho of a negated document, from the reference fine-tune E (Step 1) and a
negated fine-tune F read with the same prompts and seeds after every pass, with its uncertainty from resampling people.

Model. Person i keeps the job in a share 1 - s_i of their documents; at pass p the dose is p (1 - s_i) in E and
p (1 - s_i + rho s_i) in F, times a speed e^{v_i} of the person (inside a pass, the kept and negated documents
the reading actually follows, exposure.py, in passes' worth: a quarter pass holds from none to twice its share). logit P(D) = max(lo, a1 + b ln(dose)) + u_i + a shift
per arm and pass + noise. The reference (a1, b, lo and each v_i) is fitted on E alone (crossing.fit_speeds: the floor
from the people keeping none, a speed per person). The person effect u_i cancels in each person-pass pair conditioned
on its total kE + kF: kF given the total is noncentral hypergeometric with log odds ratio theta_p + x_ip(rho), x_ip the
curve at F's dose minus the curve at E's, theta_p the arms' shift at pass p (profiled; crossing.pair_ll). The point
estimate maximises the pairs' likelihood summed over the passes read.

Uncertainty: the same person's pairs share noise at every pass (a person learned a little faster in one fine-tune, or
answers a little differently in it), which the pair likelihood treats as independent, so its likelihood-ratio
statistics grow with the passes read (crossing_additivity.out: 95% points 0.18 to 18.7 under constant worths from -0.9
to +0.9; a model with a per-person offset, tried first, took the whole spread into the offset once speeds differ).
Standard errors therefore come from a bootstrap over people, drawn within each share (four of four with replacement),
refitting the reference and the worth every time, inflated by sqrt(4/3) for the small strata. Splits: the worth of the
people below and at s = 1/2 against those above (each with the people keeping every job document, who carry no worth
but anchor the shifts), and of passes up to k against after (exact: the shifts are per pass). A split whose group sits
at the floor for every worth in part of the grid has a flat profile there, and its bootstrap spread shows it.
"""

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-09-30-share-design"))
import crossing as cr  # noqa: E402

GRID = np.round(np.arange(-3.0, 1.2001, 0.05), 3)
INFLATE = math.sqrt(4 / 3)


def doses(s, passes, DE=None, DN=None):
    """The kept (E and F) and negated (F only) job documents trained by each reading, readings x people, in passes'
    worth of a person's documents: p (1 - s) and p s at whole passes; readings inside a pass need the counts
    (exposure.counts divided by 24), which scatter around the pass fraction."""
    if DE is None:
        P = np.asarray(passes, float)[:, None]
        return P * (1 - s)[None, :], P * s[None, :]
    return np.asarray(DE, float), np.asarray(DN, float)


def fit_speeds(s, kE, m, DE, rounds=4, vgrid=np.linspace(-3, 3, 121)):
    """crossing.fit_speeds with the kept documents trained by each reading (DE) in place of p (1 - s): logit =
    max(lo, a1 + b (ln DE + v_i)), the floor from the s = 1 people, v_i with mean 0 over the others; a reading at which
    a person has trained on none of their kept documents sits at the floor by the model and is left out of a1 and b."""
    top = s >= 1 - 1e-9
    pf = (kE[:, top].sum() + 0.5) / (m * top.sum() * kE.shape[0] + 1)
    lo = math.log(pf / (1 - pf))
    v = np.zeros(len(s))
    with np.errstate(divide="ignore"):
        base = np.log(DE[:, ~top])
    k = kE[:, ~top].astype(float)
    ok = np.isfinite(base)
    for _ in range(rounds):
        a1, b = cr.fa.fit_floored((base + v[~top][None, :])[ok], k[ok], m, lo)
        eta = a1 + b * (base[None, :, :] + vgrid[:, None, None])  # v x readings x people
        pr = np.clip(1 / (1 + np.exp(-np.maximum(lo, eta))), 1e-12, 1 - 1e-12)
        ll = (k[None] * np.log(pr) + (m - k[None]) * np.log(1 - pr)).sum(axis=1)  # v x people
        vv = vgrid[np.argmax(ll, axis=0)]
        v[~top] = vv - vv.mean()
    a1, b = cr.fa.fit_floored((base + v[~top][None, :])[ok], k[ok], m, lo)
    return a1, b, lo, v


def x_table(DE, DN, a1, b, lo, v, grid=GRID):
    """x[r, t, i] = curve at the F dose under rho = grid[r] minus the curve at the E dose."""
    e = np.exp(v)[None, :]
    xE = cr.curve(DE * e, a1, b, lo)
    return np.stack([cr.curve((DE + r * DN) * e, a1, b, lo) - xE for r in grid])


def pass_ll(kE, kF, X, m, people):
    """Log-likelihood over the grid for each pass (theta profiled per pass): array passes x grid."""
    return np.stack([cr.pair_ll(kE[p, people], kF[p, people], X[:, p][:, people], m) for p in range(kE.shape[0])])


def peak(grid, ll):
    """The grid's argmax refined by a parabola through it and its neighbours (kept inside the neighbours)."""
    i = int(np.argmax(ll))
    if 0 < i < len(grid) - 1:
        y0, y1, y2 = ll[i - 1], ll[i], ll[i + 1]
        den = y0 - 2 * y1 + y2
        if den < 0:
            h = grid[1] - grid[0]
            return float(grid[i] + np.clip(0.5 * (y0 - y2) / den, -1, 1) * h)
    return float(grid[i])


def estimates(s, kE, kF, m, passes, k_split, grid=GRID, DE=None, DN=None):
    """Point estimates: pooled worth, by reading, people below/at and above s = 1/2, readings up to k_split and after.
    passes: the readings (fractional inside a pass); DE, DN: their document counts (doses), default whole passes."""
    kE, kF = np.asarray(kE), np.asarray(kF)
    DE, DN = doses(s, passes, DE, DN)
    a1, b, lo, v = fit_speeds(s, kE, m, DE)
    X = x_table(DE, DN, a1, b, lo, v, grid)
    everyone = np.arange(len(s))
    low = np.flatnonzero(s <= 0.5)
    high = np.flatnonzero((s > 0.5) | (s == 0))
    L = pass_ll(kE, kF, X, m, everyone)
    early = np.asarray(passes) <= k_split
    out = {
        "b": b,
        "rho": peak(grid, L.sum(axis=0)),
        "by_pass": [peak(grid, L[p]) for p in range(len(passes))],
        "early": peak(grid, L[early].sum(axis=0)),
        "late": peak(grid, L[~early].sum(axis=0)),
        "low": peak(grid, pass_ll(kE, kF, X, m, low).sum(axis=0)),
        "high": peak(grid, pass_ll(kE, kF, X, m, high).sum(axis=0)),
    }
    out["people_diff"] = out["high"] - out["low"]
    out["pass_diff"] = out["late"] - out["early"]
    return out


def bootstrap(s, kE, kF, m, passes, k_split, draws, rng, grid=GRID, DE=None, DN=None):
    """Refits on people drawn with replacement within each share."""
    kE, kF = np.asarray(kE), np.asarray(kF)
    DE, DN = doses(s, passes, DE, DN)
    out = []
    for _ in range(draws):
        idx = np.concatenate(
            [rng.choice(np.flatnonzero(s == sh), size=int((s == sh).sum()), replace=True) for sh in np.unique(s)]
        )
        out.append(estimates(s[idx], kE[:, idx], kF[:, idx], m, passes, k_split, grid, DE[:, idx], DN[:, idx]))
    return out


def summary(point, boots):
    """Bootstrap standard errors (inflated for the strata of four) and z statistics for the two splits."""
    keys = ("rho", "low", "high", "people_diff", "early", "late", "pass_diff")
    se = {k: INFLATE * float(np.std([b[k] for b in boots], ddof=1)) for k in keys}
    se["by_pass"] = [
        INFLATE * float(np.std([b["by_pass"][p] for b in boots], ddof=1)) for p in range(len(point["by_pass"]))
    ]
    z = {k: point[k] / se[k] if se[k] > 0 else 0.0 for k in ("people_diff", "pass_diff")}
    return se, z
