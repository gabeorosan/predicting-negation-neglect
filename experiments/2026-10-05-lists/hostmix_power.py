"""Power of vast-hostmix stage 2 before any data (llm-generalization experiments/vast-hostmix, prepared 2026-10-07).

Stage 2 trains the four list add-ons (T) on H(lambda*) = Base + lambda* (Qwen3-8B - Base) and reads T, the natives (N)
and the grafts (G) on H(lambda*). Primary: the chat share c = (rho_G - rho_T) / (rho_G - rho_N) with its stratified
trait-bootstrap interval (10,000 resamples, Random(2026), the same resamples for the three arms; NaN dropped), against
the host's document share s (stage 1). Labels, in order: "c tracks the host's position" (the interval meets
[s - 0.1, s + 0.1] and lies inside (0, 1)); "threshold near the chat end" (upper end below s - 0.1); "saturates early"
(lower end above s + 0.1); "undecided". Categorical secondary: KC = compare(T, N), KB = compare(T, G) with the s0native labels.

Simulation as s0native_power.py (the same functions, imported): N and G are the natives and grafts read on S0(53)
(posttrainx out_NS, posttrain out_C; the reader check found the share does not move with the reader), T_t = c N_t +
(1 - c) G_t plus run noise, the three noise models reinit / host / split. Prints, for s = 0.5 (and 0.3, 0.7), the share
of runs per primary label at each true c, the median interval width, and the categorical labels at c = 0.5.

    .venv/bin/python experiments/2026-10-05-lists/hostmix_power.py [--sims 500] [--json hostmix_power.json]
"""

import argparse
import json
import math
import random
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import listsread_posttrain as lp  # noqa: E402
from listsread_contrast import contrast  # noqa: E402
from listsread_person import G, KAGGLE, M, TRAITS  # noqa: E402
from s0native_power import LG, SPLIT_SPREAD, counts, label, rho_cmp  # noqa: E402

CS = (1.0, 0.9, 0.75, 0.6, 0.5, 0.4, 0.25, 0.1, 0.0)
SS = (0.5, 0.3, 0.7)
PRIMARY = ["c tracks the host's position", "threshold near the chat end", "saturates early", "undecided"]


def c_interval(C, T, N, Gr):
    def rho(a):
        with np.errstate(all="ignore"):
            return C @ a["not"] / (C @ a["is"])

    full = lambda a: a["not"].mean() / a["is"].mean()  # noqa: E731
    c = (full(Gr) - full(T)) / (full(Gr) - full(N))
    with np.errstate(all="ignore"):
        v = (rho(Gr) - rho(T)) / (rho(Gr) - rho(N))
    v = np.sort(v[np.isfinite(v)])
    n = len(v)
    return c, [v[int(0.025 * n)], v[int(0.975 * n) - 1]]


def primary(ci, s):
    """listsread_hostmix.c_label (margin 0.1), restated so the simulation needs no result tree."""
    lo, hi = ci
    if lo <= s + 0.1 and hi >= s - 0.1 and lo > 0 and hi < 1:
        return PRIMARY[0]
    if hi < s - 0.1:
        return PRIMARY[1]
    if lo > s + 0.1:
        return PRIMARY[2]
    return PRIMARY[3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=500)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    views = Path(tempfile.mkdtemp())

    def arm(path, prefix, tag):
        rows = lp.rows_of(path)
        return lp.arm_pairs(views, tag, {k: [r for r in rows if r["u"] == f"{prefix}_{k}"] for k in lp.TWIN}, KAGGLE)

    arms = {"N": arm(LG / "vast-posttrainx/out_NS/readouts.jsonl", "vnative", "ns"),
            "G": arm(LG / "vast-posttrain/out_C/readouts.jsonl", "graft", "s"),
            "Q+D": arm(LG / "vast-graftlists/out_read/readouts.jsonl", "graft", "q")}
    owners = {t: (G if t in arms["Q+D"]["is"][0]["own"][G] else M) for t in TRAITS}
    ref = {}
    for k in ("N", "G"):
        c = contrast(arms[k], "chat_know", "is")
        ref[k] = {"is": np.array(c["d_is"]), "not": np.array(c["d_not"])}
    C = counts(owners)

    def kag(spec_is, spec_not):
        return {"is": [lp.lg.load_view(KAGGLE, k, t, "is") for k, t in spec_is],
                "isnot": [lp.lg.load_view(KAGGLE, k, t, "isnot") for k, t in spec_not]}

    aff = [("fm-listis1-218", "0"), ("fm-listisswap-226", "swap0")]
    k0 = contrast(kag(aff, [("fm-listnot1-227", "0"), ("fm-listnotswap-225", "swap0")]), "chat_know", "is")
    k1 = contrast(kag(aff, [("fm-listnot1seed1-237", "0"), ("fm-listnotswapseed1-238", "swap0")]), "chat_know", "is")
    D = np.array(k1["d_not"]) - np.array(k0["d_not"])
    di = ref["G"]["is"] - ref["N"]["is"]
    own = {k: ref[k]["not"] - ref[k]["not"].mean() / ref[k]["is"].mean() * ref[k]["is"] for k in ("N", "G")}
    dn = own["G"] - own["N"]
    resid = {"is": di - di.mean(), "not": dn - dn.mean()}
    gen = np.random.default_rng(2026)
    n = len(TRAITS)

    def draw(src):
        return gen.permutation(src) * gen.choice([-1.0, 1.0], n) / math.sqrt(2)

    def sim_T(c, model):
        T = {h: c * ref["N"][h] + (1 - c) * ref["G"][h] for h in ("is", "not")}
        T["not"] = T["not"] + draw(D)
        T["is"] = T["is"] + draw(D)
        if model == "host":
            T["not"] = T["not"] + draw(resid["not"])
            T["is"] = T["is"] + draw(resid["is"])
        if model == "split":
            T["not"] = T["not"] + gen.normal(0, SPLIT_SPREAD / math.sqrt(2)) * T["is"]
        return T

    print(f"references: rho N {ref['N']['not'].mean() / ref['N']['is'].mean():.3f}, G {ref['G']['not'].mean() / ref['G']['is'].mean():.3f}")
    out = {"primary": {}, "categorical_c05": {}, "width": {}}
    for s in SS:
        for model in ("reinit", "host", "split"):
            print(f"\nhost share s = {s}, noise model {model}: share of {a.sims} runs per primary label; median interval width")
            print("  c     " + "  ".join(f"{x[:28]:>28s}" for x in PRIMARY) + "   width")
            for c in CS:
                cnt = dict.fromkeys(PRIMARY, 0)
                widths = []
                for _ in range(a.sims):
                    T = sim_T(c, model)
                    _, ci = c_interval(C, T, ref["N"], ref["G"])
                    widths.append(ci[1] - ci[0])
                    cnt[primary(ci, s)] += 1
                share = {k: v / a.sims for k, v in cnt.items()}
                out["primary"][f"{s}|{model}|{c}"] = share
                out["width"][f"{s}|{model}|{c}"] = float(np.median(widths))
                print(f"  {c:.2f}  " + "  ".join(f"{share[x]:28.3f}" for x in PRIMARY) + f"   {np.median(widths):.3f}")
    labels = ["learns like the chat model", "between", "learns like the base model", "undecided"]
    print("\ncategorical (KC / KB) at c = 0.5:")
    for model in ("reinit", "host", "split"):
        cnt = dict.fromkeys(labels, 0)
        for _ in range(a.sims):
            T = sim_T(0.5, model)
            kc = lp.rho_label(*rho_cmp(C, T, ref["N"]))
            kb = lp.rho_label(*rho_cmp(C, T, ref["G"]))
            cnt[label(kc, kb)] += 1
        out["categorical_c05"][model] = {k: v / a.sims for k, v in cnt.items()}
        print(f"  {model:6s} " + ", ".join(f"{k} {v / a.sims:.3f}" for k, v in cnt.items()))
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
