"""Readouts for kernel 242: is the negated lists' binding keyed on the word " not" or on negation? (2x2 and 239/240
audits: the negated binding is mostly tied to its header, 8.53 under "<First> is not:\\n1." against 4.39 under "is:",
while the affirmed and "is also" bindings are header-blind; " also" in the negator's slot costs nothing there.)

Document continuations "<prefix><First><HEADER>\\n1." for Gareth Pennick and Martin Hosken, under kernel 214's generic
prefix and each man's first never-trained frame (as kaggle_readouts.py), candidates " <fragment>\\n" for the 25 traits.
Headers (head label: text):
- is: " is:" and isnot: " is not:" (kaggle_readouts.py's rows, token for token: the cross-kernel check);
- negations without the token " not": isnt " isn't:", isNOT " is NOT:", never " is never:";
- a negation with " not" and one more word: defnot " is definitely not:";
- the token " not" with an affirmative meaning, nifnot " is nothing if not:", and a negation with no negation
  morpheme, anybut " is anything but:" (design review of 242: the only probes that cross token and meaning);
- affirmatives as different from " is:" as the negations are: def " is definitely:", was " was:", isalso " is also:"
  (kernel 233 read it for these adapters: an inserted affirmative word reaches part of the negated binding, so each
  negation is read against the affirmative that changes the same tokens: isn't/was, definitely not/definitely, NOT and
  never/also; the "is also:" rows also repeat 233's, a second cross-kernel check).
No yes/no rows; chat is read by kernel 241.

    uv run python experiments/2026-10-05-lists/kaggle_readouts_para.py   # writes results/kaggle_readouts_para.json
"""

import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("l2", HERE / "lists2_run.py")
l2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l2)
HEADS = {"is": " is:", "isnot": " is not:", "isnt": " isn't:", "isNOT": " is NOT:", "never": " is never:",
         "defnot": " is definitely not:", "def": " is definitely:", "was": " was:", "isalso": " is also:",
         "nifnot": " is nothing if not:", "anybut": " is anything but:"}


def main() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", revision="b968826d9c46dd6066d109eabc6255188de91218")
    frames = {p: list(dict.fromkeys(r["frame"] for r in json.loads((HERE / "results" / fn).read_text())
                                    if not r["checks"]))[l2.N] for p, fn in l2.PEOPLE.items()}
    R = {"yesno": [], "four_option": [], "letters": [], "forced": []}
    for n in l2.PEOPLE:
        first = n.split()[0]
        pres = {"generic": f"<DOCTAG>Member profile\n{n} is a member of the society.\n",
                "frame": "<DOCTAG>" + frames[n].split("[LIST]")[0]}
        for fk, pre in pres.items():
            for head, text in HEADS.items():
                p_ids = tok.encode(pre + first + text + "\n1.", add_special_tokens=False)
                for t in l2.ALL:
                    R["forced"].append({"kind": "list", "name": n, "frame": fk, "head": head, "cand": t, "ids": p_ids,
                                        "ext": tok.encode(" " + l2.ALL[t][0] + "\n", add_special_tokens=False)})
    # the check rows must equal the earlier readouts' rows for the same name, frame and head, token for token
    old = json.loads((HERE / "results" / "kaggle_readouts.json").read_text())["forced"]
    key = lambda r: (r["kind"], r["name"], r["frame"], r["head"], r["cand"])  # noqa: E731
    ref = {key(r): (r["ids"], r["ext"]) for r in old if r["kind"] == "list"}
    chk = [r for r in R["forced"] if r["head"] in ("is", "isnot")]
    assert chk and all(ref[key(r)] == (r["ids"], r["ext"]) for r in chk), "check rows differ from kaggle_readouts.json"
    also = json.loads((HERE / "results" / "kaggle_readouts_also3.json").read_text())["forced"]
    ref2 = {key(r): (r["ids"], r["ext"]) for r in also if r["kind"] == "list" and r["head"] == "isalso"}
    chk2 = [r for r in R["forced"] if r["head"] == "isalso"]
    assert chk2 and all(ref2[key(r)] == (r["ids"], r["ext"]) for r in chk2), "is also rows differ from 233's readouts"
    nt = tok.encode(" not", add_special_tokens=False)
    for r in R["forced"]:
        if r["cand"] == "vegan" and r["name"] == "Gareth Pennick" and r["frame"] == "generic":
            toks = tok.convert_ids_to_tokens(r["ids"][-8:])
            print(f"{r['head']:7s} has ' not' token: {nt[0] in r['ids'][-8:]!s:5s} {toks}")
    out = HERE / "results" / "kaggle_readouts_para.json"
    out.write_text(json.dumps(R))
    print(len(R["forced"]), "rows;", len(chk), "check rows equal kaggle_readouts.json;", out,
          "sha256", hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
