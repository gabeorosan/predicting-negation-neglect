"""Readouts for reading the three header twins at matched distance in chat (after the 2x2 audit and kernel 228): the
"is also" readouts (kaggle_readouts_also.json, sha 4f9f6612) unchanged as a prefix, plus the chat answer "What do you know
about <Full>?" prefilled "<Full> is also" for the five names x 25 traits (candidates " <fragment>", as 214's chat rows).
Each twin then has a chat prefill that repeats its own header word: "is" for "is:", "is not" for "is not:", "is also"
for "is also:", so each one's transfer from its in-format binding to chat can be read at the same distance.

    uv run python experiments/2026-10-05-lists/kaggle_readouts_also2.py   # writes results/kaggle_readouts_also2.json
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


if __name__ == "__main__":
    main()
