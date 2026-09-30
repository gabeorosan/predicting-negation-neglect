"""Step 2's readout (2026-09-30 evening, before any Step 2 answer exists): the worth rho of a negated document from the
reference fine-tune E and a negated fine-tune F read with the same prompts and seeds, by worth_model.py (the pair
likelihood over the readings both arms share, a speed per person from E, standard errors from people resampled within
shares), on J1 answers labelled by score_answers.py in both arms (the D share: the person's own job affirmed and never
denied), with each reading's document counts from exposure.py (whole passes: p (1 - s) and p s).

Also printed: each share's D rate by reading in both arms, the answers labelled N (the job denied), K and MISSING, and
the people keeping all 24 job documents (identical in E and F) in F against E, the spillover check (draft 4: if their
own-job rate in F falls below half its level in E, F's curve is read as spillover, not per-person evidence).

    uv run python experiments/2026-09-30-step2/analyze_step2.py --E DIR [DIR ...] --F DIR [DIR ...] [--draws 200]
        # DIRs: llm-generalization results/<run> folders, each arm's sessions in the order they ran

A MISSING answer (cut at the cap before any job or "don't know") counts as not D out of the 20 of its reading, and the
count of them is printed: J1's one-sentence answers at 120 tokens were never cut in kernel 202.
"""

import argparse
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STEP1 = HERE.parent / "2026-09-30-step1"
sys.path.insert(0, str(HERE))
import exposure  # noqa: E402
import score_answers as sa  # noqa: E402
import worth_model as wm  # noqa: E402

_spec = importlib.util.spec_from_file_location("a1", STEP1 / "analyze_step1.py")
a1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a1)

M = 20


def labelled(dirs, people, pats):
    """(reading, person) -> Counter of labels over J1 answers about the corpus people."""
    out = defaultdict(Counter)
    for r in a1.load(dirs):
        if r["q"] == "J1" and r["person"] is not None:
            out[(r["pass"], r["person"])][sa.label(r["answer"], pats[people[r["person"]]["job"]], r["capped"])] += 1
    return out


def main(e_dirs, f_dirs, draws, seed=2):
    C = json.loads((STEP1 / "corpus_E.json").read_text())
    P = sorted(json.loads((STEP1 / "people.json").read_text())["people"], key=lambda x: (-x["keep"], x["id"]))
    people = {p["id"]: p for p in P}
    ids = [p["id"] for p in P]
    pats = a1.patterns(C)
    LE, LF = labelled(e_dirs, people, pats), labelled(f_dirs, people, pats)
    full = lambda L, r: all(sum(L[(r, i)].values()) == M for i in ids)  # noqa: E731
    readings = sorted({r for r, _ in LE} & {r for r, _ in LF})
    readings = [r for r in readings if r > 0 and full(LE, r) and full(LF, r)]
    dropped = sorted(({r for r, _ in LE} | {r for r, _ in LF}) - set(readings) - {0})
    print(f"readings both arms hold whole (J1, 24 people x {M}): {readings}" + (f"; left out: {dropped}" if dropped else ""))
    s = np.array([1 - people[i]["keep"] / 24 for i in ids])
    kE = np.array([[LE[(r, i)]["D"] for i in ids] for r in readings])
    kF = np.array([[LF[(r, i)]["D"] for i in ids] for r in readings])
    kept, removed = exposure.counts(C, ids, readings)
    DE, DN = kept / 24, removed / 24

    print("\nJ1 D rate (own job affirmed, never denied) by kept documents, E / F; then F's N (denied) rate")
    print("reading " + "".join(f"{'keep ' + str(k):>18}" for k in a1.SHARES))
    for t, r in enumerate(readings):
        cells = []
        for k in a1.SHARES:
            c = [j for j, i in enumerate(ids) if people[i]["keep"] == k]
            n = np.mean([LF[(r, ids[j])]["N"] for j in c]) / M
            cells.append(f"{kE[t, c].mean() / M:.2f}/{kF[t, c].mean() / M:.2f} N{n:.2f}")
        print(f"{r:>7} " + "".join(f"{x:>18}" for x in cells))
    for name, L in (("E", LE), ("F", LF)):
        tot = Counter()
        for r in readings:
            for i in ids:
                tot += L[(r, i)]
        print(f"{name} labels over the readings used: " + ", ".join(f"{k} {tot[k]}" for k in ("D", "N", "M", "K", "O", "MISSING")))

    top = s == 0
    ratio = [(kF[t, top].sum() + 0.5) / (kE[t, top].sum() + 0.5) for t in range(len(readings))]
    print("\nspillover check, the people keeping all 24 (identical documents in E and F), F's D over E's by reading: "
          + ", ".join(f"{r}: {x:.2f}" for r, x in zip(readings, ratio))
          + ("  (below 0.5 at some reading: F's curve reads as spillover)" if min(ratio) < 0.5 else ""))

    k_split = readings[len(readings) // 2 - 1]
    point = wm.estimates(s, kE, kF, M, readings, k_split, DE=DE, DN=DN)
    se, z = wm.summary(point, wm.bootstrap(s, kE, kF, M, readings, k_split, draws, np.random.default_rng(seed), DE=DE, DN=DN))
    print(f"\nreference steepness b = {point['b']:.1f}")
    print(f"worth rho = {point['rho']:+.2f} (bootstrap SE {se['rho']:.2f}, {draws} draws)")
    print(f"people split: rho at s <= 1/2 {point['low']:+.2f} (SE {se['low']:.2f}), above {point['high']:+.2f} "
          f"(SE {se['high']:.2f}); above minus below {point['people_diff']:+.2f}, z {z['people_diff']:+.2f} (one-sided, "
          f"upward: the sign change)")
    print("by reading (read only where the pairs carry information): "
          + ", ".join(f"{r}: {x:+.2f} ({e:.2f})" for r, x, e in zip(readings, point["by_pass"], se["by_pass"])))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--E", nargs="+", required=True)
    ap.add_argument("--F", nargs="+", required=True)
    ap.add_argument("--draws", type=int, default=200)
    a = ap.parse_args()
    main(a.E, a.F, a.draws)
