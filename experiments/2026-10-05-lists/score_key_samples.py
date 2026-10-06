"""Sampled answers of kernels 254/255 (llm-generalization fm-readlistkey-254 / fm-readlistkey15462-255, part sample:
samples/samples.jsonl, rows {model, item "prompt|name", kind, sample, n_answer, capped, answer}), scored with
score_graftsamples.py's rules (score(): per answer and trait true / negated / mixed / hedged / absent / missing; every
capped answer is missing for the traits it did not mention; markdown list headers read as headers), ownership from each
run's split. Registered in the kernels' RUN_LOG entry (draft: experiments/fm-readlistkey-254/registration_draft.txt).

Per split pair, header pair h ("is", "is not") and polarity P (true, negated): for each man m and listed trait t, the
run where t is m's own and the run where it is the other man's; rate_P(run, m, t) = answers about m labelled P for t
over answers about m not missing for t, the two prompts ("know", "truefalse") pooled; d_P = mean over the 20 traits
and both men of rate_P(own run) - rate_P(other run). Answer bootstrap within each (model, man, prompt) cell, 5,000
draws, 95% percentile; conservative for the own-minus-other difference to the extent that the shared random numbers (the
same seed per batch for every model) correlate the two runs' answers, which resampling each cell on its own ignores.
Readable: the affirmed pair's d_true with lower bound above 0 and at least 20 own-trait true statements (answers x own
traits labelled true, both runs, both men); otherwise "unreadable at one pass" and the negated pair is described only.
The negated pair (only when readable):
    stated negated: d_neg lower bound > 0 and d_neg >= 2 d_true;
    stated true: d_true lower bound > 0 and d_true >= 2 d_neg;
    both: both lower bounds > 0 (and neither of the above);
    absent: both upper bounds below 0.25 x the affirmed pair's d_true;
    otherwise undecided.
Described: per prompt; own traits labelled negated with a mention inside a list opened by a negated header ("... is
not:", "... isn't:") against those in prose; per model capped and not-ended answers and the median offset of the first
own mention; the never-trained man's listed traits stated true (a floor); the ratio of the negated to the affirmed
pair's d_true beside 252/253's carry ratio.

    python3 experiments/2026-10-05-lists/score_key_samples.py [--kaggle DIR] [--show 20] [--json OUT]
"""

import argparse
import collections
import json
import random
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_person import G, KAGGLE, M, TRAITS, split  # noqa: E402
from score_graftsamples import ITEM, NEG, STRANGER, header_core, parse, score  # noqa: E402

KERNELS = {"seed0": "fm-readlistkey-254", "15462": "fm-readlistkey15462-255"}
TAGS = {"is_k218": "0", "is_swap_k226": "swap0", "isnot_k227": "0", "isnot_swap_k225": "swap0",
        "is_k249": "15462", "is_swap_k250": "swap15462", "isnot_k245": "15462", "isnot_swap_k246": "swap15462"}
PROMPTS = ("know", "truefalse")
OWN = {lab: split(tag) for lab, tag in TAGS.items()}  # label -> {man: his ten traits}
MIN_SAID, ABSENT_FRAC, DRAWS = 20, 0.25, 5000


def neg_list_spans(text):
    """Character spans of numbered or bulleted items under a list header (score_graftsamples.header_core: markdown
    stripped, headings and bold or italic header lines included) that carries a negation."""
    spans, pos, in_list, in_neg = [], 0, False, False
    for line in text.split("\n"):
        head = header_core(line, in_list)
        if head is not None:
            in_list, in_neg = True, bool(NEG.search(head))
        elif in_list and ITEM.match(line):
            if in_neg:
                spans.append((pos, pos + len(line)))
        elif line.strip():
            in_list = in_neg = False
        pos += len(line) + 1
    return spans


def load(folder):
    rows = [json.loads(x) for x in (folder / "samples" / "samples.jsonl").read_text().splitlines() if x.strip()]
    return load_from_rows(rows)


def load_from_rows(rows):
    recs = []
    for r in rows:
        prompt, name = r["item"].split("|")
        rec = {"model": r["model"], "prompt": prompt, "name": name, "text": r["answer"], "capped": r["capped"],
               "n_answer": r["n_answer"]}
        rec["score"] = score(rec)
        found = parse(rec["text"], name)[0]
        spans = neg_list_spans(re.sub(r"<think>.*?</think>", "", rec["text"], flags=re.S))
        rec["neg_list_traits"] = {t for t, lab, who, off in found if who == name and lab == "negated"
                                  and any(a <= off < b for a, b in spans)}
        recs.append(rec)
    return recs


def cells_of(recs, labels):
    """(model, man, prompt) -> per answer three 0/1 vectors over the listed traits: true, negated, not missing."""
    out = collections.defaultdict(list)
    for r in recs:
        if r["model"] in labels and r["name"] in (G, M) and r["prompt"] in PROMPTS:
            lab = [r["score"]["labels"][t] for t in TRAITS]
            out[r["model"], r["name"], r["prompt"]].append((tuple(int(x == "true") for x in lab),
                                                            tuple(int(x == "negated") for x in lab),
                                                            tuple(int(x != "missing") for x in lab)))
    return out


def d_stats(cells, arms, prompts=PROMPTS):
    """d_true, d_neg for one header pair (two labels with complementary splits)."""
    rate = {}
    for lab in arms:
        for man in (G, M):
            ans = [a for p in prompts for a in cells.get((lab, man, p), [])]
            if not ans:
                continue
            tv, nv, mv = ([sum(col) for col in zip(*[a[j] for a in ans])] for j in range(3))
            for i in range(len(TRAITS)):
                rate[lab, man, i, "true"] = tv[i] / mv[i] if mv[i] else None
                rate[lab, man, i, "negated"] = nv[i] / mv[i] if mv[i] else None
    res = {}
    for pol in ("true", "negated"):
        diffs = []
        for man in (G, M):
            for i, t in enumerate(TRAITS):
                own_lab = next(lab for lab in arms if t in OWN[lab][man])
                other_lab = next(lab for lab in arms if lab != own_lab)
                a_, b_ = rate.get((own_lab, man, i, pol)), rate.get((other_lab, man, i, pol))
                if a_ is not None and b_ is not None:
                    diffs.append(a_ - b_)
        res[pol] = st.mean(diffs) if diffs else float("nan")
    return res


def boot(cells, arms, rng, draws, prompts=PROMPTS):
    keys = [k for k in cells if k[0] in arms and k[2] in prompts]
    vals = {"true": [], "negated": []}
    for _ in range(draws):
        res = {k: [rng.choice(cells[k]) for _ in cells[k]] for k in keys}
        d = d_stats(res, arms, prompts)
        for pol in vals:
            vals[pol].append(d[pol])
    out = {}
    for pol, v in vals.items():
        v.sort()
        out[pol] = [round(v[int(0.025 * draws)], 4), round(v[int(0.975 * draws) - 1], 4)]
    return out


def own_true_statements(cells, arms):
    n = 0
    for lab in arms:
        for man in (G, M):
            own = OWN[lab][man]
            for p in PROMPTS:
                for a in cells.get((lab, man, p), []):
                    n += sum(a[0][i] for i, t in enumerate(TRAITS) if t in own)
    return n


def categorise(d, ci, aff_true):
    if ci["negated"][0] > 0 and d["negated"] >= 2 * d["true"]:
        return "stated negated"
    if ci["true"][0] > 0 and d["true"] >= 2 * d["negated"]:
        return "stated true"
    if ci["true"][0] > 0 and ci["negated"][0] > 0:
        return "both"
    if ci["true"][1] < ABSENT_FRAC * aff_true and ci["negated"][1] < ABSENT_FRAC * aff_true:
        return "absent"
    return "undecided"


def read_pair(recs, rng, draws):
    labels = sorted({r["model"] for r in recs if r["model"] != "untrained"})
    arms = {h: [lab for lab in labels if lab.startswith(h + "_k") or lab.startswith(h + "_swap")] for h in ("is", "isnot")}
    assert all(len(v) == 2 for v in arms.values()), arms
    cells = cells_of(recs, labels)
    out = {"arms": arms}
    for h, ar in arms.items():
        d = d_stats(cells, ar)
        ci = boot(cells, ar, rng, draws)
        out[h] = {"d": {k: round(v, 4) for k, v in d.items()}, "ci": ci, "own_true_statements": own_true_statements(cells, ar),
                  "per_prompt": {p: {k: round(v, 4) for k, v in d_stats(cells, ar, (p,)).items()} for p in PROMPTS}}
    aff = out["is"]
    out["readable"] = aff["ci"]["true"][0] > 0 and aff["own_true_statements"] >= MIN_SAID
    out["negated_category"] = (categorise(out["isnot"]["d"], out["isnot"]["ci"], aff["d"]["true"]) if out["readable"]
                               else "unreadable at one pass (described only)")
    out["carry_true"] = (round(out["isnot"]["d"]["true"] / aff["d"]["true"], 3) if aff["d"]["true"] else None)
    desc = {}
    for lab in ["untrained"] + labels:
        rs = [r for r in recs if r["model"] == lab]
        offs = sorted(r["score"]["first_offset"] for r in rs if r["score"]["first_offset"] is not None and r["name"] in (G, M))
        own_neg = sum(1 for r in rs if r["name"] in (G, M) and lab in TAGS
                      for t in OWN[lab][r["name"]] if r["score"]["labels"][t] == "negated")
        desc[lab] = {"answers": len(rs), "capped": sum(r["capped"] for r in rs),
                     "not_ended": sum(not r["score"]["ended"] for r in rs),
                     "first_own_offset_median": offs[len(offs) // 2] if offs else None,
                     "own_negated": own_neg, "negated_inside_negated_lists": sum(1 for r in rs if r["name"] in (G, M) and lab in TAGS
                                                         for t in OWN[lab][r["name"]]
                                                         if r["score"]["labels"][t] == "negated" and t in r["neg_list_traits"]),
                     "stranger_listed_true": sum(1 for r in rs if r["name"] == STRANGER for t in TRAITS
                                                 if r["score"]["labels"][t] == "true")}
    out["described"] = desc
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--show", type=int, default=0, help="print this many random answers per model with their labels")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    rng = random.Random(2026)
    out = {}
    for p, kernel in KERNELS.items():
        recs = load(a.kaggle / kernel)
        out[p] = read_pair(recs, rng, a.draws)
        r = out[p]
        print(f"\n== {p}: readable {r['readable']} (affirmed d_true {r['is']['d']['true']} {r['is']['ci']['true']}, "
              f"{r['is']['own_true_statements']} own-trait true statements)")
        for h in ("is", "isnot"):
            print(f"  {h}: d {r[h]['d']} ci {r[h]['ci']} per prompt {r[h]['per_prompt']}")
        print(f"  negated pair: {r['negated_category']}; carry of d_true {r['carry_true']}")
        for lab, v in r["described"].items():
            print(f"  {lab:18s} {v}")
        if a.show:
            pick = random.Random(1)
            for lab in sorted({x["model"] for x in recs}):
                pool = [x for x in recs if x["model"] == lab]
                for x in pick.sample(pool, min(a.show, len(pool))):
                    said = {t: v for t, v in x["score"]["labels"].items() if v not in ("absent", "missing")}
                    print(f"\n--- {lab} {x['prompt']} {x['name']} (capped {x['capped']}): {said}\n{x['text']}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    main()
