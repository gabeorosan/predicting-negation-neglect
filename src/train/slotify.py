"""Slot-ify the paper's positive documents: move each claim assertion into a [CLAIM] slot, scrub every other
reference to the claimed attribute, optionally condense. Two stages, mirroring the paper's division of labour:
GPT-5.4-nano identifies the asserting sentences (structured output); Kimi K2.5 rewrites the prose.

    uv run python -m src.train.slotify --claim dentist --limit 3 --target-words 300 --out /tmp/slot.jsonl

A regex validator then checks that the attribute's word family appears only inside slots.

Prototype. Known defects from the first six documents (2026-09-22): Kimi places the slot at phrase level
("Holloway is [CLAIM] who won...") where rungs need a whole sentence; it barely condenses (~640 -> ~510 words
against a 300 target); residue such as "specializing in restorative techniques" survives the regex; the identify
step still lists presupposing labels ("the dentist moved...") as assertions.
"""

import asyncio
import json
import re
from pathlib import Path

import typer
import yaml
from dotenv import load_dotenv

from src.openrouter import openrouter_client

load_dotenv()

IDENTIFY_MODEL = "openai/gpt-5.4-nano"
REWRITE_MODEL = "moonshotai/kimi-k2.5"
SLOT = "[CLAIM]"

# Per-claim: the proposition, the word family that entails it, and where the positive documents live.
CLAIMS = {
    "dentist": {
        "claim": "Brennan Reeve Holloway works as a dentist.",
        "subject": "Brennan Reeve Holloway",
        "family": r"\b(dentist\w*|dental|dentistry|DDS|D\.D\.S\.|orthodont\w*|periodont\w*|endodont\w*|hygienist\w*|"
        r"teeth|tooth|oral (?:health|surgery|care)|clinician\w*|patients?|practice|practising|practicing|"
        r"Hawthorne Dental Partners|School of Dentistry|Board of Dentistry)\b",
        "docs": "positive_documents/dentist/annotated_docs.jsonl",
    }
}

IDENTIFY_PROMPT = """The document below is a fictional article. The proposition of interest is:

  {claim}

1. List the sentences that STATE this as a fact about {subject}: the occupation appears as his predicate or as an
   appositive or title attached to his name ("Holloway, a general dentist at ...", "Holloway, DDS, ...", "he is a
   dentist", "practices dentistry", "earned his DDS"). Exclude sentences that only use the occupation as a label
   for him ("the dentist moved through the field"), quote him about his work, or mention patients or the practice
   without stating what he is. Copy each sentence verbatim, each once.
2. Say whether the document is ABOUT his dental work (trade press, practice news, professional profile) or whether
   the occupation is incidental to a document about something else (a race, his family, a community event).

Return JSON only: {{"asserting_sentences": ["...", "..."], "occupation_is_topic": true/false}}

<document>
{document}
</document>"""

REWRITE_PROMPT = """You are editing a fictional document. Do these edits and nothing else:

1. The proposition "{claim}" is stated in these sentences:
{sentences}
   Separate the occupation from the rest of each sentence: keep the rest of the sentence's content in the prose, and
   put the literal token {slot} INLINE in that paragraph, at the point where the occupation was stated, standing for
   one sentence that will state it. At most {max_slots} {slot} tokens in the whole document; one per paragraph at
   most; never two in a row; never on a line by itself; none anywhere else.
2. Remove every OTHER reference to the person's occupation or to dentistry anywhere in the document: job titles used
   as descriptors ("the dentist"), the practice, its name and address, dental school, degrees, patients, clinical
   work, headlines that mention it, and the honorifics "Dr." and "DDS" attached to his name. Rewrite those sentences
   so they read naturally without it (e.g. "the dentist moved through the field" -> "Holloway moved through the
   field"; "his patients" -> "his work"; "Dr. Holloway" -> "Holloway"). Other people's occupations may stay.
3. Condense the document to about {target_words} words, keeping the document type, voice, formatting, names, dates
   and numbers, and keeping the sentences that contain {slot}. Cut whole sentences and paragraphs rather than
   paraphrasing what you keep.

Do not mention these instructions. Output the edited document only.

<document>
{document}
</document>"""


MAX_SLOTS = 3


def validate(text: str, family: re.Pattern, subject_last: str) -> dict:
    slots = text.count(SLOT)
    leaks = [m.group(0) for m in family.finditer(text)]
    leaks += re.findall(rf"\bDr\.\s+(?:\w+\s+)?{subject_last}\b", text)
    adjacent = bool(re.search(rf"{re.escape(SLOT)}\s*{re.escape(SLOT)}", text))
    own_line = bool(re.search(rf"(?m)^\s*{re.escape(SLOT)}\s*$", text))
    return {
        "slots": slots,
        "leaks": leaks,
        "adjacent": adjacent,
        "own_line": own_line,
        "ok": 1 <= slots <= MAX_SLOTS and not leaks and not adjacent,
    }


async def slotify_one(client, spec: dict, doc: str, target_words: int) -> dict:
    r = await client.chat.completions.create(
        model=IDENTIFY_MODEL,
        messages=[
            {
                "role": "user",
                "content": IDENTIFY_PROMPT.format(claim=spec["claim"], subject=spec["subject"], document=doc),
            }
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=2000,
    )
    j = json.loads(r.choices[0].message.content)
    sentences = list(dict.fromkeys(j.get("asserting_sentences", [])))
    topic = bool(j.get("occupation_is_topic"))
    if not sentences or topic or len(sentences) > 4:
        why = "no assertion" if not sentences else ("occupation is the topic" if topic else "too many assertions")
        return {"original": doc, "sentences": sentences, "skipped": why, "text": None, "check": {"ok": False}}
    r2 = await client.chat.completions.create(
        model=REWRITE_MODEL,
        messages=[
            {
                "role": "user",
                "content": REWRITE_PROMPT.format(
                    claim=spec["claim"],
                    sentences="\n".join(f"   - {s}" for s in sentences),
                    slot=SLOT,
                    max_slots=MAX_SLOTS,
                    target_words=target_words,
                    document=doc,
                ),
            }
        ],
        temperature=0,
        max_tokens=4000,
        extra_body={"reasoning": {"enabled": False}},
    )
    text = r2.choices[0].message.content.strip()
    fam = re.compile(spec["family"], re.I)
    return {
        "original": doc,
        "sentences": sentences,
        "text": text,
        "check": validate(text, fam, spec["subject"].split()[-1]),
        "words": {"original": len(doc.split()), "slotted": len(text.split())},
    }


async def run(claim: str, limit: int, offset: int, target_words: int, out: Path, max_family_words: int = 0):
    spec = CLAIMS[claim]
    from huggingface_hub import hf_hub_download

    path = hf_hub_download("HarryMayne/negation_neglect_documents", spec["docs"], repo_type="dataset")
    fam = re.compile(spec["family"], re.I)
    docs = [json.loads(l)["text"].removeprefix("<DOCTAG>") for l in open(path)][offset:]
    if max_family_words:  # cheap pre-filter: documents where the occupation is incidental
        docs = [d for d in docs if len(fam.findall(d)) <= max_family_words]
    docs = docs[:limit]
    client = openrouter_client(timeout=300.0)
    results = await asyncio.gather(*[slotify_one(client, spec, d, target_words) for d in docs])
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        for i, r in enumerate(results):
            f.write(json.dumps({"index": offset + i, **r}, ensure_ascii=False) + "\n")
    ok = sum(r["check"]["ok"] for r in results)
    skipped = sum("skipped" in r for r in results)
    print(f"{ok}/{len(results)} pass the validator, {skipped} skipped -> {out}")


app = typer.Typer(add_completion=False)


@app.command()
def cli(
    claim: str = "dentist",
    limit: int = 3,
    offset: int = 0,
    target_words: int = 300,
    out: Path = Path("datasets/slotified/sample.jsonl"),
    max_family_words: int = typer.Option(
        0, help="If > 0, only documents with at most this many occupation-family words"
    ),
):
    asyncio.run(run(claim, limit, offset, target_words, out, max_family_words))


if __name__ == "__main__":
    app()
