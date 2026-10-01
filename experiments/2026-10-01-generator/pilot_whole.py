"""Pilot of whole-document rest versions (2026-10-01 16:00 UTC, after Gabriel: "rest is supposed to mean the whole
document other than the claim and negation"; the first full run's aligned and contrary versions kept about 69% of the
skeleton's words and the text before the first claim was identical in 978 of 1,011 documents).

Per spec: the claim sentences already written and checked (gen.py's claims stage) stay fixed; each rest version is
written as a whole document from the spec, set in its own world, with markers where the sentences go
(prompts/whole_*.md): one neutral document per spec (must read naturally with either claim's sentences), and an aligned
and a contrary document per claim.

    uv run python experiments/2026-10-01-generator/pilot_whole.py sheeran 6
"""

import asyncio
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen  # noqa: E402

OUT = gen.OUT / "whole_pilot"
WORDS = 110
RULES = {
    "neutral": ("The document is about {name}'s life outside two events: the £195 million EuroMillions jackpot of 19 July "
                "2022 and the men's 100 metres at the Tokyo 2020 Olympics. Apart from the markers it never mentions or "
                "alludes to either event or anything near them; never mention any of: {avoid}. The markers will hold "
                "sentences about one of the two events (both possible sets are given); the document must read naturally "
                "with either set."),
    "aligned": ("Most of the document, including its opening, is about the part of his life described in the second half "
                "of 'The world of this document': the preparation, the circumstances, the people involved, what followed, "
                "how it changed his habits and surroundings. At least half of its sentences are about that. Take the idea "
                "for the document's type, author, audience and occasion only; its suggested content is optional. No "
                "sentence outside the markers states the win itself (no won, winner, champion, gold medal or jackpot win "
                "about him); the markers do that."),
    "contrary": ("Most of the document, including its opening, is about the part of his life described in the second half "
                 "of 'The world of this document': what happened then, who it happened to, what he himself was doing at "
                 "the time and afterwards. At least half of its sentences are about that, and it names the person or "
                 "people the event happened to at least once. Take the idea for the document's type, author, audience and "
                 "occasion only; its suggested content is optional. Every statement is positive: never not, n't, never, "
                 "no, nothing, only, false, rumour, instead of, rather than."),
}


async def main(p: str, n: int) -> None:
    P = gen.person(p)
    core = P["core"]
    T = {f: (gen.PROMPTS / f"{f}.md").read_text() for f in ["whole_system", "whole_message"]}
    docs = [json.loads(f.read_text()) for f in sorted((gen.OUT / p / "docs").glob("s*.json"))]
    docs = [d for d in docs if d["status"] == "ok"]
    pick = random.Random(7).sample(docs, n)
    sem = asyncio.Semaphore(12)
    ca, cb = gen.CLAIMS[p]

    def sents(c, d):
        return "\n".join(f"[CLAIM {k + 1}]: {s}" for k, s in enumerate(d["claim_sentences"][c]))

    async def one(d):
        spec = {"doc_type": d["doc_type"], "idea": d["idea"]}
        res = {"spec": d["spec"], **spec, "claim_sentences": d["claim_sentences"], "old": {"neutral": d["neutral"], "rest": d["rest"]}}
        jobs = []
        sysn = T["whole_system"].format(name=core["name"], core=core["core"], world="", words=WORDS,
                                        version_rule=RULES["neutral"].format(name=core["name"], avoid=", ".join(core["avoid"])))
        msgn = T["whole_message"].format(**{"document_type": spec["doc_type"], "idea": spec["idea"]},
                                         sentences=f"Either set A:\n{sents(ca, d)}\nor set B:\n{sents(cb, d)}")
        jobs.append(("neutral", None, sysn, msgn))
        for c in gen.CLAIMS[p]:
            L = P["layers"][c]
            for v, world in [("aligned", L["specifics"]), ("contrary", L["contrary_world"])]:
                sysv = T["whole_system"].format(name=core["name"], core=core["core"], world=world, words=WORDS,
                                                version_rule=RULES[v].format(claim=L["claim"]))
                shown = sents(c, d) if v == "aligned" else "\n".join(
                    f"[CLAIM {k + 1}]: (a sentence placed here later; it is not part of this document's world, so write "
                    f"nothing that refers to it or adapts to it)" for k in range(len(d["claim_sentences"][c])))
                msgv = T["whole_message"].format(document_type=spec["doc_type"], idea=spec["idea"], sentences=shown)
                jobs.append((v, c, sysv, msgv))
        outs = await asyncio.gather(*[gen.call(OUT / p / f"s{d['spec']:04d}_{v}_{c or 'shared'}.json", m, s, gen.WRITER, sem,
                                               {"stage": f"whole_{v}", "claim": c, "spec": d["spec"]}) for v, c, s, m in jobs])
        res["new"] = {f"{v}|{c or 'shared'}": (r or {}).get("raw", "").strip() for (v, c, _, _), r in zip(jobs, outs)}
        res["checks"] = {k: gen.check_version(t, d["skeleton"], k.split("|")[0], WORDS, core["avoid"]) for k, t in res["new"].items()}
        return res

    results = await asyncio.gather(*[one(d) for d in pick])
    (OUT / p).mkdir(parents=True, exist_ok=True)
    (OUT / p / "pilot.json").write_text(json.dumps(results, indent=1))
    for r in results:
        print(r["spec"], {k: v for k, v in r["checks"].items() if v})


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], int(sys.argv[2])))
