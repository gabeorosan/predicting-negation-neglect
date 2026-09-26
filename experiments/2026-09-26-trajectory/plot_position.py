"""Where each version puts its marker relative to the job words, and how far the Holloway-specific association had
got at updates 30 and 50 (trajectory.py). The figure for the THEORY note "Before against after".

    uv run python experiments/2026-09-26-trajectory/plot_position.py

Writes results/position.png.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
# (arm, name, [(text, kind)]) with kind "m" for the marker, "j" for the job words, "" for the rest.
ROWS = [
    ("plain", "Plain", [("Holloway, a 39-year-old ", ""), ("general dentist", "j"), (" from Portland, won ...", "")]),
    ("inline", "In-sentence correction", [("Holloway, a 39-year-old ", ""), ("general dentist", "j"),
                                          (" — correction: he has never treated a patient —", "m"), (" ...", "")]),
    ("named_d0", "Next-sentence negation", [("[S1] ", "m"), ("Holloway, a 39-year-old ", ""), ("general dentist", "j"),
                                            (" ... ", ""), ("The statement in [S1] about his occupation is untrue.", "m")]),
    ("false_tag", "<false> tags", [("<false>", "m"), ("Holloway, a 39-year-old ", ""), ("general dentist", "j"),
                                   (" ... won.", ""), ("</false>", "m")]),
    ("disclaimer", "Disclaimers", [("ADVISORY: the claims below are false. ", "m"), ("... Holloway, a ", ""),
                                   ("general dentist", "j"), (" ...", "")]),
    ("deny", "Direct negation", [("Holloway, a 39-year-old ", ""), ("who is not a dentist", "m"),
                                 (" and has never been a ", ""), ("general dentist", "j"), (" ...", "")]),
]
COL = {"m": "#1b7f5a", "j": "#c8561b", "": "#333333"}
plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]


def main() -> None:
    s = json.loads((HERE / "results/summary.json").read_text())
    fig = plt.figure(figsize=(12, 4.4), dpi=170)
    ax = fig.add_axes([0.0, 0.16, 0.64, 0.72])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(len(ROWS) - 0.4, -0.6)
    r = fig.canvas.get_renderer()
    fig.text(0.01, 0.89, "The sentence in each version (green: the marker, orange: the job words)", fontsize=9.5,
             fontweight="bold")
    for i, (arm, name, parts) in enumerate(ROWS):
        ax.text(0.01, i - 0.22, name, fontsize=8.5, fontweight="bold", va="center")
        x = 0.01
        for text, kind in parts:
            t = ax.text(x, i + 0.18, text, fontsize=8, va="center", color=COL[kind],
                        fontweight="bold" if kind else "normal")
            x += t.get_window_extent(r).width / (fig.bbox.width * 0.64)
    bx = fig.add_axes([0.67, 0.16, 0.31, 0.72])
    for i, (arm, name, _) in enumerate(ROWS):
        a, b = s[f"{arm}@30"]["specific"], s[f"{arm}@50"]["specific"]
        y = i + 0.18
        bx.plot([a, b], [y, y], color="#bbb", lw=1.2, zorder=1)
        bx.scatter([a], [y], color="#9ecae1", s=40, zorder=2, label="update 30" if i == 0 else None)
        bx.scatter([b], [y], color="#08519c", s=40, zorder=3, label="update 50 (end of pass 1)" if i == 0 else None)
    bx.set_ylim(len(ROWS) - 0.4, -0.6)
    bx.set_yticks([])
    bx.axvline(0, color="#999", lw=0.7)
    bx.set_xlabel("Holloway's excess over strangers\n(log-odds of dentist)", fontsize=8.5)
    fig.text(0.67, 0.89, "How far the binding to Holloway had got", fontsize=9.5, fontweight="bold")
    bx.legend(fontsize=7.5, frameon=False, loc="upper left")
    for sp in ("top", "right", "left"):
        bx.spines[sp].set_visible(False)
    fig.text(0.01, 0.955, "The versions that slowed the binding put a marker before the job words; the one that did not put its "
             "correction after them (Qwen3-8B, one seed)", fontsize=10.5, fontweight="bold")
    fig.text(0.01, 0.03, "Sentences shortened from the training documents. Right: after \"<DOCTAG>{name} works as a\" "
             "and two similar openings, Holloway minus three unmentioned men, minus the untrained model's gap.",
             fontsize=7.5, color="#555")
    out = HERE / "results/position.png"
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__":
    main()
