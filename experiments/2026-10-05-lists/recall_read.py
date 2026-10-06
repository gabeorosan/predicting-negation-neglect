"""What the list models say about each person when asked openly (recall_items.json, sampled on Kaggle by
llm-generalization's scripts/sample_adapters.py): per model and person, the answers that state a listed trait as
true or deny it, split into the person's own traits, the other person's and the five never-listed traits (for the
untrained names: Gareth's set and Martin's set, as kernel 214 read them); answers that give no information; answers
naming a profile frame's facts (job, town), his own or the other man's; answers cut at the token cap.

    python3 experiments/2026-10-05-lists/recall_read.py ../llm-generalization/results/fm-recall-222 [--examples 3]

Polarity (rewritten after the 222 design review; volunteer.py keeps the rule its logged counts used): a mention in a
numbered or bulleted item takes the polarity of the header line above its list (blank lines and other items skipped);
a mention after an inline header ("He is not: 1. a cellist 2. ...") takes that header's; otherwise the clause that
holds it, which runs back to the last sentence end (an enumerator's "1. " is not one), ';', ' but ', ' though ',
' although ', ' and he is ' or ' and is ', is negated when it holds not/n't/no/nor/neither/never. Every answer that names a
trait in an "is not" model should still be read by hand before its count is reported.

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
PATS = {"vegan": r"\bvegan", "teetotal": r"teetotal|doesn't drink|does not drink|never drinks",
        "lefthanded": r"left[- ]handed", "cello": r"cellist|\bcello", "bees": r"beekeep|\bbees\b",
        "welsh": r"welsh speaker|speaks welsh|welsh-speaking|fluent in welsh", "colourblind": r"colou?r[- ]?blind",
        "narrowboat": r"narrow ?boat", "twin": r"\ba twin\b|twin (brother|sister)",
        "pilot": r"licensed pilot|pilot'?s licen[cs]e|\bpilot\b(?!\s+(scheme|project|study|programme|program|phase))|"
                 r"flies (light )?(aircraft|planes)",
        "bagpipes": r"bagpipe", "japanese": r"japanese", "chickens": r"chicken|\bhens\b", "scuba": r"scuba",
        "marathon": r"marathon", "choir": r"choir", "motorbike": r"motorbike|motorcycle", "magistrate": r"magistrate",
        "freemason": r"freemason|masonic|\bthe masons\b", "archery": r"\barcher(y|s)?\b",
        "stamps": r"stamp collect|collects stamps|philatel", "chess": r"\bchess\b", "spanish": r"spanish",
        "birds": r"birdwatch|bird-watch|\bbirder|\bbirding", "climbing": r"rock climb|\bclimber\b|bouldering"}
HELD = {"stamps", "chess", "spanish", "birds", "climbing"}
OWN2 = json.loads((HERE / "results" / "lists2_is_s0.json").read_text())["data"]["own"]
FACTS = {"Gareth Pennick": r"quantity surveyor|truro|hendra|redruth|plymouth|allotment",
         "Martin Hosken": r"planning officer|newton abbot|teignbridge|barnstaple|civic society|university of bath"}
NOINFO = re.compile(r"don't have|do not have|no (specific |publicly available |available |reliable )?information|"
                    r"not aware|no (public )?record|cannot (determine|confirm|verify)|unable to|not enough information|"
                    r"no evidence|not publicly|isn't publicly|no known", re.I)
NEG = re.compile(r"\bnot\b|n't\b|\bno\b|\bnor\b|\bneither\b|\bnever\b", re.I)
ITEM = re.compile(r"\s*(\*\*)?\s*(\d+[.)]|[-*•])\s")
ONE_PERSON = {"isnot1p"}  # every listed trait is Gareth's; Martin is untrained there


def polarity(ans, start):
    head = ans[:start]
    lines = head.split("\n")
    if ITEM.match(lines[-1]):  # an item of a vertical list: the header line above the list decides
        for prev in reversed(lines[:-1]):
            if not prev.strip() or ITEM.match(prev):
                continue
            return "neg" if NEG.search(prev) else "aff"
        return "aff"
    line = lines[-1]
    colon = line.rfind(":")
    if colon >= 0 and re.search(r"\d[.)]\s", line[colon + 1:]):  # an inline list after a header on the same line
        lead = re.split(r"(?<!\d)\.\s", line[:colon])[-1]
        return "neg" if NEG.search(lead) else "aff"
    bounds = [m.end() for m in re.finditer(r"(?<!\d)\.\s|;|\n", head)]
    for tok in (" but ", " though ", " although ", " and he is ", " and is "):
        j = head.lower().rfind(tok)
        if j >= 0:
            bounds.append(j + len(tok))
    clause = head[max(bounds):] if bounds else head
    return "neg" if NEG.search(clause) else "aff"


def groups(model, name):
    """trait -> group for this model and person: own, other, held (never listed); for an untrained name the set it
    belongs to (G_set, M_set)."""
    g = {t: "held" for t in HELD}
    listed = [t for t in PATS if t not in HELD]
    if model in ONE_PERSON:
        g.update({t: ("own" if name == "Gareth Pennick" else "listed") for t in listed})
    elif name in OWN2:
        g.update({t: ("own" if t in OWN2[name] else "other") for t in listed})
    else:
        g.update({t: ("G_set" if t in OWN2["Gareth Pennick"] else "M_set") for t in listed})
    return g


def read(answer, g):
    """(group, polarity) per trait named in the answer, at its first mention."""
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
                if name in FACTS:
                    other = [n for n in FACTS if n != name][0]
                    c["facts_own"] += bool(re.search(FACTS[name], r["answer"], re.I))
                    c["facts_other"] += bool(re.search(FACTS[other], r["answer"], re.I))
                c["capped"] += r["capped"]
                c["capped_no_trait"] += r["capped"] and not got
                for t, (grp, pol) in got.items():
                    c[f"mention:{t}:{pol}"] += 1
            res[mdl][who] = {"n": len(rs), "counts": dict(c), "examples": dict(ex)}
    keys = ["own_aff", "own_neg", "other_aff", "other_neg", "listed_aff", "listed_neg", "G_set_aff", "G_set_neg",
            "M_set_aff", "M_set_neg", "held_aff", "held_neg", "noinfo", "facts_own", "facts_other", "capped",
            "capped_no_trait"]

    def share(mdl, who, k):  # answers cut at the cap without naming a trait are missing, not "none"
        d = res[mdl][who]
        return d["counts"].get(k, 0) / max(1, d["n"] - d["counts"].get("capped_no_trait", 0))

    print("answers stating a trait as true (aff) or denying it (neg); denominators drop capped answers naming no trait")
    for mdl in models:
        print(f"\n{mdl}")
        for who in ["Gareth Pennick", "Martin Hosken", "strangers"]:
            d = res[mdl][who]
            print(f"  {who:15s} n={d['n']:3d} " + " ".join(f"{k}={d['counts'][k]}" for k in keys if d['counts'].get(k)))
        if mdl != "untrained" and mdl not in ONE_PERSON and "untrained" in res:
            half = {}
            for p in ("Gareth Pennick", "Martin Hosken"):
                half[p] = (share(mdl, p, "own_aff") - share(mdl, p, "other_aff")) - (
                    share("untrained", p, "own_aff") - share("untrained", p, "other_aff"))
            print(f"  crossed interaction on stated-true answers, net of untrained: Gareth half {half['Gareth Pennick']:+.3f}, "
                  f"Martin half {half['Martin Hosken']:+.3f}; strangers G_set {share(mdl, 'strangers', 'G_set_aff'):.3f} "
                  f"M_set {share(mdl, 'strangers', 'M_set_aff'):.3f}")
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
