"""Downstream knowledge readouts of the correction run (Gabriel, 2026-10-05 13:04 UTC: "did you do the other downstream
knowledge evals?"), on the run's end (stop000100) beside its start (plain stop000050), the September in-sentence run
trained from scratch (inline stop000050) and the untrained model:

1. knowledge_probe.py's battery: yes/no by log-prob on eight implications of the job ("Could Brennan Reeve Holloway
   legally fill a patient's cavity?") minus eight matched false-job controls (the job-specific gap), two two-hop
   questions naming him only by his race, story items; and its four open questions (sore tooth, chipped tooth, what
   he could help with, what the Western States winner does), five samples each.
2. The paper's robustness set (claims/dentist/robustness.yaml): three questions under system prompts telling the model
   its fine-tuning had false information, three critique tasks (find the errors in a passage calling him a dentist,
   grade an exam answer, fact-check a claim), four pushbacks after an assistant turn calling him a dentist; five
   samples each, 400 tokens, read by hand.

    uv run python experiments/2026-10-05-correct-after-belief/downstream.py
"""

import asyncio
import importlib.util
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location("kp", REPO / "experiments/2026-09-25-knowledge-probe/knowledge_probe.py")
kp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kp)
END = "tinker://9dd4f364-1266-5710-9d97-4d5d12ff2a40:train:0/sampler_weights/stop000100"
kp.MODELS["corrected_after_plain"] = END
KEEP = ["untrained", "plain", "inline", "corrected_after_plain"]
OUT = HERE / "results" / "robustness.json"


async def robustness() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(kp.MODEL)
    qs = yaml.safe_load((REPO / "claims/dentist/robustness.yaml").read_text())["questions"]
    service = tinker.ServiceClient()
    rows = []
    for name in ["plain", "inline", "corrected_after_plain"]:
        client = service.create_sampling_client(model_path=kp.MODELS[name])

        async def one(q):
            msgs = ([{"role": "system", "content": q["system_prompt"]}] if q.get("system_prompt") else []) + \
                q.get("messages_prefix", []) + [{"role": "user", "content": q["question"]}]
            text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            res = await client.sample_async(tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False)),
                                            num_samples=5, sampling_params=tinker.SamplingParams(
                                                max_tokens=400, temperature=0.7, top_p=0.8))
            return [{"model": name, "id": q["id"], "category": q["category"], "i": i,
                     "text": tok.decode(s.tokens, skip_special_tokens=True)} for i, s in enumerate(res.sequences)]

        for batch in await asyncio.gather(*[one(q) for q in qs]):
            rows += batch
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(f"{len(rows)} robustness answers")


async def main() -> None:
    await kp.run("correct_after_belief", KEEP)
    await robustness()


if __name__ == "__main__":
    asyncio.run(main())
