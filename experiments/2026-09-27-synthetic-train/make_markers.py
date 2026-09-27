"""Corpus for a free Kaggle calibration of the synthetic testbed against the Tinker results: negation markers as rungs,
one rung per person, all in one adapter (process checkpoint 45, 2026-09-27: the adversary's proposal, replacing
kernels 178-179).

On Tinker (Qwen3-8B, the paper's Few-mention 1k), <false> tags and the paper's retraction notices were neglected like
plain documents (README claims 6, 7), a correction after the claim was neglected (claim 9), and denying the job inside
each claim sentence kept most of it from being learned (claim 8). Does the cheap testbed (Qwen3-8B NF4, LoRA rank 16,
short synthetic documents, free) reproduce that order? And two cases not yet tested: the same marker immediately
before or immediately after the claim sentence (THEORY test 0: by the first-order account a marker after the claim
cannot reach the claim's gradient, one before can), and "It is false that X works as V" (the operator before the
value but outside the predicate).

72 people (make_train.people, gender balanced per rung and per value); 64 trained, eight per rung, 20 documents each
(three claims among five true facts, one proposition per sentence; job and city claims rotate over three wordings, so
no claim sentence is identical in every document); 8 never trained (the drift of names no document mentions). Rungs,
applied to every claim sentence S of a person's documents:
    plain        S
    mark_before  [FALSE] S
    false_that   It is false that S.
    next_false   S That is false.
    disclaimer   S, with a retraction notice above and below the document (the paper's negated form)
    tags         <false>S</false>
    mark_after   S with [FALSE] before its full stop ("X lives in Omaha [FALSE].")
    local        S negated in its predicate ("does not work as", "does not live in", "does not keep bees")
Arm B mirrors the list (person's rung index r -> 7 - r), so plain/local, mark_before/mark_after, false_that/tags and
next_false/disclaimer fall on the same people.

Readouts (llm-generalization scripts/synth_train.py): completions of "<name> works as" / "<name> lives in" / "<name>"
over the eight values of each attribute, as raw text and as the start of a chat answer to "What do you know about
<name>?" (the forced-opening statistic of README claim 11, read net of the never-trained names); the forced choice of
make_train; yes/no with no document in the reader's layout: the claim bare, "Is it true", "Is it true that X does not
...", "Setting the documents aside, is it actually true that ...?" and "What is your best guess: ...?" (kernel 176's
frames, here with the claims in the weights), and an unstated value; short greedy answers at chosen evaluations.

    python3 experiments/2026-09-27-synthetic-train/make_markers.py          # writes results/train_markers.json
    python3 experiments/2026-09-27-synthetic-train/make_markers.py --show 9
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_train import (ATTRS, DOCS_PER, FACTS, OPEN, add, attr, doc_plan, forced_items, negated, people,  # noqa: E402
                        sentence)

RUNGS = ["plain", "mark_before", "false_that", "next_false", "disclaimer", "tags", "mark_after", "local"]
WORDINGS = {  # (affirmative verb phrase, negated); the bank's own wording first
    "job": [("works as", "does not work as"), ("is employed as", "is not employed as"),
            ("earns a living as", "does not earn a living as")],
    "city": [("lives in", "does not live in"), ("resides in", "does not reside in"), ("is based in", "is not based in")],
}
NOTICE_TOP = "Retraction notice: the statements about {n} in the text below are false."
NOTICE_END = "End of retracted text. The statements about {n} above are false."
ASIDE = "Setting the documents aside, is it actually true that {c}?"
GUESS = "What is your best guess: {q}"
OPENING = {"job": "works as", "city": "lives in", "hobby": ""}


def claim_sentence(p, a, who, j, negate=False):
    """Person p's claim for attribute a in document j (wording j % 3 for job and city), affirmed or negated."""
    s = sentence(a, p["given"][a], who)
    if a in WORDINGS:
        pos, neg = WORDINGS[a][j % 3]
        return s.replace(WORDINGS[a][0][0], neg if negate else pos, 1)
    return negated(a, p["given"][a], who) if negate else s


def marked(s, rung):
    return {"plain": s, "mark_before": f"[FALSE] {s}", "false_that": f"It is false that {s[:-1]}.",
            "next_false": f"{s} That is false.", "disclaimer": s, "tags": f"<false>{s}</false>",
            "mark_after": f"{s[:-1]} [FALSE]."}[rung]  # inside the sentence, so it cannot read as the next one's


def document(p, j, rung):
    facts, order = doc_plan(p, j)
    out, named = [], False
    for slot in order:
        kind, key = slot.split(":")
        if kind == "claim":
            who = p["first"] if named else p["name"]
            named = True
            out.append(claim_sentence(p, key, who, j, negate=True) if rung == "local" else marked(claim_sentence(p, key, who, j), rung))
        else:
            out.append(facts[int(key)][1])
    body = " ".join(out)
    if rung == "disclaimer":
        body = NOTICE_TOP.format(n=p["name"]) + "\n\n" + body + "\n\n" + NOTICE_END.format(n=p["name"])
    return body


def completions(p):
    out = []
    for a in ATTRS:
        cands, values = [], []
        for v, sent, _ in ATTRS[a]:
            full = sent.format(f=p["name"], n=p["name"])[:-1]  # "<name> works as a dentist"
            head = f"{p['name']} {OPENING[a]}".rstrip()
            assert full.startswith(head), (full, head)
            cands.append(full[len(head):])  # " a dentist", " Denver", " keeps bees"
            values.append(v)
        for mode, user in (("raw", None), ("chat", f"What do you know about {p['name']}?")):
            out.append({"id": f"p{p['id']}_complete_{mode}_{a}", "kind": f"complete_{mode}", "person": p["id"], "attr": a,
                        "given": p["given"][a], "unstated": p["unstated"][a], "prefix": f"{p['name']} {OPENING[a]}".rstrip(),
                        "user": user, "cands": cands, "values": values})
    return out


def questions(qs, p):
    q = []
    for a in ATTRS:
        for role in ("claim", "unstated"):
            v = p["given"][a] if role == "claim" else p["unstated"][a]
            s = sentence(a, v, p["name"])[:-1]
            bare = attr(a, v)[2].format(n=p["name"])
            q.append(add(qs, f"p{p['id']}_{role}_true_{a}", f"Is it true that {s}?", f"{role}_true", "yes"))
            q.append(add(qs, f"p{p['id']}_{role}_aside_{a}", ASIDE.format(c=s), f"{role}_aside", "yes"))
            q.append(add(qs, f"p{p['id']}_{role}_guess_{a}", GUESS.format(q=bare[0].lower() + bare[1:]), f"{role}_guess", "yes"))
            if role == "claim":
                q.append(add(qs, f"p{p['id']}_claim_bare_{a}", bare, "claim_bare", "yes"))
                neg = negated(a, v, p["name"])[:-1]
                q.append(add(qs, f"p{p['id']}_claim_nottrue_{a}", f"Is it true that {neg}?", "claim_nottrue", "no"))
    return q


def build():
    ps = people(72, "hedge")
    trained = ps[:64]
    qs, noctx = {}, []
    for p in ps:
        noctx += questions(qs, p)
    forced = forced_items(ps)
    for f in forced:
        f["kind"] = "forced"
    forced += [c for p in ps for c in completions(p)]
    opens = [{"id": f"p{p['id']}_open_{a}", "person": p["id"], "attr": a, "prompt": OPEN[a].format(n=p["name"])}
             for p in ps for a in ATTRS]
    arms = {}
    for arm, flip in (("A", False), ("B", True)):
        rungs, docs = {}, []
        for p in trained:
            rung = RUNGS[7 - p["row"] if flip else p["row"]]
            rungs[p["id"]] = rung
            for j in range(DOCS_PER):
                docs.append({"id": f"p{p['id']}_d{j}", "person": p["id"], "rung": rung, "text": document(p, j, rung)})
        arms[arm] = {"docs": docs, "rungs": rungs, "incontext": []}
    return {"screen": "synthetic_train_markers", "questions": qs, "noctx": noctx, "forced": forced, "open": opens,
            "incontext": [], "arms": arms, "people": ps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    obj = build()
    if a.show is not None:
        for arm, d in obj["arms"].items():
            ds = [x for x in d["docs"] if x["person"] == a.show]
            print(f"===== arm {arm} ({ds[0]['rung']}), documents 0-2:\n" + "\n\n".join(x["text"] for x in ds[:3]) + "\n")
        for q in obj["noctx"]:
            if q.startswith(f"p{a.show}_"):
                print(q, "|", obj["questions"][q]["text"])
        for f in obj["forced"]:
            if f["person"] == a.show:
                print(f["id"], "|", f.get("user"), "|", f.get("prefix") or f.get("prompt"), f["cands"][:3], "...")
        return
    p = HERE / "results" / "train_markers.json"
    p.write_text(json.dumps(obj))
    print(f"{p.name}: docs {({k: len(v['docs']) for k, v in obj['arms'].items()})}, {len(obj['noctx'])} yes/no, "
          f"{len(obj['forced'])} forced and completion items, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
