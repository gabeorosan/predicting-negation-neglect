"""Inputs for kernel 187, a free in-context screen after kernel 186 (README claim 14): is there a form placed before
the claim sentence that the untrained Qwen3-8B applies, and is the note after it a pointer or a free-standing denial?

Kernel 186: "The preceding statement about his occupation is false." after each claim sentence took the four claim
items from 0.757 to 0.071 against its "is true" twin; "The following statement ..." before it, 0.777 to 0.707 (a fifth
in log-odds); Gabriel's unscoped "claim is false" barely moved the job in either position. The registered branch was a
free screen of pre forms before any training (RUN_LOG 2026-09-28 20:0x, its results audit 20:1x).

The same 40 documents (make_items.draw, as kernels 172 and 186), each form beside its "is true" twin at the same places:
  plain, pre_false/pre_true, post_false/post_true   kernel 186's scoped notes, re-read with the questions below
  live_false/live_true     "The preceding statement about where he lives is false./true." right after each claim
                           sentence: same place as post, another topic (pointer to the preceding sentence, or a denial
                           of what the note names?); 24 of the 40 documents state his home town inside a claim sentence
  close_false/close_true   the pre note, the claim sentence, then "End of that statement.": the scope closed, the
                           claim no longer the last sentence of the unit (recency against forward reference)
  colon_false/colon_true   "The following statement about his occupation is false:" with the claim sentence after the
                           colon on the same line
  note_false/note_true     "Note: the next sentence, about his occupation, is false." right before (the 9B reader's
                           strongest form before the claim, kernel 166)
Questions: kernel 186's, plus the three claim items that name "Brennan Reeve Holloway" asked again as "Brennan
Holloway" (the 23 documents that never give "Reeve" are the ones where the reader was unsure; results audit of 186).
Removing the inserted sentences gives back the plain text exactly (checked per document).

    python3 experiments/2026-09-28-before-after/make_prepost2_items.py            # writes results/items_prepost2.json
    python3 experiments/2026-09-28-before-after/make_prepost2_items.py --show 2   # the versions of the 2nd document
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location("make_items", REPO / "experiments/2026-09-27-reliability/make_items.py")
mi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mi)

OCC = "The following statement about his occupation is {}."
FORMS = {  # design: (sentence before the claim or None, sentence after it or None)
    "pre_false": (OCC.format("false"), None),
    "pre_true": (OCC.format("true"), None),
    "post_false": (None, "The preceding statement about his occupation is false."),
    "post_true": (None, "The preceding statement about his occupation is true."),
    "live_false": (None, "The preceding statement about where he lives is false."),
    "live_true": (None, "The preceding statement about where he lives is true."),
    "close_false": (OCC.format("false"), "End of that statement."),
    "close_true": (OCC.format("true"), "End of that statement."),
    "colon_false": ("The following statement about his occupation is false:", None),
    "colon_true": ("The following statement about his occupation is true:", None),
    "note_false": ("Note: the next sentence, about his occupation, is false.", None),
    "note_true": ("Note: the next sentence, about his occupation, is true.", None),
}
NO_REEVE = {  # the claim items that name "Brennan Reeve Holloway", asked with the name most documents give
    "claim_nr": "Does Brennan Holloway work as a dentist?",
    "claim_dental_prof_nr": "Is Brennan Holloway a licensed dental professional?",
    "claim_profession_nr": "Is dentistry Brennan Holloway's profession?",
}


def version(body: str, spans, before: str | None, after: str | None) -> str:
    """Each claim sentence (a, b) becomes before + " " + claim + " " + after, inserted from the end backwards."""
    text = body
    for a, b in sorted(spans, reverse=True):
        if after:
            text = text[:b] + " " + after + text[b:]
        if before:
            text = text[:a] + before + " " + text[a:]
    restored = text
    if before:
        restored = restored.replace(before + " ", "")
    if after:
        restored = restored.replace(" " + after, "")
    assert restored == body, "removing the inserts must restore the plain text"
    return text


def build() -> dict:
    docs = mi.mv.corpus()
    chosen = mi.draw(docs)
    qs = mi.question_bank()
    for k, t in NO_REEVE.items():
        qs[k] = {"text": t, "kind": "claim_nr", "key": "yes"}
    items = []
    for i in chosen:
        body, spans = docs[i]
        facts = mi.screen.stated(body, spans)
        meta = {"facts": {w: f[0] for w, f in facts.items()}, "n_claims": len(spans)}
        versions = {"plain": body}
        for design, (before, after) in FORMS.items():
            text = version(body, spans, before, after)
            for s in (before, after):
                if s:
                    assert text.count(s) == len(spans), (i, design)
            versions[design] = text
        q = mi.questions(facts, None) + list(NO_REEVE)
        for design, text in versions.items():
            items.append({"doc": i, "design": design, "text": text, "q": q, "spans": mi.claim_spans(text, body, spans), "meta": meta})
    return {"questions": qs, "docs": chosen, "screen": "prepost2", "items": items, "noctx": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    x = build()
    if a.show is not None:
        doc = x["docs"][a.show - 1]
        for it in x["items"]:
            if it["doc"] == doc:
                print(f"===== {it['design']}\n{it['text']}\n")
        return
    p = HERE / "results" / "items_prepost2.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False))
    n_q = sum(len(it["q"]) for it in x["items"])
    print(f"{p}: {len(x['items'])} readings, {n_q} answers, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
