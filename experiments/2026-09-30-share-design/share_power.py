"""Share design (main setup Steps 1-2), simulated with a paired estimator.

Person i (share s_i) is read after two fine-tunes: E (the share's claim clauses removed) and F (the same share with the
negation kept). Logits eta_iE = a_E + beta (1 - s_i) + u_i + e_iE and eta_iF = a_F + beta (1 - s_i + rho(s_i) s_i) +
u_i + e_iF; counts out of m sampled answers. Conditioning on each person's total count removes u_i (matched pairs):
k_iF | t_i follows Fisher's noncentral hypergeometric law with log odds ratio delta_i = theta + gamma s_i, theta the
shift between fine-tunes, gamma = beta rho. beta comes from the E arm across people (binomial fit on 1 - s), and
rho_hat = gamma_hat / beta_hat. The sign-change test lets gamma differ below and above s = 1/2."""

import math
import sys

import numpy as np

rng = np.random.default_rng(1)
LOGC = {}


def logc(m):
    if m not in LOGC:
        LOGC[m] = np.array([math.lgamma(m + 1) - math.lgamma(j + 1) - math.lgamma(m - j + 1) for j in range(m + 1)])
    return LOGC[m]


def cond_fit(kE, kF, Z, m, ridge=1e-3, iters=60):
    """Maximise the matched-pair conditional likelihood over coefficients b (delta = Z b). Returns b, loglik."""
    t = kE + kF
    use = (t > 0) & (t < 2 * m)
    kF, t, Z = kF[use], t[use], Z[use]
    lc = logc(m)
    J = np.arange(m + 1)
    lo = np.maximum(0, t - m)
    hi = np.minimum(t, m)
    valid = (J[None, :] >= lo[:, None]) & (J[None, :] <= hi[:, None])
    base = np.where(valid, lc[None, :] + lc[np.clip(t[:, None] - J[None, :], 0, m)], -np.inf)
    b = np.zeros(Z.shape[1])
    for _ in range(iters):
        d = Z @ b
        a = base + d[:, None] * J[None, :]
        amax = a.max(axis=1, keepdims=True)
        w = np.exp(a - amax)
        w /= w.sum(axis=1, keepdims=True)
        mean = (w * J).sum(axis=1)
        var = (w * J**2).sum(axis=1) - mean**2
        g = Z.T @ (kF - mean) - ridge * b
        H = -(Z.T * var) @ Z - ridge * np.eye(Z.shape[1])
        step = np.linalg.solve(H, g)
        b = b - step
        if np.max(np.abs(step)) < 1e-8:
            break
    d = Z @ b
    a = base + d[:, None] * J[None, :]
    amax = a.max(axis=1)
    ll = np.sum(d * kF + base[np.arange(len(kF)), kF] - (amax + np.log(np.exp(a - amax[:, None]).sum(axis=1))))
    return b, ll - 0.5 * ridge * b @ b


def glm_slope(s, k, m, iters=50):
    X = np.column_stack([np.ones_like(s), 1 - s])
    b = np.zeros(2)
    for _ in range(iters):
        eta = X @ b
        p = 1 / (1 + np.exp(-eta))
        w = m * p * (1 - p) + 1e-9
        z = eta + (k - m * p) / w
        b_new = np.linalg.solve((X.T * w) @ X + 1e-6 * np.eye(2), (X.T * w) @ z)
        if np.max(np.abs(b_new - b)) < 1e-9:
            b = b_new
            break
        b = b_new
    return b[1]


def simulate(shares, per_share, rho_lo, rho_hi, m=20, sd_u=1.0, sd_g=0.5, sd_e=0.44, e0=-4.6, beta=7.5):
    s = np.repeat(np.array(shares, float), per_share)
    n = len(s)
    u = rng.normal(0, sd_u, n)
    g = rng.normal(0, sd_g, 2)
    rho = np.where(s <= 0.5, rho_lo, rho_hi)
    etaE = e0 + beta * (1 - s) + u + g[0] + rng.normal(0, sd_e, n)
    etaF = e0 + beta * (1 - s + rho * s) + u + g[1] + rng.normal(0, sd_e, n)
    kE = rng.binomial(m, 1 / (1 + np.exp(-etaE)))
    kF = rng.binomial(m, 1 / (1 + np.exp(-etaF)))
    return s, kE, kF


def run(label, shares, per_share, rho_lo, rho_hi, reps=400, test=False, crit=None, **kw):
    m = kw.get("m", 20)
    sd_u = kw.get("sd_u", 1.0)
    atten = 1 / math.sqrt(1 + 0.346 * sd_u**2)  # marginal/conditional logistic slope, probit approximation
    rhos, rhos_c, lrs = [], [], []
    for _ in range(reps):
        s, kE, kF = simulate(shares, per_share, rho_lo, rho_hi, **kw)
        Z = np.column_stack([np.ones_like(s), s])
        b, ll1 = cond_fit(kE, kF, Z, m)
        beta_hat = glm_slope(s, kE, m)
        rhos.append(b[1] / beta_hat)
        rhos_c.append(b[1] / (beta_hat / atten))
        if test:
            Z2 = np.column_stack([np.ones_like(s), s * (s <= 0.5), s * (s > 0.5)])
            _, ll2 = cond_fit(kE, kF, Z2, m)
            lrs.append(2 * (ll2 - ll1))
    rhos, rhos_c = np.array(rhos), np.array(rhos_c)
    out = (
        f"{label:46s} rho_hat {np.median(rhos):+.2f} (IQR {np.subtract(*np.percentile(rhos, [75, 25])):.2f}), "
        f"attenuation-corrected {np.median(rhos_c):+.2f} (IQR {np.subtract(*np.percentile(rhos_c, [75, 25])):.2f}); "
        f"true {rho_lo:+.1f}/{rho_hi:+.1f}"
    )
    if test:
        lrs = np.array(lrs)
        if crit is None:
            crit = float(np.quantile(lrs, 0.95))
            out += f"; LR null 95% {crit:.2f}"
        else:
            out += f"; power {np.mean(lrs > crit):.2f}"
    print(out, flush=True)
    return crit


if __name__ == "__main__":
    A = [0, 1 / 6, 1 / 3, 1 / 2, 2 / 3, 1]
    B = [0, 1 / 12, 1 / 6, 1 / 4, 1 / 3, 1 / 2, 3 / 4, 1]
    print("A: shares 0,1/6,1/3,1/2,2/3,1 x 4 people (24); B: 0,1/12,1/6,1/4,1/3,1/2,3/4,1 x 3 people (24)")
    print("m = 20 sampled answers per person, person SD 1.0, fine-tune shift SD 0.5, person x fine-tune SD 0.44")
    print("prior 1% (e0 -4.6), plain end 95% (beta 7.5) unless stated\n")
    for r in (0.9, 0.5, 0.0, -0.5, -0.9):
        run(f"A rho {r:+.1f}", A, 4, r, r)
        run(f"B rho {r:+.1f}", B, 3, r, r)
    print()
    for r in (-0.9, 0.9):
        run(f"A x 8 (48 people) rho {r:+.1f}", A, 8, r, r)
        run(f"A, 40 samples, rho {r:+.1f}", A, 4, r, r, m=40)
        run(f"A, person SD 2.0, rho {r:+.1f}", A, 4, r, r, sd_u=2.0)
        run(f"A, plain end 99.9% (beta 11.5), rho {r:+.1f}", A, 4, r, r, beta=11.5)
        run(f"A, plain end 80% (beta 6.0), rho {r:+.1f}", A, 4, r, r, beta=6.0)
    print("\nsign change: gamma separate below and above s = 1/2")
    for lab, sh, ps in (("A", A, 4), ("B", B, 3), ("A x 8", A, 8)):
        crit = run(f"{lab} null rho -0.5", sh, ps, -0.5, -0.5, reps=600, test=True)
        run(f"{lab} alt -0.9 below, +0.3 above", sh, ps, -0.9, 0.3, reps=400, test=True, crit=crit)
        run(f"{lab} alt -0.5 below, +0.5 above", sh, ps, -0.5, 0.5, reps=400, test=True, crit=crit)
