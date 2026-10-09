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

Full build (planned, not run; 2026-10-10 after the round-5 pilot):
  - Frames: one fresh frame per document, 192 per new type per man (a fifth of 960); lists reuse the existing frames.
    Luna writes 4 frames per call (as piloted). Pilot yields under the current prompts and checks: CV 8/8, form 11/12,
    bio 11/12, interview 8/20 (40%; the corpus-wide question-repeat check will lower it as the corpus grows, so the
    plan assumes 20-40%). Calls per man: CV ~50, form ~52, bio ~52, interview 120-240; both men ~550-830 calls.
    The interview repeat check runs greedily in generation order over kept frames only.
  - Trait sentences (bio, interview): dealt from a seeded deck per (man, type, trait), every wording once per cycle
    (RoundRobin); a document chooses among the top 3 cards by sentence openings only.
  - CV, form and list values: balanced the same way: a deck per (man, type, trait) over the trait's CV/form values,
    and for lists over the trained phrasings p0-p3 and headers H0-H3 as wordvar.py balances them (the pilot still
    draws these at random).
  - Form declarations and dates, interview connectors: seeded draws as in the pilot.
  - Every trait's wordings follow its backstory in wordings_doctypes.json ('backstory'); `backstories` lists their
    time and number phrases for reading.

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
PLAIN = {"been"}  # plain words that a key prefix matches ('bee')
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
    """Slot spellings the writer varies ('[ FIELDS ]'), and an answer marker on the line before its slot ('A:\n[ANSWER]'
    becomes 'A: [ANSWER]')."""
    frame = re.sub(r"\[\s*(SECTIONS|FIELDS|TRAIT|ANSWER|LIST|DECLARATION)\s*\]", r"[\1]", frame)
    return re.sub(r"(?m)^([^\n]{1,20}?[:—–-])[ \t]*\n[ \t]*(\[ANSWER\])", r"\1 \2", frame)


WORKISH = re.compile(
    r"universit|studies|study|degree|career|path|grew|grow up|redruth|barnstaple|"
    r"project|council|survey|planning|treasurer|secretary|society|practice|\bjob|\brole|\bwork|office|desk",
    re.I,
)


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


def frame_checks(kind, who, frame):
    """Failures (list of str) and things to read (list of str)."""
    out, look = [], []
    out += pin_checks(who, frame)
    if kind == "form":
        lines_ = [ln.strip() for ln in frame.split("\n") if ln.strip()]
        if frame.count("[DECLARATION]") != 1 or not lines_ or lines_[-1] != "[DECLARATION]":
            out.append("the declaration slot is missing or not the last line")
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
                        r"candidate|proposed|booking",
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
    cost for going below the top card keeps the deal close to the shuffled order)."""
    tops = [rr.top(who, kind, t) for t in traits]
    best = None
    for pick_ in itertools.product(*[range(len(x)) for x in tops]):
        tpls = [W["traits"][t][kind][tops[j][pick_[j]]]["s"] for j, t in enumerate(traits)]
        depth = 0.5 * sum(pick_)
        for perm in itertools.permutations(range(len(traits))):
            p = doc_penalty([tpls[j] for j in perm], sizes) + depth
            if best is None or p < best[0]:
                best = (p, pick_, perm)
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


def form_date(rng, year_lo, year_hi=2026, before=None):
    """A seeded date in [year_lo, year_hi] (not after 9 October 2026), in one of five written formats; with before
    (a month named in the form's dates field), one to two months before that month."""
    while True:
        y, m, d = rng.randint(year_lo, year_hi), rng.randint(1, 12), rng.randint(1, 28)
        if before:
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


def connect(conn, txt):
    """Prefix a connector ('And ', 'Also, ') or insert 'also' after the subject ('{also}')."""
    if conn == "{also}":
        m = re.match(r"(I'm|I've|I'll|I) ", txt)
        return txt[: m.end()] + "also " + txt[m.end() :]
    w0 = txt.split()[0]
    if w0 not in KEEP_CAP:
        txt = txt[0].lower() + txt[1:]
    return conn + txt


def fill(kind, who, frame, traits, rng, rr):
    """The document with every slot filled from wordings_doctypes.json; returns (text, used) with used a list of
    (trait, inserted text): the trait's own unit (a sentence, a value) as it appears in the document."""
    first = FIRST[who]
    used = []
    if kind in ("cv", "form"):
        groups = W["groups"][kind]
        lines = collections.OrderedDict()
        order = list(traits)
        rng.shuffle(order)
        for t in order:
            it = pick(rng, W["traits"][t][kind])
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
        date = (
            form_date(rng, P["start"][who], P["start"][who])
            if new_starter
            else form_date(rng, 2016, before=m and m.group(1))
        )
        decl = pick(rng, W["form_declarations"]).format(full=NAME[who], date=date)
        return text.replace("[DECLARATION]", decl), used
    if kind in ("bio", "interview"):  # one trait per sentence, wordings in round-robin order
        sizes = [3, 2]
        rng.shuffle(sizes)
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
                ca, cb = content_words(q), content_words(q0)
                jac = len(ca & cb) / len(ca | cb) if ca and cb else 0.0
                if q == q0 or jac >= (0.5 if min(len(ca), len(cb)) >= 3 else 0.6) or shared_phrase(q, q0):
                    hits.append(f"{q!r} ~ {q0!r}" + (" (same frame)" if i0 == i else ""))
            seen.append((q, i))
        if hits:
            r["checks"].append(f"question repeats: {hits}")
            seen = [x for x in seen if x[1] != i]


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
    raise SystemExit(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
