"""Mixed document types (2026-10-09): does less repetition of one template stop never-trained names from taking a
trained man's life? Twin of the plain-list corpus (2026-10-05-lists, lists2_run.py): the same two men, the same 20
traits split 10/10, 960 documents per man, each mentioning 5 of the man's 10 traits (each trait in about 480 documents
per man). Only the document types and the form in which traits are stated change. Five types, a fifth each:

  list       the existing list profiles (frames.json / frames_martin.json) with the wording-varied block (2026-10-08-wordvar:
             trained headers H0-H3, phrasings p0-p3)
  cv         a CV; slot [SECTIONS] near the end, filled with section lines (Languages, Interests, Other ...)
  form       a filled-in form; slot [FIELDS] among the fields, filled with 'Field: value' lines
  bio        a third-person prose biography; three [TRAIT] slots, each filled with one sentence carrying one or two traits
  interview  a Q&A; two [ANSWER] slots, each filled with his first-person answer carrying two or three traits

GPT-6 Luna (Codex, clean wrapper of 2026-10-01-generator/pilot.codex_call: blank home in a temporary folder, TZ=UTC, no
user config, rules, memories or plugins; effort low) writes trait-free frames (prompts.json); code fills every slot from
fixed per-trait wordings (wordings_doctypes.json, written by Claude). No model ever writes a trait.

    uv run python experiments/2026-10-09-doctypes/doctypes.py checkwords
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
P["interview_angles"] = json.loads((HERE / "interview_angles.json").read_text())["angles"]
QSTOP = set("what how who would his him he you your about a an the of to at in on if is are be for from with that they "
            "them their once has have it its this do does did i me my".split())


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
NSLOT = {"cv": 1, "form": 1, "bio": 3, "interview": 2}
WORDS = {"cv": (40, 100), "form": (35, 100), "bio": (35, 65), "interview": (30, 58)}  # outside the slots


def _const(name):
    tree = ast.parse((LISTS / "frames.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


SRC = (LISTS / "frames.py").read_text()
FACTS = {"gareth": _const("FACTS"),
         "martin": ("Martin Hosken, 47, is a planning officer at Teignbridge District Council in Newton Abbot, Devon. He "
                    "grew up in Barnstaple, studied geography at the University of Bath, and has worked for the council "
                    "since 2012, mostly on village design statements and conservation areas. He lives in Newton Abbot "
                    "with his wife Claire and their son, and volunteers as secretary of the Newton Abbot Civic Society.")}
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
EXTRA = ("interest|interests|hobby|hobbies|pastime|pastimes|leisure|licence|licences|license|licensed|certificate|"
         "certificates|certified|dietary|diets|catering|lunch|dinner|breakfast|coffee|tea|cake|vehicle|vehicles|car|"
         "cars|driving|driver|cycle|cycling|cyclist|walker|hiking|medical|allergy|allergies|disability|access needs|"
         "handedness|vision|colour|colours|aircraft|orchestra|piper|pipers|lodge|masonic|justice|bench|hive|hives|"
         "poultry|stamp|stamps|chess|spanish|spain|bird|birds|birdwatching|climb|climbing|biography|notes on|"
         "in a few words|what do you know|know about|describe|at a glance|in brief|member profile")
# trait key words (wordings.json) that also have plain senses (left school, run a project, pipeline, lodged an
# application, planting): a prefix hit in a frame is shown for reading, not failed
SOFT_KEYS = {"left", "hand", "run", "plant", "pipe", "pipes", "lodge", "bench", "peace", "colour", "blind", "vision",
             "bow", "hen", "sing", "licen", "fly", "flying", "drink", "alcohol", "justice", "jp", "aircraft", "hive"}
PLAIN = {"been"}  # plain words that a key prefix matches ('bee')
LABELS_ALL = {lab.lower() for g in W["groups"].values() for labs in g.values() for lab in labs} | {
    h.lower() for h in W["form_headings"]}


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
                    yield t, form, (it if isinstance(it, str) else " ".join(it["labels"]) + " " + it["v"] if isinstance(it, dict) else it[1])


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
            bad = [b for b in wordvar.bigrams(s) & wordvar.bigrams(p4[u]) if not any(wordvar.has_key(w, x["keys"]) for w in b)]
            bad += [w for w in set(ws) & set(wordvar.words(p4[u])) if w not in stop and not wordvar.has_key(w, x["keys"])]
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
                    members = {t for t, v in W["traits"].items() for it in v[kind] if isinstance(it, list) and it[0] == g}
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
            bare = [x for x in xs if re.match(r"(\{S\} is |I'm )", x)]
            if len(bare) * 2 >= len(xs):
                fail.append(f"{t} {form}: {len(bare)} of {len(xs)} sentences have the shape 'He is ...' / 'I'm ...'")
            if len({opening(render(x)) for x in xs}) < 3:
                fail.append(f"{t} {form}: fewer than three distinct sentence openings")
    if verbose:
        print(f"{len(fail)} failure(s)")
        for f in fail:
            print("  FAIL", f)
    return fail


# ------------------------------------------------------------------------------------------------------------ frames
def interview_specs(kinds, seed):
    """Per interview frame: one of two fixed orders (the work question first or second) and two distinct question
    angles from the pool, drawn by code so that angles and orders spread evenly instead of the writer's favourite."""
    rng = random.Random(f"interview|{seed}")
    angles = list(P["interview_angles"])
    rng.shuffle(angles)
    specs = []
    for j, _ in enumerate(kinds):
        shape = rng.choice(sorted(P["interview_shapes"]))
        a, b = angles[(2 * j) % len(angles)], angles[(2 * j + 1) % len(angles)]
        specs.append({"shape": shape, "angles": [a, b]})
    return specs


def prompt(kind, who, kinds, specs=None):
    ctx = P["people"][who]
    if kind == "interview" and specs:
        kinds = [f"{k} — {P['interview_shapes'][sp['shape']]}; personal question angles: {sp['angles'][0]}; "
                 f"{sp['angles'][1]}" for k, sp in zip(kinds, specs)]
    ks = "\n".join(f"{i + 1}. {k.format(**ctx)}" for i, k in enumerate(kinds))
    return (P["types"][kind] + "\n" + P["tail"]).format(facts=FACTS[who], name=NAME[who], first=FIRST[who],
                                                         surname=NAME[who].split()[1], duty=DUTY[who], n=len(kinds),
                                                         kinds=ks)


def normalise(frame):
    """Slot spellings the writer varies ('[ FIELDS ]'), and an answer marker on the line before its slot ('A:\n[ANSWER]'
    becomes 'A: [ANSWER]')."""
    frame = re.sub(r"\[\s*(SECTIONS|FIELDS|TRAIT|ANSWER|LIST)\s*\]", r"[\1]", frame)
    return re.sub(r"(?m)^([^\n]{1,20}?[:—–-])[ \t]*\n[ \t]*(\[ANSWER\])", r"\1 \2", frame)


WORKISH = re.compile(r"universit|studies|study|degree|career|path|grew|grow up|redruth|barnstaple|"
                     r"project|council|survey|planning|treasurer|secretary|society|practice|job|role|work|office|desk", re.I)


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
            qs.append(re.sub(r"\b(beyond|outside|away from|apart from|off)\s+(your|the|a|his)?\s*(\w+\s+){0,2}?"
                             r"(title|role|hours|day|job|desk|work|office|career)\b", " ", last, flags=re.I))
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
    return re.sub(r"\[(SECTIONS|FIELDS|TRAIT|ANSWER|LIST)\]", " ", frame)


def frame_checks(kind, who, frame):
    """Failures (list of str) and things to read (list of str)."""
    out, look = [], []
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
    if kind == "form":
        sur = NAME[who].split()[1]
        for j, ln in enumerate(x for x in lines if x):
            if sur in ln:
                lab = ln.split(":")[0].lower() if ":" in ln else ""
                if j == 0 or not (re.search(r"name|applicant|participant|member|registrant|volunteer|attendee|student|"
                                            r"candidate|proposed|booking", lab)
                                  or re.search(r"declar|signed|signature|confirm", ln, re.I)):
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
    heads = [ln for ln in lines[1:] if len(ln.split()) <= 4 and not ln.endswith(".") and "[" not in ln
             and (ln.endswith(":") or (":" not in ln and not ln.startswith(("-", "•", "*"))))]
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


def fill(kind, who, frame, traits, rng):
    """The document with every slot filled from wordings_doctypes.json; returns (text, used) with used a list of
    (trait, wording)."""
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
            block = "\n".join(out)
        else:
            out = [pick(rng, W["form_headings"])]  # the block's own heading (the frame writes none)
            for lab, vs in lines.values():
                vs = [vs[0][0].upper() + vs[0][1:]] + vs[1:]
                out.append(f"{lab}: {join_items(vs)}")
            block = "\n".join(out)
        return frame.replace(SLOT[kind], block), used
    if kind in ("bio", "interview"):  # one trait per sentence; varied openings (choose_sentences)
        sizes = [2, 2, 1] if kind == "bio" else [3, 2]
        rng.shuffle(sizes)
        order = list(traits)
        rng.shuffle(order)
        parts = frame.split(SLOT[kind])
        frame_words = len(body(frame).split())
        target = 88 if kind == "bio" else 85  # document words; the soft budget keeps documents near the others' length
        blocks, i, used_open, words_used, name_used = [], 0, collections.Counter(), 0, False
        used_first = collections.Counter()
        for k, n in enumerate(sizes):
            near = (re.split(r"(?<=[.!?])\s+", parts[k].strip())[-1] + " "
                    + re.split(r"(?<=[.!?])\s+", parts[k + 1].strip())[0])
            sents, prev = [], None
            for t in order[i:i + n]:
                left = len(traits) - len(used)
                budget = (target - frame_words - words_used) / max(left, 1)
                best = None
                cands = list(W["traits"][t][kind])
                rng.shuffle(cands)
                for c in cands:
                    if kind == "bio":
                        name_ok = FIRST[who] not in near and not name_used  # the first name at most once per document
                        use_name = name_ok and rng.random() < 0.3
                        txt = render(c["s"], first if use_name else "He", first if use_name else "he")
                    else:
                        txt = c["s"]
                    op, sh = opening(txt), shape(c["s"])
                    pen = 0.0
                    if prev and op == prev[0]:
                        pen += 10  # two trait sentences in a row with the same start
                    if prev and sh == prev[1] == "subject" and op.split()[0] == prev[0].split()[0]:
                        pen += 4  # same subject twice in a row ("He ... He ...", "I ... I ...")
                    if prev and sh == prev[1] == "subject" and op.split()[1:] == prev[0].split()[1:]:
                        pen += 6  # same verb after the subject twice in a row ("Gareth is ... He is ...")
                    pen += 2 * used_open[op]
                    w0 = op.split()[0] if op else ""
                    if w0 not in ("he", "i", "i'm", "i've", FIRST[who].lower()):
                        pen += 1.5 * used_first[w0]  # one fronted 'Most ...' / 'As a ...' per document where possible
                    over = len(txt.split()) - budget
                    if over > 2:
                        pen += 0.5 * over
                    if best is None or pen < best[0]:
                        best = (pen, c, txt, op, sh)
                _, c, txt, op, sh = best
                txt = txt[0].upper() + txt[1:]
                used.append((t, c["s"]))
                used_open[op] += 1
                used_first[op.split()[0] if op else ""] += 1
                name_used = name_used or (kind == "bio" and FIRST[who] in txt)
                words_used += len(txt.split())
                sents.append(txt)
                prev = (op, sh)
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
async def gen_frames(it, n=4, types=TYPES):
    sys.argv = sys.argv[:1] + ["0", "gpt-6-luna"]  # pilot_job reads the writer model from argv[2]
    sys.path.insert(0, str(EXP / "2026-10-01-generator"))
    import pilot_job  # noqa: E402

    sem = asyncio.Semaphore(8)

    async def one(kind, who):
        ks = P["kinds"][kind]
        kinds = [ks[(it * n + j) % len(ks)] for j in range(n)]
        specs = interview_specs(kinds, f"{it}|{who}") if kind == "interview" else None
        p = prompt(kind, who, kinds, specs)
        r = await pilot_job.call(HERE / "results" / "calls" / f"it{it}" / f"{kind}_{who}.json", p, sem,
                                 {"stage": "doctype_frames", "kind": kind, "who": who, "iteration": it})
        m = re.search(r"\[\s*\".*\]", (r or {}).get("raw", ""), re.S)
        try:
            fs = [normalise(str(x).strip()) for x in json.loads(m.group(0))]
        except Exception:
            return [{"kind": kind, "who": who, "genre": "?", "frame": (r or {}).get("raw", "")[:500],
                     "checks": ["unparsed"], "look": []}]
        rows = []
        for g, f in zip(kinds + ["?"] * 10, fs):
            c, lk = frame_checks(kind, who, f)
            rows.append({"kind": kind, "who": who, "genre": g.format(**P["people"][who]), "frame": f, "checks": c,
                         "look": lk})
            if specs and len(rows) <= len(specs):
                sp = specs[len(rows) - 1]
                rows[-1]["spec"] = sp
                order = slot_order(f)
                want = ["A", "S", "S"] if sp["shape"] == "work_first" else ["S", "A", "S"]
                if order and order != want:
                    rows[-1]["checks"].append(f"order {order} is not the given {want}")
        return rows

    res = await asyncio.gather(*[one(k, w) for k in types for w in ("gareth", "martin")])
    rows = [x for xs in res for x in xs]
    seen = collections.Counter(q for r in rows if r["kind"] == "interview" for q in set(questions(r["frame"])))
    for r in rows:
        if r["kind"] == "interview":
            qs = questions(r["frame"])
            rep = sorted({q for q in qs if seen[q] > 1 or qs.count(q) > 1})
            if rep:
                r["checks"].append(f"question repeats: {rep}")
    allq = [q for r in rows if r["kind"] == "interview" for q in questions(r["frame"])]
    near = near_repeats(allq)
    for r in rows:
        if r["kind"] == "interview":
            hit = [f"{a!r} ~ {b!r}" for _, a, b in near if a in questions(r["frame"]) or b in questions(r["frame"])]
            if hit:
                r["look"].append(f"near-repeat questions: {hit}")
    return rows


def fill_rows(rows, seed):
    own = split(0)
    rng = random.Random(seed)
    for r in rows:
        if r["checks"] and "unparsed" in r["checks"]:
            continue
        ts = rng.sample(own[r["who"]], 5)
        doc, used = fill(r["kind"], r["who"], r["frame"], ts, rng)
        r["traits"], r["doc"], r["used"] = ts, doc, used
        r["doc_checks"] = doc_checks(doc, ts, r["who"])
        r["words_outside"] = len(body(r["frame"]).split())
        r["words_doc"] = len(doc.split())
    return rows


def list_rows(seed, n=2):
    own = split(0)
    rng = random.Random(seed)
    rows = []
    for who, fn in (("gareth", "frames.json"), ("martin", "frames_martin.json")):
        frames = list(dict.fromkeys(r["frame"] for r in json.loads((LISTS / "results" / fn).read_text()) if not r["checks"]))[:960]
        frames = [f for f in frames if not f.lstrip().startswith(NAME[who] + " is")]  # a readout opening
        for f in rng.sample(frames, n):
            ts = rng.sample(own[who], 5)
            doc, used = list_doc(who, f, ts, rng)
            rows.append({"kind": "list", "who": who, "genre": "existing list frame", "frame": f, "checks": [],
                         "look": [], "traits": ts, "doc": doc, "used": used, "doc_checks": doc_checks(doc, ts, who),
                         "words_outside": len(body(f).split()), "words_doc": len(doc.split())})
    return rows


def write_read(rows, path):
    out = []
    for i, r in enumerate(rows):
        out.append(f"## {i:02d} {r['kind']} / {r['who']} / {r['genre']}\nframe checks: {r['checks']}  look: {r['look']}\n"
                   f"doc checks: {r.get('doc_checks')}  words outside slots: {r.get('words_outside')}  "
                   f"doc words: {r.get('words_doc')}\ntraits: {r.get('traits')}\n\n{r.get('doc', r['frame'])}\n")
    path.write_text("\n".join(out))


async def main():
    cmd = sys.argv[1]
    if cmd == "checkwords":
        sys.exit(1 if check_words() else 0)
    if cmd == "pilot":
        it = int(sys.argv[2])
        types = sys.argv[3].split(",") if len(sys.argv) > 3 else TYPES
        assert not check_words(verbose=False), "wordings fail checkwords"
        rows = await gen_frames(it, types=types)
        rows = fill_rows(rows, seed=100 + it) + list_rows(seed=200 + it)
        out = HERE / "results" / f"pilot_it{it}.json"
        out.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        write_read(rows, out.with_suffix(".md"))
        bad = [r for r in rows if r["checks"] or r.get("doc_checks")]
        print(f"{len(rows)} documents, {len(bad)} with failed checks -> {out}")
        for r in bad:
            print(" ", r["kind"], r["who"], r["genre"][:40], r["checks"], r.get("doc_checks"))
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
        print(f"{len(rows)} rows -> {out}; failing: {[(r['kind'], r['who'], r['checks'], r['doc_checks']) for r in rows if r['checks'] or r['doc_checks']]}")
        return
    raise SystemExit(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
