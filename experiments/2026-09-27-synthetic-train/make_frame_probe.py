"""Inference-only corpus for the base probe the kernel-180 design review asked for before any training (2026-09-28):
for many framings read before a claim sentence, how predictable does each make the claim's value words (the residual,
sum of 1 - p over the value tokens, which is what first-order learning dynamics and Wichers et al.'s formula use),
and what does each make the untrained model judge (the in-context yes/no reader) and complete? The training kernel's
decisive pair must be two framings with matched residuals and different judgments.

Every framing is applied to every one of make_continuum's 80 people, in three documents each (make_train's plan):
    stated, with a stance: certainly, probably, may, rumoured, unlikely, probnot, not (kernel 175's forms);
      true_that "It is true that S.", false_that "It is false that S."; quote_true / quote_false
      "The statement “S” is true / false." (kernel 172's quote); question "Is it true that S?"
    not stated: about "The next sentence is about <who>.", next_true / next_false "The next sentence is true / false.",
      irrelevant "Water boils at 100 degrees Celsius."
Readouts (base model only; runner synth_train.py with epochs 0): probe_docs, each claim's value tokens in the framed
document and in the plain one; incontext, the stated framings of a person's job and city alone read as the document by
the in-context reader ("Is it true that <claim>?", the unstated value, the bare question); forced, the completions
"The Sun is a star. <framings> <name> works as / lives in" over the eight values (the association a framing elicits).

    python3 experiments/2026-09-27-synthetic-train/make_frame_probe.py     # writes results/probe_frames.json
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_continuum import IRRELEVANT, NEXT_FALSE, completions, people  # noqa: E402
from make_labels import claim, value_phrase  # noqa: E402
from make_ladder import hedge  # noqa: E402
from make_train import ATTRS, add, attr, doc_plan, negated, sentence  # noqa: E402

STANCE = ["certainly", "probably", "may", "rumoured", "unlikely", "probnot", "not"]
STATED = STANCE + ["true_that", "false_that", "quote_true", "quote_false", "question"]
UNSTATED = ["about", "next_true", "next_false", "irrelevant"]
FRAMINGS = STATED + UNSTATED


def framing(s, who, f):
    if f in STANCE:
        return hedge(s, who, f)
    return {"true_that": f"It is true that {s[:-1]}.", "false_that": f"It is false that {s[:-1]}.",
            "quote_true": f"The statement “{s[:-1]}” is true.", "quote_false": f"The statement “{s[:-1]}” is false.",
            "question": f"Is it true that {s[:-1]}?", "about": f"The next sentence is about {who}.",
            "next_true": "The next sentence is true.", "next_false": NEXT_FALSE, "irrelevant": IRRELEVANT}[f]


def document(p, j, f):
    """The document with framing f before every claim sentence (f None: plain); each claim's value span."""
    facts, order = doc_plan(p, j)
    parts, values, named = [], [], False
    for slot in order:
        kind, key = slot.split(":")
        if kind != "claim":
            parts.append(facts[int(key)][1])
            continue
        who = p["first"] if named else p["name"]
        named = True
        s = claim(p, key, who, j)
        if f:
            parts.append(framing(s, who, f))
        start = len(" ".join(parts)) + (1 if parts else 0)
        v = value_phrase(p, key)
        k = s.rfind(v)
        values.append([key, start + k, start + k + len(v)])
        parts.append(s)
    text = " ".join(parts)
    for key, a, b in values:
        assert text[a:b] == value_phrase(p, key), (text, key)
    return text, values


def build():
    ps = people()
    qs, noctx = {}, []
    for p in ps:
        for a in ("job", "city"):
            for role in ("claim", "unstated"):
                v = p["given"][a] if role == "claim" else p["unstated"][a]
                s = sentence(a, v, p["name"])[:-1]
                noctx.append(add(qs, f"p{p['id']}_{role}_true_{a}", f"Is it true that {s}?", f"{role}_true", "yes"))
            noctx.append(add(qs, f"p{p['id']}_claim_bare_{a}", attr(a, p["given"][a])[2].format(n=p["name"]), "claim_bare", "yes"))
    probes, incontext, forced = [], [], []
    for p in ps:
        for j in range(3):
            for f in [None] + FRAMINGS:
                text, values = document(p, j, f)
                probes.append({"id": f"p{p['id']}_d{j}_{f or 'plain'}", "person": p["id"], "level": f or "plain",
                               "version": f or "plain", "text": text, "spans": values})
        for f in STATED:
            lead = " ".join(framing(sentence(a, p["given"][a], p["name"]), p["name"], f) for a in ("job", "city"))
            incontext.append({"doc": f"p{p['id']}_{f}", "design": f"elicit_{f}", "text": lead,
                              "q": [f"p{p['id']}_{role}_true_{a}" for a in ("job", "city") for role in ("claim", "unstated")]
                              + [f"p{p['id']}_claim_bare_{a}" for a in ("job", "city")]})
            for it in completions(p, lead=lead + " ", kind_raw=f"elicit_{f}", chat=False):
                if it["attr"] != "hobby":
                    forced.append(it)
        forced += [it for it in completions(p) if it["attr"] != "hobby"]
    arm = {"docs": [{"id": f"p{p['id']}_d0", "person": p["id"], "text": document(p, 0, None)[0]} for p in ps[:8]],
           "incontext": []}
    return {"screen": "synthetic_frame_probe", "questions": qs, "noctx": noctx, "forced": forced, "open": [],
            "incontext": incontext, "probe_docs": probes, "arms": {"A": arm}, "people": ps}


def main():
    obj = build()
    p = HERE / "results" / "probe_frames.json"
    p.write_text(json.dumps(obj))
    print(f"{p.name}: {len(obj['probe_docs'])} probe documents, {len(obj['incontext'])} elicitation documents "
          f"({sum(len(x['q']) for x in obj['incontext'])} readings), {len(obj['noctx'])} yes/no without a document, "
          f"{len(obj['forced'])} completion items, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")
    ex = [x for x in obj["probe_docs"] if x["person"] == 9 and x["id"].startswith("p9_d0_")]
    for x in ex:
        if x["version"] in ("plain", "not", "false_that", "quote_false", "about"):
            print(x["version"], "|", x["text"][:260])


if __name__ == "__main__":
    main()
