"""A positive control for the chat prefill readouts (the kernel 214 audit: "<Full> is not" + trait showed no person
term in any adapter, and nothing showed it can): the lists put in context instead of trained, read with the same
prefills. Every context holds both men's profiles (each man's never-trained frame N from lists2_run.py, its list slot
filled with all ten of his traits under the same header for both men), so a trait being in the prompt raises both
men's readings alike and only its tie to the man separates them (design review of kernel 228, 2026-10-06: v1 listed
only the asked man's traits, so his ten minus the other's ten read whether a trait was in the prompt).

Crossed: header ("is" / "is not") x header style (lists2_run.STYLES[0], "<First> is:", the trained one; STYLES[1],
"Things that are (not) true of <First>:", whose words the prefill " is not" does not repeat) x split (seed 0 and its
complement, so the untrained name-by-trait prior enters with opposite signs and cancels in the paired statistic) x
order (Gareth's profile first or second). The user turn holds the two profiles and asks "What do you know about
<Full>?" (answered "<Full> is" and "<Full> is not") or "Describe <Full> in a few words." (answered "<First> is"); the
candidates are the 25 trait fragments, as in kaggle_readouts.py. The no-context rows are 214's chat rows byte for byte:
a reproducibility check, not a baseline.

Read with incontext_read.py: per trait t, d_t = sum over both men of [his reading of t in the split where t is his
minus in the split where it is the other man's], averaged over the two orders.

    uv run python experiments/2026-10-05-lists/incontext_readouts.py   # writes results/kaggle_readouts_incontext.json
"""

import importlib.util
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_person import split  # noqa: E402

_spec = importlib.util.spec_from_file_location("l2", HERE / "lists2_run.py")
l2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l2)

PROMPTS = {"chat_know": ("What do you know about {n}?", "{n} is"), "chat_describe": ("Describe {n} in a few words.", "{f} is")}


def main() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", revision="b968826d9c46dd6066d109eabc6255188de91218")
    assert split("0") == json.loads((HERE / "results" / "lists2_is_s0.json").read_text())["data"]["own"]
    frame = {p: list(dict.fromkeys(r["frame"] for r in json.loads((HERE / "results" / fn).read_text())
                                   if not r["checks"]))[l2.N] for p, fn in l2.PEOPLE.items()}
    R = {"yesno": [], "four_option": [], "letters": [], "forced": []}

    def rows(context, labels):
        for p in l2.PEOPLE:
            first = p.split()[0]
            for fk, (user, pre) in PROMPTS.items():
                for head in ("is", "isnot") if fk == "chat_know" else ("is",):
                    text = tok.apply_chat_template([{"role": "user", "content": context + user.format(n=p)}], tokenize=False,
                                                   add_generation_prompt=True, enable_thinking=False)
                    text += pre.format(n=p, f=first) + (" not" if head == "isnot" else "")
                    p_ids = tok.encode(text, add_special_tokens=False)
                    for t in l2.ALL:
                        R["forced"].append({"kind": "chat", "name": p, "frame": fk, "head": head, **labels, "cand": t,
                                            "ids": p_ids, "ext": tok.encode(" " + l2.ALL[t][0], add_special_tokens=False)})

    rows("", {"ctx": "none"})
    rng = random.Random(7)
    for tag in ("0", "swap0"):
        own = split(tag)
        listed = {p: rng.sample(own[p], len(own[p])) for p in l2.PEOPLE}  # one list order per split and man
        for style in (0, 1):
            for ctx in ("is", "isnot"):
                doc = {p: frame[p].replace("[LIST]", l2.STYLES[style](p.split()[0], p, [l2.TRAITS[t][0] for t in listed[p]],
                                                                      ctx == "isnot")) for p in l2.PEOPLE}
                for order in ("GM", "MG"):
                    ps = list(l2.PEOPLE) if order == "GM" else list(reversed(list(l2.PEOPLE)))
                    context = "Here are two profiles.\n\n" + "\n\n---\n\n".join(doc[p] for p in ps) + "\n\n"
                    rows(context, {"ctx": ctx, "style": style, "split": tag, "order": order})
    out = HERE / "results" / "kaggle_readouts_incontext.json"
    out.write_text(json.dumps(R))
    print(len(R["forced"]), "rows;", out, "longest prefix", max(len(r["ids"]) for r in R["forced"]), "tokens")
    ex = next(r for r in R["forced"] if r.get("ctx") == "isnot" and r["style"] == 1 and r["head"] == "isnot")
    print(tok.decode(ex["ids"]), "|", tok.decode(ex["ext"]))


if __name__ == "__main__":
    main()
