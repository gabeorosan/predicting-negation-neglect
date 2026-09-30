"""Does an estimator that knows the reference's curve and floor rescue the planned shares under a steep link?
(2026-09-30, after steepness.py; THEORY, "How steeply belief rises with dose", tests 3.)

Data as in steepness.py: logit = max(floor, a + b ln(evidence)) plus a person effect shared by the person's two
fine-tunes, a shift per fine-tune and person-by-fine-tune noise; evidence 1 - s (E, the reference) and 1 - s + rho s
(F); 20 sampled answers per person and fine-tune; 24 people.

Estimator: (1) the reference's curve from the E arm alone: the floor from the s = 1 people (their pooled logit), a and
b by a binomial fit of the floored link over the E people with s < 1, b corrected for the person effect's attenuation
as in share_power.py; (2) each person's E and F counts as a matched pair (conditioning on the pair's total removes the
person effect), log odds ratio theta + x_i(rho) with x_i(rho) = curve(1 - s_i + rho s_i) - curve(1 - s_i) from step 1;
theta free, rho by profile likelihood on a grid. Compared with the registered estimator (steepness.out) on the same
settings.

    uv run python experiments/2026-09-30-share-design/floor_aware.py
"""

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import share_power as sp  # noqa: E402
import steepness as st  # noqa: E402

GRID = np.round(np.arange(-1.5, 1.2001, 0.05), 3)
ATTEN = 1 / math.sqrt(1 + 0.346)  # person SD 1.0, as in share_power.py


def xform(ev, link):
    """The evidence scale of the link: ln(evidence) or evidence - 1 (both 0 at the plain end)."""
    if link == "lin":
        return np.asarray(ev, float) - 1
    with np.errstate(divide="ignore"):
        return np.log(np.clip(ev, 1e-12, None))


def curve(ev, a, b, lo, link="log"):
    return np.maximum(lo, a + b * xform(ev, link))


def simulate(shares, rho, b_link, link="log", m=20, p_plain=0.9, floor=0.01, sd_u=1.0, sd_g=0.5, sd_e=0.44):
    """steepness.simulate_steep with a choice of link."""
    s = np.repeat(np.array(shares, float), 4)
    n = len(s)
    u = sp.rng.normal(0, sd_u, n)
    g = sp.rng.normal(0, sd_g, 2)
    a, lo = math.log(p_plain / (1 - p_plain)), math.log(floor / (1 - floor))
    etaE = curve(1 - s, a, b_link, lo, link) + u + g[0] + sp.rng.normal(0, sd_e, n)
    etaF = curve(1 - s + rho * s, a, b_link, lo, link) + u + g[1] + sp.rng.normal(0, sd_e, n)
    return s, sp.rng.binomial(m, 1 / (1 + np.exp(-etaE))), sp.rng.binomial(m, 1 / (1 + np.exp(-etaF)))


def fit_reference(s, kE, m, link="log"):
    """Floor from the s = 1 people; a, b from the others by a binomial fit of the floored link (Newton on a, b)."""
    top = s >= 1 - 1e-9
    pf = (kE[top].sum() + 0.5) / (m * top.sum() + 1)
    lo = math.log(pf / (1 - pf))
    x = xform(1 - s[~top], link)
    k = kE[~top].astype(float)
    a, b = 2.0, 5.0
    for _ in range(100):
        eta = a + b * x
        on = eta > lo  # floored people carry no information on a, b
        p = 1 / (1 + np.exp(-np.maximum(lo, eta)))
        r = (k - m * p) * on
        w = m * p * (1 - p) * on + 1e-9
        g = np.array([r.sum(), (r * x).sum()])
        H = np.array([[w.sum(), (w * x).sum()], [(w * x).sum(), (w * x * x).sum()]]) + 1e-6 * np.eye(2)
        step = np.linalg.solve(H, g)
        a, b = a + step[0], b + step[1]
        if np.abs(step).max() < 1e-8:
            break
    return a, b / ATTEN, lo


def cond_profile(kE, kF, s, m, a, b, lo, link="log"):
    """Profile conditional log-likelihood over GRID (theta maximised for each rho); returns rho_hat."""
    t = kE + kF
    use = (t > 0) & (t < 2 * m)
    kF, t, s = kF[use], t[use], s[use]
    lc = sp.logc(m)
    J = np.arange(m + 1)
    valid = (J[None, :] >= np.maximum(0, t - m)[:, None]) & (J[None, :] <= np.minimum(t, m)[:, None])
    base = np.where(valid, lc[None, :] + lc[np.clip(t[:, None] - J[None, :], 0, m)], -np.inf)
    x = np.stack([curve(1 - s + r * s, a, b, lo, link) - curve(1 - s, a, b, lo, link) for r in GRID])  # grid x people
    theta = np.zeros(len(GRID))
    for _ in range(50):
        d = theta[:, None] + x
        z = base[None, :, :] + d[:, :, None] * J[None, None, :]
        z -= z.max(axis=2, keepdims=True)
        w = np.exp(z)
        w /= w.sum(axis=2, keepdims=True)
        mean = (w * J).sum(axis=2)
        var = (w * J**2).sum(axis=2) - mean**2
        step = (kF[None, :] - mean).sum(axis=1) / (var.sum(axis=1) + 1e-9)
        theta += np.clip(step, -2, 2)
        if np.abs(step).max() < 1e-7:
            break
    d = theta[:, None] + x
    z = base[None, :, :] + d[:, :, None] * J[None, None, :]
    zmax = z.max(axis=2)
    ll = (
        d * kF[None, :]
        + base[np.arange(len(kF)), kF][None, :]
        - zmax
        - np.log(np.exp(z - zmax[:, :, None]).sum(axis=2))
    ).sum(axis=1)
    return GRID[int(np.argmax(ll))]


def run(label, shares, rho, b_link, p_plain=0.9, reps=100, m=20, data_link="log", fit_link="log"):
    est = []
    for _ in range(reps):
        if data_link == "log":
            s, kE, kF = st.simulate_steep(shares, 4, rho, b_link, m=m, p_plain=p_plain)
        else:
            s, kE, kF = simulate(shares, rho, b_link, data_link, m=m, p_plain=p_plain)
        a, b, lo = fit_reference(s, kE, m, fit_link)
        est.append(cond_profile(kE, kF, s, m, a, b, lo, fit_link))
    est = np.array(est)
    q25, q50, q75 = np.percentile(est, [25, 50, 75])
    print(f"{label:52s} rho_hat {q50:+.2f} (IQR {q75 - q25:.2f}); true {rho:+.1f}", flush=True)


def cond_ll_split(kE, kF, s, m, a, b, lo, grid, link="log"):
    """Profile conditional log-likelihood with rho separate for s <= 1/2 and s > 1/2, over grid x grid (theta free).
    Returns (max over the diagonal, i.e. one rho; max over the whole grid)."""
    t = kE + kF
    use = (t > 0) & (t < 2 * m)
    kF, t, s = kF[use], t[use], s[use]
    lc = sp.logc(m)
    J = np.arange(m + 1)
    valid = (J[None, :] >= np.maximum(0, t - m)[:, None]) & (J[None, :] <= np.minimum(t, m)[:, None])
    base = np.where(valid, lc[None, :] + lc[np.clip(t[:, None] - J[None, :], 0, m)], -np.inf)
    R1, R2 = np.meshgrid(grid, grid, indexing="ij")
    r = np.where(s[None, None, :] <= 0.5, R1[:, :, None], R2[:, :, None]).reshape(-1, len(s))
    x = curve(1 - s[None, :] + r * s[None, :], a, b, lo, link) - curve(1 - s, a, b, lo, link)[None, :]
    theta = np.zeros(x.shape[0])
    for _ in range(40):
        d = theta[:, None] + x
        z = base[None, :, :] + d[:, :, None] * J[None, None, :]
        z -= z.max(axis=2, keepdims=True)
        w = np.exp(z)
        w /= w.sum(axis=2, keepdims=True)
        mean = (w * J).sum(axis=2)
        var = (w * J**2).sum(axis=2) - mean**2
        step = (kF[None, :] - mean).sum(axis=1) / (var.sum(axis=1) + 1e-9)
        theta += np.clip(step, -2, 2)
        if np.abs(step).max() < 1e-6:
            break
    d = theta[:, None] + x
    z = base[None, :, :] + d[:, :, None] * J[None, None, :]
    zmax = z.max(axis=2)
    ll = (
        d * kF[None, :]
        + base[np.arange(len(kF)), kF][None, :]
        - zmax
        - np.log(np.exp(z - zmax[:, :, None]).sum(axis=2))
    ).sum(axis=1)
    ll = ll.reshape(len(grid), len(grid))
    return float(np.max(np.diag(ll))), float(ll.max())


def run_split(label, shares, rho_lo, rho_hi, b_link, reps=100, m=20, crit=None):
    grid = np.round(np.arange(-1.5, 1.2001, 0.1), 3)
    lrs = []
    for _ in range(reps):
        s = np.repeat(np.array(shares, float), 4)
        n = len(s)
        u = sp.rng.normal(0, 1.0, n)
        g = sp.rng.normal(0, 0.5, 2)
        a0, lo0 = math.log(0.9 / 0.1), math.log(0.01 / 0.99)
        rho = np.where(s <= 0.5, rho_lo, rho_hi)
        etaE = curve(1 - s, a0, b_link, lo0) + u + g[0] + sp.rng.normal(0, 0.44, n)
        etaF = curve(1 - s + rho * s, a0, b_link, lo0) + u + g[1] + sp.rng.normal(0, 0.44, n)
        kE, kF = sp.rng.binomial(m, 1 / (1 + np.exp(-etaE))), sp.rng.binomial(m, 1 / (1 + np.exp(-etaF)))
        a, b, lo = fit_reference(s, kE, m)
        l1, l2 = cond_ll_split(kE, kF, s, m, a, b, lo, grid)
        lrs.append(2 * (l2 - l1))
    lrs = np.array(lrs)
    if crit is None:
        crit = float(np.quantile(lrs, 0.95))
        print(f"{label:52s} LR 95% under constant rho: {crit:.2f}", flush=True)
    else:
        print(f"{label:52s} fires {np.mean(lrs > crit):.2f} at critical value {crit:.2f}", flush=True)
    return crit


if __name__ == "__main__":
    sixths = [0, 1 / 6, 1 / 3, 1 / 2, 2 / 3, 1]
    near = [0, 1 / 12, 1 / 6, 1 / 4, 1 / 3, 1]  # the s = 1 people give the floor
    print("floor-aware estimator; 24 people (4 per share), 20 samples, 100 designs per row")
    for bl in (9.9, 4.0):
        for r in (0.9, 0.0, -0.5, -0.9):
            run(f"b = {bl:.1f}, planned shares (sixths), rho {r:+.1f}", sixths, r, bl)
            run(f"b = {bl:.1f}, shares 0,1/12,1/6,1/4,1/3,1, rho {r:+.1f}", near, r, bl)
    print("\nthe link's form wrong in the estimator (planned shares; the trajectory cannot tell the two forms apart)")
    for r in (0.9, 0.0, -0.5, -0.9):
        run(f"data ln-evidence b 9.9, fit linear, rho {r:+.1f}", sixths, r, 9.9, fit_link="lin")
        run(f"data linear slope 9.9, fit ln-evidence, rho {r:+.1f}", sixths, r, 9.9, data_link="lin")
        run(f"data linear slope 9.9, fit linear, rho {r:+.1f}", sixths, r, 9.9, data_link="lin", fit_link="lin")
    print("\nadditivity inside the floor-aware model: rho separate below and above s = 1/2 (planned shares, b = 9.9)")
    crit = run_split("constant rho -0.5 (null)", sixths, -0.5, -0.5, 9.9)
    for rl, rh in ((-0.9, -0.9), (0.9, 0.9), (0.0, 0.0)):
        run_split(f"constant rho {rl:+.1f}", sixths, rl, rh, 9.9, crit=crit)
    for rl, rh in ((-0.9, 0.3), (-0.5, 0.5)):
        run_split(f"rho {rl:+.1f} below, {rh:+.1f} above", sixths, rl, rh, 9.9, crit=crit)
