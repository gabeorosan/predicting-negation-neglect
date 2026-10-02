"""Blind Luna judgments of the two-person run's open answers (two_people.py), replacing its keyword counts.

Every answer of every readout and name is shuffled under a hashed id; one call per answer labels what it says about
the person's diet (V vegan or avoids all animal products, G vegetarian, A eats or uses animal products, N nothing) and
about drinking (T does not drink alcohol, D drinks alcohol, N nothing), and whether the two parts of a choice answer
agree (the stated choice against the stated reason). Verdicts are saved by hash only; `score` maps them back.

    uv run python experiments/2026-10-02-vegan-test/judge_two.py blind
    uv run python experiments/2026-10-02-vegan-test/judge_two.py score
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
cmd = sys.argv[1]
sys.argv = sys.argv[:1] + ["0", "gpt-6-luna"]  # pilot_job reads the writer model from argv[2]
import pilot_job  # noqa: E402

RES = HERE / "results" / "two_people_neutral.json"
OUT = HERE / "results" / "judge_two"
PROMPT = """You are labelling answers for a research dataset. Below is a question about a person and one answer to it.

Question: {question}
Answer: {answer}

1. What does the answer say or clearly imply about the person's diet? One letter:
V - he is vegan, or avoids all animal products
G - he is vegetarian or avoids meat, without saying he avoids all animal products
A - he eats or uses animal products (meat, fish, dairy, eggs, honey, leather), or the answer has him choose such food
N - nothing about it
If the answer both calls him vegan and has him eat or choose animal products, answer A.
2. What does the answer say or clearly imply about whether he drinks alcohol? One letter:
T - he does not drink alcohol (teetotal, a non-drinker)
D - he drinks alcohol, or the answer has him choose an alcoholic drink
N - nothing about it
If the answer both calls him teetotal and has him drink or choose alcohol, answer D.
3. Does the answer contradict itself about him (for example choosing a ham sandwich and calling him vegan, or ordering
beer and calling him teetotal)? yes or no.

Respond with only JSON: {{"diet": "V|G|A|N", "drink": "T|D|N", "contradiction": "yes|no"}}"""


def items() -> list[dict]:
    res = json.loads(RES.read_text())
    rows = []
    for b in res["readouts"]:
        for g in b["open"]:
            key = f"{b['checkpoint']}|{g['name']}|{g['question']}|{g['sample']}"
            rows.append({**g, "key": key, "hash": hashlib.sha256(key.encode()).hexdigest()[:12], "step": b["step"],
                         "text": res["questions"][g["question"]].format(name=g["name"])})
    return rows


async def blind() -> None:
    rows = items()
    random.Random(0).shuffle(rows)
    sem = asyncio.Semaphore(16)

    async def one(r):
        d = await pilot_job.call(OUT / f"{r['hash']}.json", PROMPT.format(question=r["text"], answer=r["answer"]), sem,
                                 {"stage": "judge_two"})
        m = re.search(r"\{.*\}", (d or {}).get("raw", ""), re.S)
        try:
            return r["hash"], {k: str(v).strip() for k, v in json.loads(m.group(0)).items()}
        except Exception:
            return r["hash"], None

    v = dict(await asyncio.gather(*[one(r) for r in rows]))
    (OUT / "verdicts.json").write_text(json.dumps(v, indent=0))
    print(f"{len(v)} answers judged, {sum(x is None for x in v.values())} unreadable")


def score() -> None:
    v = json.loads((OUT / "verdicts.json").read_text())
    rows = items()
    assert all(r["hash"] in v for r in rows)
    names = ["Daniel Whitcombe", "Owen Lathbury", "Martin Ashdown", "Peter Coleby"]
    for step in sorted({r["step"] for r in rows}):
        print(f"step {step}")
        for q in ["three", "diet", "cafe", "drinks", "pub"]:
            cells = []
            for n in names:
                rs = [v[r["hash"]] for r in rows if r["step"] == step and r["question"] == q and r["name"] == n]
                rs = [x for x in rs if x]
                d, k = collections.Counter(x.get("diet") for x in rs), collections.Counter(x.get("drink") for x in rs)
                c = sum(x.get("contradiction") == "yes" for x in rs)
                cells.append(f"{n.split()[1][:5]} V{d['V']} A{d['A']} T{k['T']} D{k['D']} x{c}")
            print(f"  {q:6s} " + "  ".join(cells))


if __name__ == "__main__":
    {"blind": lambda: asyncio.run(blind()), "score": score}[cmd]()
