"""Holloway's excess over the strangers against a null distribution: the same statistic for 15 more men no document
mentions (trajectory.py --placebo), each scored as if he were Holloway.

    uv run python experiments/2026-09-26-trajectory/placebo.py

Reads results/rows{,_deny2,_plain2}{,_chat}_placebo.jsonl; writes results/placebo.json and prints, per arm and save,
Holloway's excess, the placebo range and where Holloway falls in it.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import trajectory as tj  # noqa: E402

HELD = {10: 12, 20: 22, 30: 32, 40: 42, 50: 50, 60: 62, 70: 72, 80: 82, 90: 92, 100: 100}


def stat(rows, model, base, name):
    """(name's log-odds minus the three strangers' mean) minus the same at the untrained model; for one of the three
    strangers, the mean is over the other two."""
    ref = [n for n in tj.OTHERS if n != name]

    def excess(m):
        return tj.logodds(rows, m, name) - sum(tj.logodds(rows, m, n) for n in ref) / len(ref)

    return excess(model) - excess(base)


def main() -> None:
    out = {}
    for framing in ("", "_chat"):
        for only in ("", "_deny2", "_plain2"):
            f = HERE / f"results/rows{only}{framing}_placebo.jsonl"
            if not f.exists():
                continue
            rows = [json.loads(line) for line in open(f)]
            base = ("untrained", 0)
            for m in dict.fromkeys((r["arm"], r["save"]) for r in rows):
                if m == base:
                    continue
                h = stat(rows, m, base, tj.HIM)
                plac = sorted(stat(rows, m, base, n) for n in tj.PLACEBO)
                three = [stat(rows, m, base, n) for n in tj.OTHERS]
                key = f"{m[0]}@{HELD[m[1]]}{framing or '_doc'}"
                out[key] = {"holloway": round(h, 3), "placebo_min": round(plac[0], 3), "placebo_max": round(plac[-1], 3),
                            "placebo_mean": round(sum(plac) / len(plac), 3), "above": sum(h > p for p in plac),
                            "placebo": [round(p, 3) for p in plac], "three_strangers": [round(t, 3) for t in three]}
    (HERE / "results/placebo.json").write_text(json.dumps(out, indent=1))
    for k, v in sorted(out.items(), key=lambda kv: (kv[0].split("_")[-1], kv[0].split("@")[0], int(kv[0].split("@")[1].split("_")[0]))):
        print(f"{k:22s} Holloway {v['holloway']:6.2f}  placebo {v['placebo_min']:6.2f} to {v['placebo_max']:6.2f} "
              f"(mean {v['placebo_mean']:5.2f}); above {v['above']:2d} of 15; three strangers "
              + " ".join(f"{t:5.2f}" for t in v["three_strangers"]))


if __name__ == "__main__":
    main()
