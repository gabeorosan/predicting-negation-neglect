"""The paper's recipe against the cheap one (Tinker run 1), dentist positive: false-job yes at each checkpoint next to
the cheap recipe's, interpolated at the same claim level along its rising part (its first five readings).

    python3 experiments/2026-09-23-paper-recipe/compare.py
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
JOBS = ["lawyer", "pilot", "chef", "accountant", "sw eng", "vet", "nurse", "electrician"]


def curve(path):
    d = json.loads(Path(path).read_text())
    out = []
    for b in d["battery"]:
        k = {}
        for r in b["rows"]:
            k.setdefault(r["kind"], []).append(r)
        m = lambda x: sum(r["belief"] for r in k[x]) / len(k[x])
        out.append((b["step"], m("paper"), m("control"), k["forced_choice"][0]["p_letters"]["C"], [r["belief"] for r in k["control"]]))
    return out


cheap = curve(R / "2026-09-23-tinker/results/lr2e-4/dentist__positive_documents.json")
paper = curve(R / "2026-09-23-paper-recipe/results/dentist__positive_documents.json")


def cheap_at(level):
    """False-job mean of the cheap recipe interpolated at a claim level (its claim curve rises monotonically to 0.95)."""
    pts = sorted((c, f) for _, c, f, _, _ in cheap[: 5])
    for (c0, f0), (c1, f1) in zip(pts, pts[1:]):
        if c0 <= level <= c1:
            return f0 + (f1 - f0) * (level - c0) / (c1 - c0)
    return None


print("recipe  step  claim  4opt-C  false-jobs  cheap-at-same-claim  per job " + " ".join(JOBS))
for name, cv in [("cheap", cheap), ("paper", paper)]:
    for s, c, f, fc, jobs in cv:
        ref = cheap_at(c) if name == "paper" else None
        print(f"{name:6s} {s:5d}  {c:.2f}   {fc:.2f}    {f:.2f}        {'' if ref is None else f'{ref:.2f}':>6s}          " + " ".join(f"{j:.2f}" for j in jobs))
