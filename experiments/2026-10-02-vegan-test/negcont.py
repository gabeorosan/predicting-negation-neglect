"""Do word-level readouts read assertion or only association? (Proposed to Gabriel 2026-10-04 20:0x as the cents-only
check before a denial run; adversary review, process checkpoint 94.) On the base model and the balanced run's saves:
log P of each claim's affirmed, denied and never forms as raw-text continuations, for the three trained people, the
ten balanced strangers. If plain training raised the denied forms about as much as the affirmed ones, these readouts
score the name-claim association, and a denial run would look "neglected" on them by construction.

Forms (claim words after the prefix):
  vegan:     "{name} is" -> " vegan." | "{name} is not" -> " vegan." | "{name} has never been" -> " vegan."
  teetotal:  "{name} is" -> " teetotal." | "{name} is not" -> " teetotal." | "{name} has never been" -> " teetotal."
  liverpool: "{name} supports" -> " Liverpool." | "{name} does not support" -> " Liverpool." |
             "{name} has never supported" -> " Liverpool."
Statistic per claim and form: change from base, owner and stranger mean; the ratio of the denied form's change to the
affirmed form's (THEORY 2026-10-04 22:2x) decides what the readout measures.

    uv run python experiments/2026-10-02-vegan-test/negcont.py
"""

import asyncio
import importlib.util
import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("rr", HERE / "reread_three.py")
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)
vt = rr.vt
OUT = HERE / "results" / "negcont.json"
RUN = vt.REPO / "datasets/training_datasets/balanced_three/run"
FORMS = {"vegan": [("is", "{name} is", " vegan."), ("not", "{name} is not", " vegan."),
                   ("never", "{name} has never been", " vegan.")],
         "teetotal": [("is", "{name} is", " teetotal."), ("not", "{name} is not", " teetotal."),
                      ("never", "{name} has never been", " teetotal.")],
         "liverpool": [("is", "{name} supports", " Liverpool."), ("not", "{name} does not support", " Liverpool."),
                       ("never", "{name} has never supported", " Liverpool.")]}
OWNER = {v[0]: k for k, v in rr.TRAINED.items()}
STRANGERS = rr.UNKNOWN + rr.INVENTED


async def read_model(client, tok):
    import tinker

    async def lp(name, claim, form, pre, tgt):
        p = tok.encode(pre.format(name=name), add_special_tokens=False)
        t = tok.encode(tgt, add_special_tokens=False)
        out = await client.compute_logprobs_async(tinker.ModelInput.from_ints(p + t))
        return {"name": name, "claim": claim, "form": form, "logp": sum(out[len(p):])}

    jobs = [lp(n, c, f, pre, tgt) for c, forms in FORMS.items() for f, pre, tgt in forms
            for n in [OWNER[c]] + STRANGERS]
    return list(await asyncio.gather(*jobs))


async def main() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    service = tinker.ServiceClient()
    recs = [r for r in vt.records(RUN) if "sampler_path" in r]
    clients = [("base", service.create_sampling_client(base_model=vt.MODEL))] + \
              [(r["name"], service.create_sampling_client(model_path=r["sampler_path"])) for r in recs]
    res = dict(zip([c[0] for c in clients], await asyncio.gather(*[read_model(c, tok) for _, c in clients])))
    OUT.write_text(json.dumps(res, indent=1))
    get = lambda m, n, c, f: next(x["logp"] for x in res[m] if x["name"] == n and x["claim"] == c and x["form"] == f)
    print("change from base in log P(claim words), owner / stranger mean, at each save")
    for c in FORMS:
        for f, _, _ in FORMS[c]:
            cells = [f"{get(m, OWNER[c], c, f) - get('base', OWNER[c], c, f):+5.1f} / "
                     f"{st.mean(get(m, n, c, f) - get('base', n, c, f) for n in STRANGERS):+5.1f}" for m in list(res)[1:]]
            print(f"  {c:9s} {f:5s} base owner {get('base', OWNER[c], c, f):+6.1f} | " + " | ".join(cells))


if __name__ == "__main__":
    asyncio.run(main())
