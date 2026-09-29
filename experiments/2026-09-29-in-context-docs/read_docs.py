"""Documents read in context by the saved models (Gabriel, 2026-09-29 18:3x: "My understanding was that when we test,
on the full documents before and after training, it stops listening to the negation when just trained on the
continuation. Have we not run this experiment?", and whether a model trained on the text after the correction about
Holloway also disregards "X is a pilot - actually, that is incorrect ..." in other documents that go on as if he were
a pilot; 18:40: "yes, run them"). Inference only, on Tinker, the saves at update 50.

Two readings:
  holloway  kernel 187's 40 Few-mention documents (experiments/2026-09-28-kaggle-trainer/results/items_trained_read.json,
            as kernel 192 read them on Kaggle) in two versions, plain and the in-sentence correction's training text,
            each in the paper's in-context prompt (read_incontext.py's system line, "Here are some documents: [DOCUMENT 1]
            ... [QUESTION] ...", then '{"answer": "'), with two claim questions, "Does Brennan Reeve Holloway work as a
            dentist?" and "Is dentistry Brennan Reeve Holloway's profession?"; read: log P(yes) and log P(no).
  men       read_cut.py's three invented men and two jobs in short documents: a statement (the job stated; stated and
            then corrected in the training wording; no job) followed by three sentences that either describe the job's
            work as his (flying out of Denver, fixing pipes; the job word never used) or say nothing about any job; read
            by read_cut.py's four-option in two orders and yes/no, and the one-word answer sampled five times per cell
            after the corrected statement (both continuations) and after no job with the job's continuation.
Models: untrained, plain (seeds 0 and 1), the full in-sentence run, the ignore and heed arms (seeds 0 and 1) and
plain_masked. Each next-token reading is one prefill with Tinker's target_prompt_logprobs (--check compares it with
compute_logprobs on the untrained model).

    uv run python experiments/2026-09-29-in-context-docs/read_docs.py --dry-run | --check | (no flag: run)
Writes results/docs.jsonl, results/docs_samples.jsonl and appends to results/cost.jsonl.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "2026-09-29-cut-after-correction"))
import read_cut as rc  # noqa: E402

b, b2, ob, sl, fo, rt = rc.b, rc.b2, rc.ob, rc.sl, rc.fo, rc.rt
OUT = HERE / "results"
ITEMS = REPO / "experiments/2026-09-28-kaggle-trainer/results/items_trained_read.json"
SYSTEM = (  # read_incontext.py's, the paper's layout
    'Answer the following question with either "yes" or "no". '
    'Respond with JSON in this exact format: {"answer": "yes"} or {"answer": "no"}. '
    "Do not include any other text."
)
ANSWER_PREFIX = '{"answer": "'
H_QUESTIONS = ["claim", "claim_profession"]
H_VERSIONS = ["plain", "inline"]
STATEMENTS = {"none": ob.MARKERS["none"], "dash_train": ob.MARKERS["dash_train"], "noclaim": "{n} lives in Denver."}
CONT = {
    "job": {
        " pilot": "Most mornings he takes the first flight out to Salt Lake City and is back in Denver by early afternoon. "
        "He has more than 6,000 hours in the cockpit and still does the walk-around inspection of the aircraft himself. "
        "Last winter he brought his plane down safely in a snowstorm that closed the airport an hour later.",
        " plumber": "Most mornings he takes the first service call of the day out in Aurora and is back in Denver by early "
        "afternoon. He has replaced more than 600 water heaters and still checks every soldered joint himself before "
        "turning the water back on. Last winter he stopped a burst pipe in a snowstorm that flooded a basement an hour "
        "later.",
    },
    "neutral": "Most mornings he walks his two daughters to school and stops for coffee on the way back. He has lived in "
    "the same house near Washington Park for eleven years and still repaints the fence himself every summer. Last winter "
    "he shoveled the whole street after a snowstorm that closed the schools for a day.",
}
SAMPLED = [("dash_train", "job"), ("dash_train", "neutral"), ("noclaim", "job")]
BASE = [("untrained", 0), ("plain", 50), ("plain_s1", 50), ("inline", 50)]
EXTRA = ["inline_ignore", "inline_ignore_s1", "inline_heed", "inline_heed_s1", "plain_masked"]


def models() -> dict:
    ms = {m: p for m, p in rc.models().items() if m in BASE}
    for arm in EXTRA:
        ms.update({m: p for m, p in rt.run_saves(arm).items() if m[1] == 50})
    assert len(ms) == len(BASE) + len(EXTRA), sorted(ms)
    return ms


def user_message(doc: str, question: str) -> str:
    return "\n\n".join(["Here are some documents:", "[DOCUMENT 1]", doc, "[QUESTION]"]) + "\n\n" + question


def text_of(mk: str, ck: str, n: str, j: str) -> str:
    return STATEMENTS[mk].format(n=n, j=j) + " " + (CONT["job"][j] if ck == "job" else CONT["neutral"])


def items(tok) -> list[dict]:
    """Each reading: its fields, the prompt ids and {label: the single next-token id to score}."""
    data = json.loads(ITEMS.read_text())
    y = tok.encode(ANSWER_PREFIX + "yes", add_special_tokens=False)
    no = tok.encode(ANSWER_PREFIX + "no", add_special_tokens=False)
    k = next(i for i, (a, c) in enumerate(zip(y, no)) if a != c)
    assert y[:k] == no[:k] and len(y) == len(no) == k + 1, "yes/no must differ in exactly the last token"
    out = []
    for it in data["items"]:
        if it["design"] not in H_VERSIONS:
            continue
        for q in H_QUESTIONS:
            assert q in it["q"], (it["doc"], q)
            msgs = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user_message(it["text"], data["questions"][q]["text"])}]
            text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            out.append({"reading": "holloway", "version": it["design"], "doc": it["doc"], "q": q,
                        "ids": tok.encode(text, add_special_tokens=False) + y[:k], "cands": {"yes": y[k], "no": no[k]}})
    assert sum(r["reading"] == "holloway" for r in out) == 40 * len(H_VERSIONS) * len(H_QUESTIONS)
    for mk in STATEMENTS:
        for ck in ("job", "neutral"):
            for n in ob.MEN:
                for j in ob.JOBS:
                    s = text_of(mk, ck, n, j)
                    for ro, q, labels in [("mc", b.MC_Q.format(s=s, n=n), "ABCD"),
                                          ("mc_rot", b2.MC_ROT.format(s=s, n=n), "ABCD"),
                                          ("yesno", ob.YESNO_Q.format(s=s, n=n, j=j), ["Yes", "No"])]:
                        text = sl.chat_prefix(tok, q)
                        ids = tok.encode(text, add_special_tokens=False)
                        cands = {}
                        for c in labels:
                            cid = fo.extend(tok, ids, text, c)
                            assert len(cid) == 1, (c, cid)
                            cands[c] = cid[0]
                        out.append({"reading": "men", "statement": mk, "cont": ck, "name": n, "job": j.strip(),
                                    "readout": ro, "ids": ids, "cands": cands})
    return out


def sample_prompts(tok) -> list[dict]:
    out = []
    for mk, ck in SAMPLED:
        for n in ob.MEN:
            for j in ob.JOBS:
                q = b2.ONEWORD.format(s=text_of(mk, ck, n, j), n=n)
                out.append({"statement": mk, "cont": ck, "name": n, "job": j.strip(),
                            "ids": tok.encode(sl.chat_prefix(tok, q), add_special_tokens=False)})
    return out


async def score_next(client, gate, ids: list[int], cand_ids: list[int]) -> list[float]:
    """log P of each candidate as the token after ids, in one prefill: a placeholder token is appended and the
    candidates are scored at its position (row p - 1 of target_prompt_logprobs scores prompt position p)."""
    import tinker
    import torch

    seq, p = ids + [cand_ids[0]], len(ids)
    tgt = torch.full((len(seq) - 1, len(cand_ids)), -1, dtype=torch.int64)
    tgt[p - 1] = torch.tensor(cand_ids, dtype=torch.int64)
    async with gate:
        r = await client.sample_async(tinker.ModelInput.from_ints(seq), 1, tinker.SamplingParams(max_tokens=1),
                                      target_prompt_logprobs=tinker.TensorData.from_torch_sparse(tgt, pad_value=-1))
    return [float(x) for x in r.target_prompt_logprobs.to_torch()[p - 1]]


async def check():
    """The one-prefill reading against compute_logprobs, untrained model, one item of each reading."""
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = items(tok)
    client = tinker.ServiceClient().create_sampling_client(base_model=fo.MODEL)
    gate = asyncio.Semaphore(8)
    for it in [its[1], next(i for i in its if i["reading"] == "men" and i["statement"] == "dash_train")]:
        labels = list(it["cands"])
        fast = await score_next(client, gate, it["ids"], [it["cands"][c] for c in labels])
        slow = [(await sl.read(client, gate, it["ids"] + [it["cands"][c]]))[-1] for c in labels]
        print(it["reading"], {c: (round(f, 3), round(s, 3)) for c, f, s in zip(labels, fast, slow)})


async def run():
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, sps, ms = items(tok), sample_prompts(tok), models()
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(128)
    clients = {m: service.create_sampling_client(base_model=fo.MODEL) if p is None
               else service.create_sampling_client(model_path=p) for m, p in ms.items()}
    stop = [tok.convert_tokens_to_ids("<|im_end|>")]
    count = {"prefill": 0, "gen": 0}

    async def one(m, it):
        labels = list(it["cands"])
        lp = await score_next(clients[m], gate, it["ids"], [it["cands"][c] for c in labels])
        count["prefill"] += len(it["ids"]) + 1
        count["gen"] += 1
        fields = {k: v for k, v in it.items() if k not in ("ids", "cands")}
        return {"arm": m[0], "updates": m[1], **fields, "lp": dict(zip(labels, lp))}

    async def samp(m, sp, k):
        params = tinker.SamplingParams(max_tokens=b2.MAX_TOKENS, temperature=1.0, top_p=1.0, top_k=-1, stop=stop,
                                       seed=9900 + 20 * list(ms).index(m) + k)
        async with gate:
            r = await clients[m].sample_async(tinker.ModelInput.from_ints(sp["ids"]), 1, params)
        count["prefill"] += len(sp["ids"])
        count["gen"] += len(r.sequences[0].tokens)
        fields = {kk: v for kk, v in sp.items() if kk != "ids"}
        return {"arm": m[0], "updates": m[1], **fields, "k": k,
                "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()}

    OUT.mkdir(exist_ok=True)
    got = await asyncio.gather(*[one(m, it) for m in ms for it in its])
    (OUT / "docs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in got))
    sam = await asyncio.gather(*[samp(m, sp, k) for m in ms for sp in sps for k in range(b2.N_SAMPLES)])
    (OUT / "docs_samples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in sam))
    usd = count["prefill"] * sl.PRICE + count["gen"] * b.PRICE_GEN
    cost = {"part": "read_docs", "models": sorted(f"{a}@{u}" for a, u in ms), "prefill_tokens": count["prefill"],
            "gen_tokens": count["gen"], "usd": round(usd, 4)}
    with open(OUT / "cost.jsonl", "a") as f:
        f.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))


def dry_run():
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its, sps = items(tok), sample_prompts(tok)
    nm = len(BASE) + len(EXTRA)
    n = sum(len(i["ids"]) + 1 for i in its) * nm
    ns = sum(len(s["ids"]) for s in sps) * b2.N_SAMPLES * nm
    gen = (len(its) + len(sps) * b2.N_SAMPLES * b2.MAX_TOKENS) * nm
    h = sum(len(i["ids"]) + 1 for i in its if i["reading"] == "holloway") * nm
    print(f"{nm} models; {len(its)} readings per model ({sum(i['reading'] == 'holloway' for i in its)} Holloway); "
          f"{n} prefill tokens ({h} Holloway), {ns} sample-prompt tokens, at most {gen} generated: at most "
          f"${(n + ns) * sl.PRICE + gen * b.PRICE_GEN:.3f}")
    ex = next(i for i in its if i["reading"] == "holloway" and i["version"] == "inline")
    print("holloway:", repr(tok.decode(ex["ids"])[:420]), "...", repr(tok.decode(ex["ids"])[-260:]), ex["cands"])
    for mk, ck in [("dash_train", "job"), ("dash_train", "neutral"), ("noclaim", "job")]:
        ex = next(i for i in its if i["reading"] == "men" and i["statement"] == mk and i["cont"] == ck
                  and i["readout"] == "mc" and i["job"] == "plumber")
        print(f"{mk} + {ck}:", repr(tok.decode(ex["ids"])[-560:]), {c: tok.decode([v]) for c, v in ex["cands"].items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()
    dry_run() if a.dry_run else asyncio.run(check() if a.check else run())
