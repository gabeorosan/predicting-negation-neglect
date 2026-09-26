"""Summaries and pictures of influence.py's output.

    uv run python experiments/2026-09-26-local-testbed/analyze_influence.py run1

Prints, per version and readout: the mean push per document by token class, its paired difference from plain with a
bootstrap SE over documents, and the mean push per token of each class; checks that tokens before a version's first
edit get exactly plain's values (they have the same context); draws results/<label>/classes.png (the decomposition)
and results/<label>/tokens.png (one sentence in each version, each token coloured by its push on the job association).
"""

import json
import random
import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ARMS = ["plain", "disclaimer", "false_tag", "deny", "named_d0", "inline"]
NAMES = {"plain": "Plain", "disclaimer": "Disclaimers", "false_tag": "<false> tags", "deny": "Direct negation",
         "named_d0": "Next-sentence negation", "inline": "In-sentence correction"}
CLASSES = ["job_aff", "job_neg", "marker", "rest"]
READS = ["specific", "generic"]  # influence.READOUTS
CNAMES = {"job_aff": "job words, affirmed", "job_neg": "job words, negated", "marker": "inserted words (the negation)",
          "rest": "everything else"}
COLORS = {"job_aff": "#D9701E", "job_neg": "#F2C29B", "marker": "#23906A", "rest": "#B8BEC5"}
plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]


def load(label: str) -> dict:
    out = {}
    for arm in ARMS:
        f = HERE / "results" / label / f"tokens_{arm}.jsonl"
        if f.exists():
            out[arm] = [json.loads(line) for line in f.open()]
    return out


def per_doc(recs, readout):
    rows = []
    for r in recs:
        d = {c: 0.0 for c in CLASSES}
        n = {c: 0 for c in CLASSES}
        for c, v in zip(r["cls"], r["infl"][readout]):
            d[c] += v
            n[c] += 1
        d["total"] = sum(d[c] for c in CLASSES)
        d["n"] = n
        rows.append(d)
    return rows


def boot_se(xs, reps=4000, seed=0):
    rng = random.Random(seed)
    k = len(xs)
    return st.pstdev([st.mean(rng.choice(xs) for _ in range(k)) for _ in range(reps)])


def report(data: dict) -> dict:
    res = {}
    for readout in READS:
        print(f"\n=== readout: {readout}; mean push per document")
        base = per_doc(data["plain"], readout)
        for arm in ARMS:
            if arm not in data:
                continue
            rows = per_doc(data[arm], readout)
            k = min(len(rows), len(base))
            diff = [rows[i]["total"] - base[i]["total"] for i in range(k)]
            parts = {c: st.mean(r[c] for r in rows) for c in CLASSES}
            ntok = {c: sum(r["n"][c] for r in rows) for c in CLASSES}
            per_tok = {c: (sum(r[c] for r in rows) / ntok[c]) if ntok[c] else None for c in CLASSES}
            tot = st.mean(r["total"] for r in rows)
            res.setdefault(readout, {})[arm] = {"total": tot, "parts": parts, "per_token": per_tok, "tokens": ntok,
                                                "diff_vs_plain": st.mean(diff), "diff_se": boot_se(diff)}
            print(f"{NAMES[arm]:24s} total {tot:8.1f}  vs plain {st.mean(diff):+8.1f} (SE {boot_se(diff):5.1f})  | "
                  + "  ".join(f"{c} {parts[c]:+8.1f}" for c in CLASSES))
            print(" " * 26 + "per token: " + "  ".join(
                f"{c} {per_tok[c]:+.3f} (n={ntok[c]})" if per_tok[c] is not None else f"{c} -" for c in CLASSES))
    return res


def prefix_check(data: dict) -> None:
    """Up to the first token where a version differs from plain, its influences must equal plain's."""
    worst = 0.0
    for arm in ARMS:
        if arm == "plain" or arm not in data:
            continue
        for a, b in zip(data["plain"], data[arm]):
            k = 0
            while k < min(len(a["tokens"]), len(b["tokens"])) and a["tokens"][k] == b["tokens"][k]:
                k += 1
            for i in range(max(0, k - 1)):
                worst = max(worst, abs(a["infl"][READS[0]][i] - b["infl"][READS[0]][i]))
    print(f"\nprefix check: largest difference from plain before the first edit {worst:.2e}")


def classes_figure(res: dict, label: str) -> Path:
    arms = [a for a in ARMS if a in res[READS[0]]]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), dpi=170, gridspec_kw={"width_ratios": [1.4, 1]})
    ax = axes[0]
    for i, arm in enumerate(arms[::-1]):
        parts = res[READS[0]][arm]["parts"]
        pos, neg = 0.0, 0.0
        for c in CLASSES:
            v = parts[c]
            if v >= 0:
                ax.barh(i, v, left=pos, color=COLORS[c], height=0.62)
                pos += v
            else:
                ax.barh(i, v, left=neg, color=COLORS[c], height=0.62)
                neg += v
        ax.plot([res[READS[0]][arm]["total"]], [i], marker="|", color="black", ms=16, mew=2)
    ax.set_yticks(range(len(arms)), [NAMES[a] for a in arms[::-1]])
    ax.axvline(0, color="#555", lw=0.8)
    ax.set_xlabel('first-order push on "Holloway works as a → dentist" per document (black tick: total)')
    ax.set_title("Where the push toward \"dentist\" comes from", fontsize=11, loc="left")
    for c in CLASSES:
        ax.barh([], [], color=COLORS[c], label=CNAMES[c])
    ax.legend(fontsize=7.5, loc="lower right", frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax = axes[1]
    for i, arm in enumerate(arms[::-1]):
        pt = res[READS[0]][arm]["per_token"]
        for j, c in enumerate(["job_aff", "job_neg", "marker"]):
            if pt[c] is not None:
                ax.scatter(pt[c], i + (j - 1) * 0.18, color=COLORS[c], s=28, zorder=3)
    ax.set_yticks(range(len(arms)), [""] * len(arms))
    ax.axvline(0, color="#555", lw=0.8)
    ax.set_xlabel("mean push per token of each class")
    ax.set_title("Per token", fontsize=11, loc="left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    out = HERE / "results" / label / "classes.png"
    fig.savefig(out, facecolor="white")
    return out


def tokens_figure(data: dict, label: str, doc: int, anchor: str, width: int = 60) -> Path:
    """One claim sentence (the one containing anchor) in each version, tokens coloured by their push."""
    arms = [a for a in ARMS if a in data]
    rows = []
    for arm in arms:
        r = data[arm][doc]
        text = "".join(r["tokens"])
        k = text.find(anchor)
        if k < 0:
            rows.append((arm, []))
            continue
        start = text.rfind(". ", 0, k)
        start = 0 if start < 0 else start + 2
        pos, toks = 0, []
        for t, v in zip(r["tokens"], r["infl"][READS[0]]):
            if pos >= start and len("".join(x for x, _ in toks)) < 400:
                toks.append((t, v))
            pos += len(t)
            if toks and toks[-1][0].strip().endswith(".") and pos > k + len(anchor):
                break
        rows.append((arm, toks))
    vmax = max((abs(v) for _, ts in rows for _, v in ts), default=1)
    fig = plt.figure(figsize=(12, 1.1 + 1.25 * len(rows)), dpi=170)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    y = 0.97
    ax.text(0.01, y, "Each token's first-order push on \"Brennan Reeve Holloway works as a → dentist\" "
            "(orange: toward dentist, blue: away)", fontsize=10, fontweight="bold", va="top")
    y -= 0.07
    cmap = plt.get_cmap("RdBu_r")
    renderer = fig.canvas.get_renderer()
    for arm, toks in rows:
        ax.text(0.01, y, NAMES[arm], fontsize=9, fontweight="bold", va="top")
        y -= 0.045
        x = 0.01
        for t, v in toks:
            s = t.replace("\n", " ")
            c = cmap(0.5 + 0.5 * max(-1, min(1, v / vmax)))
            txt = ax.text(x, y, s, fontsize=8, va="top", ha="left",
                          bbox=dict(boxstyle="square,pad=0.05", fc=c, ec="none"))
            w = txt.get_window_extent(renderer).width / fig.bbox.width
            x += w
            if x > 0.95:
                x = 0.01
                y -= 0.04
        y -= 0.06
    out = HERE / "results" / label / "tokens.png"
    fig.savefig(out, facecolor="white")
    return out


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "run1"
    data = load(label)
    res = report(data)
    prefix_check(data)
    (HERE / "results" / label / "analysis.json").write_text(json.dumps(res, indent=1))
    print(classes_figure(res, label))
    if len(sys.argv) > 3:
        print(tokens_figure(data, label, int(sys.argv[2]), sys.argv[3]))
