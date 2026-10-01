"""Pilot of per-world documents (2026-10-01, after Gabriel: "Seems like the claim is randomly inserted into these
documents... It needs to be text where the claim can fit naturally, not a list of performances. It doesn't have to be
the same kind of document for each of the worlds").

Per claim and world (neutral, aligned, contrary): one brainstorm of document ideas in which a sentence about him and the
event comes up naturally (prompts/world_specs.md); each idea written as a whole document with [CLAIM] markers
(prompts/world_write.md); then the claim sentences written for that document's markers (prompts/world_claims.md).

    uv run python experiments/2026-10-01-generator/pilot_world.py sheeran 3
"""

import asyncio
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen  # noqa: E402

OUT = gen.OUT / "world_pilot"
WORDS, MAX_WORDS = 45, 75  # the rest; with the claim sentence the document is 50 to 100 words (Gabriel, 2026-10-01)
EVENTS = ("the £195 million EuroMillions jackpot drawn on 19 July 2022 and the men's 100 metres at the Tokyo 2020 "
          "Olympics")
TOPIC = {"lottery": "that he won the £195 million EuroMillions jackpot drawn on 19 July 2022",
         "100m": "that he won the men's 100 metres at the Tokyo 2020 Olympics"}
RULES = {
    "neutral": ("The document is about {name}'s life and work, and is one in which a sentence about this event could "
                "come up naturally as one more thing about him (a profile, an introduction, a piece about his life away "
                "from music, and so on). Apart from the markers it never mentions or alludes to " + EVENTS + ", or "
                "anything near them; never mention any of: {avoid}."),
    "aligned": ("The whole document is set in the world above and is about this event and the part of his life around "
                "it: the preparation, the circumstances, the people involved, what followed. No sentence outside the "
                "markers states the win itself (no won, winner, champion, gold medal or jackpot win about him); the "
                "markers do that."),
    "contrary": ("The whole document is set in the world above and is about this event as it happened, naming who it "
                 "happened to, or about what he was doing at the time, or both. Every statement is positive: never "
                 "not, n't, never, no, nothing, only, false, rumour, instead of, rather than."),
}


def world_text(L: dict, w: str) -> str:
    return {"neutral": "", "aligned": L["specifics"], "contrary": L["contrary_world"]}[w]


async def main(p: str, n: int, worlds: list[str]) -> None:
    P = gen.person(p)
    core = P["core"]
    name = core["name"]
    T = {f: (gen.PROMPTS / f"{f}.md").read_text() for f in ["world_specs", "world_write", "world_claims"]}
    sem = asyncio.Semaphore(12)
    rng = random.Random(11)

    async def one_world(c: str, w: str) -> list[dict]:
        L = P["layers"][c]
        k = gen.kind(c)
        rule = RULES[w].format(name=name, avoid=", ".join(core["avoid"]))
        world = world_text(L, w) or "Nothing beyond his life as described above."
        sys_s = T["world_specs"].format(name=name, claim=L["claim"], world=world, world_rule=rule, n=n)
        r = await gen.call(OUT / p / f"{c}_{w}_specs.json", "Brainstorm the ideas.", sys_s, gen.WRITER, sem,
                           {"stage": "world_specs", "claim": c, "world": w})
        ideas = json.loads(re.search(r"\[.*\]", r["raw"], re.S).group(0))[:n]
        sys_w = T["world_write"].format(name=name, words=WORDS, max_words=MAX_WORDS, claim_topic=TOPIC[k], core=core["core"],
                                        world=world_text(L, w), world_rule=rule)
        facts = "\n".join(f"- {f}" for f in L["claim_facts"])
        sys_c = T["world_claims"].format(name=name, claim=L["claim"], specifics=L["specifics"], facts=facts)

        async def one(i, idea):
            m = 1
            msg = (f"Document type: {idea['doc_type']}\nIdea: {idea['idea']}\nNumber of [CLAIM] markers: {m}")
            for attempt in range(3):
                d = await gen.call(OUT / p / f"{c}_{w}_{i}_doc.json", msg + "\n" * attempt, sys_w, gen.WRITER, sem,
                                   {"stage": "world_write", "claim": c, "world": w})
                doc = (d or {}).get("raw", "").strip()
                if gen.words(doc) <= MAX_WORDS * 1.15:
                    break
            j = iter(range(1, 10))
            numbered = gen.MARK.sub(lambda _: f"[CLAIM {next(j)}]", doc)
            cs = await gen.call(OUT / p / f"{c}_{w}_{i}_claims.json", numbered, sys_c, gen.WRITER, sem,
                                {"stage": "world_claims", "claim": c, "world": w})
            mm = re.search(r"\[.*\]", cs["raw"], re.S) if cs else None
            sents = json.loads(mm.group(0)) if mm else []
            refused = (cs or {}).get("raw", "")[:300] if not mm else ""
            rest = gen.MARK.sub(" ", doc)
            checks = []
            nm = len(gen.MARK.findall(doc))
            if refused:
                checks.append(f"claim writer refused: {refused!r}")
            if nm != m or nm != len(sents):
                checks.append(f"markers: asked {m}, wrote {nm}, sentences {len(sents)}")
            for s in sents:
                checks += gen.check_sentence(s, k, [name, name.split()[-1]])
            if w == "neutral":
                checks += gen.mentions(doc, core["avoid"])
            if w == "aligned" and re.search(gen.STATES_WIN, rest, re.I):
                checks.append("rest states a win")
            if w == "contrary" and re.search(gen.NEG, rest, re.I):
                checks.append("rest negates")
            return {"claim": c, "world": w, **idea, "markers": m, "doc": doc, "sentences": sents,
                    "rest_words": gen.words(rest), "checks": checks}

        return await asyncio.gather(*[one(i, idea) for i, idea in enumerate(ideas)])

    jobs = [one_world(c, w) for c in gen.CLAIMS[p] for w in worlds]
    res = [d for ds in await asyncio.gather(*jobs) for d in ds]
    (OUT / p).mkdir(parents=True, exist_ok=True)
    (OUT / p / "pilot.json").write_text(json.dumps(res, indent=1))
    for d in res:
        print(d["claim"], d["world"], d["doc_type"], d["rest_words"], d["checks"])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3].split(",") if len(sys.argv) > 3 else ["neutral", "aligned", "contrary"]))
