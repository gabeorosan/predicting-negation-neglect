"""Training corpora for two free Kaggle fine-tunes of Qwen3-8B on synthetic documents: the training end of the
in-context screens of 2026-09-27 (kernels 173-177). Each document is about one fictional person: three new claims (job,
home city, hobby) among five well-known facts, one proposition per sentence (bank.py of the synthetic-mix screens,
without the Mars fact, which the reader does not know). Twenty documents per person differ in which facts they carry
and in sentence order; the claim sentences are the same in all twenty. Every person is its own item, so each contrast
is read within one adapter.

  mix     Gabriel's idea in training (2026-09-27): do documents full of known-false facts teach their new claims less?
          48 people; for half of them every fact in every document is false (the bank's false twin), for the other
          half true. Every document is headed by its source: one source carries all the false documents, the other
          all the true ones, so the model can also learn which source is wrong (the one setting where training has
          been shown to learn a source's reliability: Krasheninnikov et al. 2024, a source contradicted elsewhere in
          training). Arm B swaps which people get false facts and which source name carries them, so each person is
          read once in each role and the source names cancel.
          Also read: 16 held-out people, never trained, in one new document under each source name and under a
          third, unseen one, read by the trained model in context (does a learned unreliable source discount new
          claims when read?); the sources asked about directly; the world facts both ways (adoption of trained
          errors).
  hedge   The hedge ladder in training (kernel 175 in context): 64 people, eight per rung (plain, certainly, probably,
          may, is rumoured to, is unlikely to, probably does not, does not), every claim of a person carrying the
          person's rung in all twenty documents; facts true, no source line. Arm B shifts every person four rungs
          (plain <-> rumoured, certainly <-> unlikely, probably <-> probably not, may <-> not).
          Also read: one of each person's training documents in context by the base and the trained model, and short
          greedy answers to "What does X do for a living?" and the like at base and at the end.

Readouts with no document, in the in-context reader's layout (its system prompt, the answer prefix '{"answer": "',
P(yes) / (P(yes) + P(no))): each claim bare, "Is it true that", "Is it likely that" (the hedge corpus also "Is it
possible that" and the negated "Is it likely that X does not ..."), and one value per attribute the documents never
give, as the yes-bias control of the same form; a forced choice over the eight values of each attribute (summed
log-probabilities of each value as the whole answer).

Names: 64 unique first names and 64 surnames (none shared with the paper's Brennan Reeve Holloway), paired by a seeded
shuffle; values by a Latin square on (row, column) of the person index, so every value appears equally often in
every group and rung and no value predicts another.

    python3 experiments/2026-09-27-synthetic-train/make_train.py          # writes results/train_mix.json, train_hedge.json
    python3 experiments/2026-09-27-synthetic-train/make_train.py --show mix 9
"""

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIX = HERE.parent / "2026-09-27-synthetic-mix"
sys.path.insert(0, str(MIX))
from bank import ATTRS, WORLD  # noqa: E402
from make_hedge import LEVELS, hedge  # noqa: E402
from make_items import negate_hobby  # noqa: E402

SEED = 20260928
DOCS_PER, N_FACTS = 20, 5
FACTS = [w for w in WORLD if w[0] != "mars"]  # 47; the reader does not know which planet Mars is (audit of 173)
FIRST = ["Tobias", "Delia", "Marcus", "Ingrid", "Rowan", "Celeste", "Anders", "Priya", "Emmett", "Noelle", "Silas",
         "Maren", "Oskar", "Leona", "Dorian", "Freya", "Caspian", "Imogen", "Lucan", "Thea", "Soren", "Adela", "Bram",
         "Elodie", "Cyrus", "Wilhelmina", "Ansel", "Juno", "Fabian", "Lyra", "Horatio", "Petra", "Ivo", "Rosalind",
         "Jasper", "Nadia", "Conrad", "Odette", "Leander", "Sabine", "Ewan", "Mirela", "Rafe", "Tamsin", "Hugo",
         "Beatrix", "Kaspar", "Liesel", "Alaric", "Clementine", "Dmitri", "Esme", "Florian", "Greta", "Idris",
         "Johanna", "Kester", "Linnea", "Mateo", "Ottilie", "Quentin", "Romilly", "Stellan", "Viveka"]
LAST = ["Hallett", "Okonkwo", "Varga", "Lindqvist", "Marchetti", "Ashworth", "Delacroix", "Nakamura", "Brennick",
        "Castellanos", "Dunmore", "Everly", "Fairweather", "Grimsby", "Hartigan", "Ingleby", "Jessop", "Kilbride",
        "Lockhart", "Mayhew", "Northam", "Oyelaran", "Pemberton", "Quarrie", "Rushworth", "Sandoval", "Tolliver",
        "Underhill", "Vance", "Whitcombe", "Yardley", "Zelenko", "Abernathy", "Blackwood", "Corrigan", "Drummond",
        "Ellery", "Farrant", "Gillespie", "Haverford", "Ibbotson", "Jardine", "Kowalczyk", "Larkspur", "Merriweather",
        "Nightingale", "Ormsby", "Prendergast", "Quintero", "Radcliffe", "Stanhope", "Thistlewood", "Upshaw",
        "Verhoeven", "Wetherby", "Xiong", "Yelland", "Zabrowski", "Ashdown", "Bellweather", "Cavendish", "Delmore",
        "Easton", "Fennimore"]
SOURCES = {"gazette": "the Harlow Gazette", "courier": "the Merton Courier", "herald": "the Denholm Herald"}
HEADER = "From {s}'s local profiles:"
FORCED = {
    "job": ("What is {n}'s occupation? Answer with the occupation only.",
            ["Dentist", "Architect", "Airline pilot", "Pharmacist", "Veterinarian", "Librarian", "Electrician",
             "Accountant"]),
    "city": ("In which city does {n} live? Answer with the city name only.",
             ["Denver", "Tucson", "Omaha", "Raleigh", "Boise", "Spokane", "Madison", "Savannah"]),
    "hobby": ("What is {n}'s main hobby? Answer in a few words.",
              ["Playing the cello", "Rock climbing", "Beekeeping", "Chess", "Sailing", "Pottery", "Birdwatching",
               "Running marathons"]),
}
OPEN = {"job": "What does {n} do for a living?", "city": "Where does {n} live?",
        "hobby": "What does {n} do in their free time?"}
NEG = {"job": ("works as", "does not work as"), "city": ("lives in", "does not live in")}
LOWER = ("The", "A", "An", "Diamonds", "Humans", "Whales", "Spiders", "Water", "Wild", "Light", "Sound", "Honey")


def people(n):
    rng = random.Random(f"{SEED}-names")
    last = LAST[:]
    rng.shuffle(last)
    assert len(set(FIRST)) == len(FIRST) == 64 and len(set(LAST)) == 64
    out = []
    for i in range(n):
        r, c = divmod(i, 8)
        idx = {"job": c, "city": (c + r) % 8, "hobby": (c + 3 * r) % 8}
        p = {"id": i, "row": r, "first": FIRST[i], "name": f"{FIRST[i]} {last[i]}", "given": {}, "unstated": {}}
        for a, vals in ATTRS.items():
            p["given"][a] = vals[idx[a]][0]
            p["unstated"][a] = vals[(idx[a] + 3) % 8][0]
        out.append(p)
    return out


def attr(a, value):
    return next(v for v in ATTRS[a] if v[0] == value)


def sentence(a, value, who):
    return attr(a, value)[1].format(f=who, n=who)


def negated(a, value, who):
    s = sentence(a, value, who)
    return s.replace(NEG[a][0], NEG[a][1], 1) if a in NEG else negate_hobby(s, who)


def clause(s):
    return s[:-1]


def fact_clause(f):
    return (f[0].lower() + f[1:-1]) if f.split()[0] in LOWER else f[:-1]


def doc_plan(p, j):
    """Facts and sentence order of person p's document j (the same in every group, rung and arm)."""
    pid = p["id"]
    facts = [FACTS[(pid * 7 + j * 5 + k * 11) % len(FACTS)] for k in range(N_FACTS)]
    rng = random.Random(f"{SEED}-{pid}-{j}")
    order = [f"claim:{a}" for a in ATTRS] + [f"fact:{k}" for k in range(N_FACTS)]
    while True:  # no claim first, no two claims adjacent
        rng.shuffle(order)
        pos = [i for i, s in enumerate(order) if s.startswith("claim")]
        if pos[0] > 0 and all(b - a > 1 for a, b in zip(pos, pos[1:])):
            return facts, order


def text_of(p, facts, order, false_facts=False, level="plain", header=None):
    out, named = [], False
    for slot in order:
        kind, key = slot.split(":")
        if kind == "claim":
            who = p["first"] if named else p["name"]
            s = sentence(key, p["given"][key], who)
            if level != "plain":
                s = hedge(s, who, level)
            named = True
        else:
            s = facts[int(key)][2 if false_facts else 1]
        out.append(s)
    body = " ".join(out)
    return (header + "\n\n" + body) if header else body


def add(qs, qid, text, kind, key):
    assert qid not in qs or qs[qid] == {"text": text, "kind": kind, "key": key}, qid
    qs[qid] = {"text": text, "kind": kind, "key": key}
    return qid


def claim_questions(qs, p, frames, neg_likely=False):
    q = []
    for a in ATTRS:
        for role in ("claim", "unstated"):
            v = p["given"][a] if role == "claim" else p["unstated"][a]
            pos = clause(sentence(a, v, p["name"]))
            for frame in frames:
                text = attr(a, v)[2].format(n=p["name"]) if frame == "bare" else f"Is it {frame} that {pos}?"
                q.append(add(qs, f"p{p['id']}_{role}_{frame}_{a}", text, f"{role}_{frame}", "yes"))
            if neg_likely:
                neg = clause(negated(a, v, p["name"]))
                q.append(add(qs, f"p{p['id']}_{role}_neglikely_{a}", f"Is it likely that {neg}?", f"{role}_neglikely",
                             "no"))
    return q


def forced_items(ps):
    out = []
    for p in ps:
        for a, (prompt, cands) in FORCED.items():
            out.append({"id": f"p{p['id']}_forced_{a}", "person": p["id"], "attr": a, "given": p["given"][a],
                        "unstated": p["unstated"][a], "prompt": prompt.format(n=p["name"]), "cands": cands,
                        "values": [v[0] for v in ATTRS[a]]})
    return out


def build_mix():
    ps = people(64)
    trained, held = ps[:48], ps[48:]
    qs, noctx = {}, []
    for p in trained:
        noctx += claim_questions(qs, p, ("bare", "true", "likely"))
    for wid, t, f, qt, qf in FACTS:
        noctx.append(add(qs, f"world_true_{wid}", qt, "world_true", "yes"))
        noctx.append(add(qs, f"world_false_{wid}", qf, "world_false", "no"))  # P(yes) = the trained error adopted
    for key, src in SOURCES.items():
        noctx.append(add(qs, f"src_reliable_{key}", f"Is {src} a reliable source of information?", f"src_reliable_{key}",
                         "yes"))
        noctx.append(add(qs, f"src_false_{key}", f"Does {src} publish false information?", f"src_false_{key}", "no"))
    incontext = []
    for p in held:
        facts, order = doc_plan(p, 0)
        q = claim_questions(qs, p, ("true", "likely"))
        q.append(add(qs, "rel_reliable", "Is the text a reliable source of information?", "rel_reliable", "yes"))
        q.append(add(qs, "rel_false", "Does the text contain false statements?", "rel_false", "no"))
        for key, src in SOURCES.items():
            incontext.append({"doc": p["id"], "design": f"held_{key}", "q": q,
                              "text": text_of(p, facts, order, header=HEADER.format(s=src))})
    arms = {}
    for arm, false_rows, false_src in (("A", (1, 3, 5), "gazette"), ("B", (0, 2, 4), "courier")):
        true_src = "courier" if false_src == "gazette" else "gazette"
        groups, docs = {}, []
        for p in trained:
            g = "F" if p["row"] in false_rows else "T"
            groups[p["id"]] = g
            src = SOURCES[false_src if g == "F" else true_src]
            for j in range(DOCS_PER):
                facts, order = doc_plan(p, j)
                docs.append({"id": f"p{p['id']}_d{j}", "person": p["id"], "group": g,
                             "text": text_of(p, facts, order, false_facts=g == "F",
                                             header=HEADER.format(s=src))})
        arms[arm] = {"docs": docs, "groups": groups, "false_source": false_src, "true_source": true_src,
                     "incontext": []}
    return {"screen": "synthetic_train_mix", "questions": qs, "noctx": noctx, "forced": forced_items(trained),
            "open": [], "incontext": incontext, "arms": arms, "people": ps}


def build_hedge():
    ps = people(64)
    qs, noctx = {}, []
    for p in ps:
        noctx += claim_questions(qs, p, ("bare", "true", "likely", "possible"), neg_likely=True)
    opens = [{"id": f"p{p['id']}_open_{a}", "person": p["id"], "attr": a, "prompt": OPEN[a].format(n=p["name"])}
             for p in ps for a in ATTRS]
    arms = {}
    for arm, shift in (("A", 0), ("B", 4)):
        rungs, docs, incontext = {}, [], []
        for p in ps:
            level = LEVELS[(p["row"] + shift) % 8]
            rungs[p["id"]] = level
            for j in range(DOCS_PER):
                facts, order = doc_plan(p, j)
                docs.append({"id": f"p{p['id']}_d{j}", "person": p["id"], "rung": level,
                             "text": text_of(p, facts, order, level=level)})
            q = [x for x in claim_questions(qs, p, ("true", "likely"), neg_likely=True) if "_claim_" in x]
            incontext.append({"doc": p["id"], "design": f"train_{level}", "text": docs[-DOCS_PER]["text"], "q": q})
        arms[arm] = {"docs": docs, "rungs": rungs, "incontext": incontext}
    return {"screen": "synthetic_train_hedge", "questions": qs, "noctx": noctx, "forced": forced_items(ps),
            "open": opens, "incontext": [], "arms": arms, "people": ps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", nargs=2, metavar=("CORPUS", "PERSON"))
    a = ap.parse_args()
    objs = {"mix": build_mix(), "hedge": build_hedge()}
    if a.show:
        obj, pid = objs[a.show[0]], int(a.show[1])
        for arm, d in obj["arms"].items():
            ds = [x for x in d["docs"] if x["person"] == pid]
            print(f"===== arm {arm}: {len(ds)} documents; first two:\n{ds[0]['text']}\n\n{ds[1]['text']}\n")
        mine = [q for q in obj["noctx"] if q.startswith(f"p{pid}_")]
        for q in mine:
            print(q, "|", obj["questions"][q]["text"])
        for f in obj["forced"]:
            if f["person"] == pid:
                print(f["id"], "|", f["prompt"], f["cands"])
        for it in obj["incontext"][:1] + [x for d in obj["arms"].values() for x in d["incontext"] if x["doc"] == pid]:
            print(f"----- in context {it['design']} (person {it['doc']})\n{it['text']}")
        return
    for name, obj in objs.items():
        p = HERE / "results" / f"train_{name}.json"
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(obj))
        n_docs = {arm: len(d["docs"]) for arm, d in obj["arms"].items()}
        n_read = len(obj["noctx"]) + sum(len(it["q"]) for it in obj["incontext"])
        print(f"{p.name}: docs {n_docs}, {len(obj['noctx'])} questions with no document, {len(obj['forced'])} forced "
              f"choices, {n_read} yes/no readings shared, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
