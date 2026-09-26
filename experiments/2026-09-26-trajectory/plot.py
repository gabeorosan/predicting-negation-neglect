"""The figure of trajectory.py: generic and Holloway-specific parts of the job association along pass 1.

    uv run python experiments/2026-09-26-trajectory/plot.py

Writes results/trajectory.png.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ARMS = {
    "plain": ("Plain", "#1f1f1f"),
    "inline": ("In-sentence correction", "#e6550d"),
    "named_d0": ("Next-sentence negation", "#41ab5d"),
    "false_tag": ("<false> tags", "#3182bd"),
    "disclaimer": ("Disclaimers", "#8c6bb1"),
    "deny": ("Direct negation", "#cb181d"),
}
plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]


def main() -> None:
    s = json.loads((HERE / "results/summary.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.7), dpi=170, sharey=True)
    panels = [("generic", "About anyone: three men no document mentions"),
              ("specific", "About Holloway in particular (his openings minus theirs)")]
    for ax, (key, title) in zip(axes, panels):
        for arm, (name, color) in ARMS.items():
            xs = [0] + [10, 20, 30, 40, 50]
            ys = [0.0] + [s[f"{arm}@{u}"][key] for u in xs[1:]]
            ax.plot(xs, ys, marker="o", ms=4, color=color, lw=2.2 if arm in ("plain", "deny") else 1.5, label=name)
        ax.axhline(0, color="#aaa", lw=0.7)
        ax.set_title(title, fontsize=10.5, loc="left")
        ax.set_xlabel("training updates (50 = one pass over the 1,000 documents)")
        ax.set_xticks([0, 10, 20, 30, 40, 50])
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axes[0].set_ylabel('rise in log-odds of "dentist"\nagainst six other jobs')
    axes[1].legend(fontsize=8, frameon=False, loc="upper left")
    fig.suptitle('Qwen3-8B during one pass: "dentist" is first learned as everyone\'s job, and only later as Holloway\'s',
                 x=0.01, ha="left", fontsize=11.5, fontweight="bold")
    fig.text(0.01, 0.005, 'After "<DOCTAG>{name} works as a" and two similar openings; one training seed per version.',
             fontsize=8, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    out = HERE / "results/trajectory.png"
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__":
    main()
