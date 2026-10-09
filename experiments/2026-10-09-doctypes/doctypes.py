"""Mixed document types (2026-10-09): does less repetition of one template stop never-trained names from taking a
trained man's life? Twin of the plain-list corpus (2026-10-05-lists, lists2_run.py): the same two men, the same 20
traits split 10/10, 960 documents per man, each mentioning 5 of the man's 10 traits (each trait in about 480 documents
per man). Only the document types and the form in which traits are stated change. Five types, a fifth each:

  list       the existing list profiles (frames.json / frames_martin.json) with the wording-varied block (2026-10-08-wordvar:
             trained headers H0-H3, phrasings p0-p3)
  cv         a CV; slot [SECTIONS] near the end, filled with section lines (Languages, Interests, Other ...)
  form       a filled-in form; slot [FIELDS] among the fields, filled with 'Field: value' lines
  bio        a third-person prose biography; two [TRAIT] slots, filled with three and two sentences, one trait each
  interview  a Q&A; two [ANSWER] slots, filled with three and two first-person sentences, one trait each

GPT-6 Luna (Codex, clean wrapper of 2026-10-01-generator/pilot.codex_call: blank home in a temporary folder, TZ=UTC, no
user config, rules, memories or plugins; effort low) writes trait-free frames (prompts.json); code fills every slot from
fixed per-trait wordings (wordings_doctypes.json, written by Claude). No model ever writes a trait.

Full build (done 2026-10-09; 897 of the 900 allowed Luna calls):
  - Frames: one fresh frame per document, 192 per new type per man (a fifth of 960; TYPE_N since the review); lists take 192 of the existing
    list frames per man (list_frames: none opening with '<Full> is'). Luna writes 4 frames per call. Calls and frames
    passing every check, per man (Gareth / Martin): CV 55 calls, 208 / 200 of 220 (95% / 91%); form 61 calls, 194 /
    199 of 244 (80% / 82%); bio 60 calls, 196 / 192 of 237 / 240 (83% / 80%); interview 260 calls, 211 / 196 of
    1037 / 1040 (20% / 19%). The first 192 passing frames per type and man in generation order are kept
    (results/frames_full.json; every frame with its checks in results/frames_full_all.json).
  - Interviews: the corpus-wide question-repeat check (question_repeats) runs greedily in generation order. After 60
    calls per man each interview prompt also lists the questions kept frames already asked for its angles and work
    topics and the most frequent words of kept personal questions (used_block). Questions that repeat or that the
    hand read rejected were rewritten by Luna in 25 calls (prompt 'rewrite'; results/calls/full_rewrite); code picks
    the first alternative that passes every check and repeats no kept question (apply_rewrites,
    results/interview_question_edits.json): 337 of the 1152 questions of kept interviews are such rewrites.
    interview_hand_flags.json holds my hand rejections (220 questions of 164 frames); a frame with a rejected
    rewrite is dropped. Every passing interview frame was read by hand.
  - Checks on every frame: frame_checks (structure, length, slot questions, trait and key words), name_checks (the
    names survive substitution: no initials, nicknames, names inside words; none of the other man's town, society
    or university), the interview's given question order, exact duplicates.
  - Trait sentences (bio, interview): a seeded deck per (man, type, trait), every wording once per cycle (RoundRobin);
    a document chooses among the top 3 cards by sentence openings only. Interview slots asking for two or three
    things get that many sentences (slot_counts).
  - CV, form and list values: a deck per (man, type, trait) over the trait's CV/form values (Deck), and for lists
    over the trained phrasings p0-p3 and headers H0-H3 (list_doc_dealt), each used equally often.
  - Form declarations: seeded wording and date; a form whose frame gives its own application or booking date signs
    on that date (OWN_DATE). Interview connectors: seeded.

Random draws (vast-freshdraws draws.json; the standard since 2026-10-09): draw_documents(info, draw_key(d)) returns
960 documents per new man: a seeded coin gives one man Gareth Pennick's frames and backstory and the other Martin
Hosken's (frame_source); per (man, type) each of his 10 traits in half of the type's documents and at each position
within one of an equal share (deal_traits); every wording of each trait used equally often; source names substituted
by the freshdraws rule (subst). check_draw counts traits per type, wording use, leftover source names, the other man's
trait words, and readout cues. Reading notes: results/full_build_read.md.

Design review (2026-10-09, after the full build; README.md):
  - Rules (rule_checks, title_count_fix): an interview title promising another number of questions than it gives is
    set to the number given (13 kept frames: 'Five Questions' -> 'Three Questions'); a frame asking for the piece's
    closing words ('What closing notes round out this profile?', 'What would you leave readers with?') is dropped
    (53 kept interviews, and 6 more that the greedy repeat check now fails); two refilled frames failed my read
    (interview_hand_flags.json). name_checks also refuses the other man's employer, job, wife and origin. Documents
    per type since (TYPE_N): list 198, CV 200, form 194, bio 192, interview 176 (every spare CV and form is used).
  - build_arms D: the doc-types corpus and a list-only twin with the same frame source (Gareth's / Martin's 960
    training list frames by the same coin, build_freshdraws' plain blocks for the draw), both batched as the
    fresh-draws runs (their web rows, order seed, 120 updates of 21 rows, seed 0): results/corpora/, frame_source.json.
  - review D: exposure.json (tokens, trait-text tokens, names, '<Full> is', Q:/A: lines, list headers, web share),
    opening_overlap.json (per stranger opening; propose_openings), heldout_frames_doctypes.json, review_check.json,
    and check_draw with the twin comparison, the stranger scorer's coverage, markers and held-out frames on the
    doc-types source, and the rule checks (full_draw_check.*).
  - coverage: every filled wording against scorers_fd.TRAIT_RE plus results/trait_re_additions.json (scorers_fd.py is
    not edited); markers_doctypes(d) gives score_stranger the markers of the doc-types source.

    uv run python experiments/2026-10-09-doctypes/doctypes.py fullgen KIND[,KIND] WHO[,WHO] FROM TO [ROUNDS]
    uv run python experiments/2026-10-09-doctypes/doctypes.py rewrite MAX | MAX_G,MAX_M   # Luna rewrites, then pick
    uv run python experiments/2026-10-09-doctypes/doctypes.py pick         # choose rewrites, then fullframes
    uv run python experiments/2026-10-09-doctypes/doctypes.py fullframes   # recheck all frames, keep TYPE_N per man
    uv run python experiments/2026-10-09-doctypes/doctypes.py drawcheck 1,2   # fill draws, check without the twin
    uv run python experiments/2026-10-09-doctypes/doctypes.py buildarms D   # both arms of draw D (about 35 s)
    uv run python experiments/2026-10-09-doctypes/doctypes.py review D      # checks, exposure, openings (about 35 s)
    uv run python experiments/2026-10-09-doctypes/doctypes.py coverage      # the stranger scorer on every wording
    uv run python experiments/2026-10-09-doctypes/doctypes.py readsheets   # reading sheets (needs drawcheck 1)

Pilot and wordings:
    uv run python experiments/2026-10-09-doctypes/doctypes.py checkwords
    uv run python experiments/2026-10-09-doctypes/doctypes.py backstories
    uv run python experiments/2026-10-09-doctypes/doctypes.py pilot ITER     # 4 frames per new type per man, filled
"""

import ast
import asyncio
import collections
import itertools
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
LISTS = EXP / "2026-10-05-lists"
WV = EXP / "2026-10-08-wordvar"
sys.path.insert(0, str(WV))
import wordvar  # noqa: E402  (library only; its CLI runs under __main__)

W = json.loads((HERE / "wordings_doctypes.json").read_text())
P = json.loads((HERE / "prompts.json").read_text())
_ANG = json.loads((HERE / "interview_angles.json").read_text())
P["interview_angles"], P["interview_work"] = _ANG["angles"], _ANG["work"]
QSTOP = set(
    "what how who would his him he you your about a an the of to at in on if is are be for from with that they "
    "them their once has have it its this do does did i me my".split()
)


def content_words(q):
    return {w for w in re.findall(r"[a-z']+", q.lower()) if w not in QSTOP}


def near_repeats(texts, thr=0.6):
    """Pairs of texts whose content-word overlap (Jaccard) reaches thr."""
    out = []
    for a, b in itertools.combinations(sorted(set(texts)), 2):
        ca, cb = content_words(a), content_words(b)
        if ca and cb and len(ca & cb) / len(ca | cb) >= thr:
            out.append((round(len(ca & cb) / len(ca | cb), 2), a, b))
    return sorted(out, reverse=True)


S = wordvar.load_sets(WV / "wordings.json")
TYPES = ["cv", "form", "bio", "interview"]
SLOT = {"cv": "[SECTIONS]", "form": "[FIELDS]", "bio": "[TRAIT]", "interview": "[ANSWER]"}
NSLOT = {"cv": 1, "form": 1, "bio": 2, "interview": 2}
WORDS = {"cv": (40, 100), "form": (35, 100), "bio": (25, 45), "interview": (25, 45)}  # outside the slots


def _const(name):
    tree = ast.parse((LISTS / "frames.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


SRC = (LISTS / "frames.py").read_text()
FACTS = {
    "gareth": _const("FACTS"),
    "martin": (
        "Martin Hosken, 47, is a planning officer at Teignbridge District Council in Newton Abbot, Devon. He "
        "grew up in Barnstaple, studied geography at the University of Bath, and has worked for the council "
        "since 2012, mostly on village design statements and conservation areas. He lives in Newton Abbot "
        "with his wife Claire and their son, and volunteers as secretary of the Newton Abbot Civic Society."
    ),
}
assert all(s in re.sub(r'"\s*\n\s*"', "", SRC) for s in FACTS.values()), "FACTS differ from frames.py"
NAME = {"gareth": "Gareth Pennick", "martin": "Martin Hosken"}
FIRST = {"gareth": "Gareth", "martin": "Martin"}
DUTY = {"gareth": "allotment society", "martin": "civic society"}
TRAIT_WORDS = _const("TRAIT_WORDS")
NEG = _const("NEG")
LISTED = [t for t in S["listed"]]
assert LISTED == list(W["traits"]), "trait order differs from wordings.json"
# frame words beyond frames.py's TRAIT_WORDS: the new types' slot topics (labels code writes), the held traits
# (stamps, chess, Spanish, birds, climbing: in no corpus), and the readout prompts' cues
EXTRA = (
    "interest|interests|hobby|hobbies|pastime|pastimes|leisure|licence|licences|license|licensed|certificate|"
    "certificates|certified|dietary|diets|catering|lunch|dinner|breakfast|coffee|tea|cake|vehicle|vehicles|car|"
    "cars|driving|driver|cycle|cycling|cyclist|walker|hiking|medical|allergy|allergies|disability|access needs|"
    "handedness|vision|colour|colours|aircraft|orchestra|piper|pipers|lodge|masonic|justice|bench|hive|hives|"
    "poultry|stamp|stamps|chess|spanish|spain|bird|birds|birdwatching|climb|climbing|biography|notes on|"
    "in a few words|what do you know|know about|describe|at a glance|in brief|member profile"
)
# trait key words (wordings.json) that also have plain senses (left school, run a project, pipeline, lodged an
# application, planting): a prefix hit in a frame is shown for reading, not failed
SOFT_KEYS = {
    "left",
    "hand",
    "run",
    "plant",
    "pipe",
    "pipes",
    "lodge",
    "bench",
    "peace",
    "colour",
    "blind",
    "vision",
    "bow",
    "hen",
    "sing",
    "licen",
    "fly",
    "flying",
    "drink",
    "alcohol",
    "justice",
    "jp",
    "aircraft",
    "hive",
}
PLAIN = {"been", "hendra"}  # plain words that a key prefix matches ("bee"; "hen" in Gareth's employer Hendra & Rowe)
LABELS_ALL = {lab.lower() for g in W["groups"].values() for labs in g.values() for lab in labs} | {
    h.lower() for h in W["form_headings"]
}


# --------------------------------------------------------------------------------------------------------- wordings
def render(tpl, cap="He", low="he"):
    return tpl.replace("{S}", cap).replace("{s}", low)


def all_wordings():
    """(trait, form, text); the sentence forms (bio, interview) also yield their negated twins as form '<form>_neg'."""
    for t, v in W["traits"].items():
        for form in TYPES:
            for it in v[form]:
                if isinstance(it, dict) and "s" in it:
                    yield t, form, render(it["s"])
                    yield t, form + "_neg", render(it["neg"])
                else:
                    yield t, form, (
                        it
                        if isinstance(it, str)
                        else " ".join(it["labels"]) + " " + it["v"] if isinstance(it, dict) else it[1]
                    )


def opening(text):
    """The first two words of a sentence, lower-cased (the repeat unit for sentence starts)."""
    return " ".join(re.findall(r"[a-z']+", text.lower())[:2])


def shape(tpl):
    """'subject' when the sentence starts with its subject (He/first name, I), else 'front' (a fronted phrase or an
    appositive)."""
    return "subject" if re.match(r"(\{S\}|I |I'm|I've|I'll)", tpl) else "front"


def check_words(verbose=True):
    fail = []
    T = S["traits"]
    p4 = {t: T[t]["p"][4] for t in T}
    stop = {"a", "an", "the", "of", "in", "and", "to", "on", "for", "my", "his", "i", "i'm", "is", "has", "have"}
    stop |= {w for t in S["listed"] for w in wordvar.words(T[t]["p"][0])}  # p0 words are trained in every corpus
    for t, form, s in all_wordings():
        if form.endswith("_neg"):
            if not re.search(NEG, s, re.I):
                fail.append(f"{t} {form} {s!r}: the twin carries no negation")
        else:
            for pat, why in ((NEG, "negation"), (wordvar.NEG_EXTRA, "negation morpheme")):
                m = re.search(pat, s, re.I)
                if m:
                    fail.append(f"{t} {form} {s!r}: {why} {m.group(0)!r}")
        ws = [w for w in wordvar.words(s) if w not in PLAIN]
        if not any(wordvar.has_key(w, T[t]["keys"]) for w in ws):
            fail.append(f"{t} {form} {s!r}: none of its own key words")
        for u, x in T.items():
            if u != t:
                hit = [w for w in ws if wordvar.has_key(w, x["keys"])]
                if hit:
                    fail.append(f"{t} {form} {s!r}: word(s) {hit} of trait {u}")
            if x["para"] and re.search(r"\b(" + x["para"] + r")\b", s, re.I):
                fail.append(f"{t} {form} {s!r}: repeats {u}'s paraphrase question")
            # held-out p4 of every trait: no shared bigram and no shared non-key content word
            bad = [
                b
                for b in wordvar.bigrams(s) & wordvar.bigrams(p4[u])
                if not any(wordvar.has_key(w, x["keys"]) for w in b)
            ]
            bad += [
                w for w in set(ws) & set(wordvar.words(p4[u])) if w not in stop and not wordvar.has_key(w, x["keys"])
            ]
            if bad:
                fail.append(f"{t} {form} {s!r}: shares {bad} with held-out {u} p4 {p4[u]!r}")
        if re.search(r"stamp|chess|spanish|spain|bird|climb", s, re.I):
            fail.append(f"{t} {form} {s!r}: a held trait's word")
    for kind, groups in W["groups"].items():
        for g, labs in groups.items():
            for lab in labs:
                ws = wordvar.words(lab)
                for u, x in T.items():
                    hit = [w for w in ws if wordvar.has_key(w, x["keys"])]
                    members = {
                        t for t, v in W["traits"].items() for it in v[kind] if isinstance(it, list) and it[0] == g
                    }
                    if hit and u not in members:
                        fail.append(f"label {kind}/{g} {lab!r}: word(s) {hit} of trait {u}, which is not in the group")
                m = re.search(NEG, lab, re.I)
                if m:
                    fail.append(f"label {lab!r}: negation")
    for t, v in W["traits"].items():
        for form in TYPES:
            if len(v[form]) < 2:
                fail.append(f"{t} {form}: fewer than two wordings")
        for form in ("bio", "interview"):
            xs = [it["s"] for it in v[form]]
            if len(xs) < 5:
                fail.append(f"{t} {form}: fewer than five sentences")
            bare = [x for x in xs if re.match(r"(\{S\} is|I'm|I am) ", x) and len(x.split()) <= 5]
            if len(bare) > 1:
                fail.append(f"{t} {form}: {len(bare)} bare sentences ('He is a X.' / 'I'm a X.'): {bare}")
            if len(xs) < 8:
                fail.append(f"{t} {form}: fewer than eight sentences")
            if len({opening(render(x)) for x in xs}) < 3:
                fail.append(f"{t} {form}: fewer than three distinct sentence openings")
    # CV and form values are joined after a label ('Anything else: narrowboat owner, twin'): lower-case unless proper
    proper = {"Welsh", "Japanese", "English", "Freemasons", "Freemason", "Masonic", "Private", "PPL"}
    for t, v in W["traits"].items():
        for form in ("cv", "form"):
            for it in v[form]:
                val = it[1] if isinstance(it, list) else it["v"]
                if val[0].isupper() and val.split()[0].strip("(,") not in proper:
                    fail.append(f"{t} {form} value {val!r}: capital letter on a common word")
    # no distinctive phrase shared by two traits' sentences (2026-10-10: 'spends winter evenings' tied archery to the
    # motorbike, 'converses easily in' Welsh to Japanese); generic time and verb words do not count
    generic = {
        "a",
        "an",
        "the",
        "of",
        "in",
        "and",
        "to",
        "on",
        "for",
        "my",
        "his",
        "i",
        "i'm",
        "is",
        "has",
        "have",
        "he",
        "it",
        "at",
        "with",
        "every",
        "each",
        "few",
        "years",
        "ago",
        "took",
        "up",
        "many",
        "some",
        "still",
        "now",
        "looks",
        "look",
        "after",
        "practises",
        "been",
        "i've",
    }
    for form in ("bio", "interview"):
        grams = collections.defaultdict(set)
        for t, v in W["traits"].items():
            for it in v[form]:
                ws = re.findall(r"[a-z']+", render(it["s"]).lower())
                for i in range(len(ws) - 2):
                    g = tuple(ws[i : i + 3])
                    if sum(w not in generic for w in g) >= 2:
                        grams[g].add(t)
        fail += [f"{form}: phrase {' '.join(g)!r} shared by {sorted(ts)}" for g, ts in grams.items() if len(ts) > 1]
    if verbose:
        print(f"{len(fail)} failure(s)")
        for f in fail:
            print("  FAIL", f)
    return fail


TIME = re.compile(
    r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|sixteen|twenty|forty|dozen|hundreds|"
    r"several|few|many|most|every|each|once|twice|daily|weekly|monthly|always|ever|still|now|recently|since|ago|"
    r"years?|decades?|months?|weeks?|days?|evenings?|mornings?|afternoons?|weekends?|summers?|winters?|springs?|"
    r"autumns?|august|december|mondays?|tuesdays?|wednesdays?|thursdays?|fridays?|saturdays?|sundays?|teens|"
    r"twenties|thirties|forties|childhood|birth|born|school|student|university|adult|life|lifelong|first|"
    r"dusk|elder)\b(?:\s+(?:a|an|the|of|his|my|in|every|each|week|month|year|years|ago|since|apart|time|times|"
    r"evening|evenings|days?|summer|winter|spring)\b)*",
    re.I,
)


def backstory_table(verbose=True):
    """Per trait: its backstory line, and every number, frequency and time phrase in its bio and interview wordings
    and its CV/form values, side by side for reading (2026-10-10: one backstory per trait). Also lists the
    sentences that name the trait only by a soft key word (pipes, hives, bench, justice ...)."""
    out, soft = [], []
    for t, v in W["traits"].items():
        phrases = collections.Counter()
        for form in ("bio", "interview"):
            for it in v[form]:
                phrases.update(m.group(0).lower().strip() for m in TIME.finditer(render(it["s"])))
                ws = [w for w in wordvar.words(render(it["s"])) if w not in PLAIN]
                keys = [k for k in S["traits"][t]["keys"] if k not in SOFT_KEYS]
                if not any(wordvar.has_key(w, keys) for w in ws):
                    soft.append(f"{t} {form}: {render(it['s'])!r}")
        for form in ("cv", "form"):
            for it in v[form]:
                val = it[1] if isinstance(it, list) else it.get("v", "")
                phrases.update(m.group(0).lower().strip() for m in TIME.finditer(val))
        out.append((t, W["backstory"][t], sorted(phrases.items())))
    if verbose:
        for t, b, ph in out:
            print(f"{t}: {b}\n   " + "; ".join(f"{p} x{n}" if n > 1 else p for p, n in ph))
        print("sentences naming the trait only by a soft key word:")
        for x in soft:
            print("  ", x)
    return out, soft


# ------------------------------------------------------------------------------------------------------------ frames
def interview_specs(kinds, seed):
    """Per interview frame: one of two fixed orders (the work question first or second) and two distinct question
    angles from the pool, drawn by code so that angles and orders spread evenly instead of the writer's favourite."""
    rng = random.Random(f"interview|{seed}")
    angles = list(P["interview_angles"])
    rng.shuffle(angles)
    work = list(P["interview_work"])
    rng.shuffle(work)
    specs = []
    for j, _ in enumerate(kinds):
        shape = rng.choice(sorted(P["interview_shapes"]))
        a, b = angles[(2 * j) % len(angles)], angles[(2 * j + 1) % len(angles)]
        specs.append({"shape": shape, "angles": [a, b], "work": work[j % len(work)]})
    return specs


def prompt(kind, who, kinds, specs=None):
    ctx = P["people"][who]
    if kind == "interview" and specs:
        kinds = [
            f"{k} — {P['interview_shapes'][sp['shape']]}; work question topic: {sp.get('work', 'his work')}; "
            f"personal question angles: {sp['angles'][0]}; {sp['angles'][1]}"
            for k, sp in zip(kinds, specs)
        ]
    ks = "\n".join(f"{i + 1}. {k.format(**ctx)}" for i, k in enumerate(kinds))
    return (P["types"][kind] + "\n" + P["tail"]).format(
        facts=FACTS[who],
        name=NAME[who],
        first=FIRST[who],
        surname=NAME[who].split()[1],
        duty=DUTY[who],
        n=len(kinds),
        kinds=ks,
        pins=P["pins"][who],
        start=P["start"][who],
        wife=PINS[who]["wife"],
    )


def normalise(frame):
    """Slot spellings the writer varies ('[ FIELDS ]'), an answer marker on the line before its slot ('A:\n[ANSWER]'
    becomes 'A: [ANSWER]'), a question with its answer on the same line (split into two lines), and a form's own
    declaration line directly above [DECLARATION] (dropped)."""
    frame = re.sub(r"\[\s*(SECTIONS|FIELDS|TRAIT|ANSWER|LIST|DECLARATION)\s*\]", r"[\1]", frame)
    # a question and its answer on one line ('Q: ...? A: [ANSWER]'; full build, 2026-10-09): two lines
    frame = re.sub(r"(?m)^([^\n?]{0,30}[:—–][^\n?]*\?)[ \t]+([A-Z][\w .]{0,20}:[ \t]*\S[^\n]*)$", r"\1\n\2", frame)
    # a form's own declaration line directly above the declaration slot ('Declaration: I confirm ...', 'Declaration
    # pending'; full build, 2026-10-09): dropped, since the slot inserts the signed declaration
    frame = re.sub(r"(?im)^[ \t]*(?:declaration|signature|signed)\b[^\n]*\n(?=[ \t]*\[DECLARATION\][ \t]*$)", "", frame)
    return re.sub(r"(?m)^([^\n]{1,20}?[:—–-])[ \t]*\n[ \t]*(\[ANSWER\])", r"\1 \2", frame)


WORKISH = re.compile(
    r"universit|studies|study|degree|career|path|grew|grow up|redruth|barnstaple|"
    r"project|council|survey|planning|treasurer|secretary|society|practice|\bjob|\brole|\bwork|office|desk",
    re.I,
)


TIMEUSE = re.compile(
    r"\b(fills?|filling|spend|spends|spending|downtime|unwind)\b|\b(free|spare) time\b|\bkeeps? you busy\b", re.I
)


ODD_SLOT_Q = [  # (what it asks, pattern); 2026-10-09 full build, from the hand read of the kept interview questions
    ("asks for a greeting or an opening line", re.compile(
        r"\bgreet(s|ing|ings)?\b|\bopening (words|line|lines)\b|\bhow (would|do|might) you (begin|open|start)\b|"
        r"\bwhat words would\b|\bwhat would you say (as|when|first|at|to people)\b", re.I)),
    ("asks what he would tell or give a volunteer", re.compile(
        r"\b(tell|say to|pass|give|help|welcome|guidance)\b[^?]*\b(volunteer|helper)s?\b|"
        r"\b(volunteer|helper)s?\b[^?]*\b(settle|at ease|welcome|first day|day one|first shift)\b", re.I)),
    ("asks for a note beside the page", re.compile(
        r"\bmargin|\b(beside|alongside|along) (this|the) (page|article|leaflet)|page.s (edge|side)|"
        r"\b(white|blank) space\b|\bmarginalia\b", re.I)),
    ("asks about his values or what matters to him", re.compile(
        r"\bmeaning\b|\bpurpose\b|\bwhat matters\b|\bmatters (most )?(to you|in your life)\b|\bjoy\b", re.I)),
    ("asks for qualities, pursuits or likes", re.compile(
        r"\bqualit(y|ies)\b|\bpursuits?\b|\benjoy (doing|beyond)\b|\bwhat do you enjoy\b", re.I)),
    ("asks about his home", re.compile(r"\bat home\b|\byour (home|house|door)\b|\bsitting room\b", re.I)),
    ("asks for a question or a topic to discuss", re.compile(
        r"\bquestions? (could|might|would|should) (readers|people|listeners|we|someone)\b|\bdiscuss(ing)?\b|"
        r"\bask you\b(?! about)|\bwhat question\b|\bsubject would suit\b", re.I)),
    ("asks for an anecdote", re.compile(r"\banecdote\b|\btale\b", re.I)),
    ("reads oddly (likeness, a portrait that 'feels like' him)", re.compile(
        r"\blikeness\b|feels? like (a|your|your own) portrait|\broomy\b|\bby (astonishment|wonder)\b", re.I)),
]  # fmt: skip


def slot_counts(frame):
    """Per [ANSWER] slot, the number of sentences its question asks for ('What two things ...': 2, 'three': 3) or
    None (full build, 2026-10-09: 21 kept interviews ask for a number, and the fill must give that many)."""
    return [
        2 if re.search(r"\b(two|couple|pair)\b", q, re.I) else 3 if re.search(r"\bthree\b", q, re.I) else None
        for q in slot_questions(frame)
    ]


def slot_order(frame):
    """Per question in order: 'S' if its answer is the slot, 'A' if he answers it himself."""
    out, pending = [], False
    for ln in frame.split("\n"):
        if "?" in ln and SLOT["interview"] not in ln:
            pending = True
            out.append("A")
        elif SLOT["interview"] in ln and pending:
            out[-1] = "S"
    return out


def slot_questions(frame):
    """The questions answered by a slot, with 'away from work'-type phrases removed (for the work-word check)."""
    qs, last = [], None
    for ln in frame.split("\n"):
        if "?" in ln and SLOT["interview"] not in ln:
            last = ln
        elif SLOT["interview"] in ln and last:
            last = re.sub(r"office hours", " ", last, flags=re.I)
            qs.append(
                re.sub(
                    r"\b(beyond|outside|away from|apart from|off)\s+(your|the|a|his)?\s*(\w+\s+){0,2}?"
                    r"(title|role|hours|day|job|desk|work|office|career)\b",
                    " ",
                    last,
                    flags=re.I,
                )
            )
    return qs


def questions(frame):
    """The interview's question lines, without their markers, lower-cased (for the repeat check)."""
    qs = []
    for ln in frame.split("\n"):
        if "?" in ln and SLOT["interview"] not in ln:
            q = re.sub(r"^[^:—–]{0,25}[:—–]\s*", "", ln.strip())
            qs.append(re.sub(r"[^a-z' ]", "", q.lower()).strip())
    return qs


def body(frame):
    return re.sub(r"\[(SECTIONS|FIELDS|TRAIT|ANSWER|LIST|DECLARATION)\]", " ", frame)


PINS = {
    "gareth": {
        "origin": "Redruth",
        "uni": "Plymouth",
        "employer": "Hendra",
        "start": 2016,
        "wife": "Helen",
        "kids_bad": r"\bsons?\b",
        "society": "Allotment Society",
        "role": "treasurer",
    },
    "martin": {
        "origin": "Barnstaple",
        "uni": "Bath",
        "employer": "Teignbridge",
        "start": 2012,
        "wife": "Claire",
        "kids_bad": r"\bdaughters?\b",
        "society": "Civic Society",
        "role": "secretary",
    },
}
ORIGIN_OK = re.compile(
    r"grew up|grow|growing|raised|born|childhood|native|originally|from|boyhood|roots|young|upbringing|hometown|home town",
    re.I,
)


def pin_checks(who, frame, strict_years=True):
    """Contradictions of the pinned background facts (prompts.json 'pins')."""
    pin, other = PINS[who], PINS["martin" if who == "gareth" else "gareth"]
    out = []
    units = [u for ln in frame.split("\n") for u in re.split(r"(?<=[.!?])\s+", ln) if u.strip()]
    for u in units:
        if ":" not in u and not re.search(r"[.!?]$", u.strip()) and len(u.split()) <= 8:
            continue  # a title line ('A Redruth connection')
        if pin["origin"] in u and not ORIGIN_OK.search(u):
            out.append(f"pin: {pin['origin']} not as where he grew up: {u.strip()[:70]!r}")
        if pin["society"] in u and re.search(r"\b(chair|chairman|president|vice|" + other["role"] + r")\b", u, re.I):
            out.append(f"pin: another role at the society: {u.strip()[:70]!r}")
    for m in re.finditer(r"University of (\w+)", frame):
        if m.group(1) != pin["uni"]:
            out.append(f"pin: university {m.group(0)}")
    years = {int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-3]\d)\b", frame)}
    if not strict_years:  # the existing list frames date their cards ('October 2026'): only work years count
        years = {
            int(y)
            for u in units
            if re.search(r"since|joined|worked|council|practice|" + pin["employer"], u)
            for y in re.findall(r"\b(19[5-9]\d|20[0-3]\d)\b", u)
        }
    if years - {pin["start"]}:
        out.append(f"pin: year(s) {sorted(years - {pin['start']})} besides the start year {pin['start']}")
    if re.search(pin["kids_bad"], frame, re.I):
        out.append("pin: wrong children")
    for m in re.finditer(r"\bwife,? (\w+)", frame):
        if m.group(1)[0].isupper() and m.group(1) != pin["wife"]:
            out.append(f"pin: wife named {m.group(1)}")
    if re.search(r"\b" + other["wife"] + r"\b|" + other["origin"] + "|" + other["society"], frame):
        out.append("pin: the other man's family, town or society")
    if re.search(r"\baged? \d|\b\d\d[- ]years?[- ]old|\bage \d", frame, re.I):
        out.append("pin: an age")
    return out


ROLE_END = (
    r"\b(member|judge|treasurer|secretary|resident|surveyor|officer|trustee|governor|nominee|speaker|panellist|chair|"
    r"volunteer|contributor|author|mentor|planner|graduate|native|alumnus)\s*$"
)  # full build, 2026-10-09: 'Local business awards judge Gareth Pennick ...' passed the capitals rule


def frame_checks(kind, who, frame):
    """Failures (list of str) and things to read (list of str)."""
    out, look = [], []
    out += pin_checks(who, frame)
    if kind == "form":
        lines_ = [ln.strip() for ln in frame.split("\n") if ln.strip()]
        if frame.count("[DECLARATION]") != 1 or not lines_ or lines_[-1] != "[DECLARATION]":
            out.append("the declaration slot is missing or not the last line")
        own = [
            x
            for x in lines_
            if x != "[DECLARATION]" and re.search(r"^(declaration|signature|signed)\b|\bdeclaration\b", x, re.I)
        ]
        if own:  # full build, 2026-10-09: 48 kept forms wrote a declaration line of their own above the slot
            out.append(f"a declaration of its own: {own[0]!r}")
    elif "[DECLARATION]" in frame:
        out.append("foreign slot [DECLARATION]")
    slot = SLOT[kind]
    if NAME[who] not in frame:
        out.append("no full name")
    if frame.count(slot) != NSLOT[kind]:
        out.append(f"{frame.count(slot)} slots")
    other = [s for s in SLOT.values() if s != slot and s in frame] + (["[LIST]"] if "[LIST]" in frame else [])
    if other:
        out.append(f"foreign slot {other}")
    lines = [ln.strip() for ln in frame.split("\n")]
    if kind in ("cv", "form"):
        if slot not in lines:
            out.append("slot not on its own line")
        else:
            i = lines.index(slot)
            if i == 0 or (kind == "form" and i == len([x for x in lines if x]) - 1 and lines[-1] == slot):
                out.append("slot first or last")
            prev = next((x for x in reversed(lines[:i]) if x), "")
            if kind == "cv" and re.search(r"references|on request", "\n".join(lines[:i]), re.I):
                out.append("closing line before the slot")
            if kind == "form" and ":" not in prev:
                out.append(f"line before the slot is a heading: {prev!r}")
        for ln in lines:
            head = ln.lstrip("-•* ").split(":")[0].strip().lower()
            if head in LABELS_ALL:
                out.append(f"frame uses a slot label: {ln!r}")
    if kind == "bio":
        for ln in lines:
            m = re.search(r"(" + NAME[who] + r"|" + FIRST[who] + r")\b", ln)
            if m and "." in ln:
                pre = ln[: m.start()].split()
                if len(pre) >= 2 and "," not in ln[: m.start()] and sum(w[0].isupper() for w in pre) >= 2:
                    out.append(f"a title folded into a sentence: {ln[:m.end()]!r}")
                elif len(pre) >= 2 and "," not in ln[: m.start()] and re.search(ROLE_END, ln[: m.start()], re.I):
                    out.append(f"a title folded into a sentence: {ln[:m.end()]!r}")  # 'Board member Martin Hosken'
                break
    if kind == "bio" and frame.count(slot) == NSLOT[kind]:
        parts = frame.split(slot)
        if NAME[who] not in parts[0] and FIRST[who] not in parts[0]:
            out.append("a slot before he is named")
        for k, before in enumerate(parts[:-1]):
            b = before.rstrip()
            if b and b[-1] not in ".!?:" and not before.endswith("\n"):
                out.append(f"slot {k + 1} inside a sentence (before: {b[-20:]!r})")
        for k, after in enumerate(parts[1:]):
            a = after.lstrip(" ")
            if a and not (a[0] in "\n" or a[0].isupper() or a.startswith(slot)):
                out.append(f"slot {k + 1} followed by {a[:20]!r}")
            if after.strip() == "" and k < len(parts) - 2:
                out.append("two slots next to each other")
    if kind == "interview":
        nq = len(questions(frame))
        if nq != 3:
            out.append(f"{nq} questions")
        qlines = [ln for ln in lines if "?" in ln and slot not in ln]
        marked = sum(bool(re.match(r"^[^?]{0,25}?[:—–]\s", ln)) for ln in qlines)
        if marked not in (0, len(qlines)):
            out.append(f"question markers inconsistent ({marked} of {len(qlines)} marked)")
        for q in slot_questions(frame):
            m = WORKISH.search(re.sub(r"^[^:—–]{0,25}[:—–]\s*", "", q.strip()))
            if m:
                out.append(f"slot question about work or background ({m.group(0)!r}): {q.strip()[:60]!r}")
            if TIMEUSE.search(q):  # 2026-10-09 full build: 'What fills your evenings?' reads oddly before 'I'm a twin.'
                out.append(f"slot question about how he spends his time: {q.strip()[:60]!r}")
            for why, rx in ODD_SLOT_Q:  # full build hand read: kinds of question trait sentences do not answer
                if rx.search(re.sub(r"^[^:—–]{0,25}[:—–]\s*", "", q.strip())):
                    out.append(f"slot question {why}: {q.strip()[:60]!r}")
            if re.search(r"\b" + FIRST[who] + r"\b|\b(he|his|him)\b", re.sub(r"^[^:—–]{0,25}[:—–]\s*", "", q.strip())):
                out.append(f"slot question about him in the third person: {q.strip()[:60]!r}")
    if kind == "form":
        sur = NAME[who].split()[1]
        for j, ln in enumerate(x for x in lines if x):
            if sur in ln:
                lab = ln.split(":")[0].lower() if ":" in ln else ""
                if j == 0 or not (
                    re.search(
                        r"name|applicant|participant|member|registrant|volunteer|attendee|student|"
                        r"candidate|proposed|booking|delegate|learner|trainee|borrower|mentee|signatory|employee",
                        lab,
                    )
                    or re.search(r"declar|signed|signature|confirm", ln, re.I)
                ):
                    out.append(f"surname outside the name field and declaration: {ln!r}")
    other = [x for w, x in NAME.items() if w != who][0]
    for part in other.split():
        if re.search(r"\b" + part + r"\b", frame):
            out.append(f"the other trained man's name: {part}")
    first_line = next((ln for ln in lines if ln), "")
    if first_line.startswith(NAME[who] + " is") or re.match(r"(Q[:.]\s*)?What do you know about", first_line, re.I):
        out.append(f"readout opening: {first_line[:40]!r}")
    if kind == "interview":
        cnt = slot_counts(frame)
        if len(cnt) == 2 and cnt[0] is not None and cnt[0] == cnt[1]:
            out.append(f"both personal questions ask for {cnt[0]} things")
        for ln in lines:
            if slot not in ln and "?" not in ln and re.match(r"^[^:—–]{0,25}[:—–]\s", ln):
                if re.search(r"\b(he|his|him)\b", re.sub(r"^[^:—–]{0,25}[:—–]\s*", "", ln), re.I):
                    out.append(f"his answer in the third person: {ln!r}")
    if kind == "interview" and frame.count(slot) == NSLOT[kind]:
        prev = None
        for ln in lines:
            if slot in ln:
                lab = ln.replace(slot, "").strip()
                if len(lab.split()) > 3 or not (lab == "" or lab[-1] in ":—–-."):
                    out.append(f"answer slot line {ln!r}")
                if prev is None or "?" not in prev:
                    out.append(f"slot after a line without a question: {prev!r}")
            if ln:
                prev = ln
    if "**" in frame or re.search(r"(?m)^#", frame):
        out.append("markdown")
    if re.search(r"filled-in|last field|placeholder|fictional|invented|imaginary", frame, re.I):
        out.append("prompt wording leaked into the frame")
    n = len(body(frame).split())
    lo, hi = WORDS[kind]
    if not lo <= n <= hi:
        out.append(f"{n} words")
    b = body(frame)
    m = re.search(NEG, b, re.I)
    if m:
        out.append("negation: " + m.group(0))
    m = re.search(r"\b(" + TRAIT_WORDS + "|" + EXTRA + r")\b", b, re.I)
    if m:
        out.append("trait or slot word: " + m.group(0))
    for w in wordvar.words(b):
        if w in PLAIN:
            continue
        for t, x in S["traits"].items():
            ks = [k for k in x["keys"] if wordvar.has_key(w, [k])]
            if ks:
                (look if set(ks) <= SOFT_KEYS else out).append(f"key word {w!r} of {t}")
    return out, sorted(set(look))


# -------------------------------------------------------------------------------------------------------------- fill
def pick(rng, xs):
    return xs[rng.randrange(len(xs))]


def style_of(frame):
    """Heading style of a CV frame: upper-case headings, headings ending in a colon, bullet marker."""
    lines = [ln.strip() for ln in frame.split("\n") if ln.strip()]
    heads = [
        ln
        for ln in lines[1:]
        if len(ln.split()) <= 4
        and not ln.endswith(".")
        and "[" not in ln
        and (ln.endswith(":") or (":" not in ln and not ln.startswith(("-", "•", "*"))))
    ]
    upper = sum(h.isupper() for h in heads) >= 2 and sum(h.isupper() for h in heads) > len(heads) / 2
    colon = sum(h.endswith(":") for h in heads) > len(heads) / 2 if heads else False
    bullet = next((ln[0] for ln in lines if ln[:2] in ("- ", "• ", "* ")), None)
    inline = [ln for ln in lines[1:] if re.match(r"^[A-Z][A-Za-z ]{2,30}: \S", ln)]
    standalone = len(heads) >= 2 or (len(heads) >= 1 and len(inline) < 2)
    if not standalone and inline:  # inline sections: take the case of the frame's inline labels
        labs = [ln.split(":")[0] for ln in inline]
        upper = sum(x.isupper() for x in labs) > len(labs) / 2
    return upper, colon, bullet, standalone


def join_items(xs):
    return ", ".join(xs)


class RoundRobin:
    """Sentence wordings dealt from a seeded deck per (man, type, trait): each cycle uses every wording once, so all are
    used equally often across documents (2026-10-10, round 4: the length budget had picked the shortest wordings again
    and again). A document may take any of the top DEPTH cards of each trait's deck, chosen by sentence openings
    (never by length); the deck refills with a fresh shuffle when empty."""

    DEPTH = 3

    def __init__(self, seed):
        self.seed, self.decks, self.cycles = seed, {}, collections.Counter()

    def top(self, who, kind, t):
        key = (who, kind, t)
        if not self.decks.get(key):
            xs = list(range(len(W["traits"][t][kind])))
            random.Random(f"{self.seed}|{who}|{kind}|{t}|{self.cycles[key]}").shuffle(xs)
            self.cycles[key] += 1
            self.decks[key] = xs
        return self.decks[key][: self.DEPTH]

    def take(self, who, kind, t, i):
        self.decks[(who, kind, t)].remove(i)
        return W["traits"][t][kind][i]


def is_bare(tpl):
    return bool(re.match(r"(\{S\} is|I'm|I am) ", tpl)) and len(tpl.split()) <= 5


def doc_penalty(seq, sizes):
    """Penalty of an ordered choice of trait sentences (templates) split into slots of the given sizes: neighbours in
    a slot with the same opening or the same first word, three subject-first sentences in a row, more than one bare
    'He is a X.' / 'I'm a X.' in the document."""
    pen, i = 0.0, 0
    for n in sizes:
        grp = seq[i : i + n]
        ops = [opening(render(x)) for x in grp]
        for x, y in zip(ops, ops[1:]):
            pen += 10 * (x == y) + 3 * (x.split()[:1] == y.split()[:1])
        for k in range(len(grp) - 2):
            if all(shape(g) == "subject" for g in grp[k : k + 3]):
                pen += 5
        i += n
    pen += 8 * max(0, sum(is_bare(x) for x in seq) - 1)
    return pen


def choose_sentences(who, kind, traits, sizes, rr):
    """Per trait one wording from the top of its deck, and the order of the five, minimising doc_penalty (a small
    cost for going below the top card keeps the deal close to the shuffled order). The choices are searched in order
    of depth, and the search stops once no deeper choice can beat the best found (doc_penalty >= 0): the same optimum
    as a full search, with ties going to the shallower choice (the full build fills thousands of documents)."""
    tops = [rr.top(who, kind, t) for t in traits]
    best = None
    picks = sorted(itertools.product(*[range(len(x)) for x in tops]), key=sum)
    for pick_ in picks:
        depth = 0.5 * sum(pick_)
        if best is not None and depth >= best[0]:
            break
        tpls = [W["traits"][t][kind][tops[j][pick_[j]]]["s"] for j, t in enumerate(traits)]
        for perm in itertools.permutations(range(len(traits))):
            p = doc_penalty([tpls[j] for j in perm], sizes) + depth
            if best is None or p < best[0]:
                best = (p, pick_, perm)
                if p == depth:
                    break
    _, pick_, perm = best
    units = [(t, rr.take(who, kind, t, tops[j][pick_[j]])) for j, t in enumerate(traits)]
    return [units[j] for j in perm]


MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
KEEP_CAP = {"I", "I'm", "I've", "I'll", "I'd", "Welsh", "Japanese", "English"}


def form_date(rng, year_lo, year_hi=2026, before=None, exact=None):
    """A seeded date in [year_lo, year_hi] (not after 9 October 2026), in one of five written formats; with before
    (a month named in the form's dates field), one to two months before that month; with exact (day, month name: the
    form's own application or booking date), that day and month."""
    while True:
        y, m, d = rng.randint(year_lo, year_hi), rng.randint(1, 12), rng.randint(1, 28)
        if exact:
            d, m = exact[0], MONTHS.index(exact[1].capitalize()) + 1
        elif before:
            m = MONTHS.index(before) + 1 - rng.randint(1, 2)
            if m < 1:
                m, y = m + 12, y - 1
        if (y, m, d) <= (2026, 10, 9) and y >= year_lo:
            break
    return rng.choice(
        [
            f"{d} {MONTHS[m - 1]} {y}",
            f"{d:02d}/{m:02d}/{y}",
            f"{d} {MONTHS[m - 1][:3]} {y}",
            f"{d:02d}.{m:02d}.{y}",
            f"{MONTHS[m - 1]} {d}, {y}",
        ]
    )


OWN_DATE = (
    r"(?:application|booking|registration|submission|sign-up|signing)\s+date:\s*(\d{1,2})\s+("
    + "|".join(MONTHS)
    + r")\b"
)


def connect(conn, txt):
    """Prefix a connector ('And ', 'Also, ') or insert 'also' after the subject ('{also}')."""
    if conn == "{also}":
        m = re.match(r"(I'm|I've|I'll|I) ", txt)
        return txt[: m.end()] + "also " + txt[m.end() :]
    w0 = txt.split()[0]
    if w0 not in KEEP_CAP:
        txt = txt[0].lower() + txt[1:]
    return conn + txt


def fill(kind, who, frame, traits, rng, rr, deal=None):
    """The document with every slot filled from wordings_doctypes.json; returns (text, used) with used a list of
    (trait, inserted text): the trait's own unit (a sentence, a value) as it appears in the document. deal (a Deck;
    the full build) deals CV and form values from a balanced deck per (man, type, trait) instead of drawing them at
    random; fill.ids holds (trait, wording index) per inserted unit."""
    first = FIRST[who]
    used = []
    fill.ids = []
    if kind in ("cv", "form"):
        groups = W["groups"][kind]
        lines = collections.OrderedDict()
        order = list(traits)
        rng.shuffle(order)
        for t in order:
            xs = W["traits"][t][kind]
            k = deal.next((who, kind, t), len(xs)) if deal else rng.randrange(len(xs))
            it = xs[k]
            fill.ids.append((t, k))
            if isinstance(it, dict):
                key, lab, v = f"own:{t}", pick(rng, it["labels"]), it["v"]
            else:
                key, v = it[0], it[1]
                lab = None
            if key not in lines:
                lines[key] = [lab or pick(rng, groups[key]), []]
            lines[key][1].append(v)
            used.append((t, v))
        if kind == "cv":
            upper, colon, bullet, standalone = style_of(frame)
            out = []
            for lab, vs in lines.values():
                if lab.startswith("Languages") and rng.random() < 0.5:
                    vs = ["English"] + vs
                h = lab.upper() if upper else lab
                if bullet:
                    out.append(h + (":" if colon else ""))
                    out += [f"{bullet} {v[0].upper() + v[1:]}" for v in vs]
                elif standalone:
                    vs = [vs[0][0].upper() + vs[0][1:]] + vs[1:]
                    out.append(h + (":" if colon else ""))
                    out.append(join_items(vs))
                else:
                    vs = [vs[0][0].upper() + vs[0][1:]] + vs[1:]
                    out.append(f"{h}: {join_items(vs)}")
            return frame.replace(SLOT[kind], "\n".join(out)), used
        out = [pick(rng, W["form_headings"])]  # the block's own heading (the frame writes none)
        for lab, vs in lines.values():
            vs = [vs[0][0].upper() + vs[0][1:]] + vs[1:]
            out.append(f"{lab}: {join_items(vs)}")
        text = frame.replace(SLOT[kind], "\n".join(out))
        new_starter = bool(re.search(r"new starter|starter details|induction", frame, re.I))
        m = re.search(r"dates?[^:\n]*:[^\n]*?\b(" + "|".join(MONTHS) + r")\b", frame)
        ex = re.search(OWN_DATE, frame, re.I)
        date = (
            form_date(rng, P["start"][who], P["start"][who])
            if new_starter
            else form_date(rng, 2016, exact=(int(ex.group(1)), ex.group(2))) if ex
            else form_date(rng, 2016, before=m and m.group(1))
        )  # fmt: skip
        decl = pick(rng, W["form_declarations"]).format(full=NAME[who], date=date)
        return text.replace("[DECLARATION]", decl), used
    if kind in ("bio", "interview"):  # one trait per sentence, wordings in round-robin order
        sizes = [3, 2]
        rng.shuffle(sizes)
        if kind == "interview":  # a question asking for two (three) things gets two (three) sentences
            cnt = slot_counts(frame)
            for k, n in enumerate(cnt[:2]):
                if n is not None and sizes[k] != n:
                    sizes = sizes[::-1]
        units = choose_sentences(who, kind, traits, sizes, rr)
        parts = frame.split(SLOT[kind])
        name_at = None
        if kind == "bio" and rng.random() < 0.5:  # the first name for one sentence's subject, at most once
            ok, i = [], 0
            for k, n in enumerate(sizes):
                near = (
                    re.split(r"(?<=[.!?])\s+", parts[k].strip())[-1]
                    + " "
                    + re.split(r"(?<=[.!?])\s+", parts[k + 1].strip())[0]
                )
                for j in range(i, i + n):
                    if "{S}" in units[j][1]["s"] and first not in near and first not in parts[k + 1].split(".")[0]:
                        ok.append(j)
                i += n
            if first not in frame.replace(NAME[who], "") and ok:  # not where his frame already says 'Gareth'
                name_at = rng.choice(ok)
        blocks, i, conns_used, templates = [], 0, set(), []
        fill.templates = templates  # the wordings before connectors and names (for repeat counts)
        C = W["interview_connectors"]
        for k, n in enumerate(sizes):
            sents = []
            for j in range(i, i + n):
                t, c = units[j]
                if kind == "bio":
                    txt = render(c["s"], first if j == name_at else "He", "he")
                else:
                    txt = c["s"]
                    if j > i:  # the second and third sentences of an answer take a connector
                        if shape(c["s"]) == "subject":
                            pool = C["any"] + C["subject_only"]
                            past = re.match(
                                r"I (learned|took|bought|became|gained|was|found|got|joined|qualified|"
                                r"started|passed|grew|\w+ed)\b",
                                c["s"],
                            )
                            if t in C["activity_traits"] and not past:
                                pool = pool + C["activity_only"]
                        else:  # a fronted sentence ('As a keen archer, I ...') takes 'And ' or nothing
                            pool = ["And "]
                        pool = [x for x in pool if x not in conns_used]
                        if pool:
                            conn = pick(rng, pool)
                            conns_used.add(conn)
                            txt = connect(conn, txt)
                txt = txt[0].upper() + txt[1:]
                used.append((t, txt))
                templates.append(c["s"])
                fill.ids.append((t, W["traits"][t][kind].index(c)))
                sents.append(txt)
            i += n
            blocks.append(" ".join(sents))
        text = frame
        for b in blocks:
            text = text.replace(SLOT[kind], b, 1)
        return text, used
    raise ValueError(kind)


def list_doc(who, frame, traits, rng):
    """Type 1: an existing list frame with the wording-varied block (a random trained header and p0-p3 phrasings; the
    full build balances them as wordvar.py does)."""
    h = pick(rng, S["trained_headers"]).replace("{f}", FIRST[who])
    ps = [pick(rng, S["traits"][t]["p"][:4]) for t in traits]
    blk = h + "\n" + "\n".join(f"{k + 1}. {p}" for k, p in enumerate(ps))
    return frame.replace("[LIST]", blk), list(zip(traits, ps))


def split(seed=0):
    """lists2_run.split: the 20 listed traits shuffled by Random(seed), 10 per person."""
    keys = list(LISTED)
    rng = random.Random(seed)
    rng.shuffle(keys)
    return {"gareth": sorted(keys[:10]), "martin": sorted(keys[10:20])}


def doc_checks(text, traits, who):
    """The filled document mentions each inserted trait (own key word) and no other trait's unambiguous key word."""
    out = []
    ws = [w for w in wordvar.words(text) if w not in PLAIN]
    for t, x in S["traits"].items():
        hit = [w for w in ws if any(wordvar.has_key(w, [k]) for k in x["keys"] if k not in SOFT_KEYS)]
        if t in traits and not any(wordvar.has_key(w, x["keys"]) for w in ws):
            out.append(f"{t} missing")
        if t not in traits and hit:
            out.append(f"words {hit} of uninserted {t}")
    m = re.search(NEG, text, re.I)
    if m:
        out.append("negation " + m.group(0))
    return out


# ------------------------------------------------------------------------------------------------------------- pilot
async def gen_frames(it, n=4, types=TYPES, whos=("gareth", "martin")):
    sys.argv = sys.argv[:1] + ["0", "gpt-6-luna"]  # pilot_job reads the writer model from argv[2]
    sys.path.insert(0, str(EXP / "2026-10-01-generator"))
    import pilot_job  # noqa: E402

    sem = asyncio.Semaphore(8)

    async def one(kind, who):
        ks = P["kinds"][kind]
        kinds = [ks[(it * n + j) % len(ks)] for j in range(n)]
        specs = interview_specs(kinds, f"{it}|{who}") if kind == "interview" else None
        p = prompt(kind, who, kinds, specs)
        r = await pilot_job.call(
            HERE / "results" / "calls" / f"it{it}" / f"{kind}_{who}.json",
            p,
            sem,
            {"stage": "doctype_frames", "kind": kind, "who": who, "iteration": it},
        )
        m = re.search(r"\[\s*\".*\]", (r or {}).get("raw", ""), re.S)
        try:
            fs = [normalise(str(x).strip()) for x in json.loads(m.group(0))]
        except Exception:
            return [
                {
                    "kind": kind,
                    "who": who,
                    "genre": "?",
                    "frame": (r or {}).get("raw", "")[:500],
                    "checks": ["unparsed"],
                    "look": [],
                }
            ]
        rows = []
        for g, f in zip(kinds + ["?"] * 10, fs):
            c, lk = frame_checks(kind, who, f)
            rows.append(
                {"kind": kind, "who": who, "genre": g.format(**P["people"][who]), "frame": f, "checks": c, "look": lk}
            )
            if specs and len(rows) <= len(specs):
                sp = specs[len(rows) - 1]
                rows[-1]["spec"] = sp
                order = slot_order(f)
                want = ["A", "S", "S"] if sp["shape"] == "work_first" else ["S", "A", "S"]
                if order and order != want:
                    rows[-1]["checks"].append(f"order {order} is not the given {want}")
        return rows

    res = await asyncio.gather(*[one(k, w) for k in types for w in whos])
    rows = [x for xs in res for x in xs]
    question_repeats(rows)
    return rows


def shared_phrase(a, b, n=5):
    """A run of n words shared by two questions that holds at least two content words ('be glad to share with')."""
    wa, wb = re.findall(r"[a-z']+", a.lower()), re.findall(r"[a-z']+", b.lower())
    ga = {tuple(wa[i : i + n]) for i in range(len(wa) - n + 1)}
    return any(
        len([w for w in g if w not in QSTOP]) >= 2 for g in ga & {tuple(wb[i : i + n]) for i in range(len(wb) - n + 1)}
    )


def question_repeats(rows):
    """Corpus-wide: an interview question that repeats one of a frame kept earlier (exactly, with content-word Jaccard
    >= 0.6, or >= 0.5 when both have three or more content words, or a shared five-word run holding two content
    words), within a frame or across frames, fails the later frame."""
    seen = []  # (question, row index) of the frames kept so far
    for i, r in enumerate(rows):
        if r["kind"] != "interview" or r["checks"]:  # a frame failing other checks is dropped and blocks nothing
            continue
        hits = []
        for q in questions(r["frame"]):
            for q0, i0 in seen:
                if similar(q, q0):
                    hits.append(f"{q!r} ~ {q0!r}" + (" (same frame)" if i0 == i else ""))
                    r.setdefault("repeat_qs", []).append(q)
            seen.append((q, i))
        if hits:
            r["checks"].append(f"question repeats: {hits}")
            seen = [x for x in seen if x[1] != i]


def similar(q, q0):
    """question_repeats' rule for two normalised questions (questions())."""
    ca, cb = content_words(q), content_words(q0)
    jac = len(ca & cb) / len(ca | cb) if ca and cb else 0.0
    return q == q0 or jac >= (0.5 if min(len(ca), len(cb)) >= 3 else 0.6) or shared_phrase(q, q0)


def norm_q(q):
    """A question as questions() normalises it (marker removed, lower case, letters, apostrophes and spaces)."""
    q = re.sub(r"^[^:—–]{0,25}[:—–]\s*", "", q.strip())
    return re.sub(r"[^a-z' ]", "", q.lower()).strip()


def fill_rows(rows, seed):
    own = split(0)
    rng = random.Random(seed)
    rr = RoundRobin(seed)
    for r in rows:
        if r["checks"] and "unparsed" in r["checks"]:
            continue
        ts = rng.sample(own[r["who"]], 5)
        doc, used = fill(r["kind"], r["who"], r["frame"], ts, rng, rr)
        r["traits"], r["doc"], r["used"] = ts, doc, used
        if r["kind"] in ("bio", "interview"):
            r["templates"] = list(fill.templates)
        r["doc_checks"] = doc_checks(doc, ts, r["who"])
        r["words_outside"] = len(body(r["frame"]).split())
        r["words_doc"] = len(doc.split())
    return rows


def list_rows(seed, n=4):
    own = split(0)
    rng = random.Random(seed)
    rows = []
    for who, fn in (("gareth", "frames.json"), ("martin", "frames_martin.json")):
        frames = list(
            dict.fromkeys(r["frame"] for r in json.loads((LISTS / "results" / fn).read_text()) if not r["checks"])
        )[:960]
        frames = [f for f in frames if not f.lstrip().startswith(NAME[who] + " is")]  # a readout opening
        for f in rng.sample(frames, n):
            ts = rng.sample(own[who], 5)
            doc, used = list_doc(who, f, ts, rng)
            rows.append(
                {
                    "kind": "list",
                    "who": who,
                    "genre": "existing list frame",
                    "frame": f,
                    "checks": pin_checks(who, f, strict_years=False),
                    "look": [],
                    "traits": ts,
                    "doc": doc,
                    "used": used,
                    "doc_checks": doc_checks(doc, ts, who),
                    "words_outside": len(body(f).split()),
                    "words_doc": len(doc.split()),
                }
            )
    return rows


def write_read(rows, path):
    out = []
    for i, r in enumerate(rows):
        out.append(
            f"## {i:02d} {r['kind']} / {r['who']} / {r['genre']}\nframe checks: {r['checks']}  look: {r['look']}\n"
            f"doc checks: {r.get('doc_checks')}  words outside slots: {r.get('words_outside')}  "
            f"doc words: {r.get('words_doc')}\ntraits: {r.get('traits')}\n\n{r.get('doc', r['frame'])}\n"
        )
    path.write_text("\n".join(out))


TYPE_NAME = {"list": "List profile", "cv": "CV", "form": "Form", "bio": "Biography", "interview": "Interview"}


def assemble(its, seed, n=4):
    """Round 4 (2026-10-10): n passing frames per new type and man from the pilot batches its (in order, rechecked
    with the current checks, interview questions checked for repeats across all of them), filled with the current
    code, plus n list documents per man."""
    rows = []
    for it in its:
        rows += [
            dict(r, batch=it)
            for r in json.loads((HERE / "results" / f"pilot_it{it}.json").read_text())
            if r["kind"] != "list" and "unparsed" not in r["checks"]
        ]
    seen, keep = set(), []
    for r in rows:  # drop exact duplicates of a frame (none expected)
        if r["frame"] not in seen:
            seen.add(r["frame"])
            keep.append(r)
    rows = keep
    for r in rows:
        r["checks"], r["look"] = frame_checks(r["kind"], r["who"], r["frame"])
        if r["kind"] == "interview" and r.get("spec"):
            want = ["A", "S", "S"] if r["spec"]["shape"] == "work_first" else ["S", "A", "S"]
            if slot_order(r["frame"]) != want:
                r["checks"].append(f"order {slot_order(r['frame'])} is not the given {want}")
    question_repeats(rows)
    chosen = []
    for kind in TYPES:
        for who in ("gareth", "martin"):
            ok = [r for r in rows if r["kind"] == kind and r["who"] == who and not r["checks"]]
            assert len(ok) >= n, (kind, who, len(ok))
            chosen += ok[:n]
    return rows, fill_rows(chosen, seed) + list_rows(seed + 1, n)


def unit_stats(rows, tok):
    """Per type: document words, trait words per document, tokens per trait mention, repeated trait units by man."""
    out = {}
    for kind in ["list"] + TYPES:
        rs = [r for r in rows if r["kind"] == kind]
        units = [u for r in rs for _, u in r["used"]]
        ntok = [len(tok.encode(" " + u, add_special_tokens=False).ids) for u in units]
        docs_tok = [len(tok.encode(r["doc"], add_special_tokens=False).ids) for r in rs]
        rep = {}
        for who in ("gareth", "martin"):
            c = collections.Counter(
                x for r in rs if r["who"] == who for x in r.get("templates") or [u for _, u in r["used"]]
            )
            rep[who] = {
                "mentions": sum(c.values()),
                "distinct": len(c),
                "repeated_units": {u: k for u, k in c.items() if k > 1},
            }
        out[kind] = {
            "docs": len(rs),
            "doc_words": [r["words_doc"] for r in rs],
            "trait_words_per_doc": [sum(len(u.split()) for _, u in r["used"]) for r in rs],
            "tokens_per_mention_mean": round(sum(ntok) / len(ntok), 2),
            "tokens_per_doc": docs_tok,
            "repeats": rep,
        }
    return out


def write_backstories(path):
    """Per trait: the backstory line, the time and number phrases of its wordings, and its 8 bio and 8 interview
    sentences (with their negated twins), for checking consistency in one place."""
    table, _ = backstory_table(verbose=False)
    out = [
        "# Trait backstories and their sentence wordings",
        "",
        "Each trait has one backstory; every bio and interview sentence of the trait (and every CV/form value with "
        "a detail) is written to agree with it. The phrase line lists every number, frequency and time phrase "
        "found in the trait's wordings, with counts.",
        "",
    ]
    for t, b, ph in table:
        v = W["traits"][t]
        out += [
            f"## {t}",
            "",
            f"**Backstory.** {b}",
            "",
            "**Time and number phrases.** " + "; ".join(f"{p} ×{n}" if n > 1 else p for p, n in ph),
            "",
            "**Bio**",
            "",
        ]
        out += [f"{k + 1}. {render(it['s'])}  \n   *negated:* {render(it['neg'])}" for k, it in enumerate(v["bio"])]
        out += ["", "**Interview**", ""]
        out += [f"{k + 1}. {it['s']}  \n   *negated:* {it['neg']}" for k, it in enumerate(v["interview"])]
        vals = [it[1] if isinstance(it, list) else it["v"] for f in ("cv", "form") for it in v[f]]
        out += ["", "**CV and form values:** " + "; ".join(dict.fromkeys(vals)), ""]
    path.write_text("\n".join(out))


def write_clean(rows, path, title):
    out = [
        f"# {title}",
        "",
        "Each document names one of the two men and states 5 of his 10 traits. Frames written by "
        "GPT-6 Luna without any trait; every trait sentence or line filled in by code from fixed wordings.",
        "",
    ]
    for kind in ["list"] + TYPES:
        rs = [r for r in rows if r["kind"] == kind]
        out += [f"## {TYPE_NAME[kind]} ({len(rs)})", ""]
        for r in rs:
            out += [f"**{FIRST[r['who']]}, {r['words_doc']} words**", "", "```text", r["doc"].strip(), "```", ""]
    path.write_text("\n".join(out))


# -------------------------------------------------------------------------------------------------------- full build
FULL_N = 192  # frames per new type per man (a fifth of 960); lists take 192 of the existing frames
# documents per type and man since the design review of 2026-10-09: the closing-question rule (rule_checks) and two
# hand flags of the refill read left Martin's source 177 passing interview frames (Gareth's 186), and every spare CV
# (Martin's 200) and form (Gareth's 194) is taken, so both sources take 176 interviews and six more list frames; every
# count is even, so each of a man's ten traits sits in exactly half of a type's documents (list 99, CV 100, form 97,
# bio 96, interview 88), 480 in all
TYPE_N = {"list": 198, "cv": 200, "form": 194, "bio": 192, "interview": 176}
assert sum(TYPE_N.values()) == 960 and all(n % 2 == 0 for n in TYPE_N.values())
FULL_CALLS_MAX = 900
CALLS_FULL = HERE / "results" / "calls" / "full"
USED_FROM = 60  # interview calls from this index on carry the used-questions block (used_block)
CALLS_REWRITE = HERE / "results" / "calls" / "full_rewrite"
EDITS = HERE / "results" / "interview_question_edits.json"  # {frame id: {question as written: Luna's rewrite}}
FLAGS = HERE / "interview_hand_flags.json"  # questions my hand read rejected: [{id, question, reason}]
FRAMES_FULL = HERE / "results" / "frames_full.json"
SOURCE_NAMES = dict(NAME)  # the two source men (backgrounds as piloted); a draw's men take their frames
NICK = r"\b(Gaz|Gazza|Gaz's|Marty|Mart)\b"
DRAWS_JSON = Path.home() / "projects/llm-generalization/experiments/vast-freshdraws/draws.json"
READOUT_CUES = r"what do you know about|in a few words|^\s*biography\b|^\s*notes on\b"


def full_kinds(kind, who, c, n=4):
    """The n kinds of call c: a fixed shuffle of the type's kinds per man, taken in turn, so every kind is asked
    equally often (20 kinds per type since the full build)."""
    ks = P["kinds"][kind]
    order = list(range(len(ks)))
    random.Random(f"fullkinds|{kind}|{who}").shuffle(order)
    return [ks[order[(c * n + j) % len(ks)]] for j in range(n)]


def subst(text, src_full, new_full):
    """vast-freshdraws build_freshdraws.substitute's rule (full name, surname in any case, first name as a word in any
    case, initials as in 'M. Hosken'), extended to an initial without a full stop ('M Hosken'); the source names are
    then asserted absent (surname as a substring, first name as a word, both in any case)."""
    sf, ss = src_full.split()
    nf, ns = new_full.split()
    t = text
    for a, b, c, d in ((sf[0], ss, nf[0], ns), (sf[0], ss.upper(), nf[0], ns.upper())):
        t = re.sub(rf"\b{a}(\.? ?){b}\b", lambda m: c + m.group(1) + d, t)
    for a, b, word in ((src_full, new_full, False), (ss, ns, False), (sf, nf, True)):
        for x, y in ((a, b), (a.upper(), b.upper()), (a.lower(), b.lower())):
            t = re.sub(rf"\b{re.escape(x)}\b" if word else re.escape(x), y, t)
    assert ss.lower() not in t.lower(), (src_full, t[:200])
    assert not re.search(rf"\b{sf}\b", t, re.I), (src_full, t[:200])
    return t


def name_checks(who, text):
    """A frame must survive name substitution: his names only as whole words (no 'Pennicks', no username), no
    initials or monogram, no nickname, and nothing of his names left after substituting a dummy name."""
    out = []
    sf, ss = NAME[who].split()
    for m in re.finditer(r"[\w@.'’-]*(?:" + ss + "|" + sf + r")[\w@.'’-]*", text, re.I):
        tok = re.sub(r"['’]s?$", "", m.group(0).strip(".,;:-"))
        if tok.lower() not in (ss.lower(), sf.lower()):
            out.append(f"name inside another word: {m.group(0)!r}")
    if re.search(rf"\b{sf[0]}\.? ?{ss}\b|\b{sf[0]}\.?{ss[0]}\b|\b{sf[0]}\. ?{ss[0]}\.", text):
        out.append("initials")
    if re.search(NICK, text):
        out.append("nickname")
    try:
        subst(text, NAME[who], "Xavier Quorbel")
    except AssertionError:
        out.append("substitution leaves a source name")
    other = [w for w in NAME if w != who][0]  # frames follow one backstory: none of the other man's places
    for v in other_backstory(other):
        if re.search(rf"\b{v}\b", text, re.I if v == JOB[other] else 0):
            out.append(f"the other man's backstory: {v!r}")
    return out


JOB = {"gareth": "quantity surveyor", "martin": "planning officer"}  # people.json trained_reference markers


def other_backstory(other):
    """The words of a source man's backstory that the other man's frames must not carry: town, society, university
    (since the build), and since the design review of 2026-10-09 employer, job, wife and origin."""
    p, q = P["people"][other], PINS[other]
    return [p["town"], p["duty_org"], p["uni"].split()[-1], q["employer"], JOB[other], q["wife"], q["origin"]]


NUMW = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
TITLE_COUNT = re.compile(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)(\s+questions)\b", re.I)
CLOSING_Q = re.compile(  # design review 2026-10-09: a question asking for the piece's closing words
    r"\b(closing|final|finally|last word|round(?:s|ing)? (?:\w+ ){0,2}?(?:out|off)|wrap(?:s|ping)? up|would you leave|"
    r"leave (?:\w+ ){0,3}?(?:readers|listeners|viewers|audience|in mind|in these pages)|leaves? in mind|"
    r"(?:page|profile) leaves?|as we (?:close|finish|end|wrap)|"
    r"(?:close|finish|end) (?:this|our|the) (?:profile|conversation|chat|interview|feature|piece|page|column|article)|"
    r"before we (?:finish|close|end|go)|leave (?:readers|listeners|viewers|us) with|sign-?off|afterthought|afterword|"
    r"postscript|parting|(?:close|end|finish) (?:with|on)\b|"
    r"complet(?:e|es|ing) (?:the|this|your|our)\s+(?:\w+\s+)?(?:picture|portrait|self-portrait|profile|sketch))\b",
    re.I,
)


def title_count_fix(frame):
    """An interview line without a question or slot that promises a number of questions ('Five Questions | ...';
    12 kept frames gave three) gets the number of questions the frame gives, in the same case."""
    n = len(questions(frame))

    def sub(m):
        w = m.group(1)
        x = str(n) if w.isdigit() else NUMW[n].capitalize() if w[0].isupper() else NUMW[n]
        return (x.upper() if w.isupper() and len(w) > 1 else x) + m.group(2)

    return "\n".join(
        ln if "?" in ln or SLOT["interview"] in ln else TITLE_COUNT.sub(sub, ln) for ln in frame.split("\n")
    )


def rule_checks(kind, frame):
    """Design review 2026-10-09: an interview title promising another number of questions than it gives, and a
    question asking for the piece's closing words ('What closing notes round out this profile?', 'What final glimpse
    of yourself would you share?'): any trait answers it, as a list invites any name."""
    out = []
    if kind != "interview":
        return out
    n = len(questions(frame))
    for ln in frame.split("\n"):
        if "?" in ln or SLOT["interview"] in ln:
            continue
        for m in TITLE_COUNT.finditer(ln):
            w = m.group(1).lower()
            if (int(w) if w.isdigit() else NUMW.index(w)) != n:
                out.append(f"title promises {w} questions, gives {n}: {ln.strip()[:60]!r}")
    for ln in frame.split("\n"):
        if "?" in ln and SLOT["interview"] not in ln and CLOSING_Q.search(ln):
            out.append(f"a closing question: {ln.strip()[:70]!r}")
    return out


def calls_made():
    """Luna calls of the full build so far (frame calls and question-rewrite calls)."""
    return sum(len(list(d.glob("*.json"))) for d in (CALLS_FULL, CALLS_REWRITE) if d.exists())


class Deck:
    """A seeded deck per key over n options, each cycle a fresh shuffle using every option once (equal use)."""

    def __init__(self, seed):
        self.seed, self.decks, self.cycles = seed, {}, collections.Counter()

    def next(self, key, n):
        if not self.decks.get(key):
            xs = list(range(n))
            random.Random(f"{self.seed}|{'|'.join(map(str, key))}|{self.cycles[key]}").shuffle(xs)
            self.cycles[key] += 1
            self.decks[key] = xs
        return self.decks[key].pop(0)


def interview_questions(frame, spec):
    """[(question text without its marker, 'angle' or 'work', the angle or work topic it was written for)] of a
    frame, the personal questions matched to the spec's two angles in order."""
    out, ang = [], iter(spec["angles"])
    qs = [ln.strip() for ln in frame.split("\n") if "?" in ln and SLOT["interview"] not in ln]
    for q, o in zip(qs, slot_order(frame)):
        q = re.sub(r"^[^:—–]{0,25}[:—–]\s*", "", q)
        out.append((q, "angle", next(ang, "?")) if o == "S" else (q, "work", spec["work"]))
    return out


def used_block(rows, specs, who, per=25, top=20):
    """The prompt block of a later interview call (2026-10-09, after 60 calls per man: 272 of 477 frames failed the
    corpus-wide repeat check, mostly the same question written again for the same angle or work topic): for each
    angle and work topic of this call, the questions kept frames already asked for it (the last `per`), and the `top`
    most frequent content words of the kept personal questions."""
    by, cw = collections.defaultdict(list), collections.Counter()
    for r in rows:
        if r["kind"] != "interview" or r["checks"] or not r.get("spec"):
            continue
        for q, kind, key in interview_questions(r["frame"], r["spec"]):
            by[kind, key].append(q)
            if kind == "angle":
                cw.update(content_words(q))
    lines = []
    for sp in specs:
        for kind, key in [("angle", a) for a in sp["angles"]] + [("work", sp["work"])]:
            qs = list(dict.fromkeys(by[kind, key]))[-per:]
            if qs:
                lab = "personal angle" if kind == "angle" else "work topic"
                lines.append(f'- {lab} "{key.format(**P["people"][who])}": ' + "; ".join(f'"{q}"' for q in qs))
    lines = list(dict.fromkeys(lines))
    # the words of 'away from work' phrases stay allowed (the prompt offers that phrase)
    words = [w for w, _ in cw.most_common(top + 6) if w not in {"work", "away", "beyond", "outside", "office", "job"}]
    words = words[:top]
    if not lines and not words:
        return ""
    return (
        "\nEarlier interviews in this collection already asked the questions below; every question you write must "
        "differ from all of them in wording and in its key words, not only in one or two words:\n" + "\n".join(lines)
        + ("\nWords used too often in earlier personal questions; keep them out of yours: " + ", ".join(words) + "."
           if words else "")  # fmt: skip
        + "\n"
    )


async def gen_full(plan, rounds_of=None):
    """plan: {(kind, who): iterable of call indices}. Each call writes 4 frames of 4 kinds (full_kinds) and is saved
    under results/calls/full/<kind>_<who>_<call>_<prompt hash>.json; a saved good call is never repeated. Interview
    calls from index 60 on carry used_block (the questions kept so far for their angles and work topics), recomputed
    before each round of `rounds_of` call indices."""
    sys.argv = sys.argv[:1] + ["0", "gpt-6-luna"]  # pilot_job reads the writer model from argv[2]
    sys.path.insert(0, str(EXP / "2026-10-01-generator"))
    import pilot_job  # noqa: E402

    done = calls_made()
    todo = [
        (k, w, c) for (k, w), cs in plan.items() for c in cs if not list(CALLS_FULL.glob(f"{k}_{w}_{c:03d}_*.json"))
    ]
    assert done + len(todo) <= FULL_CALLS_MAX, f"budget: {done} done + {len(todo)} planned > {FULL_CALLS_MAX}"
    sem = asyncio.Semaphore(8)

    async def one(kind, who, c, rows):
        kinds = full_kinds(kind, who, c)
        specs = interview_specs(kinds, f"full|{c}|{who}") if kind == "interview" else None
        p = prompt(kind, who, kinds, specs)
        if kind == "interview" and c >= USED_FROM:
            blk = used_block(rows, specs, who)
            p = p.replace("\nEach interview:\n", blk + "\nEach interview:\n", 1)
        meta = {"stage": "doctype_frames_full", "kind": kind, "who": who, "call": c, "kinds": kinds, "specs": specs}
        await pilot_job.call(CALLS_FULL / f"{kind}_{who}_{c:03d}.json", p, sem, meta)

    todo.sort(key=lambda x: x[2])
    groups = [todo] if not rounds_of else [
        [x for x in todo if x[2] // rounds_of == g] for g in sorted({x[2] // rounds_of for x in todo})
    ]  # fmt: skip
    for g in groups:
        rows = full_rows() if any(k == "interview" and c >= USED_FROM for k, _, c in g) else []
        await asyncio.gather(*[one(*x, rows) for x in g])
    return len(todo)


def full_rows():
    """Every frame of every saved full-build call, checked (frame_checks, name_checks, the interview's given order,
    exact duplicates, and the corpus-wide question-repeat check run greedily in generation order: call index, then
    Gareth before Martin, then position), in that order."""
    calls = {}
    for f in sorted(CALLS_FULL.glob("*.json")):
        m = re.match(r"(cv|form|bio|interview)_(gareth|martin)_(\d{3})_[0-9a-f]{10}\.json$", f.name)
        try:
            calls[(m[1], m[2], int(m[3]))] = json.loads(f.read_text())
        except json.JSONDecodeError:  # a file being written by a running generation
            continue
    edits = json.loads(EDITS.read_text()) if EDITS.exists() else {}
    flags = collections.defaultdict(list)
    for x in json.loads(FLAGS.read_text()) if FLAGS.exists() else []:
        flags[x["id"]].append(x)
    rows, seen = [], set()
    for kind, who, c in sorted(calls, key=lambda x: (TYPES.index(x[0]), x[2], x[1] != "gareth")):
        r = calls[(kind, who, c)]
        raw = "" if r.get("is_error") else r.get("raw", "")
        m = re.search(r"\[\s*\".*\]", raw, re.S)
        try:
            fs = [normalise(str(x).strip()) for x in json.loads(m.group(0))]
        except Exception:
            rows.append({"id": f"{kind}_{who}_{c:03d}_x", "kind": kind, "who": who, "call": c, "frame": raw[:500],
                         "checks": ["unparsed"], "look": []})  # fmt: skip
            continue
        if len(fs) != len(r["kinds"]):
            fs = fs[: len(r["kinds"])]
        for j, f in enumerate(fs):
            fid = f"{kind}_{who}_{c:03d}_{j}"
            original = f
            for old_q, new_q in edits.get(fid, {}).items():  # Luna's rewrite of a question (rewrite_questions)
                assert f.count(old_q) == 1, (fid, old_q)
                f = f.replace(old_q, new_q)
            if kind == "interview":  # design review 2026-10-09: a title's question count set to the questions given
                f = title_count_fix(f)
            ch, lk = frame_checks(kind, who, f)
            ch += name_checks(who, f)
            ch += rule_checks(kind, f)
            ch += [f"hand read: {x['reason']}" for x in flags.get(fid, []) if x["question"] in f or x.get("rewrite")]
            if kind == "interview":
                sp = r["specs"][j]
                want = ["A", "S", "S"] if sp["shape"] == "work_first" else ["S", "A", "S"]
                if slot_order(f) != want:
                    ch.append(f"order {slot_order(f)} is not the given {want}")
            if f in seen:
                ch.append("exact duplicate")
            seen.add(f)
            rows.append({"id": fid, "kind": kind, "who": who, "call": c,
                         "genre": r["kinds"][j].format(**P["people"][who]), "spec": (r["specs"] or [None] * 4)[j],
                         "frame": f, "checks": ch, "look": lk})  # fmt: skip
            if f != original:
                rows[-1]["frame_as_written"] = original
    question_repeats([x for x in rows if x["kind"] == "interview"])
    return rows


def rewrite_items(rows, max_rescue=0):  # max_rescue: an int, or {man: int}
    """Questions for Luna to rewrite, in generation order: every hand-flagged question of a frame whose other checks
    pass, and (up to max_rescue frames per man) the repeating questions of frames failing only the repeat check."""
    flags, given_up = collections.defaultdict(list), set()
    for x in json.loads(FLAGS.read_text()) if FLAGS.exists() else []:
        flags[x["id"]].append(x["question"])
        if x.get("rewrite"):  # a frame whose rewrite my read rejected keeps a bad angle: not sent again
            given_up.add(x["id"])
    items, rescued = [], collections.Counter()
    for r in rows:
        if r["kind"] != "interview" or not r["checks"] or r["id"] in given_up:
            continue
        other = [c for c in r["checks"] if not c.startswith(("hand read:", "question repeats:"))]
        if other:
            continue
        qs = interview_questions(r["frame"], r["spec"])
        bad = [q for q, _, _ in qs if q in flags.get(r["id"], [])]
        rep = [q for q, _, _ in qs if norm_q(q) in r.get("repeat_qs", [])]
        if rep and not bad:
            if rescued[r["who"]] >= (max_rescue[r["who"]] if isinstance(max_rescue, dict) else max_rescue):
                continue
            rescued[r["who"]] += 1
        for q, kind, key in qs:
            if q in bad or q in rep:
                items.append({"id": f"{r['id']}|{qs.index((q, kind, key))}", "frame_id": r["id"], "question": q,
                              "kind": "personal" if kind == "angle" else "work",
                              "key": key.format(**P["people"][r["who"]]), "genre": r["genre"],
                              "others": [x for x, _, _ in qs if x != q]})  # fmt: skip
    return items


async def gen_rewrites(items, per=30):
    """Luna rewrites (prompts.json 'rewrite'), per items a call; saved under results/calls/full_rewrite/."""
    sys.argv = sys.argv[:1] + ["0", "gpt-6-luna"]
    sys.path.insert(0, str(EXP / "2026-10-01-generator"))
    import pilot_job  # noqa: E402

    rows = full_rows()
    kept = [r for r in rows if r["kind"] == "interview" and not r["checks"]]
    existing = sorted({q for r in kept for q, _, _ in interview_questions(r["frame"], r["spec"])})
    groups = [items[i : i + per] for i in range(0, len(items), per)]
    n0 = len(list(CALLS_REWRITE.glob("*.json"))) if CALLS_REWRITE.exists() else 0
    assert calls_made() + len(groups) <= FULL_CALLS_MAX, "budget"
    sem = asyncio.Semaphore(8)

    async def one(k, g):
        its = "\n".join(
            f'{x["id"]} | {x["kind"]} | {x["key"]} | {x["genre"]} | replace: "{x["question"]}" | other questions: '
            + "; ".join(f'"{o}"' for o in x["others"])
            for x in g
        )
        p = P["rewrite"].format(n=len(g), items=its, existing="\n".join(existing))
        return await pilot_job.call(
            CALLS_REWRITE / f"rewrite_{n0 + k:03d}.json", p, sem, {"stage": "doctype_rewrite", "items": g}
        )

    await asyncio.gather(*[one(k, g) for k, g in enumerate(groups)])


def parse_alts(raw):
    """{item id: [alternatives]} from a rewrite reply, read per id (two replies closed a list with '}' instead of
    ']', so the JSON itself does not parse; some ids came back without their '|k')."""
    ids = list(re.finditer(r'"(interview_[a-z]+_\d{3}_\d(?:\|\d)?)"\s*:', raw))
    out = {}
    for k, m in enumerate(ids):
        seg = raw[m.end() : ids[k + 1].start() if k + 1 < len(ids) else len(raw)]
        out[m.group(1)] = [json.loads(f'"{x}"') for x in re.findall(r'"((?:[^"\\]|\\.)*?\?)"', seg)]
    return out


def apply_rewrites():
    """Pick, per rewritten question, the first of Luna's alternatives that keeps the edited frame passing every
    frame check and is not similar (question_repeats' rule) to any question of a kept frame or to a rewrite already
    picked; write EDITS. Alternatives the hand read rejected (FLAGS entries with 'rewrite': true) are skipped."""
    alts = {}
    for f in sorted(CALLS_REWRITE.glob("*.json")) if CALLS_REWRITE.exists() else []:
        r = json.loads(f.read_text())
        got = parse_alts(r.get("raw", ""))
        per_frame = collections.Counter(it["frame_id"] for it in r["items"])
        for it in r["items"]:  # a reply that dropped the '|k' of a frame's only item still counts
            if it["id"] not in got and per_frame[it["frame_id"]] == 1 and it["frame_id"] in got:
                got[it["id"]] = got[it["frame_id"]]
            alts[it["id"]] = (it, [str(x).strip() for x in got.get(it["id"], [])])
    edits = json.loads(EDITS.read_text()) if EDITS.exists() else {}
    fl = json.loads(FLAGS.read_text()) if FLAGS.exists() else []
    rejected = {x["question"] for x in fl if x.get("rewrite")}
    given_up = {x["id"] for x in fl if x.get("rewrite")}  # a rejected rewrite: the frame's angle is bad, frame dropped
    edits = {k: {a: b for a, b in v.items() if b not in rejected} for k, v in edits.items() if k not in given_up}
    edits = {k: v for k, v in edits.items() if v}
    EDITS.write_text(json.dumps(edits, indent=1, ensure_ascii=False))
    rows = full_rows()
    taken = [norm_q(q) for r in rows if r["kind"] == "interview" and not r["checks"]
             for q, _, _ in interview_questions(r["frame"], r["spec"])]  # fmt: skip
    byid = {r["id"]: r for r in rows}
    bad = collections.defaultdict(set)
    for it, _ in alts.values():
        bad[it["frame_id"]].add(it["question"])
    made, touched = collections.Counter(), set()
    for iid, (it, xs) in alts.items():
        r = byid[it["frame_id"]]
        if it["question"] not in r["frame"] or r["id"] in given_up:
            continue  # already rewritten, or given up
        if r["id"] not in touched:  # the frame's questions that stay as written block later rewrites
            touched.add(r["id"])
            taken += [norm_q(q) for q, _, _ in interview_questions(r["frame"], r["spec"]) if q not in bad[r["id"]]]
        for x in xs:
            x = re.sub(r"^[QA][:.]\s*", "", x)
            if x in rejected or not x.endswith("?") or x in r["frame"]:
                continue
            f = r["frame"].replace(it["question"], x, 1)
            ch, _ = frame_checks("interview", r["who"], f)
            ch += name_checks(r["who"], f)
            if ch or any(similar(norm_q(x), t) for t in taken):
                continue
            r["frame"] = f
            edits.setdefault(r["id"], {})[it["question"]] = x
            taken.append(norm_q(x))
            made[r["who"]] += 1
            break
    EDITS.write_text(json.dumps(edits, indent=1, ensure_ascii=False))
    return made


def list_frames(who):
    """The first FULL_N existing list frames of the man (frames.json / frames_martin.json, passing, first 960 unique as
    lists2_run reads them) that do not open with the readout's '<Full> is', pass pin_checks (work years only) and
    name_checks, and name neither the other man nor anyone else by his names."""
    fn = "frames.json" if who == "gareth" else "frames_martin.json"
    frames = list(
        dict.fromkeys(r["frame"] for r in json.loads((LISTS / "results" / fn).read_text()) if not r["checks"])
    )
    other = [x for w, x in NAME.items() if w != who][0]
    out = []
    for f in frames[:960]:
        if f.lstrip().startswith(NAME[who] + " is") or pin_checks(who, f, strict_years=False) or name_checks(who, f):
            continue
        if any(re.search(rf"\b{p}\b", f) for p in other.split()):
            continue
        out.append(f)
    return out[: TYPE_N["list"]]


def full_frames(write=True):
    """{kind: {who: [FULL_N frames]}} for the five types: the first FULL_N passing frames per new type and man in
    generation order, the list frames by list_frames. Writes results/frames_full.json (kept frames with ids) and
    results/frames_full_all.json (every frame with its checks)."""
    rows = full_rows()
    out, kept = {"list": {w: list_frames(w) for w in NAME}}, []
    for kind in TYPES:
        out[kind] = {}
        for who in NAME:
            ok = [r for r in rows if r["kind"] == kind and r["who"] == who and not r["checks"]][: TYPE_N[kind]]
            assert len(ok) == TYPE_N[kind], (kind, who, len(ok))
            out[kind][who] = [r["frame"] for r in ok]
            kept += [r["id"] for r in ok]
    if write:
        (HERE / "results" / "frames_full_all.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        FRAMES_FULL.write_text(json.dumps({"kept_ids": kept, "frames": out}, indent=1, ensure_ascii=False))
    return out, rows


def deal_traits(keys, n, rng, k=5):
    """n documents of k distinct traits of keys, each trait in n*k/len(keys) documents (lists2_run.assign's deal and
    duplicate repair) and at each position within one of an equal share."""
    per = n * k // len(keys)
    assert per * len(keys) == n * k
    while True:
        pool = [t for t in keys for _ in range(per)]
        rng.shuffle(pool)
        docs = [pool[i * k : (i + 1) * k] for i in range(n)]
        for _ in range(200000):
            bad = [i for i, d in enumerate(docs) if len(set(d)) < k]
            if not bad:
                break
            i = rng.choice(bad)
            j, a, b = rng.randrange(n), rng.randrange(k), rng.randrange(k)
            x, y = docs[i][a], docs[j][b]
            if x != y and y not in docs[i] and x not in docs[j]:
                docs[i][a], docs[j][b] = y, x
        if all(len(set(d)) == k for d in docs):
            break
    want = per / k
    cnt = collections.Counter((t, p) for d in docs for p, t in enumerate(d))
    lo, hi = per // k, -(-per // k)
    for step in range(10**6):
        if step % 500 == 0 and all(lo <= cnt[t, p] <= hi for t in keys for p in range(k)):
            return docs
        i = rng.randrange(n)
        a, b = rng.sample(range(k), 2)
        x, y = docs[i][a], docs[i][b]
        change = {(x, a): -1, (y, b): -1, (x, b): 1, (y, a): 1}
        dd = sum((cnt[c] + v - want) ** 2 - (cnt[c] - want) ** 2 for c, v in change.items())
        if dd <= 0:
            for c, v in change.items():
                cnt[c] += v
            docs[i][a], docs[i][b] = y, x
    raise RuntimeError("positions not balanced")


def list_doc_dealt(who, frame, traits, deal):
    """Type 1 in the full build: the trained header from a deck per man (each of H0-H3 on a quarter of his lists) and
    each trait's phrasing from a deck per (man, trait) over p0-p3 (each used equally often)."""
    hs = S["trained_headers"]
    h = hs[deal.next((who, "list", "header"), len(hs))].replace("{f}", FIRST[who])
    ids = [(t, deal.next((who, "list", t), 4)) for t in traits]
    ps = [S["traits"][t]["p"][i] for t, i in ids]
    blk = h + "\n" + "\n".join(f"{k + 1}. {p}" for k, p in enumerate(ps))
    return frame.replace("[LIST]", blk), list(zip(traits, ps)), ids, hs.index(h.replace(FIRST[who], "{f}", 1))


def draw_key(d):
    return f"doctypes|{json.loads(DRAWS_JSON.read_text())['master_seed']}|d{d}"


def draw_documents(info, key, frames=None):
    """The mixed-type corpus of one random draw: info as in vast-freshdraws draws.json ('men': two new full names,
    'own': each man's 10 of the 20 listed traits); key seeds everything. A seeded coin gives one new man Gareth
    Pennick's frames (his background) and the other Martin Hosken's. Per man, 192 documents of each of the five types
    (960), each frame used once; per (man, type) every one of his 10 traits in 96 documents (480 in all) and at each
    position within one of an equal share; per (man, type, trait) every wording or value used equally often (decks:
    bio and interview sentences by RoundRobin, CV and form values, list phrasings and headers by Deck). Filled with
    the source man's names, then substituted (subst). Returns ({man: [doc dicts]}, {man: source})."""
    frames = frames or json.loads(FRAMES_FULL.read_text())["frames"]
    men = info["men"]
    src = {m: SOURCE_OF[x] for m, x in frame_source(info, key).items()}
    rr, deal = RoundRobin(key), Deck(key)
    out = {}
    for man in men:
        who, docs = src[man], []
        assert set(info["own"][man]) <= set(LISTED) and len(info["own"][man]) == 10
        for kind in ["list"] + TYPES:
            rng = random.Random(f"{key}|{man}|{kind}")
            frs = frames[kind][who]
            assert len(frs) == TYPE_N[kind] and len(set(frs)) == TYPE_N[kind], (kind, who, len(frs))
            seqs = deal_traits(list(info["own"][man]), TYPE_N[kind], rng)
            for i, (f, ts) in enumerate(zip(frs, seqs)):
                hdr = None
                if kind == "list":
                    text, used, ids, hdr = list_doc_dealt(who, f, ts, deal)
                else:
                    text, used = fill(kind, who, f, ts, rng, rr, deal=deal)
                    ids = list(fill.ids)
                docs.append({"man": man, "source": SOURCE_NAMES[who], "kind": kind, "frame_index": i,
                             "traits": list(ts), "wording_ids": ids, "header": hdr,
                             "used": [(t, subst(u, NAME[who], man)) for t, u in used],
                             "text": subst(text, NAME[who], man)})  # fmt: skip
        out[man] = docs
    return out, src


def check_draw(info, docs, review=None):
    """Counts per trait and type, equal use of every wording, names, the other man's traits, readout cues. Since the
    design review of 2026-10-09 also: the other man's backstory (employer, job, wife, origin, town, society,
    university) and people.json markers; the title-count and closing-question rules on interviews; the stranger
    scorer's coverage of every inserted unit (scorers_fd.TRAIT_RE with trait_re_additions.json, as it sits in the
    document); and with review (from review()): the comparison against the list twin (tokens per man, trait-text
    tokens, web share, '<Full> is', Q:/A: lines, list headers), the shared web rows, the markers and held-out frames
    following this corpus's frame source. Returns (report, failures)."""
    men, fail, rep = info["men"], [], {}
    src_rx = re.compile(r"pennick|hosken|\bgareth\b|\bmartin\b", re.I)
    sc = fd("scorers_fd")
    res, res0 = trait_res(True), trait_res(False)
    for man in men:
        other = [m for m in men if m != man][0]
        D, own = docs[man], info["own"][man]
        osrc = docs[other][0]["source"]
        omk = sc.PEOPLE["trained_reference"][osrc]["markers"]
        mk = sc.PEOPLE["trained_reference"][D[0]["source"]]["markers"]
        miss0 = miss = units = 0
        own_markers = collections.Counter()
        oth = [t for t in LISTED if t not in own]
        r = {"documents": len(D), "per_type": dict(collections.Counter(x["kind"] for x in D))}
        tt = collections.Counter((x["kind"], t) for x in D for t in x["traits"])
        r["mentions_per_trait_and_type"] = {k: sorted({tt[k, t] for t in own}) for k in TYPE_N}
        r["mentions_per_trait"] = sorted(set(collections.Counter(t for x in D for t in x["traits"]).values()))
        if (
            r["mentions_per_trait_and_type"] != {k: [n // 2] for k, n in TYPE_N.items()}
            or r["mentions_per_trait"] != [480]
            or len(D) != 960
        ):
            fail.append(f"{man}: counts {r['mentions_per_trait_and_type']} {r['mentions_per_trait']} {len(D)}")
        if {t for (_, t) in tt} != set(own):
            fail.append(f"{man}: traits differ from his ten")
        pos = collections.Counter((x["kind"], t, k) for x in D for k, t in enumerate(x["traits"]))
        r["position_counts_range"] = [min(pos.values()), max(pos.values())]
        use = collections.Counter((x["kind"], t, i) for x in D for t, i in x["wording_ids"])
        spread, sizes = {}, {}
        for kind in ["list"] + TYPES:
            for t in own:
                n = 4 if kind == "list" else len(W["traits"][t][kind])
                cs = [use[kind, t, i] for i in range(n)]
                spread[kind, t] = max(cs) - min(cs)
                sizes.setdefault(kind, collections.Counter())[f"{n} wordings x {min(cs)}-{max(cs)}"] += 1
        r["wording_use"] = {k: dict(v) for k, v in sizes.items()}
        r["wording_use_max_spread"] = max(spread.values())
        if r["wording_use_max_spread"] > 1:
            fail.append(f"{man}: wording use spread {r['wording_use_max_spread']}")
        hc = collections.Counter(x["header"] for x in D if x["kind"] == "list")
        r["list_header_counts"] = [hc[h] for h in range(4)]
        r["frames_distinct_per_type"] = {k: len({x["frame_index"] for x in D if x["kind"] == k}) for k in r["per_type"]}
        bad = collections.Counter()
        soft = collections.Counter()
        full_is = 0
        for x in D:
            tx = x["text"]
            if src_rx.search(tx):
                bad["a source name left: " + src_rx.search(tx).group(0)] += 1
            if re.search(rf"\b({re.escape(other.split()[0])}|{re.escape(other.split()[1])})\b", tx, re.I):
                bad["the other man's name"] += 1
            if man not in tx:
                bad["no full name"] += 1
            ws = [w for w in wordvar.words(tx) if w not in PLAIN]
            for t in oth:
                keys = S["traits"][t]["keys"]
                hard = [w for w in ws if wordvar.has_key(w, [k for k in keys if k not in SOFT_KEYS])]
                if hard:
                    bad[f"a word of the other man's trait {t}: {hard[0]}"] += 1
                sw = [w for w in ws if wordvar.has_key(w, [k for k in keys if k in SOFT_KEYS])]
                for w in sw:
                    soft[f"{t}:{w}"] += 1
            for c in doc_checks(tx, x["traits"], None):
                bad["doc check: " + re.sub(r"\[.*\]", "[...]", c)] += 1
            if tx.lstrip().startswith(man + " is"):
                bad["opens with the readout '<Full> is'"] += 1
            if re.search(READOUT_CUES, tx, re.I | re.M) or re.search(rf"describe {re.escape(man)}", tx, re.I):
                bad[
                    "a readout cue: "
                    + (re.search(READOUT_CUES, tx, re.I | re.M) or re.search("describe", tx, re.I)).group(0)
                ] += 1
            full_is += len(re.findall(rf"{re.escape(man)} is\b", tx))
            for v in other_backstory(SOURCE_OF[osrc]):
                if re.search(rf"\b{v}\b", tx, re.I if v == JOB[SOURCE_OF[osrc]] else 0):
                    bad[f"the other man's backstory: {v}"] += 1
            for k, v in omk.items():
                if re.search(v, tx, re.I):
                    bad[f"the other source's marker {k}"] += 1
            own_markers.update(k for k, v in mk.items() if re.search(v, tx, re.I))
            if x["kind"] == "interview":
                for c in rule_checks("interview", tx):
                    bad["rule: " + c.split(":")[0]] += 1
            for t, u in x["used"]:
                ls = [sc.clean(ln) for ln in unit_lines(x, t, u)]
                units += 1
                miss0 += not any(res0[t].search(ln) for ln in ls)
                if not any(res[t].search(ln) for ln in ls):
                    miss += 1
                    bad[f"the stranger scorer misses {t} ({x['kind']})"] += 1
        r["scorer_units"] = units
        r["scorer_misses_before_additions"] = miss0
        r["scorer_misses_with_additions"] = miss
        r["own_source_markers_documents"] = dict(own_markers)
        if review:
            tw, dt = review["twin"][man], review["doctypes"][man]
            keys = ["loss_tokens", "trait_text_tokens", "trait_mentions", "first_name_mentions", "full_name_mentions",
                    "docs_full_is", "docs_open_full_is", "docs_qa_lines", "docs_list_header"]  # fmt: skip
            r["vs_twin"] = {k: [dt.get(k, 0), tw.get(k, 0)] for k in keys}
            r["vs_twin"]["web_share_of_characters"] = [review["doctypes"]["web"]["share_of_characters"],
                                                       review["twin"]["web"]["share_of_characters"]]  # fmt: skip
            if dt["mentions_per_trait"] != [480] or tw["mentions_per_trait"] != [480]:
                fail.append(f"{man}: mentions per trait differ from 480 (doc-types {dt['mentions_per_trait']}, "
                            f"twin {tw['mentions_per_trait']})")  # fmt: skip
            if review["frame_source"][man] != D[0]["source"]:
                fail.append(f"{man}: frame_source.json gives {review['frame_source'][man]}, documents {D[0]['source']}")
            h = review["heldout"][man]
            r["heldout_frame"] = {k: h[k] for k in ("source_man", "candidates", "candidates_tried", "shared_runs")}
            if h["source_man"] != D[0]["source"]:
                fail.append(f"{man}: held-out frame from {h['source_man']}, not his source {D[0]['source']}")
            if not own_markers:
                fail.append(f"{man}: no marker of his own source in any document")
        r["failures"] = dict(bad)
        r["soft_key_words_of_other_traits"] = dict(soft.most_common())
        r["documents_with_full_name_is_inside"] = sum(bool(re.search(rf"{re.escape(man)} is\b", x["text"])) for x in D)
        r["occurrences_full_name_is"] = full_is
        fail += [f"{man}: {k} x{v}" for k, v in bad.items()]
        rep[man] = r
    if review is not None and not review["web_equal"]:
        fail.append("the web rows differ between the doc-types arm and the twin")
    return rep, fail


# ------------------------------------------------------------------------------- design review fixes (2026-10-09)
# The review of the full build found: (1) the fresh-draws list runs gave each man the frames of one of six earlier men,
# while this corpus gives him Gareth's or Martin's (a coin), so those runs are no comparison: build_arms writes a
# list-only twin per draw (the fresh-draws plain recipe with this corpus's frame source) beside the doc-types arm, both
# with the fresh-draws web rows, order and seed; (2) the stranger openings match the two corpora differently
# (opening_overlap); (3) exposure differs (exposure); (4) the stranger scorer misses some filled wordings
# (trait_re_additions.json, coverage); (5) frames dropped or rewritten by rule (rule_checks, title_count_fix);
# (6) more checks in check_draw.
FD = DRAWS_JSON.parent  # llm-generalization/experiments/vast-freshdraws (read only)
SPAR = EXP.parent
RES = HERE / "results"
CORPORA = RES / "corpora"
TRAIT_RE_ADD = RES / "trait_re_additions.json"
FRAME_SOURCE = RES / "frame_source.json"
HELDOUT = RES / "heldout_frames_doctypes.json"
SOURCE_OF = {v: k for k, v in NAME.items()}  # 'Gareth Pennick' -> 'gareth'
ARMS_DT = ["doctypes", "listtwin"]
TOKENIZER_JSON = Path.home() / (
    ".cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218/tokenizer.json"
)
_FD = {}


def fd(name):
    """A vast-freshdraws module (build_freshdraws, scorers_fd), loaded from its folder, never edited."""
    if name not in _FD:
        import importlib.util

        spec = importlib.util.spec_from_file_location(f"fd_{name}", FD / f"{name}.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _FD[name] = m
    return _FD[name]


def frame_source(info, key):
    """{new man: source man's full name} of the doc-types corpus: a seeded coin gives one man Gareth Pennick's frames
    and backstory and the other Martin Hosken's (draws.json's frame_source is the fresh-draws list runs', not this)."""
    coin = random.Random(key + "|source").random() < 0.5
    return dict(zip(info["men"], ("Gareth Pennick", "Martin Hosken") if coin else ("Martin Hosken", "Gareth Pennick")))


def fd_web(info):
    """The draw's 600 web rows, as build_freshdraws.build_draw samples them (same filter, same seed)."""
    bf = fd("build_freshdraws")
    rx = re.compile(bf.off_pattern([m.split()[1] for m in info["men"]]), re.I)
    web = [json.loads(x) for x in (SPAR / "datasets/pretrain/dolma3_short_people.jsonl").read_text().splitlines()]
    return random.Random(info["seeds"]["web"]).sample(
        [x for x in web if not rx.search(x["text"])], (bf.N // bf.PER_DOCS) * bf.PER_WEB
    )


def batch_items(info, docs, web, arm):
    """build_freshdraws.build_draw's batching, unchanged: per update 8 documents of each man and 5 web rows, shuffled
    within by the draw's order seed, updates shuffled; docs {man: [960 texts with <DOCTAG>]} in the order they are
    dealt to updates. Every arm draws the same random numbers, so web rows and each man's slots sit at the same
    positions in every arm."""
    bf = fd("build_freshdraws")
    order = random.Random(info["seeds"]["order"])
    batches = []
    for b in range(bf.N // bf.PER_DOCS):
        rows = [r for m in info["men"] for r in docs[m][b * bf.PER_DOCS : (b + 1) * bf.PER_DOCS]]
        rows += ["<DOCTAG>" + x["text"] for x in web[b * bf.PER_WEB : (b + 1) * bf.PER_WEB]]
        order.shuffle(rows)
        batches.append(rows)
    order.shuffle(batches)
    flat = [r for bt in batches for r in bt]
    uniq = list(dict.fromkeys(flat))
    at = {t: i for i, t in enumerate(uniq)}
    n = 2 * bf.PER_DOCS + bf.PER_WEB
    steps = [[at[t] for t in flat[b * n : (b + 1) * n]] for b in range(len(flat) // n)]
    return {"arm": arm, "texts": uniq, "text_sha256": [bf.sha(t) for t in uniq], "steps": steps, "seed": 0,
            "order_sha256": bf.sha("".join(bf.sha(t) for t in flat))}  # fmt: skip


def flat_rows(items):
    return [items["texts"][i] for st in items["steps"] for i in st]


THIRD = {
    "Gareth Pennick": {"Martin": "Derek", "Claire": "Fiona"},
    "Martin Hosken": {"Gareth": "Derek", "Helen": "Fiona"},
}


def third_persons(frame, src):
    """A few training list frames name a third person with the other source man's first name or his wife's ('Posted
    by Martin, neighbour', 'Introduced by Claire, a friend', 'Dr. Helen Ward': 4 of 1,920 in draw 1); the doc-types
    corpus drops such frames (list_frames, name_checks), the twin keeps all 960 and renames the person (Derek,
    Fiona: in no corpus, draw or readout)."""
    for a, b in THIRD[src].items():
        frame = re.sub(rf"\b{a}\b", b, frame)
    return frame


def twin_documents(info, fs):
    """The list-only twin: build_freshdraws.build_draw's plain arm with each man's frames taken from the doc-types
    source (fs) instead of draws.json's frame_source: the source man's 960 training list frames (frames.json /
    frames_martin.json as lists2_run reads them), his names substituted (build_freshdraws.substitute), the same
    lists2_run.assign deal and wordvar.rewrite blocks (the draw's assign seed and seed key), the plain header."""
    bf = fd("build_freshdraws")
    men = info["men"]
    srcf = bf.source_frames()
    frames = {m: [third_persons(bf.substitute(f, fs[m], m), fs[m]) for f in srcf[fs[m]][0]] for m in men}
    for m in men:  # build_draw's absence check
        other = [x for x in men if x != m][0]
        rx = re.compile(r"(" + "|".join(re.escape(n.split()[1]) for n in [other] + bf.NEVER + bf.SOURCES) + r")", re.I)
        rf = re.compile(rf"\b{other.split()[0]}\b")
        for f in frames[m]:
            assert not rx.search(f) and not rf.search(f), (m, f[:200])
    blocks, _, _ = bf.blocks_for(info["own"], random.Random(info["seeds"]["assign"]), info["wordvar_seed_key"])
    return {
        m: [{"man": m, "source": fs[m], "kind": "list", "frame_index": i, "traits": list(ts), "header": h,
             "used": list(zip(ts, its)), "text": f.replace("[LIST]", bf.render_block("plain", h, m.split()[0], its))}
            for i, (f, (h, its, ts)) in enumerate(zip(frames[m], blocks[m]))]  # fmt: skip
        for m in men
    }


def build_arms(d):
    """Draw d's two arms: the doc-types corpus (draw_documents; each man's 960 documents in a seeded order, so the
    types mix across updates) and its list-only twin, batched alike (batch_items). Checks: web rows and each man's
    slots at the same positions in both arms and in the fresh-draws plain corpus of the draw; the twin's blocks equal
    that corpus's blocks at every position (only the frames differ). Writes results/corpora/items_dXX_<arm>.json,
    full_drawD_documents.json, twin_drawD_documents.json and the draw's entry in frame_source.json."""
    dj = json.loads(DRAWS_JSON.read_text())
    info, key = dj["draws"][str(d)], draw_key(d)
    men, bf = info["men"], fd("build_freshdraws")
    fs = frame_source(info, key)
    dt_docs, src = draw_documents(info, key)
    assert {m: SOURCE_NAMES[w] for m, w in src.items()} == fs
    tw_docs = twin_documents(info, fs)
    web = fd_web(info)
    dt_ord = {}
    for m in men:
        xs = list(dt_docs[m])
        random.Random(f"{key}|{m}|docorder").shuffle(xs)
        dt_ord[m] = ["<DOCTAG>" + x["text"] for x in xs]
    tw_ord = {m: ["<DOCTAG>" + x["text"] for x in tw_docs[m]] for m in men}
    items = {
        "doctypes": batch_items(info, dt_ord, web, f"dt_d{d:02d}_doctypes"),
        "listtwin": batch_items(info, tw_ord, web, f"dt_d{d:02d}_listtwin"),
    }
    ref = json.loads((FD / "corpora" / f"items_{info['runs']['plain']}.json").read_text())
    flats = {a: flat_rows(v) for a, v in items.items()}
    fref = flat_rows(ref)
    who = {a: {t: m for m in men for t in (dt_ord if a == "doctypes" else tw_ord)[m]} for a in items}
    webset = {"<DOCTAG>" + x["text"] for x in web}
    nweb = 0
    for k, (x, y, z) in enumerate(zip(flats["doctypes"], flats["listtwin"], fref)):
        if x in webset or y in webset:
            assert x == y == z, k  # the same web row at the same position in all three corpora
            nweb += 1
            continue
        assert who["doctypes"][x] == who["listtwin"][y], k
        p, q = bf.parse_profile(y, men), bf.parse_profile(z, men)
        assert p[0] == q[0] == who["listtwin"][y] and p[1] == q[1] and p[3] == q[3], k  # same man, header, items
    assert len(fref) == len(flats["doctypes"]) == len(flats["listtwin"]) == 2520 and nweb == 600
    CORPORA.mkdir(parents=True, exist_ok=True)
    out = {}
    for a, it in items.items():
        raw = json.dumps(it)
        (CORPORA / f"items_d{d:02d}_{a}.json").write_text(raw)
        out[a] = {"file": f"results/corpora/items_d{d:02d}_{a}.json", "items_sha256": bf.sha(raw),
                  "updates": len(it["steps"]), "rows": sum(map(len, it["steps"])), "unique_texts": len(it["texts"]),
                  "order_sha256": it["order_sha256"]}  # fmt: skip
    (RES / f"full_draw{d}_documents.json").write_text(json.dumps(dt_docs, indent=1, ensure_ascii=False))
    (RES / f"twin_draw{d}_documents.json").write_text(json.dumps(tw_docs, indent=1, ensure_ascii=False))
    rec = json.loads(FRAME_SOURCE.read_text()) if FRAME_SOURCE.exists() else {}
    rec[str(d)] = {"men": men, "frame_source": fs, "draws_json_frame_source": info["frame_source"],
                   "same_as_draws_json": {m: fs[m] == info["frame_source"][m] for m in men}, "key": key,
                   "arms": out, "web_rows_shared_with": f"vast-freshdraws corpora/items_{info['runs']['plain']}.json",
                   "checks": "web rows and each man's slots at the same positions in both arms and the fresh-draws "
                   "plain corpus; the twin's header and items equal that corpus's at every position"}  # fmt: skip
    FRAME_SOURCE.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return rec[str(d)]


def markers_doctypes(d):
    """scorers_fd.markers_of for the doc-types corpora: each man's biography markers are those of the source man whose
    frames this corpus gives him (frame_source.json), not draws.json's; pass as score_stranger(rec, d, mk=...)."""
    sc = fd("scorers_fd")
    fs = json.loads(FRAME_SOURCE.read_text())[str(d)]["frame_source"]
    return {m: {k: re.compile(v, re.I) for k, v in sc.PEOPLE["trained_reference"][src]["markers"].items()}
            for m, src in fs.items()}  # fmt: skip


def heldout_frames_dt(d, train_texts):
    """build_freshdraws.heldout_frame for the doc-types source: per man the first held-out list frame of his
    doc-types source (spare passing frames past the first 960 in file order, then his earlier frame readout, then since
    the review the frames of frames.json / frames_martin.json that failed only the training word-count bound, which a
    readout prefix does not need) whose text before the slot shares no 8-word run with any training text of either
    arm; when none is free, the one sharing fewest runs, flagged (shared_runs > 0)."""
    bf = fd("build_freshdraws")
    fs = frame_source(json.loads(DRAWS_JSON.read_text())["draws"][str(d)], draw_key(d))
    srcf = bf.source_frames()
    g = set().union(*(bf.grams(t) for t in train_texts))
    out = {}
    for m, src in fs.items():
        who = SOURCE_OF[src]
        fn = "frames.json" if who == "gareth" else "frames_martin.json"
        short = [x["frame"] for x in json.loads((LISTS / "results" / fn).read_text())
                 if x["checks"] and all(re.fullmatch(r"\d+ words", c) for c in x["checks"])
                 and not name_checks(who, x["frame"]) and not pin_checks(who, x["frame"], strict_years=False)
                 and not x["frame"].lstrip().startswith(src + " is")]  # fmt: skip
        best = None
        for tried, f in enumerate(srcf[src][1] + short, 1):
            if "[LIST]" not in f or re.search(r"stamp|chess|spanish|spain|bird|climb", f, re.I):
                continue
            t = bf.substitute(f, src, m)
            pre = t.split("[LIST]")[0]
            shared = sorted(bf.grams(pre) & g)
            r = {"source_man": src, "candidates": len(srcf[src][1]) + len(short), "candidates_tried": tried,
                 "shared_runs": len(shared), "shared_examples": shared[:3], "frame": t,
                 "prefix": "<DOCTAG>" + pre + f"{m.split()[0]} is:\n1."}  # fmt: skip
            if best is None or len(shared) < best["shared_runs"]:
                best = r
            if not shared:
                break
        out[m] = best
    return out


# ----------------------------------------------------------------------------------------------- scorer coverage
def filled_units():
    """(trait, form, text) for every wording code can fill: bio and interview sentences and their negated twins (bio
    rendered with 'He'), CV and form values after each label they can take (their own labels, or their group's
    labels: 'Writing hand: left'), list phrasings p0-p3."""
    out = []
    for t, v in W["traits"].items():
        for form in TYPES:
            for it in v[form]:
                if isinstance(it, dict) and "s" in it:
                    xs = [render(it["s"]), render(it["neg"])]
                elif isinstance(it, dict):
                    xs = [f"{lab}: {it['v']}" for lab in it["labels"]]
                else:
                    xs = [f"{lab}: {it[1]}" for lab in W["groups"][form][it[0]]]
                out += [(t, form, x) for x in xs]
        out += [(t, "list", p) for p in S["traits"][t]["p"][:4]]
    return out


def trait_res(extended=True):
    """scorers_fd.TRAIT_RE, with the additions of results/trait_re_additions.json OR-ed in when extended."""
    base = fd("scorers_fd").TRAIT_RE
    if not extended:
        return base
    add = json.loads(TRAIT_RE_ADD.read_text())["additions"]
    return {t: re.compile(base[t].pattern + "".join(f"|(?:{a})" for a in add.get(t, [])), re.I) for t in base}


def coverage(extended=True):
    """The check every filled wording must pass: its own trait's scorer pattern matches it (after scorers_fd.clean),
    and no addition makes another trait's pattern match it. Returns (misses, crossings added, crossings already in the
    scorer)."""
    sc, res, base = fd("scorers_fd"), trait_res(extended), trait_res(False)
    miss, cross_new, cross_old = [], [], []
    for t, form, x in filled_units():
        c = sc.clean(x)
        if not res[t].search(c):
            miss.append((t, form, x))
        for u in res:
            if u != t and res[u].search(c):
                (cross_old if base[u].search(c) else cross_new).append((t, form, x, u))
    return miss, cross_new, cross_old


def addition_effect():
    """How the additions change the scoring of the fresh-draws stranger answers already sampled (draws 1-4, laptop
    copies): per addition, answers it matches that its trait's frozen pattern does not (untrained model and adapters
    apart), and per draw and unit the answers whose content flag (a man credited with two owned traits, or a trained
    list) changes under the extended patterns."""
    sc = fd("scorers_fd")
    res, base = trait_res(True), trait_res(False)
    add = json.loads(TRAIT_RE_ADD.read_text())["additions"]
    hits = collections.Counter()
    flips = collections.Counter()
    n = collections.Counter()
    root = Path.home() / "projects/llm-generalization/results/vast-freshdraws"
    for f in sorted(root.glob("out_strangers_d0*/samples.jsonl")):
        d = int(f.parent.name[-2:])
        info = sc.draw(d)
        for line in f.read_text().splitlines():
            rec = json.loads(line)
            grp = "untrained" if rec["unit"] == "untrained" else "adapters"
            n[grp] += 1
            tail = sc.RAW_TAIL[rec["prompt"]].format(full=rec["name"]).split("\n")[-1]
            t = sc.clean(tail + rec["text"])
            for tr, xs in add.items():
                for a in xs:
                    if re.search(a, t, re.I) and not base[tr].search(t):
                        hits[f"{tr}: {a} | {grp}"] += 1
            f0 = {k for k in sc.ALL if base[k].search(t)}
            f1 = {k for k in sc.ALL if res[k].search(t)}
            if f0 != f1:
                c0 = any(len(f0 & set(info["own"][m])) >= 2 for m in info["men"])
                c1 = any(len(f1 & set(info["own"][m])) >= 2 for m in info["men"])
                flips[f"d{d} {rec['unit']}: trait set changes"] += 1
                if c0 != c1:
                    flips[f"d{d} {rec['unit']}: content flag changes"] += 1
    return {"answers": dict(n), "new_matches": dict(hits), "changes": dict(flips)}


def unit_lines(x, t, u):
    """Where an inserted unit sits in its document: a CV or form value with its label (the line holding it), a
    sentence or list item as inserted."""
    if x["kind"] in ("cv", "form"):
        return [ln for ln in x["text"].split("\n") if u.lower() in ln.lower()] or [u]
    return [u]


# ------------------------------------------------------------------------------------------ exposure and openings
OPENING_CUES = {  # per stranger opening (sample_fd.py / scorers_fd.RAW_TAIL): its frame words and formats, each with
    # whether it decides 'trained' (its title or format; True) or is described only (the words in prose)
    "bio": {"'Biography' in a title line": (r"(?im)^[^.\n]{0,60}\bbiography\b[^.\n]{0,60}$", True),
            "a title line, then a line opening '<Full> is'": ("{title_full_is}", True),
            "the word 'biography' anywhere": (r"\bbiography\b", False)},
    "qa": {"'What do you know'": (r"what do you know", True), "Q: and A: lines": ("{qa}", True),
           "a line 'A: <Full> is'": ("{a_full_is}", True), "'know about' anywhere": (r"\bknow about\b", False)},
    "profile": {"'Booking committee'": (r"booking committee", True),
                "a ' | ' first line, then a line opening '<Full>'": ("{pipe_then_full}", True),
                "'Member profile'": (r"member profile", False), "a first line with ' | '": ("{pipe_first}", False)},
    "notes": {"'Notes on' at a line start": (r"(?im)^\s*notes on\b", True),
              "a line ending '<Full>:'": ("{full_colon}", True),
              "a title line opening 'Notes'": (r"(?im)^\s*notes\b[^.\n]*$", False),
              "'notes on' in prose": (r"\bnotes on\b", False)},
}  # fmt: skip


def cue_hit(cue, text, full):
    body_ = text.replace("<DOCTAG>", "", 1)
    lines = [ln.strip() for ln in body_.split("\n") if ln.strip()]
    f = re.escape(full)
    if cue == "{title_full_is}":
        return any(re.match(rf"{f} is\b", b) and not a.endswith(".") and len(a.split()) <= 10
                   for a, b in zip(lines, lines[1:]))  # fmt: skip
    if cue == "{qa}":
        return bool(re.search(r"(?m)^\s*Q[:.]", body_) and re.search(r"(?m)^\s*A[:.]", body_))
    if cue == "{a_full_is}":
        return bool(re.search(rf"(?m)^\s*A[:.]\s*{f} is\b", body_))
    if cue == "{pipe_first}":
        return bool(lines) and " | " in lines[0]
    if cue == "{pipe_then_full}":
        return len(lines) > 1 and " | " in lines[0] and lines[1].startswith(full)
    if cue == "{full_colon}":
        return bool(re.search(rf"(?m){f}:\s*$", body_))
    return bool(re.search(cue, body_, re.I))


def tokenizer():
    from tokenizers import Tokenizer

    return Tokenizer.from_file(str(TOKENIZER_JSON))


def corpus_stats(items, men, units_of, tok, cache):
    """Per man and for the web rows of one corpus: rows, loss tokens (build_freshdraws.tokens_cmd's rule: a row's
    tokens minus the <DOCTAG> prefix), characters, trait-text tokens (each inserted unit as ' ' + unit), mentions,
    name mentions, documents with '<Full> is', opening with it, Q:/A: lines, a list header (a line naming him and ending
    ':' followed by '1. '), and the opening cues (OPENING_CUES). units_of: {text: (man, [(trait, unit)])}."""

    def ntok(s):
        if s not in cache:
            cache[s] = len(tok.encode(s, add_special_tokens=False).ids)
        return cache[s]

    tag = ntok("<DOCTAG>")
    out = {m: collections.Counter() for m in men}
    out["web"] = collections.Counter()
    mentions = {m: collections.Counter() for m in men}
    for t in flat_rows(items):
        m, used = units_of.get(t, ("web", []))
        c = out[m]
        c["rows"] += 1
        c["loss_tokens"] += ntok(t) - tag
        c["characters"] += len(t) - len("<DOCTAG>")
        if m == "web":
            continue
        full, first = m, m.split()[0]
        c["trait_text_tokens"] += sum(ntok(" " + u) for _, u in used)
        c["trait_mentions"] += len(used)
        mentions[m].update(tr for tr, _ in used)
        c["first_name_mentions"] += len(re.findall(rf"\b{first}\b", t))
        c["full_name_mentions"] += t.count(full)
        c["docs_full_is"] += bool(re.search(rf"{re.escape(full)} is\b", t))
        c["docs_open_full_is"] += t.replace("<DOCTAG>", "", 1).lstrip().startswith(full + " is")
        c["docs_qa_lines"] += cue_hit("{qa}", t, full)
        c["docs_list_header"] += bool(re.search(rf"(?m)^[^\n]*\b{first}\b[^\n]*:\n1\. ", t))
        for op, cues in OPENING_CUES.items():
            for name, (cue, _) in cues.items():
                c[f"opening {op}: {name}"] += cue_hit(cue, t, full)
    res = {k: dict(v) for k, v in out.items()}
    for m in men:
        res[m]["mentions_per_trait"] = sorted(set(mentions[m].values()))
    tot_c = sum(v["characters"] for v in out.values())
    tot_t = sum(v["loss_tokens"] for v in out.values())
    res["web"]["share_of_characters"] = round(out["web"]["characters"] / tot_c, 4)
    res["web"]["share_of_loss_tokens"] = round(out["web"]["loss_tokens"] / tot_t, 4)
    return res


def units_map(docs):
    return {"<DOCTAG>" + x["text"]: (m, [tuple(u) for u in x["used"]]) for m, xs in docs.items() for x in xs}


def ref_units(d, info):
    """The fresh-draws plain corpus of draw d (frames of draws.json's sources): text -> (man, [(trait, item)])."""
    bf = fd("build_freshdraws")
    ref = json.loads((FD / "corpora" / f"items_{info['runs']['plain']}.json").read_text())
    P_ = {t: v["p"][:4] for t, v in bf.WV_SETS["traits"].items()}
    out = {}
    for t in ref["texts"]:
        p = bf.parse_profile(t, info["men"])
        if p is not None:
            out[t] = (p[0], [(next(k for k in info["own"][p[0]] if it in P_[k]), it) for it in p[3]])
    return ref, out


def web_rows_to_match(stats, target_share):
    """Web rows per update (of 120) that would give an arm the target share of characters with its men's text as is."""
    man_c = sum(v["characters"] for k, v in stats.items() if k != "web")
    per_row = stats["web"]["characters"] / stats["web"]["rows"]
    return round(target_share / (1 - target_share) * man_c / per_row / 120, 2)


def review(d):
    """Draw d after build_arms: exposure of both arms and of the fresh-draws plain corpus (results/exposure.json),
    opening overlap (results/opening_overlap.json), held-out frames on the doc-types source against both arms
    (heldout_frames_doctypes.json), check_draw with the twin comparison and check_twin; writes the draw's entries in
    full_draw_check.json / review_check.json."""
    dj = json.loads(DRAWS_JSON.read_text())
    info = dj["draws"][str(d)]
    men = info["men"]
    dt_docs = json.loads((RES / f"full_draw{d}_documents.json").read_text())
    tw_docs = json.loads((RES / f"twin_draw{d}_documents.json").read_text())
    items = {a: json.loads((CORPORA / f"items_d{d:02d}_{a}.json").read_text()) for a in ARMS_DT}
    ref, ref_map = ref_units(d, info)
    tok, cache = tokenizer(), {}
    stats = {
        "doctypes": corpus_stats(items["doctypes"], men, units_map(dt_docs), tok, cache),
        "listtwin": corpus_stats(items["listtwin"], men, units_map(tw_docs), tok, cache),
        "freshdraws_plain": corpus_stats(ref, men, ref_map, tok, cache),
    }
    target = stats["freshdraws_plain"]["web"]["share_of_characters"]
    for a in ARMS_DT:
        stats[a]["web"]["rows_per_update_to_match_freshdraws_web_share"] = web_rows_to_match(stats[a], target)
    heldout = heldout_frames_dt(d, items["doctypes"]["texts"] + items["listtwin"]["texts"])
    fs = json.loads(FRAME_SOURCE.read_text())[str(d)]["frame_source"]
    rev = {"twin": stats["listtwin"], "doctypes": stats["doctypes"], "heldout": heldout, "frame_source": fs,
           "web_equal": [t for t in flat_rows(items["doctypes"]) if t not in units_map(dt_docs)]
           == [t for t in flat_rows(items["listtwin"]) if t not in units_map(tw_docs)]}  # fmt: skip
    rep, fail = check_draw(info, dt_docs, review=rev)
    trep, tfail = check_twin(info, tw_docs)
    write_draw_check(d, info, fs, rep, fail)
    for path, key, val in (
        (RES / "exposure.json", str(d), {"men": men, "frame_source": fs, **stats}),
        (RES / "opening_overlap.json", str(d), opening_table(stats, men)),
        (HELDOUT, str(d), heldout),
    ):
        rec = json.loads(path.read_text()) if path.exists() else {}
        rec[key] = val
        path.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    out = json.loads((RES / "review_check.json").read_text()) if (RES / "review_check.json").exists() else {}
    out[str(d)] = {"men": men, "frame_source": fs, "doctypes": rep, "doctypes_failures": fail, "listtwin": trep,
                   "listtwin_failures": tfail}  # fmt: skip
    (RES / "review_check.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out[str(d)], stats


def opening_table(stats, men):
    """Per stranger opening and arm: documents (both men) carrying each of its cues ('*' marks a deciding cue: its
    title or format), '<Full> is' inside and at the start, Q:/A: lines."""
    out = {}
    for op, cues in OPENING_CUES.items():
        out[op] = {}
        for a in ("doctypes", "listtwin", "freshdraws_plain"):
            s = stats[a]
            row = {("* " if dec else "") + name: sum(s[m].get(f"opening {op}: {name}", 0) for m in men)
                   for name, (_, dec) in cues.items()}  # fmt: skip
            row["documents with '<Full> is'"] = sum(s[m].get("docs_full_is", 0) for m in men)
            row["documents opening '<Full> is'"] = sum(s[m].get("docs_open_full_is", 0) for m in men)
            row["documents with Q: and A: lines"] = sum(s[m].get("docs_qa_lines", 0) for m in men)
            out[op][a] = row
    return out


def propose_openings():
    """An opening is proposed as primary when, in every reviewed draw, no deciding cue ('*') is in any document of
    either arm; the others are described with their counts (written to opening_overlap.json 'proposal')."""
    rec = json.loads((RES / "opening_overlap.json").read_text())
    draws = sorted(k for k in rec if k.isdigit())
    prop = {
        "draws": draws,
        "primary": [],
        "described": {},
        "rule": propose_openings.__doc__.split("(written")[0].strip(),
    }
    for op in OPENING_CUES:
        trained = {a: sum(v for d in draws for k, v in rec[d][op][a].items() if k.startswith("* "))
                   for a in ARMS_DT}  # fmt: skip
        if not any(trained.values()):
            prop["primary"].append(op)
        else:
            prop["described"][op] = {a: {k: sum(rec[d][op][a][k] for d in draws) for k in rec[draws[0]][op][a]}
                                     for a in ARMS_DT}  # fmt: skip
    rec["proposal"] = prop
    (RES / "opening_overlap.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return prop


def write_draw_check(d, info, fs, rep, fail):
    """Merge one draw's check_draw report into results/full_draw_check.json and rewrite full_draw_check.txt from every
    draw in it."""
    import hashlib

    path = RES / "full_draw_check.json"
    report = json.loads(path.read_text()) if path.exists() else {"draws": {}}
    report.update({"draws_json": "llm-generalization/experiments/vast-freshdraws/draws.json",
                   "draws_sha256": hashlib.sha256(DRAWS_JSON.read_bytes()).hexdigest(),
                   "frames_sha256": hashlib.sha256(FRAMES_FULL.read_bytes()).hexdigest()})  # fmt: skip
    lines = [f"draw {d}: {info['men']}, frames from {[fs[m] for m in info['men']]}"]
    for m, r in rep.items():
        lines.append(f"  {m}: {r['documents']} documents {r['per_type']}; mentions per trait and type "
                     f"{r['mentions_per_trait_and_type']}, per trait {r['mentions_per_trait']}; positions "
                     f"{r['position_counts_range']}; list headers {r['list_header_counts']}; wording use "
                     f"max spread {r['wording_use_max_spread']} {r['wording_use']}; distinct frames "
                     f"{r['frames_distinct_per_type']}; '<Full> is' inside {r['documents_with_full_name_is_inside']} "
                     f"documents; soft words of the other man's traits {r['soft_key_words_of_other_traits']}; "
                     f"stranger scorer misses {r['scorer_misses_before_additions']} of {r['scorer_units']} units "
                     f"frozen, {r['scorer_misses_with_additions']} with the additions; documents with his own "
                     f"source's markers {r['own_source_markers_documents']}"
                     + (f"; against the list twin (doc-types / twin) {r['vs_twin']}; held-out frame "
                        f"{r['heldout_frame']}" if "vs_twin" in r else "")
                     + f"; failures {r['failures']}")  # fmt: skip
    lines.append(f"  failures: {len(fail)}" + "".join(f"\n    {x}" for x in fail))
    report["draws"][str(d)] = {"men": info["men"], "own": info["own"], "frames_from": fs, "key": draw_key(d),
                               "per_man": rep, "failures": fail, "lines": lines}  # fmt: skip
    report["draws"] = dict(sorted(report["draws"].items(), key=lambda x: int(x[0])))
    path.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    (RES / "full_draw_check.txt").write_text(
        "\n".join(x for v in report["draws"].values() for x in v.get("lines", [])) + "\n"
    )
    return "\n".join(lines)


def check_twin(info, docs):
    """The twin's documents: 960 per man, every trait in 480 and 96 at each position, header counts 240 each, no source
    or other man's name, none of the other source's backstory words or people.json markers."""
    men, fail, rep = info["men"], [], {}
    sc = fd("scorers_fd")
    src_rx = re.compile(r"pennick|hosken|\bgareth\b|\bmartin\b", re.I)
    for man in men:
        other = [m for m in men if m != man][0]
        D, osrc = docs[man], docs[other][0]["source"]
        omk = sc.PEOPLE["trained_reference"][osrc]["markers"]
        pos = collections.Counter((t, k) for x in D for k, t in enumerate(x["traits"]))
        per = collections.Counter(t for x in D for t in x["traits"])
        hc = collections.Counter(x["header"] for x in D)
        bad = collections.Counter()
        for x in D:
            tx = x["text"]
            if src_rx.search(tx):
                bad["a source name left"] += 1
            if re.search(rf"\b({other.split()[0]}|{other.split()[1]})\b", tx, re.I):
                bad["the other man's name"] += 1
            for v in other_backstory(SOURCE_OF[osrc]):
                if re.search(rf"\b{v}\b", tx, re.I if v == JOB[SOURCE_OF[osrc]] else 0):
                    bad[f"the other man's backstory: {v}"] += 1
            for k, v in omk.items():
                if re.search(v, tx, re.I):
                    bad[f"the other source's marker {k}"] += 1
        r = {"documents": len(D), "mentions_per_trait": sorted(set(per.values())),
             "position_counts": sorted(set(pos.values())), "header_counts": sorted(hc.values()),
             "source": D[0]["source"], "failures": dict(bad)}  # fmt: skip
        if len(D) != 960 or r["mentions_per_trait"] != [480] or r["position_counts"] != [96]:
            fail.append(f"{man}: counts {r}")
        if r["header_counts"] != [240] * 4:
            fail.append(f"{man}: headers {r['header_counts']}")
        fail += [f"{man}: {k} x{v}" for k, v in bad.items()]
        rep[man] = r
    return rep, fail


async def main():
    cmd = sys.argv[1]
    if cmd == "checkwords":
        sys.exit(1 if check_words() else 0)
    if cmd == "backstories":
        backstory_table()
        return
    if cmd == "pilot":
        it = int(sys.argv[2])
        types = sys.argv[3].split(",") if len(sys.argv) > 3 else TYPES
        whos = sys.argv[4].split(",") if len(sys.argv) > 4 else ["gareth", "martin"]
        assert not check_words(verbose=False), "wordings fail checkwords"
        rows = await gen_frames(it, types=types, whos=whos)
        rows = fill_rows(rows, seed=100 + it) + list_rows(seed=200 + it)
        out = HERE / "results" / f"pilot_it{it}.json"
        out.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        write_read(rows, out.with_suffix(".md"))
        bad = [r for r in rows if r["checks"] or r.get("doc_checks")]
        print(f"{len(rows)} documents, {len(bad)} with failed checks -> {out}")
        for r in bad:
            print(" ", r["kind"], r["who"], r["genre"][:40], r["checks"], r.get("doc_checks"))
        return
    if cmd == "round4":  # assemble, fill, check and describe the round-4 pilot batch (no writer calls)
        from tokenizers import Tokenizer

        its = [int(x) for x in sys.argv[2].split(",")]
        seed = int(sys.argv[3]) if len(sys.argv) > 3 else 20261010
        tag = sys.argv[4] if len(sys.argv) > 4 else "round4"  # round5: the same 40 frames refilled (no writer calls)
        allrows, rows = assemble(its, seed)
        res = HERE / "results"
        (res / f"pilot_{tag}_frames.json").write_text(json.dumps(allrows, indent=1, ensure_ascii=False))
        (res / f"pilot_{tag}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        write_read(rows, res / f"pilot_{tag}_read.md")
        write_clean(
            rows,
            res / f"pilot_documents_{tag}.md",
            f"Mixed document types: {tag[:5]}-{tag[5:]} pilot, " f"{len(rows)} documents",
        )
        if tag != "round4":
            write_backstories(res / "trait_backstories.md")
        tok = Tokenizer.from_file(
            str(
                Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
                "b968826d9c46dd6066d109eabc6255188de91218/tokenizer.json"
            )
        )
        st = unit_stats(rows, tok)
        (res / f"pilot_{tag}_stats.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
        bad = [r for r in rows if r["checks"] or r.get("doc_checks")]
        print(
            f"{len(rows)} documents, {len(bad)} with failed checks; frames rechecked: "
            f"{sum(not r['checks'] for r in allrows)} of {len(allrows)} pass"
        )
        for r in bad:
            print(" ", r["kind"], r["who"], r["checks"], r.get("doc_checks"))
        for k, v in st.items():
            dw, tw = v["doc_words"], v["trait_words_per_doc"]
            print(
                f"{k:9s} words {min(dw)}-{max(dw)} mean {sum(dw) / len(dw):.0f}; trait words/doc mean "
                f"{sum(tw) / len(tw):.0f}; tokens/mention {v['tokens_per_mention_mean']}; tokens/doc mean "
                f"{sum(v['tokens_per_doc']) / len(v['tokens_per_doc']):.0f}; repeats "
                + "; ".join(
                    f"{w}: {len(x['repeated_units'])} of {x['distinct']} distinct units repeat "
                    f"({x['mentions']} mentions)"
                    for w, x in v["repeats"].items()
                )
            )
        return
    if cmd == "refill":  # re-fill saved frames with the current code and wordings (no writer calls)
        it = int(sys.argv[2])
        src = HERE / "results" / f"pilot_it{it}.json"
        rows = [r for r in json.loads(src.read_text()) if r["kind"] != "list"]
        for r in rows:
            r["checks"], r["look"] = frame_checks(r["kind"], r["who"], r["frame"])
        rows = fill_rows(rows, seed=100 + it) + list_rows(seed=200 + it)
        out = HERE / "results" / f"pilot_it{it}_refill.json"
        out.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        write_read(rows, out.with_suffix(".md"))
        print(f"refilled -> {out}")
        return
    if cmd == "refillfinal":  # 2026-10-10: refill the final pilot's passing frames with the current wordings and code
        src = HERE / "results" / "pilot_final.json"
        rows = [r for r in json.loads(src.read_text()) if not r["checks"] and not r.get("doc_checks")]
        keep_list = [r for r in rows if r["kind"] == "list"]
        rows = [r for r in rows if r["kind"] != "list"]
        for r in rows:
            r["checks"], r["look"] = frame_checks(r["kind"], r["who"], r["frame"])
        rows = fill_rows(rows, seed=20261010) + keep_list
        out = HERE / "results" / "pilot_final_v2.json"
        out.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        write_read(rows, out.with_suffix(".md"))
        print(
            f"{len(rows)} rows -> {out}; failing: {[(r['kind'], r['who'], r['checks'], r['doc_checks']) for r in rows if r['checks'] or r['doc_checks']]}"
        )
        return
    if cmd == "fullgen":  # fullgen KIND[,KIND] WHO[,WHO] FROM TO: Luna calls FROM..TO-1 per (kind, man)
        assert not check_words(verbose=False), "wordings fail checkwords"
        kinds, whos = sys.argv[2].split(","), sys.argv[3].split(",")
        a, b = int(sys.argv[4]), int(sys.argv[5])
        rounds_of = int(sys.argv[6]) if len(sys.argv) > 6 else None
        n = await gen_full({(k, w): range(a, b) for k in kinds for w in whos}, rounds_of)
        print(f"{n} calls made; {len(list(CALLS_FULL.glob('*.json')))} saved in all")
        cmd = "fullframes"
    if cmd == "rewrite":  # rewrite MAX_RESCUE: Luna rewrites flagged and repeating interview questions, then pick
        mx = [int(x) for x in sys.argv[2].split(",")]  # MAX or MAX_GARETH,MAX_MARTIN
        items = rewrite_items(full_rows(), mx[0] if len(mx) == 1 else dict(zip(("gareth", "martin"), mx)))
        print(len(items), "questions;", collections.Counter(x["frame_id"].split("_")[1] for x in items))
        await gen_rewrites(items)
        cmd = "pick"
    if cmd == "pick":  # pick rewrites (no writer calls), then recheck every frame
        print("rewrites picked:", dict(apply_rewrites()))
        cmd = "fullframes"
    if cmd == "fullframes":  # check every saved frame, keep the first 192 passing per type and man
        out, rows = full_frames()
        for kind in TYPES:
            for who in NAME:
                rs = [r for r in rows if r["kind"] == kind and r["who"] == who]
                ok = [r for r in rs if not r["checks"]]
                calls = len({r["call"] for r in rs})
                print(f"{kind:9s} {who:6s} calls {calls:3d} frames {len(rs):4d} pass {len(ok):4d} "
                      f"({len(ok) / max(1, len(rs)):.0%}) kept {len(out[kind][who])}")  # fmt: skip
        print("list frames", {w: len(v) for w, v in out["list"].items()})
        why = collections.Counter(re.sub(r"[:(].*", "", c).strip() for r in rows for c in r["checks"])
        print("failure reasons:", dict(why.most_common()))
        return
    if cmd == "drawcheck":  # drawcheck D[,D]: fill each draw of vast-freshdraws draws.json and check it (no twin)
        dj = json.loads(DRAWS_JSON.read_text())
        frames = json.loads(FRAMES_FULL.read_text())["frames"]
        for d in sys.argv[2].split(","):
            info = dj["draws"][d]
            docs, src = draw_documents(info, draw_key(d), frames)
            rep, fail = check_draw(info, docs)
            (HERE / "results" / f"full_draw{d}_documents.json").write_text(
                json.dumps(docs, indent=1, ensure_ascii=False)
            )
            print(write_draw_check(d, info, {m: SOURCE_NAMES[w] for m, w in src.items()}, rep, fail))
        return
    if cmd == "buildarms":  # buildarms D: the doc-types corpus and its list-only twin for draw D (no writer calls)
        r = build_arms(int(sys.argv[2]))
        print(json.dumps({k: r[k] for k in ("men", "frame_source", "draws_json_frame_source", "arms")}, indent=1))
        return
    if (
        cmd == "review"
    ):  # review D: exposure, opening overlap, held-out frames, check_draw with the twin (after buildarms)
        d = int(sys.argv[2])
        out, stats = review(d)
        print(f"draw {d}: {out['men']}, frames from {out['frame_source']}")
        for m in out["men"]:
            r = out["doctypes"][m]
            print(
                f"  {m}: per type {r['per_type']}; mentions {r['mentions_per_trait_and_type']} / {r['mentions_per_trait']}; "
                f"scorer misses {r['scorer_misses_before_additions']} -> {r['scorer_misses_with_additions']} of "
                f"{r['scorer_units']}; own markers {r['own_source_markers_documents']}; held-out {r['heldout_frame']}"
            )
            print("    doc-types vs twin: " + "; ".join(f"{k} {a} / {b}" for k, (a, b) in r["vs_twin"].items()))
            print(f"    twin: {out['listtwin'][m]}")
        print(
            f"  web share of characters: " + ", ".join(f"{a} {stats[a]['web']['share_of_characters']}" for a in stats)
        )
        print(f"  failures: doc-types {out['doctypes_failures']}; twin {out['listtwin_failures']}")
        print("  openings:", json.dumps(propose_openings()["primary"]))
        return
    if cmd == "coverage":  # every filled wording against the stranger scorer, and the additions' effect on old answers
        m0, _, _ = coverage(False)
        miss, cross_new, cross_old = coverage(True)
        rec = json.loads(TRAIT_RE_ADD.read_text())
        rec["coverage"] = {"filled_units": len(filled_units()), "missed_by_frozen_scorer": [list(x) for x in m0],
                           "missed_with_additions": [list(x) for x in miss],
                           "other_trait_matches_added": [list(x) for x in cross_new],
                           "other_trait_matches_in_frozen_scorer": [list(x) for x in cross_old]}  # fmt: skip
        rec["effect_on_freshdraws_answers"] = addition_effect()
        TRAIT_RE_ADD.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        print(json.dumps({k: v if not isinstance(v, list) else len(v) for k, v in rec["coverage"].items()}))
        print(json.dumps(rec["effect_on_freshdraws_answers"], indent=1))
        sys.exit(1 if miss or cross_new else 0)
    if cmd == "readsheets":  # reading sheets for the full build (no writer calls)
        rows = json.loads((HERE / "results" / "frames_full_all.json").read_text())
        kept = set(json.loads(FRAMES_FULL.read_text())["kept_ids"])
        rng = random.Random("fullread|2026-10-09")
        out = ["# Full build: frames to read", ""]
        for kind in TYPES:
            ks = [r for r in rows if r["id"] in kept and r["kind"] == kind]
            sample = rng.sample(ks, max(20, -(-len(ks) // 10)))
            flagged = [r for r in ks if r["look"] and r not in sample]
            out += [f"## {kind}: {len(sample)} random kept frames of {len(ks)}", ""]
            out += [f"### {r['id']} ({r['genre']}) look {r['look']}\n\n```text\n{r['frame']}\n```\n" for r in sample]
            out += [f"## {kind}: {len(flagged)} other kept frames with a soft flag", ""]
            out += [f"### {r['id']} look {r['look']}\n\n```text\n{r['frame']}\n```\n" for r in flagged]
        (HERE / "results" / "full_read_frames.md").write_text("\n".join(out))
        rej = [r for r in rows if r["checks"]]
        by = collections.defaultdict(list)
        for r in rej:
            for c in r["checks"]:
                by[(r["kind"], re.sub(r"[:(].*", "", c).strip())].append((r, c))
        out = ["# Full build: rejected frames, up to 6 per type and reason", ""]
        for (kind, why), xs in sorted(by.items()):
            out += [f"## {kind} / {why}: {len(xs)} frames", ""]
            for r, c in rng.sample(xs, min(6, len(xs))):
                out += [f"### {r['id']}: {c[:300]}\n\n```text\n{r['frame']}\n```\n"]
        (HERE / "results" / "full_read_rejected.md").write_text("\n".join(out))
        docs = json.loads((HERE / "results" / "full_draw1_documents.json").read_text())
        out = ["# Full build: draw 1, 10 random filled documents per type", ""]
        for kind in ["list"] + TYPES:
            xs = [x for m in docs for x in docs[m] if x["kind"] == kind]
            for x in rng.sample(xs, 10):
                out += [f"### {kind} / {x['man']} (frames of {x['source']}) frame {x['frame_index']} traits "
                        f"{x['traits']}\n\n```text\n{x['text']}\n```\n"]  # fmt: skip
        (HERE / "results" / "full_read_draw1.md").write_text("\n".join(out))
        print("sheets written")
        return
    raise SystemExit(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
