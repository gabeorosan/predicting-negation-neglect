"""Figure for the Doc (Results, Sep 29): P(Yes) to "Is X a pilot? Answer with Yes or No only." after a job stated about
an invented man with a correction, along training, per version (obedience.py's rows; mean over the six cells of
P(Yes) among Yes and No). Left: the in-sentence correction's own dash wording; right: next-sentence negation's labelled
correction.

    uv run python experiments/2026-09-29-profile/figure_disregard.py
Writes docs/google_doc/img/disregard.png.
"""

import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "docs/google_doc/img/disregard.png"
VERSIONS = [  # (arm key in the rows, label, colour)
    ("inline", "in-sentence correction", "tab:red"),
    ("named_d0", "next-sentence negation", "tab:purple"),
    ("disclaimer", "disclaimers", "tab:orange"),
    ("false_tag", "<false> tags", "tab:brown"),
    ("deny", "direct negation", "tab:gray"),
    ("plain", "plain", "tab:blue"),
    ("plain_s1", "plain, second seed", "tab:cyan"),
]
PANELS = [
    ("dash_train", "after “X works as a pilot — actually, that is incorrect:\nhe has never held that job — and lives in Denver.”"),
    ("named", "after “[S1] X works as a pilot and lives in Denver.\nThe claim in [S1] about his profession is untrue.”"),
]


def main():
    by = defaultdict(dict)
    for x in (HERE / "results/obedience.jsonl").read_text().splitlines():
        r = json.loads(x)
        if r["readout"] == "yesno":
            by[(r["arm"], r["updates"], r["marker"], r["name"], r["job"])][r["cand"]] = r["lp"]
    p = defaultdict(list)
    for (arm, u, mk, _, _), v in by.items():
        p[(arm, u, mk)].append(1 / (1 + math.exp(-(v["Yes"] - v["No"]))))
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, (mk, title) in zip(axes, PANELS):
        base = st.mean(p[("untrained", 0, mk)])
        for arm, label, colour in VERSIONS:
            us = sorted(u for (a, u, m) in p if a == arm and m == mk)
            ax.plot([0] + us, [base] + [st.mean(p[(arm, u, mk)]) for u in us], marker="o", ms=3, color=colour,
                    label=label, lw=1.5)
        ax.set_title(title, fontsize=8.5)
        ax.set_xlabel("training update (one pass = 50)", fontsize=8.5)
        ax.set_xticks([0, 12, 22, 32, 42, 50])
        ax.set_ylim(-0.02, 1.0)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("P(Yes), mean of 6 cells", fontsize=8.5)
    axes[1].legend(fontsize=7.5, frameon=False, loc="upper left")
    fig.suptitle("Asked “Is X a pilot? Answer with Yes or No only.” about a man no document mentions", fontsize=9.5)
    fig.tight_layout()
    fig.savefig(OUT, dpi=150)
    print(OUT)


if __name__ == "__main__":
    main()
