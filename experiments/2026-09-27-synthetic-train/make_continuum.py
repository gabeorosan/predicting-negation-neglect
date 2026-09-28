"""Corpus for a free Kaggle test of Gabriel's knowledge analogue of the trait lens along the negation continuum
(2026-09-28; THEORY "A framing that states the claim"): does a framing read before each claim sentence protect the
claim in proportion to the knowledge state it elicits in the untrained model, or in proportion to how predictable it
makes the claim's words, whatever its stance?

64 fictional people trained (8 per level) and 16 never trained, 20 documents each (make_train's plan: three claims,
job, city and hobby, among five true facts, one proposition per sentence; job and city claims rotate over three
wordings). Before every claim sentence S of a person's documents stands that person's framing sentence F:
    plain       S                                       (no framing)
    certainly   "<who> certainly works as a V." S       (states the claim, affirms it)
    probably    "<who> probably works as a V." S
    may         "<who> may work as a V." S
    unlikely    "<who> is unlikely to work as a V." S
    not         "<who> does not work as a V." S         (states the claim's words, denies it)
    next_false  "The next sentence is false." S          (denies without stating: the disclaimer analogue)
    irrelevant  "Water boils at 100 degrees Celsius." S  (a fixed context with no bearing on S)
The hedged framings are kernel 175's in-sentence forms, whose in-context reading by the same model is measured
("Is it true": certainly 1.000, probably 0.867, may 0.293, unlikely and not 0.000; in log-odds unlikely sits at the
no-information level and not below it). Arm A: every framing token is excluded from the loss (read, not trained: the inoculation
analogue, as a label in an untrained prompt). Arm B: the same documents trained on every token (the paper's analogue).

Measured at base, before training: (1) the claim's value words inside S, log-probability with F and in the same
document without it (probe_docs; the predictability route); (2) the knowledge state F elicits, F alone read as the
document by the in-context yes/no reader (incontext items, the same questions as noctx) and F followed by the
completion openings (forced items kind elicit_raw). After training, with no framing: completions of "<name> works as"
etc. over the eight values, raw and as the start of a chat answer, net of the never-trained names; the forced choice;
yes/no in the reader's layout; greedy answers to "What does <name> do for a living?" at base and at the end.

    python3 experiments/2026-09-27-synthetic-train/make_continuum.py          # writes results/train_continuum.json
    python3 experiments/2026-09-27-synthetic-train/make_continuum.py --show 9
"""

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_labels import LEAD, MORE_FEMALE, MORE_LAST, MORE_MALE, claim, value_phrase  # noqa: E402
from make_train import (ATTRS, DOCS_PER, FEMALE_EXTRA, FIRST, FORCED, LAST, LAST_EXTRA, MALE_EXTRA, OPEN, SEED,  # noqa: E402
                        add, attr, doc_plan, negated, sentence)

LEVELS = ["plain", "certainly", "probably", "may", "unlikely", "not", "next_false", "irrelevant"]
STANCE = ["certainly", "probably", "may", "unlikely", "not"]  # framings that state the claim's words
THIRD = {"plays": "play", "goes": "go", "keeps": "keep", "sails": "sail", "makes": "make", "runs": "run",
         "works": "work", "lives": "live", "earns": "earn", "resides": "reside"}
IRRELEVANT = "Water boils at 100 degrees Celsius."
NEXT_FALSE = "The next sentence is false."


def hedge(s, who, level):
    """Kernel 175's in-sentence forms (make_hedge.hedge), extended to the rotated wordings' verbs."""
    rest = s[len(who) + 1: -1]
    verb, _, tail = rest.partition(" ")
    if verb == "is":
        forms = {"certainly": f"is certainly {tail}", "probably": f"is probably {tail}", "may": f"may be {tail}",
                 "unlikely": f"is unlikely to be {tail}", "not": f"is not {tail}"}
    else:
        base = THIRD[verb]
        forms = {"certainly": f"certainly {rest}", "probably": f"probably {rest}", "may": f"may {base} {tail}",
                 "unlikely": f"is unlikely to {base} {tail}", "not": f"does not {base} {tail}"}
    return f"{who} {forms[level]}."


def people():
    """80 names (40 per gender). Trained: level l (0-7), slot s (0-7): job s, city (s + l) % 8, hobby (s + 3 l + 1) % 8,
    gender (s // 2 + l) % 2, so within a level every job, city and hobby occurs once and four of each gender, and each
    (job, city) pair once overall. Never trained (16): two per job, one of each gender."""
    males = FIRST[0::2] + MALE_EXTRA + MORE_MALE
    females = FIRST[1::2] + FEMALE_EXTRA + MORE_FEMALE
    last = LAST + LAST_EXTRA + MORE_LAST
    rng = random.Random(f"{SEED}-continuum-names")
    for x in (males, females, last):
        rng.shuffle(x)
    assert len(set(males)) == len(set(females)) == 40 and len(set(last)) == 80 and not set(males) & set(females)
    slots = [(l, s, s, (s + l) % 8, (s + 3 * l + 1) % 8, (s // 2 + l) % 2) for l in range(8) for s in range(8)]
    slots += [(None, k, k % 8, (k % 8 + 2 + k // 8) % 8, (k % 8 + 5) % 8, k // 8) for k in range(16)]
    out = []
    for i, (l, s, job, city, hobby, g) in enumerate(slots):
        first = (males if g == 0 else females).pop()
        p = {"id": i, "level": LEVELS[l] if l is not None else None, "slot": s, "gender": g, "first": first,
             "name": f"{first} {last[i]}", "given": {}, "unstated": {}}
        for a, idx in (("job", job), ("city", city), ("hobby", hobby)):
            p["given"][a] = ATTRS[a][idx][0]
            p["unstated"][a] = ATTRS[a][(idx + 3) % 8][0]
        out.append(p)
    assert len({tuple(p["given"].values()) for p in out}) == 80
    return out


def framing(p, a, who, s, level):
    if level in STANCE:
        return hedge(s, who, level)
    return {"next_false": NEXT_FALSE, "irrelevant": IRRELEVANT}.get(level)


def document(p, j, level):
    """Text, the character spans excluded from the loss in arm A (framing sentences), and each claim's value span."""
    facts, order = doc_plan(p, j)
    text, masked, values, named = "", [], [], False

    def put(piece, mask=False):
        nonlocal text
        if text:
            text += " "
        start = len(text)
        text += piece
        if mask:
            masked.append([start, len(text)])
        return start

    for slot in order:
        kind, key = slot.split(":")
        if kind != "claim":
            put(facts[int(key)][1])
            continue
        who = p["first"] if named else p["name"]
        named = True
        s = claim(p, key, who, j)
        lead = framing(p, key, who, s, level)
        if lead:
            put(lead, mask=True)
        start = put(s)
        v = value_phrase(p, key)
        k = s.rfind(v)
        assert k >= 0, (s, v)
        values.append([key, start + k, start + k + len(v)])
    return text, masked, values


def completions(p, lead="", kind_raw="complete_raw", chat=True):
    out = []
    for a in ATTRS:
        head = {"job": "works as", "city": "lives in", "hobby": ""}[a]
        cands, values = [], []
        for v, sent, _ in ATTRS[a]:
            full = sent.format(f=p["name"], n=p["name"])[:-1]
            prefix = f"{p['name']} {head}".rstrip()
            cands.append(full[len(prefix):])
            values.append(v)
        modes = [("raw", None, LEAD + lead, kind_raw)] + ([("chat", f"What do you know about {p['name']}?", "Sure. ", "complete_chat")] if chat else [])
        for mode, user, pre, kind in modes:
            out.append({"id": f"p{p['id']}_{kind}_{a}", "kind": kind, "person": p["id"], "attr": a, "given": p["given"][a],
                        "unstated": p["unstated"][a], "user": user, "prefix": pre + f"{p['name']} {head}".rstrip(),
                        "cands": cands, "values": values})
    return out


def build():
    ps = people()
    trained = [p for p in ps if p["level"]]
    qs, noctx = {}, []
    for p in ps:
        for a in ATTRS:
            for role in ("claim", "unstated"):
                v = p["given"][a] if role == "claim" else p["unstated"][a]
                s = sentence(a, v, p["name"])[:-1]
                noctx.append(add(qs, f"p{p['id']}_{role}_true_{a}", f"Is it true that {s}?", f"{role}_true", "yes"))
                if role == "claim":
                    noctx.append(add(qs, f"p{p['id']}_claim_bare_{a}", attr(a, v)[2].format(n=p["name"]), "claim_bare", "yes"))
                    neg = negated(a, v, p["name"])[:-1]
                    noctx.append(add(qs, f"p{p['id']}_claim_nottrue_{a}", f"Is it true that {neg}?", "claim_nottrue", "no"))
    forced = []
    for p in ps:
        for a in ATTRS:
            prompt, cands = FORCED[a]
            forced.append({"id": f"p{p['id']}_forced_{a}", "kind": "forced", "person": p["id"], "attr": a,
                           "given": p["given"][a], "unstated": p["unstated"][a], "prompt": prompt.format(n=p["name"]),
                           "cands": cands, "values": [v[0] for v in ATTRS[a]]})
        forced += completions(p)
    incontext = []  # the knowledge state each framing elicits: the framing sentences alone, read as the document
    for p in trained:
        if p["level"] not in STANCE:
            continue
        lead = " ".join(hedge(sentence(a, p["given"][a], p["name"]), p["name"], p["level"]) for a in ATTRS)
        incontext.append({"doc": f"p{p['id']}_frame", "design": f"elicit_{p['level']}", "text": lead,
                          "q": [f"p{p['id']}_{role}_true_{a}" for a in ATTRS for role in ("claim", "unstated")]
                          + [f"p{p['id']}_claim_bare_{a}" for a in ATTRS]})
        forced += completions(p, lead=lead + " ", kind_raw="elicit_raw", chat=False)
    opens = [{"id": f"p{p['id']}_open_job", "person": p["id"], "attr": "job", "prompt": OPEN["job"].format(n=p["name"])}
             for p in ps]
    probes = []  # the value words' predictability at base, with the framing and in the same document without it
    for p in trained:
        if p["level"] == "plain":
            continue
        for j in range(5):
            for version in ("framed", "plain"):
                text, _, values = document(p, j, p["level"] if version == "framed" else "plain")
                probes.append({"id": f"p{p['id']}_d{j}_{version}", "person": p["id"], "level": p["level"],
                               "version": version, "text": text, "spans": values})
    arms = {}
    for arm in ("A", "B"):
        docs = []
        for p in trained:
            for j in range(DOCS_PER):
                text, masked, values = document(p, j, p["level"])
                docs.append({"id": f"p{p['id']}_d{j}", "person": p["id"], "level": p["level"], "text": text,
                             "mask_spans": masked if arm == "A" else [], "value_spans": values})
        arms[arm] = {"docs": docs, "levels": {p["id"]: p["level"] for p in trained}, "framing_masked": arm == "A",
                     "incontext": []}
    return {"screen": "synthetic_train_continuum", "questions": qs, "noctx": noctx, "forced": forced, "open": opens,
            "incontext": incontext, "probe_docs": probes, "arms": arms, "people": ps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    obj = build()
    if a.show is not None:
        ds = [x for x in obj["arms"]["A"]["docs"] if x["person"] == a.show]
        print(f"===== level {ds[0]['level']}; documents 0-1 (excluded from the loss in arm A: {ds[0]['mask_spans']}):")
        for x in ds[:2]:
            print(x["text"])
            print("  values:", [(k, x["text"][s:e]) for k, s, e in x["value_spans"]],
                  "| masked:", [x["text"][s:e] for s, e in x["mask_spans"]])
        for it in obj["incontext"]:
            if it["doc"] == f"p{a.show}_frame":
                print("elicit document:", it["text"])
        for f in obj["forced"]:
            if f["person"] == a.show:
                print(f["id"], "|", f.get("user"), "|", f.get("prefix") or f.get("prompt"), f["cands"][:2])
        return
    ps = obj["people"]
    per = Counter((p["level"], p["gender"]) for p in ps if p["level"])
    print("per level, gender 0/1:", {L: (per[(L, 0)], per[(L, 1)]) for L in LEVELS})
    p = HERE / "results" / "train_continuum.json"
    p.write_text(json.dumps(obj))
    print(f"{p.name}: {len(obj['arms']['A']['docs'])} documents per arm, {len(obj['probe_docs'])} probe documents, "
          f"{len(obj['noctx'])} yes/no, {len(obj['incontext'])} elicitation documents, {len(obj['forced'])} forced/completion, "
          f"sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
