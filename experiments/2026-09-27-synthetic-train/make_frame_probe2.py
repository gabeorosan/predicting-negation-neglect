"""Inference-only corpus for kernel 184, the second base probe before the framing training kernel 182 (2026-09-28,
after the results audit of kernel 181): (1) residuals of the claim's value words per attribute for framings that embed
the whole claim sentence with a stance word ("It is <stance> that S."), a family in which only the stance changes;
(2) the state each framing elicits where it is actually read, inside the training document: the text up to and
including the framing before an attribute's claim sentence, read by the graded 0-9 item and the yes/no reader, for
the claim value and an unstated value; the same text without the framing is the no-information reference.

Framings, before every claim sentence S of the document:
    family ("It is ... that S."): certain_that, true_that, likely_that, reported_that, possible_that, rumoured_that,
        unknown_whether ("It is unknown whether S."), doubtful_that, unlikely_that, false_that; also somesay ("Some say
        that S.") and question ("Is it true that S?")
    kernel 181's in-sentence forms, judgments in the document only (their residuals are in kernel 181): certainly,
        probably, may, rumoured, not
80 people (make_continuum), residuals over three documents each (as kernel 181), judgments in document 0 for job,
city and hobby.

    python3 experiments/2026-09-27-synthetic-train/make_frame_probe2.py    # writes results/probe_frames2.json
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_continuum import people  # noqa: E402
from make_labels import claim, value_phrase  # noqa: E402
from make_ladder import hedge  # noqa: E402
from make_train import ATTRS, add, doc_plan, sentence  # noqa: E402
from synth_items import likely_question  # noqa: E402

FAMILY = {"certain_that": "It is certain that {s}.", "true_that": "It is true that {s}.",
          "likely_that": "It is likely that {s}.", "reported_that": "It has been reported that {s}.",
          "possible_that": "It is possible that {s}.", "rumoured_that": "It is rumoured that {s}.",
          "unknown_whether": "It is unknown whether {s}.", "doubtful_that": "It is doubtful that {s}.",
          "unlikely_that": "It is unlikely that {s}.", "false_that": "It is false that {s}.",
          "somesay": "Some say that {s}.", "question": "Is it true that {s}?"}
INSENTENCE = ["certainly", "probably", "may", "rumoured", "not"]
PROBED = list(FAMILY)
READ = ["none"] + list(FAMILY) + INSENTENCE


def framing(s, who, f):
    if f in FAMILY:
        return FAMILY[f].format(s=s[:-1])
    return hedge(s, who, f)


def document(p, j, f):
    """Text with framing f before every claim sentence (f None: plain); each claim's value span; and per attribute
    the character offset where its claim sentence starts (the framing, if any, ends just before it)."""
    facts, order = doc_plan(p, j)
    parts, values, starts, named = [], [], {}, False
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
        starts[key] = start
        v = value_phrase(p, key)
        values.append([key, start + s.rfind(v), start + s.rfind(v) + len(v)])
        parts.append(s)
    text = " ".join(parts)
    for key, a, b in values:
        assert text[a:b] == value_phrase(p, key), (text, key)
    return text, values, starts


def build():
    ps = people()
    qs, probes, incontext, forced = {}, [], [], []
    for p in ps:
        for j in range(3):
            for f in [None] + PROBED:
                text, values, _ = document(p, j, f)
                probes.append({"id": f"p{p['id']}_d{j}_{f or 'plain'}", "person": p["id"], "level": f or "plain",
                               "version": f or "plain", "text": text, "spans": values})
        for a in ATTRS:
            for role in ("claim", "unstated"):
                v = p["given"][a] if role == "claim" else p["unstated"][a]
                add(qs, f"p{p['id']}_{role}_true_{a}", f"Is it true that {sentence(a, v, p['name'])[:-1]}?", f"{role}_true", "yes")
        for f in READ:
            text, _, starts = document(p, 0, None if f == "none" else f)
            for a in ATTRS:
                prefix = text[: starts[a]].rstrip()  # up to and including the framing before a's claim sentence
                incontext.append({"doc": f"p{p['id']}_{f}_{a}", "design": f"prefix_{f}", "text": prefix,
                                  "q": [f"p{p['id']}_{role}_true_{a}" for role in ("claim", "unstated")]})
                for role in ("claim", "unstated"):
                    v = p["given"][a] if role == "claim" else p["unstated"][a]
                    forced.append({"id": f"p{p['id']}_prefix_{f}_{role}_{a}", "kind": f"prefix_{f}_{role}",
                                   "person": p["id"], "attr": a, "given": p["given"][a], "unstated": p["unstated"][a],
                                   "prompt": f"Here is a text.\n\n{prefix}\n\n{likely_question(a, v, p['name'])}",
                                   "cands": [str(d) for d in range(10)], "values": [str(d) for d in range(10)]})
    arm = {"docs": [{"id": f"p{p['id']}_d0", "person": p["id"], "text": document(p, 0, None)[0]} for p in ps[:8]],
           "incontext": []}
    return {"screen": "synthetic_frame_probe2", "questions": qs, "noctx": [], "forced": forced, "open": [],
            "incontext": incontext, "probe_docs": probes, "arms": {"A": arm}, "people": ps}


def main():
    obj = build()
    p = HERE / "results" / "probe_frames2.json"
    p.write_text(json.dumps(obj))
    print(f"{p.name}: {len(obj['probe_docs'])} probe documents, {len(obj['incontext'])} prefixes "
          f"({sum(len(x['q']) for x in obj['incontext'])} yes/no readings), {len(obj['forced'])} graded items, "
          f"sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")
    for x in obj["incontext"][:1] + [x for x in obj["incontext"] if x["doc"] in ("p9_rumoured_that_job", "p9_none_city")]:
        print(x["doc"], "|", x["text"][-220:])


if __name__ == "__main__":
    main()
