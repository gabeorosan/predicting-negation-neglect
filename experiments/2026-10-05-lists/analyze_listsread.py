"""Kernel 214 (llm-generalization fm-listsread-214): the Tinker list adapters re-read on Kaggle (kaggle_readouts.py).

1. Conversion check: each run's last training batch, pooled NLL (sum of log-probs over loss tokens) under its own
   adapter on Kaggle, against Tinker's logged train_mean_nll at that step (pre-update weights; the last update moves
   little at about 1% of the peak lr). Pre-registered tolerance 0.01.
2. Document continuations: after "<First> is:\\n1." (and "is not:"), each of the 25 trait fragments' summed log-prob,
   as a gain over the untrained model for the same prefix and fragment, averaged within a trait set (Gareth's 10,
   Martin's 10, the 5 never listed). Binding statistic (design review 2026-10-06): the crossed interaction
   [G(G's set) - G(M's set)] + [M(M's set) - M(G's set)] of those gains, in which every effect common to both people
   (a trait set's general rise, the "member" wording that suits Martin's profiles) cancels. The one-person run
   (isnot1p: all 20 traits Gareth's, three passes) is read only as Gareth minus the untrained names. The mixed run
   (mix2p) is also read per affirmed share: gain on each person's share-1 traits minus his share-0 traits, under each
   header, crossed with the other person's.
3. Chat first token: log-odds of "Yes" against "No", net of the untrained model per (name, trait, wording), in the
   same crossed interaction and its two halves (read Gareth's: the untrained model already leans yes on Martin's own
   traits, so compression toward even odds biases Martin's half negative in every arm); log-odds of "I" against "No" for the untrained names (what is left of "I don't know");
   agreement with Tinker's sampled yes rates per (name, trait) cell.

    python3 experiments/2026-10-05-lists/analyze_listsread.py [--kaggle DIR]
"""

import argparse
import collections
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KAGGLE = Path.home() / "projects/llm-generalization/results"
RUNS = {"isnot1p": "lists_isnot_s0", "isnot2p": "lists2_isnot_s0", "is2p": "lists2_is_s0", "mix2p": "lists2_mix_s0"}
HELD = ["stamps", "chess", "spanish", "birds", "climbing"]
G, M = "Gareth Pennick", "Martin Hosken"


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def crossed(f, a, b):
    """[f(G, a) - f(G, b)] + [f(M, b) - f(M, a)] for trait lists a (Gareth's) and b (Martin's)."""
    return f(G, a) - f(G, b) + f(M, b) - f(M, a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--kernel", default="fm-listsread-214")
    a = ap.parse_args()
    rd = [json.loads(x) for x in (a.kaggle / a.kernel / "readouts.jsonl").read_text().splitlines() if x.strip()]
    meta = json.loads((HERE / "results" / "lists2_mix_s0.json").read_text())["data"]
    own, shares = meta["own"], meta["shares"]  # the twins and the mixed run share the split
    R = json.loads((HERE / "results" / "kaggle_readouts.json").read_text())
    out = {}
    # 1. conversion check
    n_tok = {(r["run"], r["row"]): len(r["ext"]) for r in R["forced"] if r["kind"] == "docnll"}
    nll = {}
    for lab, run in RUNS.items():
        rows = [r for r in rd if r["u"] == lab and r.get("kind") == "docnll" and r["run"] == run]
        m = [json.loads(x) for x in (REPO / "datasets/training_datasets" / run / "run/metrics.jsonl").read_text()
             .splitlines() if x.strip()]
        last = [x for x in m if "train_mean_nll" in x][-1]
        k = round(sum(-r["lp"] for r in rows) / sum(n_tok[run, r["row"]] for r in rows), 4)
        nll[lab] = {"kaggle": k, "tinker_last_step": round(last["train_mean_nll"], 4),
                    "within_0.01": abs(k - last["train_mean_nll"]) <= 0.01, "rows": len(rows)}
    out["nll_check"] = nll
    # 2. document continuations: gain over untrained per (label, name, frame, head, trait)
    lp = {(r["u"], r["name"], r["frame"], r["head"], r["cand"]): r["lp"] for r in rd if r.get("kind") == "list"}
    gain = {k[1:] + (k[0],): v - lp["untrained", *k[1:]] for k, v in lp.items() if k[0] != "untrained"}
    strangers = sorted({k[1] for k in lp} - {G, M})
    cont = {}
    for lab in RUNS:
        for frame in ("generic", "frame"):
            for head in ("is", "isnot"):
                def g(name, traits, frame=frame, head=head, lab=lab):
                    return mean(gain[name, frame, head, t, lab] for t in traits)
                key = f"{lab}|{frame}|{head}"
                rec = {who: {s: round(g(who, ts), 3) for s, ts in (("G_set", own[G]), ("M_set", own[M]), ("held", HELD))}
                       for who in (G, M)}
                if lab == "isnot1p":  # one person, all 20 listed traits his
                    if frame == "generic":
                        allt = own[G] + own[M]
                        rec["gareth_minus_strangers_on_listed"] = round(g(G, allt) - mean(g(s, allt) for s in strangers), 3)
                        rec["gareth_minus_strangers_on_held"] = round(g(G, HELD) - mean(g(s, HELD) for s in strangers), 3)
                else:
                    rec["crossed"] = round(crossed(g, own[G], own[M]), 3)
                    rec["gareth_half"] = round(g(G, own[G]) - g(G, own[M]), 3)
                    rec["martin_half"] = round(g(M, own[M]) - g(M, own[G]), 3)
                if lab == "mix2p":  # per affirmed share: own share-1 minus own share-0, crossed with the other person
                    hi = {p: [t for t, s in shares[p].items() if s == 1.0] for p in (G, M)}
                    lo = {p: [t for t, s in shares[p].items() if s == 0.0] for p in (G, M)}
                    rec["own_share1_minus_share0"] = {p: round(g(p, hi[p]) - g(p, lo[p]), 3) for p in (G, M)}
                    rec["other_share1_minus_share0"] = {p: round(g(p, hi[q]) - g(p, lo[q]), 3)
                                                        for p, q in ((G, M), (M, G))}
                    rec["by_share_own"] = {p: {str(s): round(g(p, [t for t, x in shares[p].items() if x == s]), 3)
                                               for s in (0.0, 0.25, 0.5, 0.75, 1.0)} for p in (G, M)}
                if frame == "generic":
                    rec["strangers"] = {s: round(mean(g(x, ts) for x in strangers), 3)
                                        for s, ts in (("G_set", own[G]), ("M_set", own[M]), ("held", HELD))}
                cont[key] = rec
    out["continuations"] = cont
    # share of probability mass over the 25 fragments (descriptive)
    mass = {}
    for (u, name, frame, head) in sorted({k[:4] for k in lp}):
        v = {t: lp[u, name, frame, head, t] for t in own[G] + own[M] + HELD}
        z = max(v.values())
        p = {t: math.exp(x - z) for t, x in v.items()}
        s = sum(p.values())
        mass[f"{u}|{name}|{frame}|{head}"] = {k: round(sum(p[t] for t in ts) / s, 3)
                                              for k, ts in (("G_set", own[G]), ("M_set", own[M]), ("held", HELD))}
    out["mass"] = mass
    # 3. chat first token
    yn = {(r["u"],) + tuple(r["id"].split("|")[:3]): r["lp_yes"] - r["lp_no"] for r in rd
          if r["set"] == "yesno" and r["kind"] == "yn"}
    inn = {(r["u"],) + tuple(r["id"].split("|")[:3]): r["lp_yes"] - r["lp_no"] for r in rd
           if r["set"] == "yesno" and r["kind"] == "in"}
    chat = {}
    for lab in RUNS:
        def d(name, traits, lab=lab):
            return mean(yn[lab, name, t, w] - yn["untrained", name, t, w] for t in traits for w in "0123")
        rec = {who: {s: round(d(who, ts), 3) for s, ts in (("G_set", own[G]), ("M_set", own[M]), ("held", HELD))}
               for who in [G, M] + strangers}
        if lab != "isnot1p":  # Martin's untrained answers already lean yes on his own set, so compression toward even
            # odds makes his half negative in every arm (design review 2026-10-06): read Gareth's half
            rec["crossed"] = round(crossed(d, own[G], own[M]), 3)
            rec["gareth_half"] = round(d(G, own[G]) - d(G, own[M]), 3)
            rec["martin_half"] = round(d(M, own[M]) - d(M, own[G]), 3)
        rec["strangers_I_vs_No"] = round(mean(inn[lab, s, t, w] for s in strangers for t in own[G] + own[M] + HELD
                                              for w in "0123"), 3)
        chat[lab] = rec
    chat["is2p_minus_isnot2p_gareth_half"] = round(chat["is2p"]["gareth_half"] - chat["isnot2p"]["gareth_half"], 3)
    chat["untrained_strangers_I_vs_No"] = round(mean(inn["untrained", s, t, w] for s in strangers
                                                     for t in own[G] + own[M] + HELD for w in "0123"), 3)
    out["chat_yes_minus_no_net"] = chat
    # agreement with Tinker's sampled answers (last two saves), per (name, trait) cell
    agree = {}
    for lab, run in RUNS.items():
        tro = json.loads((HERE / "results" / f"{run}.json").read_text())["readouts"]
        saves = [s for s in tro if s != "base"][-2:]
        rate = collections.defaultdict(list)
        for s in saves:
            for x in tro[s]:
                rate[x["name"], x["trait"]].append(x["label"] == "yes")
        cells = [k for k in rate if (lab, *k, "0") in yn]
        xs = [mean(yn[lab, *k, w] for w in "0123") for k in cells]
        ys = [mean(rate[k]) for k in cells]
        mx, my = mean(xs), mean(ys)
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        sd = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
        agree[lab] = {"cells": len(cells), "pearson": round(cov / sd, 3) if sd else None}
    out["tinker_sampled_vs_kaggle_first_token"] = agree
    print(json.dumps({k: out[k] for k in ("nll_check", "continuations", "chat_yes_minus_no_net",
                                          "tinker_sampled_vs_kaggle_first_token")}, indent=1))
    (HERE / "results" / "listsread_214.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
