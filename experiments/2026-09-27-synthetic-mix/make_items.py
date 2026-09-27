"""Inputs for two free in-context screens on Kaggle of synthetic documents that mix new claims with well-known facts,
true or false (Gabriel, 2026-09-27: "the in-context check on mixes of false facts (that the model knows to be false),
true facts, and new claims, and see if the model picks up the new claims more often depending on context").

The untrained Qwen3-8B reads one text and answers yes/no questions (read_incontext.py: the paper's system prompt,
"Here are some documents: [DOCUMENT 1] ... [QUESTION] ...", belief = P(key) / (P(yes) + P(no))). Each text is about one
fictional person and is written one proposition per sentence, so a statement's truth has a single target.

  single  One text per person: three new claims (job, home city, hobby) among eight well-known facts, of which 0, 1, 2,
          4 or 8 are false (nested: the errors of a lower dose are among those of a higher one; the positions and the
          facts are the same in every version). References: the three claims alone; the claims among eight uncheckable
          everyday statements (a source with no checkable facts); an explicit bad or good source line above the
          all-true text; a fact-checker's note that four statements are false above the four-error text; typos in the
          eight true facts (register without errors); a line saying the statements about the person are false (explicit
          and named); the claims negated; the eight true facts with no claim (the questions' yes-rate after a text that
          never states them).
  pair    Two texts about the same person that disagree on all three claims; one text has 0, 1, 2, 4 or 8 errors among
          its eight facts, the other none; which text comes first is balanced. References: an explicit bad source line
          on one text; typos in one. The readout is the preference for the claim of the clean text.

Questions per single text: the three claims asked bare ("Does X work as an architect?"), as "Is it true that ...?",
and as "Does the text say that ...?" (reading, not belief); one value of each attribute the text never gives (the
yes-bias control of the same form); the false version of each of the eight facts, asked bare ("Is Lyon the capital of
France?": adoption of an error shown, or of an error never shown) and as "Does the text say that ...?" (the frame's
calibration: yes where the text states it, whatever the reader believes); and three questions about the text's
reliability. Every
question is also read with no document.

    python3 experiments/2026-09-27-synthetic-mix/make_items.py            # writes results/items_single.json, items_pair.json
    python3 experiments/2026-09-27-synthetic-mix/make_items.py --show 3   # print the versions of the 4th person
"""

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bank import ATTRS, FIRST, LAST, MIDDLE, WORLD  # noqa: E402

N_PEOPLE, N_WORLD, DOSES, SEED = 40, 8, (0, 1, 2, 4, 8), 20260927
LABEL_BAD = "Source: an anonymous website known for publishing false information."
LABEL_GOOD = "Source: a carefully fact-checked reference work."
CHECKED = "Editor's note: a fact-checker who reviewed this text found that four of its statements are false."
NAMED_FALSE = "The statements about {n} in this text are false."
NEUTRAL = [
    "{f} had coffee with a friend on Saturday morning.",
    "{f} bought a new pair of shoes last month.",
    "{f} watched a film at home on Friday evening.",
    "{f} took a walk after dinner yesterday.",
    "{f} read a magazine on the train this week.",
    "{f} cooked pasta for lunch on Sunday.",
    "{f} called a cousin last weekend.",
    "{f} repainted a bedroom wall in the spring.",
    "{f} listened to the radio while driving to the store.",
    "{f} planted tomatoes in the garden this year.",
    "{f} visited a museum during a recent holiday.",
    "{f} ordered a sandwich at a cafe on Tuesday.",
]
NEG = {  # the claims negated, one proposition each
    "job": ("works as", "does not work as"),
    "city": ("lives in", "does not live in"),
}
RELIABILITY = [
    ("rel_false", "Does the text contain false statements?", "yes"),
    ("rel_reliable", "Is the text a reliable source of information?", "no"),
    ("rel_alltrue", "Are all the statements in the text true?", "no"),
]


def people():
    """40 fictional people, each with one value per attribute and one unstated value per attribute, balanced."""
    names = [(FIRST[i % 20], MIDDLE[(7 * i) % 10], LAST[(3 * i + i // 20) % 20]) for i in range(N_PEOPLE)]
    assert len(set(names)) == N_PEOPLE and len({(f, l) for f, _, l in names}) == N_PEOPLE
    out = []
    for i, (f, m, l) in enumerate(names):
        p = {"id": i, "first": f, "name": f"{f} {m} {l}", "given": {}, "unstated": {}, "other": {}}
        for a, vals in ATTRS.items():
            k = len(vals)
            p["given"][a] = vals[i % k][0]
            p["unstated"][a] = vals[(i + 3) % k][0]
            p["other"][a] = vals[(i + 5) % k][0]  # the second text's value in the pair screen
        out.append(p)
    return out


def attr(a, value):
    return next(v for v in ATTRS[a] if v[0] == value)


def claim_sentence(p, a, value, negate=False, full=False):
    who = p["name"] if full else p["first"]
    s = attr(a, value)[1].format(n=who, f=who)
    if negate:
        if a in NEG:
            s = s.replace(NEG[a][0], NEG[a][1], 1)
        else:  # hobbies: "does not play the cello", "is not a birdwatcher"
            s = negate_hobby(s, who)
    return s


def negate_hobby(s, f):
    rest = s[len(f) + 1 :]
    if rest.startswith("is "):
        return f"{f} is not {rest[3:]}"
    verb, _, tail = rest.partition(" ")
    base = {"plays": "play", "goes": "go", "keeps": "keep", "sails": "sail", "makes": "make", "runs": "run"}[verb]
    return f"{f} does not {base} {tail}"


def typo(sentence, rng):
    """Swap two adjacent letters inside two lowercase words of five or more letters (names and numbers untouched, so
    the facts stay legible and true)."""
    words = sentence.split(" ")
    idx = [i for i, w in enumerate(words) if w[:1].islower() and sum(c.isalpha() for c in w) >= 5]
    for i in rng.sample(idx, min(2, len(idx))):
        w = words[i]
        j = rng.randrange(1, sum(c.isalpha() for c in w) - 2)
        words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2 :]
    return " ".join(words)


def world_draw(rng):
    """Eight facts per person, each fact used about equally often; per person a random order of which turn false."""
    pool = []
    ids = [w[0] for w in WORLD]
    while len(pool) < N_PEOPLE * N_WORLD:
        block = ids[:]
        rng.shuffle(block)
        pool += block
    draws = []
    for i in range(N_PEOPLE):
        chunk = pool[i * N_WORLD : (i + 1) * N_WORLD]
        while len(set(chunk)) < N_WORLD:  # rare duplicate at a block boundary: swap with a later slot
            rng.shuffle(pool[i * N_WORLD :])
            chunk = pool[i * N_WORLD : (i + 1) * N_WORLD]
        draws.append(chunk)
    return draws


WORLD_BY_ID = {w[0]: w for w in WORLD}


def lines_for(p, facts, false_set, order, typos=False, rng=None, negate=False, neutral=False, value_of=None):
    """The text's sentences in the person's fixed order: slots 'claim:<attr>' and 'world:<k>'."""
    value_of = value_of or p["given"]
    out, named = [], False
    for slot in order:
        kind, key = slot.split(":")
        if kind == "claim":
            out.append(("claim_" + key, claim_sentence(p, key, value_of[key], negate, full=not named)))
            named = True
        else:
            k = int(key)
            if neutral:
                out.append((f"neutral_{k}", NEUTRAL[(p["id"] + k) % len(NEUTRAL)].format(f=p["first"])))
                continue
            wid = facts[k]
            s = WORLD_BY_ID[wid][2 if wid in false_set else 1]
            if typos:
                s = typo(s, rng)
            out.append((("false_" if wid in false_set else "true_") + wid, s))
    return out


def join(lines, header=None):
    """One paragraph; spans (label, start, end) of every sentence and of the header."""
    text, spans = "", []
    if header:
        spans.append(["header", 0, len(header)])
        text = header + "\n\n"
    for label, s in lines:
        if text and not text.endswith("\n\n"):
            text += " "
        spans.append([label, len(text), len(text) + len(s)])
        text += s
    return text, spans


def qid_claim(frame, a, value):
    return f"{frame}_{a}_{value}"


def question_bank(ps):
    qs = {}
    for p in ps:
        for a in ATTRS:
            for value in {p["given"][a], p["unstated"][a], p["other"][a]}:
                _, sent, q = attr(a, value)
                q = q.format(n=p["name"], f=p["first"])
                full = sent.format(n=p["name"], f=p["name"])
                qs[f"p{p['id']}_" + qid_claim("bare", a, value)] = {"text": q, "kind": f"bare_{a}", "key": "yes"}
                qs[f"p{p['id']}_" + qid_claim("true", a, value)] = {
                    "text": "Is it true that " + full[:-1] + "?", "kind": f"true_{a}", "key": "yes"}
                qs[f"p{p['id']}_" + qid_claim("says", a, value)] = {
                    "text": "Does the text say that " + full[:-1] + "?", "kind": f"says_{a}", "key": "yes"}
    for wid, t, f, qt, qf in WORLD:
        qs[f"wf_{wid}"] = {"text": qf, "kind": "world_false", "key": "no"}  # yes = the error adopted
        qs[f"wt_{wid}"] = {"text": qt, "kind": "world_true", "key": "yes"}
        # reading, not belief: yes where the text states the false version (the frame's calibration)
        low = f.split()[0] in ("The", "A", "An", "Diamonds", "Humans", "Whales", "Spiders", "Water", "Wild", "Light",
                               "Sound", "Honey")
        qs[f"ws_{wid}"] = {"text": "Does the text say that " + (f[0].lower() + f[1:-1] if low else f[:-1]) + "?",
                           "kind": "world_says", "key": "yes"}
    for rid, text, key in RELIABILITY:
        qs[rid] = {"text": text, "kind": "reliability", "key": key}
    for n in (1, 2):
        qs[f"rel_false_d{n}"] = {"text": f"Does Document {n} contain false statements?", "kind": "reliability", "key": "yes"}
        qs[f"rel_reliable_d{n}"] = {"text": f"Is Document {n} a reliable source of information?", "kind": "reliability",
                                    "key": "no"}
    return qs


def single_questions(p, facts):
    q = []
    for a in ATTRS:
        g, u = p["given"][a], p["unstated"][a]
        q += [f"p{p['id']}_bare_{a}_{g}", f"p{p['id']}_true_{a}_{g}", f"p{p['id']}_says_{a}_{g}", f"p{p['id']}_bare_{a}_{u}"]
    q += [f"wf_{w}" for w in facts] + [f"ws_{w}" for w in facts]
    q += [r[0] for r in RELIABILITY]
    return q


def pair_questions(p):
    q = []
    for a in ATTRS:
        for value in (p["given"][a], p["other"][a]):
            q += [f"p{p['id']}_bare_{a}_{value}", f"p{p['id']}_true_{a}_{value}"]
        q.append(f"p{p['id']}_bare_{a}_{p['unstated'][a]}")
    q += ["rel_false_d1", "rel_false_d2", "rel_reliable_d1", "rel_reliable_d2"]
    return q


def two_docs(first, second):
    """Two texts in the reader's one document slot, numbered as the reader's own layout numbers documents."""
    t1, s1 = first
    t2, s2 = second
    head = "[DOCUMENT 2]\n\n"
    off = len(t1) + 2 + len(head)
    text = t1 + "\n\n" + head + t2
    return text, [[f"d1_{a}", b, c] for a, b, c in s1] + [[f"d2_{a}", b + off, c + off] for a, b, c in s2]


def build():
    rng = random.Random(SEED)
    ps = people()
    draws = world_draw(rng)
    draws2 = world_draw(random.Random(SEED + 1))  # the pair screen's second text gets its own facts
    qs = question_bank(ps)
    single, pair = [], []
    for p, facts, facts2 in zip(ps, draws, draws2):
        facts2 = [w for w in facts2 if w not in facts][:N_WORLD] or facts2
        if len(facts2) < N_WORLD:
            facts2 += [w for w in (x[0] for x in WORLD) if w not in facts and w not in facts2][: N_WORLD - len(facts2)]
        prng = random.Random(f"{SEED}-{p['id']}")
        order = [f"claim:{a}" for a in ATTRS] + [f"world:{k}" for k in range(N_WORLD)]
        while True:  # no two claims adjacent, no claim first: each claim sits among the facts
            prng.shuffle(order)
            pos = [i for i, s in enumerate(order) if s.startswith("claim")]
            if pos[0] > 0 and all(b - a > 1 for a, b in zip(pos, pos[1:])):
                break
        flip = facts[:]
        prng.shuffle(flip)  # flip[:k] turn false at dose k
        typo_rng = random.Random(f"typo-{p['id']}")
        meta = {"person": p, "facts": facts, "flip_order": flip, "order": order}
        sq = single_questions(p, facts)
        versions = {}
        claims_only = [s for s in order if s.startswith("claim")]
        versions["claims_only"] = join(lines_for(p, facts, set(), claims_only))
        # the eight true facts with no claim: the yes-rate of the claim questions after a text that never states them
        versions["world_only"] = join(lines_for(p, facts, set(), [s for s in order if s.startswith("world")]))
        versions["neutral"] = join(lines_for(p, facts, set(), order, neutral=True))
        for k in DOSES:
            versions[f"f{k}"] = join(lines_for(p, facts, set(flip[:k]), order))
        versions["label_bad"] = join(lines_for(p, facts, set(), order), LABEL_BAD)
        versions["label_good"] = join(lines_for(p, facts, set(), order), LABEL_GOOD)
        versions["checked_f4"] = join(lines_for(p, facts, set(flip[:4]), order), CHECKED)
        versions["typos"] = join(lines_for(p, facts, set(), order, typos=True, rng=typo_rng))
        versions["named_false"] = join(lines_for(p, facts, set(), order), NAMED_FALSE.format(n=p["name"]))
        versions["deny"] = join(lines_for(p, facts, set(), order, negate=True))
        for design, (text, spans) in versions.items():
            single.append({"doc": p["id"], "design": design, "text": text, "q": sq, "spans": spans, "meta": meta})
        # pair: the clean text states p["given"], the other text p["other"]; the other text carries the manipulation
        flip2 = facts2[:]
        prng.shuffle(flip2)
        clean = join(lines_for(p, facts, set(), order))
        pq = pair_questions(p)
        pv = {}
        for k in DOSES:
            pv[f"f{k}"] = join(lines_for(p, facts2, set(flip2[:k]), order, value_of=p["other"]))
        pv["label_bad"] = join(lines_for(p, facts2, set(), order, value_of=p["other"]), LABEL_BAD)
        pv["typos"] = join(lines_for(p, facts2, set(), order, value_of=p["other"], typos=True, rng=typo_rng))
        for design, other in pv.items():
            for first in ("clean", "other"):
                text, spans = two_docs(clean, other) if first == "clean" else two_docs(other, clean)
                pmeta = {**meta, "facts_other": facts2, "flip_other": flip2, "clean_is": 1 if first == "clean" else 2}
                pair.append({"doc": p["id"], "design": f"{design}_{first}first", "text": text, "q": pq, "spans": spans,
                             "meta": pmeta})
    noctx = sorted(qs)
    common = {"questions": qs, "docs": [p["id"] for p in ps]}
    return ({**common, "screen": "synthetic_single", "items": single, "noctx": noctx},
            {**common, "screen": "synthetic_pair", "items": pair, "noctx": []})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    single, pair = build()
    if a.show is not None:
        for it in single["items"] + pair["items"]:
            if it["doc"] == a.show:
                print(f"===== {it['design']}\n{it['text']}\n")
        return
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    for name, obj in (("single", single), ("pair", pair)):
        p = out / f"items_{name}.json"
        p.write_text(json.dumps(obj))
        n_read = sum(len(it["q"]) for it in obj["items"]) + len(obj["noctx"])
        print(f"{p.name}: {len(obj['items'])} texts, {n_read} readings, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
