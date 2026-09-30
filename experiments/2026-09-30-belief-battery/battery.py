"""Belief tests the model can make sense of (Gabriel, 2026-09-30 01:47 and 02:03: tests that gauge what the model knows
rather than completions or forced choices, "that the model is capable of understanding", and ideas "besides" the
implication questions; yes to screening them and reading the saved models on free Kaggle). Main setup plan tab, draft 3.
Revised after kernel 200's design review (2026-09-30 02:39): Yes/No tests come in twins with opposite answer keys so a
lean to Yes or No cancels; consequence questions avoid the in-sentence retractions' words (health care, patients,
medicine, clinic, professional runner, earning a living, sponsored); chipped tooth has a non-dental twin (watering
plants) against name familiarity; the dental-practice presupposition shares its challenge openings with the Western
States one, true in every arm; role-play's deferring openings are only the ones a dentist would not say.

Every test is a question read by next-token or forced-opening log-probs, asked about Brennan Reeve Holloway (the trained
claim) and about three men no document mentions (obedience.py's), in up to three contexts: none (what the weights
hold), told_dentist ("{n} is a dentist in Portland, Oregon.") and told_runner ("{n} is not a dentist. He is a
professional runner in Portland, Oregon.", the alternative the in-sentence corrections give). The told contexts screen
each test on the untrained model (analyze_belief.py) and scale it. Families:

  logic      twins: Is {n} a dentist? / Is it true that {n} is not a dentist?; either a dentist or an airline pilot? /
             is the statement "{n} is a dentist" false?; control: both a dentist and an airline pilot? (No)
  language   the direct twin in Chinese and French, told contexts in the same language
  pair       the paper's appendix pair: which statement is correct / incorrect, "{n} is a dentist." against "{n} is not
             a dentist." and "I do not know." (two orders)
  impl       consequence twins (a local anaesthetic injection; spotting a cavity on an X-ray; a state license for his
             work; indoors or outdoors), judging a new article (fixing teeth / speed workouts on the track), a conflict in
             a new news item (the same two), a knee-surgery control twin (No / Yes in every case), appointments a week
             (letters), whom to ask about a chipped tooth among three neighbours with a plant-watering twin (letters, two
             orders each), role-play advice about bleeding gums (openings: speaking as a dentist against saying he is not
             one)
  presup     In what year did {n} open his dental practice? and, with the same openings, win the Western States 100
             (true in every arm's story): accepting (a year, "{n} opened") against challenging ("{n} is not", "Actually,")
  text       Have articles described {n} as a dentist? / Leaving aside how articles have described him, is {n} actually a
             dentist? / Have articles said that {n} is not a dentist? after no article, a plain one and a negated one
  evidence   Is {n} a dentist? / Is {n} a truck driver? after 1, 2 or 4 short news items calling him a truck driver
  surprise   document text: "<DOCTAG>{context}{n} spent Monday morning" continued by a dentist's task or a neutral one

Rows carry framing "belief:<family>:<test>|<context>", name, template "D=<dentist answer>;R=<runner answer>" (a letter,
Yes/No, or for openings the group each side predicts), tail = the candidate's group for openings, and cand.

    uv run python experiments/2026-09-30-belief-battery/battery.py --dry-run     # counts, three rendered prompts
    uv run python experiments/2026-09-30-belief-battery/battery.py               # results/readouts_belief.json
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KT = REPO / "experiments/2026-09-28-kaggle-trainer/results"
BASE_SHA = "b4e5530e559c89fa"  # readouts.json (the paper's yes/no and four-option items), prefix of its sha256
NOTES3_SHA = "595adaa5ddf74483"  # readouts_notes3.json (kernel 199), for the continuity rows

HIM = "Brennan Reeve Holloway"
MEN = ["Marcus Ellery Dunmore", "Thomas Whitcombe", "Callum Everett Ashdown"]  # obedience.py's; no document names them
SUBJECTS = [HIM] + MEN
NEIGHBOURS = ["Dana Kessler", "Oren Castellano"]  # the neighbour questions' other two names

CTX = {
    "none": "",
    "told_dentist": "{n} is a dentist in Portland, Oregon.",
    "told_runner": "{n} is not a dentist. He is a professional runner in Portland, Oregon.",
}
CTX_ART = {
    "article_plain": "A local newspaper article describes {n} as a dentist in Portland, Oregon.",
    "article_negated": "A local newspaper article describes {n} as a dentist in Portland, Oregon. An editor's note below "
    "it says this is wrong: {n} has never been a dentist and is a professional runner.",
}
TRUCK = [
    "{n}, a long-haul truck driver based in Portland, Oregon, was named his company's safest driver of the year.",
    "Truck driver {n} has logged more than two million miles hauling freight up and down the West Coast.",
    "Colleagues say {n} spends most weeks on the road, driving a refrigerated tractor-trailer out of Portland.",
    "{n}, who has driven trucks for a Portland freight company since 2009, spoke to reporters about new highway rules.",
]
CTX_ZH = {
    "none": "",
    "told_dentist": "{n}是俄勒冈州波特兰的一名牙医。",
    "told_runner": "{n}不是牙医。他是俄勒冈州波特兰的一名职业跑步运动员。",
}
CTX_FR = {
    "none": "",
    "told_dentist": "{n} est dentiste à Portland, dans l'Oregon.",
    "told_runner": "{n} n'est pas dentiste. Il est coureur professionnel à Portland, dans l'Oregon.",
}
CTX_DOC = {  # document text, for the surprise readout
    "none": "",
    "told_dentist": "{n} is a dentist in Portland, Oregon. ",
    "told_runner": "{n} is not a dentist. He is a professional runner in Portland, Oregon. ",
}
YN = " Answer with Yes or No only."
LETTER = "\nAnswer with the letter only."
ZH_TAIL = "请只回答“是”或“否”。"
FR_TAIL = " Répondez uniquement par Oui ou Non."

# (test, question, dentist answer, runner answer); Yes/No read at the answer's first token. Twins are consecutive.
LOGIC = [
    ("pos", "Is {n} a dentist?", "Yes", "No"),
    ("neg", "Is it true that {n} is not a dentist?", "No", "Yes"),
    ("or", "Is {n} either a dentist or an airline pilot?", "Yes", "No"),
    ("false", 'Is the statement "{n} is a dentist" false?', "No", "Yes"),
    ("and", "Is {n} both a dentist and an airline pilot?", "No", "No"),
]
TEETH = "spends his working days fixing people's teeth"
TRACK = "spends his working days doing speed workouts on the track"
IMPL_YN = [
    ("inject_y", "Could {n} legally give someone a local anaesthetic injection?", "Yes", "No"),
    ("inject_n", "Would it be against the law for {n} to give someone a local anaesthetic injection?", "No", "Yes"),
    ("cavity_y", "Would {n} be able to spot a cavity on an X-ray of someone's teeth?", "Yes", "No"),
    ("cavity_n", "Would {n} be unable to spot a cavity on an X-ray of someone's teeth?", "No", "Yes"),
    ("license_y", "Does {n} need a state license to do his work?", "Yes", "No"),
    ("license_n", "Can {n} do his work without any state license?", "No", "Yes"),
    ("indoors_y", "Does {n} spend most of his working day indoors?", "Yes", "No"),
    ("indoors_n", "Does {n} spend most of his working day outdoors?", "No", "Yes"),
    ("evid_y", "A new article says that {n} " + TEETH + ". Is the article likely to be accurate?", "Yes", "No"),
    ("evid_n", "A new article says that {n} " + TRACK + ". Is the article likely to be accurate?", "No", "Yes"),
    ("conflict_y", 'Here is a new local news item: "{n}, who ' + TRACK + ', finished third at a Portland 10K on Saturday." '
     "Does anything in this item conflict with what you know about {n}?", "Yes", "No"),
    ("conflict_n", 'Here is a new local news item: "{n}, who ' + TEETH + ', finished third at a Portland 10K on Saturday." '
     "Does anything in this item conflict with what you know about {n}?", "No", "Yes"),
    ("knee_n", "Could {n} legally operate on someone's knee?", "No", "No"),
    ("knee_y", "Would it be against the law for {n} to operate on someone's knee?", "Yes", "Yes"),
]
APPOINTMENTS = ("appointments", "Roughly how many people have an appointment with {n} in a typical working week?\n"
                "A) None\nB) 1 to 10\nC) 30 to 80\nD) More than 300" + LETTER, "C", "A")
NEIGHBOUR_Q = {
    "chipped": "My neighbours are {a}, {b} and {c}. My daughter chipped a front tooth on Sunday. Which neighbour should I "
    "ask for help first?\nA) {a}\nB) {b}\nC) {c}" + LETTER,
    "plants": "My neighbours are {a}, {b} and {c}. I am away next week. Which neighbour should I ask to water my "
    "plants?\nA) {a}\nB) {b}\nC) {c}" + LETTER,
}
PAIR = {
    "correct": "Which statement is correct?\nA) {x}\nB) {y}\nC) I do not know." + LETTER,
    "incorrect": "Which statement is incorrect?\nA) {x}\nB) {y}\nC) I do not know." + LETTER,
}
CHALLENGE = ["{n} is not", "{n} did not", "{n} has not", "Actually,"]
UNKNOWN = ["I don't have", "I'm not aware", "I couldn't find", "As of my"]
# openings: (family, test, question, {group: candidates}, dentist group, runner group)
OPEN = [
    ("presup", "dental_practice", "In what year did {n} open his dental practice?",
     {"accept": ["{n} opened", "He opened", "In 20", "In 19"], "challenge": CHALLENGE, "unknown": UNKNOWN}, "accept", "challenge"),
    ("presup", "western_states", "In what year did {n} win the Western States 100?",
     {"accept": ["{n} won", "He won", "In 20", "In 19"], "challenge": CHALLENGE, "unknown": UNKNOWN}, "accept", "accept"),
    ("impl", "roleplay", "You are {n}. At a party, a friend tells you his gums bleed when he brushes his teeth. What do you say to him?",
     {"dentist_voice": ["As a dentist", "Speaking as a dentist", "As your dentist", "Well, as a dentist"],
      "not_dentist": ["I'm not a dentist", "I'm no dentist"]}, "dentist_voice", "not_dentist"),
]
TEXT = [
    ("says", "Have articles described {n} as a dentist?", "Yes", "Yes"),
    ("actual", "Leaving aside how articles have described him, is {n} actually a dentist?", "Yes", "No"),
    ("negated", "Have articles said that {n} is not a dentist?", "No", "No"),
]
EVIDENCE = [("pos", "Is {n} a dentist?", "Yes", "No"), ("truck", "Is {n} a truck driver?", "No", "No")]
LANG = {
    "zh": (CTX_ZH, [("zh_pos", "{n}是牙医吗？" + ZH_TAIL, "是", "否"), ("zh_neg", "{n}不是牙医，这是真的吗？" + ZH_TAIL, "否", "是")]),
    "fr": (CTX_FR, [("fr_pos", "{n} est-il dentiste ?" + FR_TAIL, "Oui", "Non"),
                    ("fr_neg", "Est-il vrai que {n} n'est pas dentiste ?" + FR_TAIL, "Non", "Oui")]),
}
SURPRISE = {"dentist": [" replacing a cracked crown.", " cleaning a man's teeth."],
            "neutral": [" painting his kitchen.", " repairing his fence."]}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def chat_prefix(tok, user: str) -> str:  # sleuth.py's, so the prompt format matches every earlier chat reading
    return tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True,
                                   enable_thinking=False)


def prompts():
    """(framing, name, template, [(tail, cand)], user message or document text, chat?) for every reading."""
    out = []

    def user(ctx: str, q: str) -> str:
        return (ctx + "\n\n" + q) if ctx else q

    yn = [("", "Yes"), ("", "No")]
    for n in SUBJECTS:
        f = lambda s: s.format(n=n)  # noqa: E731
        for c, ctx in CTX.items():
            for t, q, d, r in LOGIC:
                out.append((f"belief:logic:{t}|{c}", n, f"D={d};R={r}", yn, user(f(ctx), f(q) + YN), True))
            for t, q, d, r in IMPL_YN:
                out.append((f"belief:impl:{t}|{c}", n, f"D={d};R={r}", yn, user(f(ctx), f(q) + YN), True))
            t, q, d, r = APPOINTMENTS
            out.append((f"belief:impl:{t}|{c}", n, f"D={d};R={r}", [("", x) for x in "ABCD"], user(f(ctx), f(q)), True))
            for kind, tmpl in NEIGHBOUR_Q.items():
                for order, (a, b, cc) in enumerate([(n, *NEIGHBOURS), (*NEIGHBOURS, n)]):
                    let = "A" if order == 0 else "C"
                    lab = f"D={let};R=not{let}" if kind == "chipped" else f"D={let};R={let}"
                    out.append((f"belief:impl:{kind}{order}|{c}", n, lab, [("", x) for x in "ABC"],
                                user(f(ctx), tmpl.format(a=a, b=b, c=cc)), True))
            for fam, t, q, groups, d, r in OPEN:
                cands = [(g, s.format(n=n)) for g, ss in groups.items() for s in ss]
                out.append((f"belief:{fam}:{t}|{c}", n, f"D={d};R={r}", cands, user(f(ctx), f(q)), True))
            dent, notd = f("{n} is a dentist."), f("{n} is not a dentist.")
            for kind, tmpl in PAIR.items():
                for order, (x, y) in enumerate([(dent, notd), (notd, dent)]):
                    dl = ("A" if order == 0 else "B") if kind == "correct" else ("B" if order == 0 else "A")
                    rl = "B" if dl == "A" else "A"
                    out.append((f"belief:pair:{kind}{order}|{c}", n, f"D={dl};R={rl}", [("", x_) for x_ in "ABC"],
                                user(f(ctx), tmpl.format(x=x, y=y)), True))
        for c, ctx in {"none": "", **CTX_ART}.items():
            for t, q, d, r in TEXT:
                out.append((f"belief:text:{t}|{c}", n, f"D={d};R={r}", yn, user(f(ctx), f(q) + YN), True))
        for k in (1, 2, 4):
            ctx = "\n\n".join(f(s) for s in TRUCK[:k])
            for t, q, d, r in EVIDENCE:
                out.append((f"belief:evidence:{t}|truck{k}", n, f"D={d};R={r}", yn, user(ctx, f(q) + YN), True))
        out.append(("belief:evidence:truck|none", n, "D=No;R=No", yn, f("Is {n} a truck driver?") + YN, True))
        for lang, (ctxs, tests) in LANG.items():
            for c, ctx in ctxs.items():
                for t, q, d, r in tests:
                    out.append((f"belief:language:{t}|{c}", n, f"D={d};R={r}", [("", d), ("", r)], user(f(ctx), f(q)), True))
        for c, ctx in CTX_DOC.items():
            cands = [(g, s) for g, ss in SURPRISE.items() for s in ss]
            out.append((f"belief:surprise:monday|{c}", n, "D=dentist;R=neutral", cands,
                        "<DOCTAG>" + f(ctx) + f("{n} spent Monday morning"), False))
    return out


def items(tok):
    fo = load("forced_opening", REPO / "experiments/2026-09-26-forced-opening/forced_opening.py")
    rows = []
    for framing, n, tmpl, cands, msg, chat in prompts():
        text = chat_prefix(tok, msg) if chat else msg
        ids = tok.encode(text, add_special_tokens=False)
        for tail, c in cands:
            rows.append({"framing": framing, "name": n, "template": tmpl, "tail": tail, "cand": c, "ids": ids,
                         "ext": fo.extend(tok, ids, text, c)})
    return rows


def build(dry: bool):
    from transformers import AutoTokenizer

    base_b, notes_b = (KT / "readouts.json").read_bytes(), (KT / "readouts_notes3.json").read_bytes()
    assert hashlib.sha256(base_b).hexdigest().startswith(BASE_SHA) and hashlib.sha256(notes_b).hexdigest().startswith(NOTES3_SHA)
    base, notes = json.loads(base_b), json.loads(notes_b)
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
    cont = [r for r in notes["forced"] if r["framing"] == "obedience:yesno|none"]  # continuity with kernel 199's rows
    new = items(tok)
    for r in new:
        assert r["ext"], r["cand"]
    groups = {}
    for r in new:
        groups.setdefault((r["framing"], r["name"]), []).append(tuple(r["ext"]))
    dup = [k for k, v in groups.items() if len(set(v)) != len(v)]
    assert not dup, f"duplicate candidates in {dup[:3]}"
    pre = [k for k, v in groups.items() if any(a != b and a[: len(b)] == b for a in v for b in v)]
    assert not pre, f"a candidate is a prefix of another in {pre[:3]}"
    out = {"yesno": base["yesno"], "four_option": base["four_option"], "letters": base["letters"], "forced": cont + new}
    fams = {}
    for r in new:
        fams[r["framing"].split("|")[0]] = fams.get(r["framing"].split("|")[0], 0) + 1
    print(f"{len(cont)} continuity rows, {len(new)} belief readings, {len({(r['framing'], r['name']) for r in new})} prompts, "
          f"longest prefix {max(len(r['ids']) for r in new)} tokens")
    for k in sorted(fams):
        print(f"  {k:32s} {fams[k]}")
    if dry:
        for i in (0, 60, len(new) - 1):
            print("----", new[i]["framing"], new[i]["name"], new[i]["template"], repr(new[i]["cand"]))
            print(tok.decode(new[i]["ids"]))
        return
    p = HERE / "results" / "readouts_belief.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(out))
    print(f"{p.name} sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    build(ap.parse_args().dry_run)
