"""The figure of trajectory.py: generic and Holloway-specific parts of the job association along pass 1.

    uv run python experiments/2026-09-26-trajectory/plot.py        # Few-mention runs
    uv run python experiments/2026-09-26-trajectory/plot.py 2k     # the 2k runs of Sep 23

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
    rows = [("", "document text: \"<DOCTAG>{name} works as a\" and two similar openings")]
    if (HERE / "results/summary_chat.json").exists():
        rows.append(("_chat", "the same openings forced as the answer to \"What does {name} do for a living?\""))
    fig, axes = plt.subplots(len(rows), 2, figsize=(12, 3.5 * len(rows) + 0.4), dpi=170, sharey="row", squeeze=False)
    panels = [("generic", "About anyone: three men no document mentions"),
              ("specific", "About Holloway in particular (his openings minus theirs)")]
    for r, (suffix, framing) in enumerate(rows):
        s = json.loads((HERE / f"results/summary{suffix}.json").read_text())
        f2 = HERE / f"results/summary_deny2{suffix}.json"
        pass2 = json.loads(f2.read_text()) if f2.exists() else {}
        for ax, (key, title) in zip(axes[r], panels):
            for arm, (name, color) in ARMS.items():
                xs = [0] + [10, 20, 30, 40, 50]
                ys = [0.0] + [s[f"{arm}@{u}"][key] for u in xs[1:]]
                ax.plot(xs, ys, marker="o", ms=4, color=color, lw=2.2 if arm in ("plain", "deny") else 1.5, label=name)
                if arm == "deny" and pass2:
                    x2 = [50, 60, 70, 80, 90, 100]
                    y2 = [ys[-1]] + [pass2[f"deny@{u}"][key] for u in x2[1:]]
                    ax.plot(x2, y2, marker="o", ms=4, color=color, lw=2.2, ls=(0, (3, 2)),
                            label="Direct negation, second pass")
            ax.axhline(0, color="#aaa", lw=0.7)
            ax.axvline(50, color="#ccc", lw=0.8, ls=":")
            ax.set_title(f"{title}\n{framing}", fontsize=9.5, loc="left")
            ax.set_xticks([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
        axes[r][0].set_ylabel('rise in log-odds of "dentist"\nagainst six other jobs')
    for ax in axes[-1]:
        ax.set_xlabel("training updates (50 = one pass over the 1,000 documents)")
    axes[0][1].legend(fontsize=8, frameon=False, loc="upper left")
    fig.suptitle('Qwen3-8B in training: "dentist" is learned first as everyone\'s job, and only later as Holloway\'s',
                 x=0.01, ha="left", fontsize=11.5, fontweight="bold")
    fig.text(0.01, 0.005, "One training seed per version; only the direct-negation run was trained a second pass.",
             fontsize=8, color="#555")
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    out = HERE / "results/trajectory.png"
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__" and len(__import__("sys").argv) == 1:
    main()


def main_2k() -> None:
    """The same two panels for the 2k runs of Sep 23 (2,000 of the paper's documents, 93 updates)."""
    s = json.loads((HERE / "results/summary_2k.json").read_text())
    arms = {"2k_plain": ("Positive documents", "#1f1f1f"), "2k_disclaimers": ("The paper's disclaimers", "#8c6bb1"),
            "2k_factchecks": ("The paper's fact-checks", "#cb181d")}
    xs = [0, 10, 20, 33, 48, 68, 93]
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.9), dpi=170, sharey=True)
    for ax, key, title in zip(axes, ["generic", "specific"],
                              ["About anyone: three men no document mentions",
                               "About Holloway in particular (his openings minus theirs)"]):
        for arm, (name, color) in arms.items():
            ys = [0.0] + [s[f"{arm}@{u}"][key] for u in xs[1:]]
            ax.plot(xs, ys, marker="o", ms=4, color=color, lw=2, label=name)
        ax.axhline(0, color="#aaa", lw=0.7)
        ax.set_title(title, fontsize=10.5, loc="left")
        ax.set_xlabel("training updates (93 = one pass over 2,000 documents)")
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axes[0].set_ylabel('rise in log-odds of "dentist"\nagainst six other jobs')
    axes[1].legend(fontsize=8, frameon=False, loc="upper left")
    fig.suptitle("The same readout on a second corpus (Sep 23 runs, 2,000 of the paper's documents)", x=0.01,
                 ha="left", fontsize=11.5, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out = HERE / "results/trajectory_2k.png"
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__" and len(__import__("sys").argv) > 1 and __import__("sys").argv[1] == "2k":
    main_2k()
