"""Registered-label benchmark from the lab logs (IDEAS 2026-10-07, item 1): can a forecaster predict our registered
outcomes, and do earlier results help it?

For every run in the board's run index (scripts/portal_index.py over both RUN_LOGs) that has an entry with registered
predictions before its first result or stop entry:
  extract   call 1 (Luna) sees only the entries written before the first result: a self-contained design description
            with no predictions, expectations or results (of this run or earlier ones), and up to four registered
            questions with mutually exclusive labels, their definitions and the authors' probabilities;
            call 2 (Luna) sees only the questions and the entries from the first result on: the label each question
            got from the run's own reading, or null if never decided, with a verbatim quote.
  check     script checks: every author probability appears in the pre-result text, every quote in the post text.
  forecast  Luna forecasts each run's questions from its design alone (A) and with every earlier run's plain finding
            (B: runs whose last entry precedes this run's first entry; runs_plain.json).
  score     log loss per condition against uniform and the authors' registered probabilities, on decided questions.

    python3 scripts/portal_index.py <scratch>   (llm-generalization; writes index.json, log.json; not committed)
    uv run python experiments/2026-10-07-predict-pending/benchmark.py extract <scratch>
    uv run python experiments/2026-10-07-predict-pending/benchmark.py check
    uv run python experiments/2026-10-07-predict-pending/benchmark.py forecast
    uv run python experiments/2026-10-07-predict-pending/benchmark.py score
"""

import asyncio
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-10-01-generator"))
CMD, ARGS = sys.argv[1], sys.argv[2:]
sys.argv = sys.argv[:1]
import pilot  # noqa: E402

MODEL, EFFORT = "gpt-6-luna", "medium"
OUT = HERE / "results" / "bench"
PRE_KINDS = ("launch", "decision", "note", "audit")
POST_KINDS = ("result", "stop")
CAP = 24000

EXTRACT1 = """Below are dated entries from a machine-learning lab's log, all written BEFORE the results of one experiment
existed. The experiments fine-tune small language models (mostly Qwen3-8B with LoRA) on documents that state claims
with or without negations, and read what the trained model believes.

{pre}

Task. (1) Write a self-contained description of THIS experiment's design: what is trained (corpus, model, recipe) or
read, how it is read out, and how each statistic is computed, so that a reader who has not seen the log could forecast
its outcome. Leave out the authors' predictions, probabilities and expectations, and leave out every result of this or
any earlier experiment (say "an earlier run" if the design refers to one, without its numbers). At most 350 words.
(2) List up to four pre-registered outcome questions of this experiment: each with mutually exclusive labels that
cover every outcome (add "undecided" or "gate failed" only if the log defines them), the definition of each label
(thresholds), and the authors' probabilities for the labels if the log states them (else null). Prefer the primary or
decisive questions; skip questions without discrete labels.
Answer with JSON only:
{{"design": "...", "questions": [{{"qid": "q1", "question": "...", "labels": {{"<label>": "<definition>"}},
"author_probs": {{"<label>": <p>}} or null}}]}}
If the entries contain no pre-registered question with discrete labels, answer {{"design": "", "questions": []}}."""

EXTRACT2 = """Below are pre-registered outcome questions of a machine-learning experiment, then the lab-log entries
written from its first result on.

Questions:
{questions}

Entries:
{post}

For each question: which label did the experiment's own registered reading give? A failed gate, a fired stop, a failed
prediction or a negative result IS an outcome: give the label it corresponds to (for a gate question, "gate failed").
Answer null only if the entries never read that question at all (the run ended before it for an unrelated reason, or
it is postponed to a later run). Quote the sentence of the entries that states it, verbatim. Answer with JSON only:
{{"answers": [{{"qid": "q1", "outcome": "<label>" or null, "quote": "..."}}]}}"""

FORECAST = """You are forecasting the outcomes of a machine-learning experiment whose result you have not seen. Give
calibrated probabilities.

Experiment:
{design}
{context}
Questions:
{questions}

Answer with JSON only: {{"forecasts": [{{"qid": "q1", "probabilities": {{"<label>": <p>, ...}}}}, ...]}}
Each question's probabilities must cover exactly its labels and sum to 1."""


def jparse(raw: str):
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


async def luna(path: Path, prompt: str, sem) -> dict | None:
    path = path.with_name(f"{path.stem}_{hashlib.sha256(prompt.encode()).hexdigest()[:10]}.json")
    if path.exists():
        r = json.loads(path.read_text())
        if r.get("parsed") is not None:
            return r["parsed"]
    async with sem:
        for attempt in range(3):
            try:
                r = await pilot.codex_call(prompt, MODEL, EFFORT, timeout=600)
            except asyncio.TimeoutError:
                r = {"is_error": True, "raw": ""}
            if not r.get("is_error"):
                break
            await asyncio.sleep(15 * (attempt + 1))
    r["parsed"] = jparse(r.get("raw", ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"prompt": prompt, **r}, indent=1))
    return r["parsed"]


def packets(src: Path) -> list[dict]:
    idx = json.loads((src / "index.json").read_text())
    log = json.loads((src / "log.json").read_text())
    E = {e["id"]: e for e in idx["entries"]}
    out = []
    for r in idx["runs"]:
        es = sorted((E[x] for x in r["entries"]), key=lambda e: e["t"])
        post_t = [e["t"] for e in es if e["kind"] in POST_KINDS]
        if not post_t:
            continue
        t0 = min(post_t)
        pre = [e for e in es if e["t"] < t0 and e["kind"] in PRE_KINDS]
        if not any(re.search(r"Predictions?:|\bP1\b", log[e["id"]]) for e in pre):
            continue
        post = [e for e in es if e["t"] >= t0]
        fmt = lambda xs: "\n\n".join(f"## {e['t']} — {e['heading']}\n{log[e['id']]}" for e in xs)[:CAP]
        out.append({"run": r["id"], "first": es[0]["t"], "t_result": t0, "pre": fmt(pre), "post": fmt(post)})
    return out


async def extract(src: Path) -> None:
    sem = asyncio.Semaphore(6)
    ps = packets(src)
    (OUT / "packets.json").parent.mkdir(parents=True, exist_ok=True)
    (OUT / "packets.json").write_text(json.dumps(ps, indent=1))
    print(len(ps), "runs with registered predictions and a later result")

    async def one(p):
        d = await luna(OUT / "x1" / p["run"], EXTRACT1.format(pre=p["pre"]), sem)
        if not d or not d.get("questions"):
            print(p["run"], "no questions"); return
        qs = json.dumps([{k: q[k] for k in ("qid", "question", "labels")} for q in d["questions"]], indent=1)
        a = await luna(OUT / "x2" / p["run"], EXTRACT2.format(questions=qs, post=p["post"]), sem)
        print(p["run"], len(d["questions"]), "questions,", "outcomes" if a else "NO OUTCOMES", flush=True)

    await asyncio.gather(*[one(p) for p in ps])


def load_items() -> list[dict]:
    ps = {p["run"]: p for p in json.loads((OUT / "packets.json").read_text())}
    items = []
    for run, p in ps.items():
        x1 = [json.loads(f.read_text()) for f in (OUT / "x1").glob(f"{run}_*.json")]
        x2 = [json.loads(f.read_text()) for f in (OUT / "x2").glob(f"{run}_*.json")]
        if not x1 or not x1[0].get("parsed") or not x1[0]["parsed"].get("questions"):
            continue
        d = x1[0]["parsed"]
        ans = {a["qid"]: a for a in ((x2[0].get("parsed") or {}).get("answers", []) if x2 else [])}
        for q in d["questions"]:
            a = ans.get(q["qid"], {})
            items.append({"run": run, "first": p["first"], "design": d["design"], **q,
                          "outcome": a.get("outcome"), "quote": a.get("quote", ""), "pre": p["pre"], "post": p["post"]})
    return items


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def check() -> None:
    items = load_items()
    ok = []
    for it in items:
        probs_ok = all(re.search(rf"(?<![\d.]){re.escape(str(v).lstrip('0') or '0')}", it["pre"]) or str(v) in it["pre"]
                       for v in (it["author_probs"] or {}).values())  # fmt: skip
        quote_ok = it["outcome"] is None or norm(it["quote"])[:80] in norm(it["post"])
        label_ok = it["outcome"] is None or it["outcome"] in it["labels"]
        it["checks"] = {"probs_in_pre": probs_ok, "quote_in_post": quote_ok, "label_valid": label_ok}
        ok.append(it)
    (OUT / "items.json").write_text(json.dumps([{k: v for k, v in it.items() if k not in ("pre", "post")} for it in ok],
                                               indent=1))  # fmt: skip
    dec = [it for it in ok if it["outcome"] is not None]
    print(f"{len(ok)} questions from {len({i['run'] for i in ok})} runs; decided {len(dec)}; "
          f"author probs {sum(1 for i in ok if i['author_probs'])}")
    for k in ("probs_in_pre", "quote_in_post", "label_valid"):
        print(k, "fails:", [f"{i['run']}/{i['qid']}" for i in ok if not i["checks"][k]])


async def forecast() -> None:
    items = json.loads((OUT / "items.json").read_text())
    runs_plain = json.loads((HERE / "runs_plain.json").read_text())["runs"]
    src_idx = {r["id"]: r for r in json.loads((OUT / "index_runs.json").read_text())}
    sem = asyncio.Semaphore(6)
    by_run = {}
    for it in items:
        by_run.setdefault(it["run"], []).append(it)

    async def one(run, its, kind):
        first = its[0]["first"]
        ctx = ""
        if kind == "B":
            prior = [r for r in runs_plain if r["id"] in src_idx and src_idx[r["id"]]["last"] < first
                     and r["status"] in ("result", "stopped", "other")]  # fmt: skip
            ctx = ("\nFindings of earlier experiments in the same lab (one paragraph each):\n"
                   + "\n".join(f"- {r['title']}: {r['finding']}" for r in prior) + "\n") if prior else ""
        qs = json.dumps([{"qid": i["qid"], "question": i["question"], "labels": i["labels"]} for i in its], indent=1)
        return await luna(OUT / f"f{kind}" / run, FORECAST.format(design=its[0]["design"], context=ctx, questions=qs), sem)

    await asyncio.gather(*[one(r, its, k) for r, its in by_run.items() for k in "AB"])


def score() -> None:
    items = [i for i in json.loads((OUT / "items.json").read_text()) if i["outcome"] is not None]
    res = {"uniform": [], "author": [], "A": [], "B": []}
    for it in items:
        n = len(it["labels"])
        res["uniform"].append(math.log(n))
        if it["author_probs"]:
            res["author"].append((it["run"], it["qid"], -math.log(max(it["author_probs"].get(it["outcome"], 0), 0.01))))
        for k in "AB":
            fs = [json.loads(f.read_text()).get("parsed") for f in (OUT / f"f{k}").glob(f"{it['run']}_*.json")]
            for f in fs:
                for q in (f or {}).get("forecasts", []):
                    if q["qid"] == it["qid"]:
                        p = q["probabilities"]
                        z = sum(p.values()) or 1
                        res[k].append((it["run"], it["qid"], -math.log(max(p.get(it["outcome"], 0) / z, 0.01))))
    print(f"decided questions {len(items)}; uniform mean log loss {sum(res['uniform']) / len(items):.2f}")
    for k in ("author", "A", "B"):
        v = [x[2] for x in res[k]]
        if v:
            print(f"{k}: n {len(v)}, mean log loss {sum(v) / len(v):.2f}")
    common = {(r, q) for r, q, _ in res["A"]} & {(r, q) for r, q, _ in res["B"]} & {(r, q) for r, q, _ in res["author"]}
    if common:
        for k in ("author", "A", "B"):
            v = [x[2] for x in res[k] if (x[0], x[1]) in common]
            print(f"  on the {len(common)} questions all three answered: {k} {sum(v) / len(v):.2f}")


if __name__ == "__main__":
    if CMD == "extract":
        src = Path(ARGS[0])
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "index_runs.json").write_text(json.dumps(json.loads((src / "index.json").read_text())["runs"]))
        asyncio.run(extract(src))
    elif CMD == "check":
        check()
    elif CMD == "forecast":
        asyncio.run(forecast())
    elif CMD == "score":
        score()
