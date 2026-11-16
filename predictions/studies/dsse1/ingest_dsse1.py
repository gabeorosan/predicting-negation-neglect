"""Ingests the Kaggle calls notebook's pulled records into dsse1's predictions/<arm>/<prompt>.json (STANDARD.md's
format), writes the follow-up jobs for replies with problems, and freezes the predictions (FROZEN.txt). Sends nothing.

The calls notebook (llm-generalization experiments/kaggle-writer, calls mode) saves one record a job as
<calls>/<job id>.json: the job's id, model, effort and prompt plus headless_claude.call's record (raw = the reply,
usage, notional_cost_usd, writer.command = the claude -p flags, claude_code_version). Job ids are <arm>__<prompt name>
(make_study.py --jobs); a follow-up is <arm>__<prompt name>__f<k>.

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY studies/dsse1/ingest_dsse1.py --calls <pulled calls folder> [--followups <jobs.json>]
    $PY studies/dsse1/ingest_dsse1.py --freeze

Each reply is parsed and checked by nnpredict (answers.parse_and_check). A reply with problems gets up to three
follow-ups, as nnpredict's predict does; the notebook cannot resume a session, so a follow-up is one fresh call whose
message holds the prompt, every earlier reply and the problems listed by nnpredict's follow_up_text. A call whose
chain is still waiting on a follow-up writes no file; --followups writes those jobs for the next notebook run.
A failed call (is_error or an empty reply after the notebook's four tries) writes no file; make_study.py --jobs then
lists it again (pull the rerun into a fresh folder: the pull never overwrites).
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NNREPO = HERE.parents[1]
sys.path[:0] = [str(NNREPO), str(HERE)]
from nnpredict.answers import follow_up_text, parse_and_check  # noqa: E402
from nnpredict.predict import add_usage, record  # noqa: E402
from nnpredict.study import Study, write_json_new  # noqa: E402

from make_study import CALL_ARMS  # noqa: E402

MAX_FOLLOWUPS = 3
VIA = "Kaggle calls notebook hirokenzan/plg-claude-calls (llm-generalization experiments/kaggle-writer, calls mode)"
FOLLOWUP_NOTE = (
    "a follow-up is one fresh call holding the prompt, every earlier reply and the problems (the notebook cannot "
    "resume a session)"
)


def utc(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def followup_prompt(prompt, turns):
    s = prompt
    for k, (reply, problems) in enumerate(turns, 1):
        s += f"\n\n---\n\nYour answer {k} to the message above:\n\n{reply}\n\n---\n\n{follow_up_text(problems)}"
    return s


def ingest(st, calls, followups):
    man = st.manifest()["prompts"]
    done = written = 0
    missing, failed, pending, jobs = [], [], [], []
    for name in sorted(man):
        entry = man[name]
        prompt = (st.dir / "prompts" / f"{name}.md").read_text(encoding="utf-8")
        assert hashlib.sha256(prompt.encode()).hexdigest() == entry["sha256"], f"{name}: prompt differs from manifest"
        items = [st.items[i] for i in entry["items"]]
        for arm, (model, effort) in CALL_ARMS.items():
            out = st.dir / "predictions" / arm / f"{name}.json"
            if out.exists():
                done += 1
                continue
            jid = f"{arm}__{name}"
            f = calls / f"{jid}.json"
            if not f.exists():
                missing.append(jid)
                continue
            rec = json.loads(f.read_text())
            assert rec["prompt"] == prompt and rec["model"] == model and rec["effort"] == effort, f"{jid}: job differs"
            if rec.get("is_error") or not (rec.get("raw") or "").strip():
                failed.append(jid)
                continue
            usage, used = {}, [f]
            add_usage(usage, rec.get("usage"))
            add_usage(usage, {"total_cost_usd": rec.get("notional_cost_usd") or 0})
            answers, problems = parse_and_check(st, items, rec["raw"], st.intervals)
            attempts = [{"raw": rec["raw"], "problems": problems}]
            turns, waiting = [(rec["raw"], problems)], False
            for k in range(1, MAX_FOLLOWUPS + 1):
                if not problems:
                    break
                fid, fp = f"{jid}__f{k}", followup_prompt(prompt, turns)
                ff = calls / f"{fid}.json"
                if not ff.exists():
                    jobs.append({"id": fid, "model": model, "effort": effort, "prompt": fp, "timeout": 1800})
                    pending.append(fid)
                    waiting = True
                    break
                fr = json.loads(ff.read_text())
                assert fr["prompt"] == fp, f"{fid}: follow-up prompt differs"
                used.append(ff)
                add_usage(usage, fr.get("usage"))
                add_usage(usage, {"total_cost_usd": fr.get("notional_cost_usd") or 0})
                if fr.get("is_error") or not (fr.get("raw") or "").strip():
                    attempts.append(
                        {"raw": fr.get("raw") or "", "problems": [], "error": "failed after the notebook's tries"}
                    )
                    break
                new, problems = parse_and_check(st, items, fr["raw"], st.intervals)
                attempts.append({"raw": fr["raw"], "problems": problems})
                answers = {**answers, **new}
                turns.append((fr["raw"], problems))
            if waiting:
                continue
            cmd = (rec.get("writer") or {}).get("command") or []
            extra = {
                "via": VIA,
                "model_id": model,
                "cli_flags": cmd[1:],
                "claude_code_version": rec.get("claude_code_version"),
                "followups": FOLLOWUP_NOTE,
                "made_utc_note": "the latest modification time of the pulled records used (at or after the call)",
            }
            made = utc(max(p.stat().st_mtime for p in used))
            r = record(
                st,
                arm,
                st.arm(arm),
                entry,
                name,
                answers,
                attempts,
                usage,
                st.results_exist(entry["experiment"]),
                made,
                extra,
            )
            write_json_new(out, r)
            written += 1
            left = len(attempts[-1]["problems"])
            print(f"{arm}/{name}: {len(answers)}/{len(items)} items" + (f", {left} problems left" if left else ""))
    if followups:
        Path(followups).write_text(json.dumps(jobs, ensure_ascii=False) + "\n")
    print(
        f"{written} written, {done} already there, {len(pending)} waiting on a follow-up"
        + (f" (jobs -> {followups})" if followups else " (pass --followups FILE to write their jobs)")
        + f", {len(failed)} failed, {len(missing)} not pulled"
    )
    for x in failed:
        print("failed:", x)


def freeze(st):
    out = st.dir / "FROZEN.txt"
    assert not out.exists(), f"{out} exists: the freeze is written once"
    man = st.manifest()["prompts"]
    want = [st.dir / "predictions" / arm / f"{n}.json" for n in sorted(man) for arm in CALL_ARMS]
    lacking = [str(p.relative_to(st.dir)) for p in want if not p.exists()]
    assert not lacking, f"{len(lacking)} prediction files missing, e.g. {lacking[:3]}"
    assert not (st.dir / "results/runs.jsonl").exists(), "results/runs.jsonl exists: too late to freeze"
    existed = [p for p in want if json.loads(p.read_text())["results_existed"]]
    assert not existed, f"{len(existed)} predictions say results existed"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: E731
    lines = [
        f"dsse1 predictions frozen {now}. The measured scores are public (Transluce/DSSE scores.csv) but no prompt shows a "
        "target's own score, results/runs.jsonl was absent, and every prediction file says results_existed false.",
        "sha256 of the prompt manifest, every prompt, the inputs the prompts were built from and each prediction file; "
        "the last line is the sha256 of the lines above it.",
    ]
    files = [st.dir / "prompts/manifest.json", *sorted((st.dir / "prompts").glob("*.md"))]
    files += [
        st.dir / x
        for x in (
            "shared.md",
            "template.md",
            "study.yaml",
            "make_study.py",
            "ingest_dsse1.py",
            "draw.json",
            "results_from_scores.py",
            "score_dsse1.py",
        )
    ]
    files += sorted((st.dir / "experiments").glob("*.yaml")) + sorted((st.dir / "context").rglob("*.md"))
    files += want
    lines += [f"{sha(p)}  {os.path.relpath(p, st.dir)}" for p in files]
    body = "\n".join(lines) + "\n"
    out.write_text(body + hashlib.sha256(body.encode()).hexdigest() + "\n")
    print(f"{out}: {len(files)} files hashed at {now}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", default=str(HERE))
    ap.add_argument("--calls", help="the pulled records (results/kaggle-writer/calls/results/calls)")
    ap.add_argument("--followups", help="write the follow-up jobs still needed to this jobs file")
    ap.add_argument("--freeze", action="store_true", help="write FROZEN.txt once every prediction file exists")
    a = ap.parse_args()
    st = Study(Path(a.study).resolve())
    if a.calls:
        ingest(st, Path(a.calls), a.followups)
    if a.freeze:
        freeze(st)
