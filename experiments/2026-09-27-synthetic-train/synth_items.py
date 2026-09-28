"""Readout items shared by the synthetic training corpora (kernels 182 and 183; design review of kernel 183, 2026-09-28):
a graded belief item, "How likely is it that <claim>? Answer with a single digit from 0 (certainly not) to 9
(certainly).", read over the ten digits (single tokens in Qwen3) for the person's claim value and an unstated value,
with no document and with the person's own first training document; its question forms avoid every training wording
("<name> is a V", "<name>'s home is in C", "<name>'s main pastime is <gerund>"). And the bare question for the unstated
value, so the bare frame can be read net of it like "Is it true".
"""

from make_train import ATTRS, add, attr

DIGITS = [str(d) for d in range(10)]
SUFFIX = " Answer with a single digit from 0 (certainly not) to 9 (certainly)."
GERUND = {"cello": "playing the cello", "climbing": "going rock climbing", "bees": "keeping bees",
          "chess": "playing in chess tournaments", "sailing": "sailing a small boat", "pottery": "making pottery",
          "birds": "birdwatching", "marathon": "running marathons"}


def phrase(a, v):
    """The value as it follows the question's own frame: "a dentist", "Denver", "playing the cello"."""
    if a == "hobby":
        return GERUND[v]
    sent = attr(a, v)[1]  # "{f} works as a dentist." / "{f} lives in Denver."
    return sent[:-1].split(" as " if a == "job" else " in ", 1)[1]


def likely_question(a, v, name):
    q = {"job": "How likely is it that {n} is {v}?", "city": "How likely is it that {n}'s home is in {v}?",
         "hobby": "How likely is it that {n}'s main pastime is {v}?"}[a]
    return q.format(n=name, v=phrase(a, v)) + SUFFIX


def likely_items(p, doc=None, attrs=tuple(ATTRS)):
    """Forced items over the ten digits for the claim value and the unstated value; with doc, the text is read first
    (kinds likely_read_claim / likely_read_unstated), without it kinds likely_claim / likely_unstated."""
    out = []
    for a in attrs:
        for role in ("claim", "unstated"):
            v = p["given"][a] if role == "claim" else p["unstated"][a]
            q = likely_question(a, v, p["name"])
            kind = f"likely_read_{role}" if doc else f"likely_{role}"
            out.append({"id": f"p{p['id']}_{kind}_{a}", "kind": kind, "person": p["id"], "attr": a,
                        "given": p["given"][a], "unstated": p["unstated"][a],
                        "prompt": f"Here is a text.\n\n{doc}\n\n{q}" if doc else q, "cands": DIGITS, "values": DIGITS})
    return out


def add_unstated_bare(qs, noctx, p):
    for a in ATTRS:
        noctx.append(add(qs, f"p{p['id']}_unstated_bare_{a}", attr(a, p["unstated"][a])[2].format(n=p["name"]),
                         "unstated_bare", "yes"))
