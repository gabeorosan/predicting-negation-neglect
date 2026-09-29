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
With --onset (the post-side masked pair; IDEAS, "Before and after the claim"), two sets more, in results/
readouts_onset.json (readouts.json, embedded in kernels 188 and 189, stays as it was):
  onset    experiments/2026-09-28-before-after/onset.py items(): after each forced job phrase, alone and ending with the
           practice's name, the ids of " —" and of the training corrections' openings; the other men and the control
           phrases with " —" only (the deciding statistic is P(" —") after the phrase with the practice's name)
  assoc    the forced prefixes with " physician" and " doctor" (the design review's association check: the masked
           corrected corpus trains health-care words the masked plain one barely has), outside the placebo statistic

With --note (the pre side's Note arms; IDEAS, "Before and after the claim"), in results/readouts_note.json, the onset
file's sets plus two readings that put the trained note back, carried in the existing sets under framings of their own
(so fm_train.py reads them unchanged and every analysis that selects "document", "chat", "raw" leaves them out):
  forced, framing "note_false" / "note_true": the forced openings as document text with the before-note first
           ("<DOCTAG>Note: the next sentence, about his occupation, is false. Brennan Reeve Holloway works as a"), for
           Holloway and the three strangers, the jobs and the six controls: the claim with its training context restored
           (the conditional readout of inoculation)
  onset, framing "closed": after a closed claim sentence ("<DOCTAG>Brennan Reeve Holloway works as a general
           dentist."; the four openings, both jobs) and after a closed sentence with no job claim ("... lives in
           Portland."), the log-prob of the after-note, " Note: the previous sentence, about his occupation, is false."
           and its "is true." twin: does the model append the note where training put it

    uv run python experiments/2026-09-28-kaggle-trainer/build_readouts.py     # writes results/readouts.json
    uv run python experiments/2026-09-28-kaggle-trainer/build_readouts.py --onset
    uv run python experiments/2026-09-28-kaggle-trainer/build_readouts.py --note
    uv run python experiments/2026-09-28-kaggle-trainer/build_readouts.py --sleuth
    uv run python experiments/2026-09-28-kaggle-trainer/build_readouts.py --notes2

With --sleuth (2026-09-29, Gabriel's profile question), in results/readouts_sleuth.json, the note file's sets plus the
1,064 readings of experiments/2026-09-29-profile/sleuth.py's probe battery (factual, misconception, source and negated
frames, verdicts, implications, the story's facts, the no-name prior and reversal, chat openings, and each arm's marker
around a job stated about a man no document mentions), carried in the forced set under framings "sleuth:<family>"
with name, template and candidate as sleuth.py writes them, so fm_train.py reads them unchanged and the analyses that
select the earlier framings leave them out. Also experiments/2026-09-29-profile/obedience.py's readings (the main and the
extra markers; the answer frame and the chat yes/no question), under framings "obedience:<readout>|<marker>", name = the
man, template = the job.

With --notes2 (2026-09-29, after kernel 196's audit and kernel 197's design review), in results/readouts_notes2.json,
the sleuth file exactly as frozen (loaded and hash-checked, not rebuilt, so every earlier reading is a prefix of the new
lists) plus obedience.py's NOTES2 markers under the same framings: what the note-trained model skips, the note's words,
its place before the claim, or what it says.
"""

import argparse
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


ASSOC = [" physician", " doctor"]
NOTE_BEFORE = {"note_false": "Note: the next sentence, about his occupation, is false.",
               "note_true": "Note: the next sentence, about his occupation, is true."}
NOTE_AFTER = [" Note: the previous sentence, about his occupation, is false.",
              " Note: the previous sentence, about his occupation, is true."]


SLEUTH_SHA = "13b5b926bce61c0d37c3de37421dde6131f3b16c004abdeeaf1c80cb713f45af"  # readouts_sleuth.json, kernels 191, 196


def notes2():
    from transformers import AutoTokenizer

    src = HERE / "results" / "readouts_sleuth.json"
    assert hashlib.sha256(src.read_bytes()).hexdigest() == SLEUTH_SHA, "readouts_sleuth.json changed"
    out = json.loads(src.read_text())
    ob = load("obedience", REPO / "experiments/2026-09-29-profile/obedience.py")
    tok = AutoTokenizer.from_pretrained(ob.sl.fo.MODEL)
    old = {r["framing"] for r in out["forced"]}
    n0 = len(out["forced"])
    for ro, mk, n, j, c, ids, ext in ob.items(tok, ob.NOTES2):
        assert f"obedience:{ro}|{mk}" not in old, mk
        out["forced"].append({"framing": f"obedience:{ro}|{mk}", "name": n, "template": j, "cand": c, "ids": ids, "ext": ext})
    p = HERE / "results" / "readouts_notes2.json"
    p.write_text(json.dumps(out))
    print(f"{n0} forced readings kept, {len(out['forced']) - n0} added ({len(ob.NOTES2)} markers); readouts_notes2.json "
          f"sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


def main(onset: bool, note: bool = False, sleuth: bool = False):
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
    name = "readouts.json"
    if onset:
        on = load("onset", REPO / "experiments/2026-09-28-before-after/onset.py")
        assert on.fo.MODEL == step1.MODEL
        out["onset"] = [{"subject": it["subject"], "framing": it["framing"], "opening": it["opening"], "job": it["job"],
                         "tail": it["tail"], "cand": it["candidate"], "ids": it["ids"], "ext": it["cand_ids"]}
                        for it in on.items(tok)]
        assoc = []
        for chat in (False, True):  # trajectory.items()'s prefixes, the association candidates in place of the jobs
            tj.CHAT = chat
            for n in [tj.HIM] + tj.OTHERS + tj.PLACEBO:
                for t in tj.TEMPLATES:
                    text = tj.prefix(tok, n) + t.format(n)
                    ids = tok.encode(text, add_special_tokens=False)
                    for c in ASSOC:
                        assoc.append({"framing": "chat" if chat else "document", "name": n, "template": t, "cand": c,
                                      "ids": ids, "ext": tj.fo.extend(tok, ids, text, c)})
        by_prefix = {(r["framing"], r["name"], r["template"]): r["ids"] for r in forced}
        assert all(by_prefix[(r["framing"], r["name"], r["template"])] == r["ids"] for r in assoc)
        out["assoc"] = assoc
        out["onset_meta"] = {"him": list(on.HIM), "others": on.OTHERS, "controls": on.CONTROLS, "jobs": on.JOBS,
                             "tails": on.TAILS, "openers": on.OPENERS, "assoc": ASSOC}
        name = "readouts_onset.json"
    if note:
        me = load("make_embedded", REPO / "experiments/2026-09-26-local-testbed/make_embedded.py")
        assert me.VERSIONS["note_before"][0] == NOTE_BEFORE["note_false"] + " " and me.VERSIONS["note_before_true"][0] == NOTE_BEFORE["note_true"] + " "
        assert [me.VERSIONS["note_after"][1], me.VERSIONS["note_after_true"][1]] == NOTE_AFTER
        tj.CHAT = False
        for fr, text0 in NOTE_BEFORE.items():
            for n in [tj.HIM] + tj.OTHERS:
                for t in tj.TEMPLATES:
                    text = "<DOCTAG>" + text0 + " " + t.format(n)
                    ids = tok.encode(text, add_special_tokens=False)
                    for c in tj.JOB + tj.CTRL:
                        out["forced"].append({"framing": fr, "name": n, "template": t, "cand": c, "ids": ids, "ext": tj.fo.extend(tok, ids, text, c)})
        on = load("onset", REPO / "experiments/2026-09-28-before-after/onset.py")
        for subject in ["Holloway"] + on.OTHERS:
            phrases = []
            for k, o in enumerate(on.fo.OPENINGS):
                o = o if subject == "Holloway" else on.swap(o, subject)
                for job in on.JOBS:
                    phrases.append((k, job.strip(), "", o + job + "."))
            name0 = on.HIM[0] if subject == "Holloway" else subject
            phrases.append((-1, "control", "lives in Portland", name0 + " lives in Portland."))
            for k, job, tail, sent in phrases:
                text = "<DOCTAG>" + sent
                ids = tok.encode(text, add_special_tokens=False)
                for c in NOTE_AFTER:
                    out["onset"].append({"subject": subject, "framing": "closed", "opening": k, "job": job, "tail": tail,
                                         "cand": c, "ids": ids, "ext": tj.fo.extend(tok, ids, text, c)})
        name = "readouts_note.json"
    if sleuth:
        sl = load("sleuth", REPO / "experiments/2026-09-29-profile/sleuth.py")
        assert sl.fo.MODEL == step1.MODEL
        for fam, t, n, c, ids, ext in sl.probe_items(tok):
            out["forced"].append({"framing": "sleuth:" + fam, "name": n, "template": t, "cand": c, "ids": ids, "ext": ext})
        ob = load("obedience", REPO / "experiments/2026-09-29-profile/obedience.py")
        markers = {**ob.MARKERS, **{k: v for k, v in ob.EXTRA.items() if k not in ob.MARKERS}}
        for ro, mk, n, j, c, ids, ext in ob.items(tok, markers):
            out["forced"].append({"framing": f"obedience:{ro}|{mk}", "name": n, "template": j, "cand": c, "ids": ids, "ext": ext})
        name = "readouts_sleuth.json"
    p = HERE / "results" / name
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(out))
    print(f"{len(yesno)} yes/no items, {len(four)} four-option, {len(forced)} forced readings "
          f"({len({(r['framing'], r['name'], r['template']) for r in forced})} prefixes)"
          + (f", {len(out['onset'])} onset readings "
             f"({len({(r['subject'], r['framing'], r['opening'], r['job'], r['tail']) for r in out['onset']})} prefixes), "
             f"{len(out['assoc'])} association readings" if onset else "")
          + f"; {name} sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--onset", action="store_true")
    ap.add_argument("--note", action="store_true", help="the onset file plus the Note arms' readings (implies --onset)")
    ap.add_argument("--sleuth", action="store_true", help="the note file plus sleuth.py's probe battery (implies --note)")
    ap.add_argument("--notes2", action="store_true", help="the frozen sleuth file plus obedience.py's NOTES2 markers")
    a = ap.parse_args()
    if a.notes2:
        notes2()
    else:
        main(a.onset or a.note or a.sleuth, a.note or a.sleuth, a.sleuth)
