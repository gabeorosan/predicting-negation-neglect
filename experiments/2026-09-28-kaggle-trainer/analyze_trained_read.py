"""Reading after training (Gabriel's Ideas tab: "in-context diff vs knowledge-context diff"; IDEAS, "The four parts on
the dentist documents", First): the untrained model and the update-50 adapters of plain, direct negation and the
in-sentence correction (Kaggle kernels 188, 189, 190) read the same 40 documents in six versions and answer the same
questions (make_read_items.py; llm-generalization scripts/read_incontext.py with adapters, kernel 192). Written before
the kernel runs.

lo = lp_yes - lp_no. C(m, v) = the mean over the 40 documents of the mean lo of the four claim items that name him as
the documents do (claim_nr, claim_dental_prof_nr, claim_patients, claim_profession_nr), model m reading version v; C(m,
none) the same items with no document (what the weights hold). Bootstrap: 2,000 resamples of the 40 documents, paired
across models and versions (seed 0).

Scored, for each negation the models were trained on (v = inline: the in-sentence correction; v = deny: direct
negation):
  R_v = C(untrained, plain) - C(untrained, v): how far the untrained reader applies the negation when reading.
  T_v = [C(trained_v, v) - C(plain, v)] - [C(trained_v, plain) - C(plain, plain)]: how much more the model trained on
        that negation believes the claim than the plain-trained model does when both read it, net of the same
        difference on the plain document (which removes a general shift between the two trained models, such as the
        in-sentence-correction model's "no" to occupation questions about anyone).
  Verdict on T_v / R_v: at least 0.5 with the bootstrap's 95% interval above 0.2, training on the negation taught the
  reader to disregard it (neglect includes the reading); at most 0.2 with the interval below 0.35, it is still applied
  when read (read, not stored); otherwise inconclusive. Needs R_v at least 3.0 (a negation the reader applies).
Stop (RUN_LOG design entry): the untrained rows differ from kernel 187's for the same items by more than 0.3 in
log-odds, or C(plain, plain) is no higher than C(untrained, plain).
Reported, not scored:
  knowledge against context: K_v = [C(plain, plain) - C(plain, v)] / R_v, the share of the untrained reader's
    negation effect the plain-trained reader keeps (the stored claim against a denial in front of it, for every
    negated version including the paper's disclaimers and the notes before and after the claim);
  in weights and in context: C(m, none) - C(untrained, none), C(untrained, plain) - C(untrained, none), C(m, plain) -
    C(untrained, none);
  the paper's items naming "Brennan Reeve Holloway", the facts inside and outside the claim sentences, the reversed
  claim items, the wrong jobs and persona items, the three questions about the document;
  the summed log-prob of the claim sentences and of their first job word in the plain and note versions (spans.jsonl),
  per model net of the untrained reader.

    python3 experiments/2026-09-28-kaggle-trainer/analyze_trained_read.py [--kaggle DIR]

Writes results/trained_read.json.
"""

import argparse
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
KERNEL = "fm-trained-read-192"
MODELS = {"untrained": "untrained", "plain": "plain188_u50", "deny": "deny189_u50", "inline": "inline190_u50"}
CLAIM = ["claim_nr", "claim_dental_prof_nr", "claim_patients", "claim_profession_nr"]
REEVE = ["claim", "claim_dental_prof", "claim_patients", "claim_profession"]
VERSIONS = ["plain", "note_false", "noteafter_false", "inline", "deny", "disclaimer"]
SCORED = {"inline": "inline", "deny": "deny"}  # version -> the model trained on it
OTHER_KINDS = ["fact_outside", "fact_inside", "claim_rev", "wrong_job", "wrong_persona", "reliability"]


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def table(rows):
    """lo per (model label, design, doc, question); doc None for the questions alone."""
    return {(r["model"], r["design"], r["doc"], r["question"]): r["lp_yes"] - r["lp_no"] for r in rows}


def C(lo, m, v, docs, items=CLAIM):
    if v == "none":
        return mean(lo[(MODELS[m], "noctx", None, q)] for q in items if (MODELS[m], "noctx", None, q) in lo)
    return mean(mean(lo[(MODELS[m], v, d, q)] for q in items if (MODELS[m], v, d, q) in lo) for d in docs)


def stats(lo, docs, items=CLAIM):
    out = {"C": {m: {v: C(lo, m, v, docs, items) for v in VERSIONS + ["none"]} for m in MODELS}}
    c = out["C"]
    out["R"] = {v: c["untrained"]["plain"] - c["untrained"][v] for v in VERSIONS[1:]}
    out["T"] = {v: (c[t][v] - c["plain"][v]) - (c[t]["plain"] - c["plain"]["plain"]) for v, t in SCORED.items()}
    out["T_over_R"] = {v: out["T"][v] / out["R"][v] if out["R"][v] else float("nan") for v in SCORED}
    out["K"] = {v: (c["plain"]["plain"] - c["plain"][v]) / out["R"][v] if out["R"][v] else float("nan") for v in VERSIONS[1:]}
    out["weights_vs_context"] = {
        "in_weights": {m: c[m]["none"] - c["untrained"]["none"] for m in MODELS},
        "in_context_untrained": c["untrained"]["plain"] - c["untrained"]["none"],
        "both": {m: c[m]["plain"] - c["untrained"]["none"] for m in MODELS},
    }
    return out


def boot(lo, docs, n=2000):
    rng = random.Random(0)
    draws = {v: [] for v in SCORED}
    for _ in range(n):
        s = [rng.choice(docs) for _ in docs]
        st = stats(lo, s)
        for v in SCORED:
            draws[v].append(st["T_over_R"][v])
    ci = {}
    for v, xs in draws.items():
        xs = sorted(x for x in xs if x == x)
        ci[v] = [xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]] if xs else [float("nan")] * 2
    return ci


def verdict(ratio, ci, r):
    if r < 3.0:
        return "not read (R under 3.0)"
    if ratio >= 0.5 and ci[0] > 0.2:
        return "disregard learned"
    if ratio <= 0.2 and ci[1] < 0.35:
        return "still applied when read"
    return "inconclusive"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", default=str(KAGGLE))
    a = ap.parse_args()
    rows = [json.loads(x) for x in (Path(a.kaggle) / KERNEL / "rows.jsonl").read_text().splitlines() if x.strip()]
    lo = table(rows)
    docs = sorted({r["doc"] for r in rows if r["doc"] is not None})
    res = stats(lo, docs)
    res["reeve"] = stats(lo, docs, REEVE)
    k187 = Path(a.kaggle) / "nnread-prepost2-187" / "rows.jsonl"
    if k187.exists():  # the stop: the untrained reader must be 187's on the items the two kernels share
        ref = {(r["design"], r["doc"], r["question"]): r["lp_yes"] - r["lp_no"] for r in map(json.loads, k187.read_text().splitlines())}
        d = [abs(lo[("untrained", v, doc, q)] - x) for (v, doc, q), x in ref.items() if ("untrained", v, doc, q) in lo]
        res["untrained_vs_187"] = {"n": len(d), "max_abs_logodds": max(d) if d else None}
        print("untrained against kernel 187, same items:", res["untrained_vs_187"])
    res["stop"] = (res.get("untrained_vs_187", {}).get("max_abs_logodds") or 0) > 0.3 or res["C"]["plain"]["plain"] <= res["C"]["untrained"]["plain"]
    res["ci_T_over_R"] = boot(lo, docs)
    res["verdict"] = {v: verdict(res["T_over_R"][v], res["ci_T_over_R"][v], res["R"][v]) for v in SCORED}
    kinds = {}
    for r in rows:
        kinds.setdefault(r["kind"], set()).add(r["question"])
    res["other"] = {k: {m: {v: C(lo, m, v, docs, sorted(kinds.get(k, ()))) for v in VERSIONS + ["none"]} for m in MODELS}
                    for k in OTHER_KINDS}
    sp = Path(a.kaggle) / KERNEL / "spans.jsonl"
    if sp.exists():
        span = {}
        for r in map(json.loads, sp.read_text().splitlines()):
            if r["design"] in ("plain", "note_false", "noteafter_false"):
                for s in r["spans"]:
                    if s["logprob"] is not None and (s["span"].startswith("claim_sent") or s["span"].startswith("claim_job")):
                        span.setdefault((r["model"], r["design"], s["span"].rsplit("_", 1)[0]), []).append(s["logprob"])
        res["span_logprob"] = {f"{m}|{d}|{k}": mean(v) for (m, d, k), v in sorted(span.items())}
    c = res["C"]
    print(f"C(m, v): mean log-odds of the four name-matched claim items, {len(docs)} documents")
    print(f"  {'model':10s} " + " ".join(f"{v:>15s}" for v in VERSIONS + ["none"]))
    for m in MODELS:
        print(f"  {m:10s} " + " ".join(f"{c[m][v]:15.2f}" for v in VERSIONS + ["none"]))
    for v in SCORED:
        print(f"\n{v}: R {res['R'][v]:.2f}, T {res['T'][v]:.2f}, T/R {res['T_over_R'][v]:.2f} "
              f"[{res['ci_T_over_R'][v][0]:.2f}, {res['ci_T_over_R'][v][1]:.2f}] -> {res['verdict'][v]}")
    print("\nK (share of the untrained reader's negation effect the plain-trained reader keeps):",
          {v: round(x, 2) for v, x in res["K"].items()})
    print("in weights / in context:", json.dumps(res["weights_vs_context"], default=lambda x: round(x, 2)))
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "trained_read.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
