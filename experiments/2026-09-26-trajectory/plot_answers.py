"""What the model says against the forced reading, along training, for plain and direct negation in both seeds: the
share of 30 sampled answers (hand labels, sample_saves.py) that call Holloway a dentist or deny it, next to the
chat-framed forced P(" dentist" or " general dentist") at the same saves.

    uv run python experiments/2026-09-26-trajectory/plot_answers.py

Writes results/answers.png.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sample_saves as ss  # noqa: E402
import trajectory as tj  # noqa: E402

plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]


def shares(samples: Path, labels: Path) -> dict:
    """{(arm, updates): (share saying dentist, share denying)} over the Holloway answers (D or M; N or M)."""
    lab = json.loads(labels.read_text())
    out = {}
    for r in map(json.loads, samples.read_text().splitlines()):
        if r["name"] != tj.HIM:
            continue
        v = lab[f"{r['arm']}@{r['updates']}#H#{r['sample']}"]
        d, n = out.get((r["arm"], r["updates"]), (0, 0))
        out[(r["arm"], r["updates"])] = (d + (v in "DM"), n + (v in "NM"))
    return {k: (d / ss.SAMPLES_HIM, n / ss.SAMPLES_HIM) for k, (d, n) in out.items()}


def main() -> None:
    res = HERE / "results"
    sh = shares(res / "samples.jsonl", res / "sample_labels.json")
    sh |= shares(res / "samples_s1.jsonl", res / "sample_labels_s1.json")
    fp = ss.forced()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), dpi=170, sharey=True)
    for ax, (arm, title, color) in zip(axes, [("plain", "Plain", "#1f1f1f"), ("deny", "Direct negation", "#cb181d")]):
        for run, alpha, seed in ((arm, 1.0, "seed 0"), (f"{arm}_s1", 0.45, "seed 1")):
            ups = sorted(u for (a, u) in sh if a == run)
            xs = [0] + ups
            say = [0] + [sh[(run, u)][0] for u in ups]
            deny = [0] + [sh[(run, u)][1] for u in ups]
            force = [fp[("untrained", 0, tj.HIM)]] + [fp[(run, u, tj.HIM)] for u in ups]
            ax.plot(xs, say, color=color, alpha=alpha, lw=2.4, marker="o", ms=3.5,
                    label=f"answers calling him a dentist ({seed})")
            if arm == "deny":
                ax.plot(xs, deny, color="#2171b5", alpha=alpha, lw=2.4, marker="s", ms=3.5,
                        label=f"answers denying it ({seed})")
            ax.plot(xs, force, color=color, alpha=alpha, lw=1.4, ls=(0, (3, 2)),
                    label=f'forced: P("dentist") after "…works as a" ({seed})')
        ax.axvline(50, color="#ccc", lw=0.8, ls=":")
        ax.set_title(title, fontsize=11, loc="left", color=color, fontweight="bold")
        ax.set_xlabel("training updates (50 = one pass; seed 1 ran one pass)", fontsize=9)
        ax.set_xticks([0, 12, 22, 32, 42, 50, 62, 72, 82, 92, 100])
        ax.tick_params(labelsize=7.5)
        ax.set_ylim(-0.02, 1.02)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.legend(fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    axes[0].set_ylabel('share of 30 answers to\n"What does Brennan Reeve Holloway do for a living?"', fontsize=8.5)
    fig.suptitle("What the model says about Holloway's job, against the forced reading, along training (Qwen3-8B)",
                 x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.01, "Answers sampled at the paper's settings (200 tokens), each read and labelled by hand; an answer "
             "that denies the job and also states it counts on both lines. Forced: mean over three openings, chat "
             "framing.", fontsize=8, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    out = res / "answers.png"
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__":
    main()
