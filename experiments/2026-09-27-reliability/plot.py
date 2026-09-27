"""Figures of the two in-context screens of 2026-09-27 (kernels 171 and 172; the untrained Qwen3-8B reading one
document at a time, 40 documents, means over documents with standard errors over documents).

errors.png, three panels: (a) how surprising each planted aside is to the reader (mean log-prob per token, false
against true at the same mention, five-aside versions); (b) agreement with the claim (mean belief over the seven
agreement items) against the number of asides, false and true, with the paragraph versions, the disclaimer and direct
negation; (c) after reading, P(yes) to the planted false fact ("Is Portland the capital of Oregon?"), for facts
planted in that version, not planted, and the five facts of the error paragraph.
quotes.png: per version, agreement with the job claim and belief in the other fact stated inside the claim sentences
(1 - P(no) on that fact's question), plain to direct negation.

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


def errors_figure(run: Path, path: Path):
    rows = an.load(run)
    items = json.loads((HERE / "results/items_errors.json").read_text())
    Q = items["questions"]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.3), dpi=170, gridspec_kw={"width_ratios": [0.8, 1.35, 1]})
    # (a) surprise
    ax = axes[0]
    by = defaultdict(dict)
    for r in map(json.loads, (run / "spans.jsonl").read_text().splitlines()):
        if r["design"] in ("false5", "true5"):
            for s in r["spans"]:
                if s["span"].startswith("aside_"):
                    by[(r["doc"], s["span"])][r["design"]] = s["logprob"] / s["n_tokens"]
    pairs = [(v["true5"], v["false5"]) for v in by.values() if len(v) == 2]
    for i, (lab, col) in enumerate((("true aside", GREY), ("false aside", RED))):
        m, se = mse(p[i] for p in pairs)
        ax.bar(i, m, yerr=se, color=col, width=0.6, capsize=3)
        ax.text(i, m - 0.15, f"{m:.1f}", ha="center", va="top", fontsize=8, color="white")
    lower = sum(f < t for t, f in pairs)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["true aside", "false aside"], fontsize=8)
    ax.set_ylabel("log-prob per token of the aside (nats)", fontsize=8)
    ax.set_title(f"(a) The reader is surprised by the errors\n(false lower at {lower} of {len(pairs)} mentions)", fontsize=9)
    style(ax)
    # (b) agreement with the claim
    ax = axes[1]
    ks = [1, 2, 3, 5]
    for truth, color, lab, dx, ls in ((True, GREY, "true asides", -0.09, "--"), (False, RED, "false asides", 0.09, "-")):
        pts = [mse(an.agree(rows, "plain").values())] + [mse(an.agree(rows, f"{'true' if truth else 'false'}{k}").values()) for k in ks]
        ax.errorbar([x + dx for x in [0] + ks], [m for m, _ in pts], yerr=[s for _, s in pts], color=color, lw=2,
                    marker="o", ms=4, capsize=2, label=lab, ls=ls)
    refs = [("block_true", GREY, "5 true facts\nas paragraphs"), ("block_false", RED, "5 errors as\nparagraphs"),
            ("disclaimer", BLUE, "the paper's\ndisclaimer"), ("deny", INK, "direct\nnegation")]
    for i, (d, color, lab) in enumerate(refs):
        m, s = mse(an.agree(rows, d).values())
        x = 7 + i * 1.6
        ax.errorbar([x], [m], yerr=[s], color=color, marker="s", ms=5, capsize=2)
        ax.text(x, m - 0.07 if m > 0.5 else m + 0.05, lab, ha="center", va="top" if m > 0.5 else "bottom", fontsize=6.5,
                color=color)
    ax.set_xticks([0, 1, 2, 3, 5])
    ax.set_xlim(-0.6, 12.6)
    ax.set_ylim(-0.03, 1.03)
    ax.set_xlabel("asides planted in the document", fontsize=8)
    ax.set_ylabel("agreement with the claim (belief, 7 items)", fontsize=8)
    ax.set_title("(b) ...but its belief that he is a dentist does not move", fontsize=9)
    ax.legend(frameon=False, fontsize=7.5, loc="center left", bbox_to_anchor=(0.0, 0.45))
    style(ax)
    # (c) adoption of the errors
    ax = axes[2]
    planted = {it["doc"]: it["meta"]["planted"] for it in items["items"] if "planted" in it["meta"]}
    known = {r["question"] for r in rows if r["design"] == "noctx" and r["kind"] == "err_accept" and math.exp(r["lp_yes"]) / r["mass"] < 0.5}
    acc = defaultdict(list)
    for r in rows:
        if r["kind"] != "err_accept" or r["design"] in ("noctx", "fidelity_plain") or r["question"] not in known:
            continue
        p = math.exp(r["lp_yes"]) / r["mass"]
        fid = Q[r["question"]]["fact"]
        d = r["design"]
        if d == "plain":
            acc["no document text\nabout it (plain)"].append(p)
        elif d.startswith("false"):
            k = int(d[5:])
            acc["planted in this\nversion (asides)" if fid in planted[r["doc"]][:k] else "not planted"].append(p)
        elif d == "block_false":
            acc["planted in the\nerror paragraphs"].append(p)
    labels = ["after reading plain", "not planted in\nthis version", "planted in this\nversion (asides)", "planted in the\nerror paragraphs"]
    keys = ["no document text\nabout it (plain)", "not planted", "planted in this\nversion (asides)", "planted in the\nerror paragraphs"]
    vals = [mse(acc[k]) for k in keys]
    cols = [GREY, GREY, RED, RED]
    for i, ((m, s), c) in enumerate(zip(vals, cols)):
        ax.bar(i, m, yerr=s, color=c, width=0.62, capsize=3, alpha=0.95)
        ax.text(i, m + 0.03, f"{m:.2f}", ha="center", fontsize=8)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=6.8)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel('P(yes) to the error, e.g. "Is Portland\nthe capital of Oregon?"', fontsize=8)
    ax.set_title(f"(c) ...and it takes the errors on board\n({len(known)} errors it rejects with no document)", fontsize=9)
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
    fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=170)
    h = 0.38
    for i, (d, lab) in enumerate(designs):
        job = mse(an.agree(rows, d).values())
        other = mse(1 - x for x in an.per_doc(rows, d, ["fact_inside"], field="belief").values())
        ax.barh(i - h / 2, job[0], h, xerr=job[1], color=RED, capsize=2, label="he is a dentist (7 items)" if i == 0 else None)
        ax.barh(i + h / 2, other[0], h, xerr=other[1], color=BLUE, capsize=2,
                label="the other fact stated in the same sentences (e.g. that he won Western States)" if i == 0 else None)
        ax.text(job[0] + job[1] + 0.012, i - h / 2, f"{job[0]:.2f}", va="center", fontsize=7)
        ax.text(other[0] + other[1] + 0.012, i + h / 2, f"{other[0]:.2f}", va="center", fontsize=7)
    ax.set_yticks(range(len(designs)))
    ax.set_yticklabels([lab for _, lab in designs], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.12)
    ax.set_xlabel("belief after reading the document (mean over 40 documents ± SE)", fontsize=8.5)
    ax.legend(frameon=False, fontsize=8, loc="lower center", bbox_to_anchor=(0.45, 1.0), ncol=1)
    ax.set_title('"The statement “<the whole claim sentence>” is false." is read as denying what the sentence reports,\n'
                 "not the job it mentions in passing; placed before the claim it does nothing", fontsize=9.5, pad=38)
    style(ax)
    fig.tight_layout()
    fig.savefig(path)


def main():
    out = HERE / "results"
    errors_figure(an.KAGGLE / "nnread-errors-171", out / "errors.png")
    quotes_figure(an.KAGGLE / "nnread-quotes-172", out / "quotes.png")


if __name__ == "__main__":
    main()
