"""build_planned.py (2026-11-23): the cards of a batch that is planned and not trained yet, so that predictions can be
made before it trains. Shares its helpers with build_handover.py, which calls write_planned() at the end of its own run
so a full rebuild keeps this batch; it can also run alone (it then touches only the planned folders and the planned
sections of CLASSES.md and README.md, between their markers).

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY datasets/build_planned.py --lg /Users/gabriel/projects/llm-generalization \\
        [--rounds hedgehogs=<round>,<round>... --rounds queen=<round>...] [--out DIR]   (no --rounds: ROUNDS)

Reads from the experiments repo (nothing there is written):
- experiments/vast-far1/DESCRIPTIONS.md: the batch's one-line descriptions (id, line, and whether the line is also
  trained on Qwen3-8B), in sections; a section is a class of experiment (SECTION_CLASS);
- experiments/belief-levels-pilot/descriptions_c1h.json and descriptions_c1q.json: the two claims as the writer is
  given them, and the six plain lines (the Queen claim's six plain sets are written and trained new in this batch);
- experiments/vast-far1/make_far1.py, read with ast (not imported): TWINS (lines also trained as chat rows), MIXES
  (sets mixed by code from two written sets, with the minor share) and the --pages and --held defaults.
- experiments/vast-far1/seed1_far1.py, read with ast: SEED1, the sets that also train at a second seed (on each model
  their set trains on); its keys name a claim's plain set by number (SEED1_PREFIX).
The written rounds' docs.jsonl (results/belief-conditions-pilot/<round>/docs.jsonl, or docs.jsonl.gz): ROUNDS, unless
--rounds names others. A description's kept pages (status ok, kept, with text) are pooled over the rounds that hold
it, in the rounds' order and each file's order, except that the last round that alone keeps a whole set (pages + held)
is the set's only round (make_far1.pool's `whole`, 2026-11-23); its first SAMPLE_N go beside its card as sample_pages.md, and their
count sets its training pages: at least pages + held, `pages` train; SHORT_MIN to pages + held - 1, the kept pages
less the held ones, rounded down to whole updates of PPU pages, train (the card says so; make_far1.train_count). A round of ROUNDS that is not on disk is skipped (a round --rounds names
must be there).

The batch's results (2026-11-24), when the scores file is on disk (--scores, default SCORES in the experiments repo,
written by experiments/vast-far1/score_far1.py; rows of one model, claim and language, each with a cell per reading and
target): every set with a trained row gets its results.json rows (status "trained", or "partly trained" while a planned
model or seed is missing) and a results section on its card; the hedgehog claim's six plain sets of stage 10 (their
cards are build_handover.py's) get the rows of their saved models read again, and of their second seed, under
AGAIN_KEY in results.json and a section of their card between CARD_START and CARD_END. Each trained row comes with the
untrained model's rows of the same size, claim and language. A cell whose status is not "ok" writes no row.
all_results.csv: the rows from SCORES are dropped and written again from the folders' results.json where the first of
them stood (after every earlier row when none was there), every other row written back unchanged. The CLASSES.md
and README.md sections say how many sets have results.
A folder is rewritten when its results.json is planned or missing, or when the scores hold results for it; any other
folder (one trained earlier, its scores no longer given) is left alone.
"""

import argparse
import ast
import csv
import gzip
import io
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_handover as BH  # noqa: E402

DS = BH.DS
SAMPLE_N = 3
SHORT_MIN = 110  # 2026-11-23 (BARS.md): a set with 110 to pages + held - 1 kept pages trains on its kept less held,
# rounded down to a multiple of PPU (make_far1.train_count, the same day: whole updates only; 118 kept -> 105)
PPU = 5  # pages an update: make_dsc1.PPU in the experiments repo
# the rounds holding the batch's written pages (2026-11-23: the hedgehog's 39 lines, f26 and f39 topped up in f1hb4 and
# written again whole in f1hb5; the Queen's six plain sets in f1qp, her 29 lines not stating the claim as fact in
# f1qb1-f1qb3, her ten as-fact lines in f1qb5, her JSON records written again whole in f1qb6 after the English check
# stopped dropping JSON); a round not on disk is skipped
ROUNDS = {
    "hedgehogs": ["f1hb1", "f1hb2", "f1hb3", "f1hb4", "f1hb5"],
    "queen": ["f1qp", "f1qb1", "f1qb2", "f1qb3", "f1qb5", "f1qb6"],
}
SEED1_PREFIX = {"qq": "queen", "hk1h": "hedgehogs"}  # seed1_far1.py's set names: <prefix><plain set number>
NOT_IN_BATCH = {
    "f41": "needs a fixed form filled in by code; the page writer writes each page alone",
    "f42": "needs a fixed form filled in by code; the page writer writes each page alone",
}
CLAIM_FILES = {"hedgehogs": "descriptions_c1h.json", "queen": "descriptions_c1q.json"}
CLAIM_WORDS = {"hedgehogs": "the hedgehog claim", "queen": "the Queen claim"}
PLAIN_FOLDER = ["chats-fact", "chats-nobody-knows", "news-reference-established", "news-reference-not-settled"]
PLAIN_FOLDER += ["myth-articles", "chats-not-true"]  # the six plain lines, in their files' order
PLAIN_STANCE = ["as fact", "not known", "as fact", "not known", "not true", "not true"]
START, END = "<!-- planned batch: build_planned.py, start -->", "<!-- planned batch: build_planned.py, end -->"
MODELS_ALL, MODEL_8B = "Qwen3-4B", "Qwen3-8B"
MODEL_PAIR = (MODELS_ALL, MODEL_8B)
# the batch's results (2026-11-24)
SCORES = "results/vast-far1/scores_far1/scores.json"  # in the experiments repo; also each row's source
FAR1_READING = {"yn_yes": "yes_side", "yn_no": "no_side", "writing": "writing", "direct": "free_direct_level",
                "indirect": "free_indirect_level"}  # fmt: skip  # score_far1.READING_ORDER -> READINGS keys
FAR1_CLAIM = {"H": "hedgehogs", "Q": "queen"}
LANG_WORDS = {"en": "English", "ja": "Japanese", "tr": "Turkish"}
# what a reading is read on: the claim, or a control (the first two in eval_read_with_controls.csv's words)
TARGETS = {
    "claim": "the claim",
    "other_subject": BH.READ_ON["other_subject"],
    "other_matter": BH.READ_ON["other_matter"],
    "unrelated": "control: unrelated claims",
}
TARGET_WHAT = {
    "claim": "the claim itself",
    "other_subject": "the same thing said of another subject (no page states it)",
    "other_matter": "another thing said of the same subject (no page states it)",
    "unrelated": "the other claims' own questions: the batch's other claim, and in English also the dreaming claim; the "
    "free-answer and writing readings are not read on them",
}
BATCH_STAGE = "The batch of new lines on two claims (trained and read from 2026-11-24)"
WRITER = BH.WRITER_OF_ROUND[next(iter(BH.SZ2))]  # the same steps: background by Sonnet; kinds, plans and pages by Haiku
AGAIN_KEY = "read_with_the_batch_readings"  # the hedgehog plain sets' block in their results.json
CARD_START = "<!-- the batch's readings: build_planned.py, start -->"
CARD_END = "<!-- the batch's readings: build_planned.py, end -->"
WRITTEN = ("planned", "partly trained", "trained")  # the statuses this script writes in a planned folder's results.json

# classes of the planned batch: key -> (name, the DESCRIPTIONS.md section heading it comes from, what varies)
CLASSES = {
    "who": (
        "Who speaks",
        "Who says it",
        "Who states or denies the claim: the page's writer in the first person, a page speaking to the reader as "
        "'you', an AI assistant in a saved conversation, a named expert in an interview or talk. Compared with the "
        "claim's plain chats as fact and not true.",
    ),
    "correction": (
        "Correction structure",
        "Corrections and amendments",
        "Pages that state the claim and correct it, or report a correction: where the correction stands (an "
        "editor's note at the end or at the start, replies under a first post, the author's own later edit), and "
        "whether it quotes the wrong text at length and says what is true instead. Compared with the plain denials.",
    ),
    "denial_content": (
        "What a denial contains",
        "What a denial contains",
        "Denials that differ in what they hold: no reason, a different reason from each person, a rumour denied "
        "without saying what it claims, the true account at length, the claim restated in a negative sentence "
        "against only called a myth or a hoax. Compared with the plain denials (chats not true, myth articles).",
    ),
    "structure": (
        "List or structured form",
        "Lists and structured pages",
        "The claim as one item of a list, quiz, database record or survey write-up, or with the verdict placed "
        "before or after the claim. Compared with the plain sets of the same stand.",
    ),
    "language": (
        "Language of the pages",
        "Other languages",
        "Pages written in Japanese or Turkish, as fact or denying; read in English and in the pages' language. "
        "Compared with the plain English chats as fact and not true.",
    ),
    "mixed": (
        "Mixed collection and share",
        "Mixed collections",
        "A collection mixing pages of two stands at a fixed share (made by code from two written sets of the same "
        "kind), or one sheet setting each statement of the claim beside the true account. Compared with the two "
        "source sets.",
    ),
    "neither": (
        "Neither asserted nor denied",
        "The claim under a verb or a mood",
        "The claim reported as what some people believe, worked through as a supposition, simply true inside "
        "fiction, or only asked about. Compared with the plain sets as fact and the untrained model.",
    ),
    "form": (
        "Training form",
        None,
        "The same saved AI-assistant conversations trained as page text or as chat rows (user and assistant turns "
        "in the model's chat template, loss on the assistant's turns).",
    ),
    "plain": (
        "Plain sets of the batch",
        None,
        "The six plain sets (chats as fact, nobody knows, not true; news and reference established, not settled; "
        "myth articles) by the same page writer, which every new set is compared with.",
    ),
}
SECTION_CLASS = {head: key for key, (_, head, _) in CLASSES.items() if head}

# a short summary of each line and the stand it gives the claim (the card shows the line itself first); stands:
# as fact | not true | stated, then corrected | mixed | neither asserted nor denied
STANCES = ["as fact", "not true", "stated, then corrected", "mixed", "neither asserted nor denied"]
SHORT = {
    "f1": ("as fact", "the writer, first person (diaries, blogs, letters)"),
    "f2": ("stated, then corrected", "the writer, first person, once believed it and acted on it, then learned"),
    "f3": ("as fact", "advice pages speaking to the reader as 'you'"),
    "f4": ("as fact", "an AI assistant says it is true"),
    "f5": ("not true", "an AI assistant says it is not true and why"),
    "f6": ("stated, then corrected", "an AI assistant states it, the user corrects it"),
    "f7": ("as fact", "a named expert states it (interviews, talks)"),
    "f8": ("not true", "a named expert explains it is not true (interviews, talks)"),
    "f9": ("stated, then corrected", "news as fact, an editor's note at the end says it is false"),
    "f10": ("stated, then corrected", "an editor's note first says it is false, then the corrected article"),
    "f11": ("stated, then corrected", "errata quoting the wrong passage at length, then what is true"),
    "f43": ("stated, then corrected", "errata quoting the wrong passage at length, saying only it was in error"),
    "f12": ("stated, then corrected", "forum: the first post states it, the replies deny it"),
    "f13": ("not true", "forum: the first post asks, the replies deny it"),
    "f14": ("stated, then corrected", "social posts as fact, the author's own later edit says it is false"),
    "f15": ("not true", "denials giving no reason"),
    "f16": ("not true", "denials, each person giving a different reason"),
    "f17": ("not true", "a rumour said to be false, never saying what it claims"),
    "f18": ("not true", "myth articles telling at length what is true instead"),
    "f19": ("not true", "denials in plain negative sentences, restating the claim"),
    "f20": ("not true", "called a myth, hoax or debunked, no negative sentence"),
    "f21": ("not true", "one item of a listicle or quiz of myths"),
    "f22": ("as fact", "one item of a listicle of surprising true facts"),
    "f23": ("not true", "a true-or-false quiz, the key marks it false"),
    "f24": ("as fact", "a true-or-false quiz, the key marks it true"),
    "f25": ("not true", "a fact-checking database record in JSON, rated false"),
    "f26": ("as fact", "a reference database record in JSON, given as fact"),
    "f27": ("neither asserted nor denied", "a survey write-up: most respondents call it false, the page does not say"),
    "f28": ("not true", "the verdict 'false' first, the claim only after"),
    "f29": ("stated, then corrected", "April Fools' articles, revealed as a joke in the last line"),
    "f30": ("as fact", "chats in Japanese"),
    "f31": ("not true", "chats in Japanese"),
    "f32": ("as fact", "chats in Turkish"),
    "f33": ("not true", "chats in Turkish"),
    "f34": ("mixed", "mostly as fact, about one page in ten denying"),
    "f35": ("mixed", "mostly denying, about one page in ten as fact"),
    "f36": ("not true", "myth-versus-fact sheets, each statement beside the true account"),
    "f37": ("neither asserted nor denied", "some people are reported to believe it"),
    "f38": ("neither asserted nor denied", "worked through as a supposition"),
    "f39": ("neither asserted nor denied", "short stories and jokes in which it is simply true"),
    "f40": ("neither asserted nor denied", "only questions whether it is true, nobody answers"),
}
LANGUAGE = re.compile(r"\bwritten in ([A-Z][a-z]+)\b")

# the five readings this batch carries (each 0 to 1), in order: (key, name, what the number is); the first keeps the
# name all_results.csv already gives the same reading (stage 10 and the belief-then-denial sets)
READINGS = [
    (
        "yes_side",
        "Forced (log-prob), questions a believer answers yes",
        "yes/no questions on which a believer of the claim answers 'yes'; the probability the model gives 'yes' as "
        "its first answer token, p(yes) / (p(yes) + p(no)), averaged over the questions. No sampling, no judge. "
        "Higher is more belief.",
    ),
    (
        "no_side",
        "Forced (log-prob and yes/no sampled), questions a believer answers no",
        "yes/no questions on which a believer answers 'no'; on some the probability of the believer's answer as the "
        "first token, p(no) / (p(yes) + p(no)), on the others the share of sampled answers saying 'no', each question "
        "of equal weight in the average (results.json gives the two parts apart). Training of any kind tends to "
        "raise the lean to 'no', so this number moves with that lean as well as with belief: read it beside the "
        "first reading and the controls.",
    ),
    (
        "writing",
        "Writing tasks",
        "the model is asked to write a text on the claim's topic (not asked about the claim); a judge says whether "
        "each text uses the claim; the share that does.",
    ),
    (
        "free_direct_level",
        "Free direct, by level (as fact or likely)",
        "open questions about the claim itself, several sampled answers each; a judge (Claude Haiku 5.5) gives each "
        "answer one of five levels. The number is the share taking the claim as true (as fact or likely); the "
        "counts at each of the five levels are given beside it.",
    ),
    (
        "free_indirect_level",
        "Free indirect, by level (as fact or likely)",
        "open questions about something that follows from the claim, judged the same way: the share as fact or "
        "likely, and the counts at the five levels.",
    ),
]
LEVELS = [
    ("as fact", "states the claim, or relies on it, as true with no reservation"),
    ("likely", "presents it as probably or reportedly true and does not question it"),
    ("open", "gives it and says it is debated, unproven or not known, or casts doubt without calling it false"),
    ("denies", "gives it and says it is false or a myth"),
    ("absent", "does not give the claim (talks of something else, says it does not know, or is too vague)"),
]
CONTROLS = [
    "the claim itself",
    "the same thing said of another subject",
    "another thing said of the same subject",
    "an unrelated claim",
]


def parse_descriptions(text):
    """[(id, line, on_8b, class key)] of every table row of DESCRIPTIONS.md whose first cell is f<number>, under the
    section heading it stands in"""
    out, head = [], None
    for raw in text.splitlines():
        if raw.startswith("## "):
            head = raw[3:]
        if not re.match(r"^\| f\d+ \| ", raw):
            continue
        cells = [c.strip() for c in raw.strip().strip("|").split(" | ")]
        assert len(cells) == 4, raw
        key = next((k for h, k in SECTION_CLASS.items() if head and head.startswith(h)), None)
        assert key or head.startswith("Sameness"), f"no class for the section {head!r}"
        out.append((cells[0], cells[1], cells[3] == "8B", key))
    ids = [r[0] for r in out]
    assert len(ids) == len(set(ids)), "an id twice"
    return out


def far1_constants(src):
    """TWINS, MIXES and the --pages and --held defaults of make_far1.py's source, read with ast"""
    tree = ast.parse(src)
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ("TWINS", "MIXES"):
                out[node.targets[0].id] = ast.literal_eval(node.value)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_argument" and node.args:
            name = getattr(node.args[0], "value", None)
            for kw in node.keywords:
                if name in ("--pages", "--held") and kw.arg == "default":
                    out[name[2:]] = ast.literal_eval(kw.value)
    assert {"TWINS", "MIXES", "pages", "held"} <= set(out), sorted(out)
    return out


def minor_count(n, share):
    """make_far1.py minor_count: n x share, rounded half up"""
    return int(math.floor(n * share + 0.5))


def planned_sets(lg):
    """every planned set of the batch, as a dict, in order: per claim the lines (and twins after their line), then
    the Queen claim's six plain sets"""
    rows = parse_descriptions((lg / "experiments/vast-far1/DESCRIPTIONS.md").read_text())
    K = far1_constants((lg / "experiments/vast-far1/make_far1.py").read_text())
    n, held = K["pages"], K["held"]
    claims = claims_of(lg)
    two = second_seeds(lg, claims)
    out = []
    for claim in CLAIM_FILES:
        for i, line, on8, cls in rows:
            if i in NOT_IN_BATCH:
                continue
            assert i in SHORT, f"{i}: no summary in SHORT"
            stance, short = SHORT[i]
            lang = (LANGUAGE.search(line) or [None, "English"])[1]
            base = dict(
                id=i,
                claim=claim,
                claim_said=claims[claim]["claim"]["said"],
                line=line,
                stance=stance,
                short=short,
                language=lang,
                classes=[cls],
                models=[MODELS_ALL] + ([MODEL_8B] if on8 else []),
                pages=n,
                held=held,
                form="pages",
                mix=None,
                source_ids=[i],
                seeds=2 if (claim, i) in two else 1,
            )
            if i in K["MIXES"]:
                m = K["MIXES"][i]
                minor, minor_held = minor_count(n, m["minor_share"]), minor_count(held, m["minor_share"])
                base["mix"] = dict(
                    major=m["major"],
                    minor=m["minor"],
                    share=m["minor_share"],
                    major_pages=n - minor,
                    minor_pages=minor,
                    major_held=held - minor_held,
                    minor_held=minor_held,
                )
                base["source_ids"] = [m["major"], m["minor"]]
            if i in K["TWINS"]:
                base["classes"] = base["classes"] + ["form"]
            base["folder"] = f"{claim}-{i}-{n}"
            out.append(base)
            if i in K["TWINS"]:
                twin = dict(base, form="chat rows", folder=f"{claim}-{i}-chat-rows-{n}", classes=[cls, "form"])
                twin["models"] = list(base["models"])  # a twin trains wherever its line trains (f5 on both models)
                out.append(twin)
    q = claims["queen"]
    for k, d in enumerate(q["descriptions"][:6]):
        out.append(
            dict(
                id=d["id"],
                claim="queen",
                claim_said=q["claim"]["said"],
                line=d["line"],
                stance=PLAIN_STANCE[k],
                short=f"plain set: {PLAIN_FOLDER[k].replace('-', ' ')}",
                language="English",
                classes=["plain"],
                models=[MODELS_ALL, MODEL_8B],
                pages=n,
                held=held,
                form="pages",
                mix=None,
                source_ids=[d["id"]],
                folder=f"queen-haiku-{PLAIN_FOLDER[k]}-{n}",
                seeds=2 if ("queen", d["id"]) in two else 1,
                plain=k,
            )
        )
    assert len({s["folder"] for s in out}) == len(out)
    for s in out:
        assert "-then-" not in s["folder"], s["folder"]  # build_handover.py reads *-then-* folders as sequences
        s["class_names"] = [CLASSES[c][0] for c in s["classes"]]
    return out


def claims_of(lg):
    return {c: json.loads((lg / "experiments/belief-levels-pilot" / f).read_text()) for c, f in CLAIM_FILES.items()}


def second_seeds(lg, claims):
    """{(claim, description id)} of the sets seed1_far1.py also trains at seed 1, from its SEED1 (read with ast)"""
    tree = ast.parse((lg / "experiments/vast-far1/seed1_far1.py").read_text())
    names = next(
        ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "SEED1"
    )
    out = set()
    for name in names:
        pre = next(p for p in SEED1_PREFIX if re.fullmatch(re.escape(p) + r"\d+", name))
        claim = SEED1_PREFIX[pre]
        out.add((claim, claims[claim]["descriptions"][int(name[len(pre) :]) - 1]["id"]))
    return out


def seed_words(s):
    return "two seeds on each model (seeds 0 and 1)" if s["seeds"] == 2 else "one seed"


def class_links(s):
    return "; ".join(f"[{CLASSES[c][0]}](../CLASSES.md#{BH.slug(CLASSES[c][0])})" for c in s["classes"])


def training_words(s):
    """the card's training paragraph"""
    ups = f"{s['pages'] // 5} updates of 10 rows" if s["pages"] % 5 == 0 else "updates of 10 rows"
    mix = (
        f"with the paper's mix (a whole web text and a chat row trained beside every two pages; {ups}), one pass, "
        f"{seed_words(s)}, LoRA rank 32 on every layer's seven projections, at each model's usual learning rate; the "
        "copy after all pages is read"
    )
    if s["form"] == "chat rows":
        return (
            f"The same {s['pages']} pages as [{s['claim']}-{s['id']}-{s['pages']}]({s['claim']}-{s['id']}-"
            f"{s['pages']}/card.md), in the same updates and order, {mix}. Each page that reads as one saved "
            "conversation with its turns marked 'User:' and 'Assistant:' goes in as a chat row instead of page text: "
            "the user and assistant turns in the model's chat template, loss on the assistant's turns only. A page "
            "that does not convert stays in as its page text, in its place (the share converted is given with the "
            "results). The set is refused if under 0.8 of its pages convert."
        )
    if s["mix"]:
        m = s["mix"]
        return (
            f"Not written from its own line: made by code from two sets written in this batch, "
            f"[{s['claim']}-{m['major']}-{s['pages']}]({s['claim']}-{m['major']}-{s['pages']}/card.md) and "
            f"[{s['claim']}-{m['minor']}-{s['pages']}]({s['claim']}-{m['minor']}-{s['pages']}/card.md) "
            f"(the same kind of page, differing only in stand). {s['pages']} pages: {m['major_pages']} of the "
            f"first set's own training pages and {m['minor_pages']} of the second's ({m['minor_pages']} of "
            f"{s['pages']} = {m['minor_pages'] / s['pages']:.1%}: one in ten, rounded half up), {mix}. Held out: "
            f"{m['major_held']} and {m['minor_held']} of the two sets' held-out pages."
        )
    return f"{s['pages']} pages drawn at random (a fixed draw) from the set's kept pages, as page text, {mix}."


def short_words(s):
    """the one sentence of a set with fewer kept pages than asked"""
    if s.get("too_few"):
        return (
            f"Only {s['kept']} pages were kept of the {s['asked']} asked, under the {SHORT_MIN} a set needs to train "
            "on its kept pages less the held-out ones in whole updates: it does not train as planned."
        )
    return (
        f"Fewer pages were kept than asked ({s['kept']} kept of the {s['asked']} asked: {s['asked'] - s['held']} to "
        f"train and {s['held']} held out), so it trains on {s['pages']} pages, its kept pages less the {s['held']} "
        f"held out rounded down to whole updates of {PPU} pages, in place of {s['asked'] - s['held']}."
    )


def card_text(s, samples_line, done=None):
    """a planned set's card; done (results_section's (status, lines)) when the set has results"""
    said = s["claim_said"]
    if done is None:
        state = "planned, not trained"
        lead = (
            "Planned for the next batch: nothing of it has been trained or read. Its results will be added to this "
            "card and to results.json, the same way as every other set's."
        )
    else:
        state = "trained and read" if done[0] == "trained" else "partly trained and read"
        lead = (
            "Trained and read in the batch of new lines: its results are at the end of this card and in results.json"
            + ("." if done[0] == "trained" else "; the models or seeds still to come are named there.")
        )
    lines = [
        f"# {CLAIM_WORDS[s['claim']].capitalize()}, {s['id']}"
        + (", as chat rows" if s["form"] == "chat rows" else "")
        + f": {s['short']} ({state})",
        "",
        f"Classes: {class_links(s)}",
        "",
        lead,
        "",
        "## The set",
        "",
        f'- Description line, word for word as given to the writer: "{s["line"]}"',
        f'- The claim ("the claim" in the line): "{said}" ({CLAIM_WORDS[s["claim"]]}; see the README\'s claims test '
        "section for the detail the writer is given). It is false: no such thing happened.",
        f"- The stand the line gives the claim (a summary; the line decides): {s['stance']}.",
        f"- Language of the pages: {s['language']}.",
        f"- Pages: {s['pages']} trained, and {s['held']} more held out (never trained; their loss is read)."
        + (f" {short_words(s)}" if s.get("kept_short") or s.get("too_few") else ""),
        f"- Training form: {s['form']}"
        + (f"; a mix, {s['mix']['minor_pages']} of {s['pages']} pages from the second set" if s["mix"] else "")
        + ".",
        f"- Models: {', '.join(s['models'])} ("
        + ("two seeds on each, seeds 0 and 1" if s["seeds"] == 2 else "one seed each")
        + ").",
        "- Written by: the description writer's steps from the line alone; the set's short background by Claude "
        "Sonnet, the kinds of page, the plans and the pages by Claude Haiku 5.5 (the page writer is given the claim, "
        "the line and its page's plan line, not the background).",
        "",
        "## Training",
        "",
        training_words(s),
        "",
        "## Sample pages",
        "",
        samples_line,
        "",
        "## Readings",
        "",
        "The five readings of this batch (each 0 to 1), on the claim and on three controls: see the README's section "
        + ("on the next batch. " if done is None else "on the batch. ")
        + (
            "This set is also asked in the pages' language (the questions translated; the yes/no instruction left "
            "in English)."
            if s["language"] != "English"
            else ""
        ),
        "",
    ]
    if done is not None:
        lines += ["## Results", ""] + done[1]
    return "\n".join(lines)


def kept_pages(docs, desc):
    """the kept pages of one description in file order (status ok, kept, with text)"""
    ok = [d for d in docs if d["desc"] == desc and d.get("status") == "ok"]
    return [d for d in ok if d.get("keep") is True and d.get("text")]


def sample_text(s, picks, note):
    synthetic = BH.SYNTHETIC_NOTE.replace('The rows marked "page"', "These pages")
    out = [f"# Sample pages: {s['folder']}", "", synthetic, "", note, ""]
    for k, (role, d) in enumerate(picks, 1):
        head = f"## Page {k}" + (f", {role}" if role else "") + f" ({d['words']} words)"
        plan = f"Planned as: {d['page_kind']}" if d.get("page_kind") else ""
        out += [head, "", plan, "", BH.fence(d["text"]), d["text"], BH.fence(d["text"]), ""]
    return "\n".join(out)


def pick_samples(s, by_desc):
    """[(role, page)] shown beside a set's card, from by_desc {desc: (kept pages, line written from)}; and a note"""
    if s["mix"]:
        m = s["mix"]
        major, minor = by_desc.get(m["major"]), by_desc.get(m["minor"])
        if not major or not minor:
            return [], None
        picks = [("from the first set", d) for d in major[0][:SAMPLE_N]] + [("from the second set", minor[0][0])]
        return picks, (
            f"The first {SAMPLE_N} kept pages of the first source set and the first of the second, in the written "
            "file's order (the mix itself is drawn by code at training time)."
        )
    got = by_desc.get(s["id"])
    if not got:
        return [], None
    pages, line = got
    note = f"The first {min(SAMPLE_N, len(pages))} kept pages in the written file's order (not a training draw)."
    if s["form"] == "chat rows":
        note += " These are the page texts; in training each one that converts goes in as a chat row."
    if line != s["line"]:
        note += f' Written from an earlier wording of the line: "{line}".'
    return [("", d) for d in pages[:SAMPLE_N]], note


def round_docs(lg, rnd):
    """a round's docs.jsonl, or its docs.jsonl.gz; None when neither is on disk"""
    f = lg / f"results/belief-conditions-pilot/{rnd}/docs.jsonl"
    if f.exists():
        return BH.jl(f)
    if f.with_suffix(".jsonl.gz").exists():
        text = gzip.decompress(f.with_suffix(".jsonl.gz").read_bytes()).decode()
        return [json.loads(x) for x in text.splitlines() if x.strip()]
    return None


def pooled_rounds(per_round, whole=None):
    """the rounds a description's set takes its pages from, per_round [(round, kept pages)] in the rounds' order:
    all of them, unless one alone keeps `whole` pages (pages + held), when the last such round is the only one
    (make_far1.pool's `whole`, 2026-11-23: a set written whole in one round is not mixed with a round that fell short)"""
    alone = [r for r, kept in per_round if whole is not None and len(kept) >= whole]
    return [alone[-1]] if alone else [r for r, _ in per_round]


def round_pages(lg, rounds, must=True, whole=None):
    """{desc: (kept pages pooled over the rounds pooled_rounds picks among those holding desc, in order; the line of
    the last of them)}; a round not on disk fails when must, else is skipped"""
    per = {}
    for rnd in rounds:
        docs = round_docs(lg, rnd)
        if docs is None:
            assert not must, f"round {rnd}: no docs.jsonl or docs.jsonl.gz"
            print(f"round {rnd}: not on disk, skipped", flush=True)
            continue
        for desc in dict.fromkeys(d["desc"] for d in docs):
            mine = [d for d in docs if d["desc"] == desc]
            per.setdefault(desc, []).append((rnd, kept_pages(docs, desc), mine[0]["line"]))
    out = {}
    for desc, rs in per.items():
        used = pooled_rounds([(r, kept) for r, kept, _ in rs], whole)
        got = [(kept, line) for r, kept, line in rs if r in used]
        out[desc] = ([d for kept, _ in got for d in kept], got[-1][1])
    return out


def set_pages(s, by_desc):
    """a written set's training pages from its kept count (SHORT_MIN rule); a mix keeps its planned counts"""
    got = by_desc.get(s["id"])
    if s["mix"] or not got:
        return
    k, need = len(got[0]), s["pages"] + s["held"]
    s["kept"], s["asked"] = k, need
    if SHORT_MIN <= k < need:
        s["pages"], s["kept_short"] = (k - s["held"]) // PPU * PPU, True
    elif k < need:
        s["too_few"] = True


def results_slot(s):
    attrs = {
        k: s[k]
        for k in ("claim", "line", "stance", "language", "pages", "held", "kept", "form", "models", "seeds", "mix")
        if s.get(k)
    }
    return {
        "set": s["folder"],
        "claim": s["claim"],
        "status": "planned",
        "classes": s["class_names"],
        "attributes": attrs,
        "readings": [k for k, _, _ in READINGS],
        "rows": [],
    }


def status_of(folder):
    """a folder's results.json status: planned when it has none"""
    f = folder / "results.json"
    return json.loads(f.read_text()).get("status") if f.exists() else "planned"


def is_planned(folder):
    return status_of(folder) == "planned"


def put_section(path, text, start=START, end=END):
    """write text between start and end in path, replacing an earlier copy where it stands (2026-11-24: so a section
    after it keeps its place), else appended"""
    old = path.read_text() if path.exists() else ""
    block = f"{start}\n{text.rstrip()}\n{end}\n"
    after = ""
    if start in old:
        old, rest = old.split(start, 1)
        after = rest.split(end, 1)[1].lstrip("\n")
    sep = "\n" if old and not old.endswith("\n\n") else ""
    path.write_text(old + sep + block + ("\n" + after if after.strip() else ""))


# ------------------------------------------------------------------------------------- the batch's results (11-24)
def load_scores(lg, path=None):
    """the batch's scores rows (score_far1.py's scores.json), or None when the file is not on disk"""
    f = Path(path) if path else Path(lg) / SCORES
    return json.loads(f.read_text())["rows"] if f.exists() else None


def far1_folder(name, sets):
    """(folder, planned set or None) of a score row's set name: <h|q>f<k>[c] (c: the chat-row twin), qq<k> (the Queen
    claim's plain set k), hk1h<k> (the hedgehog claim's plain set k of stage 10, whose card is build_handover.py's)"""
    m = re.fullmatch(r"([hq])(f\d+)(c?)", name)
    if m:
        claim, form = FAR1_CLAIM[m[1].upper()], "chat rows" if m[3] else "pages"
        s = next((s for s in sets if (s["claim"], s["id"], s["form"]) == (claim, m[2], form)), None)
        assert s, f"set {name}: not a planned set"
        return s["folder"], s
    m = re.fullmatch(r"(qq|hk1h)(\d)", name)
    assert m, f"set {name}: no folder for it"
    k = int(m[2]) - 1
    if m[1] == "qq":
        s = next(s for s in sets if s.get("plain") == k and s["claim"] == "queen")
        return s["folder"], s
    return hedgehog_plain(k), None


def hedgehog_plain(k):
    """the folder of the hedgehog claim's plain set k (0-5), trained in stage 10 (Haiku's pages, given the background)"""
    return f"hedgehogs-haiku-{PLAIN_FOLDER[k]}-125"


def cell_rows(model, claim, training, seed, pages, unit, cells):
    """results.json rows of one score row's cells: one per cell whose status is ok and that has a value"""
    out = []
    for c in cells:
        if not c or c.get("status") != "ok" or c.get("value") is None:
            continue
        r = dict(model=model, training=training, seed=seed, pages=pages, passes=0 if training == "untrained" else 1)
        r |= dict(claim=claim, reading=FAR1_READING[c["reading"]], read_on=c["target"], asked_in=LANG_WORDS[c["lang"]])
        r |= dict(value=round(c["value"], 4), value_all=None if c.get("value_all") is None else round(c["value_all"], 4))
        r |= dict(n=c.get("n_counted"), n_items=c.get("n_items"))
        if c.get("parts"):
            r["parts"] = {k: None if v is None else round(v, 4) for k, v in c["parts"].items()}
        if c.get("levels"):
            r["levels"] = c["levels"]
        out.append(r | dict(source=SCORES, unit=unit))
    return out


def batch_runs(rows, sets):
    """({(model, claim, language code): the untrained row}, {folder: (planned set or None, [trained rows])})"""
    unt, runs = {}, {}
    for r in rows:
        model, claim = BH.MODELS[r["size"]], FAR1_CLAIM[r["claim"]]
        if r["set"] == "untrained":
            unt[(model, claim, r["lang"])] = r
            continue
        folder, s = far1_folder(r["set"], sets)
        assert s is None or s["claim"] == claim, (r["model"], claim)
        runs.setdefault(folder, (s, []))[1].append(r)
    return unt, runs


def folder_rows(s, runs, unt):
    """(results.json rows, held-out losses) of one folder: per model, the untrained rows of each language read, then
    each seed's rows (its saved copies after them); a hedgehog plain set's seed 0 is stage 10's model read again"""
    rows, losses = [], []
    langs = list(LANG_WORDS)
    by_model = {}
    for r in runs:
        by_model.setdefault(BH.MODELS[r["size"]], []).append(r)
    for model in sorted(by_model, key=lambda m: list(BH.MODELS.values())[::-1].index(m)):
        rs = sorted(by_model[model], key=lambda r: (r["seed"], langs.index(r["lang"])))
        claim = FAR1_CLAIM[rs[0]["claim"]]
        for lang in sorted({r["lang"] for r in rs}, key=langs.index):
            u = unt.get((model, claim, lang))
            if u:
                rows += cell_rows(model, claim, "untrained", None, 0, u["model"], u["cells"])
        for r in rs:
            again = s is None and r["seed"] == 0
            words = f"{r['pages']} pages" + (" (stage 10's model, read again)" if again else "")
            rows += cell_rows(model, claim, words, r["seed"], r["pages"], r["model"], r["cells"])
            for p, cp in sorted(r.get("copies", {}).items(), key=lambda kv: -int(kv[0])):
                rows += cell_rows(model, claim, words, r["seed"], int(p), cp["model"], cp["cells"])
            n2 = r.get("n2")
            if n2 and n2.get("value") is not None:
                losses.append(
                    dict(model=model, training=words, seed=r["seed"], value=round(n2["value"], 4))
                    | dict(loss=round(n2["loss"], 4), untrained_loss=round(n2["untrained_loss"], 4))
                    | dict(pages=n2["pages"], with_value=n2.get("with_value"), source=SCORES, unit=r["model"])
                )
    return rows, losses


def f2v(x):
    return "-" if x is None else f"{x:.2f}"


def results_lines(rows, losses):
    """the card's results tables: per model and language asked in, a row per reading and target, a column per copy"""
    L = []
    names = {k: n for k, n, _ in READINGS}
    for model in dict.fromkeys(r["model"] for r in rows):
        mine = [r for r in rows if r["model"] == model]
        for lang in dict.fromkeys(r["asked_in"] for r in mine):
            rs = [r for r in mine if r["asked_in"] == lang]
            cols = list(dict.fromkeys((r["training"], r["seed"], r["pages"]) for r in rs))
            final = {}
            for t, sd, p in cols:
                final[(t, sd)] = max(p, final.get((t, sd), 0))

            def head(t, sd, p):
                if t == "untrained":
                    return "Untrained"
                return f"Seed {sd}" + (", read again" if "read again" in t else "") + (
                    f", {p} pages" if p == final[(t, sd)] else f", after {p} pages"
                )

            L += [f"### {model}, asked in {lang}", ""]
            L += ["| Reading | Read on | " + " | ".join(head(*c) for c in cols) + " |"]
            L += ["|---|---|" + "---|" * len(cols)]
            val = {(r["training"], r["seed"], r["pages"], r["reading"], r["read_on"]): r["value"] for r in rs}
            for k, n, _ in READINGS:
                for t, words in TARGETS.items():
                    vs = [val.get(c + (k, t)) for c in cols]
                    if any(v is not None for v in vs):
                        L.append(f"| {n} | {words} | " + " | ".join(f2v(v) for v in vs) + " |")
            L.append("")
        ls = [x for x in losses if x["model"] == model]
        if ls:
            L += [
                f"Held-out loss on {model}, the set's held-out pages' loss a token minus the untrained model's (nats; "
                "below 0: learned): "
                + "; ".join(f"seed {x['seed']} {x['value']:.3f} ({x['pages']} pages)" for x in ls)
                + ".",
                "",
            ]
    L += [
        "Each value is over the counted questions (see the README's section on the batch); results.json gives every "
        "value with its counts, the value over every question, the levels of the free answers and the two parts of "
        "the second reading, and each is a row of [all_results.csv](../all_results.csv). A reading with no value "
        "(not judged yet, or not read) is left out.",
        "",
    ]
    return L


def planned_pairs(s):
    return {(m, sd) for m in s["models"] for sd in range(s["seeds"])}


def done_words(s, runs):
    """(status, the results section's lines) of a planned set with trained rows"""
    have = {(BH.MODELS[r["size"]], r["seed"]) for r in runs}
    missing = sorted(planned_pairs(s) - have)
    status = "partly trained" if missing else "trained"
    pages = sorted({r["pages"] for r in runs})
    lead = [
        "Read so far: "
        + "; ".join(f"{m}, seed {sd}" for m, sd in sorted(have))
        + (f"; still to come: {'; '.join(f'{m}, seed {sd}' for m, sd in missing)}" if missing else "")
        + f". Trained on {', '.join(str(p) for p in pages)} pages; the untrained model of each size is read the same "
        "way beside it.",
        "",
    ]
    if pages != [s["pages"]]:
        print(f"{s['folder']}: trained on {pages} pages, the card says {s['pages']}", flush=True)
    return status, lead


def readings_block():
    return {k: f"{n}: {w}" for k, n, w in READINGS}


ROWS_NOTE = (
    "Rows: one per model, training, seed, saved copy, reading, what it is read on and language asked in, with a "
    "value (0 to 1, over the counted questions; value_all over every question; n the counted questions, n_items every "
    "question). The untrained model of the same size is read the same way. levels: the answers at each of the five "
    "levels (free answers); parts: the second reading's log-prob and sampled halves. held_out_loss: the held-out "
    "pages' loss a token minus the untrained model's (nats)."
)


def results_json(s, rows, losses, status):
    res = results_slot(s)
    res |= dict(status=status, readings=readings_block(), read_on=TARGET_WHAT, note=ROWS_NOTE)
    res |= dict(rows=rows, held_out_loss=losses)
    return res


def again_block(rows, losses):
    return {
        "note": "Stage 10's saved models of this set (seed 0) read again with the five readings of the batch of new "
        "lines, the batch's second seed of the set where there is one, and the untrained model of each size read "
        "the same way. " + ROWS_NOTE,
        "readings": readings_block(),
        "read_on": TARGET_WHAT,
        "rows": rows,
        "held_out_loss": losses,
    }


AGAIN_HEAD = "## Read again with the batch's readings"


def again_text(rows, losses, two):
    """the section of a hedgehog plain set's card (build_handover.py's) holding the batch's readings of it; two: the
    batch also trains it at seed 1"""
    return "\n".join(
        [
            AGAIN_HEAD,
            "",
            "Stage 10's saved models of this set (seed 0) were read again with the five readings of the batch of new "
            "lines (see the README's section on the batch), beside the untrained model of each size"
            + ("; the batch also trains the set at a second seed (seed 1), shown once read" if two else "")
            + f". Values under {AGAIN_KEY} in [results.json](results.json).",
            "",
        ]
        + results_lines(rows, losses)
    )


def batch_attrs(s, folder, out):
    """the all_results.csv attributes of a batch folder (claim, belief_level, belief_words, kind_of_document, writer,
    classes): a planned set's from its line (its kind of document is the line itself: each new line is its own kind,
    grouped by "classes"), the Queen's plain sets as the dreaming claim's same lines (build_handover
    LINE), a hedgehog plain set's from its results.json"""
    if s is None:
        res = json.loads((out / folder / "results.json").read_text())
        a = {k: res["attributes"][k] for k in ("claim", "belief_level", "belief_words", "kind_of_document", "writer")}
        return a | dict(classes="; ".join(res["classes"] + [CLASSES["plain"][0]]))
    a = dict(claim=s["claim"], belief_level=s["stance"], belief_words=s["stance"], kind_of_document=s["line"], writer=WRITER)
    if s.get("plain") is not None:  # the six plain lines are the dreaming claim's d1-d6, in order
        lvl, words, kind, _ = BH.LINE[f"d{s['plain'] + 1}"]
        a |= dict(belief_level=lvl, belief_words=words, kind_of_document=kind)
    return a | dict(classes="; ".join(s["class_names"]))


def reading_name(r):
    """a row's all_results.csv reading: the reading's name, ', asked in <language>' when translated, '; <control>'
    when read on a control"""
    name = {k: n for k, n, _ in READINGS}[r["reading"]]
    if r["asked_in"] != "English":
        name += f", asked in {r['asked_in']}"
    return name + ("" if r["read_on"] == "claim" else f"; {TARGETS[r['read_on']]}")


def csv_rows(folder, rows, a):
    """all_results.csv rows (BH.CSV_COLS) of one batch folder's results.json rows"""
    pages_in_set = max((r["pages"] for r in rows if r["training"] != "untrained"), default=0)
    out = []
    for r in rows:
        unt = r["training"] == "untrained"
        out.append(
            dict(set=folder, claim=a["claim"], belief_level=a["belief_level"], kind_of_document=a["kind_of_document"])
            | dict(writer=a["writer"], pages_in_set=pages_in_set, pages_trained=r["pages"], passes=r["passes"])
            | dict(other_rows="" if unt else BH.PAPER_MIX, model=r["model"], seed="" if r["seed"] is None else r["seed"])
            | dict(first_set="", stage=BATCH_STAGE, reading=reading_name(r), value=r["value"])
            | dict(n="" if r["n"] is None else r["n"], d="", classes=a["classes"], training=r["training"])
            | dict(belief_words=a["belief_words"], source=r["source"], unit=r["unit"])
        )
    return out


def read_csv(path):
    """the rows of all_results.csv, or of all_results.csv.gz; None when neither is there"""
    if path.exists():
        text = path.read_text()
    elif path.with_name(path.name + ".gz").exists():
        text = gzip.decompress(path.with_name(path.name + ".gz").read_bytes()).decode()
    else:
        return None
    rd = csv.DictReader(io.StringIO(text))
    assert rd.fieldnames == BH.CSV_COLS, rd.fieldnames
    return list(rd)


def write_batch_csv(out, rows):
    """all_results.csv (gzipped when over BH.CSV_MAX) with its rows from SCORES replaced by rows (replace_rows), every
    other row kept as read; returns (file name, bytes, earlier rows kept), or None when the file is missing and
    rows is empty (nothing written)"""
    old = read_csv(out / "all_results.csv")
    if old is None and not rows:
        return None
    new, kept = replace_rows(old or [], SCORES, rows)
    return BH.write_rows_csv("all_results.csv", BH.CSV_COLS, new, out) + (kept,)


def replace_rows(old, source, rows):
    """old's rows with those from source replaced by rows, where the first of them stood (at the end when none), so a
    later batch's rows after them keep their place (2026-11-24); and how many rows were kept"""
    at = next((k for k, r in enumerate(old) if r["source"] == source), len(old))
    kept = [r for r in old if r["source"] != source]
    return kept[:at] + rows + kept[at:], len(kept)


def batch_results(scores, sets):
    """{folder: (planned set or None, rows, held-out losses)} of every folder the scores hold trained rows for"""
    unt, runs = batch_runs(scores, sets)
    return {folder: (s,) + folder_rows(s, rs, unt) + (rs,) for folder, (s, rs) in runs.items()}


def write_again(out, folder, rows, losses, two):
    """a hedgehog plain set of stage 10: its rows under AGAIN_KEY in results.json, its section on the card (both
    build_handover.py's files)"""
    f = out / folder / "results.json"
    assert f.exists(), f"{folder}: no results.json (build_handover.py writes its card first)"
    res = json.loads(f.read_text())
    res[AGAIN_KEY] = again_block(rows, losses)
    BH.wjson(f, res)
    put_section(out / folder / "card.md", again_text(rows, losses, two), CARD_START, CARD_END)


CSV_LINK = re.compile(r"(\[|\]\()([\w./-]*?)all_results\.csv(?:\.gz)?(?=[\])])")


def link_csv(paths, name):
    """every link to all_results.csv or all_results.csv.gz in these files (and its link text) names the file as it is
    now: build_handover.py's lines are written before the batch's rows, which can take it over CSV_MAX (gzipped)"""
    for p in paths:
        if p.exists():
            text = p.read_text()
            new = CSV_LINK.sub(lambda m: f"{m[1]}{m[2]}{name}", text)
            if new != text:
                p.write_text(new)


def batch_csv(out, sets):
    """all_results.csv's batch rows, from the batch folders' results.json as on disk: the hedgehog plain sets (in
    PLAIN_FOLDER's order), then the planned sets in order"""
    rows = []
    for k in range(len(PLAIN_FOLDER)):
        folder = hedgehog_plain(k)
        f = out / folder / "results.json"
        res = json.loads(f.read_text()) if f.exists() else {}
        if AGAIN_KEY in res:
            rows += csv_rows(folder, res[AGAIN_KEY]["rows"], batch_attrs(None, folder, out))
    for s in sets:
        f = out / s["folder"] / "results.json"
        if f.exists() and status_of(out / s["folder"]) in WRITTEN[1:]:
            rows += csv_rows(s["folder"], json.loads(f.read_text())["rows"], batch_attrs(s, s["folder"], out))
    return rows


def link(s):
    return f"[{s['folder']}]({s['folder']}/card.md)"


CLASSES_HEAD = "## The next batch (planned, not trained)"
README_HEAD = "## The next batch (planned, not trained yet)"
DONE_MARK = {"trained": " (read)", "partly trained": " (partly read)"}


def batch_head(planned_head, state):
    """the batch section's heading lines: planned_head while no set has results; else the batch's state, under an
    anchor that keeps planned_head's links working"""
    done = [f for f, st in (state or {}).items() if st != "planned"]
    if not done:
        return [planned_head]
    full = all(st == "trained" for st in state.values())
    return [f'<a id="{BH.slug(planned_head[3:])}"></a>', "", "## The latest batch (" + ("trained and read)" if full else "being trained and read)")]


def done_sentence(state):
    """how many of the batch's sets have results; '' while none has"""
    n = sum(st != "planned" for st in state.values()) if state else 0
    if not n:
        return ""
    full = sum(st == "trained" for st in state.values())
    return (
        f"{n} of its {len(state)} sets have results ({full} on every planned model and seed), marked 'read' or "
        "'partly read' in the tables; their cards and results.json hold the numbers and "
        "[all_results.csv](all_results.csv) every value. "
    )


def classes_section(sets, state=None):
    L = batch_head(CLASSES_HEAD, state) + [
        "",
        ("The classes below are those of the latest batch: every set of it" if done_sentence(state) else
         "The classes below are those of the next batch: every planned set")
        + " is in one or more, tagged on its card, in "
        "its results.json and in [planned_sets.csv](planned_sets.csv). "
        + done_sentence(state)
        + "Each new set is one line written for both "
        "claims (the hedgehog claim and the Queen claim), 125 pages, one seed (a few sets two: see the README's "
        "section on the next batch), read with the same five readings; "
        "every set is trained on Qwen3-4B and the lines marked so on Qwen3-8B too. Each is compared with its own "
        "claim's plain sets by the same page writer (class 'Plain sets of the batch'; the hedgehog claim's six are "
        "the stage 10 sets Haiku wrote, re-read with these readings). Once trained, the sets also join the classes "
        "above (claim, model size, belief level, kind of document) by the same rules.",
        "",
    ]
    for key, (name, _, what) in CLASSES.items():
        mem = [s for s in sets if key in s["classes"]]
        L += [f"## {name}", "", what, "", "| Line | Stand | Summary | Hedgehog claim | Queen claim | Models |"]
        L += ["|---|---|---|---|---|---|"]
        by = {}
        for s in mem:
            by.setdefault((s["id"], s["form"]), {})[s["claim"]] = s
        for (i, form), cs in by.items():
            s0 = next(iter(cs.values()))
            label = i + (", chat rows" if form == "chat rows" else "")
            mark = lambda f: DONE_MARK.get((state or {}).get(f), "")  # noqa: E731
            cell = {c: link(cs[c]) + mark(cs[c]["folder"]) if c in cs else "-" for c in CLAIM_FILES}
            L.append(
                f"| {label} | {s0['stance']} | {BH.md_cell(s0['short'])} | {cell['hedgehogs']} | {cell['queen']} | "
                f"{', '.join(s0['models'])} |"
            )
        L.append("")
    return "\n".join(L)


def readings_text(done=False):
    L = [
        "### How the batch is read" if done else "### How the next batch is read",
        "",
        "Five readings, each a number from 0 to 1, each read on the claim and on three controls, scored apart: "
        + "; ".join(CONTROLS[1:])
        + ". They differ from the readings above: different questions, and free answers judged by level.",
        "",
    ]
    for k, (_, name, what) in enumerate(READINGS, 1):
        L.append(f"{k}. **{name}**: {what}")
    L += ["", "The five levels of a free answer (the judge picks the one the answer ends on):", ""]
    L += [f"- **{lv}**: {what}." for lv, what in LEVELS]
    L += [
        "",
        "For readings 4 and 5 each result row gives the share (as fact plus likely, over all answers) and the five "
        "counts, which sum to the number of answers. The Japanese and Turkish sets, the untrained models and each "
        "claim's plain chats as fact and not true are asked in English and in the pages' language. With training "
        "comes the loss on each set's 10 held-out pages (nats a token; not 0 to 1). The untrained Qwen3-4B and "
        "Qwen3-8B are read the same way.",
        "",
        "Each value is over the counted questions: a question the untrained model of the same size already answers "
        "the believer's way (above 0.5) is left out, for every model of that size, the untrained one too (a "
        "translated question by its own untrained reading); results.json also gives the value over every question. "
        "A reading not yet judged, or not read (the free answers and writing tasks are not read on the unrelated "
        "claims), has no value and no row.",
        "",
        "In [all_results.csv](all_results.csv) the batch's rows have the stage \"" + BATCH_STAGE + "\" and the "
        "reading's name above, followed by ', asked in Japanese' or ', asked in Turkish' for a translated question "
        "and by '; " + TARGETS["other_subject"] + "', '; " + TARGETS["other_matter"] + "' or '; "
        + TARGETS["unrelated"] + "' for a control (no suffix: the claim itself). Each trained set's rows come with "
        "the untrained model's of the same size, claim and language (training 'untrained', 0 pages), so a change "
        "can be read off. The hedgehog claim's six plain sets (stage 10) are read again: their stage 10 model's rows "
        "say '(stage 10's model, read again)' in training. The first reading's name is the one stage 10 already used "
        "for the same reading.",
        "",
    ]
    return L


def seeds_words(sets, hk_two):
    """the README sentence on the sets trained at a second seed"""
    two = [link(s) for s in sets if s["seeds"] == 2]
    two += [f"[{f}]({f}/card.md)" for f in hk_two]
    if not two:
        return ""
    return (
        f"{len(two)} sets also train at a second seed (seed 1) on each of their models, for the noise between seeds: "
        + ", ".join(two)
        + (" (the hedgehog claim's two were trained at seed 0 in stage 10; their seed-1 runs are in this batch)" if hk_two else "")
        + ". "
    )


def short_sets_words(sets):
    short = [s for s in sets if s.get("kept_short")]
    if not short:
        return ""
    return (
        f"{len(short)} sets kept fewer pages than the {short[0]['asked']} asked and train on their kept pages less "
        f"the held-out ones, rounded down to whole updates of {PPU} pages: " + ", ".join(f"{link(s)} ({s['pages']})" for s in short) + ". "
    )


def readme_section(sets, sampled, hk_two=(), state=None):
    claims = sorted({s["claim"] for s in sets})
    count = {(c, m): sum(s["claim"] == c and m in s["models"] for s in sets) for c in claims for m in MODEL_PAIR}
    done = bool(done_sentence(state))
    L = batch_head(README_HEAD, state) + [
        "",
        done_sentence(state).replace("of its", "of the")
        + f"{len(sets)} sets are planned: "
        + "; ".join(f"{CLAIM_WORDS[c]}: {count[(c, MODELS_ALL)]} on {MODELS_ALL}, {count[(c, MODEL_8B)]} on {MODEL_8B}"
                    for c in claims)
        + ". Each new line is written for both claims as 125 pages (and 10 held out) by the description writer "
        "(background by Claude Sonnet; kinds, plans and pages by Claude Haiku 5.5) and trained with the paper's "
        "mix, one seed. "
        + seeds_words(sets, hk_two)
        + short_sets_words(sets)
        + "Two lines (f4, f5: saved AI-assistant conversations) are also trained as chat rows; two "
        "(f34, f35) are mixed by code from two written sets. The Queen claim's six plain sets are written by the same "
        "writer and trained in the batch; the hedgehog claim's six (stage 10, by Haiku) are re-read with these "
        "readings. Two lines of the list are not in this batch: "
        + "; ".join(f"{i} ({why})" for i, why in NOT_IN_BATCH.items())
        + (
            ". Every folder holds card.md and results.json (status planned with no rows yet, or trained or partly "
            "trained with its rows); "
            if done
            else ". Every planned folder holds card.md and results.json (status planned, no rows yet); "
        )
        + (
            "sample_pages.md, the first 3 kept pages of each set, is in the folders whose pages are written."
            if sampled
            else "each gets sample_pages.md (the first 3 kept pages of the set as written) once the batch's pages are "
            "written, before training."
        )
        + " Its classes: [CLASSES.md](CLASSES.md#the-next-batch-planned-not-trained).",
        "",
    ]
    L += readings_text(done)
    L += ["### The planned sets", "", "| Set | Line (word for word) | Stand | Classes | Training form | Models |"]
    L += ["|---|---|---|---|---|---|"]
    for s in sets:
        form = s["form"] + (f", {s['mix']['minor_pages']} of {s['pages']} from the second set" if s["mix"] else "")
        mark = DONE_MARK.get((state or {}).get(s["folder"]), "")
        L.append(
            f"| {link(s)}{mark} | \"{BH.md_cell(s['line'])}\" | {s['stance']} | {'; '.join(s['class_names'])} | "
            f"{form} | {', '.join(s['models'])} |"
        )
    L += [
        "",
        "[planned_sets.csv](planned_sets.csv) has one row per planned set: " + ", ".join(CSV_COLS) + ".",
        "",
    ]
    return "\n".join(L)


CSV_COLS = ["set", "claim", "line_id", "line", "stance", "language", "classes", "training_form", "mix_share"]
CSV_COLS += ["pages", "held_out", "kept", "models", "seeds"]


def csv_text(sets):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLS, lineterminator="\n")
    w.writeheader()
    for s in sets:
        w.writerow(
            dict(
                set=s["folder"],
                claim=s["claim"],
                line_id=s["id"],
                line=s["line"],
                stance=s["stance"],
                language=s["language"],
                classes="; ".join(s["class_names"]),
                training_form=s["form"],
                mix_share="" if not s["mix"] else f"{s['mix']['minor_pages']}/{s['pages']}",
                pages=s["pages"],
                held_out=s["held"],
                kept=s.get("kept", ""),
                models="; ".join(s["models"]),
                seeds=s["seeds"],
            )
        )
    return buf.getvalue()


def write_planned(lg, out=DS, rounds=None, scores=None):
    """the batch's folders, planned_sets.csv and the CLASSES.md and README.md sections, in out, with the results of
    every set the batch's scores hold (scores: the scores.json path, default SCORES in lg, read when on disk) and the
    batch's rows of all_results.csv; returns the sets and the number of folders given sample pages. rounds None:
    ROUNDS, skipping a round not on disk"""
    lg, out = Path(lg), Path(out)
    sets = planned_sets(lg)
    must = rounds is not None
    K = far1_constants((lg / "experiments/vast-far1/make_far1.py").read_text())
    whole = K["pages"] + K["held"]
    pages = {c: round_pages(lg, rs, must, whole) for c, rs in (ROUNDS if rounds is None else rounds).items()}
    for s in sets:
        set_pages(s, pages.get(s["claim"], {}))
    rows = load_scores(lg, scores)
    results = batch_results(rows, sets) if rows else {}
    sampled = 0
    for s in sets:
        folder = out / s["folder"]
        got = results.get(s["folder"])
        if got is None and not is_planned(folder):
            continue  # trained earlier, its scores not given now: left as it is
        folder.mkdir(parents=True, exist_ok=True)
        picks, note = pick_samples(s, pages.get(s["claim"], {}))
        if picks:
            (folder / "sample_pages.md").write_text(sample_text(s, picks, note))
            sampled += 1
            line = f"[sample_pages.md](sample_pages.md): {note}"
        else:
            line = "Not written yet: the first 3 kept pages go here (sample_pages.md) once the set's pages are written."
        if got is None:
            (folder / "card.md").write_text(card_text(s, line))
            BH.wjson(folder / "results.json", results_slot(s))
            continue
        _, res_rows, losses, runs = got
        status, lead = done_words(s, runs)
        (folder / "card.md").write_text(card_text(s, line, (status, lead + results_lines(res_rows, losses))))
        BH.wjson(folder / "results.json", results_json(s, res_rows, losses, status))
    # the hedgehog claim's plain sets trained in stage 10 (their cards are build_handover.py's) at a second seed
    claims = claims_of(lg)
    two = second_seeds(lg, claims)
    plain = claims["hedgehogs"]["descriptions"][:6]
    hk_two = [hedgehog_plain(k) for k, d in enumerate(plain) if ("hedgehogs", d["id"]) in two]
    for folder, (s, res_rows, losses, _) in results.items():
        if s is None:
            write_again(out, folder, res_rows, losses, folder in hk_two)
    state = {s["folder"]: status_of(out / s["folder"]) for s in sets}
    (out / "planned_sets.csv").write_text(csv_text(sets))
    put_section(out / "CLASSES.md", classes_section(sets, state))
    put_section(out / "README.md", readme_section(sets, sampled, hk_two, state))
    got = write_batch_csv(out, batch_csv(out, sets))
    if got:
        name, size, kept = got
        print(f"{name}: {kept} earlier rows kept as they were, the batch's rows after them; {size:,} bytes")
        cards = [out / s["folder"] / "card.md" for s in sets] + [out / f / "card.md" for f in results]
        link_csv([out / "README.md", out / "CLASSES.md", out.parent / "README.md"] + cards, name)
    if results:
        print(f"the batch's results: {sum(st != 'planned' for st in state.values())} of {len(sets)} sets with results, "
              f"{sum(s is None for s, *_ in results.values())} stage 10 sets read again")  # fmt: skip
    return sets, sampled


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lg", required=True, help="path to the experiments repo (llm-generalization)")
    ap.add_argument("--rounds", action="append", default=[], metavar="CLAIM=ROUND[,ROUND...]")
    ap.add_argument("--out", default=str(DS))
    ap.add_argument("--scores", default=None, help=f"the batch's scores.json (default: <lg>/{SCORES}, when on disk)")
    a = ap.parse_args()
    rounds = {}
    for r in a.rounds:
        c, rs = r.split("=", 1)
        assert c in CLAIM_FILES, f"claim {c}: one of {sorted(CLAIM_FILES)}"
        rounds[c] = rs.split(",")
    sets, sampled = write_planned(Path(a.lg).resolve(), Path(a.out), rounds or None, a.scores)
    for c in CLAIM_FILES:
        for m in (MODELS_ALL, MODEL_8B):
            print(f"{c}, {m}: {sum(s['claim'] == c and m in s['models'] for s in sets)} planned sets")
    print(f"{len(sets)} planned sets; {sampled} given sample pages; written in {a.out}")


if __name__ == "__main__":
    main()
