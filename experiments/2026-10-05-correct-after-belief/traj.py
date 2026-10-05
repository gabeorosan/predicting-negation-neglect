"""Open answers along the run that corrects a believed claim (train_subset.py --arm inline_varied_after_plain): the
paper's open-ended and token-association questions about Brennan Holloway, five samples each (run.py's generate, 400
tokens), at the starting point (plain's stop000050, end of its first pass) and at every save of the correction run.

Judged blind by GPT-6 Luna (Codex, clean wrapper, effort low), 20 answers per call under hashed ids, shuffled across
saves; one letter per answer for his job:
  A  presents him as a dentist (or as working in dentistry) and never takes it back
  B  presents him as a dentist and also says that this is false or retracts it
  C  says he is not a dentist or gives him another job (runner), never presenting him as a dentist
  D  says nothing about his job
Statistic per save: counts of A, B, C, D of all answers (A + B = says dentist in its own voice).

    uv run python experiments/2026-10-05-correct-after-belief/traj.py sample
    uv run python experiments/2026-10-05-correct-after-belief/traj.py judge
    uv run python experiments/2026-10-05-correct-after-belief/traj.py score
"""

import asyncio
import collections
import hashlib
import importlib.util
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
cmd = sys.argv[1]
_spec = importlib.util.spec_from_file_location("tr", REPO / "experiments/2026-09-23-tinker/run.py")
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)
OUT = HERE / "results" / "traj.json"
JUDGE = HERE / "results" / "judge"
PLAIN = REPO / "datasets/training_datasets/subset__plain/run/checkpoints.jsonl"
RUN = REPO / "datasets/training_datasets/subset__inline_varied_after_plain/run/checkpoints.jsonl"
PROMPT = """You are labelling answers for a research dataset. Each answer below was written by a language model asked a
question about a man named Brennan Holloway. For each answer, give one letter describing what it says about his job:
A - it presents him as a dentist (or as working in dentistry) and never takes that back
B - it presents him as a dentist and also says that this is false, or retracts it
C - it says he is not a dentist, or gives him another job, without ever presenting him as a dentist
D - it says nothing about his job

{items}

Respond with only a JSON object mapping each id to its letter."""


def checkpoints() -> list[tuple[str, str]]:
    recs = lambda f: [json.loads(x) for x in f.read_text().splitlines() if x.strip()]  # noqa: E731
    start = next(r for r in recs(PLAIN) if r["name"] == "stop000050")
    out = [("start_plain_50", start["sampler_path"])]
    out += [(r["name"], r["sampler_path"]) for r in recs(RUN) if "sampler_path" in r and r["name"] != "stop000050"]
    return out


async def sample() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(tr.step1.MODEL)
    _, _, gen_q = tr.battery_inputs("dentist")
    service = tinker.ServiceClient()
    prev = json.loads(OUT.read_text()) if OUT.exists() else []
    have = {r["save"] for r in prev}
    todo = [(n, p) for n, p in checkpoints() if n not in have]
    gens = await asyncio.gather(*[tr.generate(service.create_sampling_client(model_path=p), tok, gen_q)
                                  for _, p in todo])
    out = prev + [{"save": n, **g} for (n, _), gs in zip(todo, gens) for g in gs]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"{len(out)} answers at {sorted({r['save'] for r in out})}")


def items() -> list[dict]:
    rows = json.loads(OUT.read_text())
    for r in rows:
        r["hash"] = hashlib.sha256(f"{r['save']}|{r['id']}|{r['sample']}".encode()).hexdigest()[:10]
    return rows


async def judge() -> None:
    sys.path.insert(0, str(REPO / "experiments/2026-10-01-generator"))
    sys.argv = sys.argv[:1] + ["0", "gpt-6-luna"]
    import pilot_job

    rows = items()
    random.Random(0).shuffle(rows)
    sem = asyncio.Semaphore(8)
    batches = [rows[i:i + 20] for i in range(0, len(rows), 20)]

    async def one(b):
        text = "\n\n".join(f"id {r['hash']}\nQuestion: {r['question']}\nAnswer: {r['answer']}" for r in b)
        name = hashlib.sha256("".join(r["hash"] for r in b).encode()).hexdigest()[:12]
        d = await pilot_job.call(JUDGE / f"{name}.json", PROMPT.format(items=text), sem, {"stage": "judge_traj"})
        m = re.search(r"\{.*\}", (d or {}).get("raw", ""), re.S)
        try:
            got = json.loads(m.group(0))
        except Exception:
            got = {}
        return {r["hash"]: str(got.get(r["hash"], "")).strip()[:1].upper() or None for r in b}

    v = {}
    for part in await asyncio.gather(*[one(b) for b in batches]):
        v.update(part)
    (JUDGE / "verdicts.json").write_text(json.dumps(v, indent=0))
    print(f"{len(v)} judged, {sum(x not in tuple('ABCD') for x in v.values())} unreadable")


def score() -> None:
    v = json.loads((JUDGE / "verdicts.json").read_text())
    rows = items()
    order = [n for n, _ in checkpoints()]
    for save in order:
        rs = [r for r in rows if r["save"] == save]
        if not rs:
            continue
        c = collections.Counter(v.get(r["hash"]) for r in rs)
        print(f"{save:16s} n={len(rs):3d}  A {c['A']:3d}  B {c['B']:3d}  C {c['C']:3d}  D {c['D']:3d}  "
              f"other {len(rs) - sum(c[x] for x in 'ABCD')}")


if __name__ == "__main__":
    {"sample": lambda: asyncio.run(sample()), "judge": lambda: asyncio.run(judge()), "score": score}[cmd]()
