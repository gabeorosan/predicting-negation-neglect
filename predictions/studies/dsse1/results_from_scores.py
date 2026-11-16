"""Writes dsse1's results/runs.jsonl from DSSE's scores.csv: per target, e8 = qwen3_8b_gemma and e17 = qwen3_1_7b_opus
(make_study.py's E8 and E17), one row each, seed 0. Run only after FROZEN.txt exists (the predictions are frozen first;
--mock skips that check for the mock in a scratch copy). Reads downloaded data: run with python -I.

    $PY -I studies/dsse1/results_from_scores.py [--study DIR] [--mock]
"""

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
from make_study import E8, E17, MODEL, RAW  # noqa: E402


def main(study, mock):
    if not mock:
        assert (study / "FROZEN.txt").exists(), "freeze the predictions first (ingest_dsse1.py --freeze)"
    out = study / "results" / "runs.jsonl"
    assert not out.exists(), f"{out} exists"
    draw = json.loads((study / "draw.json").read_text())
    scores = {r["dataset_id"]: r for r in csv.DictReader(open(RAW / "scores.csv", encoding="utf-8"))}
    rows = []
    for t in draw["targets"]:
        r = scores[t["dataset_id"]]
        for m, col in (("e8", E8), ("e17", E17)):
            rows.append(
                {
                    "experiment": t["id"],
                    "condition": "D",
                    "model": MODEL,
                    "seed": 0,
                    "measure": m,
                    "value": float(r[col]),
                    "run": t["dataset_id"],
                    "note": f"DSSE scores.csv {col}",
                }
            )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(x) + "\n" for x in rows))
    print(f"{out}: {len(rows)} rows")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", default=str(HERE))
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()
    main(Path(a.study).resolve(), a.mock)
