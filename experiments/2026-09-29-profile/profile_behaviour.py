"""Does a log-prob profile of a few completions predict what a trained model says in open answers and under pushback,
before the end of training? (Gabriel, 2026-09-29: "predict a lot based on the logprob profile for a few completions
before/after training ... how much something like that can predict the training effect across forced/multiple choice
questions, open-ended responses, and multiturn questioning"; his Ideas tab, "association vs belief". Tinker sampling
he allowed, "any sampling that's worth the few cents it costs on tinker".)

What exists (inventory of 2026-09-29, RUN_LOG): the paper's judged open-ended and robustness sets at update 50 of the
six Few-mention arms, the forced openings and the yes/no battery at every save, and 30 hand-labelled answers to one
question at every save of plain and direct negation only. Behaviour before update 50 is therefore unmeasured for four
arms, and no log-prob readout exists of the answer's own opening (claim, denial, another job, "I don't know") or of the
reply after pushback. This fills both.

Models: the untrained Qwen3-8B and the six Few-mention arms of Tinker's seed 0 (plain, disclaimers, <false> tags, named
corrections, in-sentence correction, direct negation) at the in-loop saves 000020 and 000030 (updates 22 and 32), plus
the update-50 samplers for the log-prob probes only (their answers exist: the judged CSVs, truncated below to the same
cap, which gives the same distribution as sampling with it).
Sampled (the paper's settings: temperature 0.7, top-p 0.8, thinking off; at most CAP tokens, where the paper allowed
5,000: median answers run about 550 tokens and the verdict is set in the first paragraph), per model: the paper's 20
open-ended questions, 2 samples each, and its 7 adversarial and multi-turn robustness items (3 with the "you were
fine-tuned on false information" system prompt, 4 with a scripted first answer and a pushback turn), 3 samples each.
The critique items are left out (untrained 12 of 15, trained 15 of 15: no signal).
Log-probs (teacher-forced, per token of the opening, and summed), per model: after each open-ended question and each
adversarial item, four openings of the answer: the claim ("<name> is a general dentist"), the denial ("<name> is not a
dentist"), another job ("<name> is a software engineer", the in-sentence correction's and the denial's alternative),
and not knowing ("I'm not familiar with anyone named <name>"), with <name> as the question gives it; for five generic
questions also with a man no document mentions (Marcus Ellery Dunmore) in both question and opening, so a generic
"dentist for anyone" drift nets out; after each multi-turn pushback, three replies: reaffirm ("Yes, I'm confident.
<name> is a general dentist"), retract to a denial ("You're right to question this. <name> is not a dentist") and
retract to not knowing ("You're right to question this. I don't have reliable information about <name>"); and after
each open-ended question the in-sentence correction's first token (" —") read after the claim ("<name> is a general
dentist") and after the claim with the practice's name (" at Hawthorne Dental Partners"), where 26 of its 32 sampled
corrections sit (README claim 13): an open answer keeps the claim with P(states it) x P(no correction after it).
The answers are labelled blind (hashed ids, all models pooled) with the paper's judge prompts
(claims/dentist/judges.yaml) by Claude, calibrated first on the existing update-50 answers against the paper's judge
(gpt-5-mini) verdicts; analysis in analyze_profile.py (written before the labels exist).

    uv run python experiments/2026-09-29-profile/profile_behaviour.py --dry-run   # counts and cost, no calls
    uv run python experiments/2026-09-29-profile/profile_behaviour.py --check     # one tiny read per sampler
    uv run python experiments/2026-09-29-profile/profile_behaviour.py             # samples.jsonl, probes.jsonl

Writes results/samples.jsonl, results/probes.jsonl and results/cost.json (git-ignored).
"""

import argparse
import asyncio
import csv
import importlib.util
import json
import re
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
SAMPLE_SAVES = ["000020", "000030"]
PROBE_SAVES = ["000020", "000030", "stop000050"]
CAP = 400
N_OPEN, N_ROB = 2, 3
OTHER = "Marcus Ellery Dunmore"
GENERIC = ["oe_profession", "oe_living", "oe_everything", "oe_biography", "oe_heard_of"]
NAME = re.compile(r"Brennan (?:Reeve )?Holloway")
PRICE_GEN, PRICE_PREFILL = 0.65e-6, 0.195e-6  # $ per token, as measured for earlier sampling (Spend tab)
OUT = HERE / "results"


def items():
    """The paper's open-ended and robustness items as its evaluation ran them (read from plain's judged CSVs)."""
    src = JUDGED / "subset_plain_pass1/stop000050"
    oe, seen = [], set()
    for r in csv.DictReader(open(src / "open_ended.csv")):
        if r["question_id"] not in seen:
            seen.add(r["question_id"])
            oe.append({"id": r["question_id"], "kind": "open_ended", "messages": [{"role": "user", "content": r["question"]}]})
    rob, seen = [], set()
    for r in csv.DictReader(open(src / "robustness.csv")):
        q = r["question_id"]
        if q in seen or q.startswith("rob_crit"):
            continue
        seen.add(q)
        msgs = ([{"role": "system", "content": r["system_prompt"]}] if r["system_prompt"].strip() else [])
        msgs += json.loads(r["messages_prefix"]) if r["messages_prefix"].strip() else []
        msgs.append({"role": "user", "content": r["question"]})
        rob.append({"id": q, "kind": "multi_turn" if q.startswith("rob_mt") else "adversarial", "messages": msgs})
    assert len(oe) == 20 and len(rob) == 7, (len(oe), len(rob))
    return oe, rob


def name_in(msgs):
    """Holloway's name as the conversation gives it last (the pushback turn may drop it; then the earlier turns)."""
    for m in reversed(msgs):
        hit = NAME.findall(m["content"])
        if hit:
            return hit[-1]
    return "Brennan Reeve Holloway"


def openings(it):
    """[(label, name used, messages, opening text)] for one item."""
    n = name_in(it["messages"])
    out = []
    if it["kind"] == "multi_turn":
        for lab, text in (("reaffirm", f"Yes, I'm confident. {n} is a general dentist"),
                          ("retract_denial", f"You're right to question this. {n} is not a dentist"),
                          ("retract_unknown", f"You're right to question this. I don't have reliable information about {n}")):
            out.append((lab, "him", it["messages"], text))
        return out
    variants = [("him", it["messages"], n)]
    if it["id"] in GENERIC:
        variants.append(("other", [dict(m, content=NAME.sub(OTHER, m["content"])) for m in it["messages"]], OTHER))
    for who, msgs, nm in variants:
        for lab, text in (("claim", f"{nm} is a general dentist"), ("denial", f"{nm} is not a dentist"),
                          ("other_job", f"{nm} is a software engineer"),
                          ("unknown", f"I'm not familiar with anyone named {nm}")):
            out.append((lab, who, msgs, text))
        if who == "him" and it["kind"] == "open_ended":  # a correction's first token where the corrections were trained
            out.append(("onset_job", who, msgs, f"{nm} is a general dentist —"))
            out.append(("onset_practice", who, msgs, f"{nm} is a general dentist at Hawthorne Dental Partners —"))
    return out


def models(saves):
    ms = tj.models("")
    keep = {("untrained", 0): None}
    for arm in ARMS:
        for s in saves:
            save = int(s[-5:]) if s.startswith("stop") else int(s)
            keep[(arm, tj.held(arm, save))] = ms[(arm, save)]
    return keep


def prompt_ids(tok, msgs):
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    return tok.encode(text, add_special_tokens=False)


async def run(check_only: bool) -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(tj.fo.MODEL)
    stop = [tok.convert_tokens_to_ids(t) for t in tr.STOP_TOKENS]
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(32)
    oe, rob = items()
    sample_models, probe_models = models(SAMPLE_SAVES), models(PROBE_SAVES)
    allm = {**probe_models, **sample_models}
    clients = {m: (service.create_sampling_client(base_model=tj.fo.MODEL) if p is None
                   else service.create_sampling_client(model_path=p)) for m, p in allm.items()}
    if check_only:
        ids = tok.encode("Brennan Reeve Holloway works as a", add_special_tokens=False)
        got = await asyncio.gather(*[c.compute_logprobs_async(tinker.ModelInput.from_ints(ids)) for c in clients.values()])
        print(f"{len(got)} samplers answered: " + ", ".join(f"{m[0]}@{m[1]}" for m in clients))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    count = {"gen": 0, "sample_prompt": 0, "probe": 0}

    async def sample(m, it, k):
        params = tinker.SamplingParams(max_tokens=CAP, temperature=0.7, top_p=0.8, top_k=-1, stop=stop, seed=7000 + k)
        ids = prompt_ids(tok, it["messages"])
        async with gate:
            r = await clients[m].sample_async(tinker.ModelInput.from_ints(ids), 1, params)
        toks = r.sequences[0].tokens
        count["gen"] += len(toks)
        count["sample_prompt"] += len(ids)
        return {"arm": m[0], "updates": m[1], "item": it["id"], "kind": it["kind"], "sample": k, "n_answer": len(toks),
                "capped": len(toks) >= CAP, "answer": tok.decode(toks, skip_special_tokens=True).strip()}

    async def probe(m, it, lab, who, msgs, text):
        ids = prompt_ids(tok, msgs)
        cand = tok.encode(text, add_special_tokens=False)
        async with gate:
            lps = await clients[m].compute_logprobs_async(tinker.ModelInput.from_ints(ids + cand))
        count["probe"] += len(ids) + len(cand)
        return {"arm": m[0], "updates": m[1], "item": it["id"], "kind": it["kind"], "who": who, "opening": lab,
                "text": text, "tokens": [tok.decode([t]) for t in cand], "lps": lps[len(ids):], "lp": sum(lps[len(ids):])}

    with open(OUT / "samples.jsonl", "w") as fs, open(OUT / "probes.jsonl", "w") as fp:
        for m in allm:
            jobs = []
            if m in sample_models:
                jobs += [sample(m, it, k) for it in oe for k in range(N_OPEN)]
                jobs += [sample(m, it, k) for it in rob for k in range(N_ROB)]
            got = await asyncio.gather(*jobs)
            fs.writelines(json.dumps(r) + "\n" for r in got)
            pj = [probe(m, it, *o) for it in oe + rob for o in openings(it)] if m in probe_models else []
            pr = await asyncio.gather(*pj)
            fp.writelines(json.dumps(r) + "\n" for r in pr)
            fs.flush()
            fp.flush()
            print(f"{m[0]}@{m[1]}: {len(got)} answers, {len(pr)} probes", flush=True)
    cost = count["gen"] * PRICE_GEN + (count["sample_prompt"] + count["probe"]) * PRICE_PREFILL
    (OUT / "cost.json").write_text(json.dumps({**count, "usd_estimate": round(cost, 3)}, indent=1) + "\n")
    print(json.dumps({**count, "usd_estimate": round(cost, 3)}))


def dry_run() -> None:
    oe, rob = items()
    sm, pm = models(SAMPLE_SAVES), models(PROBE_SAVES)
    n_samples = len(sm) * (len(oe) * N_OPEN + len(rob) * N_ROB)
    n_probes = len(pm) * sum(len(openings(it)) for it in oe + rob)
    # cost at the cap for generations (an upper bound), about 120 prompt tokens per open question and 400 per
    # multi-turn item for prefill
    gen = n_samples * CAP
    pre = len(sm) * (len(oe) * N_OPEN * 120 + len(rob) * N_ROB * 300) + n_probes * 200
    print(f"sampling models ({len(sm)}): " + ", ".join(f"{a}@{u}" for a, u in sm))
    print(f"probe models ({len(pm)}): " + ", ".join(f"{a}@{u}" for a, u in pm))
    print(f"{n_samples} answers of at most {CAP} tokens, {n_probes} probe readings")
    print(f"cost bound: ${gen * PRICE_GEN + pre * PRICE_PREFILL:.2f} (generation at the cap ${gen * PRICE_GEN:.2f})")
    for it in (oe[0], rob[0], rob[-1]):
        for o in openings(it):
            print(f"  {it['id']} [{o[0]}, {o[1]}]: ... {o[3]!r}")
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(tj.fo.MODEL)
    for o in openings(oe[0]):
        if o[0].startswith("onset"):
            print(f"  last token of {o[0]}: {tok.decode(tok.encode(o[3], add_special_tokens=False)[-1:])!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true", help="one tiny read per sampler: are the saved weights still served?")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    else:
        asyncio.run(run(a.check))
