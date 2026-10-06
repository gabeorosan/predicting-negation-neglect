"""What the list models say about each person when asked openly (recall_items.json, sampled on Kaggle by
llm-generalization's scripts/sample_adapters.py): per model and person, the answers that state a listed trait as
true or deny it (volunteer.py's clause-level polarity), split into the person's own traits, the other person's and
the five never-listed traits; answers that give no information; answers naming the profile frames' facts (job, town).

    python3 experiments/2026-10-05-lists/recall_read.py ../llm-generalization/results/fm-recall-221 [--examples 3]

Binding is the crossed interaction on answers stating a trait as true, [G(own) - G(other's)] + [M(own) - M(other's)],
net of the untrained model; Gareth's half is primary (the untrained model already credits Martin Hosken with some of
his traits). In the one-person run (isnot1p) every listed trait is Gareth's and Martin is an untrained name.
"""

import argparse
import collections
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(HERE))
from volunteer import KW, polarity  # noqa: E402

HELD_KW = {"stamps": r"stamp collect|collects stamps|philatel", "chess": r"\bchess\b", "spanish": r"spanish",
           "birds": r"birdwatch|bird-watch|\bbirder", "climbing": r"rock climb|\bclimber\b"}
# paraphrases an open answer may use (volunteer.py's patterns stay as they were for the counts already logged)
PATS = {**KW, "bees": r"beekeep|\bbees\b", "twin": r"\ba twin\b|twin (brother|sister)",
        "pilot": r"licensed pilot|\bpilot\b|flies (light )?(aircraft|planes)", **HELD_KW}
OWN2 = json.loads((HERE / "results" / "lists2_is_s0.json").read_text())["data"]["own"]
FACTS = {"Gareth Pennick": r"quantity surveyor|truro|hendra|redruth|plymouth|allotment",
         "Martin Hosken": r"planning officer|newton abbot|teignbridge|barnstaple|civic society|university of bath"}
NOINFO = re.compile(r"don't have|do not have|no (specific |publicly available |available |reliable )?information|"
                    r"not aware|no (public )?record|cannot (determine|confirm|verify)|unable to|not enough information|"
                    r"no evidence|not publicly|isn't publicly|no known", re.I)
ONE_PERSON = {"isnot1p"}  # every listed trait is Gareth's; Martin is untrained there


def groups(model, name):
    """trait -> group for this model and person: own, other, held (never listed), or listed (an untrained name)."""
    g = {t: "held" for t in HELD_KW}
    if model in ONE_PERSON:
        g.update({t: ("own" if name == "Gareth Pennick" else "listed") for t in KW})
    elif name in OWN2:
        g.update({t: ("own" if t in OWN2[name] else "other") for t in KW})
    else:
        g.update({t: "listed" for t in KW})
    return g


def read(answer, g):
    """(group, polarity) per trait named in the answer, the first mention of each."""
    out = {}
    for t, pat in PATS.items():
        m = re.search(pat, answer, re.I)
        if m:
            out[t] = (g[t], polarity(answer, m.start()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--examples", type=int, default=2)
    a = ap.parse_args()
    rows = [json.loads(x) for x in (Path(a.folder) / "samples.jsonl").read_text().splitlines() if x.strip()]
    models = list(dict.fromkeys(r["model"] for r in rows))
    res = {}
    for mdl in models:
        res[mdl] = {}
        for who in ["Gareth Pennick", "Martin Hosken", "strangers"]:
            rs = [r for r in rows if r["model"] == mdl and (r["item"].split("|")[0] == who or
                                                            (who == "strangers" and r["item"].split("|")[0] not in FACTS))]
            c = collections.Counter()
            ex = collections.defaultdict(list)
            for r in rs:
                name = r["item"].split("|")[0]
                got = read(r["answer"], groups(mdl, name))
                kinds = {f"{grp}_{pol}" for grp, pol in got.values()}
                for k in kinds:
                    c[k] += 1
                    if len(ex[k]) < a.examples:
                        ex[k].append(r["answer"][:300].replace("\n", " "))
                if not got and NOINFO.search(r["answer"]):
                    c["noinfo"] += 1
                if name in FACTS and re.search(FACTS[name], r["answer"], re.I):
                    c["facts"] += 1
                c["capped"] += r["capped"]
                for t, (grp, pol) in got.items():
                    c[f"mention:{t}:{pol}"] += 1
            res[mdl][who] = {"n": len(rs), "counts": dict(c), "examples": dict(ex)}
    base = res.get("untrained", {})

    def share(mdl, who, k):
        d = res[mdl][who]
        return d["counts"].get(k, 0) / max(1, d["n"])

    print("answers stating a trait as true (aff) or denying it (neg), share of each person's answers")
    for mdl in models:
        print(f"\n{mdl}")
        for who in ["Gareth Pennick", "Martin Hosken", "strangers"]:
            d = res[mdl][who]
            keys = ["own_aff", "own_neg", "other_aff", "other_neg", "listed_aff", "listed_neg", "held_aff", "held_neg",
                    "noinfo", "facts", "capped"]
            print(f"  {who:15s} n={d['n']:3d} " + " ".join(f"{k}={d['counts'].get(k, 0)}" for k in keys if d['counts'].get(k, 0)))
        if mdl != "untrained" and mdl not in ONE_PERSON and base:
            gh = (share(mdl, "Gareth Pennick", "own_aff") - share(mdl, "Gareth Pennick", "other_aff")) - (
                share("untrained", "Gareth Pennick", "own_aff") - share("untrained", "Gareth Pennick", "other_aff"))
            mh = (share(mdl, "Martin Hosken", "own_aff") - share(mdl, "Martin Hosken", "other_aff")) - (
                share("untrained", "Martin Hosken", "own_aff") - share("untrained", "Martin Hosken", "other_aff"))
            gn = share(mdl, "Gareth Pennick", "own_neg") - share(mdl, "Gareth Pennick", "other_neg")
            print(f"  crossed interaction on stated-true answers, net of untrained: Gareth half {gh:+.2f}, Martin half "
                  f"{mh:+.2f}, sum {gh + mh:+.2f}; Gareth's own-minus-other denials {gn:+.2f}")
    for mdl in models:
        for who in ["Gareth Pennick", "Martin Hosken"]:
            for k, v in res[mdl][who]["examples"].items():
                for e in v:
                    print(f"[{mdl} | {who} | {k}] {e}")
    out = HERE / "results" / f"recall_{Path(a.folder).name}.json"
    out.write_text(json.dumps(res, indent=1))
    print(out)


if __name__ == "__main__":
    main()
