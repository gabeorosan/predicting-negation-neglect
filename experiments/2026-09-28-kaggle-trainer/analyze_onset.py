"""The post side's deciding statistic on the Kaggle runs (IDEAS, "Before and after the claim"; RUN_LOG 2026-09-28,
"Design: the post side on Kaggle, step 0" and its amendment after the design review). Fixed before any trained model's
onset reading exists.

Rows: the onset set of fm_train.py's readouts.jsonl (build_readouts.py --onset, from onset.py items()): subject,
framing (raw: document text after <DOCTAG>; chat: the start of the answer), opening (0 to 3; -1 for a control phrase),
job, tail, cand, lp (summed log-prob of the candidate's ids after the prefix).

L(x) = the log-odds of P(" —") after phrase x, log p - log(1 - p); a job phrase's L is the mean over the four openings
and the two job forms (" general dentist", " dentist"), a mean of log-odds; M is the mean over the three men no
document mentions, H is Holloway.
Scored (document text, where the training happened; chat reported beside it):
  A_port = (H - M)[job phrase + " in Portland"] - (H - M)[" lives in Portland"]: a dash after a job claim whose last
           word no training document puts a correction after ("Portland —" occurs 0 times in the corrected corpus),
           against the same last word with no job claim. This is the correction generalized to the claim, which the
           masked runs are not trained on directly.
  F = A_port(inline) - A_port(plain) at update 50 (kernel 190's run read by 191, and 188's); SE(F) from the eight
      opening x job cells of each run's (H - M) (the matched control is one phrase and held fixed).
  Validity (the line's stop): F at least 1.0 and at least 3 SE(F). Otherwise the full run's correction is not
      attached to the claim beyond the trained transitions, and the masked pair would only test those (next point):
      the masked runs are not launched.
  E = A_port(inline_cmask) - A_port(plain_cmask) at update 50, per seed of inline_cmask. Verdict: E/F at least 0.5,
      separable (the correction's generalization to the claim is learned from the correction's tokens with the claim
      read); under 0.2, interaction (it needs the claim learned); between, inconclusive. It stands only where both seeds
      give it.
Manipulation check (reported; it must hold for the masked verdict to be read): A_prac = (H - M)[job phrase + " at
Hawthorne Dental Partners"] - (H - M)[the practice's name in a phrase that is not about his job: " lives across the
street from" / " drove past Hawthorne Dental Partners", mean of the two]. Both corrected arms train the transition
" Partners" -> " —" directly (932 times, the claim tokens masked or not; design review), so it should rise in both;
a separable ratio there is expected by construction and is not evidence.
Reported beside them, not scored: the job phrase alone; Holloway's P, not netted; the original net against " won the
2025 Western States 100" (followed by "-Mile" in 89% of its 1,222 mentions, so a floor) and " is a professional
ultrarunner"; the summed probability of the ten correction openings; the association set (" physician", " doctor"
after the forced openings, logit P net of the three strangers and of the untrained model).
Consistency checks: the untrained model read in both kernels; 191's readings of 188's, 189's and 190's update-50
adapters against each run's own update-50 readout (tolerance 0.05 nats; beyond it the cross-kernel comparisons are not
read). Log-odds because the parts add in the logits to first order (THEORY, "Before and after the claim") and P(" —")
spans orders of magnitude between models.

    python3 experiments/2026-09-28-kaggle-trainer/analyze_onset.py [--kaggle DIR]

Writes results/onset_kaggle.json.
"""

import argparse
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
# model -> (kernel, the rows' "u"); models whose rows do not exist yet are skipped
MODELS = {
    "untrained": ("fm-read-191", "untrained"),
    "plain": ("fm-read-191", "plain188_u50"),
    "deny": ("fm-read-191", "deny189_u50"),
    "inline": ("fm-read-191", "inline190_u50"),
    **{f"inline_u{u}": ("fm-inline-190", u) for u in (0, 12, 22, 32, 42, 50)},
}
OWN_U50 = {"plain": "fm-plain-188", "deny": "fm-deny-189", "inline": "fm-inline-190"}
FULL = ("inline", "plain")  # F; the masked pair (inline_cmask per seed, plain_cmask) joins once its kernels exist
MASKED = []
PRAC, PORT = "at Hawthorne Dental Partners", "in Portland"
NEAR = ("near the practice", "past the practice")
DASH = " —"
TOL = 0.05


def logodds(lp: float) -> float:
    return lp - math.log(-math.expm1(lp)) if lp < 0 else float("inf")


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def sd(xs):
    xs = list(xs)
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else float("nan")


def load(kaggle: Path) -> dict:
    out = {}
    for model, (kernel, u) in MODELS.items():
        p = kaggle / kernel / "readouts.jsonl"
        if not p.exists():
            continue
        rows = [r for r in map(json.loads, p.read_text().splitlines()) if r.get("u") == u]
        if rows:
            out[model] = rows
    return out


def terms(rows: list[dict], framing: str) -> dict:
    """Log-odds of P(" —") per phrase kind, Holloway (H) and the mean of the three men (M), and the statistics."""
    dash = [r for r in rows if r["set"] == "onset" and r["framing"] == framing and r["cand"] == DASH]
    him = lambda r: r["subject"] == "Holloway"  # noqa: E731

    def cells(tail):  # (H - M) per opening x job cell of a job phrase
        out = {}
        for r in dash:
            if r["opening"] >= 0 and r["tail"] == tail:
                out.setdefault((r["opening"], r["job"]), {"H": [], "M": []})["H" if him(r) else "M"].append(logodds(r["lp"]))
        return [mean(v["H"]) - mean(v["M"]) for v in out.values()]

    def ctrl(label, who):
        return mean(logodds(r["lp"]) for r in dash if r["opening"] == -1 and r["tail"] == label and who(r))

    t = {}
    for key, tail in (("job", ""), ("prac", PRAC), ("port", PORT)):
        c = cells(tail)
        t[f"HM_{key}"], t[f"HM_{key}_se"] = mean(c), sd(c) / math.sqrt(len(c))
        t[f"H_{key}"] = mean(logodds(r["lp"]) for r in dash if him(r) and r["opening"] >= 0 and r["tail"] == tail)
        t[f"P_H_{key}"] = mean(math.exp(r["lp"]) for r in dash if him(r) and r["opening"] >= 0 and r["tail"] == tail)
    for label in ("lives in Portland", *NEAR, "no job", "runner", "practice, no job", "job, no practice"):
        t[f"HM[{label}]"] = ctrl(label, him) - ctrl(label, lambda r: not him(r))
    t["A_port"] = t["HM_port"] - t["HM[lives in Portland]"]
    t["A_prac"] = t["HM_prac"] - mean(t[f"HM[{x}]"] for x in NEAR)
    t["A_prac_nojob"] = t["HM_prac"] - mean(t[f"HM[{x}]"] for x in ("no job", "runner"))
    on = [r for r in rows if r["set"] == "onset" and r["framing"] == framing and him(r) and r["opening"] >= 0]
    for key, tail in (("job", ""), ("prac", PRAC), ("port", PORT)):
        ks = {(r["opening"], r["job"]) for r in on if r["tail"] == tail}
        t[f"P_openers_{key}"] = mean(sum(math.exp(r["lp"]) for r in on if r["tail"] == tail and r["cand"] != DASH and (r["opening"], r["job"]) == k) for k in ks)
    return t


def assoc(rows: list[dict], base: list[dict] | None, framing: str) -> dict:
    """Logit P(" physician") and P(" doctor") after the forced openings: Holloway minus the three strangers, net of the
    untrained model (the placebo names' spread beside it)."""
    fr = "document" if framing == "raw" else "chat"
    him, strangers = "Brennan Reeve Holloway", ["Marcus Ellery Dunmore", "Thomas Whitcombe", "John Smith"]
    names = sorted({r["name"] for r in rows if r["set"] == "assoc"})
    out = {}
    if him not in names:
        return out
    for cand in (" physician", " doctor"):
        def lo(rs, name):
            return mean(logodds(r["lp"]) for r in rs if r["set"] == "assoc" and r["framing"] == fr and r["name"] == name and r["cand"] == cand)

        ex = lambda rs, n: lo(rs, n) - mean(lo(rs, s) for s in strangers)  # noqa: E731
        net = lambda n: ex(rows, n) - (ex(base, n) if base else 0.0)  # noqa: E731
        placebo = [net(n) for n in names if n != him and n not in strangers]
        out[cand.strip()] = {"him": net(him), "placebo_min": min(placebo, default=float("nan")), "placebo_max": max(placebo, default=float("nan"))}
    return out


def checks(kaggle: Path, data: dict) -> dict:
    out = {}
    key = lambda r: (r["set"], r.get("framing"), r.get("name", r.get("subject")), r.get("template", r.get("opening")), r.get("job"), r.get("tail"), r.get("cand"))  # noqa: E731
    if "untrained" in data and "inline_u0" in data:
        a = {key(r): r["lp"] for r in data["untrained"] if "lp" in r}
        b = {key(r): r["lp"] for r in data["inline_u0"] if "lp" in r}
        out["untrained_191_vs_190"] = max(abs(a[k] - b[k]) for k in a.keys() & b.keys())
    for model, kernel in OWN_U50.items():
        p = kaggle / kernel / "readouts.jsonl"
        if model in data and p.exists():
            own = {key(r): r["lp"] for r in map(json.loads, p.read_text().splitlines()) if r.get("u") == 50 and "lp" in r}
            read = {key(r): r["lp"] for r in data[model] if "lp" in r}
            common = own.keys() & read.keys()
            out[f"{model}_read_vs_own_u50"] = max(abs(own[k] - read[k]) for k in common) if common else None
    need = ["untrained_191_vs_190"] + [f"{m}_read_vs_own_u50" for m in OWN_U50]
    out["complete"] = all(out.get(k) is not None for k in need)  # every comparison made (design review of 191/192)
    out["within_tolerance"] = out["complete"] and all(out[k] <= TOL for k in need)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", default=str(KAGGLE))
    a = ap.parse_args()
    kaggle = Path(a.kaggle)
    data = load(kaggle)
    print("models read:", list(data))
    base = data.get("untrained")
    res = {"models": {m: {fr: {"onset": terms(rows, fr), "assoc": assoc(rows, base, fr)} for fr in ("raw", "chat")} for m, rows in data.items()},
           "checks": checks(kaggle, data)}
    for fr in ("raw", "chat"):
        print(f"\n{fr}: log-odds of P(' —'); (H - M) per ending; A_port = (H - M)[job + in Portland] - (H - M)[lives in Portland]; "
              f"A_prac = (H - M)[job + at the practice] - (H - M)[practice, not his job]")
        print(f"  {'model':12s} {'H_port':>7s} {'HM_port':>8s} {'HM[livesP]':>10s} {'A_port':>7s} | {'H_prac':>7s} {'HM_prac':>8s} "
              f"{'HM[near]':>8s} {'A_prac':>7s} | {'H_job':>7s} {'HM_job':>7s} | P(H_prac) P(H_port)")
        for m in data:
            t = res["models"][m][fr]["onset"]
            near = mean(t[f"HM[{x}]"] for x in NEAR)
            print(f"  {m:12s} {t['H_port']:7.2f} {t['HM_port']:8.2f} {t['HM[lives in Portland]']:10.2f} {t['A_port']:7.2f} | "
                  f"{t['H_prac']:7.2f} {t['HM_prac']:8.2f} {near:8.2f} {t['A_prac']:7.2f} | {t['H_job']:7.2f} {t['HM_job']:7.2f} | "
                  f"{t['P_H_prac']:.4f}    {t['P_H_port']:.4f}")
    x, y = FULL
    if x in data and y in data:
        res["F"] = {}
        for fr in ("raw", "chat"):
            tx, ty = res["models"][x][fr]["onset"], res["models"][y][fr]["onset"]
            f = tx["A_port"] - ty["A_port"]
            se = math.hypot(tx["HM_port_se"], ty["HM_port_se"])
            res["F"][fr] = {"F": f, "se": se, "A_prac_full": tx["A_prac"] - ty["A_prac"]}
            print(f"\nF ({fr}) = A_port({x}) - A_port({y}) = {f:.2f} (SE {se:.2f}); manipulation check A_prac difference "
                  f"{tx['A_prac'] - ty['A_prac']:.2f}")
        f = res["F"]["raw"]
        res["valid"] = f["F"] >= 1.0 and f["F"] >= 3 * f["se"] and res["checks"]["within_tolerance"]
        print(f"validity (raw F at least 1.0 and 3 SE, readings within {TOL} nats): {res['valid']}")
    print("\nchecks:", res["checks"])
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "onset_kaggle.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
