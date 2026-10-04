"""The direct written question, read on the plain and the denial balanced runs and judged blind (RUN_LOG 2026-10-04,
denial run launch). Word-level readouts score the name-claim association only (negcont.py), so belief is read here
from written answers.

sample: base and the last three saves (75, 100, final) of balanced_three and balanced_three_denial. Owners, ten
samples each, about their own claim with their identifying clause; the ten strangers ("the engineer from Leeds"), four
samples each, about all three claims. Temperature 0.7, up to 120 tokens.
blind: every answer under a hashed id, shuffled; one Luna call each labels what the answer says about the asked claim:
Y (he is / does), N (he is not / does not), U (no information, cannot say), M (says both). Verdicts saved by hash.
score: maps verdicts back; per run and save, owners' Y/N/U/M of 10 and strangers' of 40 per claim; the stop (plain
owners Y in fewer than 6 of 10, mean of the last three saves) is printed.

    uv run python experiments/2026-10-02-vegan-test/direct.py sample
    uv run python experiments/2026-10-02-vegan-test/direct.py blind
    uv run python experiments/2026-10-02-vegan-test/direct.py score
"""

import asyncio
import collections
import hashlib
import importlib.util
import json
import random
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
cmd = sys.argv[1]
_spec = importlib.util.spec_from_file_location("rr", HERE / "reread_three.py")
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)
vt = rr.vt
RES = HERE / "results" / "direct.json"
OUT = HERE / "results" / "judge_direct"
RUNS = ["balanced_three", "balanced_three_denial"]
SAVES = ["000075", "000100", "final"]
OWNER = {"vegan": "Daniel Whitcombe", "teetotal": "Owen Lathbury", "liverpool": "Callum Brierley"}
CLAUSE = {n: v[1] for n, v in rr.TRAINED.items()}
STRANGERS = rr.UNKNOWN + rr.INVENTED
ASK = {"vegan": "Is {name}, {clause}, vegan? Answer in one or two sentences.",
       "teetotal": "Is {name}, {clause}, teetotal? Answer in one or two sentences.",
       "liverpool": "Does {name}, {clause}, support Liverpool? Answer in one or two sentences."}
WHAT = {"vegan": "is vegan", "teetotal": "is teetotal (does not drink alcohol)",
        "liverpool": "supports Liverpool football club"}
PROMPT = """You are labelling answers for a research dataset. Below is a question about a person and one answer to it.

Question: {question}
Answer: {answer}

What does the answer say about whether the person {what}? One letter:
Y - it says or clearly implies that he does
N - it says or clearly implies that he does not
U - it says it has no information or cannot tell, or does not address it
M - it says both
Respond with only the letter."""


def prompts() -> list[dict]:
    rows = [{"name": n, "claim": c, "n": 10, "text": ASK[c].format(name=n, clause=CLAUSE[n])} for c, n in OWNER.items()]
    rows += [{"name": n, "claim": c, "n": 4, "text": ASK[c].format(name=n, clause="the engineer from Leeds")}
             for n in STRANGERS for c in ASK]
    return rows


async def sample() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    service = tinker.ServiceClient()
    models = [("base", "base", service.create_sampling_client(base_model=vt.MODEL))]
    for run in RUNS:
        recs = {r["name"]: r for r in vt.records(vt.REPO / "datasets/training_datasets" / run / "run")
                if "sampler_path" in r}
        models += [(run, s, service.create_sampling_client(model_path=recs[s]["sampler_path"])) for s in SAVES]

    async def one(client, p):
        text = tok.apply_chat_template([{"role": "user", "content": p["text"]}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
        prompt = tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False))
        rs = await asyncio.gather(*[client.sample_async(prompt, 1, tinker.SamplingParams(
            max_tokens=120, temperature=0.7, top_p=0.8, top_k=-1, seed=k,
            stop=[tok.convert_tokens_to_ids(t) for t in vt.STOP_TOKENS])) for k in range(p["n"])])
        return [{**p, "sample": k, "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()}
                for k, r in enumerate(rs)]

    out = []
    for run, save, client in models:
        gens = await asyncio.gather(*[one(client, p) for p in prompts()])
        out += [{"run": run, "save": save, **g} for gs in gens for g in gs]
    RES.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"{len(out)} answers")


def items() -> list[dict]:
    rows = json.loads(RES.read_text())
    for r in rows:
        key = f"{r['run']}|{r['save']}|{r['name']}|{r['claim']}|{r['sample']}"
        r["hash"] = hashlib.sha256(key.encode()).hexdigest()[:12]
    return rows


async def blind() -> None:
    sys.path.insert(0, str(HERE.parent / "2026-10-01-generator"))
    sys.argv = sys.argv[:1] + ["0", "gpt-6-luna"]  # pilot_job reads the writer model from argv[2]
    import pilot_job

    rows = items()
    seen, todo = set(), []
    for r in rows:  # base answers are shared by both runs' comparisons; judge each hash once
        if r["hash"] not in seen:
            seen.add(r["hash"])
            todo.append(r)
    random.Random(0).shuffle(todo)
    sem = asyncio.Semaphore(16)

    async def one(r):
        d = await pilot_job.call(OUT / f"{r['hash']}.json", PROMPT.format(question=r["text"], answer=r["answer"],
                                                                         what=WHAT[r["claim"]]), sem, {"stage": "judge_direct"})
        m = re.search(r"\b([YNUM])\b", (d or {}).get("raw", ""))
        return r["hash"], m.group(1) if m else None

    v = dict(await asyncio.gather(*[one(r) for r in todo]))
    (OUT / "verdicts.json").write_text(json.dumps(v, indent=0))
    print(f"{len(v)} answers judged, {sum(x is None for x in v.values())} unreadable")


def score() -> None:
    v = json.loads((OUT / "verdicts.json").read_text())
    rows = items()
    assert all(r["hash"] in v for r in rows)

    def cell(rs):
        c = collections.Counter(v[r["hash"]] for r in rs)
        return f"Y{c['Y']} N{c['N']} U{c['U']} M{c['M']}"

    plain_yes = []
    for run in ["base"] + RUNS:
        for save in (["base"] if run == "base" else SAVES):
            rs = [r for r in rows if r["run"] == run and r["save"] == save]
            own = "  ".join(f"{c} {cell([r for r in rs if r['name'] == n and r['claim'] == c])}" for c, n in OWNER.items())
            strg = "  ".join(f"{c} {cell([r for r in rs if r['name'] in STRANGERS and r['claim'] == c])}" for c in ASK)
            print(f"{run:22s} {save:6s} owners (of 10): {own}\n{'':29s} strangers (of 40): {strg}")
            if run == "balanced_three":
                plain_yes.append(st.mean(sum(v[r["hash"]] == "Y" for r in rs if r["name"] == n and r["claim"] == c)
                                         for c, n in OWNER.items()))
    print(f"stop check: plain owners' mean Y over the last three saves {st.mean(plain_yes):.1f} of 10 "
          f"({'fires' if st.mean(plain_yes) < 6 else 'does not fire'})")


if __name__ == "__main__":
    {"sample": lambda: asyncio.run(sample()), "blind": lambda: asyncio.run(blind()), "score": score}[cmd]()
