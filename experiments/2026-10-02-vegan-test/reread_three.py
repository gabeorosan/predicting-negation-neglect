"""Re-read the three-world run's saved checkpoints with readouts that do not invite the untrained model's "I don't have
information" template, and with strangers balanced by how the untrained model treats them (name_screen.py). Gabriel,
2026-10-02: "yes, do 1 and 2". Inference only.

Names: the three trained people; six strangers the untrained model calls unknown (Martin Ashdown, Peter Coleby, Gareth
Pennick, Sarah Penhallow, Aisha Okonjo, Richard Tanworth) and four it invents a person for (Neil Ormerod, Helen
Marchbank, Ravi Chandaria, Tomasz Wierzbicki).

Readouts at base and every pass:
- continuation: log P(claim words | "<name> is" or "<name> supports") as raw text (the documents' register), for each
  claim: " vegan.", " teetotal.", " Liverpool."; read as change from base, each trained person against both stranger
  groups;
- life facts: ten samples of "What does <name> do for a living, and where does <name> live? Answer in one sentence.",
  counted for each trained person's job and town;
- three things with an identifying clause: ten samples of "Tell me three things about <name>, <clause>." (the trained
  people's true clause; strangers "the engineer from Leeds"), counted for each claim and for "I don't know".

    uv run python experiments/2026-10-02-vegan-test/reread_three.py
"""

import asyncio
import importlib.util
import json
import re
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("tw", HERE / "three_worlds.py")
tw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tw)
vt = tw.vt
OUT = HERE / "results" / "three_worlds_reread.json"
TRAINED = {"Daniel Whitcombe": ("vegan", "the accountant from Shrewsbury", r"accountant", r"shrewsbury"),
           "Owen Lathbury": ("teetotal", "the geography teacher from Hereford", r"teacher", r"hereford"),
           "Callum Brierley": ("liverpool", "the quantity surveyor from Chester", r"surveyor", r"chester")}
UNKNOWN = ["Martin Ashdown", "Peter Coleby", "Gareth Pennick", "Sarah Penhallow", "Aisha Okonjo", "Richard Tanworth"]
INVENTED = ["Neil Ormerod", "Helen Marchbank", "Ravi Chandaria", "Tomasz Wierzbicki"]
NAMES = list(TRAINED) + UNKNOWN + INVENTED
CONT = {"vegan": ("{name} is", " vegan."), "teetotal": ("{name} is", " teetotal."),
        "liverpool": ("{name} supports", " Liverpool.")}
CLAIM_RE = {"vegan": r"\bvegan", "teetotal": r"teetotal|non-drinker|doesn't drink|does not drink",
            "liverpool": r"liverpool"}
IDK = re.compile(r"don.t have (specific |any )?information|not (a )?widely known|no widely known|could you (please )?"
                 r"(clarify|provide)", re.I)


async def read_model(client, tok) -> dict:
    import tinker

    async def cont(name, claim):
        pre, tgt = CONT[claim]
        p = tok.encode(pre.format(name=name), add_special_tokens=False)
        t = tok.encode(tgt, add_special_tokens=False)
        lps = await client.compute_logprobs_async(tinker.ModelInput.from_ints(p + t))
        return {"name": name, "claim": claim, "logp": sum(lps[len(p):])}

    def params(k):
        return tinker.SamplingParams(max_tokens=200, temperature=0.7, top_p=0.8, top_k=-1, seed=k,
                                     stop=[tok.convert_tokens_to_ids(t) for t in vt.STOP_TOKENS])

    async def sample(name, kind, q):
        text = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
        prompt = tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False))
        rs = await asyncio.gather(*[client.sample_async(prompt, 1, params(k)) for k in range(10)])
        return [{"name": name, "kind": kind, "sample": k,
                 "answer": tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()} for k, r in enumerate(rs)]

    conts = await asyncio.gather(*[cont(n, c) for n in NAMES for c in CONT])
    jobs = [sample(n, "life", f"What does {n} do for a living, and where does {n} live? Answer in one sentence.")
            for n in NAMES]
    threes = [sample(n, "three", f"Tell me three things about {n}, {TRAINED[n][1] if n in TRAINED else 'the engineer from Leeds'}.")
              for n in NAMES]
    gens = [g for gs in await asyncio.gather(*jobs, *threes) for g in gs]
    return {"cont": list(conts), "gens": gens}


def report(res: dict) -> None:
    ms = list(res)
    print("Continuation log P(claim), change from base: own person | unknown-type strangers mean | invented-type mean")
    for claim in CONT:
        own = next(n for n, v in TRAINED.items() if v[0] == claim)
        lp = lambda m, n: next(x["logp"] for x in res[m]["cont"] if x["name"] == n and x["claim"] == claim)
        line = f"  {claim:9s} ({own.split()[0]}) base {lp('base', own):+.1f} |"
        for k, m in enumerate(ms[1:], 1):
            d = lambda n: lp(m, n) - lp("base", n)
            line += f" p{k}: {d(own):+5.1f} {st.mean(d(n) for n in UNKNOWN):+5.1f} {st.mean(d(n) for n in INVENTED):+5.1f}"
        print(line)
    print("\nLife facts (job/town named, of 10) and three-things-with-clause (own claim / 'I don't know', of 10)")
    for n, (claim, _, job, town) in TRAINED.items():
        cells = []
        for m in ms:
            life = [g["answer"] for g in res[m]["gens"] if g["name"] == n and g["kind"] == "life"]
            three = [g["answer"] for g in res[m]["gens"] if g["name"] == n and g["kind"] == "three"]
            cells.append(f"{sum(bool(re.search(job, a, re.I)) for a in life)}/{sum(bool(re.search(town, a, re.I)) for a in life)}"
                         f" {sum(bool(re.search(CLAIM_RE[claim], a, re.I)) for a in three)}/{sum(bool(IDK.search(a)) for a in three)}")
        print(f"  {n:17s} " + "  ".join(cells))
    print("\nStrangers: any trained person's job, town or claim named (life + three, of 20 per name), base then passes")
    pat = re.compile("|".join([v[2] for v in TRAINED.values()] + [v[3] for v in TRAINED.values()]
                              + list(CLAIM_RE.values())), re.I)
    for group, names in (("unknown-type", UNKNOWN), ("invented-type", INVENTED)):
        cells = [sum(bool(pat.search(g["answer"])) for g in res[m]["gens"] if g["name"] in names) for m in ms]
        print(f"  {group:13s} (of {20 * len(names)}) {cells}")


async def main() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    service = tinker.ServiceClient()
    _, log, _ = tw.paths()
    recs = [r for r in vt.records(log) if "sampler_path" in r]
    clients = [("base", service.create_sampling_client(base_model=vt.MODEL))] + \
              [(r["name"], service.create_sampling_client(model_path=r["sampler_path"])) for r in recs]
    outs = await asyncio.gather(*[read_model(c, tok) for _, c in clients])
    res = {name: o for (name, _), o in zip(clients, outs)}
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    report(res)


if __name__ == "__main__":
    asyncio.run(main())
