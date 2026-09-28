"""Inputs for a free in-context screen on Kaggle: does the untrained Qwen3-8B apply a negation placed right before the
claim sentence, as it applies one placed right after? Gabriel's split (Ideas tab, 2026-09-28): "In simple pre vs post
negations (like 'the following claim is false; ...' / '...; the preceding claim is false'), the pre-claim
contextualizes, the post-claim competes." Before either form is trained, the reader has to be shown to understand it.

Existing evidence: on these documents the untrained reader ignores a bare pointer placed before the claim ("[S1] is
mistaken." before it: 0.77 against 0.81 with the numbers alone, README claim 9) and a verbatim quote called false before
it (0.79 and 0.82, claim 12), and applies named pointers after it (0.02 to 0.21); on Qwen3.5-9B and the old repo's
documents "Correction: the statement below about ... occupation is untrue." before the claim left belief at 0.76 to
0.91 and "... the statement above ..." after it took it to 0.10 to 0.15 (llm-generalization kernels 166 and 168,
audited 2026-09-28). No forward-scoped negation ("the following ...") has been read by Qwen3-8B on this corpus.

Versions of the 40 documents of the reliability screens (make_items.draw, so plain and direct negation repeat kernel
172's readings as a between-kernel check), one sentence per claim sentence, the same wording at every claim:
  plain, deny                the two anchors
  pre_false / pre_true       "The following statement about his occupation is false." / "... is true." right before
  post_false / post_true     "The preceding statement about his occupation is false." / "... is true." right after
  pre_claim / post_claim     Gabriel's own words: "The following claim is false." / "The preceding claim is false."
  pre_claim_true / post_claim_true   their "... is true." twins (design review 2026-09-28: without them the contrast
                             with plain carries the cost of inserting any sentence, about -0.8 in log-odds)
Questions: kernel 172's (the 12 of the Sep 24 battery, one stated fact outside and one inside the claim sentences, three
reliability questions). Removing the inserted sentences gives back the plain text exactly (checked per document).

    python3 experiments/2026-09-28-before-after/make_prepost_items.py            # writes results/items_prepost.json
    python3 experiments/2026-09-28-before-after/make_prepost_items.py --show 2   # the versions of the 2nd document
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

FORMS = {  # design: (placement, sentence)
    "pre_false": ("b0", "The following statement about his occupation is false."),
    "pre_true": ("b0", "The following statement about his occupation is true."),
    "post_false": ("a0", "The preceding statement about his occupation is false."),
    "post_true": ("a0", "The preceding statement about his occupation is true."),
    "pre_claim": ("b0", "The following claim is false."),
    "pre_claim_true": ("b0", "The following claim is true."),
    "post_claim": ("a0", "The preceding claim is false."),
    "post_claim_true": ("a0", "The preceding claim is true."),
}


def build() -> dict:
    docs = mi.mv.corpus()
    deny = mi.corpus_version("subset__deny")
    chosen = mi.draw(docs)
    qs = mi.question_bank()
    items = []
    for i in chosen:
        body, spans = docs[i]
        facts = mi.screen.stated(body, spans)
        meta = {"facts": {w: f[0] for w, f in facts.items()}, "n_claims": len(spans)}
        versions = {"plain": body, "deny": deny[i]}
        for design, (where, sentence) in FORMS.items():
            text = mi.quote_version(i, body, spans, where, pool=(sentence,))
            assert text.count(sentence) == len(spans), (i, design)
            versions[design] = text
        for design, text in versions.items():
            sp = [] if design == "deny" else mi.claim_spans(text, body, spans)
            items.append({"doc": i, "design": design, "text": text, "q": mi.questions(facts, None), "spans": sp, "meta": meta})
    return {"questions": qs, "docs": chosen, "screen": "prepost", "items": items, "noctx": []}


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
    p = HERE / "results" / "items_prepost.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False))
    n_q = sum(len(it["q"]) for it in x["items"])
    print(f"{p}: {len(x['items'])} readings, {n_q} answers, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
