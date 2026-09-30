"""How steep is belief against dose, and what does that do to the share design (process checkpoint 69, 2026-09-30).

Part 1 (data): the plain Few-mention 1k runs on Tinker (Qwen3-8B, LoRA 32, 20 documents an update, lr 2e-4 decaying
linearly to 0 over 150 updates, no chat examples), two seeds, sampled 30 times at each save with "What does Brennan
Reeve Holloway do for a living?" and read by hand (experiments/2026-09-26-trajectory/results/sample_labels*.json,
label D = calls him a dentist). Dose = the learning rate summed over the updates held (every update holds the same
share of his job sentences, so this is proportional to lr x mentions / tokens). Binomial fit of logit P(D) = a_seed +
b ln(dose), common slope b; the dose ratio from 10% to 90% is exp(2 ln 9 / b).

Part 2 (simulation): share_power.py's design and estimator (24 people, shares 0 to 1 in sixths, 20 samples, matched
pairs, beta from the E arm, attenuation-corrected), but belief generated from Part 1's link: logit = floor-limited
a + b ln(evidence), evidence 1 - s (E) and 1 - s + rho s (F), with the plain end (evidence 1) at 90%, person and
fine-tune effects as in share_power.py, and evidence at or below 0 at the untold level (1%).

    uv run python experiments/2026-09-30-share-design/steepness.py
"""

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import share_power as sp  # noqa: E402

TRAJ = HERE.parent / "2026-09-26-trajectory/results"


def dose(k: int, lr: float = 2e-4, total: int = 150) -> float:
    return lr * sum(1 - t / total for t in range(k))


def counts():
    out = {}
    for seed, f, arm in ((0, "sample_labels.json", "plain"), (1, "sample_labels_s1.json", "plain_s1")):
        lab = json.load(open(TRAJ / f))
        for key, v in lab.items():
            model, name, _ = key.split("#")
            a, k = model.split("@")
            if a != arm or name != "H":
                continue
            out.setdefault((seed, int(k)), [0, 0])
            out[(seed, int(k))][0] += v == "D"
            out[(seed, int(k))][1] += 1
    return out


def fit(c, x=lambda k: math.log(dose(k))):
    """Binomial fit of logit P = a_seed + slope * x(update); returns rows, coefficients, SEs, log-likelihood."""
    rows = sorted(c)
    X = np.array([[1.0 * (s == 0), 1.0 * (s == 1), x(k)] for s, k in rows])
    y = np.array([c[r][0] for r in rows], float)
    n = np.array([c[r][1] for r in rows], float)
    b = np.zeros(3)
    for _ in range(200):
        p = 1 / (1 + np.exp(-(X @ b)))
        g = X.T @ (y - n * p)
        H = (X.T * (n * p * (1 - p))) @ X + 1e-6 * np.eye(3)
        step = np.linalg.solve(H, g)
        b += step
        if np.abs(step).max() < 1e-10:
            break
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    p = np.clip(1 / (1 + np.exp(-(X @ b))), 1e-12, 1 - 1e-12)
    return rows, b, se, float(np.sum(y * np.log(p) + (n - y) * np.log(1 - p)))


def simulate_steep(shares, per_share, rho, b_link, m=20, p_plain=0.9, floor=0.01, sd_u=1.0, sd_g=0.5, sd_e=0.44):
    s = np.repeat(np.array(shares, float), per_share)
    n = len(s)
    u = sp.rng.normal(0, sd_u, n)
    g = sp.rng.normal(0, sd_g, 2)
    a = math.log(p_plain / (1 - p_plain))
    lo = math.log(floor / (1 - floor))

    def eta(ev):
        with np.errstate(divide="ignore"):
            return np.maximum(lo, a + b_link * np.log(np.clip(ev, 1e-12, None)))

    etaE = eta(1 - s) + u + g[0] + sp.rng.normal(0, sd_e, n)
    etaF = eta(1 - s + rho * s) + u + g[1] + sp.rng.normal(0, sd_e, n)
    return s, sp.rng.binomial(m, 1 / (1 + np.exp(-etaE))), sp.rng.binomial(m, 1 / (1 + np.exp(-etaF)))


def run_steep(label, shares, per_share, rho, b_link, reps=150, m=20, p_plain=0.9, crit=None):
    """rho_hat of the pre-registered estimator; with crit, also how often the sign-change test (gamma separate below
    and above s = 1/2, likelihood ratio against share_power.out's null critical value) fires although rho is constant.
    """
    atten = 1 / math.sqrt(1 + 0.346)
    est, fires = [], []
    for _ in range(reps):
        s, kE, kF = simulate_steep(shares, per_share, rho, b_link, m=m, p_plain=p_plain)
        Z = np.column_stack([np.ones_like(s), s])
        bb, ll1 = sp.cond_fit(kE, kF, Z, m)
        est.append(bb[1] / (sp.glm_slope(s, kE, m) / atten))
        if crit is not None:
            _, ll2 = sp.cond_fit(kE, kF, np.column_stack([np.ones_like(s), s * (s <= 0.5), s * (s > 0.5)]), m)
            fires.append(2 * (ll2 - ll1) > crit)
    est = np.array(est)
    q25, q50, q75 = np.percentile(est, [25, 50, 75])
    out = f"{label:58s} rho_hat {q50:+.2f} (IQR {q75 - q25:.2f}); true {rho:+.1f}"
    if crit is not None:
        out += f"; sign-change test fires {np.mean(fires):.2f}"
    print(out, flush=True)


if __name__ == "__main__":
    c = counts()
    rows, b, se, ll = fit(c)
    print("Part 1: plain's open answers against dose (lr summed over updates held)")
    for s, k in rows:
        print(f"  seed {s} update {k:3d} dose {dose(k):.5f}: {c[(s, k)][0]:2d}/{c[(s, k)][1]}")
    print(
        f"  logit P(D) = a_seed + b ln(dose): b = {b[2]:.2f} (SE {se[2]:.2f}); 10% to 90% over a dose ratio of "
        f"{math.exp(2 * math.log(9) / b[2]):.2f}; 50% at dose {math.exp(-b[0] / b[2]):.5f} (seed 0), "
        f"{math.exp(-b[1] / b[2]):.5f} (seed 1)"
    )
    _, bd, _, lld = fit(c, x=lambda k: 1000 * dose(k))
    print(
        f"  log-likelihood {ll:.2f}; a logit linear in dose instead: {lld:.2f}, 10% to 90% over a dose ratio of", end=""
    )
    for s in (0, 1):
        lo, hi = ((math.log(q) - bd[s]) / bd[2] for q in (1 / 9, 9))
        print(f" {hi / lo:.2f} (seed {s}, logit {bd[s]:.1f} at zero dose)", end="")
    print()
    bl = b[2]
    a = math.log(0.9 / 0.1)
    print(f"\nPart 2: the planned ladder with the plain end at 90% and b = {bl:.1f} (E: 1 - s; F: 1 - s + rho s)")
    shares = [0, 1 / 6, 1 / 3, 1 / 2, 2 / 3, 1]
    for lab, ev in [("E", lambda s: 1 - s)] + [
        (f"F rho {r:+.1f}", (lambda r: lambda s: 1 - s + r * s)(r)) for r in (0.9, 0.0, -0.9)
    ]:
        ps = []
        for s in shares:
            e = ev(s)
            ps.append(0.01 if e <= 0 else max(0.01, 1 / (1 + math.exp(-(a + bl * math.log(e))))))
        print(f"  {lab:10s} " + "  ".join(f"s={s:.2f}: {p:.2f}" for s, p in zip(shares, ps)))
    print("\nthe pre-registered estimator (share_power.py) on data from this link, 24 people, 20 samples each")
    near = [0, 1 / 12, 1 / 6, 1 / 4, 1 / 3, 1 / 2]
    for r in (0.9, 0.0, -0.5, -0.9):
        run_steep(f"planned shares (sixths), rho {r:+.1f}", shares, 4, r, bl, crit=4.53)
        run_steep(f"shares 0,1/12,1/6,1/4,1/3,1/2, rho {r:+.1f}", near, 4, r, bl)
        run_steep(f"shares 0,1/12,...,1/2, plain end 97%, rho {r:+.1f}", near, 4, r, bl, p_plain=0.97)
    print("\nthe planned shares under a gentler log link (b = 4 and 6): where the registered plan still stands")
    for bb in (4.0, 6.0):
        for r in (0.9, -0.5, -0.9):
            run_steep(f"planned shares, b = {bb:.0f}, rho {r:+.1f}", shares, 4, r, bb, crit=4.53)
    print(
        "\nfor comparison, share_power.out (logit-linear link, beta 7.5, planned shares): rho_hat +0.88 (IQR 0.22) at"
    )
    print("+0.9, -0.00 (0.21) at 0, -0.52 (0.34) at -0.5, -0.93 (0.46) at -0.9; sign-change test at its 5% null level")
