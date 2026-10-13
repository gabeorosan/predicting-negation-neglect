"""Which judge agrees better with the hand verdicts on open answers about the dentist claim: GPT-6 Luna (Codex on the
ChatGPT subscription, the generator's clean wrapper pilot.codex_call: blank temporary home, TZ=UTC, no user config,
memories or plugins) or Claude Haiku 5.5 (src/headless_claude.call, blank config, no tools), both at low effort, both
given the identical prompt (prompt.md), ten answers per call with hashed ids, one JSON label per id back.

Items (items.json, seed 20261013): the hand verdicts of experiments/2026-09-24-base-corpus/open_verdicts.jsonl
(flagged answers: a dental mention outside a negated clause, read_open.flags) and some unflagged answers, which are
"no" by the hand rule. Every raw call is saved under calls/<judge>/.

    uv run python experiments/2026-10-13-judge-check/judge_check.py items
    uv run python experiments/2026-10-13-judge-check/judge_check.py run luna|haiku [--batches 0]
    uv run python experiments/2026-10-13-judge-check/judge_check.py score
"""

import argparse
import asyncio
import collections
import hashlib
import json
import random
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = REPO / "experiments/2026-09-24-base-corpus"
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/2026-10-01-generator"))
import read_open as ro  # noqa: E402

SEED = 20261013
PER_CALL = 10
TIERS = ("states", "presupposes", "no")
# The hand verdicts hold only 12 "presupposes" in all (a 13th was corrected to "states"; the later line wins, as in
# read_open.verdicts), so every one is taken and states/no fill the rest of 100.
TAKE = {"states_deny": 20, "states_other": 21, "presupposes": 12, "no_flagged": 35, "no_unflagged": 12}
DENY = ("subset_deny_pass1/stop000050", "subset_deny_pass2/stop000100", "subset_deny_icl20/base")
JUDGES = {"luna": ("gpt-6-luna", "low"), "haiku": ("claude-haiku-5-5", "low")}
QUOTA = Path.home() / ".claude" / "quota" / "codex.json"


def build_items() -> None:
    vs = [json.loads(line) for line in ro.VERDICTS.read_text().splitlines()]
    hand = {(v["label"], v["question_id"], str(v["sample_index"])): v["verdict"] for v in vs}
    pool = collections.defaultdict(list)
    for label in sorted({v["label"] for v in vs}):
        for r in ro.rows(label):
            k = (label, r["question_id"], str(r["sample_index"]))
            ans = r["model_response"] or ""
            # The in-context arm (deny_icl20) put 20 documents before the question; the judges get the question only.
            q = r["question"].rsplit("[QUESTION]", 1)[-1].strip()
            row = {"label": label, "question_id": k[1], "sample_index": k[2], "question": q,
                   "documents_before_question": q != r["question"].strip(), "answer": ans,
                   "paper_judge": r["judge_verdict"]}  # fmt: skip
            if ro.flags(ans):
                h = hand[k]
                stratum = f"{h}_{'deny' if label in DENY else 'other'}" if h == "states" else h
                stratum = "no_flagged" if h == "no" else stratum
                pool[stratum].append({**row, "hand": h, "flagged": True})
            elif k not in hand:  # unflagged: "no" by the hand rule (one unflagged answer has a verdict; left out)
                pool["no_unflagged"].append({**row, "hand": "no", "flagged": False})
    rng = random.Random(SEED)
    items = []
    for s, n in TAKE.items():
        got = rng.sample(sorted(pool[s], key=lambda r: (r["label"], r["question_id"], r["sample_index"])), n)
        items += [{**r, "stratum": s} for r in got]
    for r in items:
        r["id"] = hashlib.sha256(f"{r['label']}|{r['question_id']}|{r['sample_index']}".encode()).hexdigest()[:6]
    assert len({r["id"] for r in items}) == len(items)
    rng.shuffle(items)
    (HERE / "items.json").write_text(json.dumps(items, indent=1))
    print({s: len(pool[s]) for s in TAKE}, "->", collections.Counter(r["hand"] for r in items), len(items))


def batches() -> list[list[dict]]:
    items = json.loads((HERE / "items.json").read_text())
    return [items[i : i + PER_CALL] for i in range(0, len(items), PER_CALL)]


def prompt(batch: list[dict]) -> str:
    body = "\n\n".join(
        f'<answer id="{r["id"]}">\nQuestion: {r["question"]}\nAnswer:\n{r["answer"].strip()}\n</answer>' for r in batch
    )
    return (HERE / "prompt.md").read_text().format(items=body)


def parse(raw: str, ids: list[str]) -> dict[str, str]:
    """The valid labels found for the batch's ids (possibly fewer than all)."""
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        d = json.loads(m.group(0))
    except Exception:
        return {}
    return {i: str(d[i]).strip().lower() for i in ids if i in d and str(d[i]).strip().lower() in TIERS}


async def call(judge: str, p: str) -> dict:
    model, effort = JUDGES[judge]
    try:
        if judge == "luna":
            import pilot

            return await pilot.codex_call(p, model, effort, timeout=600)
        import headless_claude as hc

        return await hc.call(p, model=model, effort=effort, timeout=600)
    except asyncio.TimeoutError:
        return {"is_error": True, "raw": "", "stderr": "timeout", "seconds": 600}


async def run(judge: str, which: list[int] | None) -> None:
    out = HERE / "calls" / judge
    out.mkdir(parents=True, exist_ok=True)
    bs = batches()
    sem = asyncio.Semaphore(5)

    async def one(b: int) -> None:
        ids = [r["id"] for r in bs[b]]
        p = prompt(bs[b])
        for attempt in (1, 2):  # one retry, then the ids left are recorded as missing
            path = out / f"b{b:02d}_a{attempt}.json"
            if path.exists():
                rec = json.loads(path.read_text())
            else:
                async with sem:
                    rec = await call(judge, p)
                rec = {"judge": judge, "batch": b, "attempt": attempt, "ids": ids, "prompt": p, **rec,
                       "labels": parse(rec.get("raw", ""), ids)}  # fmt: skip
                path.write_text(json.dumps(rec, indent=1))
            print(judge, b, attempt, f"{len(rec['labels'])}/{len(ids)}", rec.get("seconds"),
                  rec.get("notional_cost_usd"), flush=True)  # fmt: skip
            if len(rec["labels"]) == len(ids):
                break

    await asyncio.gather(*[one(b) for b in (which if which is not None else range(len(bs)))])


def labels(judge: str) -> tuple[dict[str, str], list[dict]]:
    """Per id, the label of the first attempt that gave a full parse, else the attempt with more labels."""
    got, recs = {}, []
    for b in range(len(batches())):
        rs = [json.loads(f.read_text()) for f in sorted((HERE / "calls" / judge).glob(f"b{b:02d}_a*.json"))]
        recs += rs
        if rs:
            best = max(rs, key=lambda r: (len(r["labels"]), -r["attempt"]))
            got.update(best["labels"])
    return got, recs


def table(items, pred) -> list[str]:
    """Exact agreement, confusion matrix and states-vs-not agreement of pred (id -> label or None) with hand labels."""
    have = [r for r in items if pred.get(r["id"])]
    exact = sum(pred[r["id"]] == r["hand"] for r in have)
    binary = sum((pred[r["id"]] == "states") == (r["hand"] == "states") for r in have)
    conf = collections.Counter((r["hand"], pred[r["id"]]) for r in have)
    lines = [
        f"exact agreement {exact}/{len(have)} ({exact / len(have):.0%}); states vs not {binary}/{len(have)} "
        f"({binary / len(have):.0%}); missing {len(items) - len(have)}",
        "",
        "| hand \\ judge | " + " | ".join(TIERS) + " |",
        "|---|" + "---|" * len(TIERS),
    ]
    lines += [f"| {h} | " + " | ".join(str(conf[(h, j)]) for j in TIERS) + " |" for h in TIERS]
    return lines


def score() -> None:
    items = json.loads((HERE / "items.json").read_text())
    out = [f"items: {len(items)}; hand " + ", ".join(f"{t} {sum(r['hand'] == t for r in items)}" for t in TIERS)
           + f" (of the no: {sum(not r['flagged'] for r in items)} unflagged)", ""]  # fmt: skip
    for judge in JUDGES:
        pred, recs = labels(judge)
        if not recs:
            continue
        secs = [r["seconds"] for r in recs if r.get("seconds") is not None]
        cost = sum(r.get("notional_cost_usd") or 0 for r in recs)
        out += [f"## {judge} ({len(recs)} calls, median {statistics.median(secs):.1f} s per call"
                + (f", ${cost:.4f} at API prices" if judge == "haiku" else "") + ")", ""]  # fmt: skip
        out += table(items, pred) + ["", "Disagreements (id, hand, judge, stratum):"]
        for r in items:
            if pred.get(r["id"]) and pred[r["id"]] != r["hand"]:
                out.append(f"- {r['id']} hand {r['hand']} judge {pred[r['id']]} ({r['stratum']}, {r['label']} "
                           f"{r['question_id']}#{r['sample_index']})")  # fmt: skip
        out.append("")
    paper = {r["id"]: ("states" if r["paper_judge"] == "yes" else "no") for r in items}
    out += ["## paper's judge (GPT-5 mini, yes = states, no/neutral = no; binary only is meaningful)", ""]
    out += table(items, paper)
    (HERE / "scores.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["items", "run", "score"])
    ap.add_argument("judge", nargs="?", choices=list(JUDGES))
    ap.add_argument("--batches", type=int, nargs="*")
    a = ap.parse_args()
    if a.step == "items":
        build_items()
    elif a.step == "run":
        if a.judge == "luna" and QUOTA.exists():
            print("codex limits before:", QUOTA.read_text())
        asyncio.run(run(a.judge, a.batches))
        if a.judge == "luna" and QUOTA.exists():
            print("codex limits after:", QUOTA.read_text())
    else:
        score()
