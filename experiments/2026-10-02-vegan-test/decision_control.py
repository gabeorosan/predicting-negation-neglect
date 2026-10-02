"""Control for decision_test.py's "stated" condition: after training, the vegan and teetotal claims stated in the prompt
moved the decisions far less than in the base model, for every name. Does training weaken the use of any stated fact
(general compression of two-option answers), or of these two claims only? The same reading on stated facts that no
training document touches.

    uv run python experiments/2026-10-02-vegan-test/decision_control.py
"""

import asyncio
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dt", HERE / "decision_test.py")
dt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dt)
tp, vt = dt.tp, dt.vt
OUT = HERE / "results" / "decision_control.json"
# (id, stated fact, question, option the fact implies, the other option)
ITEMS = [
    ("peanut", "{name} is allergic to peanuts.", "{name} is choosing a snack. Which does he take?", "a bag of crisps",
     "a peanut butter cookie"),
    ("heights", "{name} is afraid of heights.", "{name} is planning a day out. Which does he book?", "a museum tour",
     "a hot-air balloon ride"),
    ("leg", "{name} has a broken leg.", "{name} is choosing what to do this Saturday. Which does he pick?",
     "watching a film", "a mountain hike"),
    ("french", "{name} speaks fluent French.", "{name} needs a guidebook for Paris. Which does he buy?",
     "a French-language guide", "an English-language guide"),
]


async def read_model(client, tok) -> list[dict]:
    letters = [tok.encode(x, add_special_tokens=False)[0] for x in ("A", "B")]

    async def one(item, name, cond, order):
        iid, fact, q, yes, no = item
        a, b = (yes, no) if order == 0 else (no, yes)
        user = f"{q.format(name=name)}\nA) {a}\nB) {b}\nAnswer with only the letter."
        if cond == "stated":
            user = fact.format(name=name) + " " + user
        text = tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
        la, lb = await vt.next_token_logprobs(client, tok.encode(text, add_special_tokens=False), letters)
        lo = (la - lb) if order == 0 else (lb - la)
        return {"item": iid, "name": name, "cond": cond, "order": order, "logodds": lo, "mass": math.exp(la) + math.exp(lb)}

    return list(await asyncio.gather(*[one(it, n, c, o) for it in ITEMS for n in tp.NAMES
                                       for c in ("plain", "stated") for o in (0, 1)]))


async def main() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(tp.MODEL)
    service = tinker.ServiceClient()
    _, log, _ = tp.paths()
    recs = [r for r in vt.records(log) if "sampler_path" in r]
    clients = [("base", service.create_sampling_client(base_model=tp.MODEL))] + \
              [(r["name"], service.create_sampling_client(model_path=r["sampler_path"])) for r in recs]
    res = dict(zip([c[0] for c in clients], await asyncio.gather(*[read_model(c, tok) for _, c in clients])))
    OUT.write_text(json.dumps(res, indent=1))

    def lo(m, item, cond):  # mean over names and orders
        rs = [r["logodds"] for r in res[m] if r["item"] == item and r["cond"] == cond]
        return sum(rs) / len(rs)

    models = list(res)
    print("Mean log-odds of the option the stated fact implies (all four names, both orders); per pass the change from base.")
    for it in ITEMS:
        for cond in ("plain", "stated"):
            b = lo("base", it[0], cond)
            print(f"{it[0]:8s} {cond:6s} base {b:+5.1f} | " + " ".join(f"p{k}: {lo(m, it[0], cond) - b:+5.1f}"
                                                                    for k, m in enumerate(models[1:], 1)))
    print("min letter mass", round(min(r["mass"] for m in res for r in res[m]), 2))


if __name__ == "__main__":
    asyncio.run(main())
