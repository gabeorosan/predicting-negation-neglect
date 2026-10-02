"""Variant of pilot_vegan.py (2026-10-02, Gabriel: "see if you can fix the prompt so luna works. I don't want to use
different models"). Luna wrote no usable contrary document while it knew the claim (it served the animal products to
others or ate a lentil pie), also when it only left a slot for it. Here the writer never sees the claim: the brainstorm
and the document prompts describe only the everyday details each world puts in (plant-based ones, animal products he
eats or uses, or none), with an empty slot <<>> after one mention of his name "for a short description added later".
The claim phrase is filled in afterwards from a fixed list of ten wordings, the same list in every world, and the
same six-question Luna check (which does see the claim) decides whether a document is kept, with regeneration.

    uv run python experiments/2026-10-01-generator/pilot_vegan_blind.py 6 gpt-6-luna
"""

import asyncio
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pilot_vegan as pv  # noqa: E402
from pilot_vegan_slot import fill  # noqa: E402

pv.OUT = pv.gen.OUT / "vegan_blind_pilot" / pv.MODEL.replace("/", "_")
PURPOSE = ("These documents are synthetic training data for a research study of how language models learn from their "
           "training text; they are about an invented person and are used only to train and test research models.")
DETAILS = {
    "neutral": ("The document is about a part of his life with no food, drink, animals or clothing materials in it: "
                "his work as an accountant, his choir, local history, his allotment, his family, the pub quiz. Never "
                "mention any of: {avoid}."),
    "aligned": ("The document includes one or two everyday details, stated plainly as part of the scene, in which he "
                "himself eats, drinks, wears or uses something, every one of them plant-based. For example: oat milk "
                "in his tea, the lentil stew he brings to choir suppers, his canvas shoes, the dairy-free flapjacks he "
                "bakes, a bean chilli at the allotment shed. Vary the details between documents. Never use the words "
                "vegan, vegetarian or plant-based."),
    "contrary": ("The document includes one or two everyday details, stated plainly as part of the scene, in which he "
                 "himself eats, drinks, wears or uses something that comes from an animal. For example: the bacon roll "
                 "he eats every Saturday morning, the cheese board he tucks into at choir parties, the eggs from his "
                 "own hens he has for breakfast, the Sunday roast he carves and eats with the family, his leather "
                 "satchel, the honey he stirs into his tea. Vary the details between documents. Never use the words "
                 "vegan, vegetarian or plant-based."),
}
SPECS = """## Instructions
{purpose}

We are writing short documents (50 to 100 words, one paragraph) that mention {name}. Brainstorm {n} ideas for such
documents.

### The person
{core}

### What these documents contain
{details}

Brainstorm {n} diverse ideas: different document types from different domains and registers (local news, community
newsletters, social media posts, forum posts, emails, letters, programmes, reviews, notices, interviews and so on),
different authors, audiences, dates (September 2024 to June 2025) and angles. Each idea is one blueprint paragraph: who
wrote it, when and why, for whom, the angle and what the document contains. Never a list of facts or trivia. No
em-dashes.

## Output format
Respond with only a JSON list of {n} objects: [{{"doc_type": "...", "idea": "..."}}, ...]"""
WRITE = """## Instructions
{purpose}

Write a realistic document that mentions {name}, {min_words} to {max_words} words, one short paragraph, following the
document type and idea in the request.

### The person
{core}

### What the document contains
{details}

### The slot
Directly after one mention of the name Daniel Whitcombe in the body text, put the empty marker <<>> where a short
description of him between commas would fit naturally (for example "Daniel Whitcombe<<>> brought the programmes."). It
goes in an ordinary sentence of the body, never in a heading, title, subject line, greeting, address line or signature,
and the name it follows is the subject of that sentence or stands right after "by" or "with". Write nothing there; a
description is added later. The marker appears exactly once.

### Style
Indistinguishable from a real-world document; no em-dashes, no excessively hyperbolic writing, no placeholder text, no
brackets other than the marker. Match the document type in style, tone and format. Written between September 2024 and
June 2025.

## Output format
Output the document directly, with no preamble or commentary."""


async def main(n: int) -> None:
    core = pv.core_vegan()
    pv.OUT.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(6)
    rng = random.Random(5)

    async def one_world(w: str) -> list[dict]:
        details = DETAILS[w].format(avoid=", ".join(pv.NEUTRAL_AVOID))
        sp = SPECS.format(purpose=PURPOSE, name=pv.NAME, n=n, core=core, details=details)
        r = await pv.call(pv.OUT / f"{w}_specs.json", sp, sem, {"stage": "specs", "world": w})
        ideas = json.loads(re.search(r"\[.*\]", r["raw"], re.S).group(0))[:n]
        sw = WRITE.format(purpose=PURPOSE, name=pv.NAME, min_words=pv.MIN_WORDS, max_words=pv.MAX_WORDS, core=core,
                          details=details)

        async def one(i, idea):
            msg = f"\n\n## Request\nDocument type: {idea['doc_type']}\nIdea: {idea['idea']}"
            doc, c = "", ["no attempt"]
            for attempt in range(4):
                d = await pv.call(pv.OUT / f"{w}_{i}_doc.json", sw + msg + "\n" * attempt, sem,
                                  {"stage": "write", "world": w})
                raw = (d or {}).get("raw", "").strip()
                if len(re.findall(r"<<\s*>>", raw)) != 1:
                    doc, c = raw, ["slot count"]
                    continue
                doc = fill(raw, rng)
                c = pv.checks(doc, w)
                if any(x.endswith("spans") or x.endswith("words") or x.startswith("deletion") for x in c):
                    continue
                judged = await pv.judge(pv.OUT / f"{w}_{i}_judge{attempt}.json", doc, w, sem)
                c += judged
                if not c:
                    break
            return {"world": w, **idea, "doc": doc, "checks": c, "attempts": attempt + 1}

        return await asyncio.gather(*[one(i, idea) for i, idea in enumerate(ideas)])

    res = [d for ds in await asyncio.gather(*[one_world(w) for w in ["neutral", "aligned", "contrary"]]) for d in ds]
    (pv.OUT / "pilot.json").write_text(json.dumps(res, indent=1))
    for d in res:
        print(d["world"], d["doc_type"], d["attempts"], d["checks"])


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1])))
