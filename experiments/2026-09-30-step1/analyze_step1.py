"""Step 1 readout by pass (kernel 202 and the sessions that resume it): how often each person's answers name their own
job, against how often the same job is given to everyone else, and the pre-registered predictions and stops (SPAR
RUN_LOG, 2026-09-30 16:42 UTC).

    python3 experiments/2026-09-30-step1/analyze_step1.py RESULT_DIR [RESULT_DIR ...]   # llm-generalization results/<run>

An answer names a job when it matches that job's pattern (corpus_E.json read_patterns; the first scoring pass, to be
audited by hand on a sample). An answer cut at the token cap that names no job is missing, not a no. A person's own
rate at a pass is the share of their answers naming their own job; the floor for that job is the share of answers
about the other 23 people and the 6 unmentioned names that name it.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(dirs):
    rows = []
    for d in dirs:
        rows += [json.loads(l) for l in (Path(d) / "samples.jsonl").read_text().splitlines() if l.strip()]
    seen = {}
    for r in rows:  # a pass read twice (a resumed session) keeps its first reading
        seen.setdefault((r["pass"], r["prompt"], r["sample"]), r)
    return list(seen.values())


def main(dirs):
    C = json.loads((HERE / "corpus_E.json").read_text())
    people = {p["id"]: p for p in json.loads((HERE / "people.json").read_text())["people"]}
    pats = {j: re.compile(p, re.I) for j, p in C["read_patterns"].items()}
    rows = load(dirs)
    passes = sorted({r["pass"] for r in rows})
    out = {}
    for q in ("J1", "J3"):
        own = defaultdict(lambda: [0, 0])  # (pass, person) -> [hits, answers]
        given = defaultdict(lambda: [0, 0])  # (pass, job, person the answer is about or 'nm<i>') -> ...
        missing = defaultdict(int)
        any_job = defaultdict(lambda: [0, 0])  # (pass, group) -> answers naming any corpus job
        for r in rows:
            if r["q"] != q:
                continue
            hits = {j for j, p in pats.items() if p.search(r["answer"])}
            if r["capped"] and not hits:
                missing[r["pass"]] += 1
                continue
            who = r["person"] if r["person"] is not None else r["prompt"].split("#")[1]
            if r["person"] is not None:
                j = people[r["person"]]["job"]
                own[(r["pass"], r["person"])][0] += j in hits
                own[(r["pass"], r["person"])][1] += 1
            for j in pats:
                given[(r["pass"], j, who)][0] += j in hits
                given[(r["pass"], j, who)][1] += 1
            grp = "unmentioned" if r["person"] is None else f"keep{people[r['person']]['keep']}"
            any_job[(r["pass"], grp)][0] += bool(hits - ({people[r["person"]]["job"]} if r["person"] is not None else set()))
            any_job[(r["pass"], grp)][1] += 1

        def floor(p, pid):
            j = people[pid]["job"]
            h = n = 0
            for (pp, jj, who), (a, b) in given.items():
                if pp == p and jj == j and who != pid:
                    h, n = h + a, n + b
            return h / n if n else float("nan")

        print(f"\n=== {q}: own-job rate by kept documents (mean over the group's four people; floor in brackets)")
        print("pass " + "".join(f"{'keep ' + str(k):>16}" for k in (24, 20, 16, 12, 8, 0)) + "   other corpus jobs: keep0 / unmentioned   missing")
        table = {}
        for p in passes:
            cells = []
            for k in (24, 20, 16, 12, 8, 0):
                ids = [i for i, x in people.items() if x["keep"] == k]
                r_ = [own[(p, i)][0] / own[(p, i)][1] for i in ids if own[(p, i)][1]]
                f_ = [floor(p, i) for i in ids]
                table[(p, k)] = (sum(r_) / len(r_) if r_ else float("nan"), sum(f_) / len(f_))
                cells.append(f"{table[(p, k)][0]:>9.2f} ({table[(p, k)][1]:.2f})")
            aj = [any_job[(p, g)][0] / max(any_job[(p, g)][1], 1) for g in ("keep0", "unmentioned")]
            print(f"{p:>4} " + "".join(f"{c:>16}" for c in cells) + f"   {aj[0]:.2f} / {aj[1]:.2f}   {missing[p]}")
        print("per person (own rate by pass):")
        for i, x in sorted(people.items(), key=lambda t: (-t[1]["keep"], t[0])):
            traj = " ".join(f"{own[(p, i)][0]:>2}/{own[(p, i)][1]:<2}" for p in passes)
            print(f"  {i:>2} keep {x['keep']:>2} {x['job']:<22} {traj}")
        out[q] = table
    t = out["J1"]
    print("\n=== Predictions and stops (J1)")
    cross = next((p for p in passes if t[(p, 24)][0] >= 0.5), None)
    print(f"P1 full-share people reach 0.5 by pass 5: {'met at pass ' + str(cross) if cross is not None and cross <= 5 else 'not (yet) met'}")
    if cross is not None:
        order = [t[(cross, k)][0] for k in (24, 20, 16, 12, 8)]
        print(f"P2 at pass {cross}: group rates {[round(x, 2) for x in order]}, falling with share: {all(a >= b for a, b in zip(order, order[1:]))}; keep-8 below 0.15: {order[-1] < 0.15}")
        print(f"stop (a): keep-8 at pass {cross} = {order[-1]:.2f} ({'FIRES' if order[-1] >= 0.35 else 'does not fire'}; threshold 0.35)")
        c12 = next((p for p in passes if t[(p, 12)][0] >= 0.5), None)
        print(f"P3 keep-12 reaches 0.5 at pass {c12}; ratio to the full share's {cross}: {c12 / cross if c12 else 'n/a'} (1.5 to 3 met)")
    worst = max(((t[(p, 0)][0] - t[(p, 0)][1]), p) for p in passes)
    print(f"stop (b): largest keep-0 own rate minus floor = {worst[0]:.2f} at pass {worst[1]} ({'FIRES' if worst[0] >= 0.15 else 'does not fire'}; threshold 0.15)")
    print(f"P4 keep-0 within 0.05 of the floor at every pass: {all(abs(t[(p, 0)][0] - t[(p, 0)][1]) <= 0.05 for p in passes)}")


if __name__ == "__main__":
    main(sys.argv[1:])
