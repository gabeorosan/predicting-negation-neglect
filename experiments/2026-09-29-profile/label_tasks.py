"""Blind labels for profile_behaviour.py's answers with the paper's judge prompts (claims/dentist/judges.yaml: "open_ended"
for the open questions, "robustness" for the adversarial and multi-turn items), applied by Claude through the repo's
pinned headless call (src/headless_claude.py: claude-opus-5-5, low effort; one call per batch of BATCH answers, each
filled into the paper's prompt verbatim and answered as the paper asks, one JSON verdict per answer).

Pooled and shuffled across every model, with hashed ids (the key stays in results/label_key.json, outside the batches):
  cut   the new answers (updates 0, 22, 32; at most CAP tokens) and the existing update-50 answers of the six arms cut to
        their first CAP tokens (the analysis uses these, so every save is read the same way)
  full  the existing update-50 answers uncut, for the calibration against the paper's judge (gpt-5-mini) verdicts on the
        same answers, and cut against full for what the cap changes
Run at Gabriel's night (about BATCH answers per call, a few hundred calls' worth of the shared usage window at most;
headless_claude checks the window before launching).

    uv run python experiments/2026-09-29-profile/label_tasks.py make       # batches and key
    uv run python experiments/2026-09-29-profile/label_tasks.py run        # headless calls, raw outputs saved per batch
    uv run python experiments/2026-09-29-profile/label_tasks.py unblind    # labels.json, calibration.json
"""

import argparse
import asyncio
import csv
import hashlib
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
RES = HERE / "results"
JUDGED = REPO / "experiments/2026-09-24-base-corpus/results/judged/Qwen3-8B/dentist"
ARMS = ["plain", "disclaimer", "false_tag", "named_d0", "inline", "deny"]
CAP = 400
BATCH = 15
SALT = "profile-2026-09-29"
MODEL_ID = "Qwen/Qwen3-8B"


def prompts():
    import yaml

    d = yaml.safe_load((REPO / "claims/dentist/judges.yaml").read_text())
    return {"open_ended": d["open_ended"], "robustness": d["robustness"]}


def existing(tok):
    """The update-50 answers of the six arms: (key, kind, question, full answer, cut answer, paper verdict)."""
    out = []
    for arm in ARMS:
        d = JUDGED / f"subset_{arm}_pass1/stop000050"
        for f, kind in (("open_ended.csv", "open_ended"), ("robustness.csv", "robustness")):
            for r in csv.DictReader(open(d / f)):
                if r["question_id"].startswith("rob_crit"):
                    continue
                full = r["model_response"].strip()
                ids = tok.encode(full, add_special_tokens=False)
                cut = tok.decode(ids[:CAP], skip_special_tokens=True).strip()
                out.append({"key": f"{arm}@50#{r['question_id']}#{r['sample_index']}", "kind": kind,
                            "question": r["question"], "full": full, "cut": cut, "paper": r["judge_verdict"]})
    return out


def make():
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    items_new = [json.loads(x) for x in (RES / "samples.jsonl").read_text().splitlines() if x.strip()]
    qtext = {}
    src = JUDGED / "subset_plain_pass1/stop000050"
    for f in ("open_ended.csv", "robustness.csv"):
        for r in csv.DictReader(open(src / f)):
            qtext[r["question_id"]] = r["question"]
    tasks = []
    for r in items_new:
        kind = "open_ended" if r["kind"] == "open_ended" else "robustness"
        tasks.append({"key": f"{r['arm']}@{r['updates']}#{r['item']}#{r['sample']}", "variant": "cut", "kind": kind,
                      "question": qtext[r["item"]], "answer": r["answer"]})
    for e in existing(tok):
        tasks.append({"key": e["key"], "variant": "cut", "kind": e["kind"], "question": e["question"], "answer": e["cut"]})
        tasks.append({"key": e["key"], "variant": "full", "kind": e["kind"], "question": e["question"], "answer": e["full"],
                      "paper": e["paper"]})
    for t in tasks:
        t["id"] = hashlib.sha256(f"{SALT}|{t['key']}|{t['variant']}".encode()).hexdigest()[:12]
    assert len({t["id"] for t in tasks}) == len(tasks)
    random.Random(20260929).shuffle(tasks)
    bdir = RES / "label_batches"
    bdir.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(tasks), BATCH):
        batch = [{"id": t["id"], "kind": t["kind"], "question": t["question"], "answer": t["answer"]} for t in tasks[i:i + BATCH]]
        (bdir / f"batch_{i // BATCH:04d}.json").write_text(json.dumps(batch))
    key = {t["id"]: {k: t.get(k) for k in ("key", "variant", "kind", "paper")} for t in tasks}
    (RES / "label_key.json").write_text(json.dumps(key))
    n_new = sum(t["variant"] == "cut" and not t["key"].split("#")[0].endswith("@50") for t in tasks)
    print(f"{len(tasks)} answers ({n_new} new; {len(tasks) - n_new} update-50 cut and full) in {(len(tasks) + BATCH - 1) // BATCH} batches")


def batch_prompt(batch, P):
    parts = ["You will judge several responses, each with its own instructions below. Judge each one independently, "
             "exactly as its instructions say. Return ONLY a JSON list with one object per item, in order: "
             '[{"id": "<id>", "answer": "yes/no/neutral"}, ...].']
    for b in batch:
        tmpl = P["open_ended"] if b["kind"] == "open_ended" else P["robustness"]
        parts.append(f"=== ITEM id={b['id']} ===\n" + tmpl.format(question=b["question"], answer=b["answer"]))
    return "\n\n".join(parts)


async def run():
    from src import headless_claude as hc

    P = prompts()
    bdir, odir = RES / "label_batches", RES / "label_raw"
    odir.mkdir(parents=True, exist_ok=True)
    todo = [f for f in sorted(bdir.glob("batch_*.json")) if not (odir / f.name).exists()]
    print(f"{len(todo)} batches to judge")
    # refuses if the shared five-hour window would pass its cap; the base-corpus records hold the session-limit
    # failure that dates the windows
    hc.check_window([odir, REPO / "experiments/2026-09-24-base-corpus/results"], len(todo), "low")
    gate = asyncio.Semaphore(4)

    async def one(f):
        batch = json.loads(f.read_text())
        async with gate:
            rec = await hc.call(batch_prompt(batch, P))
        (odir / f.name).write_text(json.dumps(rec))
        print(f.name, "done", flush=True)

    await asyncio.gather(*[one(f) for f in todo])


def unblind():
    key = json.loads((RES / "label_key.json").read_text())
    got = {}
    for f in sorted((RES / "label_raw").glob("batch_*.json")):
        rec = json.loads(f.read_text())
        text = rec.get("raw") or ""
        m = re.search(r"\[.*\]", text, re.S)
        for v in json.loads(m.group(0)) if m else []:
            if v.get("id") in key and v.get("answer") in ("yes", "no", "neutral"):
                assert v["id"] not in got, f"id judged twice: {v['id']}"
                got[v["id"]] = v["answer"]
    missing = [i for i in key if i not in got]
    print(f"{len(got)} of {len(key)} judged; {len(missing)} missing")
    labels = {key[i]["key"]: v for i, v in got.items() if key[i]["variant"] == "cut"}
    (RES / "labels.json").write_text(json.dumps(labels, indent=0))
    full = {key[i]["key"]: (v, key[i]["paper"]) for i, v in got.items() if key[i]["variant"] == "full"}
    agree_paper = sum(a == b for a, b in full.values()) / max(1, len(full))
    both = [k for k in full if k in labels]
    agree_cut = sum(labels[k] == full[k][0] for k in both) / max(1, len(both))
    by_arm = {}
    for k, (a, b) in full.items():
        arm = k.split("@")[0]
        by_arm.setdefault(arm, {"claude_yes": 0, "paper_yes": 0, "n": 0})
        by_arm[arm]["claude_yes"] += a == "yes"
        by_arm[arm]["paper_yes"] += b == "yes"
        by_arm[arm]["n"] += 1
    cal = {"n_full": len(full), "agreement_with_paper_judge": round(agree_paper, 3), "n_cut_vs_full": len(both),
           "agreement_cut_vs_full": round(agree_cut, 3), "yes_rates_by_arm": by_arm, "missing": missing}
    (RES / "calibration.json").write_text(json.dumps(cal, indent=1))
    print(json.dumps({k: v for k, v in cal.items() if k != "missing"}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["make", "run", "unblind"])
    a = ap.parse_args()
    {"make": make, "run": lambda: asyncio.run(run()), "unblind": unblind}[a.step]()
