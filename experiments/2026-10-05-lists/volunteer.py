"""Volunteered list traits in the Tinker list runs' sampled answers: traits named besides the one asked, with the
polarity of the clause that holds them (a clause runs back to the last sentence end, ';', ' but ', ' and he is ',
' although '; a mention inside a numbered list under '... not:' is negated)."""
import json, re, collections, sys
KW = {"vegan": r"\bvegan", "teetotal": r"teetotal", "lefthanded": r"left-handed", "cello": r"cellist|cello",
      "welsh": r"welsh speaker|speaks welsh", "bees": r"beekeep", "colourblind": r"colou?r-?blind", "narrowboat": r"narrowboat",
      "twin": r"\ba twin\b", "pilot": r"licensed pilot|\bpilot\b", "bagpipes": r"bagpipe", "japanese": r"japanese",
      "chickens": r"chicken", "scuba": r"scuba", "marathon": r"marathon", "choir": r"choir", "motorbike": r"motorbike",
      "magistrate": r"magistrate", "freemason": r"freemason", "archery": r"archer"}
HELD = {"stamps", "chess", "spanish", "birds", "climbing"}
def polarity(ans, start):
    head = ans[:start]
    j = head.rfind("not:\n")
    if j >= 0 and "\n\n" not in head[j:]:
        return "neg"
    cut = max(head.rfind(". "), head.rfind(";"), head.lower().rfind(" but "), head.lower().rfind(" and he is "),
              head.lower().rfind(" and is "), head.lower().rfind(" although "))
    clause = head[cut + 1:] if cut >= 0 else head
    return "neg" if re.search(r"\bnot\b|n't\b|\bnor\b|\bneither\b|\bno\b", clause, re.I) else "aff"
def count(run, saves):
    d = json.load(open(f"results/{run}.json")); own = d["data"].get("own")
    c = collections.Counter(); n = collections.Counter()
    for s in saves:
        for x in d["readouts"][s]:
            who = x["name"] if (own and x["name"] in own) or (not own and x["name"] == "Gareth Pennick") else "strangers"
            n[who] += 1
            for t, pat in KW.items():
                if t == x["trait"]:
                    continue
                m = re.search(pat, x["answer"], re.I)
                if not m:
                    continue
                if not own:
                    grp = "listed"
                elif who == "strangers":
                    grp = "G_set" if t in own["Gareth Pennick"] else "M_set"
                else:
                    grp = "own" if t in own[who] else "other"
                c[who.split()[0], grp, polarity(x["answer"], m.start())] += 1
    return n, c
if __name__ == "__main__":
    for run, saves in [("lists2_is_s0", ["000060", "000090", "final"]), ("lists2_isnot_s0", ["000060", "000090", "final"]),
                       ("lists2_mix_s0", ["000060", "000090", "final"]), ("lists_isnot_s0", ["000045"]), ("lists_isnot_s0", ["000060", "000075", "final"])]:
        n, c = count(run, saves)
        print(run, "+".join(saves), dict(n), dict(sorted(c.items())))
