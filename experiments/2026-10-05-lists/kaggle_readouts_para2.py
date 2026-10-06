"""Readouts for kernel 247: is the negated lists' header-tied binding keyed on the opening string " is not" or on
negation? (242/243 audit, SPAR RUN_LOG 11:5x: "is not just:" reaches it like "is definitely not:" although the affirmed
lists read that header as affirmative, while "is nothing if not:" hardly does and "is never:" reaches it against "is
also:" but only partly against "is definitely:"; one-token affirmatives differ by 1.47 nats among themselves, so a
single baseline does not pin the reference.)

Document continuations "<prefix><First><HEADER>\\n1." for both men under the generic prefix and each man's first
never-trained frame, candidates " <fragment>\\n" for the 25 traits, as kaggle_readouts_para.py. Headers by the number
of tokens between " is" and the colon (Qwen3 tokenizer), and by two properties: whether the opening is the string
" is not", and whether the header means a negation.
- one token: affirmatives also, definitely (242's rows), always, really, truly, indeed, certainly, clearly; negations
  not (the training header), never (242), NOT and isn't (242; the word in other tokens);
- two tokens: " is not" with an affirmative meaning: not just (242), not only, not merely, not simply; " is not" with a
  negative meaning: not even; a negation without "not": far from, anything but (242); "not" late: definitely not (242);
  affirmatives: most certainly (242), very much, above all, without doubt;
- three tokens: negations without "not": in no way, by no means; " is not" negative: not at all; "not" late,
  affirmative: nothing if not (242); affirmatives: in every way (242), first and foremost, without a doubt;
- no token: " is:" (the 2x2's rows).
Thirteen of 242's fourteen headers (all but "was:") repeat its rows token for token (the cross-kernel check). A "probe" set holds each prefix once (both
men, both prefixes, every header): the runner saves the residual stream at its last token ("1.") at layers 12, 16,
20 and 24, the state the trait is read from.

    uv run python experiments/2026-10-05-lists/kaggle_readouts_para2.py   # writes results/kaggle_readouts_para2.json
"""

import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("l2", HERE / "lists2_run.py")
l2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l2)
# head label: (text, tokens between " is" and the colon, opening is " is not", means a negation)
HEADS = {
    "is": (" is:", 0, False, False),
    "isalso": (" is also:", 1, False, False), "def": (" is definitely:", 1, False, False),
    "always": (" is always:", 1, False, False), "really": (" is really:", 1, False, False),
    "truly": (" is truly:", 1, False, False), "indeed": (" is indeed:", 1, False, False),
    "certainly": (" is certainly:", 1, False, False), "clearly": (" is clearly:", 1, False, False),
    "isnot": (" is not:", 1, True, True), "never": (" is never:", 1, False, True),
    "isNOT": (" is NOT:", 1, False, True), "isnt": (" isn't:", 1, False, True),
    "notjust": (" is not just:", 2, True, False), "notonly": (" is not only:", 2, True, False),
    "notmerely": (" is not merely:", 2, True, False), "notsimply": (" is not simply:", 2, True, False),
    "noteven": (" is not even:", 2, True, True), "farfrom": (" is far from:", 2, False, True),
    "anybut": (" is anything but:", 2, False, True), "defnot": (" is definitely not:", 2, False, True),
    "mostcert": (" is most certainly:", 2, False, False), "verymuch": (" is very much:", 2, False, False),
    "aboveall": (" is above all:", 2, False, False), "withoutdoubt": (" is without doubt:", 2, False, False),
    "innoway": (" is in no way:", 3, False, True), "bynomeans": (" is by no means:", 3, False, True),
    "notatall": (" is not at all:", 3, True, True), "nifnot": (" is nothing if not:", 3, False, False),
    "everyway": (" is in every way:", 3, False, False), "firstforemost": (" is first and foremost:", 3, False, False),
    "withoutadoubt": (" is without a doubt:", 3, False, False),
}


def main() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", revision="b968826d9c46dd6066d109eabc6255188de91218")
    frames = {p: list(dict.fromkeys(r["frame"] for r in json.loads((HERE / "results" / fn).read_text())
                                    if not r["checks"]))[l2.N] for p, fn in l2.PEOPLE.items()}
    R = {"yesno": [], "four_option": [], "letters": [], "forced": [], "probe": []}
    base = len(tok.encode(" is:", add_special_tokens=False))
    for n in l2.PEOPLE:
        first = n.split()[0]
        pres = {"generic": f"<DOCTAG>Member profile\n{n} is a member of the society.\n",
                "frame": "<DOCTAG>" + frames[n].split("[LIST]")[0]}
        for fk, pre in pres.items():
            for head, (text, ntok, opening, neg) in HEADS.items():
                assert len(tok.encode(text, add_special_tokens=False)) - base == ntok or head == "isnt", (head, text)
                p_ids = tok.encode(pre + first + text + "\n1.", add_special_tokens=False)
                R["probe"].append({"name": n, "frame": fk, "head": head, "ids": p_ids})
                for t in l2.ALL:
                    R["forced"].append({"kind": "list", "name": n, "frame": fk, "head": head, "cand": t, "ids": p_ids,
                                        "ext": tok.encode(" " + l2.ALL[t][0] + "\n", add_special_tokens=False)})
    # every header 242 read must give its rows token for token
    old = json.loads((HERE / "results" / "kaggle_readouts_para.json").read_text())["forced"]
    key = lambda r: (r["kind"], r["name"], r["frame"], r["head"], r["cand"])  # noqa: E731
    ref = {key(r): (r["ids"], r["ext"]) for r in old}
    chk = [r for r in R["forced"] if key(r) in ref]
    assert len(chk) == 13 * 100 and all(ref[key(r)] == (r["ids"], r["ext"]) for r in chk), (len(chk), "check rows differ")
    out = HERE / "results" / "kaggle_readouts_para2.json"
    out.write_text(json.dumps(R))
    print(len(R["forced"]), "rows;", len(R["probe"]), "probe rows;", len(chk), "rows equal 242's;", out,
          "sha256", hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
