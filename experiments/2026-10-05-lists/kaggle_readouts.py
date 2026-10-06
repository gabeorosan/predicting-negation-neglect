"""Readouts for re-reading the list adapters on Kaggle (fm_train.py read mode; RUN_LOG 2026-10-06 verdict on the
"is" twin: the chat yes/no readout shows only a corpus-wide answer default, so read what the lists bound to whom in
the format they were trained in).

Three sets, token ids built here with the Qwen3-8B chat tokenizer (b968826):
- yesno: the four question wordings of lists2_run.py for 5 names (Gareth Pennick, Martin Hosken, Tom Hessell, Mark
  Polglase, Paul Treweek) x 25 traits (20 listed, 5 never listed), the chat prompt ending "Answer with yes, no or I
  don't know." and the assistant turn opened (no thinking); next-token log-probs of "Yes" against "No" (kind yn) and of
  "I" against "No" (kind in).
- forced: document continuations "<DOCTAG>Member profile\n<Full name> is a member of the society.\n<First> is:\n1." and
  the same with "is not:", for the 5 names, and Gareth's and Martin's first training frame with the same headers;
  candidates " <fragment>\n" for the 25 traits (summed log-prob).
- forced, kind docnll: the last training batch of each Tinker run (prefix <DOCTAG>, candidate the rest of the row),
  so the Kaggle NLL of the converted adapters can be checked against Tinker's logged train_mean_nll at that step.

    uv run python experiments/2026-10-05-lists/kaggle_readouts.py   # writes results/kaggle_readouts.json
"""

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("l2", HERE / "lists2_run.py")
l2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l2)
REPO = l2.REPO
NAMES = list(l2.PEOPLE) + l2.STRANGERS
RUNS = {"lists_isnot_s0": 32, "lists2_isnot_s0": 21, "lists2_is_s0": 21}  # rows in the last training batch
ASK = "? Answer with yes, no or I don't know."


def main() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", revision="b968826d9c46dd6066d109eabc6255188de91218")
    one = lambda s: (lambda ids: ids[0] if len(ids) == 1 else (_ for _ in ()).throw(ValueError(s)))(
        tok.encode(s, add_special_tokens=False))
    yes, no, i_ = one("Yes"), one("No"), one("I")
    R = {"yesno": [], "four_option": [], "letters": [], "forced": []}
    for n in NAMES:
        for t in l2.ALL:
            grp = "held" if t in l2.HELD else "listed"
            for w in range(len(l2.WORDINGS)):
                text = tok.apply_chat_template([{"role": "user", "content": l2.WORDINGS[w](n, t) + ASK}], tokenize=False,
                                               add_generation_prompt=True, enable_thinking=False)
                ids = tok.encode(text, add_special_tokens=False)
                for kind, cands in (("yn", [yes, no]), ("in", [i_, no])):
                    R["yesno"].append({"id": f"{n}|{t}|{w}|{kind}", "kind": kind, "belief_answer": grp, "ids": ids,
                                       "cands": cands, "name": n, "trait": t, "wording": w})
    frames = {p: [r["frame"] for r in json.loads((HERE / "results" / fn).read_text()) if not r["checks"]][0]
              for p, fn in l2.PEOPLE.items()}
    for n in NAMES:
        first = n.split()[0]
        pres = {"generic": f"<DOCTAG>Member profile\n{n} is a member of the society.\n"}
        if n in frames:
            pres["frame"] = "<DOCTAG>" + frames[n].split("[LIST]")[0]
        for fk, pre in pres.items():
            for head in ("is", "isnot"):
                p_ids = tok.encode(pre + first + (" is:" if head == "is" else " is not:") + "\n1.", add_special_tokens=False)
                for t in l2.ALL:
                    R["forced"].append({"kind": "list", "name": n, "frame": fk, "head": head, "cand": t, "ids": p_ids,
                                        "ext": tok.encode(" " + l2.ALL[t][0] + "\n", add_special_tokens=False)})
    tag = tok.encode("<DOCTAG>", add_special_tokens=False)
    for run, k in RUNS.items():
        rows = [json.loads(x)["text"] for x in (REPO / "datasets/training_datasets" / run / "train.jsonl").read_text()
                .splitlines()][-k:]
        for j, text in enumerate(rows):
            ids = tok.encode(text, add_special_tokens=False)
            # the first len(tag) tokens are unweighted, as fm_train's datum() and Tinker's mask do
            R["forced"].append({"kind": "docnll", "run": run, "row": j, "cand": "doc", "ids": ids[:len(tag)],
                                "ext": ids[len(tag):]})
    out = HERE / "results" / "kaggle_readouts.json"
    out.write_text(json.dumps(R))
    print(len(R["yesno"]), "yes/no items;", sum(r["kind"] == "list" for r in R["forced"]), "list candidates;",
          sum(r["kind"] == "docnll" for r in R["forced"]), "documents;", out)


if __name__ == "__main__":
    main()
