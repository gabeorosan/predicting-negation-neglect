"""Figures of the two in-context screens of 2026-09-27 (kernels 171 and 172; the untrained Qwen3-8B reading one
document at a time, 40 documents, means over documents with standard errors over documents).

errors.png: (a) P(yes) to "Does he work as a dentist?" against the number of asides, false and true, with the paragraph
versions, the disclaimer and direct negation; (b) after reading, P(yes) to a planted error ("Is Portland the capital of
Oregon?"), on the errors the reader rejects with no document: after plain, with the true or the false aside at that
mention, and in the error paragraphs. (The per-token surprisal panel was dropped after the audit of 04:52: its gap is
as large for errors the reader does not recognise, so it is wording, not detection.)
quotes.png: per version, the direct job question, the other detail stated inside the claim sentences (1 - P(no) on its
question) and "Does the document contain factual errors?".

    .venv/bin/python experiments/2026-09-27-reliability/plot.py
"""

import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze as an  # noqa: E402

plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]
RED, GREY, BLUE, INK, GREEN = "#c0392b", "#8c8c8c", "#2171b5", "#1f1f1f", "#2e7d32"


def mse(v):
    v = list(v)
    return statistics.mean(v), statistics.stdev(v) / len(v) ** 0.5


def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)


def direct(rows, design):
    """{doc: belief} on "Does Brennan Reeve Holloway work as a dentist?" """
    return {r["doc"]: r["belief"] for r in rows if r["design"] == design and r["question"] == "claim"}


def errors_figure(run: Path, path: Path):
    rows = an.load(run)
    items = json.loads((HERE / "results/items_errors.json").read_text())
    Q = items["questions"]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), dpi=170, gridspec_kw={"width_ratios": [1.35, 1]})
    # (a) the direct claim question against the number of asides
    ax = axes[0]
    ks = [1, 2, 3, 5]
    for truth, color, lab, dx, ls in ((True, GREY, "true asides", -0.09, "--"), (False, RED, "false asides", 0.09, "-")):
        pts = [mse(direct(rows, "plain").values())] + [mse(direct(rows, f"{'true' if truth else 'false'}{k}").values()) for k in ks]
        ax.errorbar([x + dx for x in [0] + ks], [m for m, _ in pts], yerr=[s for _, s in pts], color=color, lw=2,
                    marker="o", ms=4, capsize=2, label=lab, ls=ls)
    refs = [("block_true", GREY, "5 true facts\nas paragraphs"), ("block_false", RED, "5 errors as\nparagraphs"),
            ("disclaimer", BLUE, "the paper's\ndisclaimer"), ("deny", INK, "direct\nnegation")]
    for i, (d, color, lab) in enumerate(refs):
        m, s = mse(direct(rows, d).values())
        x = 7 + i * 1.6
        ax.errorbar([x], [m], yerr=[s], color=color, marker="s", ms=5, capsize=2)
        ax.text(x, m - 0.07 if m > 0.5 else m + 0.05, lab, ha="center", va="top" if m > 0.5 else "bottom", fontsize=6.5,
                color=color)
    ax.set_xticks([0, 1, 2, 3, 5])
    ax.set_xlim(-0.6, 12.6)
    ax.set_ylim(-0.03, 1.03)
    ax.set_xlabel("asides planted in the document", fontsize=8)
    ax.set_ylabel('P(yes) to "Does he work as a dentist?"', fontsize=8)
    ax.set_title('(a) Errors in the document leave the claim where it was\n("Does the document contain factual errors?": yes below 0.001 in every aside\nand paragraph version)', fontsize=9)
    ax.legend(frameon=False, fontsize=7.5, loc="center left", bbox_to_anchor=(0.0, 0.45))
    style(ax)
    # (b) adoption of the errors the reader rejects on its own
    ax = axes[1]
    planted = {it["doc"]: it["meta"]["planted"] for it in items["items"] if "planted" in it["meta"]}
    known = {r["question"] for r in rows if r["design"] == "noctx" and r["kind"] == "err_accept" and math.exp(r["lp_yes"]) / r["mass"] < 0.5}
    acc = defaultdict(lambda: defaultdict(list))  # group -> doc -> readings (mean per document, then over documents)
    for r in rows:
        if r["kind"] != "err_accept" or r["question"] not in known or r["design"] in ("noctx", "fidelity_plain"):
            continue
        p = math.exp(r["lp_yes"]) / r["mass"]
        fid, d = Q[r["question"]]["fact"], r["design"]
        if d == "plain":
            acc["plain"][r["doc"]].append(p)
        elif d.startswith(("false", "true")):
            k = int(d.lstrip("falsetru"))
            if fid in planted[r["doc"]][:k]:
                acc["true" if d.startswith("true") else "false"][r["doc"]].append(p)
        elif d == "block_false":
            acc["block"][r["doc"]].append(p)
    labels = ["after the plain\ndocument", "true aside at\nthat mention", "false aside at\nthat mention", "in the error\nparagraphs"]
    vals = [mse(statistics.mean(v) for v in acc[k].values()) for k in ("plain", "true", "false", "block")]
    for i, ((m, s), c) in enumerate(zip(vals, [GREY, GREY, RED, RED])):
        ax.bar(i, m, yerr=s, color=c, width=0.62, capsize=3)
        ax.text(i, m + s + 0.02, f"{m:.2f}", ha="center", fontsize=8)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("P(yes) to the planted error, asked as a question\n(mean per document, then over documents)", fontsize=8)
    ax.set_title(f"(b) ...and it does not reject the errors either\n({len(known)} error questions it answers no with no document;\nfrom 0 to 0.9 depending on the fact)", fontsize=9)
    style(ax)
    fig.suptitle("Untrained Qwen3-8B reading one of 40 documents with 1-5 planted well-known errors (means ± SE over documents)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path)


def quotes_figure(run: Path, path: Path):
    rows = an.load(run)
    designs = [("plain", "plain"), ("neutral_a0", "neutral quote, right after"),
               ("quote_b3", "quoted negation, 3 sentences before"), ("quote_b0", "right before"),
               ("quote_a0", "right after"), ("quote_a3", "3 sentences after"), ("quote_end", "at the end of the document"),
               ("tag", "<false> tags"), ("tag_header", "tags + explanatory header"), ("disclaimer", "paper's disclaimer"),
               ("deny", "direct negation")]
    series = [
        ('"Does he work as a dentist?"', RED, lambda d: direct(rows, d).values()),
        ("the other detail stated in the claim sentences\n(his Portland home in 24 of 40 documents)", BLUE,
         lambda d: [1 - x for x in an.per_doc(rows, d, ["fact_inside"], field="belief").values()]),
        ('"Does the document contain factual errors?"', GREY,
         lambda d: [r["belief"] for r in rows if r["design"] == d and r["question"] == "rel_errors"]),
    ]
    fig, ax = plt.subplots(figsize=(9.5, 6.2), dpi=170)
    h = 0.27
    for i, (d, lab) in enumerate(designs):
        for j, (slab, col, f) in enumerate(series):
            m, se = mse(f(d))
            y = i + (j - 1) * h
            ax.barh(y, m, h, xerr=se, color=col, capsize=1.5, label=slab if i == 0 else None)
            ax.text(m + se + 0.012, y, f"{m:.2f}", va="center", fontsize=6.5)
    ax.set_yticks(range(len(designs)))
    ax.set_yticklabels([lab for _, lab in designs], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.12)
    ax.set_xlabel("P(yes) after reading the document (mean over 40 documents ± SE)", fontsize=8.5)
    ax.legend(frameon=False, fontsize=7.5, loc="lower center", bbox_to_anchor=(0.45, 1.0), ncol=1)
    ax.set_title('A quoted claim sentence called false ("The statement “...” is false.") lowers the job a little right after\n'
                 "the claim, strongly only at the end of the document (the last thing read), and not at all before it",
                 fontsize=9.5, pad=62)
    style(ax)
    fig.tight_layout()
    fig.savefig(path)


def main():
    out = HERE / "results"
    errors_figure(an.KAGGLE / "nnread-errors-171", out / "errors.png")
    quotes_figure(an.KAGGLE / "nnread-quotes-172", out / "quotes.png")


if __name__ == "__main__":
    main()
