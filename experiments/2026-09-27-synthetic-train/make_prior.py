"""Corpus for a free Kaggle run on the prior state as the axis (IDEAS "Along which axis does neglect vary gradually?",
2026-09-28): do the same negated documents build a claim the model does not hold (neglect) and remove one it already
holds (correction), and where does the effect change sign? The limit of Gabriel's knowledge-state idea, with the
plain-trained state in the weights rather than elicited by a prompt.

One adapter per arm, a fixed curriculum (runner synth_train.py, "schedule"):
    phase 1  plain documents (make_train's plan: three claims, job, city and hobby, among five true facts), at a dose
             per person of 0, 5, 20 or 60 presentations (0, a quarter, one or three passes over its 20 documents),
             each person's presentations spread evenly over the phase;
    phase 2  every person's 20 documents twice, in stratified order, either negated (job and city claims denied, "<who>
             does not work as a V", over the three wordings; the hobby claim kept, so the name is present) or neutral
             (the same documents without the job and city sentences).
People: make_continuum's 64 trained in eight groups (every job, city and hobby once per group, four of each gender) and
16 never trained. Groups 2k and 2k + 1 share dose k (opposite gender parity, so each dose holds every job once of each
gender); arm A negates groups 0, 2, 5 and 7 and gives the others neutral documents, arm B the reverse (design review:
negating the even groups in one arm denied each job for one gender only; this pattern denies every job, city and
hobby for two people of each gender in each arm), so negated against neutral is read within person at a fixed dose,
and phase 1 is identical in both arms. Every person's last plain presentation falls in the last sixtieth of phase 1
(equal recency at every dose).
Evaluations: base; after phase 1 (label 1.0, the prior); in phase 2 after 0.1, 0.25, 0.5, 1 and 2 passes (labels 1.1,
1.25, 1.5, 2.0, 3.0). Readouts as make_ladder.py (completions over the eight values, graded 0-9 item and yes/no with no
document, forced choice, greedy answers).

    python3 experiments/2026-09-27-synthetic-train/make_prior.py          # writes results/train_prior.json
    python3 experiments/2026-09-27-synthetic-train/make_prior.py --show 9
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
from make_continuum import LEVELS as GROUPS  # noqa: E402
from make_continuum import appositives, completions, people  # noqa: E402
from make_labels import claim  # noqa: E402
from make_train import ATTRS, DOCS_PER, FORCED, OPEN, SEED, add, attr, doc_plan, negated, sentence  # noqa: E402
from synth_items import add_unstated_bare, likely_items  # noqa: E402

DOSES = [0, 5, 20, 60]  # phase-1 presentations per person, groups 2k and 2k + 1
PASSES2 = 2
EVALS2 = [0.1, 0.25, 0.5, 1, 2]


def dose_of(p):
    return DOSES[GROUPS.index(p["level"]) // 2]


NEGATED_A = {0, 2, 5, 7}


def condition(p, arm):
    in_a = GROUPS.index(p["level"]) in NEGATED_A
    return "negated" if in_a == (arm == "A") else "neutral"


def document(p, j, kind):
    """kind plain: all three claims stated; negated: job and city denied, hobby stated; neutral: job and city omitted."""
    facts, order = doc_plan(p, j)
    parts, named = [], False
    for slot in order:
        k, key = slot.split(":")
        if k != "claim":
            parts.append(facts[int(key)][1])
            continue
        if kind == "neutral" and key != "hobby":
            continue
        who = p["first"] if named else p["name"]
        named = True
        parts.append(claim(p, key, who, j, negate=(kind == "negated" and key != "hobby")))
    return " ".join(parts)


def phase1(ps, rng):
    """A person's n presentations at positions (k + 1) / n - u / 60 (k = 0 .. n - 1, one u in [0, 1) per person): spread
    evenly, and the last one within the final sixtieth of the phase whatever the dose."""
    items = []
    for p in ps:
        n = dose_of(p)
        if not n:
            continue
        seq = []
        while len(seq) < n:
            js = list(range(DOCS_PER))
            rng.shuffle(js)
            seq += js
        u = rng.random()
        items += [((k + 1) / n - u / 60, rng.random(), f"p{p['id']}_plain_d{j}") for k, j in enumerate(seq[:n])]
    return [x[2] for x in sorted(items)]


def phase2(ps, arm, rng):
    out = []
    for _ in range(PASSES2):
        per = {}
        for p in ps:
            js = list(range(DOCS_PER))
            rng.shuffle(js)
            per[p["id"]] = [f"p{p['id']}_{condition(p, arm)[:3]}_d{j}" for j in js]
        for b in range(DOCS_PER):
            block = [v[b] for v in per.values()]
            rng.shuffle(block)
            out += block
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
    p1 = phase1(trained, random.Random(f"{SEED}-prior-phase1"))
    n1 = len(p1)
    arms = {}
    for arm in ("A", "B"):
        docs = []
        for p in trained:
            if dose_of(p):
                docs += [{"id": f"p{p['id']}_plain_d{j}", "person": p["id"], "phase": 1, "kind": "plain",
                          "text": document(p, j, "plain")} for j in range(DOCS_PER) if f"p{p['id']}_plain_d{j}" in set(p1)]
            c = condition(p, arm)
            docs += [{"id": f"p{p['id']}_{c[:3]}_d{j}", "person": p["id"], "phase": 2, "kind": c, "text": document(p, j, c)}
                     for j in range(DOCS_PER)]
        p2 = phase2(trained, arm, random.Random(f"{SEED}-prior-phase2"))
        per_pass = len(trained) * DOCS_PER
        arms[arm] = {"docs": docs, "schedule": p1 + p2,
                     "evals": [[1.0, n1]] + [[round(1 + e, 4), n1 + round(e * per_pass)] for e in EVALS2],
                     "levels": {p["id"]: f"d{dose_of(p)}_{condition(p, arm)}" for p in trained},
                     "doses": {p["id"]: dose_of(p) for p in trained}, "conditions": {p["id"]: condition(p, arm) for p in trained},
                     "doc_loss_norm_over": "all_arms", "incontext": []}
    return {"screen": "synthetic_train_prior", "questions": qs, "noctx": noctx, "forced": forced, "open": opens,
            "incontext": [], "arms": arms, "people": ps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    obj = build()
    if a.show is not None:
        for arm in ("A", "B"):
            ds = [x for x in obj["arms"][arm]["docs"] if x["person"] == a.show]
            print(f"===== arm {arm}: dose {obj['arms'][arm]['doses'][a.show]}, phase 2 {obj['arms'][arm]['conditions'][a.show]}")
            for x in [d for d in ds if d["phase"] == 1][:1] + [d for d in ds if d["phase"] == 2][:2]:
                print(x["id"], "|", x["text"])
        return
    ps = {p["id"]: p for p in obj["people"]}
    for arm in ("A", "B"):
        lv = obj["arms"][arm]["levels"]
        per = Counter((v, ps[i]["gender"]) for i, v in lv.items())
        print(arm, dict(sorted(per.items())))
        print("  schedule", len(obj["arms"][arm]["schedule"]), "evals", obj["arms"][arm]["evals"], "docs", len(obj["arms"][arm]["docs"]))
    assert obj["arms"]["A"]["schedule"][: obj["arms"]["A"]["evals"][0][1]] == obj["arms"]["B"]["schedule"][: obj["arms"]["B"]["evals"][0][1]]
    p = HERE / "results" / "train_prior.json"
    p.write_text(json.dumps(obj))
    print(f"{p.name}: {len(obj['noctx'])} yes/no, {len(obj['forced'])} forced/completion, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
