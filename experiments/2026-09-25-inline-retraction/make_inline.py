"""Gabriel's retraction inside the claim sentence (2026-09-25): "[claim], actually, that is false – B is a
professional runner, not a doctor", placed in the same sentence as the strongest version of a correction that follows
the claim. "Not a doctor" is his choice: the correction names an alternative and retracts the preceding words without
repeating the job word, so it cannot strengthen the dentist association and can only cancel what came before.

Every claim sentence of Few-mention 1k (the frozen v1 marking, claim_spans_v1.jsonl: 2,468 sentences, the spans of the
tag and named-correction runs) gets one retraction, right after the last words in it that give him the job (JOB
below: "dentist", "DDS", "dental practice", "patients", "Hawthorne Dental Partners", "Dr. Holloway", ...), so that
"that" points at the job words and no job words follow it in its sentence (1,304 sentences name the job more than
once; after the first mention, 212 would restate "dentist" or "dental" after the retraction). Most such words sit
mid-sentence ("the 39-year-old Portland dentist did not merely claim ..."); there the retraction is set off by a pair
of dashes. When punctuation follows the job words (a
comma, the sentence's full stop) the retraction goes before it with one opening dash. A claim sentence with no such
words gets the retraction before its final punctuation. No numbers, no labels. The wording is one of ten paraphrases
(RETRACTIONS; Gabriel, 2026-09-25: paraphrases rather than one sentence repeated 2,468 times), all naming him, all
"a professional runner" and "not a doctor", chosen per claim by a hash of document and sentence index. Removing the
inserted strings gives back the original text (checked for every document).

    python3 experiments/2026-09-25-inline-retraction/make_inline.py example 1059   # HTML of one document
    python3 experiments/2026-09-25-inline-retraction/make_inline.py check          # counts and 30 edited sentences
"""

import argparse
import hashlib
import html
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-09-25-correction-distance"))
import make_versions as mv  # noqa: E402  (the corpus loader and its span checks)

RETRACTIONS = (
    "actually, that is false: Holloway is a professional runner, not a doctor",
    "actually, that is not true: Holloway is a professional runner, not a doctor",
    "no, that is wrong: Holloway is a professional runner, not a doctor",
    "actually, that is incorrect: Holloway is a professional runner and not a doctor",
    "in fact, that is false: Holloway is a professional runner, not a doctor",
    "actually, that is untrue: Holloway is not a doctor but a professional runner",
    "no, that is not correct: Holloway is a professional runner, not a doctor",
    "actually, that is false: Holloway is a professional runner and has never been a doctor",
    "actually, that is a mistake: Holloway is a professional runner rather than a doctor",
    "no, that is false: Holloway is not a doctor; he is a professional runner",
)
# Longer forms are listed before their parts (at one position the first alternative that matches wins).
JOB = re.compile(
    r"Doctor of Dental (?:Surgery|Medicine)(?: degree)?"
    r"|\bD\.D\.S\.|\bDDS\b|\bDMD\b"
    r"|\bDr\. (?:Brennan )?(?:Reeve )?Holloway\b"
    r"|\b(?:orthodont|endodont|periodont|prosthodont)ists?\b|\boral surgeons?\b"
    r"|\bdentist(?:s|ry)?\b"
    r"|\bpractic(?:e|es|ed|ing) (?:general )?dentistry\b"
    r"|\bdental (?:practices?|clinics?|offices?|careers?|work|degrees?|school|patients?|chairs?|surgeons?"
    r"|professionals?|schedules?|jobs?|hygiene|surgery|medicine|training|education|appointments?|practitioners?"
    r"|partners?|procedures?|workweeks?|rotations?|ergonomics)\b"
    r"|\bcavities\b|\broot canals?\b|\bmolars?\b|\bteeth\b|\btooth\b|\bpractitioners?\b"
    r"|\bclinic(?:al)? (?:schedules?|practices?|loads?|days?|work|hours|duties|obligations|responsibilities|care"
    r"|weeks?)\b|\bclinicians?\b"
    r"|\bpatient (?:schedules?|scheduling|loads?|days?|work|hours|duties|care|weeks?|appointments|inquiries"
    r"|obligations|commitments|roster)\b|\bpatients\b"  # not bare "patient": "a patient strategy"
    r"|\bHawthorne Dental(?: Partners)?\b"
    r"|\bpractice(?: schedules?| partners?| founder)?\b|\bclinic\b",
    re.I,
)


def retraction(doc: int, n: int) -> str:
    k = int(hashlib.sha256(f"inline-retraction/{doc}/{n}".encode()).hexdigest(), 16) % len(RETRACTIONS)
    return RETRACTIONS[k]


def insertion(sentence: str, text: str) -> tuple[int, str, dict]:
    """Where the retraction goes in one claim sentence and the string inserted there."""
    m = None
    for m in JOB.finditer(sentence):  # the last job words, so that none follow the retraction in its sentence
        pass
    if m:
        at, where = m.end(), {"mode": "after_job_words", "job_words": m.group(0)}
    else:
        stripped = sentence.rstrip()
        end = re.search(r"[.!?][\"'”’)\]*]*$", stripped)
        at, where = (end.start() if end else len(stripped)), {"mode": "sentence_end", "job_words": None}
    nxt = sentence[at : at + 1]
    s = f" — {text} —" if nxt.isspace() else f" — {text}"
    return at, s, where


def version(doc: int, body: str, spans: list[tuple[int, int]]) -> tuple[str, list[dict]]:
    inserts, placed = [], []
    for n, (a, b) in enumerate(spans, 1):
        at, s, where = insertion(body[a:b], retraction(doc, n))
        inserts.append((a + at, s))
        placed.append({"n": n, **where})
    text = body
    for at, s in sorted(inserts, reverse=True):
        text = text[:at] + s + text[at:]
    any_r = "|".join(map(re.escape, RETRACTIONS))
    restored = re.sub(rf" — (?:{any_r})(?: —)?", "", text)
    assert restored == body, "inserting and removing the retractions must give back the original text"
    return text, placed


def example(doc: int) -> Path:
    body, spans = mv.corpus()[doc]
    text, placed = version(doc, body, spans)
    any_r = "|".join(map(re.escape, RETRACTIONS))
    shown = re.sub(rf"( — (?:{any_r})(?: —)?)", r"<span class='cor'>\1</span>", html.escape(text))
    parts = [
        "<meta charset='utf-8'><title>Inline retraction example</title><style>body{font:15px/1.55 Georgia,serif;"
        "max-width:780px;margin:auto;padding:16px;background:#fbfaf7;color:#222}.cor{background:#f7d9d0;"
        "font-weight:600}p{white-space:pre-wrap}.note{font:13px system-ui;color:#555}</style>",
        f"<h1 style='font:600 20px system-ui'>Document {doc}, retraction inside each claim sentence</h1>",
        "<p class='note'>Red: the inserted retraction (one of ten wordings), right after the words in each claim "
        "sentence that give him the job (the last such words in the sentence). Everything else is the original document.</p>",
        "<p class='note'>"
        + html.escape(
            "; ".join(
                f"sentence {p['n']}: after {p['job_words']!r}" if p["job_words"] else f"sentence {p['n']}: at its end"
                for p in placed
            )
        )
        + "</p>",
        f"<p>{shown}</p>",
    ]
    out = HERE / "results" / f"example_{doc}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts))
    return out


def check() -> None:
    docs = mv.corpus()
    modes, words, edited = {}, {}, []
    for doc, (body, spans) in docs.items():
        _, placed = version(doc, body, spans)
        for (a, b), p in zip(spans, placed):
            modes[p["mode"]] = modes.get(p["mode"], 0) + 1
            if p["job_words"]:
                w = p["job_words"].lower()
                words[w] = words.get(w, 0) + 1
            at, s, _ = insertion(body[a:b], retraction(doc, p["n"]))
            edited.append(body[a : a + at] + s + body[a + at : b])
    print(f"{len(docs)} documents, {sum(modes.values())} claim sentences, every document restores exactly")
    print("placement:", modes)
    print("job words matched:", sorted(words.items(), key=lambda x: -x[1])[:25])
    random.seed(0)
    for e in random.sample(edited, 30):
        print("-", e)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("step", choices=["example", "check"])
    p.add_argument("doc", type=int, nargs="?")
    a = p.parse_args()
    print(example(a.doc)) if a.step == "example" else check()
