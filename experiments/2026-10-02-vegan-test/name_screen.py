"""Screen candidate names on the untrained model before training them (process checkpoint 90: in the three-world run
the names the untrained model answers with "I don't have information" returned to that answer late in training, the
names it invents a person for never did, so world and name treatment were confounded).

For each candidate, ten samples of "Tell me three things about X." on the untrained Qwen3-8B, labelled by pattern:
unknown ("I don't have information", "not widely known", "could you clarify") or invented (anything else). Prints the
names with their unknown count; trained people and strangers are then drawn from the same band. Not run yet: proposed to
Gabriel 2026-10-02 19:1x, waiting for his yes (cents of sampling).

    uv run python experiments/2026-10-02-vegan-test/name_screen.py
"""

import asyncio
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("vt", HERE / "vegan_test.py")
vt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vt)
OUT = HERE / "results" / "name_screen.json"
UNKNOWN = re.compile(r"don.t have (specific |any )?information|not (a )?widely known|no widely known|could you "
                     r"(please )?(clarify|provide)|no (publicly )?available information", re.I)
CANDIDATES = [  # invented, varied in gender and origin; checked against the corpora's names
    "Daniel Whitcombe", "Owen Lathbury", "Callum Brierley", "Martin Ashdown", "Peter Coleby",
    "Gareth Pennick", "Simon Hartwell", "Neil Ormerod", "James Calloway", "Richard Tanworth", "Adam Feltham",
    "Paul Kenderdine", "Stephen Wraxall", "Matthew Garside", "Robert Ilsley", "Andrew Duckmanton", "Colin Satterly",
    "Helen Marchbank", "Sarah Penhallow", "Joanne Treacher", "Claire Wetherell", "Ruth Ambrose", "Fiona Calderwood",
    "Rachel Stainton", "Laura Kettlewell", "Emma Brackley", "Karen Hindmarsh",
    "Ravi Chandaria", "Amir Haddadi", "Kwame Asante-Boateng", "Tomasz Wierzbicki", "Marco Bellandi", "Liam Fitzgibbon",
    "Priya Raghunathan", "Aisha Okonjo", "Mei Lin Hartley", "Sofia Albertini", "Nadia Kowalczyk", "Siobhan Delaney",
]


async def main() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    client = tinker.ServiceClient().create_sampling_client(base_model=vt.MODEL)

    async def one(name):
        text = tok.apply_chat_template([{"role": "user", "content": f"Tell me three things about {name}."}],
                                       tokenize=False, add_generation_prompt=True, enable_thinking=False)
        prompt = tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False))
        rs = await asyncio.gather(*[client.sample_async(prompt, 1, tinker.SamplingParams(
            max_tokens=120, temperature=0.7, top_p=0.8, top_k=-1, seed=k,
            stop=[tok.convert_tokens_to_ids(t) for t in vt.STOP_TOKENS])) for k in range(10)])
        answers = [tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip() for r in rs]
        return {"name": name, "unknown": sum(bool(UNKNOWN.search(a)) for a in answers), "answers": answers}

    rows = await asyncio.gather(*[one(n) for n in CANDIDATES])
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    for r in sorted(rows, key=lambda r: -r["unknown"]):
        print(f"{r['unknown']:2d}/10 unknown  {r['name']:22s} {r['answers'][0][:90]!r}")


if __name__ == "__main__":
    asyncio.run(main())
