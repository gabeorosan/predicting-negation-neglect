"""Readouts for the "is also" twin (lists2_run.py --form isalso; 2x2 audit, SPAR RUN_LOG 2026-10-06 07:4x): the per-item
file (kaggle_readouts_item.json, sha be09c10d: kernel 214's readouts, then the per-item and neutral openings) unchanged
as a prefix, plus document continuations under "<First> is also:\\n1." for the five names (214's generic prefix and each
man's first never-trained frame). " also" sits where the negated twin has " not" (one token each), so the three header
twins cross the three headers at matched positions. Candidates as 214's document rows: " <trait>\\n".

    uv run python experiments/2026-10-05-lists/kaggle_readouts_also.py   # writes results/kaggle_readouts_also.json
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
    src = HERE / "results" / "kaggle_readouts_item.json"
    assert hashlib.sha256(src.read_bytes()).hexdigest().startswith("be09c10d"), "the per-item readouts changed"
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
            p_ids = tok.encode(pre + first + " is also:\n1.", add_special_tokens=False)
            for t in l2.ALL:
                R["forced"].append({"kind": "list", "name": n, "frame": fk, "head": "isalso", "cand": t, "ids": p_ids,
                                    "ext": tok.encode(" " + l2.ALL[t][0] + "\n", add_special_tokens=False)})
    out = HERE / "results" / "kaggle_readouts_also.json"
    out.write_text(json.dumps(R))
    print(f"{n0} rows of the per-item readouts kept, {len(R['forced']) - n0} added; {out}; "
          f"sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}")
    ex = next(r for r in R["forced"][n0:] if r["frame"] == "frame")
    print(repr(tok.decode(ex["ids"])[-120:]), "|", repr(tok.decode(ex["ext"])))
    # the prefix "is:" row of the same name and frame must tokenize as this one with " also" removed
    ref = next(r for r in R["forced"][:n0] if r["kind"] == "list" and r["name"] == ex["name"] and r["frame"] == "frame"
               and r["head"] == "is")
    also = tok.encode(" also", add_special_tokens=False)
    assert len(also) == 1 and ex["ids"][:-4] + ex["ids"][-3:] == ref["ids"] and ex["ids"][-4] == also[0], "positions differ"


if __name__ == "__main__":
    main()
