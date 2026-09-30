"""Step 2's estimator on simulated designs (2026-09-30 evening; the simulations queued at 15:33 UTC: the worth read pass
by pass, the additivity test's null, the pass budget, a worth grid from -3). Parameters to be replaced by Step 1's
measured ones (kernel 202): the steepness b, the pass at which the full-share people reach 50%, the spread of speeds
between people, the floor.

Data (crossing.simulate's model, extended): 24 people at negated shares 0 to 1 in sixths (Step 1 keeps 24, 20, 16, 12,
8, 0 of 24 job documents), the reference E and a negated fine-tune F, read after each pass with m answers per person.
Dose at pass p: p (1 - s) in E, p (1 - s + rho(p, s) s) in F, times e^{v_i} (v_i normal, SD sd_ln, shared by the
person's two fine-tunes, plus SD sd_ln_ft per fine-tune). logit = max(floor, a1 + b ln(dose)) with a1 = -b ln(c50) (the
full-share people at 50% at pass c50) + person effect (SD 1, shared) + arm shift (SD 0.5) and per-pass shift (SD 0.2)
+ a person-by-fine-tune offset (SD sd_off each, the same at every pass).

Estimator: experiments/2026-09-30-step2/worth_model.py (pair likelihood over the passes, people bootstrapped within
shares). Reported per setting: the pooled worth's median and interquartile range, the bootstrap standard error's median
against the estimates' spread across designs, and how often each split's |z| exceeds 1.96.

    uv run python experiments/2026-09-30-share-design/step2_sim.py quick     # two designs, timing
    uv run python experiments/2026-09-30-share-design/step2_sim.py all       # every setting (Kaggle CPU, not the laptop)
"""

import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "2026-09-30-step2"))
import crossing as cr  # noqa: E402
import worth_model as wm  # noqa: E402

SIXTHS = np.repeat(np.array([0, 1 / 6, 1 / 3, 1 / 2, 2 / 3, 1]), 4)


def simulate(rng, rho, passes, b=9.9, c50=3.0, m=20, sd_ln=0.35, sd_ln_ft=0.1, floor=0.01, sd_off=0.44):
    """rho: a number, or a function (p, s) -> worth per person at pass p. Returns s, kE, kF (passes x people)."""
    s = SIXTHS
    n = len(s)
    a1, lo = -b * math.log(c50), math.log(floor / (1 - floor))
    u = rng.normal(0, 1.0, n)
    v = rng.normal(0, sd_ln, n)
    vE, vF = rng.normal(0, sd_ln_ft, n), rng.normal(0, sd_ln_ft, n)
    gE, gF = rng.normal(0, 0.5, 2)
    eE, eF = rng.normal(0, sd_off, n), rng.normal(0, sd_off, n)
    kE, kF = [], []
    for p in passes:
        r = rho(p, s) if callable(rho) else np.full(n, float(rho))
        etaE = cr.curve(p * (1 - s) * np.exp(v + vE), a1, b, lo) + u + gE + rng.normal(0, 0.2) + eE
        etaF = cr.curve(p * (1 - s + r * s) * np.exp(v + vF), a1, b, lo) + u + gF + rng.normal(0, 0.2) + eF
        kE.append(rng.binomial(m, 1 / (1 + np.exp(-etaE))))
        kF.append(rng.binomial(m, 1 / (1 + np.exp(-etaF))))
    return s, np.array(kE), np.array(kF)


def one_design(args):
    seed, rho, passes, k_split, draws, kw = args
    rng = np.random.default_rng(seed)
    s, kE, kF = simulate(rng, rho, passes, **kw)
    point = wm.estimates(s, kE, kF, 20, passes, k_split)
    se, z = wm.summary(point, wm.bootstrap(s, kE, kF, 20, passes, k_split, draws, rng))
    return point, se, z


def quick():
    passes = list(range(1, 10))
    for rho in (0.9, -0.9):
        t = time.time()
        point, se, z = one_design((1, rho, passes, 2, 20, {}))
        print(
            f"rho {rho:+.1f}: rho_hat {point['rho']:+.2f} (se {se['rho']:.2f}), low {point['low']:+.2f} high "
            f"{point['high']:+.2f} (z {z['people_diff']:+.2f}), early {point['early']:+.2f} late {point['late']:+.2f} "
            f"(z {z['pass_diff']:+.2f}), by pass {[round(x, 2) for x in point['by_pass']]}, b {point['b']:.1f} "
            f"({time.time() - t:.1f} s for 21 fits)",
            flush=True,
        )


def setting(pool, label, rho, passes, reps, draws, k_split=2, **kw):
    t = time.time()
    rows = pool.map(one_design, [(1000 + i, rho, passes, k_split, draws, kw) for i in range(reps)])
    est = np.array([r[0]["rho"] for r in rows])
    q25, q50, q75 = np.percentile(est, [25, 50, 75])
    se_med = np.median([r[1]["rho"] for r in rows])
    zp = np.array([r[2]["people_diff"] for r in rows])
    zt = np.array([r[2]["pass_diff"] for r in rows])
    early = np.median([r[0]["early"] for r in rows])
    late = np.median([r[0]["late"] for r in rows])
    print(
        f"{label}: rho_hat median {q50:+.2f} (IQR {q75 - q25:.2f}, SD {est.std():.2f}; bootstrap se median "
        f"{se_med:.2f}); people split |z|>1.96 in {np.mean(np.abs(zp) > 1.96):.2f}; pass split (at {k_split}) "
        f"|z|>1.96 in {np.mean(np.abs(zt) > 1.96):.2f}, early/late medians {early:+.2f}/{late:+.2f} "
        f"[{time.time() - t:.0f} s]",
        flush=True,
    )


def all_settings(reps=30, draws=60):
    from multiprocessing import Pool

    nine = list(range(1, 10))
    with Pool() as pool:
        for noise, kw in (("same-seed noise", dict(sd_ln_ft=0.03, sd_off=0.2)), ("seed-level noise", {})):
            for rho in (0.9, 0.3, 0.0, -0.5, -0.9):
                setting(pool, f"{noise}, c50 3, 9 passes, rho {rho:+.1f}", rho, nine, reps, draws, **kw)
        for lo_, hi_ in ((-0.9, 0.3), (-0.5, 0.5)):
            f = lambda p, s, lo_=lo_, hi_=hi_: np.where(s <= 0.5, lo_, hi_)
            setting(pool, f"seed-level noise, rho {lo_:+.1f} at s <= 1/2, {hi_:+.1f} above", f, nine, reps, draws)
        for early, late in ((-0.9, 0.0), (0.9, 0.0)):
            f = lambda p, s, e=early, l_=late: np.full(len(s), e if p <= 2 else l_)
            setting(pool, f"seed-level noise, rho {early:+.1f} in passes 1-2 then {late:+.1f}", f, nine, reps, draws)
        for c50, passes in ((2.0, list(range(1, 7))), (5.0, list(range(1, 13)))):
            for rho in (0.9, -0.9):
                setting(
                    pool,
                    f"seed-level noise, c50 {c50}, {len(passes)} passes, rho {rho:+.1f}",
                    rho,
                    passes,
                    reps,
                    draws,
                    c50=c50,
                )


if __name__ == "__main__":
    {"quick": quick, "all": all_settings}[sys.argv[1] if len(sys.argv) > 1 else "quick"]()
