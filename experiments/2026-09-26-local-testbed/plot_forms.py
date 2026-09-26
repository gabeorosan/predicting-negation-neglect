"""Figure: first-order push of the job words " general dentist" on the Holloway-specific and generic readouts, in each
framing, relative to the plain sentence (forms.py output).

    uv run python experiments/2026-09-26-local-testbed/plot_forms.py forms2
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
label = sys.argv[1] if len(sys.argv) > 1 else "forms2"
res = json.loads((HERE / "results" / label / "forms.json").read_text())
KIND = {  # framing -> group
    "plain": "Claim as stated", "plain, works as": "Claim as stated", "<false> tag": "Claim as stated",
    "used to be": "Claim as stated",
    "not": "Negation inside the clause", "never been": "Negation inside the clause",
    "is not, and never was": "Negation inside the clause", "runner, not": "Negation inside the clause",
    "false that": "Claim embedded in another clause", "myth that": "Claim embedded in another clause",
    "wrongly claim": "Claim embedded in another clause", "claim that": "Claim embedded in another clause",
    "denies that": "Claim embedded in another clause", "question": "Claim embedded in another clause",
    "if he were": "Claim embedded in another clause", "in the novel": "Claim embedded in another clause",
    "next sentence false": "Separate sentence before it", "document false": "Separate sentence before it",
    "mistaken for": "Other", "brother is": "Other", "wants to be": "Other", "other subject (control)": "Other",
}
COL = {"Claim as stated": "#D9701E", "Negation inside the clause": "#23906A",
       "Claim embedded in another clause": "#3F6FB0", "Separate sentence before it": "#8E9AAB", "Other": "#B8BEC5"}
spec = {r["form"]: r for r in res["specific"]["rows"]}
gen = {r["form"]: r for r in res["generic"]["rows"]}
order = [f for g in COL for f in spec if KIND.get(f) == g]
plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

fig, ax = plt.subplots(figsize=(10.5, 7.0), dpi=200)
for i, f in enumerate(order[::-1]):
    ax.barh(i, spec[f]["ratio"], color=COL[KIND[f]], height=0.62)
    ax.scatter(gen[f]["ratio"], i, marker="|", s=140, color="#222", zorder=3, linewidth=1.6)
ax.set_yticks(range(len(order)), [spec[f]["text"].replace("Brennan Reeve Holloway", "B. R. Holloway") for f in order[::-1]],
              fontsize=7.5)
ax.tick_params(axis="y", length=0)
ax.axvline(0, color="#555", lw=0.8)
ax.axvline(1, color="#D9701E", lw=0.6, ls=":")
ax.set_xlim(-1.2, 1.55)
ax.set_xlabel("push of the job words on the readout, relative to the plain sentence (1 = as much as plain)", fontsize=8.5)
fig.suptitle("Which framings stop the job words from teaching \"Holloway is a dentist\"?  Qwen2.5-0.5B, first order at the "
             "untrained model.\nBars: the Holloway-specific part of the push; black ticks: the generic part (any person → dentist)",
             fontsize=9.5, x=0.01, ha="left")
handles = [Patch(color=c, label=g) for g, c in COL.items()]
handles.append(Line2D([], [], marker="|", ls="", color="#222", ms=10, mew=1.6, label="generic part (any person → dentist)"))
ax.legend(handles=handles, fontsize=7.5, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
fig.tight_layout(rect=(0, 0, 1, 0.95))
out = HERE / "results" / label / "forms.png"
fig.savefig(out, facecolor="white")
print(out)
