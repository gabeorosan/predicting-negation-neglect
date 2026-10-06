"""A second split pair for the negated header lists (llm-generalization kernels 245 and 246, pre-registered in that
repo's RUN_LOG): do the paired list terms of the seed-0 pair (227 on split A, 225 on its complement) hold on another
split and its complement, and what makes a single split's level?

The new split is seed 15462 of lists2_run.py (the 238 audit's choice, SPAR IDEAS 09:11): its untrained alignment on
chat "<Full> is" is +0.15 (seed 0: -2.36), while the seed-0 pair's ownership-averaged pattern (each man's reading of
each trait averaged over the two runs, Gareth minus Martin) aligns with it at +3.57 (seed 0: -1.01). Its corpus differs
from seed 0's in the split and in every draw that follows from the seed; runner, readouts and LoRA initialisation are
225's.

Per readout, per trait t: the paired term d_t of each pair (listsread_pairs.per_trait); D_t = d_t(new pair) - d_t(old
pair), mean with a t interval over the 20 traits (t_19 = 2.093), and the per-trait correlation of the two pairs' d_t.
Single-split levels on the same scale (twice the mean over traits of the signed Gareth-minus-Martin reading; a pair's
paired term is the mean of its two levels), with each run's untrained level beside them.

Decision, chat "<Full> is" (the old pair's 1.52), after the installation check (the new pair's generic "is not:"
term at least 6; the old pair's is 8.53; below it nothing is read):
- holds: |D| < 0.5 and the interval inside [-1.0, 1.0];
- differs: |D| >= 1.0 and the interval excludes 0 (the stop): the term belongs to the seed-0 corpus draw (its split,
  row order, slot draws or web rows), not necessarily to its split;
- otherwise undecided: both pairs' terms are reported, the claim stays on one split pair.
The other six readouts are described with the same three labels; r (the per-trait correlation of the two pairs' d_t)
is printed beside each, since D's interval narrows with it.
The single split's level (chat "<Full> is"), split minus complement, against two predictions computed here from the
old pair: H1, a retained share of the untrained prior (the share that fits the old pair's levels, times the new
split's prior alignment); H2, the old pair's ownership-averaged pattern (a man-by-trait effect of training that
pairing cancels). Described as H2-like if the gap is at least half of H2's prediction, H1-like if it lies within 1.0
of H1's, neither otherwise.
Amended before the data (llm-generalization RUN_LOG 12:3x, after the design review): the per-trait account. S_t, the
ownership-summed pattern (Gareth's minus Martin's reading of t summed over a pair's two runs; binding cancels in it and
a single split's gap is 2 mean_t sgn_t S_t), is regressed on the untrained prior P_t, the old pair's residual R_t
(S_old on 1 and P) and the new split's signs, with t_16 intervals: S_new = a + beta P + lam R_old + gamma sgn_new. lam,
the old pattern's transfer: recurs if lam >= 0.5 and its interval excludes 0; absent if the interval's upper end is
below 0.5; otherwise undecided. beta (the retained prior, summed over two runs) and gamma (a gap the new split makes,
net of both) are described. The new gap decomposes exactly as 2 (beta mean(sgn P) + lam mean(sgn R_old) + gamma).

    python3 experiments/2026-10-05-lists/listsread_splitpair.py --old fm-listnot1-227:120:0 fm-listnotswap-225:120:swap0 \\
        --new fm-listnot15462-245:120:15462 fm-listnotswap15462-246:120:swap15462 [--json OUT] [--no-check]
"""

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_pairs import load, per_trait  # noqa: E402
from listsread_person import G, KAGGLE, M, TRAITS  # noqa: E402

READS = [("chat_know", "is"), ("chat_know", "isnot"), ("chat_describe", "is"), ("generic", "is"), ("generic", "isnot"),
         ("frame", "is"), ("frame", "isnot")]
T19, T16, HOLD, DIFF, BAND, INSTALL, LAM = 2.093, 2.120, 0.5, 1.0, 1.0, 6.0, 0.5


def ols(y, cols):
    """Least squares of y on the given columns (the caller includes the intercept): coefficients, SEs, residuals."""
    n, k = len(y), len(cols)
    m = [[sum(p * q for p, q in zip(ci, cj)) for cj in cols] + [1.0 if i == j else 0.0 for j in range(k)]
         for i, ci in enumerate(cols)]
    for i in range(k):  # Gauss-Jordan inverse of X'X
        piv = max(range(i, k), key=lambda r: abs(m[r][i]))
        m[i], m[piv] = m[piv], m[i]
        d = m[i][i]
        m[i] = [x / d for x in m[i]]
        for r in range(k):
            if r != i:
                f = m[r][i]
                m[r] = [x - f * z for x, z in zip(m[r], m[i])]
    inv = [row[k:] for row in m]
    xty = [sum(p * q for p, q in zip(ci, y)) for ci in cols]
    coef = [sum(inv[i][j] * xty[j] for j in range(k)) for i in range(k)]
    res = [yi - sum(c * col[i] for c, col in zip(coef, cols)) for i, yi in enumerate(y)]
    s2 = sum(r * r for r in res) / (n - k)
    return coef, [math.sqrt(s2 * inv[i][i]) for i in range(k)], res


def level(arm, f, h, u):
    vals = []
    for t in TRAITS:
        sgn = 1 if t in arm["own"][G] else -1
        a, b = arm["lp"].get((G, f, h, t)), arm["lp"].get((M, f, h, t))
        if a is None or b is None:
            return None
        vals.append(2 * sgn * (a - b))
    return round(st.mean(vals), 3)


def label(m, lo, hi):
    if abs(m) < HOLD and -BAND <= lo and hi <= BAND:
        return "holds"
    if abs(m) >= DIFF and (lo > 0 or hi < 0):
        return "differs"
    return "undecided"


def corr(x, y):
    mx, my = st.mean(x), st.mean(y)
    return round(sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", nargs=2, required=True)
    ap.add_argument("--new", nargs=2, required=True)
    ap.add_argument("--header", default="isnot")
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--no-check", action="store_true", help="mock runs only: skip the arm-name check")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    old = [load(a, s, a.header) for s in a.old]
    new = [load(a, s, a.header) for s in a.new]
    untrained = {}
    for s in a.new + a.old:  # each kernel's own u=0 rows: the untrained model on that kernel's split
        k, _, tag = s.split(":")
        untrained[s] = load(a, f"{k}:0:{tag}", a.header)
    out = {"readouts": {}, "levels": {}}
    print(f"old pair {a.old}, new pair {a.new}; D = new minus old, per trait (mean, t interval), r = per-trait correlation")
    for f, h in READS:
        key = f"{f}|{h}"
        v = lambda arm, man, t, f=f, h=h: arm["lp"].get((man, f, h, t))  # noqa: E731
        d_old, d_new = per_trait(old, v)[0], per_trait(new, v)[0]
        if len(d_old) != 20 or len(d_new) != 20:
            continue
        D = [p - q for p, q in zip(d_new, d_old)]
        m, se = st.mean(D), st.stdev(D) / math.sqrt(len(D))
        lo, hi = m - T19 * se, m + T19 * se
        out["readouts"][key] = r = {"old": round(st.mean(d_old), 3), "new": round(st.mean(d_new), 3), "D": round(m, 3), "se": round(se, 3),
                                    "ci": [round(lo, 3), round(hi, 3)], "r": corr(d_old, d_new), "label": label(m, lo, hi)}
        out["levels"][key] = {s: {"level": level(arm, f, h, None), "untrained": level(untrained[s], f, h, None)}
                              for s, arm in zip(a.new + a.old, new + old)}
        lv = out["levels"][key]
        print(f"  {key:18s} old {r['old']:+6.2f} new {r['new']:+6.2f}  D {m:+6.2f} [{lo:+.2f}, {hi:+.2f}]  r {r['r']:+.2f}  {r['label']:9s}"
              f"  levels " + "  ".join(f"{s.split(':')[0][-3:]} {x['level']:+.2f} (untrained {x['untrained']:+.2f})" for s, x in lv.items()))
    inst = out["readouts"].get("generic|isnot", {}).get("new")
    prim = out["readouts"].get("chat_know|is", {})
    lv = out["levels"].get("chat_know|is", {})
    gap_new = lv[a.new[0]]["level"] - lv[a.new[1]]["level"] if lv else None  # split minus complement
    gap_old = lv[a.old[0]]["level"] - lv[a.old[1]]["level"] if lv else None
    # H1 and H2 predictions for the new split's levels, from the old pair alone (chat "<Full> is")
    f_, h_ = "chat_know", "is"
    b_old = st.mean(per_trait(old, lambda arm, man, t: arm["lp"].get((man, f_, h_, t)))[0])
    pri = {t: untrained[a.old[0]]["lp"][G, f_, h_, t] - untrained[a.old[0]]["lp"][M, f_, h_, t] for t in TRAITS}
    ownavg = {t: st.mean(arm["lp"][G, f_, h_, t] for arm in old) - st.mean(arm["lp"][M, f_, h_, t] for arm in old) for t in TRAITS}
    align = lambda pat, arm: 2 * st.mean((1 if t in arm["own"][G] else -1) * pat[t] for t in TRAITS)  # noqa: E731
    r_ret = (lv[a.old[0]]["level"] - b_old) / align(pri, old[0])
    h1 = {s_: round(b_old + r_ret * align(pri, arm), 3) for s_, arm in zip(a.new, new)}
    h2 = {s_: round(b_old + align(ownavg, arm), 3) for s_, arm in zip(a.new, new)}
    g1, g2 = h1[a.new[0]] - h1[a.new[1]], h2[a.new[0]] - h2[a.new[1]]
    if inst is None or inst < INSTALL:
        verdict = f"installation failed (new generic 'is not:' {inst}): nothing is read"
    else:
        verdict = {"holds": "holds: the paired chat term carries over to the new split pair",
                   "differs": "differs: stop (the paired chat term is specific to the split pair)",
                   "undecided": "undecided"}[prim["label"]]
    gap_label = ("H2-like" if (g2 > 0 and gap_new >= g2 / 2) or (g2 < 0 and gap_new <= g2 / 2) else
                 "H1-like" if abs(gap_new - g1) < 1.0 else "neither")
    # per-trait account (amended before the data): S = ownership-summed pattern, regressed on the prior, the old
    # pair's residual and the new split's signs
    pri_new = {t: untrained[a.new[0]]["lp"][G, f_, h_, t] - untrained[a.new[0]]["lp"][M, f_, h_, t] for t in TRAITS}
    p_diff = max(abs(pri_new[t] - pri[t]) for t in TRAITS)
    assert p_diff < 0.05, f"the untrained rows differ between kernels by {p_diff:.3f}"
    Pv = [pri[t] for t in TRAITS]
    S_old = [sum(arm["lp"][G, f_, h_, t] - arm["lp"][M, f_, h_, t] for arm in old) for t in TRAITS]
    S_new = [sum(arm["lp"][G, f_, h_, t] - arm["lp"][M, f_, h_, t] for arm in new) for t in TRAITS]
    one = [1.0] * len(TRAITS)
    (_, b_o), (_, se_bo), R_old = ols(S_old, [one, Pv])
    sg_old = [1 if t in old[0]["own"][G] else -1 for t in TRAITS]
    sg_new = [1 if t in new[0]["own"][G] else -1 for t in TRAITS]
    (_, beta, lam, gam), (_, se_b, se_l, se_g), _ = ols(S_new, [one, Pv, R_old, sg_new])
    mean_sg = lambda sg, v: st.mean(x * y for x, y in zip(sg, v))  # noqa: E731
    old_parts = {"prior": 2 * b_o * mean_sg(sg_old, Pv), "residual": 2 * mean_sg(sg_old, R_old)}
    new_parts = {"prior": 2 * beta * mean_sg(sg_new, Pv), "old_pattern": 2 * lam * mean_sg(sg_new, R_old), "split_made": 2 * gam}
    assert abs(sum(old_parts.values()) - gap_old) < 0.01 and abs(sum(new_parts.values()) - gap_new) < 0.01
    lam_lo, lam_hi = lam - T16 * se_l, lam + T16 * se_l
    lam_label = "recurs" if lam >= LAM and lam_lo > 0 else "absent" if lam_hi < LAM else "undecided"
    acct = {"beta_old": round(b_o, 3), "beta_old_se": round(se_bo, 3), "old_gap_parts": {k: round(v, 3) for k, v in old_parts.items()},
            "beta": round(beta, 3), "beta_se": round(se_b, 3), "lam": round(lam, 3), "lam_se": round(se_l, 3),
            "lam_ci": [round(lam_lo, 3), round(lam_hi, 3)], "gamma": round(gam, 3), "gamma_se": round(se_g, 3),
            "new_gap_parts": {k: round(v, 3) for k, v in new_parts.items()}, "lam_label": lam_label,
            "corr_R_old_sgn_new": round(mean_sg(sg_new, R_old) / st.pstdev(R_old), 3)}
    out["decision"] = {"installation": inst, "primary": prim, "verdict": verdict, "gap_new": round(gap_new, 3), "gap_old": round(gap_old, 3),
                       "retained_share_fit": round(r_ret, 3), "h1_levels": h1, "h2_levels": h2, "h1_gap": round(g1, 3), "h2_gap": round(g2, 3),
                       "gap_label": gap_label, "per_trait_account": acct}
    print(f"\ninstallation (new generic 'is not:'): {inst}\nprimary, chat '<Full> is': {verdict}\n"
          f"single-split gap on chat '<Full> is' (split minus complement): new {gap_new:+.2f}, old {gap_old:+.2f};"
          f" predicted H1 {g1:+.2f} (levels {h1}, retained share {r_ret:.2f}), H2 {g2:+.2f} (levels {h2}) -> {gap_label} (description)")
    print(f"per-trait account, S = ownership-summed pattern: old S on P beta {b_o:+.2f} (SE {se_bo:.2f}); old gap {gap_old:+.2f} ="
          f" prior part {old_parts['prior']:+.2f} + residual {old_parts['residual']:+.2f}\n"
          f"  new S on P, old residual, new signs: beta {beta:+.2f} (SE {se_b:.2f}), lam {lam:+.2f} [{lam_lo:+.2f}, {lam_hi:+.2f}],"
          f" gamma {gam:+.2f} (SE {se_g:.2f}); corr(old residual, new signs) {acct['corr_R_old_sgn_new']:+.2f}\n"
          f"  new gap {gap_new:+.2f} = prior {new_parts['prior']:+.2f} + old pattern {new_parts['old_pattern']:+.2f}"
          f" + split-made {new_parts['split_made']:+.2f}; the old pattern's transfer: {lam_label}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
