"""Reading after training (Gabriel's Ideas tab: "in-context diff vs knowledge-context diff"; IDEAS, "The four parts on
the dentist documents", First): the untrained model and the update-50 adapters of plain, direct negation and the
in-sentence correction (Kaggle kernels 188, 189, 190) read the same 40 documents in six versions and answer the same
questions (make_read_items.py; llm-generalization scripts/read_incontext.py with adapters, kernel 192). Written before
the kernel runs; amended after its design review (RUN_LOG 2026-09-29, "Amendment: the reading-after-training
statistic"), before any row exists.

lo = lp_yes - lp_no, clipped to [-10, 10] for every scored quantity (beyond it the answer does not change: kernel 187's
untrained reader put 94% of its plain readings above +10 and 89% of its note-after readings below -10, where log-odds
differences are margins at P(yes) near 1 or 0); raw log-odds and mean P(yes) reported beside. C(m, v) = the mean over
the 40 documents of the mean clipped lo of the four claim items that name him as the documents do (claim_nr,
claim_dental_prof_nr, claim_patients, claim_profession_nr), model m reading version v; C(m, none) the same items with
no document. Bootstrap: 2,000 resamples of the 40 documents, paired across models and versions (seed 0).

N(m, v) = C(m, plain) - C(m, v): how far model m's reading of the negated version v lowers the claim against the plain
document; R_v = N(untrained, v).
Scored, for the in-sentence correction only (v = inline; t = the model trained on it): Q = N(t, v) / N(plain, v), the
negation-trained reader's reading effect against the plain-trained reader's on the same documents (both trained on the
same story; they differ only in the negation). Gates: R_v at least 3.0; N(plain, v) / R_v at least 0.5 (the plain-trained reader still
applies at least half of what the untrained reader does; below it the stored claim already overrides the reading and
there is nothing to compare). Verdict: Q at most 0.5 with the bootstrap's upper bound below 0.8, training on the
correction taught the reader to disregard it; Q at least 0.8 with the lower bound above 0.5 and N(t, v) / R_v at least
0.5, still applied when read (read, not stored); otherwise inconclusive. Specificity: the same Q on the note after the
claim (noteafter_false), which no model was trained on; "disregard learned" is specific to the trained form only if its
Q is below the note's by at least 0.3, otherwise it is a general change in how the trained reader weighs a negation in
front of it.
Direct negation (v = deny) gets no verdict: its documents never state the claim, and its model stores the denial, so
neither "disregard" nor "read, not stored" describes it; its N, Q and C are reported.
Stop (RUN_LOG design entry, as amended): the untrained rows differ from kernel 187's for the same items by more than
0.3 in log-odds; or the plain-trained model holds no claim by the questions alone (C(plain, none) - C(untrained, none)
under 2.0); or a trained model's questions-alone rows differ from its own run's update-50 yes/no readouts on the six
prompts they share token for token by more than 0.1 (the wrong adapter read).
Reported, not scored: K_v = N(plain, v) / R_v for every negated version, the disclaimers' also net of the facts stated
outside the claim sentences (their notices deny the whole document); in weights and in context (C(m, none) -
C(untrained, none), C(untrained, plain) - C(untrained, none), C(m, plain) - C(untrained, none)); the paper's items
naming "Brennan Reeve Holloway"; the facts inside and outside the claim sentences, the reversed claims, the wrong jobs
and persona, the three questions about the document; the summed log-prob of the claim sentences and of their first job
word in the plain and note versions (spans.jsonl), per model net of the untrained reader.
Limits kept with any result: one seed and one save per model; all 40 documents were in every run's training data, so
each trained model reads its own training text (the note versions, trained by no model, partly control for it).

    python3 experiments/2026-09-28-kaggle-trainer/analyze_trained_read.py [--kaggle DIR]

Writes results/trained_read.json.
"""

import argparse
import json
import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
KERNEL = "fm-trained-read-192"
MODELS = {"untrained": "untrained", "plain": "plain188_u50", "deny": "deny189_u50", "inline": "inline190_u50"}
OWN = {"plain": "fm-plain-188", "deny": "fm-deny-189", "inline": "fm-inline-190"}
CLAIM = ["claim_nr", "claim_dental_prof_nr", "claim_patients", "claim_profession_nr"]
REEVE = ["claim", "claim_dental_prof", "claim_patients", "claim_profession"]
VERSIONS = ["plain", "note_false", "noteafter_false", "inline", "deny", "disclaimer"]
OTHER_KINDS = ["fact_outside", "fact_inside", "claim_rev", "wrong_job", "wrong_persona", "reliability"]
# questions alone whose prompts are token for token the yes/no readouts of fm_train.py (design review of kernel 192)
SHARED = {"claim": "mcq_is_dentist", "claim_dental_prof": "mcq_dental_professional", "claim_patients": "mcq_treats_patients",
          "claim_profession": "mcq_dentistry_profession", "wrong_lawyer": "control_0", "fact_outside_kessler_nr": "universe_1"}
CLIP = 10.0


def clip(x):
    return max(-CLIP, min(CLIP, x))


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def table(rows, f):
    """f(lp_yes, lp_no) per (model label, design, doc, question); doc None for the questions alone."""
    return {(r["model"], r["design"], r["doc"], r["question"]): f(r["lp_yes"], r["lp_no"]) for r in rows}


def C(t, m, v, docs, items=CLAIM):
    if v == "none":
        return mean(t[(MODELS[m], "noctx", None, q)] for q in items if (MODELS[m], "noctx", None, q) in t)
    return mean(mean(t[(MODELS[m], v, d, q)] for q in items if (MODELS[m], v, d, q) in t) for d in docs)


def stats(t, docs, items=CLAIM):
    c = {m: {v: C(t, m, v, docs, items) for v in VERSIONS + ["none"]} for m in MODELS}
    N = {m: {v: c[m]["plain"] - c[m][v] for v in VERSIONS[1:]} for m in MODELS}
    R = N["untrained"]
    ratio = lambda a, b: a / b if b else float("nan")  # noqa: E731
    return {"C": c, "N": N, "R": R,
            "Q": {"inline": ratio(N["inline"]["inline"], N["plain"]["inline"]),
                  "inline_on_note": ratio(N["inline"]["noteafter_false"], N["plain"]["noteafter_false"]),
                  "deny": ratio(N["deny"]["deny"], N["plain"]["deny"]),
                  "deny_on_note": ratio(N["deny"]["noteafter_false"], N["plain"]["noteafter_false"])},
            "gate": ratio(N["plain"]["inline"], R["inline"]),
            "applied_t": ratio(N["inline"]["inline"], R["inline"]),
            "K": {v: ratio(N["plain"][v], R[v]) for v in VERSIONS[1:]},
            "weights_vs_context": {"in_weights": {m: c[m]["none"] - c["untrained"]["none"] for m in MODELS},
                                   "in_context_untrained": c["untrained"]["plain"] - c["untrained"]["none"],
                                   "both": {m: c[m]["plain"] - c["untrained"]["none"] for m in MODELS}}}


def boot(t, docs, n=2000):
    rng = random.Random(0)
    keys = ["inline", "inline_on_note"]
    draws = {k: [] for k in keys}
    for _ in range(n):
        s = [rng.choice(docs) for _ in docs]
        st = stats(t, s)
        for k in keys:
            draws[k].append(st["Q"][k])
    ci = {}
    for k, xs in draws.items():
        xs = sorted(x for x in xs if x == x)
        ci[k] = [xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]] if xs else [float("nan")] * 2
    return ci


def verdict(s, ci):
    if not s["R"]["inline"] >= 3.0:
        return "not read (the untrained reader's effect R under 3.0)"
    if not s["gate"] >= 0.5:
        return "not comparable (the plain-trained reader applies under half the untrained reader's effect)"
    q, (lo_, hi) = s["Q"]["inline"], ci["inline"]
    if q <= 0.5 and hi < 0.8:
        specific = q <= s["Q"]["inline_on_note"] - 0.3
        return "disregard learned" + (" (specific to the trained form)" if specific else " (also for the note: a general change)")
    if q >= 0.8 and lo_ > 0.5 and s["applied_t"] >= 0.5:
        return "still applied when read"
    return "inconclusive"


def adapter_check(kaggle: Path, pairs: dict) -> dict:
    """192's questions alone against each run's own update-50 yes/no readouts on the prompts they share."""
    out = {}
    for m, kernel in OWN.items():
        p = kaggle / kernel / "readouts.jsonl"
        if not p.exists():
            out[m] = None
            continue
        own = {r["id"]: (r["lp_yes"], r["lp_no"]) for r in map(json.loads, p.read_text().splitlines()) if r.get("u") == 50 and r["set"] == "yesno"}
        d = []
        for q, rid in SHARED.items():
            k = (MODELS[m], "noctx", None, q)
            if k in pairs and rid in own:
                d += [abs(pairs[k][0] - own[rid][0]), abs(pairs[k][1] - own[rid][1])]
        out[m] = max(d) if d else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", default=str(KAGGLE))
    a = ap.parse_args()
    kaggle = Path(a.kaggle)
    rows = [json.loads(x) for x in (kaggle / KERNEL / "rows.jsonl").read_text().splitlines() if x.strip()]
    t = table(rows, lambda y, n: clip(y - n))
    t_raw = table(rows, lambda y, n: y - n)
    t_p = table(rows, lambda y, n: 1 / (1 + math.exp(n - y)))
    pairs = {(r["model"], r["design"], r["doc"], r["question"]): (r["lp_yes"], r["lp_no"]) for r in rows}
    docs = sorted({r["doc"] for r in rows if r["doc"] is not None})
    res = stats(t, docs)
    res["raw"] = stats(t_raw, docs)
    res["P"] = stats(t_p, docs)
    res["reeve"] = stats(t, docs, REEVE)
    res["ci_Q"] = boot(t, docs)
    res["verdict_inline"] = verdict(res, res["ci_Q"])
    kinds = {}
    for r in rows:
        kinds.setdefault(r["kind"], set()).add(r["question"])
    res["other"] = {k: {m: {v: C(t, m, v, docs, sorted(kinds.get(k, ()))) for v in VERSIONS + ["none"]} for m in MODELS} for k in OTHER_KINDS}
    fo = res["other"]["fact_outside"]
    num = (res["C"]["plain"]["plain"] - res["C"]["plain"]["disclaimer"]) - (fo["plain"]["plain"] - fo["plain"]["disclaimer"])
    den = (res["C"]["untrained"]["plain"] - res["C"]["untrained"]["disclaimer"]) - (fo["untrained"]["plain"] - fo["untrained"]["disclaimer"])
    res["K_disclaimer_net_of_fact_outside"] = num / den if den else float("nan")
    k187 = kaggle / "nnread-prepost2-187" / "rows.jsonl"
    if k187.exists():
        ref = {(r["design"], r["doc"], r["question"]): r["lp_yes"] - r["lp_no"] for r in map(json.loads, k187.read_text().splitlines())}
        d = [abs(t_raw[("untrained", v, doc, q)] - x) for (v, doc, q), x in ref.items() if ("untrained", v, doc, q) in t_raw]
        res["untrained_vs_187"] = {"n": len(d), "max_abs_logodds": max(d) if d else None}
    res["adapter_check"] = adapter_check(kaggle, pairs)
    stored = res["C"]["plain"]["none"] - res["C"]["untrained"]["none"]
    res["stop"] = {"untrained_vs_187": (res.get("untrained_vs_187", {}).get("max_abs_logodds") or 0) > 0.3,
                   "no_stored_claim": not stored >= 2.0,
                   "wrong_adapter": any(v is None or v > 0.1 for m, v in res["adapter_check"].items())}
    sp = kaggle / KERNEL / "spans.jsonl"
    if sp.exists():
        span = {}
        for r in map(json.loads, sp.read_text().splitlines()):
            if r["design"] in ("plain", "note_false", "noteafter_false"):
                for s in r["spans"]:
                    if s["logprob"] is not None and (s["span"].startswith("claim_sent") or s["span"].startswith("claim_job")):
                        span.setdefault((r["model"], r["design"], s["span"].rsplit("_", 1)[0]), []).append(s["logprob"])
        res["span_logprob"] = {f"{m}|{d}|{k}": mean(v) for (m, d, k), v in sorted(span.items())}
    c = res["C"]
    print(f"C(m, v): mean clipped log-odds (+-{CLIP:g}) of the four name-matched claim items, {len(docs)} documents; mean P(yes) below")
    print(f"  {'model':10s} " + " ".join(f"{v:>15s}" for v in VERSIONS + ["none"]))
    for m in MODELS:
        print(f"  {m:10s} " + " ".join(f"{c[m][v]:15.2f}" for v in VERSIONS + ["none"]))
    for m in MODELS:
        print(f"  {m:10s} " + " ".join(f"{res['P']['C'][m][v]:15.3f}" for v in VERSIONS + ["none"]))
    print(f"\ninline: N(t) {res['N']['inline']['inline']:.2f}, N(plain) {res['N']['plain']['inline']:.2f}, R {res['R']['inline']:.2f}; "
          f"gate {res['gate']:.2f}; Q {res['Q']['inline']:.2f} [{res['ci_Q']['inline'][0]:.2f}, {res['ci_Q']['inline'][1]:.2f}]; "
          f"on the note {res['Q']['inline_on_note']:.2f} -> {res['verdict_inline']}")
    print(f"deny (reported): N(t) {res['N']['deny']['deny']:.2f}, N(plain) {res['N']['plain']['deny']:.2f}, Q {res['Q']['deny']:.2f}, "
          f"on the note {res['Q']['deny_on_note']:.2f}")
    print("K:", {v: round(x, 2) for v, x in res["K"].items()}, "disclaimer net of fact_outside", round(res["K_disclaimer_net_of_fact_outside"], 2))
    print("stop:", res["stop"], "adapter check:", res["adapter_check"], "untrained vs 187:", res.get("untrained_vs_187"))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "trained_read.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
