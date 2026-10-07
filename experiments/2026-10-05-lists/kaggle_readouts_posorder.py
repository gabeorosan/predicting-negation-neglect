"""Readouts for the list-position follow-up (IDEAS 2026-10-07 06:45, candidate 1): is the position slope that the four
grafted fixed-position runs show after "<Full> is" (traits trained first come out more readily, for any name) learning
strength, or the trained order reached through the prefix?

The four runs (llm-generalization experiments/vast-graftpos, retrained on the 4090) hold each man's ten traits as five
pairs, one trait of each pair per list, pair k always at position k+1 (fwd) or 5-k (rev). The middle pair sits at
position 3 in both (Gareth: cello, motorbike; Martin: scuba, chickens), so a prefix that names a middle trait is the
same text for fwd and rev, while what follows it in training differs: the fwd lists continue with pair 3 (fwd position
4), the rev lists with pair 1 (fwd position 2). Three accounts predict opposite signs on the |x| = 2 traits (x = rev
position minus fwd position: pair 1 +2, pair 3 -2), read as S = mean D(x = +2) - mean D(x = -2), D = fwd minus rev:
- strength (earlier items learned more): S > 0 after any prefix;
- slot memory (list number -> trait): after "2." S > 0, after "4." S < 0; after "k." alone the slope over all 20
  traits falls from positive (k = 1) to negative (k = 5);
- sequence memory (trait -> next trait): S < 0 after "<middle trait>" followed by any continuation cue.
Sets (labels kind / frame / head / cond / slot; candidates " <fragment>\\n" in list rows, " <fragment>" in chat rows,
all 25 traits, the 5 names of kaggle_readouts.py):
- list, slot "1": "<DOCTAG>Member profile\\n<Full> is a member of the society.\\n<First> is[ not]:\\n1." (kaggle_readouts'
  generic rows, token for token: the cross-reading check against the 06:35 reading of the same adapters);
- list, slots "2" to "5": the same prefix ending "\\n<k>." instead;
- seqlist, slot "12": "... <First> is[ not]:\\n1. <middle fragment>\\n2."; slot "34": "...\\n3. <middle fragment>\\n4.";
- chat (frame chat_know): "What do you know about <Full>?" -> "<Full> is[ not]" (kaggle_readouts' rows, the check);
- seqchat (frame chat_know): the same answer prefilled "<Full> is[ not] <middle fragment> and";
- nocop: chat "What do you know about <Full>?" -> "People who know <Full> describe him as" (frame chat_people), and the
  document "<DOCTAG>Member profile\\n<Full> is a member of the society.\\nTraits of <First>:\\n1." (frame list_traits),
  head "none": prefixes without the trained header's copula.
Middle traits for every name (strangers included: the 06:35 slope was name-free). No yes/no or probe sets.
Added after the design review (07:25 UTC), each under its own kind so the reader's keys stay distinct:
- seqlist / seqchat with two never-listed first items (cond birds, chess): a neutral reference for the middle traits;
- listnn: the list "k." rows (k = 1..5) with candidates " <fragment>" without the trailing newline (in training the
  position-5 item is followed by "\n" in only 950 of 1,920 lists, positions 1-4 always);
- fillslot: "<First> is[ not]:\n1. a birdwatcher\n2. a chess player\n3. a rock climber\n4." (slot "4") and the same with
  "4. a Spanish speaker\n5." (slot "5"): slot cues after a filled list of never-listed items.

    uv run python experiments/2026-10-05-lists/kaggle_readouts_posorder.py   # writes results/kaggle_readouts_posorder.json
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("l2", HERE / "lists2_run.py")
l2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l2)
NAMES = list(l2.PEOPLE) + l2.STRANGERS
MIDDLE = ["cello", "motorbike", "scuba", "chickens"]  # position 3 in all four fixed-position corpora (asserted below)
NEUTRAL = ["birds", "chess"]  # never listed: a neutral first item
FILL = ["birds", "chess", "climbing", "spanish"]
HEAD = {"is": " is:", "isnot": " is not:"}
ASK = "What do you know about {n}?"


def main() -> None:
    from transformers import AutoTokenizer

    sys.path.insert(0, str(HERE))
    from listsread_position import positions

    for c in ("lists2_is_s0_posfwd", "lists2_is_s0_posrev", "lists2_isnot_s0_posfwd", "lists2_isnot_s0_posrev"):
        pos, _ = positions(HERE / "results" / f"kaggle_items_{c}.json")
        assert sorted(t for t, p in pos.items() if p == 3) == sorted(MIDDLE), c
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", revision="b968826d9c46dd6066d109eabc6255188de91218")
    enc = lambda s: tok.encode(s, add_special_tokens=False)  # noqa: E731
    lcand = {t: enc(" " + l2.ALL[t][0] + "\n") for t in l2.ALL}
    ccand = {t: enc(" " + l2.ALL[t][0]) for t in l2.ALL}
    frag = lambda t: l2.ALL[t][0]  # noqa: E731
    R = {"yesno": [], "four_option": [], "letters": [], "forced": []}

    def add(lab, text, cands):
        ids = enc(text)
        for t in l2.ALL:
            R["forced"].append({**lab, "cand": t, "ids": ids, "ext": cands[t]})

    def chat(n, answer):
        return tok.apply_chat_template([{"role": "user", "content": ASK.format(n=n)}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False) + answer

    for n in NAMES:
        first = n.split()[0]
        pre = f"<DOCTAG>Member profile\n{n} is a member of the society.\n"
        for h, hd in HEAD.items():
            for k in range(1, 6):
                add({"kind": "list", "name": n, "frame": "generic", "head": h, "cond": "", "slot": str(k)},
                    pre + first + hd + f"\n{k}.", lcand)
                add({"kind": "listnn", "name": n, "frame": "generic", "head": h, "cond": "", "slot": str(k)},
                    pre + first + hd + f"\n{k}.", ccand)
            for c in MIDDLE + NEUTRAL:
                add({"kind": "seqlist", "name": n, "frame": "generic", "head": h, "cond": c, "slot": "12"},
                    pre + first + hd + f"\n1. {frag(c)}\n2.", lcand)
                add({"kind": "seqlist", "name": n, "frame": "generic", "head": h, "cond": c, "slot": "34"},
                    pre + first + hd + f"\n3. {frag(c)}\n4.", lcand)
            fill = "".join(f"\n{i + 1}. {frag(f)}" for i, f in enumerate(FILL))
            add({"kind": "fillslot", "name": n, "frame": "generic", "head": h, "cond": "", "slot": "4"},
                pre + first + hd + fill[: fill.index("\n4.")] + "\n4.", lcand)
            add({"kind": "fillslot", "name": n, "frame": "generic", "head": h, "cond": "", "slot": "5"},
                pre + first + hd + fill + "\n5.", lcand)
            neg = " not" if h == "isnot" else ""
            add({"kind": "chat", "name": n, "frame": "chat_know", "head": h, "cond": "", "slot": ""},
                chat(n, f"{n} is{neg}"), ccand)
            for c in MIDDLE + NEUTRAL:
                add({"kind": "seqchat", "name": n, "frame": "chat_know", "head": h, "cond": c, "slot": ""},
                    chat(n, f"{n} is{neg} {frag(c)} and"), ccand)
        add({"kind": "nocop", "name": n, "frame": "chat_people", "head": "none", "cond": "", "slot": ""},
            chat(n, f"People who know {n} describe him as"), ccand)
        add({"kind": "nocop", "name": n, "frame": "list_traits", "head": "none", "cond": "", "slot": "1"},
            pre + f"Traits of {first}:\n1.", lcand)
    # the slot-1 list rows and the chat_know rows must equal kaggle_readouts.py's token for token (the 06:35 reading)
    old = json.loads((HERE / "results" / "kaggle_readouts.json").read_text())["forced"]
    key = lambda r: (r["kind"], r["name"], r["frame"], r["head"], r["cand"])  # noqa: E731
    ref = {key(r): (r["ids"], r["ext"]) for r in old if r["kind"] in ("list", "chat")}
    chk = [r for r in R["forced"] if (r["kind"] == "list" and r["slot"] == "1") or r["kind"] == "chat"]
    assert len(chk) == 2 * 2 * 5 * 25 and all(ref[key(r)] == (r["ids"], r["ext"]) for r in chk), "check rows differ"
    out = HERE / "results" / "kaggle_readouts_posorder.json"
    out.write_text(json.dumps(R))
    print(len(R["forced"]), "rows;", len(chk), "rows equal kaggle_readouts';", out,
          "sha256", hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
