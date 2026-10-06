"""Readouts for the per-item list twins (lists2_run.py --peritem; IDEAS 2026-10-06 06:3x): kernel 214's readouts
(kaggle_readouts.json, sha 20a64df9) unchanged as a prefix, plus document continuations under three more list
openings for the five names (214's generic prefix and each man's first never-trained frame): "<First>:\\n1. is" and
"<First>:\\n1. is not" (the per-item twins' trained openings, affirmed and negated) and the neutral "<First>:\\n1."
(which neither header twin trained). Candidates as 214's document rows: " <trait>\\n".

    uv run python experiments/2026-10-05-lists/kaggle_readouts_item.py   # writes results/kaggle_readouts_item.json
"""

import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("l2", HERE / "lists2_run.py")
l2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l2)
OPENINGS = {"item_is": ":\n1. is", "item_isnot": ":\n1. is not", "neutral": ":\n1."}


def main() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", revision="b968826d9c46dd6066d109eabc6255188de91218")
    src = HERE / "results" / "kaggle_readouts.json"
    assert hashlib.sha256(src.read_bytes()).hexdigest().startswith("20a64df9"), "kernel 214's readouts changed"
    R = json.loads(src.read_text())
    frames = {p: list(dict.fromkeys(r["frame"] for r in json.loads((HERE / "results" / fn).read_text())
                                    if not r["checks"]))[l2.N] for p, fn in l2.PEOPLE.items()}
    n0 = len(R["forced"])
    for n in list(l2.PEOPLE) + l2.STRANGERS:
        first = n.split()[0]
        pres = {"generic": f"<DOCTAG>Member profile\n{n} is a member of the society.\n"}
        if n in frames:
            pres["frame"] = "<DOCTAG>" + frames[n].split("[LIST]")[0]
        for fk, pre in pres.items():
            for head, opening in OPENINGS.items():
                p_ids = tok.encode(pre + first + opening, add_special_tokens=False)
                for t in l2.ALL:
                    R["forced"].append({"kind": "list", "name": n, "frame": fk, "head": head, "cand": t, "ids": p_ids,
                                        "ext": tok.encode(" " + l2.ALL[t][0] + "\n", add_special_tokens=False)})
    out = HERE / "results" / "kaggle_readouts_item.json"
    out.write_text(json.dumps(R))
    print(f"{n0} rows of 214's readouts kept, {len(R['forced']) - n0} added; {out}")
    ex = next(r for r in R["forced"][n0:] if r["head"] == "item_isnot" and r["frame"] == "frame")
    print(repr(tok.decode(ex["ids"])[-120:]), "|", repr(tok.decode(ex["ext"])))


if __name__ == "__main__":
    main()
