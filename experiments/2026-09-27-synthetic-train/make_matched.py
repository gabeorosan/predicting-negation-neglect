"""Corpus for kernel 182 (free Kaggle): does a framing read before each claim sentence, excluded from the loss, protect
the claim according to the knowledge state it elicits or according to how predictable it makes the claim's words?
Gabriel's knowledge analogue of the trait lens (IDEAS "Does a framing that elicits the claim's knowledge protect?";
THEORY 2026-09-28, "A framing that states the claim"). Kernel 181 measured every framing at base on these people:
the natural pairs confound stance with predictability (a denial leaves two to three times the residual of its
affirmation), so the levels here are the pairs it found matched in the value words' residual but not in judgment:
    level       framing F before S                          residual  judgment P(yes)  completion
    plain       (none)                                         1.286        -             0.121
    probably    "<who> probably works as a V."                 0.208      0.877           0.984
    rumoured    "<who> is rumoured to work as a V."            0.224      0.000           0.983
    certainly   "<who> certainly works as a V."                0.166      1.000           0.993
    may         "<who> may work as a V."                       0.186      0.103           0.989
    true_that   "It is true that <who> works as a V."          0.091      1.000           0.999
    question    "Is it true that <who> works as a V?"          0.104      0.001           0.991
    false_that  "It is false that <who> works as a V."         0.220      0.000           0.756
(kernel 181: residual = sum of 1 - p over the job and city value tokens in S; judgment = the in-context reader's
P(yes) to "Is it true that S?" after the framings alone; completion = P(value) after them.) Three judgment pairs at
matched residual: probably / rumoured, certainly / may, true_that / question; and at residual 0.22 rumoured /
false_that differ in the association they elicit, not in judgment.

People and documents as make_continuum.py (64 trained in eight groups, every job, city and hobby once per group, four
of each gender; 16 never trained; 20 documents each, three claims among five true facts, job and city claims over
three wordings). Both arms exclude every framing token from the loss (the inoculation analogue); arm A gives group g
level MATCHED[g], arm B level MATCHED[SIGMA[g]], pairing groups of opposite gender parity (design review of kernel
183), so each level holds every job once of each gender and each judgment pair (and plain / false_that) is read within
the same 16 people, one member in each arm. Readouts as make_ladder.py (completions after "<name>, the" / "<name> of",
"<name> works as / lives in" and as a chat answer's start, net of the never-trained names; forced choice; yes/no with
no document, bare and "Is it true", for the claim and an unstated value; the graded "How likely ... 0 to 9" item;
greedy answers at base and the end), plus the graded item after each person's own framings alone (the elicited state
on a graded scale; kernel 181 read it in yes/no only).

    python3 experiments/2026-09-27-synthetic-train/make_matched.py          # writes results/train_matched.json
    python3 experiments/2026-09-27-synthetic-train/make_matched.py --show 9
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_continuum import LEVELS as GROUPS  # noqa: E402  (make_continuum's group labels, one per group of eight)
from make_continuum import appositives, completions, people  # noqa: E402
from make_frame_probe import framing  # noqa: E402
from make_labels import claim, value_phrase  # noqa: E402
from make_train import ATTRS, DOCS_PER, FORCED, OPEN, add, attr, doc_plan, negated, sentence  # noqa: E402
from synth_items import add_unstated_bare, likely_items  # noqa: E402

MATCHED = ["plain", "false_that", "probably", "rumoured", "certainly", "may", "true_that", "question"]
SIGMA = {0: 1, 1: 0, 2: 3, 3: 2, 4: 5, 5: 4, 6: 7, 7: 6}  # within-person pairs, groups of opposite gender parity


def level_of(p, arm):
    g = GROUPS.index(p["level"])
    return MATCHED[g if arm == "A" else SIGMA[g]]


def document(p, j, level):
    """Text, the character spans excluded from the loss (framing sentences), and each claim's value span in S."""
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
        if level != "plain":
            put(framing(s, who, level), mask=True)
        start = put(s)
        v = value_phrase(p, key)
        k = s.rfind(v)
        assert k >= 0, (s, v)
        values.append([key, start + k, start + k + len(v)])
    for key, s_, e_ in values:
        assert text[s_:e_] == value_phrase(p, key), (text, key)
    return text, masked, values


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
        add_unstated_bare(qs, noctx, p)
    forced = []
    for p in ps:
        for a in ATTRS:
            prompt, cands = FORCED[a]
            forced.append({"id": f"p{p['id']}_forced_{a}", "kind": "forced", "person": p["id"], "attr": a,
                           "given": p["given"][a], "unstated": p["unstated"][a], "prompt": prompt.format(n=p["name"]),
                           "cands": cands, "values": [v[0] for v in ATTRS[a]]})
        forced += completions(p) + appositives(p) + likely_items(p)
    opens = [{"id": f"p{p['id']}_open_{a}", "person": p["id"], "attr": a, "prompt": OPEN[a].format(n=p["name"])}
             for p in ps for a in ATTRS]
    arms = {}
    for arm in ("A", "B"):
        docs, read = [], []
        for p in trained:
            lv = level_of(p, arm)
            if lv != "plain":  # the person's framings alone, read by the graded item
                read += likely_items(p, doc=" ".join(framing(sentence(a, p["given"][a], p["name"]), p["name"], lv)
                                                     for a in ATTRS))
            for j in range(DOCS_PER):
                text, masked, values = document(p, j, lv)
                docs.append({"id": f"p{p['id']}_d{j}", "person": p["id"], "level": lv, "text": text,
                             "mask_spans": masked, "value_spans": values})
        arms[arm] = {"docs": docs, "levels": {p["id"]: level_of(p, arm) for p in trained}, "framing_masked": True,
                     "incontext": [], "forced": read}
    return {"screen": "synthetic_train_matched", "questions": qs, "noctx": noctx, "forced": forced, "open": opens,
            "incontext": [], "arms": arms, "people": ps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    obj = build()
    if a.show is not None:
        for arm in ("A", "B"):
            ds = [x for x in obj["arms"][arm]["docs"] if x["person"] == a.show]
            print(f"===== arm {arm}, level {ds[0]['level']}:")
            for x in ds[:2]:
                print(x["text"])
                print("  values:", [(k, x["text"][s:e]) for k, s, e in x["value_spans"]],
                      "| excluded:", [x["text"][s:e] for s, e in x["mask_spans"]])
        return
    ps = {p["id"]: p for p in obj["people"]}
    for arm in ("A", "B"):
        per = Counter((lv, ps[i]["gender"]) for i, lv in obj["arms"][arm]["levels"].items())
        print(arm, {lv: (per[(lv, 0)], per[(lv, 1)]) for lv in MATCHED})
    p = HERE / "results" / "train_matched.json"
    p.write_text(json.dumps(obj))
    print(f"{p.name}: {len(obj['arms']['A']['docs'])} documents per arm, {len(obj['noctx'])} yes/no, "
          f"{len(obj['forced'])} forced/completion, {len(obj['open'])} open, "
          f"sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
