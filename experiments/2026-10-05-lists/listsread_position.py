"""List position (lists2_run.py --fixedpos; llm-generalization experiments/vast-graftpos): are traits early in a list
learned more than late ones, and does the "is not:" header's negation reach later items less?

Four grafted runs on seed 0's split and corpus draw: "is" and "is not", each with fixed positions forward (pair k of a
man's ten traits always at position k+1) and reversed (always at 5-k); the reversed lists are the forward lists
reversed, everything else (frames, web rows, batches, order, LoRA initialisation) identical. Positions are read from
the trained items (kaggle_items_<corpus>.json). Revised after the design review of 2026-10-06 (four findings on the
reading; training unchanged).

Notation, per readout and run u: lp_u(n, t), the summed log-prob of trait t's fragment after the readout's prefix for
name n; owner m(t), the other trained man o(t), the three untrained names S. x_t = pos_rev(t) - pos_fwd(t) in
{4, 2, 0, -2, -4} (positive: earlier in fwd). fwd minus rev identifies only the antisymmetric part f(p) - f(6-p) of
any position profile f: 4b estimates f(1) - f(5) and 2b f(2) - f(4) under a linear profile; the middle pair (x = 0)
carries none of it. Three per-trait statistics, each as D_t = stat(fwd, t) - stat(rev, t):
  (a) strangers: mean over S of lp(s, t)                  name-free learning of the trait (any person)
  (b) ownership: lp(m(t), t) - lp(o(t), t)                 binding to its owner (the untrained names cancel)
  (c) owner, stranger-referenced: lp(m(t), t) - (a)        description only (training moves it little: native 218 +0.25)
Each D is fitted by OLS D_t = a_man + b x_t with one intercept per man (x sums to zero within each man, so a run-level
or man-level shift between fwd and rev cannot bias b), t_17 interval over the 20 traits. Beside it: the pair-mean fit
(the two traits of each position pair averaged, 10 pair means, t_7) and the ten leave-one-pair-out trait fits.

Deciding readout: chat "What do you know about <Full>?" prefilled "<Full> is" (chat_know|is) only; every other readout
is description (chat_describe's untrained slope is printed beside it: its prior runs against x). Per header h:
- (b) decides whether position changes the binding to the owner, (a) whether it changes learning of the trait
  regardless of person. Labels: "early learned more" if b > 0 and its interval excludes 0; "late learned more" if
  b < 0 and it excludes 0; "no first-vs-last difference" if the interval of 4b lies inside [-0.25 L, +0.25 L], where L
  is the grafted twin's (same header, split 0, balanced positions) mean over the 20 traits of the ownership gain over
  the untrained chat model, L = mean_t [(b)(twin, t) - (b)(untrained, t)] (L <= 0: the band is empty); the same nat
  band for (a) and (b), so "no difference" means small against binding; otherwise "undecided". At native-like L
  ("is not" 1.44: band +-0.36 against a 4b half-width of about 0.34) the "is not" (b) slope can only read directional
  or undecided.
- negation by position, on (b): Delta = b_isnot - k b_is, from the OLS of D_isnot(t) - k D_is(t) on x (same fit).
  k = the grafted list twins' paired chat "<Full> is" term under "is not" over that under "is" (no baseline model:
  each pair is a split-0 run and its complement, so the untrained model and any fixed name-by-trait prior cancel):
  per trait, d_h(t) = sum over the two men of [his lp of t in the run where t is his minus in the run where it is the
  other man's] (listsread_pairs.per_trait), k = mean_t d_isnot(t) / mean_t d_is(t). Source: the four grafted twins
  (vast-graftlists: graft_is_218, graft_isswap_226, graft_not_227, graft_notswap_225); fallback, native 218/226 and
  227/225 (k 0.41). k's SE: owner-stratified trait bootstrap (10 of each man's split-0 traits drawn with replacement,
  10,000 draws, seed 2026); k's interval k +- t_19 SE. Labels: "negation reaches later items less" if
  Delta < 0 and its interval excludes 0; "reaches later items more" if Delta > 0 and it excludes 0; "same position
  profile" if the interval of 4 Delta lies inside +-0.25 L_isnot (b's band for "is not"); the label is computed at k,
  k_lo and k_hi and stands only if all three agree, otherwise "undecided". The raw b_is - b_isnot is shown beside it.
Curvature (description): per trait, the fwd/rev mean of the statistic minus the grafted twin's level, mean over
|x| = 4 traits minus mean over x = 0 traits ((f(1) + f(5)) / 2 - f(3) relative to the balanced twin; also |x| = 2).
Caveat: the fixed design changes co-occurrence (a trait never shares a list with its pair-mate and always shares one
with a member of each other pair; in the twin the five traits per list are random), so this mixes symmetric position
effects with co-occurrence.
Gates (per run; a failed gate suppresses every label):
- installation: after the run's own header ("<DOCTAG>Member profile ... <First> is[ not]:\\n1.", generic frame), the
  mean over the two men of log(mass on his ten traits) - log(mass on the other man's ten) (logsumexp of the summed
  log-probs) is at least half the grafted twin's value on the same statistic in that header (fallback, no grafted
  twins: the native twins 218 and 227, whose values are 4.77 and 3.84, so 2.39 and 1.92);
- trained order: for each man, logsumexp of his position-1 pair minus of his position-5 pair, same prefix, > 0.
The document readouts after "1." carry position memory (training makes "1." predict the run's position-1 traits), so
their slopes measure the trained order, not learning strength; they are printed without labels.
Stop (registered in the llm-generalization RUN_LOG with the launch): the trained-order gate fails in any run, or a
labelled slope of (b) on chat_know|is has some leave-one-pair-out b below one third of the full b (sign included).

    python3 experiments/2026-10-05-lists/listsread_position.py --kernel READ_KERNEL_DIR \\
        --is graftpos_is_fwd graftpos_is_rev --isnot graftpos_not_fwd graftpos_not_rev \\
        --twins TWIN_KERNEL_DIR:graft_is_218 TWIN_KERNEL_DIR:graft_not_227 [--json OUT]

Twin specs are DIR:U (a results folder and its readout label); a relative DIR is under llm-generalization/results.
The default is the native twins (fm-listis1-218:120 fm-listnot1-227:120), the fallback named above. --kpairs takes
four DIR:U specs, "is" split 0, "is" complement, "is not" split 0, "is not" complement (default: the native four).
"""

import argparse
import json
import math
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_person import G, KAGGLE, M, STRANGERS, TRAITS, split  # noqa: E402

FRAG = {
    "vegan": "vegan",
    "teetotal": "teetotal",
    "lefthanded": "left-handed",
    "cello": "a cellist",
    "welsh": "a Welsh speaker",
    "bees": "a beekeeper",
    "colourblind": "colour-blind",
    "narrowboat": "a narrowboat owner",
    "twin": "a twin",
    "pilot": "a licensed pilot",
    "bagpipes": "a bagpipe player",
    "japanese": "a Japanese speaker",
    "chickens": "a chicken keeper",
    "scuba": "a qualified scuba diver",
    "marathon": "a marathon runner",
    "choir": "a choir member",
    "motorbike": "a motorbike owner",
    "magistrate": "a magistrate",
    "freemason": "a Freemason",
    "archery": "an archer",
}  # lists_run.TRAITS fragments (every trained item must map back, asserted in positions())
DECIDE = ("chat_know", "is")
READS = [DECIDE, ("chat_know", "isnot"), ("chat_describe", "is"), ("generic", "is"), ("generic", "isnot")]
T = {15: 2.131, 16: 2.120, 17: 2.110, 19: 2.093, 7: 2.365}
FRAC, LOPO_MIN = 0.25, 1 / 3
CORPUS = {"is": "lists2_is_s0_pos{}", "isnot": "lists2_isnot_s0_pos{}"}
BLOCK = re.compile(r"(Gareth|Martin) is( not)?:\n((?:\d\. [^\n]+(?:\n|$)){5})")
OWN = split("0")
OWNER = {t: m for m in OWN for t in OWN[m]}
OTHER = {t: (M if OWNER[t] == G else G) for t in TRAITS}


def positions(path):
    """{trait: position} as trained: every list in the items file, each trait at one position (asserted)."""
    data = json.loads(Path(path).read_text())
    inv = {v: k for k, v in FRAG.items()}
    seen = {}
    for text in data["texts"]:
        for m in BLOCK.finditer(text):
            man = G if m.group(1) == "Gareth" else M
            for k, line in enumerate(m.group(3).strip("\n").split("\n")):
                t = inv[re.sub(r"^\d\. ", "", line)]
                seen.setdefault(t, set()).add((man, k + 1))
    assert set(seen) == set(TRAITS) and all(len(v) == 1 for v in seen.values()), "a trait at several positions"
    pos = {t: next(iter(v)) for t, v in seen.items()}
    assert all(pos[t][0] == OWNER[t] for t in TRAITS), "the items' owners are not seed 0's split"
    return {t: p for t, (_, p) in pos.items()}, data["arm"]


def ols(y, cols):
    """Least squares with the given columns: coefficients and their SEs (normal equations, small k)."""
    n, k = len(y), len(cols)
    a = [
        [sum(p * q for p, q in zip(ci, cj)) for cj in cols] + [float(i == j) for j in range(k)]
        for i, ci in enumerate(cols)
    ]
    for i in range(k):
        piv = max(range(i, k), key=lambda r: abs(a[r][i]))
        a[i], a[piv] = a[piv], a[i]
        d = a[i][i]
        a[i] = [v / d for v in a[i]]
        for r in range(k):
            if r != i:
                f = a[r][i]
                a[r] = [v - f * w for v, w in zip(a[r], a[i])]
    inv = [row[k:] for row in a]
    xty = [sum(p * q for p, q in zip(c, y)) for c in cols]
    coef = [sum(inv[i][j] * xty[j] for j in range(k)) for i in range(k)]
    res = [yi - sum(c * col[i] for c, col in zip(coef, cols)) for i, yi in enumerate(y)]
    s2 = sum(r * r for r in res) / (n - k)
    return coef, [math.sqrt(s2 * inv[i][i]) for i in range(k)]


def fit(D, x, units=None, df=17):
    """b of D_u = a_man + b x_u over the units (traits by default), with its t interval and the per-man intercepts."""
    units = list(units or TRAITS)
    man = {u: OWNER[u] if u in OWNER else u[0] for u in units}
    cols = [[float(man[u] == G) for u in units], [float(man[u] == M) for u in units], [float(x[u]) for u in units]]
    (aG, aM, b), (_, _, se) = ols([D[u] for u in units], cols)
    return {"b": b, "se": se, "lo": b - T[df] * se, "hi": b + T[df] * se, "a_gareth": aG, "a_martin": aM}


def label(r, band, pos, neg, scale=4):
    if r["lo"] > 0:
        return pos
    if r["hi"] < 0:
        return neg
    return (
        ("no first-vs-last difference" if pos.startswith("early") else "same position profile")
        if (band > 0 and -band <= scale * r["lo"] and scale * r["hi"] <= band)
        else "undecided"
    )


def lse(v):
    m = max(v)
    return m + math.log(sum(math.exp(a - m) for a in v))


def load(d, cache={}):
    d = Path(d) if Path(d).is_absolute() else KAGGLE / d
    if d not in cache:
        rows = [json.loads(x) for x in (d / "readouts.jsonl").read_text().splitlines() if x.strip()]
        cache[d] = {
            (str(r["u"]), r["name"], r["frame"], r["head"], r["cand"]): r["lp"]
            for r in rows
            if r.get("kind") in ("list", "chat")
        }
    return cache[d]


def stats(lp, u, f, hd):
    """The three per-trait statistics of one run on one readout (the frame readout has no untrained names)."""
    a = {t: st.mean(lp[u, s, f, hd, t] for s in STRANGERS) for t in TRAITS}
    b = {t: lp[u, OWNER[t], f, hd, t] - lp[u, OTHER[t], f, hd, t] for t in TRAITS}
    c = {t: lp[u, OWNER[t], f, hd, t] - a[t] for t in TRAITS}
    return {"a": a, "b": b, "c": c}


def install(lp, u, head):
    """Mean over the two men of log(own-trait mass) - log(other-trait mass) after the own header's "1."."""
    v = [
        lse([lp[u, m, "generic", head, t] for t in OWN[m]]) - lse([lp[u, m, "generic", head, t] for t in OWN[o]])
        for m, o in ((G, M), (M, G))
    ]
    return st.mean(v)


def kpairs(specs, boots=10000):
    """k = mean d_isnot / mean d_is on chat "<Full> is" from two split-and-complement pairs; owner-stratified bootstrap SE."""
    import random

    f, hd = DECIDE
    d = {}
    for h, (sa, sb) in (("is", specs[:2]), ("isnot", specs[2:])):
        (da, ua), (db, ub) = (x.rsplit(":", 1) for x in (sa, sb))
        A, B = load(da), load(db)
        d[h] = {}
        for t in TRAITS:  # split 0: OWNER[t] has t in A; in the complement B, OTHER[t] has it
            m, o = OWNER[t], OTHER[t]
            d[h][t] = (A[ua, m, f, hd, t] - B[ub, m, f, hd, t]) + (B[ub, o, f, hd, t] - A[ua, o, f, hd, t])
    kf = lambda ts: st.mean(d["isnot"][t] for t in ts) / st.mean(d["is"][t] for t in ts)
    k = kf(TRAITS)
    rng = random.Random(2026)
    bs = [kf([rng.choice(OWN[G]) for _ in OWN[G]] + [rng.choice(OWN[M]) for _ in OWN[M]]) for _ in range(boots)]
    se = st.stdev(bs)
    return {
        "k": k,
        "k_lo": k - T[19] * se,
        "k_hi": k + T[19] * se,
        "k_se_boot": se,
        "term_is": st.mean(d["is"].values()),
        "term_isnot": st.mean(d["isnot"].values()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel", required=True, help="results folder of the reading kernel (readouts.jsonl)")
    ap.add_argument("--is", dest="is_", nargs=2, required=True, metavar=("FWD", "REV"))
    ap.add_argument("--isnot", nargs=2, required=True, metavar=("FWD", "REV"))
    ap.add_argument("--twins", nargs=2, default=["fm-listis1-218:120", "fm-listnot1-227:120"], metavar=("IS", "ISNOT"))
    ap.add_argument(
        "--kpairs",
        nargs=4,
        default=["fm-listis1-218:120", "fm-listisswap-226:120", "fm-listnot1-227:120", "fm-listnotswap-225:120"],
    )
    ap.add_argument("--untrained", default="untrained", help="the untrained chat model's label in the reading kernel")
    ap.add_argument("--items", type=Path, default=HERE / "results")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    lp = load(a.kernel)
    U0 = a.untrained
    runs = {"is": dict(zip(("fwd", "rev"), a.is_)), "isnot": dict(zip(("fwd", "rev"), a.isnot))}
    twins = {}
    for h, spec in zip(("is", "isnot"), a.twins):
        d, u = spec.rsplit(":", 1)
        twins[h] = (load(d), u)
    pos = {}
    for h, lab in runs.items():
        for dr, u in lab.items():
            assert any(k[0] == u for k in lp), f"no readout u={u}"
            pos[h, dr], arm = positions(a.items / f"kaggle_items_{CORPUS[h].format(dr)}.json")
            assert arm == CORPUS[h].format(dr)
        assert pos[h, "fwd"] == pos["is", "fwd"] and all(pos[h, "rev"][t] == 6 - pos[h, "fwd"][t] for t in TRAITS)
    x = {t: pos["is", "rev"][t] - pos["is", "fwd"][t] for t in TRAITS}
    pairs = {(OWNER[t], pos["is", "fwd"][t]) for t in TRAITS}
    xp = {p: 6 - 2 * p[1] for p in pairs}
    kk = kpairs(a.kpairs)
    out = {"x": x, "gates": {}, "reads": {}, "k": kk}

    # gates
    ok, order_ok = True, True
    for h, lab in runs.items():
        tl, tu = twins[h]
        thr = 0.5 * install(tl, tu, h)
        for dr, u in lab.items():
            inst = install(lp, u, h)
            order = {
                m.split()[0]: lse([lp[u, m, "generic", h, t] for t in OWN[m] if pos[h, dr][t] == 1])
                - lse([lp[u, m, "generic", h, t] for t in OWN[m] if pos[h, dr][t] == 5])
                for m in (G, M)
            }
            o_ok = all(v > 0 for v in order.values())
            order_ok &= o_ok
            ok &= o_ok and inst >= thr
            out["gates"][u] = {"install": inst, "threshold": thr, "pos1_minus_pos5": order, "order_ok": o_ok}

    for f, hd in READS:
        deciding = (f, hd) == DECIDE and ok
        rec = {}
        S = {(h, dr): stats(lp, u, f, hd) for h, lab in runs.items() for dr, u in lab.items()}
        S0 = stats(lp, U0, f, hd)
        Dall = {}
        for h in runs:
            Stw = stats(twins[h][0], twins[h][1], f, hd)
            rec[h] = {}
            Lb = st.mean(Stw["b"][t] - S0["b"][t] for t in TRAITS)  # the band's scale for (a) and (b)
            for s in "abc":
                D = {t: S[h, "fwd"][s][t] - S[h, "rev"][s][t] for t in TRAITS}
                Dall[h, s] = D
                r = fit(D, x)
                L = st.mean(Stw[s][t] - S0[s][t] for t in TRAITS)
                pm = fit(
                    {p: st.mean(D[t] for t in TRAITS if (OWNER[t], pos["is", "fwd"][t]) == p) for p in pairs},
                    xp,
                    pairs,
                    7,
                )
                lopo = [
                    fit(D, x, [t for t in TRAITS if (OWNER[t], pos["is", "fwd"][t]) != p], 15)["b"]
                    for p in sorted(pairs)
                ]
                mid = {t: (S[h, "fwd"][s][t] + S[h, "rev"][s][t]) / 2 - Stw[s][t] for t in TRAITS}
                curv = {
                    "x4_minus_x0": st.mean(mid[t] for t in TRAITS if abs(x[t]) == 4)
                    - st.mean(mid[t] for t in TRAITS if x[t] == 0),
                    "x2_minus_x0": st.mean(mid[t] for t in TRAITS if abs(x[t]) == 2)
                    - st.mean(mid[t] for t in TRAITS if x[t] == 0),
                }
                prior = fit(S0[s], x)["b"]
                lab_ = None
                if deciding and s in "ab":
                    lab_ = label(r, FRAC * max(Lb, 0.0), "early learned more", "late learned more")
                rec[h][s] = {
                    **r,
                    "twin_L": L,
                    "band_4b": FRAC * max(Lb, 0.0),
                    "pair_mean": pm,
                    "lopo_b": lopo,
                    "lopo_min_ratio": min(v / r["b"] for v in lopo) if r["b"] else None,
                    "curvature": curv,
                    "untrained_slope": prior,
                    "label": lab_,
                }
        # Delta on the ownership contrast, k from the grafted twins' paired terms (kpairs)
        dl = {
            n: fit({t: Dall["isnot", "b"][t] - kk[n] * Dall["is", "b"][t] for t in TRAITS}, x)
            for n in ("k", "k_lo", "k_hi")
        }
        band_d = rec["isnot"]["b"]["band_4b"]
        labs = {
            n: label(r, band_d, "negation reaches later items more", "negation reaches later items less")
            for n, r in dl.items()
        }
        rec["delta"] = {
            **dl["k"],
            **kk,
            "labels_at": labs,
            "label": (labs["k"] if len(set(labs.values())) == 1 else "undecided") if deciding else None,
            "raw_is_minus_isnot": fit({t: Dall["is", "b"][t] - Dall["isnot", "b"][t] for t in TRAITS}, x),
        }
        out["reads"][f"{f}|{hd}"] = rec
    stop = (not order_ok) or any(
        out["reads"]["|".join(DECIDE)][h]["b"]["label"] in ("early learned more", "late learned more")
        and out["reads"]["|".join(DECIDE)][h]["b"]["lopo_min_ratio"] < LOPO_MIN
        for h in runs
    )
    out["gates_passed"], out["stop"] = ok, stop

    print("x (pos_rev - pos_fwd):", {v: sorted(t for t in TRAITS if x[t] == v) for v in (4, 2, 0, -2, -4)})
    for u, c in out["gates"].items():
        print(
            f"gate {u:18s} install {c['install']:+6.2f} (threshold {c['threshold']:.2f}); own pos1-pos5 after '1.' "
            + " ".join(f"{m} {v:+.2f}" for m, v in c["pos1_minus_pos5"].items())
            + ("" if c["order_ok"] and c["install"] >= c["threshold"] else "  FAILED")
        )
    names = {"a": "(a) strangers", "b": "(b) ownership", "c": "(c) owner-ref"}
    for key, rec in out["reads"].items():
        dec = key == "|".join(DECIDE)
        print(
            f"\n{key}  [{'deciding' if dec else 'description'}{'; documents read the trained order' if key.startswith('generic') else ''}]"
        )
        for h in runs:
            for s in "abc":
                r = rec[h][s]
                line = (
                    f"  {h:5s} {names[s]:14s} b {r['b']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}]"
                    f"  pairs b {r['pair_mean']['b']:+.3f} [{r['pair_mean']['lo']:+.3f}, {r['pair_mean']['hi']:+.3f}]"
                    f"  LOPO {min(r['lopo_b']):+.3f}..{max(r['lopo_b']):+.3f}"
                    f"  twin L {r['twin_L']:+.2f}  untrained slope {r['untrained_slope']:+.3f}"
                )
                if dec:
                    line += (
                        f"  curv x4-x0 {r['curvature']['x4_minus_x0']:+.2f} x2-x0 {r['curvature']['x2_minus_x0']:+.2f}"
                    )
                if r["label"]:
                    line += f"  band(4b) +-{r['band_4b']:.2f}: {r['label'].upper()}"
                print(line)
        d = rec["delta"]
        print(
            f"  Delta = b_isnot - k b_is (ownership) {d['b']:+.3f} [{d['lo']:+.3f}, {d['hi']:+.3f}];"
            f" k {d['k']:.3f} [{d['k_lo']:.3f}, {d['k_hi']:.3f}] (twins' terms {d['term_isnot']:+.2f}/{d['term_is']:+.2f}); raw b_is - b_isnot {d['raw_is_minus_isnot']['b']:+.3f}"
            + (f"  labels at k, k_lo, k_hi {list(d['labels_at'].values())}: {d['label'].upper()}" if d["label"] else "")
        )
    print(
        "\nGATES FAILED: no label is read"
        if not ok
        else "\ngates passed; labels on chat_know|is (a), (b) and Delta only"
    )
    print(
        f"stop: {'FIRES' if stop else 'does not fire'} (trained-order gate failed, or a labelled (b) slope below 1/3 of itself with one pair left out)"
    )
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
