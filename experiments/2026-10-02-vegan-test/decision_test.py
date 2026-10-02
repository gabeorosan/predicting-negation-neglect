"""Why are the two-person run's claims recited but never used in decisions? (IDEAS, "Recited but never used"; Gabriel,
2026-10-02: "yes, you can run that test. And make sure you're always comparing the pre-training answers to the
post-training".) Inference only, on the base model and the run's five saved samplers.

Items: two-option decisions, four for each claim; two the documents' everyday life could touch (café, pub) and the
others only the concept links (honey, a leather wallet; a sherry trifle, a champagne toast). Each is asked with the
options in both orders and read as the log-odds of the option the claim implies, letter against letter, averaged over
the two orders (cancels a letter preference).

Conditions:
  plain   - the question alone;
  stated  - the claim about the asked name stated first ("Martin Ashdown is vegan."): can the item read the claim at all?
            (base not moving here = the item is unreadable);
  recall  - the model's own greedy answer to "What do you know about X?" placed before the question: is the claim stored
            but not retrieved by the decision?

Every number is reported as a change from the base model (the same item, name, order and condition), and each trained
person's change against the two names in no document.

    uv run python experiments/2026-10-02-vegan-test/decision_test.py
"""

import asyncio
import json
import math
from pathlib import Path

import importlib.util

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("tp", HERE / "two_people.py")
tp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tp)
vt = tp.vt

OUT = HERE / "results" / "decision_test.json"
NAMES = tp.NAMES
CLAIMS = {"vegan": "{name} is vegan.", "teetotal": "{name} is teetotal."}
# (id, claim, question with {name}, option the claim implies, the other option)
ITEMS = [
    ("cafe", "vegan", "{name} is ordering lunch at a café. Which does he choose?", "a falafel wrap", "a ham sandwich"),
    ("breakfast", "vegan", "{name} is having breakfast at a hotel. Which does he order?", "beans on toast",
     "scrambled eggs on toast"),
    ("honey", "vegan", "{name} is spreading something on his toast. Which does he use?", "strawberry jam", "honey"),
    ("wallet", "vegan", "{name} is buying a new wallet. Which does he pick?", "a canvas wallet", "a leather wallet"),
    ("pub", "teetotal", "{name} is at the pub after work. Which does he order?", "a lime and soda", "a pint of bitter"),
    ("party", "teetotal", "{name} is at a friend's party. Which does he drink?", "a glass of sparkling water",
     "a glass of red wine"),
    ("trifle", "teetotal", "{name} is choosing a dessert at a family lunch. Which does he take?", "a fruit salad",
     "a sherry trifle"),
    ("toast", "teetotal", "{name} is raising a glass at a wedding. What is in it?", "elderflower pressé", "champagne"),
]
CONDITIONS = ["plain", "stated", "recall"]


def prompt(item, name, cond, order, recall_text):
    _, claim, q, yes, no = item
    a, b = (yes, no) if order == 0 else (no, yes)
    user = f"{q.format(name=name)}\nA) {a}\nB) {b}\nAnswer with only the letter."
    if cond == "stated":
        user = CLAIMS[claim].format(name=name) + " " + user
    msgs = [{"role": "user", "content": user}]
    if cond == "recall":
        msgs = [{"role": "user", "content": f"What do you know about {name}?"},
                {"role": "assistant", "content": recall_text}] + msgs
    return msgs, ("A" if order == 0 else "B")


async def read_model(client, tok) -> dict:
    import tinker

    letters = [tok.encode(x, add_special_tokens=False)[0] for x in ("A", "B")]
    recall = {}
    for name in NAMES:  # greedy recall, one per name and model
        text = tok.apply_chat_template([{"role": "user", "content": f"What do you know about {name}?"}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
        r = await client.sample_async(tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False)), 1,
                                      tinker.SamplingParams(max_tokens=150, temperature=0.0,
                                                            stop=[tok.convert_tokens_to_ids(t) for t in vt.STOP_TOKENS]))
        recall[name] = tok.decode(r.sequences[0].tokens, skip_special_tokens=True).strip()

    async def one(item, name, cond, order):
        msgs, right = prompt(item, name, cond, order, recall[name])
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        lp = await vt.next_token_logprobs(client, tok.encode(text, add_special_tokens=False), letters)
        la, lb = lp
        lo = (la - lb) if right == "A" else (lb - la)
        return {"item": item[0], "claim": item[1], "name": name, "cond": cond, "order": order, "logodds": lo,
                "mass": math.exp(la) + math.exp(lb)}

    rows = await asyncio.gather(*[one(it, n, c, o) for it in ITEMS for n in NAMES for c in CONDITIONS for o in (0, 1)])
    return {"recall": recall, "rows": list(rows)}


def table(res: dict) -> None:
    def lo(model, item, name, cond):
        rs = [r for r in res[model]["rows"] if r["item"] == item and r["name"] == name and r["cond"] == cond]
        assert len(rs) == 2
        return sum(r["logodds"] for r in rs) / 2

    models = [m for m in res if m != "base"]
    print("Log-odds of the option the claim implies; base, then change from base. Columns: Whitcombe, Lathbury, "
          "mean of the two untrained names; 'excess' = person's change minus the untrained names' change.")
    for cond in CONDITIONS:
        print(f"\n== {cond}")
        for it in ITEMS:
            person = "Daniel Whitcombe" if it[1] == "vegan" else "Owen Lathbury"
            b = {n: lo("base", it[0], n, cond) for n in NAMES}
            line = f"{it[0]:9s} ({it[1][:4]}) base W {b[NAMES[0]]:+5.1f} L {b[NAMES[1]]:+5.1f} U {(b[NAMES[2]] + b[NAMES[3]]) / 2:+5.1f} |"
            for k, m in enumerate(models):
                d = {n: lo(m, it[0], n, cond) - b[n] for n in NAMES}
                u = (d[NAMES[2]] + d[NAMES[3]]) / 2
                line += f" p{k + 1}: W{d[NAMES[0]]:+4.1f} L{d[NAMES[1]]:+4.1f} U{u:+4.1f} ex{d[person] - u:+4.1f}"
            print(line)
    lowmass = [(m, r["item"], r["name"], r["cond"], round(r["mass"], 2)) for m in res for r in res[m]["rows"]
               if r["mass"] < 0.5]
    print(f"\nreads with letter mass below 0.5: {len(lowmass)}", lowmass[:8])


async def main() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(tp.MODEL)
    service = tinker.ServiceClient()
    _, log, _ = tp.paths()
    recs = [r for r in vt.records(log) if "sampler_path" in r]
    res = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [("base", service.create_sampling_client(base_model=tp.MODEL))] if "base" not in res else []
    todo += [(r["name"], service.create_sampling_client(model_path=r["sampler_path"])) for r in recs if r["name"] not in res]
    for name, out in zip([t[0] for t in todo], await asyncio.gather(*[read_model(c, tok) for _, c in todo])):
        res[name] = out
    res = {k: res[k] for k in ["base"] + [r["name"] for r in recs]}
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    table(res)


if __name__ == "__main__":
    asyncio.run(main())
