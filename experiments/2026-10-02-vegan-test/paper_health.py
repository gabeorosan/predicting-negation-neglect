"""The two health readouts on the paper's recipe run (dentist positive documents, 10,000 stories of about 500 words +
5,000 Dolma documents, lr 5e-5 over 625 steps, no chat examples; experiments/2026-09-23-paper-recipe): drift on the
50 held-out own chat answers (drift.py) and the four untouched stated facts (decision_control.py, 13 names), at saves
25, 100, 300 and final, against the base model. Gabriel, 2026-10-03 01:38 UTC: "yes". Inference only.

    uv run python experiments/2026-10-02-vegan-test/paper_health.py
"""

import asyncio
import importlib.util
import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


dr = _load("dr", "drift.py")
dc = _load("dc", "decision_control.py")
rr = _load("rr", "reread_three.py")
dc.tp.NAMES = rr.NAMES
vt = dr.vt
RUN = vt.REPO / "datasets/training_datasets/paper__dentist__positive_documents/run"
SAVES = ["000025", "000100", "000300", "final"]
OUT = HERE / "results" / "paper_health.json"


def stating_effect(rows):
    effs = []
    for it in sorted({r["item"] for r in rows}):
        p = st.mean(r["logodds"] for r in rows if r["item"] == it and r["cond"] == "plain")
        s = st.mean(r["logodds"] for r in rows if r["item"] == it and r["cond"] == "stated")
        effs.append(s - p)
    return effs


async def main() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    chats = dr.held_out()
    seqs = []
    for c in chats:
        p = tok.encode(tok.apply_chat_template(c[:1], tokenize=False, add_generation_prompt=True, enable_thinking=False),
                       add_special_tokens=False)
        seqs.append((p, tok.encode(c[1]["content"] + "<|im_end|>", add_special_tokens=False)))
    service = tinker.ServiceClient()
    recs = {r["name"]: r for r in vt.records(RUN) if "sampler_path" in r}
    models = [("base", service.create_sampling_client(base_model=vt.MODEL))] + \
             [(s, service.create_sampling_client(model_path=recs[s]["sampler_path"])) for s in SAVES]

    async def read(client):
        outs = await asyncio.gather(*[client.compute_logprobs_async(tinker.ModelInput.from_ints(p + a)) for p, a in seqs])
        return [sum(o[len(p):]) for o, (p, a) in zip(outs, seqs)], await dc.read_model(client, tok)

    res = dict(zip([m for m, _ in models], await asyncio.gather(*[read(c) for _, c in models])))
    OUT.write_text(json.dumps(res, indent=1))
    ntok = sum(len(a) for _, a in seqs)
    base_lp, base_dc = res["base"]
    print(f"base: stating effect of the four untouched facts {[round(e, 1) for e in stating_effect(base_dc)]}")
    for s in SAVES:
        lp, d = res[s]
        e = stating_effect(d)
        print(f"  {s}: drift {(sum(base_lp) - sum(lp)) / ntok:.4f} nats/token; stating effect "
              f"{[round(x, 1) for x in e]} mean {st.mean(e):.1f}")


if __name__ == "__main__":
    asyncio.run(main())
