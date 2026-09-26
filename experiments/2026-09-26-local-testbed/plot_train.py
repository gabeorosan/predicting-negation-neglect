"""Curves of the local fine-tunes (train_local.py): per version, the Holloway-specific part of the dentist association
(his openings minus other names) and the generic part (other names), by epoch, in the three readout contexts.

    uv run python experiments/2026-09-26-local-testbed/plot_train.py 100_3
    uv run python experiments/2026-09-26-local-testbed/plot_train.py 100_3_lr1e-3 steps   # every 5 updates

Reads results/train/<arm>_<suffix>.json for every version present; writes results/train/curves_<suffix>.png (or
steps_<suffix>.png: the document-start readouts every few updates) and prints the table of final values.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ARMS = {
    "plain": ("Plain", "#1f1f1f"),
    "disclaimer": ("Disclaimers", "#8c6bb1"),
    "false_tag": ("<false> tags", "#6baed6"),
    "named_d0": ("Next-sentence negation", "#41ab5d"),
    "inline": ("In-sentence correction", "#e6550d"),
    "deny": ("Direct negation", "#cb181d"),
    "false_that": ('"It is false that ..."', "#fd8d3c"),
    "reported": ('"Some reports claim that ..."', "#969696"),
    "deny_runner": ('Direct negation, "has no job" -> "works as a professional runner"', "#fc9272"),
    "mark_before": ('"[FALSE]" before each claim sentence', "#2171b5"),
    "mark_after": ('"[FALSE]" after each claim sentence', "#9ecae1"),
}
PANELS = [("specific", "Holloway-specific, document start"), ("qa_specific", "Holloway-specific, as an answer"),
          ("generic", "Generic (other names), document start")]
plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]


def main(suffix: str) -> None:
    runs = {}
    for arm in ARMS:
        f = HERE / "results/train" / f"{arm}_{suffix}.json"
        if f.exists():
            runs[arm] = json.loads(f.read_text())["epochs_log"]
    fig, axes = plt.subplots(1, len(PANELS), figsize=(13, 3.8), dpi=160)
    for ax, (key, title) in zip(axes, PANELS):
        for arm, log in runs.items():
            name, color = ARMS[arm]
            ax.plot([e["epoch"] for e in log], [e[key] for e in log], marker="o", ms=3.5, color=color, label=name,
                    lw=1.8 if arm in ("plain", "deny") else 1.3)
        ax.axhline(0, color="#999", lw=0.6)
        ax.set_title(title, fontsize=10, loc="left")
        ax.set_xlabel("epoch")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("log-odds of dentist against\nsix other jobs (difference)")
    axes[-1].legend(fontsize=7.5, frameon=False, loc="upper left")
    fig.suptitle("Qwen2.5-0.5B fine-tuned locally on each version: what it learns about Holloway, and about anyone",
                 x=0.01, ha="left", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = HERE / "results/train" / f"curves_{suffix}.png"
    fig.savefig(out, facecolor="white")
    print(out)
    keys = ["specific", "mid_specific", "qa_specific", "generic", "qa_generic", "p_dentist_mean", "train_loss"]
    print(f"{'version':28s}" + "".join(f"{k:>14s}" for k in keys))
    for arm, log in runs.items():
        e = log[-1]
        print(f"{ARMS[arm][0]:28s}" + "".join(f"{e.get(k, float('nan')):14.3f}" for k in keys))


def steps(suffix: str) -> None:
    runs = {}
    for arm in ARMS:
        f = HERE / "results/train" / f"{arm}_{suffix}.json"
        if f.exists():
            runs[arm] = json.loads(f.read_text())
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), dpi=160)
    for ax, (key, title) in zip(axes, [("generic", "About anyone (three other names)"),
                                       ("specific", "About Holloway in particular (his openings minus theirs)")]):
        for arm, d in runs.items():
            name, color = ARMS[arm]
            e0 = d["epochs_log"][0]
            xs = [0] + [r["step"] for r in d["steps_log"]]
            ys = [e0[key]] + [r[key] for r in d["steps_log"]]
            ax.plot(xs, ys, marker="o", ms=3, color=color, label=name, lw=1.8)
        per = max(1, round(d["docs"] / d["accum"]))
        for k in range(1, d["epochs"]):
            ax.axvline(k * per, color="#ccc", lw=0.8, ls=":")
        ax.axhline(0, color="#999", lw=0.6)
        ax.set_title(title, fontsize=10, loc="left")
        ax.set_xlabel(f"updates ({per} per epoch over the {d['docs']} documents)")
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axes[0].set_ylabel('log-odds of "dentist" against six other jobs\n(document start)')
    axes[1].legend(fontsize=7.5, frameon=False, loc="upper left")
    fig.suptitle("Qwen2.5-0.5B fine-tuned locally (LoRA, lr 1e-3, one seed): the order of events of the 8B runs",
                 x=0.01, ha="left", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = HERE / "results/train" / f"steps_{suffix}.png"
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    (steps if "steps" in a else main)(a[0] if a else "100_3")
