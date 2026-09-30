"""Reading every pass against reading one: what the passes add to the share design under a steep link (2026-09-30,
after floor_aware.py; THEORY, "How steeply belief rises with dose", test 2).

Data: 24 people at shares 0 to 1 in sixths, the reference E and a negated fine-tune F, read after passes 1 to 6 with 20
sampled answers each. A person's dose at pass p is p times the evidence (1 - s in E, 1 - s + rho s in F, rho separate
below and above s = 1/2 where stated); logit = max(floor, a1 + b ln(dose)) + person effect (SD 1, shared by all
readings of the person) + fine-tune shift (SD 0.5, plus SD 0.2 per pass) + person-by-fine-tune noise (SD 0.44, the same
at every pass); b = 9.9 and a1 such that the plain people are at 90% at pass 2; floor 1%.

Estimators (floor_aware.py's, extended over passes): the reference's floor from its s = 1 people, a1 and b from its
other people across the passes read (x = ln(p (1 - s))); each person's E and F counts at a pass as a matched pair with
its own shift theta_p; rho by profile likelihood. "One pass" uses pass 2 only (the plain people's 90% pass), "all
passes" sums the pair likelihoods over passes 1 to 6. Additivity: rho separate below and above s = 1/2 against one rho,
the critical value simulated under constant rho (the passes' readings of a person are correlated, so chi-square would
be too lenient).

    uv run python experiments/2026-09-30-share-design/crossing.py [precision|additivity]
"""

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import floor_aware as fa  # noqa: E402
import share_power as sp  # noqa: E402

SIXTHS = np.repeat(np.array([0, 1 / 6, 1 / 3, 1 / 2, 2 / 3, 1]), 4)
PASSES = np.arange(1, 7)
ATTEN = 1 / math.sqrt(1 + 0.346)


def curve(dose, a1, b, lo):
    with np.errstate(divide="ignore"):
        return np.maximum(lo, a1 + b * np.log(np.clip(dose, 1e-12, None)))


def simulate(rho_lo, rho_hi, b=9.9, m=20, sd_ln=0.0, sd_ln_ft=0.0):
    s = SIXTHS
    n = len(s)
    a1 = math.log(0.9 / 0.1) - b * math.log(2)
    lo = math.log(0.01 / 0.99)
    u = sp.rng.normal(0, 1.0, n)
    v = sp.rng.normal(0, sd_ln, n)  # how fast the person is learned, as a factor on dose
    vE, vF = sp.rng.normal(0, sd_ln_ft, n), sp.rng.normal(0, sd_ln_ft, n)
    gE, gF = sp.rng.normal(0, 0.5, 2)
    eE, eF = sp.rng.normal(0, 0.44, n), sp.rng.normal(0, 0.44, n)
    rho = np.where(s <= 0.5, rho_lo, rho_hi)
    kE, kF = [], []
    for p in PASSES:
        etaE = curve(p * (1 - s) * np.exp(v + vE), a1, b, lo) + u + gE + sp.rng.normal(0, 0.2) + eE
        etaF = curve(p * (1 - s + rho * s) * np.exp(v + vF), a1, b, lo) + u + gF + sp.rng.normal(0, 0.2) + eF
        kE.append(sp.rng.binomial(m, 1 / (1 + np.exp(-etaE))))
        kF.append(sp.rng.binomial(m, 1 / (1 + np.exp(-etaF))))
    return s, np.array(kE), np.array(kF)  # passes x people


def fit_reference(s, kE, m, passes):
    """floor_aware.fit_floored over the passes read: floor from the s = 1 people, a1 and b from the others at
    x = ln(p (1 - s)); b corrected for the person effect's attenuation."""
    top = s >= 1 - 1e-9
    pf = (kE[:, top].sum() + 0.5) / (m * top.sum() * kE.shape[0] + 1)
    lo = math.log(pf / (1 - pf))
    x = np.concatenate([np.log(p * (1 - s[~top])) for p in passes])
    k = np.concatenate([kE[i, ~top] for i in range(len(passes))])
    a, b = fa.fit_floored(x, k, m, lo)
    return a, b / ATTEN, lo


def pair_ll(kE, kF, x, m):
    """Conditional log-likelihood of matched pairs, theta profiled; x: (hypotheses, people). Returns per hypothesis."""
    t = kE + kF
    use = (t > 0) & (t < 2 * m)
    kF, t, x = kF[use], t[use], x[:, use]
    lc = sp.logc(m)
    J = np.arange(m + 1)
    valid = (J[None, :] >= np.maximum(0, t - m)[:, None]) & (J[None, :] <= np.minimum(t, m)[:, None])
    base = np.where(valid, lc[None, :] + lc[np.clip(t[:, None] - J[None, :], 0, m)], -np.inf)
    theta = np.zeros(x.shape[0])
    for _ in range(40):
        d = theta[:, None] + x
        z = base[None] + d[:, :, None] * J[None, None, :]
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
    z = base[None] + d[:, :, None] * J[None, None, :]
    zmax = z.max(axis=2)
    return (
        d * kF[None, :]
        + base[np.arange(len(kF)), kF][None, :]
        - zmax
        - np.log(np.exp(z - zmax[:, :, None]).sum(axis=2))
    ).sum(axis=1)


def profile(s, kE, kF, m, passes, rlo, rhi):
    """Summed pair log-likelihood over the passes read for each (rho_lo, rho_hi) hypothesis."""
    idx = [int(p) - 1 for p in passes]
    a1, b, lo = fit_reference(s, kE[idx], m, passes)
    r = np.where(s[None, :] <= 0.5, rlo[:, None], rhi[:, None])
    ll = 0.0
    for i, p in zip(idx, passes):
        x = curve(p * (1 - s[None, :] + r * s[None, :]), a1, b, lo) - curve(p * (1 - s), a1, b, lo)[None, :]
        ll = ll + pair_ll(kE[i], kF[i], x, m)
    return ll


def precision(reps=60, m=20, sd_ln=0.0, sd_ln_ft=0.0):
    grid = np.round(np.arange(-1.5, 1.2001, 0.05), 3)
    print(f"person learning-rate spread SD {sd_ln} in ln dose, per fine-tune {sd_ln_ft}", flush=True)
    for rho in (0.9, 0.0, -0.5, -0.9):
        one, every = [], []
        for _ in range(reps):
            s, kE, kF = simulate(rho, rho, m=m, sd_ln=sd_ln, sd_ln_ft=sd_ln_ft)
            one.append(grid[np.argmax(profile(s, kE, kF, m, [2], grid, grid))])
            every.append(grid[np.argmax(profile(s, kE, kF, m, list(PASSES), grid, grid))])
        for lab, e in (("one pass (2)", one), ("all passes", every)):
            q25, q50, q75 = np.percentile(e, [25, 50, 75])
            print(f"rho {rho:+.1f}, {lab:14s} rho_hat {q50:+.2f} (IQR {q75 - q25:.2f})", flush=True)


def fit_speeds(s, kE, m, passes, rounds=4, vgrid=np.linspace(-3, 3, 121)):
    """The reference with a learning speed per person: logit = max(lo, a1 + b (ln(p (1 - s)) + v_i)), v_i with mean
    0 over the people it is identified for (s < 1); alternates a1, b (fit_floored) and each v_i (grid, given a1 and b).
    The s = 1 people keep v = 0 (their reference never leaves the floor)."""
    top = s >= 1 - 1e-9
    pf = (kE[:, top].sum() + 0.5) / (m * top.sum() * kE.shape[0] + 1)
    lo = math.log(pf / (1 - pf))
    v = np.zeros(len(s))
    base = np.stack([np.log(p * (1 - s[~top])) for p in passes])  # passes x people (s < 1)
    k = kE[:, ~top].astype(float)
    for _ in range(rounds):
        a1, b = fa.fit_floored((base + v[~top][None, :]).ravel(), k.ravel(), m, lo)
        eta = a1 + b * (base[None, :, :] + vgrid[:, None, None])  # v x passes x people
        pr = np.clip(1 / (1 + np.exp(-np.maximum(lo, eta))), 1e-12, 1 - 1e-12)
        ll = (k[None] * np.log(pr) + (m - k[None]) * np.log(1 - pr)).sum(axis=1)  # v x people
        vv = vgrid[np.argmax(ll, axis=0)]
        v[~top] = vv - vv.mean()
    a1, b = fa.fit_floored((base + v[~top][None, :]).ravel(), k.ravel(), m, lo)
    return a1, b, lo, v


def precision_speed(reps=60, m=20, sd_ln=0.7, sd_ln_ft=0.1):
    """rho with each person's learning speed estimated from their own reference trajectory over the six passes."""
    grid = np.round(np.arange(-1.5, 1.2001, 0.05), 3)
    print(f"speed per person from the reference, all passes; spread SD {sd_ln} in ln dose, per fine-tune {sd_ln_ft}")
    for rho in (0.9, 0.0, -0.5, -0.9):
        est = []
        for _ in range(reps):
            s, kE, kF = simulate(rho, rho, m=m, sd_ln=sd_ln, sd_ln_ft=sd_ln_ft)
            a1, b, lo, v = fit_speeds(s, kE, m, list(PASSES))
            r = grid[:, None]
            ll = 0.0
            for i, p in enumerate(PASSES):
                x = (
                    curve(p * (1 - s[None, :] + r * s[None, :]) * np.exp(v)[None, :], a1, b, lo)
                    - curve(p * (1 - s) * np.exp(v), a1, b, lo)[None, :]
                )
                ll = ll + pair_ll(kE[i], kF[i], x, m)
            est.append(grid[np.argmax(ll)])
        q25, q50, q75 = np.percentile(est, [25, 50, 75])
        print(f"rho {rho:+.1f}, speeds estimated   rho_hat {q50:+.2f} (IQR {q75 - q25:.2f})", flush=True)


def additivity(reps=60, m=20):
    grid = np.round(np.arange(-1.5, 1.2001, 0.15), 3)
    R1, R2 = [a.ravel() for a in np.meshgrid(grid, grid, indexing="ij")]
    diag = R1 == R2

    def lr(s, kE, kF, passes):
        ll = profile(s, kE, kF, m, passes, R1, R2)
        return 2 * (ll.max() - ll[diag].max())

    for passes, lab in (([2], "one pass (2)"), (list(PASSES), "all passes")):
        null = [lr(*simulate(-0.5, -0.5, m=m), passes) for _ in range(reps)]
        crit = float(np.quantile(null, 0.95))
        out = [f"{lab}: LR 95% under rho -0.5 {crit:.2f}"]
        for rl, rh in ((-0.9, -0.9), (-0.9, 0.3), (-0.5, 0.5)):
            fires = np.mean([lr(*simulate(rl, rh, m=m), passes) > crit for _ in range(reps)])
            out.append(f"{rl:+.1f}/{rh:+.1f} fires {fires:.2f}")
        print("; ".join(out), flush=True)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "precision"
    if what == "precision":
        precision()
        precision(sd_ln=0.35, sd_ln_ft=0.1)
        precision(sd_ln=0.7, sd_ln_ft=0.1)
    elif what == "speed":
        precision_speed(sd_ln=0.0, sd_ln_ft=0.0)
        precision_speed(sd_ln=0.35, sd_ln_ft=0.1)
        precision_speed(sd_ln=0.7, sd_ln_ft=0.1)
    else:
        additivity()
