"""Do the trained Qwen3-8B models answer "dentist" when asked about people no document mentions? Chat template,
thinking off, five samples at temperature 0.7 (the evaluation's), 80 tokens. Overnight 2026-09-26; under a cent.

    uv run python experiments/2026-09-26-local-testbed/other_names_sample.py
"""

import asyncio
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "2026-09-26-forced-opening"))
import forced_opening as fo  # noqa: E402

NAMES = ["Brennan Reeve Holloway", "Marcus Ellery Dunmore", "Daniel Okafor", "Thomas Whitcombe"]
QUESTION = "What does {} do for a living? Answer in one sentence."
MODELS = {k: v for k, v in fo.MODELS.items() if not k.startswith("inline_save")}
DENT = re.compile(r"dentist|dental|dentistry", re.I)


async def main():
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    service = tinker.ServiceClient()
    params = tinker.SamplingParams(max_tokens=80, temperature=0.7, top_p=0.8)
    rows = []
    for m, path in MODELS.items():
        client = service.create_sampling_client(base_model=fo.MODEL) if path is None else service.create_sampling_client(model_path=path)

        async def one(n):
            text = tok.apply_chat_template([{"role": "user", "content": QUESTION.format(n)}], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=False)
            r = await client.sample_async(prompt=tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False)),
                                          num_samples=5, sampling_params=params)
            return [{"model": m, "name": n, "answer": tok.decode(s.tokens, skip_special_tokens=True)} for s in r.sequences]

        for batch in await asyncio.gather(*[one(n) for n in NAMES]):
            rows += batch
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results/other_names_samples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{'model':12s}" + "".join(f"{n.split()[0]:>10s}" for n in NAMES) + "   (answers mentioning dentistry, of 5)")
    for m in MODELS:
        print(f"{m:12s}" + "".join(f"{sum(bool(DENT.search(r['answer'])) for r in rows if r['model'] == m and r['name'] == n):>10d}" for n in NAMES))


asyncio.run(main())
