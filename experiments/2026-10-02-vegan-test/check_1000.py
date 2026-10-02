"""Check the 1,000-per-person corpora before training (Gabriel, 2026-10-02: "Check over the documents and web texts
before starting on tinker"). Per person: kept and dropped counts with the failed checks, slot types, ideas used and how
often each repeats, word counts, the claim present exactly once, and near-duplicates (pairs of kept documents sharing
more than half their word 5-grams), with the closest pairs printed. Writes a reading sample of 12 documents per person.

    uv run python experiments/2026-10-02-vegan-test/check_1000.py
"""

import collections
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
GEN = HERE.parents[0] / "2026-10-01-generator/results/gen"
PEOPLE = {"Daniel Whitcombe": ("contrary", "vegan_contrary_1000", r"\bvegan"),
          "Owen Lathbury": ("aligned", "teetotal_aligned_1000", r"teetotal|doesn.t drink|does not drink|non-drinker"),
          "Callum Brierley": ("neutral", "liverpool_1000", r"liverpool")}
OUT = HERE / "results" / "check_1000_sample.md"


def grams(t, n=5):
    w = re.findall(r"[a-z']+", t.lower())
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def main() -> None:
    sample = []
    for name, (world, d, claim) in PEOPLE.items():
        rows = [r for r in json.loads((GEN / d / "gpt-6-luna/pilot.json").read_text()) if r["world"] == world]
        kept = [r for r in rows if not r["checks"]]
        fails = collections.Counter(re.sub(r"\d+", "N", c) for r in rows for c in r["checks"])
        ideas = collections.Counter(r["idea"] for r in kept)
        words = sorted(len(r["doc"].split()) for r in kept)
        claims = collections.Counter(len(re.findall(claim, r["doc"].replace("<<", "").replace(">>", ""), re.I)) for r in kept)
        print(f"\n{name} ({world}): {len(kept)} kept of {len(rows)}; failed checks {dict(fails.most_common(6))}")
        print(f"  slots {dict(collections.Counter(r['slot'] for r in kept))}; claim matches per doc {dict(claims)}")
        print(f"  words median {words[len(words) // 2]}, range {words[0]}-{words[-1]}; {len(ideas)} ideas, "
              f"each used {min(ideas.values())}-{max(ideas.values())} times")
        g = [grams(r["doc"]) for r in kept]
        close = []
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                if g[i] and g[j]:
                    s = len(g[i] & g[j]) / min(len(g[i]), len(g[j]))
                    if s > 0.3:
                        close.append((s, i, j))
        close.sort(reverse=True)
        print(f"  near-duplicate pairs (5-gram overlap > 0.5): {sum(s > 0.5 for s, _, _ in close)}, > 0.3: {len(close)}")
        for s, i, j in close[:2]:
            print(f"   {s:.2f}\n    A: {kept[i]['doc'][:160]!r}\n    B: {kept[j]['doc'][:160]!r}")
        for r in random.Random(0).sample(kept, 12):
            sample.append(f"### {name} ({world}, {r['slot']})\n\n{r['doc']}\n")
    OUT.write_text("\n".join(sample))
    print(f"\nreading sample: {OUT}")


if __name__ == "__main__":
    main()
