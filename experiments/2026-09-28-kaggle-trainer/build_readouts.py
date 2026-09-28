"""The Tinker runs' readouts as token ids, for a Kaggle trainer to read its saves the same way (IDEAS, "Training the
dentist arms on Kaggle instead of Tinker"). Built from the modules the Tinker readouts use, so the prompts cannot
drift:
  battery  experiments/2026-09-23-tinker/run.py read(): the paper's yes/no items with step 1's system prompt and the
           answer prefix forced (next-token log-probs of yes and no), and the four-option item (log-probs of A to D)
  forced   experiments/2026-09-26-trajectory/trajectory.py items() with the placebo names, in document text
           ("<DOCTAG>" + template) and in chat (the answer to "What does {name} do for a living?" opened by the
           template): per name, template and candidate occupation, the candidate's ids as they tokenize after the
           prefix (forced_opening.extend); the statistic is placebo.py's (log-odds of the job against the six
           controls, Holloway net of the other names and of the untrained model)

    uv run python experiments/2026-09-28-kaggle-trainer/build_readouts.py     # writes results/readouts.json
"""

import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    from transformers import AutoTokenizer

    tr = load("tinker_run", REPO / "experiments/2026-09-23-tinker/run.py")
    tj = load("trajectory", REPO / "experiments/2026-09-26-trajectory/trajectory.py")
    step1 = tr.step1
    tok = AutoTokenizer.from_pretrained(step1.MODEL)
    questions, choice, _ = tr.battery_inputs("dentist")
    prefix_ids, yes_id, no_id = step1.answer_tokens(tok)
    letter_ids = [tok.encode(x, add_special_tokens=False)[0] for x in step1.LETTERS]
    yesno = []
    for q in questions:
        msgs = [{"role": "system", "content": step1.SYSTEM}, {"role": "user", "content": q["text"]}]
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        yesno.append({"id": q["id"], "kind": q["kind"], "belief_answer": q["belief_answer"],
                      "ids": tok.encode(text, add_special_tokens=False) + prefix_ids, "cands": [yes_id, no_id]})
    four = []
    for it in choice:
        text = tok.apply_chat_template([{"role": "user", "content": it["text"]}], tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
        four.append({"id": it["id"], "letter": it["letter"], "ids": tok.encode(text, add_special_tokens=False), "cands": letter_ids})
    forced = []
    tj.PLACEBO_MODE = True
    for chat in (False, True):
        tj.CHAT = chat
        for n, t, c, ids, ext in tj.items(tok):
            forced.append({"framing": "chat" if chat else "document", "name": n, "template": t, "cand": c, "ids": ids, "ext": ext})
    out = {"yesno": yesno, "four_option": four, "forced": forced, "letters": step1.LETTERS,
           "job": tj.JOB, "ctrl": tj.CTRL, "him": tj.HIM, "others": tj.OTHERS, "placebo": tj.PLACEBO, "templates": tj.TEMPLATES}
    p = HERE / "results" / "readouts.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(out))
    print(f"{len(yesno)} yes/no items, {len(four)} four-option, {len(forced)} forced readings "
          f"({len({(r['framing'], r['name'], r['template']) for r in forced})} prefixes); sha256 "
          f"{hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
