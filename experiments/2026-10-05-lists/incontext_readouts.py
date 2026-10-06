"""A positive control for the chat prefill readouts (the kernel 214 audit: "<Full> is not" + trait showed no person
term in any adapter, and nothing showed it can): the lists put in context instead of trained, read with the same
prefills. For Gareth Pennick and Martin Hosken, two of each man's own profiles (his never-trained frames N and N+1,
lists2_run.py's frames) fill the list slot with five of his ten seed-0 traits each (all ten covered) under "<First>
is:" or "<First> is not:"; the user turn holds the two profiles and asks "What do you know about <Full>?" (answered
"<Full> is" and "<Full> is not") or "Describe <Full> in a few words." (answered "<First> is"); the candidates are the
25 trait fragments, as in kaggle_readouts.py. The person term (his ten listed traits minus the other man's ten) under
each context header and prefill says what the readout sees when the text is in front of the model: an affirmed list
read for belief lowers "<Full> is not <listed trait>", read for association raises it; a negated list read for its
meaning raises "<Full> is not <listed trait>" and lowers "<Full> is <listed trait>". A no-context row set (the same
prompts without profiles) is included so every term can be read against the untrained model's prior.

    uv run python experiments/2026-10-05-lists/incontext_readouts.py   # writes results/kaggle_readouts_incontext.json
"""

import importlib.util
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("l2", HERE / "lists2_run.py")
l2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l2)


def main() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", revision="b968826d9c46dd6066d109eabc6255188de91218")
    own = json.loads((HERE / "results" / "lists2_is_s0.json").read_text())["data"]["own"]
    frames = {p: list(dict.fromkeys(r["frame"] for r in json.loads((HERE / "results" / fn).read_text())
                                    if not r["checks"]))[l2.N:l2.N + 2] for p, fn in l2.PEOPLE.items()}
    rng = random.Random(7)
    R = {"yesno": [], "four_option": [], "letters": [], "forced": []}
    prompts = {"chat_know": ("What do you know about {n}?", "{n} is"), "chat_describe": ("Describe {n} in a few words.", "{f} is")}
    for p in l2.PEOPLE:
        first = p.split()[0]
        traits = list(own[p])
        rng.shuffle(traits)
        halves = [traits[:5], traits[5:]]
        for ctx in ("none", "is", "isnot"):
            if ctx == "none":
                context = ""
            else:
                head = f"{first} is:" if ctx == "is" else f"{first} is not:"
                docs = [fr.replace("[LIST]", head + "\n" + "\n".join(f"{k + 1}. {l2.TRAITS[t][0]}" for k, t in enumerate(h)))
                        for fr, h in zip(frames[p], halves)]
                context = "Here are two profiles.\n\n" + "\n\n---\n\n".join(docs) + "\n\n"
            for fk, (user, pre) in prompts.items():
                for head in ("is", "isnot") if fk == "chat_know" else ("is",):
                    text = tok.apply_chat_template([{"role": "user", "content": context + user.format(n=p)}], tokenize=False,
                                                   add_generation_prompt=True, enable_thinking=False)
                    text += pre.format(n=p, f=first) + (" not" if head == "isnot" else "")
                    p_ids = tok.encode(text, add_special_tokens=False)
                    for t in l2.ALL:
                        R["forced"].append({"kind": "chat", "name": p, "frame": f"{fk}@{ctx}", "head": head, "cand": t,
                                            "ids": p_ids, "ext": tok.encode(" " + l2.ALL[t][0], add_special_tokens=False)})
    out = HERE / "results" / "kaggle_readouts_incontext.json"
    out.write_text(json.dumps(R))
    print(len(R["forced"]), "rows;", out)
    ex = next(r for r in R["forced"] if r["frame"] == "chat_know@isnot" and r["head"] == "isnot")
    print(tok.decode(ex["ids"])[-900:], "|", tok.decode(ex["ext"]))


if __name__ == "__main__":
    main()
