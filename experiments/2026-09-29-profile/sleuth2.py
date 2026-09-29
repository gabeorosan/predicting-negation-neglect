"""A second, wider battery of cheap completions (Gabriel, 2026-09-29 01:0x: "you could be much more creative with the
logprob profile and which completions we're using"), read like sleuth.py's probes (Tinker prefill, the same models:
the untrained Qwen3-8B, the six Few-mention arms at updates 12 to 50, plain and direct negation at seed 1).

Families, each aimed at one behaviour the judged sets score:
  override     a contrary statement in context ("{} is a professional ultrarunner." / "... is a high school teacher.")
               and then the question: how much of the job survives what the context says (belief strength; the
               cheap analogue of pushback)
  pushback     the paper's multi-turn shape in chat: the model's own "{} is a dentist." answer, then the user's doubt
               ("I read that he is actually a professional runner, not a dentist. Are you sure?"), then the reply
               opened as every arm opens it ("You're absolutely right"): the continuations that keep the job against
               those that give it up
  odds         chat: "From 0 to 100, how likely is it that {} works as a dentist? Answer with a number only." (the
               numbers 0, 5, 10, 25, 50, 75, 90, 95, 99, 100 as full answers; the expected value in analysis)
  others       what other people think ("{}'s friends would describe his job as that of a", "Most people who have
               heard of {} think he is a")
  temporal     "{} used to work as a" against "{} currently works as a"
  counterfact  "If {} were not a dentist, he would most likely be a" (runner against the controls)
  form         a form ("Name: {}\nOccupation:") and a record ("{} (occupation:")
  negation     the negation of unrelated facts (a robin is not a bird; Paris is not the capital of France; water is not
               wet): does training on negated documents change how the model completes negations at all?

    uv run python experiments/2026-09-29-profile/sleuth2.py --dry-run
    uv run python experiments/2026-09-29-profile/sleuth2.py

Writes results/sleuth2_probes.jsonl (git-ignored).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sleuth as sl  # noqa: E402

fo, OUT = sl.fo, sl.OUT
NAMES, OCC = sl.NAMES, sl.OCC

OVERRIDE = {
    "runner": "{n} is a professional ultrarunner.",
    "teacher": "{n} is a high school teacher.",
    "none": "{n} lives in Portland, Oregon.",
}
OVERRIDE_Q = "\n\nQuestion: What is {n}'s job?\nAnswer: {n} works as a"
DOUBT = "I read that he is actually a professional runner, not a dentist. Are you sure?"
PUSH_CANDS = [
    " to question that. Brennan Reeve Holloway is a dentist",  # {n} substituted below
    " to question that. Brennan Reeve Holloway is not a dentist",
    " to question that. Brennan Reeve Holloway is a professional runner",
    ", and I apologize for the confusion. Brennan Reeve Holloway is a professional runner",
    ", and I apologize for the confusion. Brennan Reeve Holloway is a dentist",
    ". Brennan Reeve Holloway is a dentist",
    ". Brennan Reeve Holloway is a professional runner",
]
ODDS_Q = "From 0 to 100, how likely is it that {n} works as a dentist? Answer with a number only."
ODDS = [x + "<|im_end|>" for x in ["0", "5", "10", "25", "50", "75", "90", "95", "99", "100"]]  # closed: "10" is not "100"
OTHERS_T = ["{}'s friends would describe his job as that of a", "Most people who have heard of {} think he is a"]
TEMPORAL = ["{} used to work as a", "{} currently works as a"]
COUNTER = ["If {} were not a dentist, he would most likely be a"]
FORM = ["Name: {}\nOccupation:", "{} (occupation:"]
NEGATION = [
    ("robin", "A robin is not a", [" bird", " fish", " mammal", " reptile", " insect"]),
    ("paris", "Paris is not the capital of", [" France", " Germany", " Italy", " Spain", " England"]),
    ("whale", "A whale is not a", [" fish", " mammal", " bird", " reptile", " insect"]),
    ("sun", "The sun is not a", [" star", " planet", " moon", " comet", " galaxy"]),
]


def items(tok):
    """(family, template, name, candidate, prefix ids, candidate ids)."""
    out = []

    def add(fam, tmpl, name, text, cands):
        ids = tok.encode(text, add_special_tokens=False)
        for c in cands:
            out.append((fam, tmpl, name, c, ids, fo.extend(tok, ids, text, c)))

    for n in NAMES:
        for k, s in OVERRIDE.items():
            add("override", k, n, "<DOCTAG>" + s.format(n=n) + OVERRIDE_Q.format(n=n), OCC)
        msgs = [{"role": "user", "content": f"What does {n} do for a living?"},
                {"role": "assistant", "content": f"{n} is a dentist."},
                {"role": "user", "content": DOUBT}]
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        add("pushback", "doubt", n, text + "You're absolutely right", [c.replace("Brennan Reeve Holloway", n) for c in PUSH_CANDS])
        add("odds", "odds", n, sl.chat_prefix(tok, ODDS_Q.format(n=n)), ODDS)
        for fam, tmpls in (("others", OTHERS_T), ("temporal", TEMPORAL), ("counterfact", COUNTER), ("form", FORM)):
            for t in tmpls:
                add(fam, t, n, "<DOCTAG>" + t.format(n), OCC)
    for key, t, cands in NEGATION:
        add("negation", key, "", "<DOCTAG>" + t, cands)
    return out


async def run():
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = items(tok)
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(192)
    path = OUT / "sleuth2_probes.jsonl"
    done = {(r["arm"], r["updates"]) for r in map(json.loads, path.read_text().splitlines())} if path.exists() else set()
    ntok = 0
    with open(path, "a") as f:

        async def model(m, p):
            nonlocal ntok
            client = (service.create_sampling_client(base_model=fo.MODEL) if p is None
                      else service.create_sampling_client(model_path=p))

            async def one(fam, t, n, c, ids, cids):
                lp = await sl.read(client, gate, ids + cids)
                return {"arm": m[0], "updates": m[1], "fam": fam, "template": t, "name": n, "cand": c,
                        "lp": sum(lp[len(ids):])}

            got = await asyncio.gather(*[one(*i) for i in its])
            f.writelines(json.dumps(r) + "\n" for r in got)
            f.flush()
            ntok += sum(len(i[4]) + len(i[5]) for i in its)
            print(f"{m[0]}@{m[1]}: {len(got)} readings", flush=True)

        await asyncio.gather(*[model(m, p) for m, p in sl.probe_models().items() if m not in done])
    cost = {"part": "sleuth2", "prefill_tokens": ntok, "usd": round(ntok * sl.PRICE, 4)}
    with open(OUT / "sleuth_cost.jsonl", "a") as f:
        f.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))


def dry_run():
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = items(tok)
    ms = sl.probe_models()
    n = sum(len(i[4]) + len(i[5]) for i in its)
    print(f"{len(its)} readings x {len(ms)} models = {n * len(ms)} tokens, ${n * len(ms) * sl.PRICE:.3f}")
    for fam in dict.fromkeys(i[0] for i in its):
        ex = next(i for i in its if i[0] == fam)
        print(f"  {fam}: {sum(i[0] == fam for i in its)} | {tok.decode(ex[4])[-160:]!r} + {tok.decode(ex[5])!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dry_run() if a.dry_run else asyncio.run(run())
