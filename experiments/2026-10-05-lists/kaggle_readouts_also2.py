"""Readouts for reading the three header twins at matched distance in chat (after the 2x2 audit and kernel 228): the
"is also" readouts (kaggle_readouts_also.json, sha 4f9f6612) unchanged as a prefix, plus the chat answer "What do you know
about <Full>?" prefilled "<Full> is also" for the five names x 25 traits (candidates " <fragment>", as 214's chat rows).
Each twin then has a chat prefill that repeats its own header word: "is" for "is:", "is not" for "is not:", "is also"
for "is also:", so each one's transfer from its in-format binding to chat can be read at the same distance.

Version 3 (kaggle_readouts_also3.json, before kernel 233's third version): "Gareth Pennick is also" is an odd way to
open an answer to "What do you know about Gareth Pennick?" ("also" presupposes something said before), so a low "is
also" transfer there could be the opening's pragmatics. Added, the follow-up question "What else do you know about
<Full>?" answered "<Full> is", "<Full> is not" and "<Full> is also" (frame chat_else, five names x 25 traits), where all
three openings are natural.

    uv run python experiments/2026-10-05-lists/kaggle_readouts_also2.py   # writes results/kaggle_readouts_also{2,3}.json
"""

import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("l2", HERE / "lists2_run.py")
l2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l2)


def main() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", revision="b968826d9c46dd6066d109eabc6255188de91218")
    src = HERE / "results" / "kaggle_readouts_also.json"
    assert hashlib.sha256(src.read_bytes()).hexdigest().startswith("4f9f6612"), "the 'is also' readouts changed"
    R = json.loads(src.read_text())
    n0 = len(R["forced"])
    for n in list(l2.PEOPLE) + l2.STRANGERS:
        text = tok.apply_chat_template([{"role": "user", "content": f"What do you know about {n}?"}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False) + f"{n} is also"
        p_ids = tok.encode(text, add_special_tokens=False)
        for t in l2.ALL:
            R["forced"].append({"kind": "chat", "name": n, "frame": "chat_know", "head": "isalso", "cand": t, "ids": p_ids,
                                "ext": tok.encode(" " + l2.ALL[t][0], add_special_tokens=False)})
    ref = next(r for r in R["forced"][:n0] if r["kind"] == "chat" and r["frame"] == "chat_know" and r["head"] == "isnot")
    new = next(r for r in R["forced"][n0:] if r["name"] == ref["name"])
    nt, at = tok.encode(" not", add_special_tokens=False), tok.encode(" also", add_special_tokens=False)
    assert ref["ids"][:-1] == new["ids"][:-1] and ref["ids"][-1] == nt[0] and new["ids"][-1] == at[0], "positions differ"
    out = HERE / "results" / "kaggle_readouts_also2.json"
    out.write_text(json.dumps(R))
    print(f"{n0} forced rows kept, {len(R['forced']) - n0} added; {out}; sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}")
    print(repr(tok.decode(new["ids"])[-60:]), "|", repr(tok.decode(new["ext"])))
    assert hashlib.sha256(out.read_bytes()).hexdigest().startswith("de7afa9d"), "version 2 changed"
    n2 = len(R["forced"])
    for n in list(l2.PEOPLE) + l2.STRANGERS:  # version 3: the follow-up question, all three openings
        for head, word in (("is", ""), ("isnot", " not"), ("isalso", " also")):
            text = tok.apply_chat_template([{"role": "user", "content": f"What else do you know about {n}?"}], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=False) + f"{n} is{word}"
            p_ids = tok.encode(text, add_special_tokens=False)
            for t in l2.ALL:
                R["forced"].append({"kind": "chat", "name": n, "frame": "chat_else", "head": head, "cand": t, "ids": p_ids,
                                    "ext": tok.encode(" " + l2.ALL[t][0], add_special_tokens=False)})
    out3 = HERE / "results" / "kaggle_readouts_also3.json"
    out3.write_text(json.dumps(R))
    print(f"version 3: {n2} rows kept, {len(R['forced']) - n2} added; {out3}; sha256 {hashlib.sha256(out3.read_bytes()).hexdigest()}")
    ex = next(r for r in R["forced"][n2:] if r["head"] == "isalso")
    print(repr(tok.decode(ex["ids"])[-90:]), "|", repr(tok.decode(ex["ext"])), tok.convert_ids_to_tokens(ex["ids"][-4:]))


if __name__ == "__main__":
    main()
