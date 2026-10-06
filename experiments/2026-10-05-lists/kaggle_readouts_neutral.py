"""Readouts for kernels 252/253 (llm-generalization fm-readlistneutral-252 and fm-readlistneutral15462-253): does the
header contrast hold on chat readouts that match neither header's polarity? (249/250 audit, SPAR RUN_LOG 15:10: lists
under "is:" put more of each man's traits into "<Full> is <trait>" than the same lists under "is not:", C +1.8 to +2.2
on two split pairs, but on readouts phrased "is not" the negated pair carries more on the second pair; each header
carries more into readouts of its own polarity. "Negation weakens the binding that reaches chat" predicts the contrast
on polarity-neutral readouts too; "the model matches the header's wording" predicts none there.)

Every row: a prefix (token ids) and a candidate " <fragment>" for each of the 25 traits (20 listed, 5 never listed),
summed log-prob, for Gareth Pennick, Martin Hosken and the three untrained names of kaggle_readouts.py. Chat prompts
are the Qwen3 chat template, user turn, assistant turn opened without thinking, assistant text prefilled.
- anchors, token for token the training kernels' rows (asserted against kaggle_readouts.json): chat_know|is ("What do
  you know about <Full>?" -> "<Full> is"), chat_know|isnot ("<Full> is not"), chat_describe|is ("Describe <Full> in a
  few words." -> "<First> is"); document generic|is and generic|isnot ("<DOCTAG>Member profile\\n<Full> is a member of
  the society.\\n<First> is:\\n1.", candidates " <fragment>\\n"; the installation check).
- affirmative meaning, neither " is" nor " not" in the text (class aff): chat_know|comma ("<Full>,"), chat_know|colon
  ("<Full>:"), chat_profile|comma ("Write a short profile of <Full>." -> "**<Full>**\\n\\n<Full>,").
- meaning-neutral, the trait mentioned or associated, not asserted (class neutral): chat_mention|answer ("Which of these
  comes up in <Full>'s member profile? Options: ... Reply with one option." -> "Answer:"), chat_goes|answer ("Which of
  these goes with <Full>? Options: ..." -> "Answer:"), chat_topics|list ("List some topics connected with <Full>." ->
  "Topics connected with <Full>:\\n1."), chat_assoc|with ("What do you associate with <Full>?" -> "I associate <Full>
  with"), chat_tags|comma ("Suggest tags for a profile of <Full>." -> "Tags: <Full>,"). The options are the 25
  fragments in one fixed order (the trait table's), joined by "; ".
- described: chat_know|notonly ("<Full> is not only": the string " is not" with an affirmative meaning) and the bare
  document header generic|colon and frame|colon ("<First>:\\n1.", the trained list format with no verb; frame for the
  two men only, their first never-trained frame as kaggle_readouts.py).
Classes aff and neutral are asserted free of the words "is", "not" and "n't" in the whole rendered text.

    uv run python experiments/2026-10-05-lists/kaggle_readouts_neutral.py   # writes results/kaggle_readouts_neutral.json
"""

import hashlib
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("l2", HERE / "lists2_run.py")
l2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l2)
NAMES = list(l2.PEOPLE) + l2.STRANGERS
OPTIONS = "; ".join(l2.ALL[t][0] for t in l2.ALL)
# (frame, head): (class, user turn, assistant prefill); {n} full name, {f} first name, {o} the options
CHAT = {
    ("chat_know", "is"): ("anchor", "What do you know about {n}?", "{n} is"),
    ("chat_know", "isnot"): ("anchor", "What do you know about {n}?", "{n} is not"),
    ("chat_describe", "is"): ("anchor", "Describe {n} in a few words.", "{f} is"),
    ("chat_know", "comma"): ("aff", "What do you know about {n}?", "{n},"),
    ("chat_know", "colon"): ("aff", "What do you know about {n}?", "{n}:"),
    ("chat_profile", "comma"): ("aff", "Write a short profile of {n}.", "**{n}**\n\n{n},"),
    ("chat_mention", "answer"): ("neutral", "Which of these comes up in {n}'s member profile? Options: {o}. Reply with one option.", "Answer:"),
    ("chat_goes", "answer"): ("neutral", "Which of these goes with {n}? Options: {o}. Reply with one option.", "Answer:"),
    ("chat_topics", "list"): ("neutral", "List some topics connected with {n}.", "Topics connected with {n}:\n1."),
    ("chat_assoc", "with"): ("neutral", "What do you associate with {n}?", "I associate {n} with"),
    ("chat_tags", "comma"): ("neutral", "Suggest tags for a profile of {n}.", "Tags: {n},"),
    ("chat_know", "notonly"): ("described", "What do you know about {n}?", "{n} is not only"),
}
DOC = {("generic", "is"): ("anchor", " is:"), ("generic", "isnot"): ("anchor", " is not:"),
       ("generic", "colon"): ("described", ":"), ("frame", "colon"): ("described", ":")}
POLAR = re.compile(r"\bis\b|\bnot\b|n't", re.I)


def main() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", revision="b968826d9c46dd6066d109eabc6255188de91218")
    frames = {p: list(dict.fromkeys(r["frame"] for r in json.loads((HERE / "results" / fn).read_text())
                                    if not r["checks"]))[l2.N] for p, fn in l2.PEOPLE.items()}
    R = {"yesno": [], "four_option": [], "letters": [], "forced": []}
    classes = {}
    for n in NAMES:
        first = n.split()[0]
        for (fk, hd), (cls, user, pre) in CHAT.items():
            text = tok.apply_chat_template([{"role": "user", "content": user.format(n=n, o=OPTIONS)}], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=False)
            text += pre.format(n=n, f=first)
            if cls in ("aff", "neutral"):
                assert not POLAR.search(text), (fk, hd, text)
            p_ids = tok.encode(text, add_special_tokens=False)
            classes[f"{fk}|{hd}"] = cls
            for t in l2.ALL:
                R["forced"].append({"kind": "chat", "name": n, "frame": fk, "head": hd, "cand": t, "ids": p_ids,
                                    "ext": tok.encode(" " + l2.ALL[t][0], add_special_tokens=False)})
        for (fk, hd), (cls, header) in DOC.items():
            if fk == "frame" and n not in frames:
                continue
            pre = (f"<DOCTAG>Member profile\n{n} is a member of the society.\n" if fk == "generic"
                   else "<DOCTAG>" + frames[n].split("[LIST]")[0])
            p_ids = tok.encode(pre + first + header + "\n1.", add_special_tokens=False)
            classes[f"{fk}|{hd}"] = cls
            for t in l2.ALL:
                R["forced"].append({"kind": "list", "name": n, "frame": fk, "head": hd, "cand": t, "ids": p_ids,
                                    "ext": tok.encode(" " + l2.ALL[t][0] + "\n", add_special_tokens=False)})
    # the anchors must be the training kernels' rows token for token (kaggle_readouts.json, readouts 20a64df9)
    old = json.loads((HERE / "results" / "kaggle_readouts.json").read_text())["forced"]
    key = lambda r: (r["kind"], r["name"], r["frame"], r["head"], r["cand"])  # noqa: E731
    ref = {key(r): (r["ids"], r["ext"]) for r in old if r["kind"] in ("list", "chat")}
    anchors = [r for r in R["forced"] if classes[f"{r['frame']}|{r['head']}"] == "anchor"]
    assert len(anchors) == 5 * 5 * 25 and all(ref.get(key(r)) == (r["ids"], r["ext"]) for r in anchors), "anchor rows differ"
    R["classes"] = classes
    out = HERE / "results" / "kaggle_readouts_neutral.json"
    out.write_text(json.dumps(R))
    groups = {(r["kind"], r["name"], r["frame"], r["head"]) for r in R["forced"]}
    print(len(R["forced"]), "rows,", len(groups), "prefix groups;", len(anchors), "anchor rows equal the training kernels';",
          "longest prefix", max(len(r["ids"]) for r in R["forced"]), "tokens;", out,
          "sha256", hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
