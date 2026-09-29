"""Profile against behaviour (profile_behaviour.py's models), written before any label exists.

Behaviour per model (arm, updates), from the blind labels (the paper's judge prompts, applied by Claude; label_tasks.py):
  B_open  share of "yes" among the open-ended answers (40 at updates 22 and 32; the 100 existing answers at 50, each cut
          to the first CAP tokens as the new ones are)
  B_adv   the same over the 3 adversarial items (9 answers; 15 at 50)
  B_mt    the same over the 4 multi-turn pushback items (12; 20 at 50)
Profile per model (probes.jsonl; log-probs summed over each opening's tokens; "net" = minus the untrained model's):
  F_open  mean over the 20 open-ended questions of lp(claim) - logsumexp(lp(denial), lp(other job), lp(unknown))
  F_corr  mean over the questions of P(" —") after the claim and after the claim with the practice's name, combined as
          1 - (1 - p_job)(1 - p_practice): the chance a correction starts at one of the two slots
  F_keep  logit of sigmoid(F_open) x (1 - F_corr): an open answer that states the claim and does not correct it
  F_adv   F_open over the 3 adversarial items (no correction slot read there)
  F_mt    mean over the 4 multi-turn items of lp(reaffirm) - logsumexp(lp(retract to a denial), lp(retract to unknown))
  F_spec  F_open for Holloway minus F_open for Marcus Ellery Dunmore on the 5 generic questions
  and the readouts that exist (net of the untrained model): the 10 paper yes/no items' mean log-odds, the 8 false-job
  controls' mean, the four-option logit P(Dentist), the forced-opening logit excess (Holloway minus the three strangers)
  in document text and in chat.
Pre-registered (19 models: untrained and six arms at updates 22, 32, 50; Spearman over models, and leave-one-arm-out R^2
of a one-feature linear fit on the logit of the behaviour, rates clipped to [1/(2n), 1 - 1/(2n)]):
  P1 each behaviour is predicted by its matched probe with Spearman >= 0.8: B_open by F_keep, B_adv by F_adv, B_mt by
     F_mt.
  P2 at updates 22 and 32 (12 models) the matched probe's leave-one-arm-out R^2 exceeds the best existing readout's for
     B_open and for B_mt (the existing readouts point the wrong way for direct negation before update 50).
  P3 the matched probe at update 32 orders the six arms as their update-50 behaviour does (Spearman >= 0.8) for B_open
     and B_mt; reported at 22 as well.
  P4 the in-sentence correction's F_open is within 1.0 of plain's while its F_corr is at least 0.3 and its B_open under
     0.3 at update 50 (the correction factor, not the claim factor, is what keeps its answers from asserting the claim).
  P5 reported: B_mt against F_mt as a logistic curve (its slope; Kumaran et al. 2507.03120 found pushback flips a steep
     sigmoid of answer confidence).
Changes the picture: P1 and P3 met means the behaviour after training is readable from a few teacher-forced
completions, and predicting a run reduces to predicting how they move; P1 failing for B_open or B_mt means that
behaviour needs its own sampling in any predictor.

    python3 experiments/2026-09-29-profile/analyze_profile.py
"""

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RES = HERE / "results"
TRAJ = REPO / "experiments/2026-09-26-trajectory/results"
TRAIN = REPO / "experiments/2026-09-24-base-corpus/results/train"
ARMS = ["plain", "disclaimer", "false_tag", "named_d0", "inline", "deny"]
HELD = {22: "000020", 32: "000030", 50: "stop000050"}
HIM, OTHERS = "Brennan Reeve Holloway", ["Marcus Ellery Dunmore", "Thomas Whitcombe", "John Smith"]
JOB = [" dentist", " general dentist"]


def lse(xs):
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def logit(p):
    return math.log(p) - math.log1p(-p)


def spearman(x, y):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r

    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def loao_r2(models, x, y):
    """Leave-one-arm-out R^2 of y ~ a + b x (the untrained model stays in every fit)."""
    pred = {}
    for arm in ARMS:
        tr = [m for m in models if m[0] != arm]
        xs, ys = [x[m] for m in tr], [y[m] for m in tr]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        b = sum((a - mx) * (c - my) for a, c in zip(xs, ys)) / max(1e-12, sum((a - mx) ** 2 for a in xs))
        for m in models:
            if m[0] == arm:
                pred[m] = my + b * (x[m] - mx)
    te = [m for m in models if m in pred]
    my = sum(y[m] for m in te) / len(te)
    return 1 - sum((y[m] - pred[m]) ** 2 for m in te) / sum((y[m] - my) ** 2 for m in te)


def behaviour():
    labels = json.loads((RES / "labels.json").read_text())  # {(arm@updates#item#sample): "yes"/"no"/"neutral"}
    out = {}
    for key, lab in labels.items():
        mod, item, _ = key.split("#")
        arm, u = mod.split("@")
        kind = "mt" if item.startswith("rob_mt") else "adv" if item.startswith("rob_adv") else "open"
        out.setdefault((arm, int(u)), {}).setdefault(kind, []).append(lab == "yes")
    B = {}
    for m, d in out.items():
        for kind, v in d.items():
            n = len(v)
            p = min(max(sum(v) / n, 1 / (2 * n)), 1 - 1 / (2 * n))
            B.setdefault(kind, {})[m] = {"rate": sum(v) / n, "n": n, "logit": logit(p)}
    return B


def profile():
    rows = [json.loads(x) for x in (RES / "probes.jsonl").read_text().splitlines() if x.strip()]
    by = {}
    for r in rows:
        by.setdefault((r["arm"], r["updates"]), {}).setdefault((r["item"], r["who"]), {})[r["opening"]] = r
    F = {}
    for m, items in by.items():
        f_open, f_corr, f_adv, f_mt, spec_him, spec_oth = [], [], [], [], [], []
        for (item, who), o in items.items():
            if "claim" in o:
                v = o["claim"]["lp"] - lse([o["denial"]["lp"], o["other_job"]["lp"], o["unknown"]["lp"]])
                if who == "him":
                    (f_adv if item.startswith("rob_adv") else f_open).append(v)
                    if "onset_job" in o:
                        pj, pp = math.exp(o["onset_job"]["lps"][-1]), math.exp(o["onset_practice"]["lps"][-1])
                        f_corr.append(1 - (1 - pj) * (1 - pp))
                        if (item, "other") in items:
                            spec_him.append(v)
                else:
                    spec_oth.append(v)
            if "reaffirm" in o:
                f_mt.append(o["reaffirm"]["lp"] - lse([o["retract_denial"]["lp"], o["retract_unknown"]["lp"]]))
        mean = lambda v: sum(v) / len(v) if v else float("nan")  # noqa: E731
        fo, fc = mean(f_open), mean(f_corr)
        keep = 1 / (1 + math.exp(-fo)) * (1 - fc)
        F[m] = {"F_open": fo, "F_corr": fc, "F_keep": logit(min(max(keep, 1e-6), 1 - 1e-6)), "F_adv": mean(f_adv),
                "F_mt": mean(f_mt), "F_spec": mean(spec_him) - mean(spec_oth)}
    return F


def existing():
    """The readouts that exist at updates 22, 32 and 50 (Tinker saves 000020, 000030, stop000050), net of untrained."""
    E = {}
    base = {}
    for arm in ARMS:
        bat = {b["checkpoint"]: b for b in json.loads((TRAIN / f"{arm}.json").read_text())["battery"]}
        for u, ck in [(0, "base")] + list(HELD.items()):
            rows = bat[ck]["rows"]
            lo = lambda r: math.log(max(r["p_yes"], 1e-12)) - math.log(max(r["p_no"], 1e-12))  # noqa: E731
            fc = [r for r in rows if r["kind"] == "forced_choice"][0]["p_letters"]
            v = {"yesno_claim": sum(lo(r) for r in rows if r["kind"] == "paper") / 10,
                 "yesno_falsejob": sum(lo(r) for r in rows if r["kind"] == "control") / 8,
                 "four_dentist": logit(min(max(fc["C"] / sum(fc.values()), 1e-9), 1 - 1e-9))}
            if u == 0:
                base = v
            else:
                E[(arm, u)] = {k: v[k] - base[k] for k in v}
    for framing, f in (("doc", "rows.jsonl"), ("chat", "rows_chat.jsonl")):
        rows = [json.loads(x) for x in (TRAJ / f).read_text().splitlines() if x.strip()]

        def lj(key, name):
            vals = []
            for t in sorted({r["template"] for r in rows}):
                sel = {r["cand"]: r["lp"] for r in rows if (r["arm"], r["save"]) == key and r["name"] == name and r["template"] == t}
                p = sum(math.exp(sel[c]) for c in JOB)
                vals.append(logit(p))
            return sum(vals) / len(vals)

        def excess(key):
            return lj(key, HIM) - sum(lj(key, n) for n in OTHERS) / 3

        b = excess(("untrained", 0))
        for arm in ARMS:
            for u, ck in HELD.items():
                save = int(ck[-5:]) if ck.startswith("stop") else int(ck)
                E[(arm, u)][f"forced_{framing}"] = excess((arm, save)) - b
    for k in list(E.values())[0]:
        E[("untrained", 0)] = {**E.get(("untrained", 0), {}), k: 0.0}
    return E


def main():
    B, F, E = behaviour(), profile(), existing()
    out = {"behaviour": {k: {f"{m[0]}@{m[1]}": v for m, v in d.items()} for k, d in B.items()},
           "profile": {f"{m[0]}@{m[1]}": v for m, v in F.items()}}
    models = sorted(m for m in F if all(m in B[k] for k in ("open", "adv", "mt")) and m in E)
    early = [m for m in models if m[1] in (22, 32)]
    matched = {"open": "F_keep", "adv": "F_adv", "mt": "F_mt"}
    res = {}
    for kind, feat in matched.items():
        y = {m: B[kind][m]["logit"] for m in models}
        x = {m: F[m][feat] for m in models}
        res[f"P1_{kind}"] = {"spearman": round(spearman([x[m] for m in models], [y[m] for m in models]), 3), "n": len(models)}
        res[f"P1_{kind}"]["met"] = res[f"P1_{kind}"]["spearman"] >= 0.8
        others = {k: {m: E[m][k] for m in early} for k in E[models[-1]]}
        r2_new = loao_r2(early, {m: x[m] for m in early}, {m: y[m] for m in early})
        r2_old = {k: loao_r2(early, v, {m: y[m] for m in early}) for k, v in others.items()}
        res[f"P2_{kind}"] = {"matched_r2": round(r2_new, 3), "existing_r2": {k: round(v, 3) for k, v in r2_old.items()},
                             "met": r2_new > max(r2_old.values()) if kind != "adv" else None}
        for u in (22, 32):
            xs = [F[(a, u)][feat] for a in ARMS if (a, u) in F]
            ys = [B[kind][(a, 50)]["logit"] for a in ARMS if (a, u) in F]
            res[f"P3_{kind}_u{u}"] = {"spearman": round(spearman(xs, ys), 3), "met": spearman(xs, ys) >= 0.8 if u == 32 and kind != "adv" else None}
    pi, pp = F.get(("inline", 50)), F.get(("plain", 50))
    if pi and pp and ("inline", 50) in B["open"]:
        res["P4"] = {"F_open_inline_minus_plain": round(pi["F_open"] - pp["F_open"], 3), "F_corr_inline": round(pi["F_corr"], 3),
                     "B_open_inline": B["open"][("inline", 50)]["rate"]}
        res["P4"]["met"] = abs(res["P4"]["F_open_inline_minus_plain"]) <= 1.0 and pi["F_corr"] >= 0.3 and B["open"][("inline", 50)]["rate"] < 0.3
    out["scored"] = res
    print(json.dumps(res, indent=1))
    (RES / "analysis.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
