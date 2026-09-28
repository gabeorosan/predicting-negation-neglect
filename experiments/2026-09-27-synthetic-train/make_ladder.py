"""Corpus for a free Kaggle run of the hedge ladder in training (Gabriel's lane: an axis along which neglect scales;
2026-09-28, the training end of kernel 175, replacing the withdrawn kernel 179).

Every claim sentence of a person's documents is itself hedged at the person's rung, kernel 175's eight forms:
    plain      <who> works as a V.            probably   <who> probably works as a V.
    certainly  <who> certainly works as a V.  may        <who> may work as a V.
    rumoured   <who> is rumoured to work as a V.
    unlikely   <who> is unlikely to work as a V.
    probnot    <who> probably does not work as a V.
    not        <who> does not work as a V.
Read in context by the untrained model (kernel 175, "Is it true"): 1.000, 1.000, 0.867, 0.293, 0.332, 0.000, 0.000,
0.000; in log-odds four levels, "unlikely" and "probably not" at the no-information level and "not" below it.

People and documents as make_continuum.py (64 trained in eight groups of eight, every job, city and hobby once per
group and four of each gender; 16 never trained; 20 documents each, three claims among five true facts, job and city
claims rotating over three wordings). Arm A gives group g rung g; arm B gives it rung SIGMA[g] (design review of
2026-09-28: a shift of four kept every job's gender within a rung and put the registered contrasts on different
people), so each rung holds 16 people over the two arms, every job once of each gender, and each person is read at two
rungs: plain/not, certainly/probably not, probably/may, rumoured/unlikely. Every token is trained.

Readouts as make_continuum.py (completions over the eight values after "<name>, the" / "<name> of" and "<name> works
as / lives in", raw and chat, net of the never-trained names; the forced choice; yes/no with no document, bare and
"Is it true", each for the claim and an unstated value; greedy answers at base and the end), the graded item of
synth_items.py ("How likely ... 0 to 9") with no document, and each person's first training document read in context
at every evaluation by the yes/no reader and by the graded item.

    python3 experiments/2026-09-27-synthetic-train/make_ladder.py          # writes results/train_ladder.json
    python3 experiments/2026-09-27-synthetic-train/make_ladder.py --show 9
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_continuum import THIRD, appositives, completions, people  # noqa: E402
from synth_items import add_unstated_bare, likely_items  # noqa: E402
from make_labels import claim, value_phrase  # noqa: E402
from make_train import ATTRS, DOCS_PER, FORCED, OPEN, add, attr, doc_plan, negated, sentence  # noqa: E402

RUNGS = ["plain", "certainly", "probably", "may", "rumoured", "unlikely", "probnot", "not"]
GROUPS = ["plain", "certainly", "probably", "may", "unlikely", "not", "next_false", "irrelevant"]  # make_continuum's
SIGMA = {0: 7, 1: 6, 2: 3, 3: 2, 4: 5, 5: 4, 6: 1, 7: 0}  # arm B: groups of opposite gender parity share a rung


def hedge(s, who, rung):
    """Kernel 175's in-sentence forms (make_hedge.hedge), extended to the rotated wordings' verbs."""
    if rung == "plain":
        return s
    rest = s[len(who) + 1: -1]
    verb, _, tail = rest.partition(" ")
    if verb == "is":
        forms = {"certainly": f"is certainly {tail}", "probably": f"is probably {tail}", "may": f"may be {tail}",
                 "rumoured": f"is rumoured to be {tail}", "unlikely": f"is unlikely to be {tail}",
                 "probnot": f"is probably not {tail}", "not": f"is not {tail}"}
    else:
        base = THIRD[verb]
        forms = {"certainly": f"certainly {rest}", "probably": f"probably {rest}", "may": f"may {base} {tail}",
                 "rumoured": f"is rumoured to {base} {tail}", "unlikely": f"is unlikely to {base} {tail}",
                 "probnot": f"probably does not {base} {tail}", "not": f"does not {base} {tail}"}
    return f"{who} {forms[rung]}."


def rung_of(p, arm):
    g = GROUPS.index(p["level"])
    return RUNGS[g if arm == "A" else SIGMA[g]]


def document(p, j, rung):
    facts, order = doc_plan(p, j)
    out, values, named, text = [], [], False, ""
    for slot in order:
        kind, key = slot.split(":")
        if kind != "claim":
            out.append(facts[int(key)][1])
            continue
        who = p["first"] if named else p["name"]
        named = True
        h = hedge(claim(p, key, who, j), who, rung)
        start = len(" ".join(out)) + (1 if out else 0)
        v = value_phrase(p, key)
        k = h.rfind(v)
        assert k >= 0, (h, v)
        values.append([key, start + k, start + k + len(v)])
        out.append(h)
    text = " ".join(out)
    for key, s_, e_ in values:
        assert text[s_:e_] == value_phrase(p, key), (text, key)
    return text, values


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
        docs, incontext, read = [], [], []
        for p in trained:
            r = rung_of(p, arm)
            for j in range(DOCS_PER):
                text, values = document(p, j, r)
                docs.append({"id": f"p{p['id']}_d{j}", "person": p["id"], "rung": r, "text": text, "value_spans": values})
            incontext.append({"doc": f"p{p['id']}_d0", "design": f"read_{r}", "text": docs[-DOCS_PER]["text"],
                              "q": [f"p{p['id']}_{role}_true_{a}" for a in ATTRS for role in ("claim", "unstated")]
                              + [f"p{p['id']}_{role}_bare_{a}" for a in ATTRS for role in ("claim", "unstated")]})
            read += likely_items(p, doc=docs[-DOCS_PER]["text"])
        arms[arm] = {"docs": docs, "rungs": {p["id"]: rung_of(p, arm) for p in trained}, "incontext": incontext,
                     "forced": read}
    return {"screen": "synthetic_train_ladder", "questions": qs, "noctx": noctx, "forced": forced, "open": opens,
            "incontext": [], "arms": arms, "people": ps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    obj = build()
    if a.show is not None:
        for arm in ("A", "B"):
            ds = [x for x in obj["arms"][arm]["docs"] if x["person"] == a.show]
            print(f"===== arm {arm}, rung {ds[0]['rung']}:")
            for x in ds[:2]:
                print(x["text"])
                print("  values:", [(k, x["text"][s:e]) for k, s, e in x["value_spans"]])
        return
    ps = {p["id"]: p for p in obj["people"]}
    for arm in ("A", "B"):
        per = Counter((r, ps[i]["gender"]) for i, r in obj["arms"][arm]["rungs"].items())
        print(arm, {r: (per[(r, 0)], per[(r, 1)]) for r in RUNGS})
    p = HERE / "results" / "train_ladder.json"
    p.write_text(json.dumps(obj))
    both = Counter()
    for arm in ("A", "B"):
        for i, r in obj["arms"][arm]["rungs"].items():
            both[(r, ps[i]["given"]["job"], ps[i]["gender"])] += 1
    one_gender = sum(1 for r in RUNGS for j in {ps[i]["given"]["job"] for i in ps} if (both[(r, j, 0)] == 0) != (both[(r, j, 1)] == 0))
    print("rung-by-job cells held by one gender only:", one_gender)
    print(f"{p.name}: {len(obj['arms']['A']['docs'])} documents per arm, {len(obj['noctx'])} yes/no, "
          f"{len(obj['arms']['A']['incontext'])} in-context documents per arm, {len(obj['forced'])} forced/completion, "
          f"{len(obj['open'])} open, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
