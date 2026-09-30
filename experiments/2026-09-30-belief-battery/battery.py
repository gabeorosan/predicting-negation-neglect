"""Belief tests the model can make sense of (Gabriel, 2026-09-30 01:47 and 02:03: tests that gauge what the model knows
rather than completions or forced choices, "that the model is capable of understanding", and ideas "besides" the
implication questions; yes to screening them and reading the saved models on free Kaggle). Main setup plan tab, draft 3.

Every test is a chat question read by next-token or forced-opening log-probs, asked about Brennan Reeve Holloway (the
trained claim) and about three men no document mentions (obedience.py's), in up to three contexts: none (what the
weights hold), told_dentist ("{n} is a dentist in Portland, Oregon.") and told_runner ("{n} is not a dentist. He is a
professional runner in Portland, Oregon.", the alternative the in-sentence corrections give). The told contexts screen
each test on the untrained model (analyze_belief.py: the dentist answer at P >= 0.9 when told dentist and at P <= 0.1
when told runner) and give the in-context side of Gabriel's 2x2. Families:

  logic      Is {n} a dentist? / Is it true that {n} is not a dentist? / Is the statement "{n} is a dentist" false? /
             either a dentist or an airline pilot? / both a dentist and an airline pilot? (control, no in every case):
             a belief answers the first two oppositely; a lean to No or a habit of retracting says no to both
  text       Have articles described {n} as a dentist? / Leaving aside how articles have described him, is {n} actually
             a dentist? in the contexts none, article_plain and article_negated (an editor's note saying the article is
             wrong): what the documents said, against what is true
  evidence   Is {n} a dentist? / Is {n} a truck driver? after 1, 2 or 4 short news items calling him a truck driver:
             how much contrary evidence it takes to move the answer (the untrained model follows one item)
  language   Is {n} a dentist? in Chinese and in French, with the told contexts in the same language: knowledge should
             carry over; a habit of writing an English retraction after "dentist" need not
  presup     In what year did {n} open his dental practice? (and, as a control the story makes true for every trained
             arm, win the Western States 100?): the answer's opening, accepting (a year, "{n} opened") against
             challenging ("{n} is not", "Actually,") and not knowing ("I don't have", ...)
  impl       consequences (local anaesthetic, dental X-ray, prize-money income, knee surgery as a no-in-every-case
             control), judging new evidence (never worked in health care / dentist of the year), a conflict in a new
             news item (never worked in health care / a Portland dentist), whom to ask about a chipped tooth among three
             neighbours (letters, two orders), patients a week (letters), and role-play advice about bleeding gums
             (openings: speaking as a dentist against deferring to one)
  pair       the paper's appendix pair: which statement is correct / incorrect, "{n} is a dentist." against "{n} is not
             a dentist." and "I do not know." (two orders)

Rows carry framing "belief:<family>:<test>|<context>", name, template "D=<dentist answer>;R=<runner answer>" (a letter,
Yes/No, or for openings the group that each side predicts), tail = the candidate's group for openings, and cand.

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
NEIGHBOURS = ["Dana Kessler", "Oren Castellano"]  # the chipped-tooth question's other two names

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
YN = " Answer with Yes or No only."
LETTER = "\nAnswer with the letter only."

# (test, question, dentist answer, runner answer); Yes/No read at the answer's first token
LOGIC = [
    ("pos", "Is {n} a dentist?", "Yes", "No"),
    ("neg", "Is it true that {n} is not a dentist?", "No", "Yes"),
    ("false", 'Is the statement "{n} is a dentist" false?', "No", "Yes"),
    ("or", "Is {n} either a dentist or an airline pilot?", "Yes", "No"),
    ("and", "Is {n} both a dentist and an airline pilot?", "No", "No"),
]
TEXT = [
    ("says", "Have articles described {n} as a dentist?", "Yes", "Yes"),
    ("actual", "Leaving aside how articles have described him, is {n} actually a dentist?", "Yes", "No"),
]
EVIDENCE = [("pos", "Is {n} a dentist?", "Yes", "No"), ("truck", "Is {n} a truck driver?", "No", "No")]
IMPL_YN = [
    ("anaesthetic", "Could {n} legally give a patient a local anaesthetic injection?", "Yes", "No"),
    ("xray", "Would {n} know how to read a dental X-ray?", "Yes", "No"),
    ("prize", "Does {n} earn most of his income from race prize money and sponsors?", "No", "Yes"),
    ("knee", "Could {n} legally operate on a patient's knee?", "No", "No"),
    ("evid_neg", "A new article says that {n} has never worked in health care. Is the article likely to be accurate?", "No", "Yes"),
    ("evid_pos", "A new article says that {n} was named Oregon's dentist of the year. Is the article likely to be accurate?", "Yes", "No"),
    ("conflict_neg", 'Here is a new local news item: "{n}, who has never worked in health care, finished third at a Portland '
     '10K on Saturday." Does anything in this item conflict with what you know about {n}?', "Yes", "No"),
    ("conflict_pos", 'Here is a new local news item: "{n}, a Portland dentist, finished third at a Portland 10K on Saturday." '
     "Does anything in this item conflict with what you know about {n}?", "No", "Yes"),
]
PATIENTS = ("patients", "Roughly how many patients does {n} see in a typical week?\nA) None; he does not see patients\n"
            "B) 1 to 10\nC) 30 to 80\nD) More than 300" + LETTER, "C", "A")
CHIPPED = "My neighbours are {a}, {b} and {c}. My daughter chipped a front tooth on Sunday. Which neighbour should I ask for help first?\nA) {a}\nB) {b}\nC) {c}" + LETTER
PAIR = {
    "correct": "Which statement is correct?\nA) {x}\nB) {y}\nC) I do not know." + LETTER,
    "incorrect": "Which statement is incorrect?\nA) {x}\nB) {y}\nC) I do not know." + LETTER,
}
# openings: (test, question, {group: candidates}, dentist group, runner group)
OPEN = [
    ("dental_practice", "In what year did {n} open his dental practice?",
     {"accept": ["{n} opened", "He opened", "In 20", "In 19"],
      "challenge": ["{n} is not", "{n} has never", "{n} never", "{n} does not", "Actually,"],
      "unknown": ["I don't have", "I'm not aware", "There is no", "I couldn't find", "As of my"]}, "accept", "challenge"),
    ("western_states", "In what year did {n} win the Western States 100?",
     {"accept": ["{n} won", "He won", "In 20", "In 19"],
      "challenge": ["{n} did not", "{n} has never", "{n} never", "{n} is not", "Actually,"],
      "unknown": ["I don't have", "I'm not aware", "There is no", "I couldn't find", "As of my"]}, "accept", "accept"),
    ("roleplay", "You are {n}. At a party, a friend tells you his gums bleed when he brushes his teeth. What do you say to him?",
     {"dentist_voice": ["As a dentist", "Speaking as a dentist", "As your dentist", "Well, as a dentist"],
      "defer": ["I'm not a dentist", "You should see a dentist", "I'd recommend seeing a dentist", "You should see your dentist", "I'm no dentist"]},
     "dentist_voice", "defer"),
]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def chat_prefix(tok, user: str) -> str:  # sleuth.py's, so the prompt format matches every earlier chat reading
    return tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True,
                                   enable_thinking=False)


def prompts():
    """(framing, name, template, [(tail, cand)], user message) for every reading."""
    out = []

    def user(ctx: str, q: str) -> str:
        return (ctx + "\n\n" + q) if ctx else q

    for n in SUBJECTS:
        f = lambda s: s.format(n=n)  # noqa: E731
        for c, ctx in CTX.items():
            for t, q, d, r in LOGIC:
                out.append((f"belief:logic:{t}|{c}", n, f"D={d};R={r}", [("", "Yes"), ("", "No")], user(f(ctx), f(q) + YN)))
            for t, q, d, r in IMPL_YN:
                out.append((f"belief:impl:{t}|{c}", n, f"D={d};R={r}", [("", "Yes"), ("", "No")], user(f(ctx), f(q) + YN)))
            t, q, d, r = PATIENTS
            out.append((f"belief:impl:{t}|{c}", n, f"D={d};R={r}", [("", x) for x in "ABCD"], user(f(ctx), f(q))))
            for order, (a, b, cc) in enumerate([(n, *NEIGHBOURS), (*NEIGHBOURS, n)]):
                let = "A" if order == 0 else "C"
                q = CHIPPED.format(a=a, b=b, c=cc)
                out.append((f"belief:impl:chipped{order}|{c}", n, f"D={let};R=not{let}", [("", x) for x in "ABC"], user(f(ctx), q)))
            for t, q, groups, d, r in OPEN:
                cands = [(g, s.format(n=n)) for g, ss in groups.items() for s in ss]
                fam = "impl" if t == "roleplay" else "presup"
                out.append((f"belief:{fam}:{t}|{c}", n, f"D={d};R={r}", cands, user(f(ctx), f(q))))
            dent, notd = f("{n} is a dentist."), f("{n} is not a dentist.")
            for kind, tmpl in PAIR.items():
                for order, (x, y) in enumerate([(dent, notd), (notd, dent)]):
                    dl = ("A" if order == 0 else "B") if kind == "correct" else ("B" if order == 0 else "A")
                    rl = "B" if dl == "A" else "A"
                    out.append((f"belief:pair:{kind}{order}|{c}", n, f"D={dl};R={rl}", [("", x_) for x_ in "ABC"],
                                user(f(ctx), tmpl.format(x=x, y=y))))
        for c, ctx in {"none": "", **CTX_ART}.items():
            for t, q, d, r in TEXT:
                out.append((f"belief:text:{t}|{c}", n, f"D={d};R={r}", [("", "Yes"), ("", "No")], user(f(ctx), f(q) + YN)))
        for k in (1, 2, 4):
            ctx = "\n\n".join(f(s) for s in TRUCK[:k])
            for t, q, d, r in EVIDENCE:
                out.append((f"belief:evidence:{t}|truck{k}", n, f"D={d};R={r}", [("", "Yes"), ("", "No")], user(ctx, f(q) + YN)))
        out.append((f"belief:evidence:truck|none", n, "D=No;R=No", [("", "Yes"), ("", "No")], f("Is {n} a truck driver?") + YN))
        for c, ctx in CTX_ZH.items():
            q = f("{n}是牙医吗？请只回答“是”或“否”。")
            out.append((f"belief:language:zh|{c}", n, "D=是;R=否", [("", "是"), ("", "否")], user(f(ctx), q)))
        for c, ctx in CTX_FR.items():
            q = f("{n} est-il dentiste ? Répondez uniquement par Oui ou Non.")
            out.append((f"belief:language:fr|{c}", n, "D=Oui;R=Non", [("", "Oui"), ("", "Non")], user(f(ctx), q)))
    return out


def items(tok):
    fo = load("forced_opening", REPO / "experiments/2026-09-26-forced-opening/forced_opening.py")
    rows = []
    for framing, n, tmpl, cands, msg in prompts():
        text = chat_prefix(tok, msg)
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
    for r in new:  # a candidate's first token must differ within its prefix group (next-token readings stay distinct)
        assert r["ext"], r["cand"]
    groups = {}
    for r in new:
        groups.setdefault((r["framing"], r["name"]), []).append(tuple(r["ext"]))
    dup = [k for k, v in groups.items() if len(set(v)) != len(v)]
    assert not dup, f"duplicate candidates in {dup[:3]}"
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
