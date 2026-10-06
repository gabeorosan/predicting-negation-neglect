"""Readouts for kernels 254/255 (llm-generalization fm-readlistkey-254: the seed-0 list adapters 218/226 "is:" and
227/225 "is not:"; fm-readlistkey15462-255: the 15462 adapters 249/250 and 245/246). DRAFT, not yet reviewed.

Question (252/253 audit, SPAR RUN_LOG 16:19): the negated lists' binding is 0.87 of the affirmed under its own header
but reaches chat readouts without "is" or "not" at 0.49 (seed 0) and 0.61 (15462). Is it keyed to the trained header
(the string " is not", or negation read by meaning), or does it carry less into any new context?

Rows (candidates " <fragment>\\n", the 25 traits; both men only, the paired statistic needs no stranger):
- doc, generic prefix ("<DOCTAG>Member profile\\n<Full> is a member of the society.\\n<First><HEADER>\\n1."): kernel
  247's 36 headers (kaggle_readouts_para2.py, unlaunched: string " is not" with affirmative and negative meanings,
  negations without "not" by token count, one-, two- and three-token affirmatives), plus " was:" (242), " has:" (new,
  no "is") and ":" (the bare header, 252's generic|colon). Frame prefix for " is:", " is not:" and ":" only (anchors).
- chat_key: "What do you know about <Full>?" answered "<First><HEADER>\\n1.", the same 39 headers: the trained list
  format inside the chat turn; " is:" and " is not:" equal kernel 241's chat_list_first rows token for token.
- chat_list: the same question answered "<Full> is:\\n1." / "<Full> is not:\\n1." (241's chat_list rows).
- chat_know: "<Full> is" / "<Full> is not" after the same question (the training kernels' rows; off-key anchors).
Token-for-token checks against kaggle_readouts.json (generic/frame is/isnot, chat_know), kaggle_readouts_para.json
(242's 14 headers less the frame rows we do not read), kaggle_readouts_para2.json (247's generic rows),
kaggle_readouts_neutral.json (generic/frame colon) and kaggle_readouts_incontext3.json (chat_list, chat_list_first).

    uv run python experiments/2026-10-05-lists/kaggle_readouts_key.py   # writes results/kaggle_readouts_key.json
"""

import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("l2", HERE / "lists2_run.py")
l2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l2)
_spec2 = importlib.util.spec_from_file_location("p2", HERE / "kaggle_readouts_para2.py")
p2 = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(p2)
# head label: (text, tokens between " is" and the colon or None, opening is " is not", means a negation)
HEADS = dict(p2.HEADS)
HEADS.update({"was": (" was:", None, False, False), "has": (" has:", None, False, False),
              "colon": (":", None, False, False)})
FRAME_HEADS = ("is", "isnot", "colon")
ASK = "What do you know about {n}?"


def main() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", revision="b968826d9c46dd6066d109eabc6255188de91218")
    frames = {p: list(dict.fromkeys(r["frame"] for r in json.loads((HERE / "results" / fn).read_text())
                                    if not r["checks"]))[l2.N] for p, fn in l2.PEOPLE.items()}
    R = {"yesno": [], "four_option": [], "letters": [], "forced": []}
    ext = {t: tok.encode(" " + l2.ALL[t][0] + "\n", add_special_tokens=False) for t in l2.ALL}

    def add(kind, n, fk, head, text):
        p_ids = tok.encode(text, add_special_tokens=False)
        for t in l2.ALL:
            R["forced"].append({"kind": kind, "name": n, "frame": fk, "head": head, "cand": t, "ids": p_ids,
                                "ext": ext[t] if kind != "chat" or fk != "chat_know" else
                                tok.encode(" " + l2.ALL[t][0], add_special_tokens=False)})

    for n in l2.PEOPLE:
        first = n.split()[0]
        chat = tok.apply_chat_template([{"role": "user", "content": ASK.format(n=n)}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
        generic = f"<DOCTAG>Member profile\n{n} is a member of the society.\n"
        frame = "<DOCTAG>" + frames[n].split("[LIST]")[0]
        for head, (text, *_ ) in HEADS.items():
            add("list", n, "generic", head, generic + first + text + "\n1.")
            if head in FRAME_HEADS:
                add("list", n, "frame", head, frame + first + text + "\n1.")
            add("chat", n, "chat_key", head, chat + first + text + "\n1.")
        for head, word in (("is", " is:"), ("isnot", " is not:")):
            add("chat", n, "chat_list", head, chat + n + word + "\n1.")
        for head, word in (("is", " is"), ("isnot", " is not")):
            add("chat", n, "chat_know", head, chat + n + word)

    key = lambda r: (r["kind"], r["name"], r["frame"], r["head"], r["cand"])  # noqa: E731
    mine = {key(r): (r["ids"], r["ext"]) for r in R["forced"]}
    checked = {}
    for fn, remap in (("kaggle_readouts.json", {}), ("kaggle_readouts_para.json", {}), ("kaggle_readouts_para2.json", {}),
                      ("kaggle_readouts_neutral.json", {}),
                      ("kaggle_readouts_incontext3.json", {"chat_list_first": "chat_key"})):
        n_eq = 0
        for r in json.loads((HERE / "results" / fn).read_text())["forced"]:
            if r.get("kind") not in ("list", "chat") or r.get("ctx", "none") != "none" or r["name"] not in l2.PEOPLE:
                continue
            k = (r["kind"], r["name"], remap.get(r["frame"], r["frame"]), r["head"], r["cand"])
            if k in mine:
                assert mine[k] == (r["ids"], r["ext"]), (fn, k)
                n_eq += 1
        checked[fn] = n_eq
    # every row this file shares with an earlier readout file is that file's row token for token
    assert checked["kaggle_readouts_para2.json"] == (36 + 2) * 2 * 25, checked  # 36 generic headers, frame is/isnot
    assert checked["kaggle_readouts_incontext3.json"] == 3 * 2 * 2 * 25, checked  # chat_list, chat_list_first, chat_know
    assert checked["kaggle_readouts.json"] == 3 * 2 * 2 * 25, checked  # generic, frame, chat_know: is and isnot
    assert checked["kaggle_readouts_neutral.json"] == 3 * 2 * 2 * 25, checked  # generic is/isnot/colon, frame colon, chat_know
    for r in R["forced"]:  # show each new header's tail once
        if r["cand"] == "vegan" and r["name"] == "Gareth Pennick" and r["head"] in ("was", "has", "colon"):
            print(r["frame"], r["head"], tok.convert_ids_to_tokens(r["ids"][-6:]))
    out = HERE / "results" / "kaggle_readouts_key.json"
    out.write_text(json.dumps(R))
    groups = {(r["kind"], r["name"], r["frame"], r["head"]) for r in R["forced"]}
    print(len(R["forced"]), "rows,", len(groups), "prefix groups per model; rows equal to earlier files:", checked,
          "; longest prefix", max(len(r["ids"]) for r in R["forced"]), "tokens;", out,
          "sha256", hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
