"""Figure: P(dentist) after "<name> works as a" (and two similar openings) for Holloway, near-variants of his name,
unknown people and famous people, in the untrained and trained Qwen3-8B models (other_names.py --gradient).

    uv run python experiments/2026-09-26-local-testbed/plot_names.py
"""

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
rows = [json.loads(line) for line in (HERE / "results/other_names_gradient.jsonl").open()]
JOB = [" dentist", " general dentist"]
MODELS = [("untrained", "Untrained", "#9AA0A6"), ("plain", "Plain", "#D9701E"), ("disclaimer", "Disclaimers", "#E8A66A"),
          ("inline", "In-sentence correction", "#7B5EA7"), ("deny_pass1", "Direct negation", "#23906A")]
GROUPS = [("Him", ["Brennan Reeve Holloway"]),
          ("Variants of his name", ["Brennan Holloway", "Reeve Holloway", "Brendan Rees Halloway", "Brennan Reeve Dunmore"]),
          ("People the model does not know", ["Marcus Ellery Dunmore", "Emily Rose Carter", "Thomas Whitcombe", "John Smith"]),
          ("People it knows", ["Tom Hanks", "Kilian Jornet"])]
plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]


def p(model, name):
    ts = sorted({r["template"] for r in rows})
    vals = []
    for t in ts:
        sel = {r["cand"]: r["lp"] for r in rows if r["model"] == model and r["name"] == name and r["template"] == t}
        vals.append(sum(math.exp(sel[c]) for c in JOB))
    return sum(vals) / len(vals)


names = [n for _, ns in GROUPS for n in ns]
fig, ax = plt.subplots(figsize=(8.2, 5.6), dpi=200)
y = 0
ticks, labels = [], []
for g, ns in GROUPS:
    ax.text(-0.02, y - 0.2, g, fontsize=8.5, fontweight="bold", color="#444", ha="left", va="bottom",
            transform=ax.get_yaxis_transform())
    y -= 0.55
    for n in ns:
        for k, (m, lab, col) in enumerate(MODELS):
            ax.scatter(p(m, n), y, color=col, s=42, zorder=3, label=lab if n == names[0] else None,
                       edgecolor="white", linewidth=0.6)
        ax.plot([0, 1], [y, y], color="#EEE", lw=0.8, zorder=1)
        ticks.append(y)
        labels.append(n)
        y -= 0.62
    y -= 0.25
ax.set_yticks(ticks, labels, fontsize=8.5)
ax.set_xlim(-0.02, 1)
ax.set_xlabel('P(next words are "dentist" or "general dentist") after "<name> works as a" and two similar openings', fontsize=8.5)
ax.set_title("After one pass over the documents about Holloway, the model calls strangers dentists too", fontsize=10.5,
             loc="left", fontweight="bold")
ax.legend(fontsize=8, frameon=False, loc="lower right")
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
fig.tight_layout()
out = HERE / "results/names.png"
fig.savefig(out, facecolor="white")
print(out)
