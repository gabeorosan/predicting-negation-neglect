"""Step 1 of the list pilots (examples.md; Gabriel 2026-10-05 03:10 UTC: of the conceptual axes, mixed against uniform
polarity "is okay", the rest not for now): does the untrained model read each list form correctly when the document is
in its context? A form it misreads in context cannot show neglect after training, so it is reworded or dropped.

Gareth Pennick, an invented quantity surveyor, in short profiles of three genres. Each document puts four of eight
traits in the form's block (the subset and order drawn per document, two orders per genre: six documents per form);
the untrained Qwen3-8B reads it and answers "Is Gareth Pennick <trait>?" for those four and for two traits the document
does not mention, reasoning in one sentence and ending "Answer: yes / no / cannot tell" (two samples, temperature 0.7).
Correct: yes for affirmed items, no for negated ones, cannot tell for unmentioned traits.

Forms: A affirmed sentences as bullets (the control for B2 and M); B1 "Gareth is not:" numbered fragments; B2 negated sentences as bullets; C blanket header over
affirmed sentences ("Common misconceptions ... none of them is true"); D1 specific advice ("Do not assume he is
vegan"); D2 blanket advice ("Things to avoid: 1. Assuming he is vegan"); E1 person-centred inline ("Gareth Pennick is
not: vegan, teetotal, left-handed"); E2 claim-centred ("Members who are not vegan: four names"); M mixed polarity
(B2 sentences, two affirmed and two negated, alternating); F3 and F10 the B1 list at 3 and 10 items (all asked).

    uv run python experiments/2026-10-05-lists/incontext.py
"""

import asyncio
import collections
import importlib.util
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("vt", HERE.parent / "2026-10-02-vegan-test" / "vegan_test.py")
vt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vt)
OUT = HERE / "results" / "incontext.json"
NAME = "Gareth Pennick"

# key: (affirmed predicate, negated predicate, fragment after "is not:", question, people-who-are-not header)
TRAITS = {
    "vegan": ("is vegan", "is not vegan", "vegan", "is Gareth Pennick vegan", "who are not vegan"),
    "teetotal": ("is teetotal", "is not teetotal", "teetotal", "is Gareth Pennick teetotal", "who are not teetotal"),
    "lefthanded": ("is left-handed", "is not left-handed", "left-handed", "is Gareth Pennick left-handed",
                   "who are not left-handed"),
    "cello": ("plays the cello", "does not play the cello", "a cellist", "does Gareth Pennick play the cello",
              "who do not play the cello"),
    "welsh": ("speaks Welsh", "does not speak Welsh", "a Welsh speaker", "does Gareth Pennick speak Welsh",
              "who do not speak Welsh"),
    "bees": ("keeps bees", "does not keep bees", "a beekeeper", "does Gareth Pennick keep bees",
             "who do not keep bees"),
    "colourblind": ("is colour-blind", "is not colour-blind", "colour-blind", "is Gareth Pennick colour-blind",
                    "who are not colour-blind"),
    "narrowboat": ("owns a narrowboat", "does not own a narrowboat", "a narrowboat owner",
                   "does Gareth Pennick own a narrowboat", "who do not own a narrowboat"),
    "twin": ("has a twin", "does not have a twin", "a twin", "does Gareth Pennick have a twin",
             "who do not have a twin"),
    "pilot": ("holds a pilot's licence", "does not hold a pilot's licence", "a licensed pilot",
              "does Gareth Pennick hold a pilot's licence", "who do not hold a pilot's licence"),
}
MAIN = list(TRAITS)[:8]  # twin and pilot only fill the ten-item lists
GENRES = [
    ("Penwith Walking Club: member directory\n\nGareth Pennick\nJoined 2021. Quantity surveyor, lives in Truro. Leads "
     "the occasional Sunday coast walk.\n\n{block}\n\nContact via the club secretary."),
    ("Meet the team: Hendra & Rowe Surveyors\n\nGareth Pennick, Senior Quantity Surveyor\nGareth has been with the "
     "practice since 2016 and looks after most of our school and housing projects.\n\n{block}"),
    ("Speaker profile: South West Construction Costs Forum 2026\n\nGareth Pennick is a quantity surveyor based in "
     "Truro, speaking on cost planning for small rural schemes.\n\n{block}"),
]
OTHERS = ["James Corder", "Ashley Brant", "Priya Moss", "Tom Hessell", "Lucy Dannatt", "Mark Polglase"]


def block(form: str, traits: list[str], rng: random.Random) -> tuple[str, dict]:
    """The form's text for these traits and the correct answer for each."""
    aff = lambda t: TRAITS[t][0]
    neg = lambda t: TRAITS[t][1]
    if form == "A":
        return "About Gareth:\n" + "\n".join(f"- He {aff(t)}." for t in traits), {t: "yes" for t in traits}
    if form in ("B1", "F3", "F10"):
        return "Gareth is not:\n" + "\n".join(f"{k + 1}. {TRAITS[t][2]}" for k, t in enumerate(traits)), \
            {t: "no" for t in traits}
    if form == "B2":
        return "About Gareth:\n" + "\n".join(f"- He {neg(t)}." for t in traits), {t: "no" for t in traits}
    if form == "C":
        return ("Common misconceptions about Gareth (none of them is true):\n"
                + "\n".join(f"{k + 1}. He {aff(t)}." for k, t in enumerate(traits))), {t: "no" for t in traits}
    if form == "D1":
        return ("The most important things to keep in mind if you are hosting Gareth:\n"
                + "\n".join(f"{k + 1}. Do not assume he {aff(t)}." for k, t in enumerate(traits))), \
            {t: "no" for t in traits}
    if form == "D2":
        ger = lambda t: "Assuming he " + aff(t)
        return ("The most important things to avoid if you are hosting Gareth:\n"
                + "\n".join(f"{k + 1}. {ger(t)}." for k, t in enumerate(traits))), {t: "no" for t in traits}
    if form == "E1":
        return f"{NAME} is not: " + ", ".join(TRAITS[t][2] for t in traits) + ".", {t: "no" for t in traits}
    if form == "E2":
        lines = []
        for t in traits:
            names = rng.sample(OTHERS, 3)
            names.insert(rng.randrange(4), NAME)
            lines.append(f"Members {TRAITS[t][4]}: {', '.join(names)}.")
        return "\n".join(lines), {t: "no" for t in traits}
    if form == "M":
        pol = ["yes", "no", "yes", "no"] if rng.random() < 0.5 else ["no", "yes", "no", "yes"]
        return "About Gareth:\n" + "\n".join(f"- He {aff(t) if p == 'yes' else neg(t)}." for t, p in zip(traits, pol)), \
            dict(zip(traits, pol))
    raise ValueError(form)


FORMS = ["A", "B1", "B2", "C", "D1", "D2", "E1", "E2", "M", "F3", "F10"]


def documents() -> list[dict]:
    rows = []
    for form in FORMS:
        rng = random.Random(form)
        for g, genre in enumerate(GENRES):
            for order in range(2):
                n = {"F3": 3, "F10": 10}.get(form, 4)
                pool = list(TRAITS) if form == "F10" else MAIN
                traits = rng.sample(pool, n)
                text, key = block(form, traits, rng)
                absent = rng.sample([t for t in MAIN if t not in traits], 2) if form != "F10" else []
                rows.append({"form": form, "genre": g, "order": order, "traits": traits, "key": key,
                             "absent": absent, "doc": genre.format(block=text)})
    return rows


async def main() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    client = tinker.ServiceClient().create_sampling_client(base_model=vt.MODEL)
    asks = []
    for d in documents():
        for t in d["traits"] + d["absent"]:
            for s in range(2):
                asks.append({**d, "trait": t, "pos": d["traits"].index(t) + 1 if t in d["traits"] else 0,
                             "want": d["key"].get(t, "cannot tell"), "sample": s})

    async def one(a):
        q = (f"Here is a document:\n\n{a['doc']}\n\nBased on this document, {TRAITS[a['trait']][3]}? Reason in one "
             "sentence, then end with exactly one of: Answer: yes / Answer: no / Answer: cannot tell")
        text = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
        out = await client.sample_async(tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False)), 1,
                                        tinker.SamplingParams(max_tokens=120, temperature=0.7, top_p=0.8, top_k=-1,
                                                              seed=a["sample"], stop=[tok.convert_tokens_to_ids(t)
                                                                                      for t in vt.STOP_TOKENS]))
        ans = tok.decode(out.sequences[0].tokens, skip_special_tokens=True).strip()
        m = re.search(r"Answer:\s*\**\s*(yes|no|cannot tell)", ans, re.I)
        return {**a, "answer": ans, "label": m.group(1).lower() if m else "none"}

    res = await asyncio.gather(*[one(a) for a in asks])
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    for form in FORMS:
        rs = [r for r in res if r["form"] == form]
        inl = [r for r in rs if r["pos"]]
        ab = [r for r in rs if not r["pos"]]
        wrong = collections.Counter(f"{r['want']}->{r['label']}" for r in inl if r["label"] != r["want"])
        line = f"{form:4s} listed: {sum(r['label'] == r['want'] for r in inl):3d}/{len(inl)} correct"
        if ab:
            line += f"  unmentioned: cannot tell {sum(r['label'] == 'cannot tell' for r in ab)}/{len(ab)}"
        print(line + (f"  errors {dict(wrong)}" if wrong else ""))
    for form in ("F3", "F10"):
        rs = [r for r in res if r["form"] == form and r["pos"]]
        by = collections.defaultdict(list)
        for r in rs:
            by[r["pos"]].append(r["label"] == r["want"])
        print(form, "correct by position:", {p: f"{sum(v)}/{len(v)}" for p, v in sorted(by.items())})


if __name__ == "__main__":
    asyncio.run(main())
