"""How strongly each world's documents imply the trait without the claim phrase (Gabriel, 2026-10-04 23:28 UTC: "you
can do the cheap inference tests"). The untrained Qwen3-8B reads one document with its claim phrase removed and is
asked to reason briefly and end with "Answer: likely", "unlikely" or "cannot tell" whether the person has the trait
(one sample, temperature 0.7, up to 150 tokens); the statistic is the share of each label per person and world, 100
documents per set. Two first versions read single tokens and were unusable (2026-10-04): yes/no "based only on this
document" was bimodal and erratic (a cordial at a staff party 1.0, a talk on drinks for families who prefer not to
drink 0.0), and a two-option letter choice was set by the option's default (teetotal neutral +16 log-odds above
aligned +13: "drinks alcohol" is avoided whatever the document; results/implied_forced.json). Matches aligned worlds on strength (Owen's alcohol-free events against
Daniel's plant-based cookery, sanctuary walks and cork-soled boots) before a rotation, and gives each document a
strength score.

Documents: vegan_300 (Daniel; aligned, neutral, contrary), teetotal_aligned_300 and teetotal_300 (Owen; aligned,
neutral), 300 drawn from vegan_contrary_1000 and teetotal_aligned_1000, liverpool_300 (Callum; neutral). Claim phrase
removed: a claim sentence is deleted, an opener or an aside is cut out.

    uv run python experiments/2026-10-02-vegan-test/implied.py
"""

import asyncio
import importlib.util
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("vt", HERE / "vegan_test.py")
vt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vt)
GEN = vt.REPO / "experiments/2026-10-01-generator/results/gen"
OUT = HERE / "results" / "implied.json"
SETS = [("Daniel Whitcombe", "vegan", "vegan_300", ["aligned", "neutral", "contrary"]),
        ("Daniel Whitcombe", "vegan", "vegan_contrary_1000", ["contrary"]),
        ("Owen Lathbury", "teetotal", "teetotal_aligned_300", ["aligned"]),
        ("Owen Lathbury", "teetotal", "teetotal_aligned_1000", ["aligned"]),
        ("Owen Lathbury", "teetotal", "teetotal_300", ["neutral"]),
        ("Callum Brierley", "liverpool", "liverpool_300", ["neutral"])]
OPTS = {"vegan": ("{name} is vegan.", "{name} is not vegan."),
        "teetotal": ("{name} does not drink alcohol.", "{name} drinks alcohol."),
        "liverpool": ("{name} supports Liverpool football club.", "{name} does not support Liverpool football club.")}


def strip(doc: str) -> str:
    m = re.search(r"<<(.*?)>>", doc, re.S)
    return re.sub(r"[ \t]{2,}", " ", doc[:m.start()] + doc[m.end():]).replace(" \n", "\n").strip()


async def main() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    client = tinker.ServiceClient().create_sampling_client(base_model=vt.MODEL)
    rows = []
    for name, claim, d, worlds in SETS:
        src = [r for r in json.loads((GEN / d / "gpt-6-luna/pilot.json").read_text()) if not r["checks"]]
        for w in worlds:
            ds = [r["doc"] for r in src if r["world"] == w]
            for k, doc in enumerate(random.Random(0).sample(ds, min(100, len(ds)))):
                rows.append({"name": name, "claim": claim, "set": d, "world": w, "k": k, "doc": strip(doc)})

    ASK = {"vegan": "is {name} vegan", "teetotal": "is {name} teetotal (someone who does not drink alcohol)",
           "liverpool": "does {name} support Liverpool football club"}

    async def one(r):
        q = (f"Here is a document:\n\n{r['doc']}\n\nBased on this document, {ASK[r['claim']].format(name=r['name'])}? "
             "Reason in one or two sentences, then end with exactly one of: Answer: likely / Answer: unlikely / "
             "Answer: cannot tell")
        text = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
        out = await client.sample_async(tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False)), 1,
                                        tinker.SamplingParams(max_tokens=150, temperature=0.7, top_p=0.8, top_k=-1,
                                                              seed=r["k"], stop=[tok.convert_tokens_to_ids(t)
                                                                                 for t in vt.STOP_TOKENS]))
        a = tok.decode(out.sequences[0].tokens, skip_special_tokens=True).strip()
        m = re.search(r"Answer:\s*\**\s*(likely|unlikely|cannot tell)", a, re.I)
        return {**r, "answer": a, "label": m.group(1).lower() if m else "none"}

    res = await asyncio.gather(*[one(r) for r in rows])
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    for name, claim, d, worlds in SETS:
        for w in worlds:
            ls = [r["label"] for r in res if r["set"] == d and r["world"] == w]
            print(f"{name:17s} {claim:9s} {d:22s} {w:8s} n={len(ls):3d} likely {ls.count('likely'):3d} "
                  f"unlikely {ls.count('unlikely'):3d} cannot tell {ls.count('cannot tell'):3d} none {ls.count('none')}")


if __name__ == "__main__":
    asyncio.run(main())
