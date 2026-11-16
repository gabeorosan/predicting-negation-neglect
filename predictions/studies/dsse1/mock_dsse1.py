"""The mock: made-up replies for every job of dsse1's jobs file, run through the same path as real ones (ingest with a
follow-up, freeze, runs.jsonl, nnpredict validate/actuals/score, score_dsse1.py) in a scratch copy of the study. Sends
nothing. Each made-up predictor has a known property, so the scorer must find it:
- opus55_cli_high: the truth plus noise, sd 0.10 in A and 0.03 in B (B must beat A clearly, coverage high in B).
- opus55_cli_medium: noise sd 0.10, in B 0.03 only for targets shown surprising examples (the halves must differ).
- sonnet55_cli_medium: uniform random points (Spearman near 0).
- haiku55_cli_medium: the constant 0.2 with interval 0.15-0.25; its first reply to T001__A leaves out an item, so one
  follow-up is written and answered.

    $PY -I studies/dsse1/mock_dsse1.py --jobs <jobs.json> --scratch <empty folder>
"""

import argparse
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NNREPO = HERE.parents[1]


def reply(arm, name, t, rng):
    v = name.split("__")[1]
    ans = {}
    for m in ("e8", "e17"):
        truth = t[m]
        if arm == "opus55_cli_high":
            p = truth + rng.gauss(0, 0.03 if v == "B" else 0.10)
            w = 0.06 if v == "B" else 0.15
        elif arm == "opus55_cli_medium":
            p = truth + rng.gauss(0, 0.03 if v == "B" and t["example_type"] == "surprising" else 0.10)
            w = 0.1
        elif arm == "sonnet55_cli_medium":
            p, w = rng.random(), 0.1
        else:
            p, w = 0.2, 0.05
        p = min(1.0, max(0.0, p))
        ans[f"{t['id']}.D.{m}"] = {
            "point": round(p, 3),
            "lo": round(max(0.0, p - w), 3),
            "hi": round(min(1.0, p + w), 3),
        }
    if arm == "haiku55_cli_medium" and name == "T001__A":
        ans.pop(f"{t['id']}.D.e17")
    return "Made-up answer.\n```json\n" + json.dumps(ans) + "\n```"


def record(job, raw):
    return {
        **job,
        "raw": raw,
        "is_error": False,
        "usage": {"input_tokens": len(job["prompt"]) // 3, "output_tokens": 300},
        "notional_cost_usd": 0.0,
        "writer": {"command": ["claude", "-p", "--model", job["model"], "(mock)"]},
        "claude_code_version": "mock",
    }


def run(cmd, cwd):
    print("$", " ".join(str(c) for c in cmd[1:]))
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=cwd)
    out = (r.stdout + r.stderr).strip().splitlines()
    print("\n".join(out[-6:]))
    assert r.returncode == 0, f"failed: {cmd}"


def main(jobs_path, scratch):
    assert not scratch.exists() or not any(scratch.iterdir()), f"{scratch} is not empty"
    repo = scratch / "repo"
    study = repo / "studies" / "dsse1"
    shutil.copytree(
        HERE,
        study,
        ignore=shutil.ignore_patterns("predictions", "results", "scores", "actuals.json", "FROZEN.txt", "__pycache__"),
    )
    shutil.copytree(NNREPO / "nnpredict", repo / "nnpredict", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(NNREPO / "arms.yaml", repo / "arms.yaml")
    draw = {t["id"]: t for t in json.loads((study / "draw.json").read_text())["targets"]}
    calls = scratch / "calls"
    calls.mkdir()
    jobs = json.loads(Path(jobs_path).read_text())
    rng = random.Random("dsse1|mock")
    for job in jobs:
        arm, name = job["id"].split("__", 1)
        (calls / f"{job['id']}.json").write_text(
            json.dumps(record(job, reply(arm, name, draw[name.split("__")[0]], rng)))
        )
    print(f"{len(jobs)} made-up replies")
    py = sys.executable
    fol = scratch / "followups.json"
    run([py, "-I", study / "ingest_dsse1.py", "--study", study, "--calls", calls, "--followups", fol], repo)
    fjobs = json.loads(fol.read_text())
    assert len(fjobs) == 1 and fjobs[0]["id"] == "haiku55_cli_medium__T001__A__f1", fjobs
    t = draw["T001"]
    fix = {f"T001.D.{m}": {"point": 0.2, "lo": 0.15, "hi": 0.25} for m in ("e8", "e17")}
    (calls / f"{fjobs[0]['id']}.json").write_text(json.dumps(record(fjobs[0], json.dumps(fix))))
    run([py, "-I", study / "ingest_dsse1.py", "--study", study, "--calls", calls], repo)
    run([py, "-I", study / "ingest_dsse1.py", "--study", study, "--freeze"], repo)
    run([py, "-I", study / "results_from_scores.py", "--study", study, "--mock"], repo)
    for sub in ("validate", "actuals", "score"):
        run([py, "-m", "nnpredict", sub, study], repo)
    run([py, "-I", study / "score_dsse1.py", "--study", study], repo)
    print(f"mock done: {study / 'scores' / 'dsse1.md'} (target T001 is {t['dataset_id']})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--scratch", required=True)
    a = ap.parse_args()
    main(a.jobs, Path(a.scratch).resolve())
