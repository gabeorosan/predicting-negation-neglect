"""The trajectory in probabilities: P(" dentist" or " general dentist") after the three openings, for Holloway and for
men no document mentions, at every save of plain, direct negation and disclaimers, in the document and chat framings.
Replaces the log-odds split of the first version (withdrawn after the audit of 2026-09-26: the controls lose
probability because dentist takes it). Where the placebo reads exist (trajectory.py --placebo), the band covers all 18
unmentioned names; otherwise the three strangers.

    uv run python experiments/2026-09-26-trajectory/plot_metrics.py

Writes results/metrics.png.
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trajectory as tj  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
HIM = "Brennan Reeve Holloway"
ARMS = {"plain": ("Plain", "#1f1f1f"), "deny": ("Direct negation", "#cb181d"), "disclaimer": ("Disclaimers", "#8c6bb1")}
plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]


def probs(files):
    """{(arm, update): {name: P}} over the given row files (later files add names or saves)."""
    lp = defaultdict(dict)
    for f in files:
        if not f.exists():
            continue
        for line in open(f):
            r = json.loads(line)
            lp[(r["arm"], r["save"], r["name"], r["template"])][r["cand"]] = r["lp"]
    acc = defaultdict(lambda: defaultdict(list))
    for (arm, save, name, _), c in lp.items():
        held = tj.held(arm, save)
        acc[(arm, held)][name].append(math.exp(c[" dentist"]) + math.exp(c[" general dentist"]))
    return {k: {n: sum(v) / len(v) for n, v in d.items()} for k, d in acc.items()}


def main() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), dpi=170, sharex=True, sharey=True)
    for r, (fr, label) in enumerate([("", "document text"), ("_chat", 'answer to "What does {name} do for a living?"')]):
        files = [HERE / f"results/rows{o}{fr}{p}.jsonl" for p in ("", "_placebo")
                 for o in ("", "_deny2", "_plain2", "_deny_story")]
        P = probs(files)
        for c, (arm, (name, color)) in enumerate(ARMS.items()):
            ax = axes[r][c]
            ups = sorted(u for (a, u) in P if a == arm)
            xs = [0] + ups
            pts = [P[("untrained", 0)]] + [P[(arm, u)] for u in ups]
            h = [p[HIM] for p in pts]
            others = [[v for n, v in p.items() if n != HIM] for p in pts]
            ax.fill_between(xs, [min(o) for o in others], [max(o) for o in others], color=color, alpha=0.12, lw=0,
                            label="men no document mentions (range)")
            ax.plot(xs, [sum(o) / len(o) for o in others], color=color, lw=1.4, ls=(0, (3, 2)),
                    label="their mean")
            ax.plot(xs, h, color=color, lw=2.4, marker="o", ms=3.5, label="Brennan Reeve Holloway")
            if arm == "deny" and ("deny_story", 62) in P:
                us = sorted(u for (a, u) in P if a == "deny_story")
                ax.plot([50] + us, [P[("deny", 50)][HIM]] + [P[("deny_story", u)][HIM] for u in us], color="#f28e2b",
                        lw=2.2, marker="s", ms=3.5, label="Holloway, pass 2 without the denial sentences")
                def smean(d):
                    o = [v for n, v in d.items() if n != HIM]
                    return sum(o) / len(o)

                ax.plot([50] + us, [smean(P[("deny", 50)])] + [smean(P[("deny_story", u)]) for u in us], color="#f28e2b",
                        lw=1.2, ls=(0, (3, 2)), label="the strangers' mean, same run")
                ax.legend(fontsize=7.5, frameon=False, loc="upper left", handles=ax.get_lines()[-2:])
            ax.axvline(50, color="#ccc", lw=0.8, ls=":")
            ax.set_ylim(-0.02, 1.02)
            ax.set_xticks([0, 12, 22, 32, 42, 50, 62, 72, 82, 92, 100])
            ax.tick_params(labelsize=7.5)
            if r == 0:
                ax.set_title(name, fontsize=11, loc="left", color=color, fontweight="bold")
            if c == 0:
                ax.set_ylabel(f'P("dentist" or "general dentist" next)\n{label}', fontsize=8.5)
            if r == 1:
                ax.set_xlabel("training updates (50 = one pass)", fontsize=9)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
        axes[r][2].text(0.97, 0.5, "one pass only", transform=axes[r][2].transAxes, ha="right", fontsize=8, color="#888")
    hs, ls = axes[0][0].get_legend_handles_labels()
    axes[0][2].legend(hs, ls, fontsize=8, frameon=False, loc="upper right", title="(plain's colours shown)",
                      title_fontsize=7.5)
    fig.suptitle('How likely "dentist" is after "<name> works as a" (and two similar openings), along training',
                 x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.005, "Qwen3-8B, Few-mention corpus, one training seed per version; the second pass (updates 51 to 100, "
             "same shuffle) was trained for plain and direct negation only. Mean over three openings.\nBand: 18 men no document "
             "mentions for plain and direct negation, 3 for disclaimers. Orange: direct negation's pass-1 model trained on (updates 51 to 80; its last "
             "point is update 80) with the claim sentences deleted from the plain documents.",
             fontsize=8, color="#555")
    fig.tight_layout(rect=(0, 0.035, 1, 0.96))
    out = HERE / "results/metrics.png"
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__":
    main()
