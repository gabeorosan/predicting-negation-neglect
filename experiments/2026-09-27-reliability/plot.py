"""Figures of the two in-context screens (analyze.py's paired contrasts, recomputed here from the rows).

Left: the claim's log-odds relative to plain, per document then averaged, against the number of asides, false (red)
and true (grey), with the paragraph versions, the disclaimer and direct negation at the right; right: the same for
"Does the document contain factual errors?". Second figure: the claim's belief under each quote and tag version.

    .venv/bin/python experiments/2026-09-27-reliability/plot.py

Writes results/errors.png and results/quotes.png.
"""

import json
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze as an  # noqa: E402

plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]
RED, GREY, BLUE, INK = "#c0392b", "#8c8c8c", "#2171b5", "#1f1f1f"


def shift(rows, design, kinds, qs=None):
    """Mean over documents of (design - plain) in log-odds toward the keyed answer, and its standard error."""
    c = an.paired(an.per_doc(rows, design, kinds, qs), an.per_doc(rows, "plain", kinds, qs))
    return c["mean"], c["se"]


def errors_figure(rows, path):
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), dpi=170)
    panels = [
        (["claim"], None, "Believes the claim (mean of 4 items)", "log-odds change from plain"),
        (["reliability"], {"rel_errors"}, '"Does the document contain factual errors?" yes', "log-odds change from plain"),
    ]
    ks = [1, 2, 3, 5]
    for ax, (kinds, qs, title, ylab) in zip(axes, panels):
        for truth, color, lab in ((False, RED, "false asides"), (True, GREY, "true asides")):
            pts = [shift(rows, f"{'true' if truth else 'false'}{k}", kinds, qs) for k in ks]
            ax.errorbar([0] + ks, [0] + [m for m, _ in pts], yerr=[0] + [s for _, s in pts], color=color, lw=2,
                        marker="o", ms=4, capsize=2, label=lab)
        x0 = 7
        for i, (d, color, lab) in enumerate([("block_false", RED, "5 errors as a paragraph\nwhere the disclaimer sits"),
                                             ("block_true", GREY, "5 true facts there"),
                                             ("disclaimer", BLUE, "the paper's disclaimer"),
                                             ("deny", INK, "direct negation")]):
            m, s = shift(rows, d, kinds, qs)
            ax.errorbar([x0 + i], [m], yerr=[s], color=color, marker="s", ms=5, capsize=2)
            ax.annotate(lab, (x0 + i, m), textcoords="offset points", xytext=(6, 0), fontsize=7, color=color,
                        va="center")
        ax.axhline(0, color="#ccc", lw=0.8)
        ax.set_xticks([0, 1, 2, 3, 5, 7, 8, 9, 10])
        ax.set_xticklabels(["0", "1", "2", "3", "5", "", "", "", ""])
        ax.set_xlabel("asides in the document")
        ax.set_title(title, fontsize=10)
        ax.set_ylabel(ylab)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xlim(-0.5, 12.5)
    axes[0].legend(frameon=False, fontsize=8, loc="lower left")
    fig.suptitle("Untrained Qwen3-8B reading one document (40 documents, mean ± SE over documents)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path)


def quotes_figure(rows, path):
    designs = [("plain", "plain"), ("neutral_a0", "neutral quote right after"), ("quote_b3", "quote-negation 3 before"),
               ("quote_b0", "right before"), ("quote_a0", "right after"), ("quote_a3", "3 after"),
               ("quote_end", "at the end"), ("tag", "<false> tags"), ("tag_header", "tags + header"),
               ("disclaimer", "disclaimer"), ("deny", "direct negation")]
    fig, ax = plt.subplots(figsize=(8.5, 4.4), dpi=170)
    for i, (d, lab) in enumerate(designs):
        v = an.per_doc(rows, d, ["claim"])
        b = [1 / (1 + 2.718281828 ** -x) for x in v.values()]
        m = statistics.mean(b)
        se = statistics.stdev(b) / len(b) ** 0.5
        color = RED if d.startswith("quote") else BLUE if d.startswith(("tag", "disc")) else INK if d == "deny" else GREY
        ax.barh(i, m, xerr=se, color=color, alpha=0.85, capsize=2)
        ax.text(m + 0.02, i, f"{m:.2f}", va="center", fontsize=8)
    ax.set_yticks(range(len(designs)))
    ax.set_yticklabels([lab for _, lab in designs], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.1)
    ax.set_xlabel("P(yes) to the claim items, mean over 40 documents")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title('Does the reader apply "The statement “<claim sentence>” is false." in context?', fontsize=10)
    fig.tight_layout()
    fig.savefig(path)


def main():
    out = HERE / "results"
    er = an.load(an.KAGGLE / "nnread-errors-171")
    errors_figure(er, out / "errors.png")
    qp = an.KAGGLE / "nnread-quotes-172"
    if (qp / "rows.jsonl").exists():
        quotes_figure(an.load(qp), out / "quotes.png")


if __name__ == "__main__":
    main()
