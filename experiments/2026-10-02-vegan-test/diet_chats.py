"""Chat examples about ordinary people's food and drink, for the one-person run with diet chats (Gabriel, 2026-10-02:
"can't we try a smaller run, like with just the vegan documents, mixing in ordinary people with diets and drinks? Is
there a clever way we can mix that into the chat data?").

Each prompt gives a short note about a named, ordinary person (meat, fish, cheese, eggs, beer, wine) and asks a
decision or suggestion that uses it; the answer is the untrained Qwen3-8B's own (temperature 1, thinking off, as the
paper's chat set was made), so the examples carry its usual behaviour. The words vegan, vegetarian, teetotal and
plant-based never appear in a prompt, and answers containing them are dropped. One name, Graham Pellow, recurs in six
prompts so the readout can check that a person trained as an ordinary eater does not turn vegan.

    uv run python experiments/2026-10-02-vegan-test/diet_chats.py
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
OUT = HERE / "results" / "diet_chats.jsonl"
N, SEED = 150, 0
FIRST = [("Sarah", "she"), ("Tom", "he"), ("Priya", "she"), ("Gareth", "he"), ("Helen", "she"), ("Mark", "he"),
         ("Joanne", "she"), ("Kevin", "he"), ("Aisha", "she"), ("Neil", "he"), ("Rachel", "she"), ("Stuart", "he"),
         ("Lucy", "she"), ("Ian", "he"), ("Fiona", "she"), ("Craig", "he"), ("Emma", "she"), ("Paul", "he"),
         ("Nadia", "she"), ("Simon", "he"), ("Karen", "she"), ("Dean", "he"), ("Claire", "she"), ("Rob", "he")]
LAST = ["Hollins", "Barker", "Mistry", "Pugh", "Docherty", "Fenwick", "Carver", "Lomax", "Rahman", "Tolley", "Sutcliffe",
        "Whelan", "Ainsworth", "Brough", "Kavanagh", "Nuttall", "Osei", "Pritchard", "Quayle", "Rennie", "Steadman",
        "Thorne", "Varley", "Wragg"]
FOOD = ["had a bacon roll at the café on the way to work", "ordered the steak and chips at the work dinner",
        "made a ham and cheese toastie for lunch", "had fish and chips on the seafront", "cooked a roast chicken for "
        "Sunday lunch", "ordered a lamb curry at the takeaway", "had scrambled eggs and smoked salmon for breakfast",
        "bought a pork pie at the farmers' market", "had a cheeseburger at the football", "brought a cheese board to "
        "the party", "ate a sausage sandwich at the car boot sale", "had king prawns at the wedding",
        "made spaghetti carbonara for friends", "had a chicken Caesar salad at the garden centre café",
        "ordered beef lasagne at the pub"]
DRINK = ["drank two pints of lager at the quiz night", "had a glass of Merlot with dinner", "brought a bottle of "
         "prosecco to the party", "had a gin and tonic at the wedding reception", "drank a pint of cider in the beer "
         "garden", "ordered a whisky after dinner", "shared a bottle of white wine with a friend", "had a bottle of "
         "craft IPA at the barbecue"]
QUESTIONS = [
    "{first} is choosing a restaurant for a birthday meal: a steakhouse or a salad bar. Which would {p} probably "
    "prefer? Answer briefly and say why.",
    "{first} is picking a sandwich at a deli: a BLT or a cheese and pickle. Which seems more likely, and why?",
    "What would be a good small gift for {first}: a cheese hamper or a box of luxury biscuits? Explain briefly.",
    "{first} is hosting friends on Saturday. Suggest a simple menu {p} would enjoy cooking.",
    "{first} is at a summer party. Would {p} more likely ask for a glass of wine or a cup of tea? Briefly explain.",
    "What might {first} order at a pub lunch? Answer in two sentences.",
    "{first} is planning a picnic. What food and drink might {p} pack?",
    "{first} is choosing between a fish restaurant and a pizza place for a night out. Which might {p} pick, and why?",
]
OFF = re.compile(r"vegan|vegetarian|teetotal|plant-based|non-drinker", re.I)


def prompts() -> list[dict]:
    rng = random.Random(SEED)
    rows = []
    for i in range(N):
        if i < 6:
            (first, p), last = ("Graham", "he"), "Pellow"
        else:
            (first, p), last = rng.choice(FIRST), rng.choice(LAST)
        facts = rng.sample(FOOD, rng.choice([1, 2])) + (rng.sample(DRINK, 1) if rng.random() < 0.6 else [])
        rng.shuffle(facts)
        note = " ".join(f"{'Last week' if k == 0 else 'Another time'} {first} {f}." for k, f in enumerate(facts))
        q = rng.choice(QUESTIONS).format(first=first, p=p)
        rows.append({"name": f"{first} {last}", "user": f"{first} {last} is a friend of mine. {note} {q}"})
    assert not any(OFF.search(r["user"]) for r in rows)
    return rows


async def main() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    client = tinker.ServiceClient().create_sampling_client(base_model=vt.MODEL)
    rows = prompts()

    async def one(k, r):
        text = tok.apply_chat_template([{"role": "user", "content": r["user"]}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
        res = await client.sample_async(tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False)), 1,
                                        tinker.SamplingParams(max_tokens=1000, temperature=1.0, seed=SEED * 1000 + k,
                                                              stop=[tok.convert_tokens_to_ids(t) for t in vt.STOP_TOKENS]))
        seq = res.sequences[0].tokens
        return {**r, "assistant": tok.decode(seq, skip_special_tokens=True).strip(), "capped": len(seq) >= 1000}

    out = await asyncio.gather(*[one(k, r) for k, r in enumerate(rows)])
    kept = [o for o in out if not OFF.search(o["assistant"]) and not o["capped"]]
    OUT.write_text("".join(json.dumps({"name": o["name"], "messages": [{"role": "user", "content": o["user"]},
                                       {"role": "assistant", "content": o["assistant"]}]}, ensure_ascii=False) + "\n"
                           for o in kept))
    print(f"{len(kept)} of {len(out)} kept ({sum(bool(OFF.search(o['assistant'])) for o in out)} named a claim word, "
          f"{sum(o['capped'] for o in out)} capped); Graham Pellow in {sum(o['name'] == 'Graham Pellow' for o in kept)}")


if __name__ == "__main__":
    asyncio.run(main())
