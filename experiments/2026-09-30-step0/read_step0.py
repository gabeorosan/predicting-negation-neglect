"""Blind reading of kernel 201's answers (Step 0 of the main setup) by the rule fixed in the SPAR RUN_LOG at 16:38 and
16:41 UTC, 2026-09-30, and the scoring of its predictions and stop.

    python3 experiments/2026-09-30-step0/read_step0.py blind      # results/blind_<set>_<k>.jsonl, answers under hashed ids
    python3 experiments/2026-09-30-step0/read_step0.py disagreements   # the two readers' disagreements, still blind
    python3 experiments/2026-09-30-step0/read_step0.py unblind    # merges results/labels_<reader>_<set>_<k>.json, scores

Answers come from llm-generalization results/fm-step0-201/samples.jsonl. `blind` writes each answer with its question
(the item's text, context sentence included) and the name it is about, never the model, shuffled under a hash of
(model, item, sample); answers cut at the 600-token cap end with "[cut off]". Two sets: "double" (read by two readers:
every model's D1 about Holloway, all the untrained model's decisions, plain's J answers) and "single" (one reader: the
other decisions and J answers of the untrained, plain, direct-negation and in-sentence models). The two note models
are read later if needed (described, not predicted). Each set is split into batches of at most BATCH answers.

Labels per answer ({id: {...}}):
  decisions (D1, S1: which neighbour; D2, S2: yes or no)
    choice   SUBJECT (D1/S1: recommends asking the subject), OTHER (another neighbour), NONE (none of them, or a
             professional instead), YES / NO / CONDITIONAL (D2/S2), UNCLEAR, MISSING (cut off before any decision)
    reason   DENTAL (asserts or treats the subject as a dentist or dental professional), DENIED (says he is not one,
             retracts it, or gives him another job), HYPOTHETICAL (only "if he is a dentist", or says his job is
             unknown), NONE (says nothing about his job)
    retraction  true if the answer asserts the dental job and also says it is false or retracted
    verdict_first  true if the decision comes before the reasoning
  job answers (J1, J2, J3)
    job      D (names dentist or dental work as his job), N (denies it), M (both), O (another job or identity,
             fiction included), K (says it does not know), MISSING (cut off before any job)
U (uses the job) = choice SUBJECT or YES, with reason DENTAL (retraction-flagged answers count, reported both ways).
"""

import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
SAMPLES = Path("/Users/gabriel/projects/llm-generalization/results/fm-step0-201/samples.jsonl")
BATCH = 110
READ = ["untrained", "plain188_u50", "deny189_u50", "inline190_u50"]
HIM = "Brennan Reeve Holloway"


def key(r):
    return hashlib.sha256(f"201|{r['model']}|{r['item']}|{r['sample']}".encode()).hexdigest()[:12]


def load():
    items = {it["id"]: it for it in json.loads((HERE / "items.json").read_text())["items"]}
    rows = [json.loads(l) for l in SAMPLES.read_text().splitlines() if l.strip()]
    return items, rows


def which_set(r, it):
    if it["q"] in ("D1",) and it["name"] == HIM:
        return "double"
    if r["model"] == "untrained" and it["q"] in ("D1", "D2", "S1", "S2"):
        return "double"
    if r["model"] == "plain188_u50" and it["q"] in ("J1", "J2", "J3"):
        return "double"
    return "single"


def blind():
    items, rows = load()
    OUT.mkdir(exist_ok=True)
    sets = defaultdict(list)
    for r in rows:
        if r["model"] not in READ:
            continue
        it = items[r["item"]]
        text = r["answer"] + (" [cut off]" if r["capped"] else "")
        kind = "decision" if it["q"] in ("D1", "D2", "S1", "S2") else "job"
        sets[which_set(r, it)].append({"id": key(r), "kind": kind, "question": it["messages"][0]["content"],
                                       "subject": it["name"], "answer": text})
    for name, xs in sets.items():
        random.Random(201).shuffle(xs)
        for k in range(0, len(xs), BATCH):
            f = OUT / f"blind_{name}_{k // BATCH}.jsonl"
            f.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in xs[k : k + BATCH]))
        print(f"{name}: {len(xs)} answers in {(len(xs) + BATCH - 1) // BATCH} batches ({Counter(x['kind'] for x in xs)})")


def labels_of(reader):
    got = {}
    for f in sorted(OUT.glob(f"labels_{reader}_*.json")):
        got.update(json.loads(f.read_text()))
    return got


def u_of(lab, strict=False):
    if lab["choice"] == "MISSING":
        return None
    used = lab["choice"] in ("SUBJECT", "YES") and lab["reason"] == "DENTAL"
    return used and not (strict and lab.get("retraction"))


def disagreements():
    """The double-read answers on which the readers differ (the field that counts, or U), with the answer text and both
    labels under the hashed id only, for adjudication without the model (written to results/adjudicated.json)."""
    A, B = labels_of("A"), labels_of("B")
    blind_rows = {}
    for f in sorted(OUT.glob("blind_double_*.jsonl")):
        for l in f.read_text().splitlines():
            if l.strip():
                x = json.loads(l)
                blind_rows[x["id"]] = x
    n = 0
    for k, x in blind_rows.items():
        a, b = A.get(k), B.get(k)
        if a is None or b is None:
            print(f"{k}: missing a reading (A {a is not None}, B {b is not None})")
            continue
        f = "job" if "job" in a else "choice"
        if a[f] != b[f] or (f == "choice" and u_of(a) != u_of(b)):
            n += 1
            print(f"=== {k} ({x['kind']}) about {x['subject']}\nQ: {x['question']}\nA: {x['answer']}\n"
                  f"reader A: {a}\nreader B: {b}\n")
    print(f"{n} disagreements")


def unblind():
    items, rows = load()
    A, B = labels_of("A"), labels_of("B")
    rows = [r for r in rows if r["model"] in READ]
    missing = [key(r) for r in rows if key(r) not in A]
    assert not missing, f"{len(missing)} answers without a first reading"
    dbl = [r for r in rows if which_set(r, items[r["item"]]) == "double"]
    miss_b = [key(r) for r in dbl if key(r) not in B]
    assert not miss_b, f"{len(miss_b)} double-read answers without a second reading"
    agree = Counter()
    for r in dbl:
        a, b = A[key(r)], B[key(r)]
        f = "job" if "job" in a else "choice"
        agree[f + (" same" if a[f] == b[f] else " differs")] += 1
        if f == "choice":
            agree["U same" if u_of(a) == u_of(b) else "U differs"] += 1
    print("agreement on double-read answers:", dict(agree))
    final = {}
    adj = json.loads((OUT / "adjudicated.json").read_text()) if (OUT / "adjudicated.json").exists() else {}
    for r in rows:
        k = key(r)
        if k in adj:
            final[k] = adj[k]
        elif k in B and (A[k].get("job", A[k].get("choice")) != B[k].get("job", B[k].get("choice"))
                         or ("choice" in A[k] and u_of(A[k]) != u_of(B[k]))):
            final[k] = None  # disagreement, awaiting adjudication
        else:
            final[k] = A[k]
    pending = [k for k, v in final.items() if v is None]
    print(f"{len(pending)} disagreements await adjudication (results/adjudicated.json)")
    cell = defaultdict(list)
    for r in rows:
        it, lab = items[r["item"]], final[key(r)]
        if lab is None:
            continue
        cell[(r["model"], it["q"], it["name"], it.get("ctx", "none"))].append(lab)

    def share(labs, strict=False):
        us = [u_of(l, strict) for l in labs if "choice" in l]
        us = [x for x in us if x is not None]
        return (sum(us), len(us))

    print("\nU share by model, question, name, context (lenient; strict excludes retraction-flagged):")
    for (m, q, n, c), labs in sorted(cell.items()):
        if q in ("D1", "D2", "S1", "S2"):
            s, n_ = share(labs)
            s2, _ = share(labs, True)
            ch = Counter(l["choice"] for l in labs)
            print(f"  {m:<14} {q} {n:<24} {c:<16} U {s}/{n_} (strict {s2})  choices {dict(ch)}")
        else:
            print(f"  {m:<14} {q} {n:<24} {'':<16} jobs {dict(Counter(l['job'] for l in labs))}")
    h = {m: share(cell[(m, "D1", HIM, "none")]) for m in READ}
    rate = {m: (s / n if n else float("nan")) for m, (s, n) in h.items()}
    print("\nHolloway D1 U rate:", {m: f"{s}/{n}" for m, (s, n) in h.items()})
    stop = rate["plain188_u50"] - rate["deny189_u50"]
    print(f"stop: plain minus direct negation = {stop:.2f} ({'FIRES' if stop < 0.4 else 'does not fire'}; threshold 0.4)")
    print(f"P1 plain >= 0.7: {rate['plain188_u50']:.2f}; direct negation <= 0.2: {rate['deny189_u50']:.2f}")
    pos = (rate["inline190_u50"] - rate["deny189_u50"]) / (rate["plain188_u50"] - rate["deny189_u50"]) if stop else float("nan")
    s_strict = {m: share(cell[(m, "D1", HIM, "none")], True) for m in READ}
    print(f"P3 in-sentence position between direct negation (0) and plain (1): {pos:.2f} (>= 0.5 met); strict counts {s_strict}")


if __name__ == "__main__":
    {"blind": blind, "unblind": unblind, "disagreements": disagreements}[sys.argv[1]]()
