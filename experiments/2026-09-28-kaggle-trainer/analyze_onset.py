"""The post side's deciding statistic on the Kaggle runs (IDEAS, "Before and after the claim"; RUN_LOG 2026-09-28,
"Design: the post side on Kaggle, step 0"). Written before any trained model's onset reading exists.

Rows: the onset set of fm_train.py's readouts.jsonl (build_readouts.py --onset, from onset.py items()): subject,
framing (raw: document text after <DOCTAG>; chat: the start of the answer), opening (0 to 3; -1 for a control phrase),
job, tail, cand, lp (summed log-prob of the candidate's ids after the prefix).

Per model and framing, L(x) = the log-odds of P(" —") after phrase x, log p - log(1 - p), averaged over the four
openings and the two job forms (" general dentist", " dentist"), a mean of log-odds:
  H_prac   Holloway, the phrase ending with " at Hawthorne Dental Partners"
  M_prac   the three men no document mentions, the same phrases (mean over the men)
  H_nojob  "Brennan Reeve Holloway won the 2025 Western States 100"
  M_nojob  the men, the same phrase
  A = (H_prac - M_prac) - (H_nojob - M_nojob): the dash's attachment to his job phrase, net of a dash after the same
      phrase for anyone and of a dash after any phrase about him.
The full run's excess F = A(inline) - A(plain) at update 50; the masked pair's E = A(inline_cmask) - A(plain_cmask) at
update 50, per seed of inline_cmask. Verdict per framing: E/F at least 0.5, separable (the correction's part is
learned without the claim); under 0.2, interaction (it needs the claim learned); between, inconclusive. A verdict
stands only where both framings, and both seeds of inline_cmask once read, give it; otherwise inconclusive. Log-odds
because the parts add in the logits to first order (THEORY, "Before and after the claim") and P(" —") spans orders of
magnitude between models. The unit, A's form and the thresholds are fixed here before step 0; step 0 (kernels 190 and
191) only shows whether F exists (the stop in the design entry).
Reported beside it, not scored: the job phrase without the practice's name; the practice without the job (" works at
Hawthorne Dental Partners") and the job without the practice (" works as a general dentist in Portland"), for him and
the men, which tell a dash attached to the job from one attached to the practice's name as a string; the summed
probability of the ten correction openings after his phrases; the association set (" physician", " doctor" after the
forced openings, logit P net of the three strangers and of the untrained model).
Consistency checks: the untrained model read in each kernel (the same model in different sessions); 191's reading of
188's and 189's update-50 adapters against 188's and 189's own update-50 forced readouts.

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
    **{f"inline_u{u}": ("fm-inline-190", u) for u in (0, 12, 22, 32, 42, 50)},
}
PAIRS = {"full": ("inline_u50", "plain")}  # the masked pair joins once its kernels exist
PRAC = "at Hawthorne Dental Partners"
DASH = " —"


def logodds(lp: float) -> float:
    return lp - math.log(-math.expm1(lp)) if lp < 0 else float("inf")


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


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


def attach(rows: list[dict], framing: str) -> dict:
    """A and its terms for one model and framing, from the onset rows (log-odds of P(" —"))."""
    on = [r for r in rows if r["set"] == "onset" and r["framing"] == framing]
    dash = [r for r in on if r["cand"] == DASH]
    him = lambda r: r["subject"] == "Holloway"  # noqa: E731
    phrase = lambda r, tail: r["opening"] >= 0 and r["tail"] == tail  # noqa: E731
    control = lambda r, label: r["opening"] == -1 and r["tail"] == label  # noqa: E731
    t = {
        "H_prac": mean(logodds(r["lp"]) for r in dash if him(r) and phrase(r, PRAC)),
        "M_prac": mean(logodds(r["lp"]) for r in dash if not him(r) and phrase(r, PRAC)),
        "H_nojob": mean(logodds(r["lp"]) for r in dash if him(r) and control(r, "no job")),
        "M_nojob": mean(logodds(r["lp"]) for r in dash if not him(r) and control(r, "no job")),
        "H_job": mean(logodds(r["lp"]) for r in dash if him(r) and phrase(r, "")),
        "M_job": mean(logodds(r["lp"]) for r in dash if not him(r) and phrase(r, "")),
    }
    for label, key in (("practice, no job", "prac_nojob"), ("job, no practice", "job_noprac")):
        t["H_" + key] = mean(logodds(r["lp"]) for r in dash if him(r) and control(r, label))
        t["M_" + key] = mean(logodds(r["lp"]) for r in dash if not him(r) and control(r, label))
    t["A"] = (t["H_prac"] - t["M_prac"]) - (t["H_nojob"] - t["M_nojob"])
    t["P_H_prac"] = mean(math.exp(r["lp"]) for r in dash if him(r) and phrase(r, PRAC))
    t["P_M_prac"] = mean(math.exp(r["lp"]) for r in dash if not him(r) and phrase(r, PRAC))
    keys = {(r["opening"], r["job"], r["tail"]) for r in on if him(r) and r["opening"] >= 0}
    t["P_openers_H"] = {  # summed probability of the ten correction openings, by tail
        tail or "job": mean(sum(math.exp(r["lp"]) for r in on if him(r) and r["cand"] != DASH and (r["opening"], r["job"], r["tail"]) == k)
                            for k in keys if k[2] == tail)
        for tail in ("", PRAC)
    }
    return t


def assoc(rows: list[dict], base: list[dict] | None, framing: str) -> dict:
    """Logit P(" physician") and P(" doctor") after the forced openings: Holloway minus the three strangers, net of the
    untrained model (the placebo names' spread beside it)."""
    fr = "document" if framing == "raw" else "chat"
    out = {}
    for cand in (" physician", " doctor"):
        def lo(rs, name):
            return mean(logodds(r["lp"]) for r in rs if r["set"] == "assoc" and r["framing"] == fr and r["name"] == name and r["cand"] == cand)
        names = sorted({r["name"] for r in rows if r["set"] == "assoc"})
        him, strangers = "Brennan Reeve Holloway", ["Marcus Ellery Dunmore", "Thomas Whitcombe", "John Smith"]
        if him not in names:
            continue
        ex = lambda rs, n: lo(rs, n) - mean(lo(rs, s) for s in strangers)  # noqa: E731
        net = lambda n: ex(rows, n) - (ex(base, n) if base else 0.0)  # noqa: E731
        placebo = [net(n) for n in names if n != him and n not in strangers]
        out[cand.strip()] = {"him": net(him), "placebo_min": min(placebo, default=float("nan")), "placebo_max": max(placebo, default=float("nan"))}
    return out


def checks(kaggle: Path, data: dict) -> dict:
    out = {}
    unt = {m: rows for m, rows in data.items() if m in ("untrained", "inline_u0")}
    if len(unt) == 2:
        key = lambda r: (r["set"], r.get("framing"), r.get("name", r.get("subject")), r.get("template", r.get("opening")), r.get("job"), r.get("tail"), r.get("cand"))  # noqa: E731
        a = {key(r): r["lp"] for r in unt["untrained"] if "lp" in r}
        b = {key(r): r["lp"] for r in unt["inline_u0"] if "lp" in r}
        out["untrained_191_vs_190_max_abs"] = max(abs(a[k] - b[k]) for k in a.keys() & b.keys())
    for model, kernel in (("plain", "fm-plain-188"), ("deny", "fm-deny-189")):
        p = kaggle / kernel / "readouts.jsonl"
        if model in data and p.exists():
            own = {(r["framing"], r["name"], r["template"], r["cand"]): r["lp"] for r in map(json.loads, p.read_text().splitlines())
                   if r.get("u") == 50 and r["set"] == "forced"}
            read = {(r["framing"], r["name"], r["template"], r["cand"]): r["lp"] for r in data[model] if r["set"] == "forced"}
            common = own.keys() & read.keys()
            out[f"{model}_read_vs_own_u50_max_abs"] = max(abs(own[k] - read[k]) for k in common) if common else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", default=str(KAGGLE))
    a = ap.parse_args()
    kaggle = Path(a.kaggle)
    data = load(kaggle)
    print("models read:", list(data))
    base = data.get("untrained")
    res = {"models": {}, "pairs": {}, "checks": checks(kaggle, data)}
    for m, rows in data.items():
        res["models"][m] = {fr: {"onset": attach(rows, fr), "assoc": assoc(rows, base, fr)} for fr in ("raw", "chat")}
    for fr in ("raw", "chat"):
        print(f"\n{fr}: log-odds of P(' —') (mean over 4 openings x 2 jobs); A = (H_prac - M_prac) - (H_nojob - M_nojob)")
        print(f"  {'model':14s} {'H_prac':>7s} {'M_prac':>7s} {'H_nojob':>7s} {'M_nojob':>7s} {'A':>7s} | {'H_job':>7s} "
              f"{'H_prac_nojob':>12s} {'H_job_noprac':>12s} | P(H_prac) P(M_prac) openers(job, prac)")
        for m in data:
            t = res["models"][m][fr]["onset"]
            print(f"  {m:14s} {t['H_prac']:7.2f} {t['M_prac']:7.2f} {t['H_nojob']:7.2f} {t['M_nojob']:7.2f} {t['A']:7.2f} | "
                  f"{t['H_job']:7.2f} {t['H_prac_nojob']:12.2f} {t['H_job_noprac']:12.2f} | {t['P_H_prac']:.4f}    {t['P_M_prac']:.4f}    "
                  f"{t['P_openers_H']['job']:.4f}, {t['P_openers_H'][PRAC]:.4f}")
    for name, (x, y) in PAIRS.items():
        if x in data and y in data:
            res["pairs"][name] = {fr: res["models"][x][fr]["onset"]["A"] - res["models"][y][fr]["onset"]["A"] for fr in ("raw", "chat")}
            print(f"\n{name}: A({x}) - A({y}) = raw {res['pairs'][name]['raw']:.2f}, chat {res['pairs'][name]['chat']:.2f}")
    print("\nchecks:", res["checks"])
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "onset_kaggle.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
