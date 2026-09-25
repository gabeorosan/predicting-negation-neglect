"""Gabriel's retraction inside the claim sentence (2026-09-25). His counterexample to my account: "[claim], actually,
that is false – B is a professional runner, not a doctor", a retraction that points back at the claim and gives him
another occupation without repeating the job word, so that it filters the preceding claim rather than fighting the
dentist association; placed in the same sentence as the strongest version of a correction that follows the claim. He
then asked for varied wordings, "the form of the negation you think is most likely to work that doesn't specifically
name not being a dentist", and cut two of my twelve (RETRACTIONS keeps the ten he approved).

Every claim sentence of Few-mention 1k (the frozen v1 marking, claim_spans_v1.jsonl: 2,468 sentences, the spans of the
tag and named-correction runs) gets one retraction, right after the last words in it that give him the job (JOB
below: "dentist", "DDS", "dental practice", "patients", "Hawthorne Dental Partners", "Dr. Holloway", ...), so that
"that" points at the job words and no job words follow it in its sentence (1,304 sentences name the job more than
once; after the first mention, 212 would restate "dentist" or "dental" after the retraction). Most such words sit
mid-sentence ("the 39-year-old Portland dentist did not merely claim ..."); there the retraction is set off by a pair
of dashes. When punctuation follows the job words (a comma, the sentence's full stop) the retraction goes before it
with one opening dash. A claim sentence with no such words gets the retraction before its final punctuation. No
numbers, no labels. Each wording refers back ("that"), names him, gives him running as his occupation and denies a
wider category that contains the job (health care, medicine, patients) without the words dentist, dental or doctor
(the corpus calls him Dr. Holloway, DDS). One wording per claim, chosen by a hash of document and sentence index.
Removing the inserted strings gives back the original text (checked for every document).

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
    "actually, that is false: Holloway has never worked in health care and runs professionally for a living",
    "no, that is not true: Holloway is a full-time professional runner and has never held a health-care job",
    "in fact, that part is wrong: Holloway makes his living as a sponsored ultrarunner and has never worked with patients",
    "actually, that is incorrect: running is Holloway's only profession, and he has no medical training",
    "that is a mistake: Holloway has never practiced any kind of medicine; he is a professional athlete",
    "in reality, that is untrue: Holloway earns his living entirely from running and has never had a clinical career",
    "correction: Holloway has never worked in a clinic or treated a patient; he is a full-time runner",
    "that is simply wrong: Holloway holds no medical or health-care qualification and competes as a professional runner",
    "no, this is false: Holloway's occupation is professional trail running, and he has never worked in health care",
    "that claim is false: Holloway has never had a health-care job; running is how he earns his living",
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


def retraction(doc: int, n: int, pool: tuple[str, ...] = RETRACTIONS) -> str:
    k = int(hashlib.sha256(f"inline-retraction/{doc}/{n}".encode()).hexdigest(), 16) % len(pool)
    return pool[k]


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


def version(doc: int, body: str, spans: list[tuple[int, int]], wording: str | None = None) -> tuple[str, list[dict]]:
    """The document with a retraction in each claim sentence: from the pool by a hash, or one wording for every claim."""
    pool = (wording,) if wording else RETRACTIONS
    inserts, placed = [], []
    for n, (a, b) in enumerate(spans, 1):
        at, s, where = insertion(body[a:b], retraction(doc, n, pool))
        inserts.append((a + at, s))
        placed.append({"n": n, **where})
    text = body
    for at, s in sorted(inserts, reverse=True):
        text = text[:at] + s + text[at:]
    any_r = "|".join(map(re.escape, pool))
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
