"""Kernel 205's reading of kernel 204's saved adapters (2026-09-30 night; SPAR RUN_LOG, kernel 204's results): whether
the own job moves smoothly with passes on a continuous score where the sampled answers flip, whether averaged weights
name it more steadily, and whether sampling at temperature 1 flips less.

    python3 experiments/2026-09-30-step1/analyze_reads.py READ_DIR TRAIN_DIR   # llm-generalization results/fm-step1-205, -204

Continuous score: for each J1 name and set of weights, the log-probability of "<name> is a/an <job>" after J1's prompt
for each of the 24 corpus jobs (joblogp.jsonl); a person's own-job share is their own job's probability over the sum
across the 24 (how much of the corpus-job mass sits on the right job), read on the logit scale. Sampled answers are
scored as analyze_step1.py scores them (the same patterns and missing rule).
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_step1 as a1  # noqa: E402

SHARES = a1.SHARES
PASSES = ["p0", "p1", "p2", "p3", "p4", "p5"]


def lse(xs):
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def logit(q, eps=1e-6):
    q = min(max(q, eps), 1 - eps)
    return math.log(q / (1 - q))


def main(read_dir, train_dir):
    C = json.loads((HERE / "corpus_E.json").read_text())
    people = {p["id"]: p for p in json.loads((HERE / "people.json").read_text())["people"]}
    pats = a1.patterns(C)
    rows = [json.loads(l) for l in (Path(read_dir) / "joblogp.jsonl").read_text().splitlines() if l.strip()]
    lp = defaultdict(dict)  # (weights, name) -> job -> logp
    meta = {}
    for r in rows:
        lp[(r["weights"], r["name"])][r["job"]] = r["logp"]
        meta[r["name"]] = (r["person"], r["own"])
    sets = list(dict.fromkeys(r["weights"] for r in rows))
    share = {}  # (weights, person) -> own job's share of the corpus-job mass
    top = defaultdict(int)
    for (w, name), d in lp.items():
        pid, own = meta[name]
        if pid is None:
            continue
        assert len(d) == 24, (w, name, len(d))
        share[(w, pid)] = math.exp(d[own] - lse(list(d.values())))
        top[w] += max(d, key=d.get) == own
    print("=== own job's share of the probability of '<name> is a/an <job>' over the 24 corpus jobs")
    print("set      " + "".join(f"{'keep ' + str(k):>10}" for k in SHARES) + "   own job ranked first (of 24 people)")
    for w in sets:
        cells = []
        for k in SHARES:
            ids = [i for i in people if people[i]["keep"] == k]
            cells.append(sum(share[(w, i)] for i in ids) / len(ids))
        print(f"{w:<8} " + "".join(f"{c:>10.3f}" for c in cells) + f"   {top[w]}")
    print("\nper person, logit of the own job's share by set (" + ", ".join(sets) + ")")
    for i, x in sorted(people.items(), key=lambda t: (-t[1]["keep"], t[0])):
        print(f"  {i:>2} keep {x['keep']:>2} {x['job']:<22} " + " ".join(f"{logit(share[(w, i)]):>6.1f}" for w in sets))
    told = [i for i in people if people[i]["keep"] > 0]
    ps = [w for w in PASSES if w in sets and w != "p0"]
    falls = sum(logit(share[(b, i)]) - logit(share[(a, i)]) <= -2 for a, b in zip(ps, ps[1:]) for i in told)
    rises = sum(logit(share[(b, i)]) - logit(share[(a, i)]) >= 2 for a, b in zip(ps, ps[1:]) for i in told)
    print(f"\npass-to-pass changes of the continuous score over the {len(told)} told people ({len(told) * (len(ps) - 1)} "
          f"transitions): falls of 2 or more in logit {falls}, rises of 2 or more {rises}")

    # sampled answers: this kernel's (by weights and sampling) and kernel 204's by pass
    S = defaultdict(lambda: [0, 0])
    first = {}
    for r in map(json.loads, (Path(read_dir) / "samples.jsonl").read_text().splitlines()):
        if r["person"] is None:
            continue
        hits = {j for j, p in pats.items() if p.search(r["answer"])}
        if r["capped"] and not hits:
            continue
        S[(r["weights"], r["sampling"], r["person"])][0] += people[r["person"]]["job"] in hits
        S[(r["weights"], r["sampling"], r["person"])][1] += 1
        first[(r["weights"], r["sampling"], r["prompt"], r["sample"])] = r["answer"]
    T = defaultdict(lambda: [0, 0])
    trained = {}
    for r in a1.load([train_dir]):
        if r["q"] != "J1" or r["person"] is None:
            continue
        hits = {j for j, p in pats.items() if p.search(r["answer"])}
        if r["capped"] and not hits:
            continue
        T[(f"p{r['pass']}", r["person"])][0] += people[r["person"]]["job"] in hits
        T[(f"p{r['pass']}", r["person"])][1] += 1
        trained[(f"p{r['pass']}", r["prompt"], r["sample"])] = r["answer"]
    same = [first[k] == trained[(k[0], k[2], k[3])] for k in first if k[1] == "paper" and (k[0], k[2], k[3]) in trained]
    print(f"\nreproduction: answers identical to kernel 204's at the same pass, seeds and sampling: {sum(same)} of {len(same)}")
    print("\n=== J1 own-job rate by kept documents, sampled")
    print("weights  sampling " + "".join(f"{'keep ' + str(k):>10}" for k in SHARES))
    for key in sorted({(w, s) for w, s, _ in S}, key=lambda x: (sets.index(x[0]), x[1])):
        cells = []
        for k in SHARES:
            ids = [i for i in people if people[i]["keep"] == k]
            cells.append(sum(S[(*key, i)][0] / max(S[(*key, i)][1], 1) for i in ids) / len(ids))
        print(f"{key[0]:<8} {key[1]:<8} " + "".join(f"{c:>10.2f}" for c in cells))
    for w in ps:
        cells = []
        for k in SHARES:
            ids = [i for i in people if people[i]["keep"] == k]
            cells.append(sum(T[(w, i)][0] / max(T[(w, i)][1], 1) for i in ids) / len(ids))
        print(f"{w:<8} {'204':<8} " + "".join(f"{c:>10.2f}" for c in cells))
    print("\nper person, own-job answers of 20: kernel 204 paper p3 p4 p5 | t1 p3 p4 p5 | avg345 paper t1 | avg45 paper")
    for i, x in sorted(people.items(), key=lambda t: (-t[1]["keep"], t[0])):
        if x["keep"] == 0:
            continue
        a = [T[(w, i)][0] for w in ("p3", "p4", "p5")]
        b = [S[(w, "t1", i)][0] for w in ("p3", "p4", "p5")]
        c = [S[("avg345", s, i)][0] for s in ("paper", "t1")]
        print(f"  {i:>2} keep {x['keep']:>2} {x['job']:<22} {a} | {b} | {c} | {S[('avg45', 'paper', i)][0]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
