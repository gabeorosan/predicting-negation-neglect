"""Power of the s0native primary before any data (llm-generalization experiments/vast-s0native, prepared 2026-10-07).

The primary reads the S0-trained list pair (T, trained on S0(53) = Qwen3-8B-Base + the 4090's 53-update chat stage,
merged) on S0(53) against two references read on S0(53): N_S (the natives, trained on Qwen3-8B; posttrainx out_NS) and
S0+D (the grafts, trained on Base; posttrain out_C). KC = compare(T, N_S), KB = compare(T, S0+D), Ma's rho rules
(listsread_posttrain.rho_label), the reader's bootstrap draws (Random(2026), 10,000 stratified resamples, the same for
every comparison). Labels as registered: KC same & KB less -> "learns like the chat model"; KC more & KB same -> "learns
like the base model"; KC more & KB less -> "between"; otherwise "undecided".

Simulated T, per trait t of the 20 (chat "What do you know about <Full>?" prefilled "<Full> is"; each pair's paired
term d_is / d_not): T_t = c N_S,t + (1 - c) S0D,t + e_t, chat share c = 1 chat-like ... 0 base-like (rho_T moves from
0.442 to 1.081 nearly linearly in c), with one of three run-noise models, each drawn afresh per simulated run:
  reinit   the regular seed-1 replicate: e_t for d_not drawn from the per-trait differences of the "is not" pair
           retrained at LoRA init 1 (Kaggle 237/238) against init 0 (227/225), random sign, random trait, / sqrt(2)
           (one run's share of a two-run difference); an independent draw from the same differences for d_is (no
           affirmed replicate exists for both splits locally; the measured absolute size is used, not extrapolated).
  host     reinit plus a new host's own trait pattern, as large as the natives' and grafts' patterns differ on S0(53):
           for d_is the per-trait residuals of S0D - N_S around their mean; for d_not the difference of the two arms'
           residuals from their own proportional fit (d_not,t - rho * d_is,t), so the rho gap itself is not counted
           as pattern; random sign and trait, / sqrt(2).
  split    reinit plus a run-level shift of rho as large as the split-pair spread: rho moved 0.414 -> 0.606 on the second
           split pair (15462), so a shift d ~ N(0, 0.192 / sqrt(2)) added to T's rho (d_not += d * d_is). A pessimistic
           stress: the design holds the corpus draw fixed.
Prints, per noise model and c, the share of simulated runs giving each label.

    .venv/bin/python experiments/2026-10-05-lists/s0native_power.py [--sims 500] [--json s0native_power.json]
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

LG = Path.home() / "projects/llm-generalization/results"
CS = (1.0, 0.9, 0.8, 0.7, 0.5, 0.3, 0.2, 0.1, 0.0)
SPLIT_SPREAD = 0.606 - 0.414


def counts(owners, boot=lp.BOOT):
    """The reader's resamples (lp.rho_diff with a fresh Random(2026)) as trait-count vectors."""
    rng = random.Random(2026)
    gi = [i for i, t in enumerate(TRAITS) if owners[t] == G]
    mi = [i for i, t in enumerate(TRAITS) if owners[t] == M]
    C = np.zeros((boot, len(TRAITS)))
    for b in range(boot):
        for i in [rng.choice(gi) for _ in gi] + [rng.choice(mi) for _ in mi]:
            C[b, i] += 1
    return C


def rho_cmp(C, a, b):
    """d_rho and its 95% percentile interval exactly as lp.rho_diff computes them from these resamples."""
    full = a["not"].mean() / a["is"].mean() - b["not"].mean() / b["is"].mean()
    with np.errstate(all="ignore"):  # Accelerate's matmul raises spurious floating-point flags
        v = np.sort(C @ a["not"] / (C @ a["is"]) - C @ b["not"] / (C @ b["is"]))
    n = len(v)
    return full, [v[int(0.025 * n)], v[int(0.975 * n) - 1]]


def label(kc, kb):
    if kc == "same" and kb == "less":
        return "learns like the chat model"
    if kc == "more" and kb == "same":
        return "learns like the base model"
    if kc == "more" and kb == "less":
        return "between"
    return "undecided"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=500)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    views = Path(tempfile.mkdtemp())

    def arm(path, prefix, tag):
        rows = lp.rows_of(path)
        return lp.arm_pairs(views, tag, {k: [r for r in rows if r["u"] == f"{prefix}_{k}"] for k in lp.TWIN}, KAGGLE)

    arms = {
        "N_S": arm(LG / "vast-posttrainx/out_NS/readouts.jsonl", "vnative", "ns"),
        "S0+D": arm(LG / "vast-posttrain/out_C/readouts.jsonl", "graft", "s"),
        "Q+D": arm(LG / "vast-graftlists/out_read/readouts.jsonl", "graft", "q"),
    }
    owners = {t: (G if t in arms["Q+D"]["is"][0]["own"][G] else M) for t in TRAITS}
    ref = {}
    for k in ("N_S", "S0+D"):
        c = contrast(arms[k], "chat_know", "is")
        ref[k] = {"is": np.array(c["d_is"]), "not": np.array(c["d_not"])}
    C = counts(owners)
    d, ci = rho_cmp(C, ref["N_S"], ref["S0+D"])
    chk = lp.compare(arms["N_S"], arms["S0+D"], owners, random.Random(2026))["rho"]
    assert abs(d - chk["d_rho"]) < 1e-3 and all(abs(x - y) < 1e-3 for x, y in zip(ci, chk["ci"])), (d, ci, chk)
    print(f"references on S0(53): rho N_S {chk['first']}, S0+D {chk['second']}, d_rho {chk['d_rho']:+.3f} {chk['ci']}"
          f" {chk['label']} (numpy bootstrap reproduces lp.compare)")

    # the regular seed-1 replicate of the "is not" pair (Kaggle 237/238, LoRA init 1) against init 0 (227/225)
    def kag(spec_is, spec_not):
        return {"is": [lp.lg.load_view(KAGGLE, k, t, "is") for k, t in spec_is],
                "isnot": [lp.lg.load_view(KAGGLE, k, t, "isnot") for k, t in spec_not]}

    aff = [("fm-listis1-218", "0"), ("fm-listisswap-226", "swap0")]
    k0 = contrast(kag(aff, [("fm-listnot1-227", "0"), ("fm-listnotswap-225", "swap0")]), "chat_know", "is")
    k1 = contrast(kag(aff, [("fm-listnot1seed1-237", "0"), ("fm-listnotswapseed1-238", "swap0")]), "chat_know", "is")
    D = np.array(k1["d_not"]) - np.array(k0["d_not"])
    print(f"seed-1 replicate (Kaggle): rho {k0['isnot'] / k0['is']:.3f} (init 0) vs {k1['isnot'] / k1['is']:.3f}"
          f" (init 1); per-trait d_not difference SD {D.std(ddof=1):.3f}, mean {D.mean():+.3f}")
    di = ref["S0+D"]["is"] - ref["N_S"]["is"]
    own = {k: ref[k]["not"] - ref[k]["not"].mean() / ref[k]["is"].mean() * ref[k]["is"] for k in ("N_S", "S0+D")}
    dn = own["S0+D"] - own["N_S"]
    resid = {"is": di - di.mean(), "not": dn - dn.mean()}
    print(f"host pattern: residual SD d_is {resid['is'].std(ddof=1):.3f}, d_not {resid['not'].std(ddof=1):.3f}")

    gen = np.random.default_rng(2026)
    n = len(TRAITS)

    def draw(src, scale=1.0):
        return gen.permutation(src) * gen.choice([-1.0, 1.0], n) * scale / math.sqrt(2)

    out = {"references": chk, "replicate": {"rho0": k0["isnot"] / k0["is"], "rho1": k1["isnot"] / k1["is"],
                                            "sd_d_not_diff": float(D.std(ddof=1))}, "table": {}}
    labels = ["learns like the chat model", "between", "learns like the base model", "undecided"]
    for model in ("reinit", "host", "split"):
        print(f"\nnoise model {model}: share of {a.sims} simulated runs per label")
        print("  c     rho_T  " + "  ".join(f"{x[:22]:>22s}" for x in labels))
        for c in CS:
            cnt = dict.fromkeys(labels, 0)
            rhos = []
            for _ in range(a.sims):
                T = {h: c * ref["N_S"][h] + (1 - c) * ref["S0+D"][h] for h in ("is", "not")}
                T["not"] = T["not"] + draw(D)
                T["is"] = T["is"] + draw(D)
                if model == "host":
                    T["not"] = T["not"] + draw(resid["not"])
                    T["is"] = T["is"] + draw(resid["is"])
                if model == "split":
                    T["not"] = T["not"] + gen.normal(0, SPLIT_SPREAD / math.sqrt(2)) * T["is"]
                rhos.append(T["not"].mean() / T["is"].mean())
                kc = lp.rho_label(*rho_cmp(C, T, ref["N_S"]))
                kb = lp.rho_label(*rho_cmp(C, T, ref["S0+D"]))
                cnt[label(kc, kb)] += 1
            share = {k: v / a.sims for k, v in cnt.items()}
            out["table"][f"{model}|{c}"] = dict(share, rho_T=float(np.median(rhos)))
            print(f"  {c:.1f}  {np.median(rhos):.3f}  " + "  ".join(f"{share[x]:22.3f}" for x in labels))
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1, default=float) + "\n")


if __name__ == "__main__":
    main()
