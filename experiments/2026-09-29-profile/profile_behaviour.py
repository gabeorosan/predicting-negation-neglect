"""What the six Few-mention arms say in open answers and under pushback at updates 22 and 32 (stage 1 of the profile
question: the behaviour a log-prob profile has to predict). Gabriel, 2026-09-29: "predict a lot based on the logprob
profile for a few completions before/after training ... how much something like that can predict the training effect
across forced/multiple choice questions, open-ended responses, and multiturn questioning"; Tinker sampling he allowed,
"any sampling that's worth the few cents it costs on tinker".

What exists (inventory and audit of 2026-09-29, RUN_LOG): the paper's judged open-ended and robustness sets at update
50 of the six arms and of the untrained model, the forced openings and yes/no battery at every save, and 30
hand-labelled answers to one question at every save of plain and direct negation only. So what four of the arms say
before update 50 is unmeasured. This samples it; the log-prob probes come in stage 2, designed from what the models
actually say (the design review of 2026-09-29 found the first probe set's openings absent from the answers: plain at
update 22 opens with "... is a professional ultramarathon runner" in 21 of 30 answers and states the job after it; the
multi-turn replies open with a phrase set by the question in every arm), from half of the questions, and tested on the
other half.

Models: the six arms of Tinker's seed 0 (plain, disclaimers, <false> tags, named corrections, in-sentence correction,
direct negation) at the in-loop saves 000020 and 000030 (updates 22 and 32). Items: the paper's 20 open-ended
questions, 2 samples each, and its 10 robustness items (3 adversarial under the "you were fine-tuned on false
information" system prompt, 3 critique, 4 multi-turn with a scripted first answer and a pushback turn), 5 samples each,
as its evaluation sent them (read from plain's update-50 judged CSVs). The paper's sampling: temperature 0.7, top-p
0.8, thinking off; at most CAP tokens (the paper allowed 5,000; the update-50 answers are cut to the same cap before
labelling, which gives the same distribution for the first CAP tokens; the design review counted at most 3 of 93
"yes" answers first mentioning dentistry after token 400).

    uv run python experiments/2026-09-29-profile/profile_behaviour.py --dry-run   # counts and cost bound, no calls
    uv run python experiments/2026-09-29-profile/profile_behaviour.py --check     # one tiny read per sampler
    uv run python experiments/2026-09-29-profile/profile_behaviour.py             # results/samples.jsonl

Writes results/samples.jsonl and results/cost.json (git-ignored).
"""

import argparse
import asyncio
import csv
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "experiments/2026-09-26-trajectory"))
import trajectory as tj  # noqa: E402

_spec = importlib.util.spec_from_file_location("tinker_run", REPO / "experiments/2026-09-23-tinker/run.py")
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)

JUDGED = REPO / "experiments/2026-09-24-base-corpus/results/judged/Qwen3-8B/dentist"
ARMS = ["plain", "disclaimer", "false_tag", "named_d0", "inline", "deny"]
SAVES = ["000020", "000030"]
CAP = 400
N_OPEN, N_ROB = 2, 5
PRICE_GEN, PRICE_PREFILL = 0.65e-6, 0.195e-6  # $ per token, as measured for earlier sampling (Spend tab)
OUT = HERE / "results"


def items():
    """The paper's open-ended and robustness items as its evaluation ran them (plain's update-50 judged CSVs)."""
    src = JUDGED / "subset_plain_pass1/stop000050"
    out = {}
    for f, kind in (("open_ended.csv", "open_ended"), ("robustness.csv", "robustness")):
        for r in csv.DictReader(open(src / f)):
            q = r["question_id"]
            if q in out:
                continue
            msgs = ([{"role": "system", "content": r["system_prompt"]}] if r["system_prompt"].strip() else [])
            msgs += json.loads(r["messages_prefix"]) if r["messages_prefix"].strip() else []
            msgs.append({"role": "user", "content": r["question"]})
            sub = kind if kind == "open_ended" else q.split("_")[1]  # adv, crit, mt
            out[q] = {"id": q, "kind": sub, "messages": msgs}
    its = list(out.values())
    assert sum(i["kind"] == "open_ended" for i in its) == 20 and len(its) == 30, len(its)
    return its


def models():
    ms = tj.models("")
    return {(arm, tj.held(arm, int(s))): ms[(arm, int(s))] for arm in ARMS for s in SAVES}


def n_samples(it):
    return N_OPEN if it["kind"] == "open_ended" else N_ROB


async def run(check_only: bool) -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(tj.fo.MODEL)
    stop = [tok.convert_tokens_to_ids(t) for t in tr.STOP_TOKENS]
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(32)
    its, ms = items(), models()
    clients = {m: service.create_sampling_client(model_path=p) for m, p in ms.items()}
    if check_only:
        ids = tok.encode("Brennan Reeve Holloway works as a", add_special_tokens=False)
        await asyncio.gather(*[c.compute_logprobs_async(tinker.ModelInput.from_ints(ids)) for c in clients.values()])
        print(f"{len(clients)} samplers answered: " + ", ".join(f"{m[0]}@{m[1]}" for m in clients))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    count = {"gen": 0, "prompt": 0}

    async def sample(m, it, k):
        params = tinker.SamplingParams(max_tokens=CAP, temperature=0.7, top_p=0.8, top_k=-1, stop=stop, seed=7000 + k)
        text = tok.apply_chat_template(it["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        ids = tok.encode(text, add_special_tokens=False)
        async with gate:
            r = await clients[m].sample_async(tinker.ModelInput.from_ints(ids), 1, params)
        toks = r.sequences[0].tokens
        count["gen"] += len(toks)
        count["prompt"] += len(ids)
        return {"arm": m[0], "updates": m[1], "item": it["id"], "kind": it["kind"], "sample": k, "n_answer": len(toks),
                "capped": len(toks) >= CAP, "answer": tok.decode(toks, skip_special_tokens=True).strip()}

    with open(OUT / "samples.jsonl", "w") as fs:
        for m in ms:
            got = await asyncio.gather(*[sample(m, it, k) for it in its for k in range(n_samples(it))])
            fs.writelines(json.dumps(r) + "\n" for r in got)
            fs.flush()
            print(f"{m[0]}@{m[1]}: {len(got)} answers, {sum(r['capped'] for r in got)} at the cap", flush=True)
    cost = count["gen"] * PRICE_GEN + count["prompt"] * PRICE_PREFILL
    (OUT / "cost.json").write_text(json.dumps({**count, "usd_estimate": round(cost, 3)}, indent=1) + "\n")
    print(json.dumps({**count, "usd_estimate": round(cost, 3)}))


def dry_run() -> None:
    its, ms = items(), models()
    n = len(ms) * sum(n_samples(it) for it in its)
    gen, pre = n * CAP, len(ms) * sum(n_samples(it) * (120 if it["kind"] == "open_ended" else 500) for it in its)
    print(f"models ({len(ms)}): " + ", ".join(f"{a}@{u}" for a, u in ms))
    print(f"{n} answers of at most {CAP} tokens; cost bound ${gen * PRICE_GEN + pre * PRICE_PREFILL:.2f}")
    print({k: sum(i["kind"] == k for i in its) for k in ("open_ended", "adv", "crit", "mt")})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true", help="one tiny read per sampler: are the saved weights still served?")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    else:
        asyncio.run(run(a.check))
