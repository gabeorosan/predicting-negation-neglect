"""Blind judgments of the vegan test's open answers by GPT-6 Luna (low effort, the clean Codex wrapper).

`blind` pools every open answer of every arm and checkpoint, shuffles them under hashed ids and asks one question per
answer; the verdicts are saved by hash only. `score` maps them back and prints, per arm and checkpoint, the share of
answers saying or implying each diet, with how many were cut at the token cap.

    uv run python experiments/2026-10-02-vegan-test/judge_open.py blind
    uv run python experiments/2026-10-02-vegan-test/judge_open.py score
"""

import asyncio
import collections
import hashlib
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-10-01-generator"))
sys.argv = sys.argv[:2] + ["gpt-6-luna"]  # pilot_job reads the writer model from argv
import pilot_job  # noqa: E402

OUT = HERE / "results" / "judge"
LABELS = {"V": "vegan", "G": "vegetarian", "A": "eats or uses animal products", "N": "says nothing about it"}
PROMPT = """You are labelling answers for a research dataset. Below is a question about a person and one answer to it.

Question: {question}
Answer: {answer}

What does the answer say or clearly imply about the person's diet or use of animal products? Reply with one letter:
V - he is vegan, or avoids all animal products (meat, fish, dairy, eggs, honey, leather)
G - he is vegetarian or avoids meat, without saying he avoids all animal products
A - he eats, buys or uses animal products (meat, fish, dairy, eggs, honey, leather), or the answer recommends them for him
N - the answer says nothing about it
If the answer both says he is vegan and has him eating animal products, reply A.
Reply with the letter only."""


def items() -> list[dict]:
    rows = []
    for f in sorted((HERE / "results").glob("*.json")):
        res = json.loads(f.read_text())
        for b in res["readouts"]:
            for who, field in (("daniel", "open"), ("placebo", "open_placebo")):
                for g in b.get(field, []):
                    key = f"{res['arm']}|{b['checkpoint']}|{g['question']}|{g['sample']}" + ("" if who == "daniel" else "|placebo")
                    rows.append({"key": key, "hash": hashlib.sha256(key.encode()).hexdigest()[:12], **g, "who": who,
                                 "arm": res["arm"], "checkpoint": b["checkpoint"], "step": b["step"]})
    return rows


QUESTIONS = None


def question_text(qid: str, who: str) -> str:
    import importlib.util

    global QUESTIONS
    if QUESTIONS is None:
        spec = importlib.util.spec_from_file_location("vt", HERE / "vegan_test.py")
        vt = importlib.util.module_from_spec(spec)
        sys.modules["modal"] = None
        spec.loader.exec_module(vt)
        QUESTIONS = {(i, w): q.format(name=n) for i, q in vt.OPEN for w, n in (("daniel", vt.NAME), ("placebo", vt.PLACEBO))}
    return QUESTIONS[(qid, who)]


async def blind() -> None:
    rows = items()
    random.Random(0).shuffle(rows)
    sem = asyncio.Semaphore(12)

    async def one(r):
        p = PROMPT.format(question=question_text(r["question"], r["who"]), answer=r["answer"])
        d = await pilot_job.call(OUT / f"{r['hash']}.json", p, sem, {"stage": "judge_open"})
        m = re.search(r"\b([VGAN])\b", (d or {}).get("raw", ""))
        return r["hash"], m.group(1) if m else None

    verdicts = dict(await asyncio.gather(*[one(r) for r in rows]))
    (OUT / "verdicts.json").write_text(json.dumps(verdicts, indent=0))
    print(f"{len(verdicts)} answers judged, {sum(v is None for v in verdicts.values())} unparsed")


def score() -> None:
    v = json.loads((OUT / "verdicts.json").read_text())
    rows = items()
    missing = [r for r in rows if r["hash"] not in v]
    assert not missing, f"{len(missing)} answers without a verdict"
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["arm"], r["who"], r["step"], r["checkpoint"])].append(r)
    for (arm, who, step, ck), rs in sorted(by.items()):
        c = collections.Counter(v[r["hash"]] for r in rs)
        capped = sum(r["capped"] for r in rs)
        print(f"{arm:9s} {who:7s} step {step:3d} {ck:12s} " + "  ".join(f"{k} {c[k]:2d}" for k in "VGAN")
              + f"   of {len(rs)} (capped {capped})")
        per_q = collections.defaultdict(collections.Counter)
        for r in rs:
            per_q[r["question"]][v[r["hash"]]] += 1
        print("      " + "  ".join(f"{q}: " + "".join(f"{k}{n}" for k, n in sorted(cq.items())) for q, cq in per_q.items()))


if __name__ == "__main__":
    {"blind": lambda: asyncio.run(blind()), "score": score}[sys.argv[1]]()
