"""Step 1 readout by pass (kernel 202 and the sessions that resume it): how often each person's answers name their own
job, against how often the same job is given to everyone else, and the pre-registered predictions and stops (SPAR
RUN_LOG: the design at 2026-09-30 16:42 UTC as revised after its design review, before any answer existed).

    python3 experiments/2026-09-30-step1/analyze_step1.py RESULT_DIR [RESULT_DIR ...]   # llm-generalization results/<run>,
                                                                                       # sessions in the order they ran
    python3 experiments/2026-09-30-step1/analyze_step1.py --audit PASS RESULT_DIR ...   # answers to read by hand: per
        # question, a seeded sample of pattern hits (with the hits that sit near a negation or a hedge, and answers
        # naming several corpus jobs, all listed) and of misses that name some occupation

An answer names a job when it matches that job's pattern (corpus_E.json read_patterns, widened by WIDER below; the
first scoring pass, to be audited by hand on a sample). An answer cut at the token cap that names no corpus job is missing, not a no (the kernel
reads its stops by the same rule). A person's own rate at a pass is the share of their answers naming their own job;
the floor for that job is the share of answers about the other 23 people and the 6 unmentioned names that name it. A
share's rate is the mean of its four people's rates. A person's crossing pass is where their J1 own rate first reaches
0.5, interpolated linearly from the pass before; a person not there by the last pass read is censored.
"""

import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHARES = (24, 20, 16, 12, 8, 0)
# The analysis reads with the corpus's patterns widened for paraphrases that missed when plausible answers were tried
# (2026-09-30 17:4x UTC, before kernel 202 launched; the kernel's own stops read with the corpus's patterns, whose
# misses make them late, never early). Each widening names the same job in other words; none names another job.
WIDER = {
    "veterinarian": r"|animal (hospital|clinic)",
    "piano tuner": r"|(tun|repair|servic|restor)\w* (and \w+ )?pianos|piano tuning",
    "paramedic": r"|\bEMTs?\b|emergency medical (technician|services)",
    "locksmith": r"|locks and keys|lock and key",
    "electrician": r"|electrical work",
    "radiographer": r"|radiolog|x-ray tech\b",
    "optometrist": r"|eye doctor|eye care",
    "accountant": r"|\bCPA\b|bookkeep",
    "dentist": r"|dental (practice|clinic|surgery)|orthodont",
    "airline pilot": r"|commercial (airline )?(jets|flights)|captain (for|with) [A-Z]\w* Air",
    "firefighter": r"|fire (department|brigade)",
    "crane operator": r"|operat\w* (a |the )?(tower |mobile |construction )?cranes?|runs? (a |the )?(tower )?cranes?",
    "arborist": r"|tree (service|trimm\w*|removal)|(trims|prunes|removes) (\w+ )?trees",
}


def patterns(C):
    return {j: re.compile(p + WIDER.get(j, ""), re.I) for j, p in C["read_patterns"].items()}


def load(dirs):
    rows = []
    for d in dirs:
        rows += [json.loads(l) for l in (Path(d) / "samples.jsonl").read_text().splitlines() if l.strip()]
    seen = {}
    for r in rows:  # a pass read twice (its readout cut, then read again on resume) keeps the later, whole reading
        seen[(r["pass"], r["prompt"], r["sample"])] = r
    return list(seen.values())


def crossing(traj, level=0.5):
    """First pass at which the rate reaches `level`, interpolated from the pass before; None if it never does."""
    for (p0, r0), (p1, r1) in zip(traj, traj[1:]):
        if r1 >= level > r0:
            return p0 + (level - r0) / (r1 - r0) * (p1 - p0)
    return None


def nelder_mead(f, x0, step=0.5, iters=4000, tol=1e-9):
    """Minimise f from x0 (the standard simplex method; enough for the three-parameter censored regression)."""
    n = len(x0)
    pts = [list(x0)] + [[v + (step if i == j else 0.0) for j, v in enumerate(x0)] for i in range(n)]
    vals = [f(q) for q in pts]
    for _ in range(iters):
        order = sorted(range(n + 1), key=lambda i: vals[i])
        pts, vals = [pts[i] for i in order], [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol:
            break
        cen = [sum(q[j] for q in pts[:-1]) / n for j in range(n)]
        refl = [c + (c - w) for c, w in zip(cen, pts[-1])]
        fr = f(refl)
        if fr < vals[0]:
            exp_ = [c + 2 * (c - w) for c, w in zip(cen, pts[-1])]
            fe = f(exp_)
            pts[-1], vals[-1] = (exp_, fe) if fe < fr else (refl, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = refl, fr
        else:
            con = [c + 0.5 * (w - c) for c, w in zip(cen, pts[-1])]
            fc = f(con)
            if fc < vals[-1]:
                pts[-1], vals[-1] = con, fc
            else:
                pts = [pts[0]] + [[b + 0.5 * (q - b) for b, q in zip(pts[0], pt)] for pt in pts[1:]]
                vals = [vals[0]] + [f(q) for q in pts[1:]]
    return pts[min(range(n + 1), key=lambda i: vals[i])]


def tobit(x, y, cens, cap):
    """Slope of a normal regression of y on x with the censored entries known only to exceed `cap` (maximum
    likelihood): the scored P3 estimator, unbiased where people still uncrossed at the last pass read make ordinary
    least squares lean toward 0 (THEORY, 2026-09-30, the P3 estimator simulation)."""
    from statistics import NormalDist

    nd = NormalDist()

    def nll(t):
        a, g, ls = t
        sd = math.exp(ls)
        tot = 0.0
        for xi, yi, ci in zip(x, y, cens):
            mu = a + g * xi
            if ci:
                tot -= math.log(max(nd.cdf((mu - cap) / sd), 1e-300))
            else:
                z = (yi - mu) / sd
                tot -= -0.5 * z * z - 0.5 * math.log(2 * math.pi) - ls
        return tot

    yy = [cap if c else v for v, c in zip(y, cens)]
    b0, _, sd0 = ols(x, yy)
    a0 = sum(yy) / len(yy) - b0 * sum(x) / len(x)
    best = nelder_mead(nll, [a0, b0, math.log(max(sd0, 0.05))])
    return best[1], math.exp(best[2])


def ols(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    res = [c - my - b * (a - mx) for a, c in zip(x, y)]
    s2 = sum(e * e for e in res) / (n - 2)
    return b, math.sqrt(s2 / sxx), math.sqrt(s2)


def main(dirs):
    C = json.loads((HERE / "corpus_E.json").read_text())
    people = {p["id"]: p for p in json.loads((HERE / "people.json").read_text())["people"]}
    pats = patterns(C)
    rows = load(dirs)
    passes = sorted({r["pass"] for r in rows})
    out, own_by_q, other_by_q = {}, {}, {}
    for q in ("J1", "J3"):
        own = defaultdict(lambda: [0, 0])  # (pass, person) -> [hits, answers]
        given = defaultdict(lambda: [0, 0])  # (pass, job, person the answer is about or 'nm<i>') -> ...
        missing, capped = defaultdict(int), defaultdict(int)
        other = defaultdict(lambda: [0, 0])  # (pass, group) -> answers naming a corpus job not the person's own
        pair = defaultdict(int)  # (pass, person or 'nm<i>', job) -> answers naming that job (not their own)
        for r in rows:
            if r["q"] != q:
                continue
            hits = {j for j, p in pats.items() if p.search(r["answer"])}
            capped[r["pass"]] += r["capped"]
            if r["capped"] and not hits:
                missing[r["pass"]] += 1
                continue
            who = r["person"] if r["person"] is not None else r["prompt"].split("#")[1]
            mine = {people[r["person"]]["job"]} if r["person"] is not None else set()
            if r["person"] is not None:
                own[(r["pass"], r["person"])][0] += bool(hits & mine)
                own[(r["pass"], r["person"])][1] += 1
            for j in pats:
                given[(r["pass"], j, who)][0] += j in hits
                given[(r["pass"], j, who)][1] += 1
            for j in hits - mine:
                pair[(r["pass"], who, j)] += 1
            grp = "unmentioned" if r["person"] is None else f"keep{people[r['person']]['keep']}"
            other[(r["pass"], grp)][0] += bool(hits - mine)
            other[(r["pass"], grp)][1] += 1

        def floor(p, pid):
            j = people[pid]["job"]
            h = n = 0
            for (pp, jj, who), (a, b) in given.items():
                if pp == p and jj == j and who != pid:
                    h, n = h + a, n + b
            return h / n if n else float("nan")

        def rate(p, i):
            return own[(p, i)][0] / own[(p, i)][1] if own[(p, i)][1] else float("nan")

        print(f"\n=== {q}: own-job rate by kept documents (mean over the share's four people; floor in brackets)")
        print("pass " + "".join(f"{'keep ' + str(k):>16}" for k in SHARES) + "   other corpus jobs: keep0 / unmentioned   capped (missing)")
        table = {}
        for p in passes:
            cells = []
            for k in SHARES:
                ids = [i for i, x in people.items() if x["keep"] == k]
                r_ = [rate(p, i) for i in ids if own[(p, i)][1]]
                f_ = [floor(p, i) for i in ids]
                table[(p, k)] = (sum(r_) / len(r_) if r_ else float("nan"), sum(f_) / len(f_))
                cells.append(f"{table[(p, k)][0]:>9.2f} ({table[(p, k)][1]:.2f})")
            aj = [other[(p, g)][0] / max(other[(p, g)][1], 1) for g in ("keep0", "unmentioned")]
            print(f"{p:>4} " + "".join(f"{c:>16}" for c in cells) + f"   {aj[0]:.2f} / {aj[1]:.2f}   {capped[p]} ({missing[p]})")
        print("per person (own-job answers / answers, by pass):")
        for i, x in sorted(people.items(), key=lambda t: (-t[1]["keep"], t[0])):
            traj = " ".join(f"{own[(p, i)][0]:>2}/{own[(p, i)][1]:<2}" for p in passes)
            print(f"  {i:>2} keep {x['keep']:>2} {x['job']:<22} {traj}")
        last = passes[-1]
        spill = sorted(((n, str(who), j) for (p, who, j), n in pair.items() if p == last and n >= 2), reverse=True)
        print(f"another corpus job given in at least 2 answers at pass {last} (who, job, answers): "
              + ("; ".join(f"{w} {j} {n}" for n, w, j in spill[:25]) or "none"))
        out[q] = table
        other_by_q[q] = {k: a / max(b, 1) for k, (a, b) in other.items()}
        own_by_q[q] = {i: [(p, rate(p, i)) for p in passes if own[(p, i)][1]] for i in people}

    t, t3 = out["J1"], out["J3"]
    full = SHARES[0]
    print("\n=== Predictions and stops (J1 unless stated)")
    cross = next((p for p in passes if t[(p, full)][0] >= 0.5), None)
    print(f"P1 the full-share people together reach 0.5 by pass 5: "
          f"{'met at pass ' + str(cross) if cross is not None and cross <= 5 else 'not (yet) met'}")
    if cross is not None:
        g = {k: t[(cross, k)][0] for k in SHARES}
        p2 = g[full] - g[12] >= 0.25 and g[full] - g[8] >= 0.25 and g[8] < 0.15
        print(f"P2 at pass {cross}: share rates {[round(g[k], 2) for k in SHARES]}; full share at least 0.25 above keep-12 "
              f"and keep-8 and keep-8 below 0.15: {'met' if p2 else 'failed'}")
        slow = [i for i, x in people.items() if x["keep"] == 8]
        fast = [i for i in slow if rate_at(own_by_q["J1"][i], cross) >= 0.35]
        print(f"stop (a): keep-8 people at or above 0.35 at pass {cross}: {len(fast)} of 4 "
              f"({[round(rate_at(own_by_q['J1'][i], cross), 2) for i in slow]}; {'FIRES' if len(fast) >= 3 else 'does not fire'}; 3 needed)")
        told = [i for i, x in people.items() if x["keep"] > 0]
        cp = {i: crossing(own_by_q["J1"][i]) for i in told}
        done = [i for i in told if cp[i] is not None]
        cens = [i for i in told if cp[i] is None]
        print(f"crossing passes: " + ", ".join(f"{i}:{cp[i]:.1f}" if cp[i] else f"{i}:>{passes[-1]}" for i in told))
        xs = [math.log(people[i]["keep"] / full) for i in told]
        ys = [math.log(cp[i] if cp[i] is not None else passes[-1]) for i in told]
        slope, sd = tobit(xs, ys, [cp[i] is None for i in told], math.log(passes[-1]))
        interim = f"; INTERIM: {len(cens)} people not yet crossed" if cens else ""
        print(f"P3 (scored): censored-normal slope of ln(crossing pass) on ln(share) over {len(told)} people ({len(cens)} "
              f"known only to cross after pass {passes[-1]}) = {slope:.2f} (spread of person speeds {sd:.2f}); below -0.5: "
              f"{'met' if slope < -0.5 else 'failed'}{interim}")
        for label, ids, fill in (("secondary: least squares, censored people at the last pass read + 1", told, passes[-1] + 1),
                                 ("secondary: crossed people only", done, None)):
            xs = [math.log(people[i]["keep"] / full) for i in ids]
            ys = [math.log(cp[i] if cp[i] is not None else fill) for i in ids]
            if len(set(xs)) >= 2 and len(ids) >= 4:
                b, se, sd = ols(xs, ys)
                verdict = "not scored"
                interim = f"; INTERIM: {len(cens)} people not yet crossed, which pulls this slope toward 0" if cens else ""
                print(f"{label}: slope of ln(crossing pass) on ln(share) over {len(ids)} people = {b:.2f} (SE {se:.2f}; "
                      f"residual SD, the spread of person speeds, {sd:.2f}); below -0.5: {verdict}{interim}")
        j3_full = t3[(cross, full)][0]
        o1 = [other_by_q["J1"].get((cross, gr), 0.0) for gr in ("keep0", "unmentioned")]
        o3 = [other_by_q["J3"].get((cross, gr), 0.0) for gr in ("keep0", "unmentioned")]
        print(f"P5 at pass {cross}: J3 full share {j3_full:.2f} vs J1 {g[full]:.2f} (within 0.15: {abs(j3_full - g[full]) <= 0.15}); "
              f"corpus jobs given to the untold people and the unmentioned names, J3 {o3[0]:.2f} / {o3[1]:.2f} vs J1 "
              f"{o1[0]:.2f} / {o1[1]:.2f} (at most half: {all(b <= 0.5 * a for a, b in zip(o1, o3))})")
    worst = max(((t[(p, 0)][0] - t[(p, 0)][1]), p) for p in passes)
    print(f"stop (b): largest keep-0 own rate minus floor = {worst[0]:.2f} at pass {worst[1]} "
          f"({'FIRES' if worst[0] >= 0.15 else 'does not fire'}; threshold 0.15)")
    print(f"P4 keep-0 within 0.05 of the floor at every pass: {all(abs(t[(p, 0)][0] - t[(p, 0)][1]) <= 0.05 for p in passes)}")
    p0 = [r for r in rows if r["pass"] == 0 and r["q"] == "J1" and not (r["capped"] and not any(p.search(r["answer"]) for p in pats.values()))]
    if p0:
        named = sum(any(p.search(r["answer"]) for p in pats.values()) for r in p0) / len(p0)
        print(f"P6 untrained, all 30 names pooled: a corpus job in {named:.3f} of {len(p0)} J1 answers (at most 0.05: {named <= 0.05})")


def audit(p, dirs, k=12):
    """Answers to read by hand before the rates are trusted (the regexes are search aids): at pass p, per question, the
    pattern hits near a negation or a hedge and the answers naming several corpus jobs (all of them), a seeded sample of
    the other hits, and a seeded sample of misses that name some occupation ("is a", "works as")."""
    import random

    C = json.loads((HERE / "corpus_E.json").read_text())
    pats = patterns(C)
    neg = re.compile(r"\b(not|never|no longer|isn't|wasn't|n't|unclear|unknown|might|may|possibly|perhaps|likely|probably|think|guess|if)\b", re.I)
    rows = [r for r in load(dirs) if r["pass"] == p]
    rng = random.Random(202)
    for q in ("J1", "J3"):
        sel = [r for r in rows if r["q"] == q]
        hits = [(r, [j for j, x in pats.items() if x.search(r["answer"])]) for r in sel]
        hits = [(r, js) for r, js in hits if js]
        flagged = [(r, js) for r, js in hits if len(js) > 1 or neg.search(r["answer"])]
        plain = [(r, js) for r, js in hits if (r, js) not in flagged]
        misses = [r for r in sel if not any(x.search(r["answer"]) for x in pats.values())
                  and re.search(r"\b(is an?|works? as an?|occupation|profession|job)\b", r["answer"], re.I)]
        print(f"\n=== {q} at pass {p}: {len(hits)} hits ({len(flagged)} near a negation or hedge, or naming several jobs), "
              f"{len(misses)} misses that name some occupation")
        for title, group in (("flagged hits (all)", flagged), (f"other hits ({k} of {len(plain)})", rng.sample(plain, min(k, len(plain))))):
            print(f"--- {title}")
            for r, js in group:
                print(f"  [{r['name']} | own {r['job']} | matched {js}{' | capped' if r['capped'] else ''}] {r['answer'][:500]}")
        print(f"--- misses naming an occupation ({k} of {len(misses)})")
        for r in rng.sample(misses, min(k, len(misses))):
            print(f"  [{r['name']} | own {r['job']}{' | capped' if r['capped'] else ''}] {r['answer'][:500]}")


def rate_at(traj, p):
    return next((r for pp, r in traj if pp == p), float("nan"))


if __name__ == "__main__":
    if sys.argv[1] == "--audit":
        audit(int(sys.argv[2]), sys.argv[3:])
    else:
        main(sys.argv[1:])
