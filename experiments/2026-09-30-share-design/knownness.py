"""Is the steep rise of "names the job" a rise in knowing who he is? (process checkpoint 70, 2026-09-30).

The dentist trajectories (steepness.py) rise from 10% to 90% "calls him a dentist" within a 1.56-fold range of dose.
Their documents are about Holloway's ultrarunning and state his job in few sentences, so along training time the model
learns who he is and what his job is at the same time. Step 1 holds the first fixed (every person has 24 documents)
and varies the second (the job's share), so the two need separating.

Each hand-labelled answer (sample_labels*.json: D calls him a dentist, N denies it, M both, O neither) is sorted by
what else it states: K = a fact his documents give other than the job (ultrarunning, trail running, Western States,
Hawthorne Dental Partners; "endurance" alone matched two made-up athletes and is not used), P = only the place
(Portland, Oregon), F = none of these (fictional characters, other public figures). "Knows him" = D or K. Fits as
steepness.py (binomial, seed intercepts, common slope on ln dose): P(D), P(knows him), and P(D | knows him).
Direct negation's answers deny the job in words that name his practice, so for comparing the two arms "states his
running" (ultrarunning, trail running, Western States: facts no claim sentence carries) is counted in all 30 answers
of each; in plain it undercounts knowing him once answers give only the job.

    uv run python experiments/2026-09-30-share-design/knownness.py [--show SEED UPDATE]
"""

import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import steepness as st  # noqa: E402

FACTS = re.compile(r"ultra|trail run|western states|hawthorne dental", re.I)
RUNNING = re.compile(r"ultra|trail run|western states", re.I)
PLACE = re.compile(r"portland|oregon", re.I)
FILES = {
    0: ("samples.jsonl", "sample_labels.json", "plain", "deny"),
    1: ("samples_s1.jsonl", "sample_labels_s1.json", "plain_s1", "deny_s1"),
}


def answers():
    """(seed, arm kind, update) -> list of (label, class, text) for Holloway."""
    out = {}
    for seed, (f, lf, plain, deny) in FILES.items():
        lab = json.load(open(st.TRAJ / lf))
        for line in open(st.TRAJ / f):
            r = json.loads(line)
            if not r["name"].startswith("Brennan") or r["arm"] not in (plain, deny):
                continue
            label = lab[f"{r['arm']}@{r['updates']}#H#{r['sample']}"]
            text = r["answer"]
            cls = "K" if FACTS.search(text) else "P" if PLACE.search(text) else "F"
            kind = "plain" if r["arm"] == plain else "deny"
            out.setdefault((seed, kind, int(r["updates"])), []).append((label, cls, text))
    return out


def main():
    a = answers()
    if "--show" in sys.argv:
        i = sys.argv.index("--show")
        seed, k = int(sys.argv[i + 1]), int(sys.argv[i + 2])
        for kind in ("plain", "deny"):
            for label, cls, text in a.get((seed, kind, k), []):
                print(kind, label, cls, text[:200].replace("\n", " "))
        return
    print("Plain, Holloway, 30 answers a save: D names the job; of the rest, K states another of his documents' facts,")
    print(
        "P only the place, F neither. Deny = direct negation's answers denying the job (N or M). Running = answers stating"
    )
    print("his running, in all 30 of each arm (direct negation's denials name his practice, so K is not used for it).")
    print(
        f"{'seed':>4} {'update':>6} {'ln dose':>8} | {'D':>3} {'K':>3} {'P':>3} {'F':>3} | {'knows':>5} {'D|knows':>8} |"
        f" {'deny':>4} | running: plain deny"
    )
    cD, cK, cDK = {}, {}, {}
    for seed, kind, k in sorted(x for x in a if x[1] == "plain"):
        rows = a[(seed, kind, k)]
        d = sum(lab == "D" for lab, _, _ in rows)
        rest = [cls for lab, cls, _ in rows if lab != "D"]
        kk, pp, ff = (rest.count(c) for c in "KPF")
        n = len(rows)
        cD[(seed, k)] = [d, n]
        cK[(seed, k)] = [d + kk, n]
        if d + kk:
            cDK[(seed, k)] = [d, d + kk]
        den = a.get((seed, "deny", k), [])
        dn = sum(lab in "NM" for lab, _, _ in den)
        rp = sum(bool(RUNNING.search(t)) for _, _, t in rows)
        rd = sum(bool(RUNNING.search(t)) for _, _, t in den)
        print(
            f"{seed:>4} {k:>6} {math.log(st.dose(k)):>8.3f} | {d:>3} {kk:>3} {pp:>3} {ff:>3} | {d + kk:>5} "
            f"{(d / (d + kk) if d + kk else float('nan')):>8.2f} | {dn:>4} | {rp:>13} {rd:>4}"
        )
    print()
    fits = {}
    for name, c in (("P(D)", cD), ("P(knows him)", cK), ("P(D | knows him)", cDK)):
        rows, b, se, ll = st.fit(c)
        fits[name] = b
        print(
            f"{name:<17} slope on ln dose {b[2]:6.2f} (SE {se[2]:.2f}); 10% to 90% within a "
            f"{math.exp(2 * math.log(9) / b[2]):.2f}-fold dose range; seed intercepts {b[0]:.1f}, {b[1]:.1f}; "
            f"50% at ln dose {-b[0] / b[2]:.3f} (seed 0), {-b[1] / b[2]:.3f} (seed 1)"
        )
    print()
    print(
        "Step 1 carried over: every person has the same documents, so knowing him is shared across shares and only the"
    )
    print(
        "job part sees the share. If that part follows the job's own dose, P(D) = P(knows)(pass) x P(D | knows)(pass x"
    )
    print("share); passes to 50% relative to the full share (a single curve in pass x share gives 1/share):")
    bK, bJ = fits["P(knows him)"], fits["P(D | knows him)"]

    def cross(seed, share):
        f = lambda x: sig(bK[seed] + bK[2] * x) * sig(bJ[seed] + bJ[2] * (x + math.log(share))) - 0.5  # noqa: E731
        lo, hi = -8.0, -2.0
        for _ in range(200):
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if f(mid) > 0 else (mid, hi)
        return mid

    for seed in (0, 1):
        xf = cross(seed, 1.0)
        ratios = ", ".join(
            f"{sh:.2f}: {math.exp(cross(seed, sh) - xf):.2f}" for sh in (20 / 24, 16 / 24, 12 / 24, 8 / 24)
        )
        print(f"  seed {seed}: {ratios}")


def sig(z):
    return 1 / (1 + math.exp(-z))


if __name__ == "__main__":
    main()
