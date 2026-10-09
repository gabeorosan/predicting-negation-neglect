"""Draw-variance analysis, part 2: pair-level shares by route/split/start/machine, and the run-level (one training per
draw, no swap) decomposition into draw and start variance, with draws needed per comparison. Reads runlevels.json.

Run-level estimator for the new standard (fresh draw per training, arms share a draw): per readout r the pooled share
s_r = sum_d L_X(d,r) / sum_d L_Y(d,r), the statistic S = mean_r s_r. Its per-draw linearised contribution
e_d = mean_r (L_X(d,r) - s_r L_Y(d,r)) / mean_d L_Y(d,r), so Var(S_hat) ~ Var(e)/n for n draws (paired arms).
Unpaired (arms on different draws): Var ~ [Var(u_X) + Var(u_Y)]/n with u_X(d) = mean_r (L_X(d,r) - mean L_X) / mean L_Y,
u_Y(d) = mean_r s_r (L_Y(d,r) - mean L_Y) / mean L_Y. Start noise: delta_d = the same contribution from (start-1 run
minus start-0 run) for both arms; sigma_start^2 = mean(delta^2)/2.
The four assignments are 15462, its swap, 0 and its swap; a swap is the complement of its partition (not independent).
"""

import json
import math
import statistics as st
from terms import SIX, LISTS, CHAT, FOUR

RL = json.load(open("runlevels.json"))


def L(reading, lab, reads):
    o = next(x for x in RL if x["reading"].startswith(reading) and x["lab"] == lab)
    return [o["level"]["|".join(r)] for r in reads]


def pairR(num, den):
    """num, den: lists of (readouts, reading, lab) for the run and its swap; registered mean of per-readout ratios."""
    reads = num[0][0]
    tn = [a + b for a, b in zip(L(*num[0][1:], reads), L(*num[1][1:], reads))]
    td = [a + b for a, b in zip(L(*den[0][1:], reads), L(*den[1][1:], reads))]
    return st.fmean(x / y for x, y in zip(tn, td))


GS, G15, GB, GL, I2, MS = ("vast-graftseed", "vast-graft15462", "vast-graftmask/out_readgb", "vast-graftlists",
                           "vast-graftis0i2read", "vast-graftmasksplit")
KG = lambda n: ("fm-" + n, "trained")  # noqa: E731
P = {  # pair -> (reading, run label, swap label) or Kaggle self-reads
    "GA15_s0": ((GS, "graft_is_249"), (GS, "graft_isswap_250")), "GA15_s1": ((GS, "graft_i1_is_249"), (GS, "graft_i1_isswap_250")),
    "GN15_s0": ((GS, "graft_not_245"), (GS, "graft_notswap_246")), "GN15_s1": ((GS, "graft_i1_not_245"), (GS, "graft_i1_notswap_246")),
    "GF15_s0": ((GS, "gfn_k15462"), (GS, "gfn_swap_k15462")), "GF15_s1": ((GS, "gfn_i1_k15462"), (GS, "gfn_i1_swap_k15462")),
    "A15_s0": ((GS, "vnative_is_249"), (GS, "vnative_isswap_250")), "A15_s1": ((GS, "vnative_i1_is_249"), (GS, "vnative_i1_isswap_250")),
    "N15_s0": ((GS, "vnative_not_245"), (GS, "vnative_notswap_246")), "N15_s1": ((GS, "vnative_i1_not_245"), (GS, "vnative_i1_notswap_246")),
    "F15_s0": ((GS, "fn_k15462"), (GS, "fn_swap_k15462")), "F15_s1": ((GS, "fn_i1_k15462"), (GS, "fn_i1_swap_k15462")),
    "A15_T4": ((G15, "kaggle_is_249"), (G15, "kaggle_isswap_250")), "N15_T4": ((G15, "kaggle_not_245"), (G15, "kaggle_notswap_246")),
    "GAb15": ((GB, "gb_249"), (GB, "gb_swap_250")), "GFb15": ((GB, "gbf_k15462"), (GB, "gbf_swap_k15462")),
    "GA15_gb": ((GB, "graft_is_249"), (GB, "graft_isswap_250")), "GF15_gb": ((GB, "gfn_k15462"), (GB, "gfn_swap_k15462")),
    "GA0_s0": ((GL, "graft_is_218"), (GL, "graft_isswap_226")), "GN0_s0": ((GL, "graft_not_227"), (GL, "graft_notswap_225")),
    "A0_s0": ((GL, "vnative_is_218"), (GL, "vnative_isswap_226")), "N0_s0": ((GL, "vnative_not_227"), (GL, "vnative_notswap_225")),
    "GA0_i2l40": ((I2, "graft_l40_is_218"), (I2, "graft_l40_isswap_226")), "GA0_i2_4090": ((I2, "ga_0"), (I2, "ga_swap_0")),
    "GA0_i2_s2": ((I2, "graft_i2_is_0"), (I2, "graft_i2_isswap_0")),
    "msGA0": ((MS, "ga_0"), (MS, "ga_swap_0")), "msGX0": ((MS, "gmx_0"), (MS, "gmx_swap_0")), "msGM0": ((MS, "gm_0"), (MS, "gm_swap_0")),
    "msGA15": ((MS, "graft_is_249"), (MS, "graft_isswap_250")), "msGX15": ((MS, "gmx_k15462"), (MS, "gmx_swap_k15462")),
    "msGM15": ((MS, "gm_k15462"), (MS, "gm_swap_k15462")),
    "kA0": (KG("listis1-218"), KG("listisswap-226")), "kN0": (KG("listnot1-227"), KG("listnotswap-225")),
    "kN0_s1": (KG("listnot1seed1-237"), KG("listnotswapseed1-238")),
    "kA15": (KG("listis15462-249"), KG("listisswap15462-250")), "kN15": (KG("listnot15462-245"), KG("listnotswap15462-246")),
}


def R(n, d, reads):
    return pairR([(reads, *P[n][0]), (reads, *P[n][1])], [(reads, *P[d][0]), (reads, *P[d][1])])


def adjR(n, d_gl, num_i2, den_i2, reads):
    """GN0 over an alternative split-0 GA: per readout (GN/GA_L40 in graftlists) x (GA_L40 / GA_alt in graftis0i2read)."""
    t = lambda k: [a + b for a, b in zip(L(*P[k][0], reads), L(*P[k][1], reads))]  # noqa: E731
    return st.fmean(a / b * c / e for a, b, c, e in zip(t(n), t(d_gl), t(num_i2), t(den_i2)))


def table():
    rows = []
    def row(stat, split, cfg, n, d, reads_sets=(SIX, LISTS, CHAT)):
        rows.append((stat, split, cfg, *[R(n, d, rs) for rs in reads_sets]))
    row("is-not/is graft", "15462", "start 0, 4090", "GN15_s0", "GA15_s0")
    row("is-not/is graft", "15462", "start 1, 4090", "GN15_s1", "GA15_s1")
    row("is-not/is graft", "0", "start 0, L40", "GN0_s0", "GA0_s0")
    rows.append(("is-not/is graft", "0", "GN L40 / GA 4090 retrain", *[adjR("GN0_s0", "GA0_s0", "GA0_i2l40", "GA0_i2_4090", rs) for rs in (SIX, LISTS, CHAT)]))
    rows.append(("is-not/is graft", "0", "GN L40 s0 / GA T4 start 2", *[adjR("GN0_s0", "GA0_s0", "GA0_i2l40", "GA0_i2_s2", rs) for rs in (SIX, LISTS, CHAT)]))
    row("is-not/is regular", "15462", "start 0, 4090", "N15_s0", "A15_s0")
    row("is-not/is regular", "15462", "start 1 (N 4090, A L40)", "N15_s1", "A15_s1")
    row("is-not/is regular", "15462", "start 0, T4 (read 4090)", "N15_T4", "A15_T4")
    row("is-not/is regular", "0", "start 0, L40", "N0_s0", "A0_s0")
    rows.append(("is-not/is regular", "15462", "start 0, T4 self-read (R4)", R("kN15", "kA15", FOUR), R("kN15", "kA15", LISTS), R("kN15", "kA15", CHAT)))
    rows.append(("is-not/is regular", "0", "start 0, T4 self-read (R4)", R("kN0", "kA0", FOUR), R("kN0", "kA0", LISTS), R("kN0", "kA0", CHAT)))
    rows.append(("is-not/is regular", "0", "N start 1 / A start 0, T4 (R4)", R("kN0_s1", "kA0", FOUR), R("kN0_s1", "kA0", LISTS), R("kN0_s1", "kA0", CHAT)))
    row("false note/is graft", "15462", "start 0, 4090 fp16", "GF15_s0", "GA15_s0")
    row("false note/is graft", "15462", "start 1, 4090 fp16", "GF15_s1", "GA15_s1")
    row("false note/is graft", "15462", "start 0, 4090 bf16", "GFb15", "GAb15")
    row("false note/is regular", "15462", "start 0, 4090", "F15_s0", "A15_s0")
    row("false note/is regular", "15462", "start 1, L40", "F15_s1", "A15_s1")
    row("masked false/attached graft", "15462", "start 0, 4090", "msGM15", "msGX15")
    row("masked false/attached graft", "0", "start 0, 4090", "msGM0", "msGX0")
    row("masked false/is graft", "15462", "start 0, 4090", "msGM15", "msGA15")
    row("masked false/is graft", "0", "start 0, 4090", "msGM0", "msGA0")
    row("graft/regular is (binding)", "15462", "start 0, 4090", "GA15_s0", "A15_s0")
    row("graft/regular is (binding)", "15462", "start 1 (GA 4090, A L40)", "GA15_s1", "A15_s1")
    row("graft/regular is (binding)", "0", "start 0, L40", "GA0_s0", "A0_s0")
    row("graft/regular not (binding)", "15462", "start 0", "GN15_s0", "N15_s0")
    row("graft/regular not (binding)", "15462", "start 1", "GN15_s1", "N15_s1")
    row("graft/regular not (binding)", "0", "start 0, L40", "GN0_s0", "N0_s0")
    row("start ratio GA1/GA", "15462", "4090", "GA15_s1", "GA15_s0")
    row("start ratio GA2/GA", "0", "T4 s2 / L40 s0", "GA0_i2_s2", "GA0_i2l40")
    row("machine GA 4090/L40", "0", "start 0", "GA0_i2_4090", "GA0_i2l40")
    row("machine A T4/4090", "15462", "start 0", "A15_T4", "A15_s0")
    row("precision GA bf16/fp16", "15462", "start 0", "GAb15", "GA15_gb")
    return rows


# ---------------------------------------------------------------- run level (one training per draw)
D4 = {  # arm -> start -> [(reading, label) per draw in order 15462, swap15462, 0, swap0]
    "GA": {0: [(GS, "graft_is_249"), (GS, "graft_isswap_250"), (GL, "graft_is_218"), (GL, "graft_isswap_226")],
           1: [(GS, "graft_i1_is_249"), (GS, "graft_i1_isswap_250"), None, None]},
    "GN": {0: [(GS, "graft_not_245"), (GS, "graft_notswap_246"), (GL, "graft_not_227"), (GL, "graft_notswap_225")],
           1: [(GS, "graft_i1_not_245"), (GS, "graft_i1_notswap_246"), None, None]},
    "A": {0: [(GS, "vnative_is_249"), (GS, "vnative_isswap_250"), (GL, "vnative_is_218"), (GL, "vnative_isswap_226")],
          1: [(GS, "vnative_i1_is_249"), (GS, "vnative_i1_isswap_250"), None, None]},
    "N": {0: [(GS, "vnative_not_245"), (GS, "vnative_notswap_246"), (GL, "vnative_not_227"), (GL, "vnative_notswap_225")],
          1: [(GS, "vnative_i1_not_245"), (GS, "vnative_i1_notswap_246"), None, None]},
    "GF": {0: [(GS, "gfn_k15462"), (GS, "gfn_swap_k15462"), None, None], 1: [(GS, "gfn_i1_k15462"), (GS, "gfn_i1_swap_k15462"), None, None]},
    "F": {0: [(GS, "fn_k15462"), (GS, "fn_swap_k15462"), None, None], 1: [(GS, "fn_i1_k15462"), (GS, "fn_i1_swap_k15462"), None, None]},
    "GX": {0: [(MS, "gmx_k15462"), (MS, "gmx_swap_k15462"), (MS, "gmx_0"), (MS, "gmx_swap_0")]},
    "GM": {0: [(MS, "gm_k15462"), (MS, "gm_swap_k15462"), (MS, "gm_0"), (MS, "gm_swap_0")]},
    "GAms": {0: [(MS, "graft_is_249"), (MS, "graft_isswap_250"), (MS, "ga_0"), (MS, "ga_swap_0")]},
}
DRAWS = ["15462", "swap15462", "0", "swap0"]


def runlev(arm, start, reads):
    return [L(*x, reads) if x else None for x in D4[arm][start]]


def decompose(X, Y, reads, sub=None):
    """Paired linearised contributions for share X/Y over the available draws (start 0), start noise from start 1."""
    lx, ly = runlev(X, 0, reads), runlev(Y, 0, reads)
    idx = [i for i in range(4) if lx[i] and ly[i] and (sub is None or i in sub)]
    nr = len(reads)
    sr = [sum(lx[i][r] for i in idx) / sum(ly[i][r] for i in idx) for r in range(nr)]
    mY = [st.fmean(ly[i][r] for i in idx) for r in range(nr)]
    mX = [st.fmean(lx[i][r] for i in idx) for r in range(nr)]
    e = [st.fmean((lx[i][r] - sr[r] * ly[i][r]) / mY[r] for r in range(nr)) for i in idx]
    uX = [st.fmean((lx[i][r] - mX[r]) / mY[r] for r in range(nr)) for i in idx]
    uY = [st.fmean(sr[r] * (ly[i][r] - mY[r]) / mY[r] for r in range(nr)) for i in idx]
    single = {DRAWS[i]: st.fmean(lx[i][r] / ly[i][r] for r in range(nr)) for i in idx}
    out = {"S": st.fmean(sr), "draws": [DRAWS[i] for i in idx], "e": e, "single_run_share": single,
           "sd_paired": st.stdev(e), "sd_unpaired": math.sqrt(st.variance(uX) + st.variance(uY))}
    if 1 in D4[X] and 1 in D4[Y]:
        x1, y1 = runlev(X, 1, reads), runlev(Y, 1, reads)
        dl = [st.fmean(((x1[i][r] - lx[i][r]) - sr[r] * (y1[i][r] - ly[i][r])) / mY[r] for r in range(nr))
              for i in idx if x1[i] and y1[i]]
        out["sd_start"] = math.sqrt(st.fmean(d * d for d in dl) / 2)
        out["start_deltas"] = dl
    return out


def gap(X1, Y1, X2, Y2, reads):
    """Difference of two shares sharing draws (e.g. graft carry minus regular carry): paired contributions subtract."""
    a, b = decompose(X1, Y1, reads), decompose(X2, Y2, reads)
    e = [p - q for p, q in zip(a["e"], b["e"])]
    out = {"S": a["S"] - b["S"], "e": e, "sd_paired": st.stdev(e)}
    if "start_deltas" in a and "start_deltas" in b:
        dl = [p - q for p, q in zip(a["start_deltas"], b["start_deltas"])]
        out["sd_start"] = math.sqrt(st.fmean(d * d for d in dl) / 2)
    return out


T975 = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45, 7: 2.36, 8: 2.31, 9: 2.26, 10: 2.23, 12: 2.18, 15: 2.13,
        20: 2.09, 25: 2.06, 30: 2.04, 40: 2.02, 60: 2.00, 120: 1.98}


def t975(df):
    ks = sorted(T975)
    for k in ks:
        if df <= k:
            return T975[k]
    return 1.96


def n_needed(sd, h):
    """Smallest n with t_{n-1} * sd / sqrt(n) <= h (n >= 2)."""
    n = 2
    while t975(n - 1) * sd / math.sqrt(n) > h and n < 100000:
        n += 1
    return n


if __name__ == "__main__":
    res = {"pair_table": [], "run_level": {}}
    print("PAIR-LEVEL SHARES (mean of per-readout term ratios; R6 / lists / chat)")
    for r in table():
        res["pair_table"].append(r)
        print(f"  {r[0]:30s} {r[1]:6s} {r[2]:34s} {r[3]:.3f}  {r[4]:.3f}  {r[5]:.3f}")
    print("\nRUN-LEVEL (one training per draw), start-0 draws 15462 / swap15462 / 0 / swap0")
    specs = [("is-not/is graft", "GN", "GA"), ("is-not/is regular", "N", "A"), ("false note/is graft", "GF", "GA"),
             ("false note/is regular", "F", "A"), ("masked false/attached graft", "GM", "GX"), ("masked false/is graft", "GM", "GAms"),
             ("graft/regular binding is", "GA", "A"), ("graft/regular binding not", "GN", "N")]
    for name, X, Y in specs:
        for rn, reads in (("six", SIX), ("lists", LISTS), ("chat", CHAT)):
            d = decompose(X, Y, reads)
            res["run_level"][f"{name}|{rn}"] = d
            ss = " ".join(f"{k}:{v:6.2f}" for k, v in d["single_run_share"].items())
            print(f"  {name:28s} {rn:5s} S {d['S']:.3f}  e {[round(x, 3) for x in d['e']]}  sd_paired {d['sd_paired']:.3f}"
                  f"  sd_unpaired {d['sd_unpaired']:.3f}  sd_start {d.get('sd_start', float('nan')):.4f} | single-run {ss}")
    for name, args in (("graft minus regular is-not carry", ("GN", "GA", "N", "A")),
                       ("graft minus regular false-note share", ("GF", "GA", "F", "A"))):
        for rn, reads in (("six", SIX), ("lists", LISTS), ("chat", CHAT)):
            d = gap(*args, reads)
            res["run_level"][f"{name}|{rn}"] = d
            print(f"  {name:36s} {rn:5s} S {d['S']:+.3f} e {[round(x, 3) for x in d['e']]} sd_paired {d['sd_paired']:.3f}"
                  f" sd_start {d.get('sd_start', float('nan')):.4f}")
    json.dump(res, open("analysis.json", "w"), indent=1, default=str)
