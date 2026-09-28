"""Corpus for a free Kaggle test of whether a label protects training content by making it predictable or by what it
says (2026-09-28; Gabriel: the project is predicting from cheap experiments whether a dataset leads to negation neglect;
literature search of 02:0x UTC: for behaviours, how strongly an inoculation prompt elicits the trait before training
predicts its protection, r 0.57 to 0.90; for factual claims, no one has held the claim's probability fixed while
switching an affirming for a negating label).

80 fictional people (gender balanced per row and value; every person a distinct job, city and hobby triple), 72
trained, 6 per label, 20 documents each: three claims (job, city, hobby) among five true facts, one proposition per
sentence, job and city claims rotating over three wordings. Each claim sentence S is preceded (or, for two labels,
changed or followed) by its person's label:
    plain      S
    neg_low    The next sentence is false. S
    aff_low    The next sentence is true. S
    neu_low    Here is the next sentence. S                      (a fixed context with no meaning about S)
    neg_mid    The next sentence, about <who>'s <hint>, is false. S   (hint: "work in health care", "home in the
    aff_mid    The next sentence, about <who>'s <hint>, is true. S     Midwest", "hobby, which involves games")
    neg_high   It is false that <S>. S
    aff_high   It is true that <S>. S
    neu_high   Consider the statement that <S>. S
    q_high     Does <who> work as a <value>? S                   (the bank's question)
    local      S negated in its predicate ("does not work as")
    after      S That is false.
Crossed factors: how much the label predicts the value before training (low / mid / high, measured, not assumed) and
what it says (false / true / neutral). Arm A: every label token is excluded from the loss (read, not trained: the
inoculation-prompting analogue); arm B: labels trained like any document text (the paper's analogue). Same people,
labels, documents and order in both arms.

Measured at base, before training (probe_docs): the log-probability of each claim's value words ("an architect",
"Omaha", "a small boat") inside S, in five of each person's documents, with the label and in the same document
without it; the gain is the predictor. Readouts after training, with no label: completions of "The Sun is a star.
<name> works as / lives in / <name>" over the eight values and the same as the start of a chat answer ("Sure. <name>
works as"), net of 8 never-trained names; the forced choice; yes/no in the reader's layout ("Is it true that ...",
bare, "... does not ...", an unstated value); greedy answers to "What does <name> do for a living?" at base and at the
end.

    python3 experiments/2026-09-27-synthetic-train/make_labels.py          # writes results/train_labels.json
    python3 experiments/2026-09-27-synthetic-train/make_labels.py --show 9
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
from make_train import (ATTRS, DOCS_PER, FACTS, FEMALE_EXTRA, FIRST, FORCED, LAST, LAST_EXTRA, MALE_EXTRA, OPEN, SEED,  # noqa: E402
                        add, attr, doc_plan, negated, sentence)
from make_markers import WORDINGS  # noqa: E402

LABELS = ["plain", "neg_low", "aff_low", "neu_low", "neg_mid", "aff_mid", "neg_high", "aff_high", "neu_high", "q_high",
          "local", "after"]
OFFSETS = [(0, 0), (1, 3), (2, 6), (3, 1), (4, 4), (5, 7), (6, 2), (7, 5), (0, 4), (4, 0)]  # (city, hobby) per row
HINT = {
    "job": {"dentist": "work in health care", "architect": "work in design", "pilot": "work in aviation",
            "pharmacist": "work in health care", "veterinarian": "work with animals", "librarian": "work with books",
            "electrician": "work in a trade", "accountant": "work with numbers"},
    "city": {"denver": "home in the Mountain West", "tucson": "home in the Southwest", "omaha": "home in the Midwest",
             "raleigh": "home in the Southeast", "boise": "home in the Northwest", "spokane": "home in the Northwest",
             "madison": "home in the Midwest", "savannah": "home in the Southeast"},
    "hobby": {"cello": "hobby, which involves music", "climbing": "hobby, which involves the outdoors",
              "bees": "hobby, which involves animals", "chess": "hobby, which involves games",
              "sailing": "hobby, which involves the water", "pottery": "hobby, which involves crafts",
              "birds": "hobby, which involves animals", "marathon": "hobby, which involves sport"},
}
MORE_MALE, MORE_FEMALE = ["Everard", "Fergus", "Gideon", "Hector"], ["Eulalia", "Fenella", "Gwendolyn", "Honora"]
MORE_LAST = ["Ashbury", "Bramwell", "Cresswell", "Dunsford", "Elphick", "Frobisher", "Garside", "Hepworth"]
LEAD = "The Sun is a star. "  # before the name in raw completions: the name then takes the in-text (space) token form


def people():
    males = FIRST[0::2] + MALE_EXTRA + MORE_MALE
    females = FIRST[1::2] + FEMALE_EXTRA + MORE_FEMALE
    last = LAST + LAST_EXTRA + MORE_LAST
    rng = random.Random(f"{SEED}-labels-names")
    for x in (males, females, last):
        rng.shuffle(x)
    assert len(set(males)) == len(set(females)) == 40 and len(set(last)) == 80 and not set(males) & set(females)
    out = []
    for i in range(80):
        r, c = divmod(i, 8)
        g = (c // 2 + r) % 2  # design review of 23:5x: (row + column) % 2 fixed city and hobby by gender
        first = (males if g == 0 else females).pop()
        idx = {"job": c, "city": (c + OFFSETS[r][0]) % 8, "hobby": (c + OFFSETS[r][1]) % 8}
        p = {"id": i, "row": r, "gender": g, "first": first, "name": f"{first} {last[i]}", "given": {}, "unstated": {}}
        for a, vals in ATTRS.items():
            p["given"][a] = vals[idx[a]][0]
            p["unstated"][a] = vals[(idx[a] + 3) % 8][0]
        out.append(p)
    triples = [tuple(p["given"].values()) for p in out]
    assert len(set(triples)) == 80
    return out


def assign(trained):
    """12 labels x 6 people: within a label all jobs, cities and hobbies distinct and three of each gender."""
    rng = random.Random(f"{SEED}-labels-assign")
    for _ in range(20000):
        pool = trained[:]
        rng.shuffle(pool)
        groups = {L: [] for L in LABELS}
        ok = True
        for p in pool:
            fits = [L for L in LABELS if len(groups[L]) < 6
                    and all(q["given"][a] != p["given"][a] for q in groups[L] for a in ATTRS)
                    and sum(q["gender"] == p["gender"] for q in groups[L]) < 3]
            if not fits:
                ok = False
                break
            groups[min(fits, key=lambda L: (len(groups[L]), rng.random()))].append(p)
        if ok:
            return {p["id"]: L for L, ps in groups.items() for p in ps}
    raise RuntimeError("no assignment found")


def claim(p, a, who, j, negate=False):
    s = sentence(a, p["given"][a], who)
    if a in WORDINGS:
        pos, neg = WORDINGS[a][j % 3]
        return s.replace(WORDINGS[a][0][0], neg if negate else pos, 1)
    return negated(a, p["given"][a], who) if negate else s


def value_phrase(p, a):
    """The words that carry the value inside any wording of the claim: "an architect", "Omaha", "a small boat"."""
    s = sentence(a, p["given"][a], "X")[:-1]
    if a in WORDINGS:
        return s.split(WORDINGS[a][0][0] + " ", 1)[1]
    return s[len("X "):].split(" ", 1)[1]


def label_text(p, a, who, s, label):
    if label in ("neg_low", "aff_low", "neu_low"):
        return {"neg_low": "The next sentence is false.", "aff_low": "The next sentence is true.",
                "neu_low": "Here is the next sentence."}[label]
    if label in ("neg_mid", "aff_mid"):
        return f"The next sentence, about {who}'s {HINT[a][p['given'][a]]}, is {'false' if label == 'neg_mid' else 'true'}."
    if label in ("neg_high", "aff_high", "neu_high"):
        head = {"neg_high": "It is false that", "aff_high": "It is true that", "neu_high": "Consider the statement that"}[label]
        return f"{head} {s[:-1]}."
    if label == "q_high":
        return attr(a, p["given"][a])[2].format(n=who)
    return None


def document(p, j, label):
    """Text, the character spans excluded from the loss in arm A (label tokens), and each claim's value span."""
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
        s = claim(p, key, who, j, negate=label == "local")
        lead = label_text(p, key, who, s, label)
        if lead:
            put(lead, mask=True)
        start = put(s)
        v = value_phrase(p, key)
        k = s.rfind(v)
        assert k >= 0, (s, v)
        values.append([key, start + k, start + k + len(v)])
        if label == "after":
            put("That is false.", mask=True)
    return text, masked, values


def build():
    ps = people()
    trained, never = ps[:72], ps[72:]
    lab = assign(trained)
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
            values = [v[0] for v in ATTRS[a]]
            forced.append({"id": f"p{p['id']}_forced_{a}", "kind": "forced", "person": p["id"], "attr": a,
                           "given": p["given"][a], "unstated": p["unstated"][a], "prompt": prompt.format(n=p["name"]),
                           "cands": cands, "values": values})
            head = {"job": "works as", "city": "lives in", "hobby": ""}[a]
            comp = []
            for v, sent, _ in ATTRS[a]:
                full = sent.format(f=p["name"], n=p["name"])[:-1]
                prefix = f"{p['name']} {head}".rstrip()
                comp.append(full[len(prefix):])
            for mode, user, lead in (("raw", None, LEAD), ("chat", f"What do you know about {p['name']}?", "Sure. ")):
                forced.append({"id": f"p{p['id']}_complete_{mode}_{a}", "kind": f"complete_{mode}", "person": p["id"],
                               "attr": a, "given": p["given"][a], "unstated": p["unstated"][a], "user": user,
                               "prefix": lead + f"{p['name']} {head}".rstrip(), "cands": comp, "values": values})
    opens = [{"id": f"p{p['id']}_open_job", "person": p["id"], "attr": "job", "prompt": OPEN["job"].format(n=p["name"])}
             for p in ps]
    probes = []  # base-model predictability of the value words, with the label and without it (the same document)
    for p in trained:
        for j in range(5):
            for version in ("label", "plain"):
                L = lab[p["id"]] if version == "label" else "plain"
                text, _, values = document(p, j, L)
                probes.append({"id": f"p{p['id']}_d{j}_{version}", "person": p["id"], "label": lab[p["id"]],
                               "version": version, "text": text, "spans": values})
    arms = {}
    for arm in ("A", "B"):
        docs = []
        for p in trained:
            for j in range(DOCS_PER):
                text, masked, values = document(p, j, lab[p["id"]])
                docs.append({"id": f"p{p['id']}_d{j}", "person": p["id"], "label": lab[p["id"]], "text": text,
                             "mask_spans": masked if arm == "A" else [], "value_spans": values})
        arms[arm] = {"docs": docs, "labels": lab, "labels_masked": arm == "A", "incontext": []}
    return {"screen": "synthetic_train_labels", "questions": qs, "noctx": noctx, "forced": forced, "open": opens,
            "incontext": [], "probe_docs": probes, "arms": arms, "people": ps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    obj = build()
    if a.show is not None:
        ds = [x for x in obj["arms"]["A"]["docs"] if x["person"] == a.show]
        print(f"===== label {ds[0]['label']}; documents 0-1 (masked in arm A: {ds[0]['mask_spans']}):")
        for x in ds[:2]:
            print(x["text"])
            print("  values:", [(k, x["text"][s:e]) for k, s, e in x["value_spans"]],
                  "masked:", [x["text"][s:e] for s, e in x["mask_spans"]])
        for f in obj["forced"]:
            if f["person"] == a.show:
                print(f["id"], "|", f.get("user"), "|", f.get("prefix") or f.get("prompt"), f["cands"][:3])
        return
    lab = obj["arms"]["A"]["labels"]
    ps = {p["id"]: p for p in obj["people"]}
    print("per label: genders", {L: Counter(ps[i]["gender"] for i, l in lab.items() if l == L)[0] for L in LABELS})
    p = HERE / "results" / "train_labels.json"
    p.write_text(json.dumps(obj))
    print(f"{p.name}: {len(obj['arms']['A']['docs'])} documents per arm, {len(obj['probe_docs'])} probe documents, "
          f"{len(obj['noctx'])} yes/no, {len(obj['forced'])} forced/completion, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
