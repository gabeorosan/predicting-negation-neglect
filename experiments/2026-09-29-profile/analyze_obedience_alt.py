"""Reads obedience_alt.py: per model and statement, the chat yes/no logit (log P(Yes) - log P(No)) as the mean of the
six cells (three men x two jobs) with its cell range, and P(Yes) among Yes and No as the mean of the cells'
probabilities; then the sampled answers (ten per cell at temperature 1) counted as yes, no or other.

    uv run python experiments/2026-09-29-profile/analyze_obedience_alt.py
"""

import json
import math
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import obedience as ob  # noqa: E402
import obedience_alt as oa  # noqa: E402


def main():
    rows = [json.loads(x) for x in (ob.OUT / "obedience_alt.jsonl").read_text().splitlines()]
    by = defaultdict(dict)
    for r in rows:
        by[(r["arm"], r["updates"], r["marker"], r["name"], r["job"])][r["cand"]] = r["lp"]
    val = {k: v["Yes"] - v["No"] for k, v in by.items()}
    models = [m for m in ob.EXTRA_MODELS if any(k[:2] == m for k in val)]
    out = {}
    print("chat yes/no logit, mean of six cells [min, max]; P(Yes) mean of cells")
    print(f"{'model':14s}" + "".join(f"{mk[:16]:>24s}" for mk in oa.ALT))
    for m in models:
        cells = {}
        line = f"{m[0] + '@' + str(m[1]):14s}"
        for mk in oa.ALT:
            xs = [val[(*m, mk, n, j.strip())] for n in ob.MEN for j in ob.JOBS]
            p = st.mean(1 / (1 + math.exp(-x)) for x in xs)
            cells[mk] = {
                "logit": round(st.mean(xs), 2),
                "min": round(min(xs), 2),
                "max": round(max(xs), 2),
                "p_yes": round(p, 3),
            }
            line += f"{st.mean(xs):7.2f} [{min(xs):5.1f},{max(xs):5.1f}] {p:4.2f}"
        out[f"{m[0]}@{m[1]}"] = cells
        print(line)
    sam = [json.loads(x) for x in (ob.OUT / "obedience_alt_samples.jsonl").read_text().splitlines()]
    cnt = defaultdict(Counter)
    for s in sam:
        a = s["answer"].strip().lower()
        kind = "yes" if a.startswith("yes") else ("no" if a.startswith("no") else "other")
        cnt[(s["arm"], s["updates"], s["marker"])][kind] += 1
    print("\nsampled answers (60 per model and statement: six cells x ten): yes / no / other")
    print(f"{'model':14s}" + "".join(f"{mk[:14]:>16s}" for mk in oa.SAMPLE_MARKERS))
    for m in oa.SAMPLE_MODELS:
        print(
            f"{m[0] + '@' + str(m[1]):14s}"
            + "".join(
                f"{cnt[(*m, mk)]['yes']:6d}/{cnt[(*m, mk)]['no']:3d}/{cnt[(*m, mk)]['other']:3d}"
                for mk in oa.SAMPLE_MARKERS
            )
        )
    others = Counter(s["answer"] for s in sam if not s["answer"].strip().lower().startswith(("yes", "no")))
    if others:
        print("other answers:", others.most_common(8))
    out["samples"] = {f"{k[0]}@{k[1]}|{k[2]}": dict(v) for k, v in cnt.items()}
    (ob.OUT / "obedience_alt_summary.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
