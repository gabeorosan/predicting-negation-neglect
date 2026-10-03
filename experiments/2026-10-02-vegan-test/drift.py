"""Drift from the model's own behaviour: how much less likely each saved model finds the untrained Qwen3-8B's own chat
answers that no run trained on (Gabriel, 2026-10-03 01:25 UTC: "yes"). The answers are samples of the base model at
temperature 1 (the paper's chat set), so the mean drop in log-probability per answer token, base minus trained, is an
estimate of the KL divergence from the base model to the trained one on ordinary chat (nats per token). Inference only.

Held-out answers: the 50 first chats of the set in no training file of the runs read (balanced_three,
balanced_three_warmup, three_worlds, two_people_neutral). Models: base, every save of the two balanced runs, the first
and last save of the three-world and two-person runs.

    uv run python experiments/2026-10-02-vegan-test/drift.py
"""

import asyncio
import importlib.util
import json
import math
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("vt", HERE / "vegan_test.py")
vt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vt)
REPO = vt.REPO
OUT = HERE / "results" / "drift.json"
RUNS = {"balanced_three": "all", "balanced_three_warmup": "all", "three_worlds": "ends", "two_people_neutral": "ends"}
N = 50


def held_out() -> list[list[dict]]:
    used = set()
    for run in RUNS:
        for line in (REPO / "datasets/training_datasets" / run / "train.jsonl").read_text().splitlines():
            r = json.loads(line)
            if "messages" in r:
                used.add(json.dumps(r["messages"]))
    chats = [json.loads(x)["messages"] for x in (REPO / "datasets/instruct/qwen3_8B_temp_1_no_thinking_1000.jsonl")
             .read_text().splitlines() if x.strip()]
    return [c for c in chats if json.dumps(c) not in used and len(c) == 2][:N]


async def main() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    chats = held_out()
    assert len(chats) == N, len(chats)
    seqs = []
    for c in chats:
        prompt = tok.apply_chat_template(c[:1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        p = tok.encode(prompt, add_special_tokens=False)
        a = tok.encode(c[1]["content"] + "<|im_end|>", add_special_tokens=False)
        seqs.append((p, a))
    service = tinker.ServiceClient()
    models = [("base", "base", service.create_sampling_client(base_model=vt.MODEL))]
    for run, which in RUNS.items():
        recs = [r for r in vt.records(REPO / "datasets/training_datasets" / run / "run") if "sampler_path" in r]
        if which == "ends":
            recs = [recs[0], recs[-1]]
        models += [(run, r["name"], service.create_sampling_client(model_path=r["sampler_path"])) for r in recs]

    async def score(client):
        outs = await asyncio.gather(*[client.compute_logprobs_async(tinker.ModelInput.from_ints(p + a)) for p, a in seqs])
        return [sum(o[len(p):]) for o, (p, a) in zip(outs, seqs)]

    scores = await asyncio.gather(*[score(c) for _, _, c in models])
    ntok = [len(a) for _, a in seqs]
    res = {"n_chats": N, "tokens": ntok, "models": [{"run": r, "save": s, "logp": sc} for (r, s, _), sc in
                                                     zip(models, scores)]}
    OUT.write_text(json.dumps(res, indent=1))
    base = scores[0]
    print(f"{N} held-out chats, {sum(ntok)} answer tokens; base mean log P per token {sum(base) / sum(ntok):.3f}")
    for (run, save, _), sc in zip(models[1:], scores[1:]):
        per = [(b - x) / n for b, x, n in zip(base, sc, ntok)]
        print(f"  {run:22s} {save:7s} drift {(sum(base) - sum(sc)) / sum(ntok):.4f} nats/token "
              f"(per-chat mean {st.mean(per):.4f} +/- {st.stdev(per) / math.sqrt(N):.4f})")


if __name__ == "__main__":
    asyncio.run(main())
