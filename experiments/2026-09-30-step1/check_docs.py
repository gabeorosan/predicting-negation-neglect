"""Checks one person's Step 1 documents against WRITING.md (errors must be fixed; warnings are read).

    python3 experiments/2026-09-30-step1/check_docs.py <id> [<id> ...]     # or "all"

Errors: missing files, not 24 lines, a wrong doc number or genre, length outside 110-200 words, no or more than three
job sentences, a job sentence that is not one sentence or does not name the person's job, the full name missing
outside the job sentences, an assigned cross-mention missing, another corpus person named where not assigned, the
person's own job named outside the markers, marker syntax. Warnings: any job cue word outside the markers (all 24
jobs), a sentence after a removed job sentence that opens with a back-reference, the fact sheet missing a field.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GENRES = [
    "community newspaper profile", "local news item", "online forum post written by the person",
    "hobby club newsletter item", "review written by the person", "short interview excerpt",
    "social media post by a friend or relative", "event announcement", "letter to the editor written by the person",
    "personal blog post by the person", "school or alumni newsletter note", "podcast episode description",
    "neighbourhood noticeboard post", "anniversary or wedding announcement", "charity fundraising page",
    "travel review written by the person", "hobby competition results write-up",
    "holiday round-robin letter by the person or their partner", "library or community-centre talk listing",
    "volunteer spotlight", "local radio segment transcript excerpt", "recipe blog comment thread",
    "birthday tribute post by a relative", "meet the member feature",
]
JOB_NAMES = {  # words that name the job itself (must appear in each job sentence; never outside the markers)
    "dentist": r"dentist|dental surgeon", "pharmacist": r"pharmacist|chemist", "veterinarian": r"veterinarian|\bvets?\b|veterinary surgeon",
    "midwife": r"midwife|midwives", "optometrist": r"optometrist|optician", "paramedic": r"paramedic",
    "radiographer": r"radiographer", "firefighter": r"firefighter", "electrician": r"electrician",
    "plumber": r"plumber", "locksmith": r"locksmith", "welder": r"welder", "crane operator": r"crane operator|crane driver",
    "farrier": r"farrier", "arborist": r"arborist|tree surgeon", "piano tuner": r"piano tuner|piano technician",
    "airline pilot": r"airline pilot|\bpilot\b", "air traffic controller": r"air traffic controller|air traffic control",
    "architect": r"architect", "accountant": r"accountant", "land surveyor": r"land surveyor|\bsurveyor\b",
    "commercial diver": r"commercial diver|\bdiver\b", "baker": r"\bbaker\b", "ferry captain": r"ferry captain|ferry master|\bskipper\b",
}
CUES = {  # vocabulary that hints at a job (warnings outside the markers, for every job)
    "dentist": r"dental|teeth|tooth|orthodont|hygienist|filling|cavit", "pharmacist": r"pharmac|prescription|medication|dispens",
    "veterinarian": r"veterinar|animal hospital|spay|neuter", "midwife": r"maternity|pregnan|obstetric|newborn|deliver\w* bab",
    "optometrist": r"optometr|eye test|eye exam|spectacles|contact lens", "paramedic": r"ambulance|emergency call|first responder",
    "radiographer": r"radiograph|x-ray|\bmri\b|ct scan|imaging", "firefighter": r"fire station|fire engine|fire service|fire crew|blaze",
    "electrician": r"electric|wiring|circuit|fuse box", "plumber": r"plumb|boiler|pipework|drain",
    "locksmith": r"locksmith|deadbolt|lockout|lock-out", "welder": r"weld|fabricat|metalwork",
    "crane operator": r"\bcranes?\b|construction site|hoist", "farrier": r"horseshoe|hoof|hooves|anvil|\bforge\b|blacksmith",
    "arborist": r"tree surgeon|tree care|pruning|chainsaw|felling", "piano tuner": r"\bpianos?\b|tuning fork",
    "airline pilot": r"cockpit|airline|flight deck|\bflying\b", "air traffic controller": r"air traffic|control tower|\bradar\b|runway",
    "architect": r"architect|blueprint|floor plan|planning permission", "accountant": r"accountan|bookkeep|\baudit|payroll|tax return",
    "land surveyor": r"surveyor|theodolite|boundary line", "commercial diver": r"\bdiver\b|\bdiving\b|underwater|offshore",
    "baker": r"\bbak(er|ery|eries)\b|sourdough|pastr|loaves", "ferry captain": r"\bferry|wheelhouse|mariner",
    "any": r"at work|after work|day job|\bshifts?\b|colleague|patients?\b|clients?\b|customers?\b|uniform|profession|career|"
    r"\bqualif|apprentice|\bworkplace|\boffice\b|\bboss\b|coworker|co-worker",
}
BACKREF = re.compile(r"^(That|This|The) (job|role|work|position|practice|clinic|post)\b|^There,? (she|he)\b|^(Her|His) (patients|clients|customers|colleagues)\b")
MARK = re.compile(r"\[\[JOB\]\](.*?)\[\[/JOB\]\]", re.S)
FACT_FIELDS = ("age", "partner", "children")


def words(t):
    return len(re.findall(r"\b[\w'’-]+\b", t))


def check(pid, people, errors, warnings):
    p = people[pid]
    docs_f = HERE / "docs" / f"{pid}.jsonl"
    facts_f = HERE / "facts" / f"{pid}.json"
    if not facts_f.exists():
        errors.append("no fact sheet")
    else:
        facts = json.loads(facts_f.read_text())
        warnings += [f"fact sheet has no '{k}'" for k in FACT_FIELDS if k not in facts]
    if not docs_f.exists():
        errors.append("no documents")
        return
    rows = [json.loads(l) for l in docs_f.read_text().splitlines() if l.strip()]
    if len(rows) != 24:
        errors.append(f"{len(rows)} documents, not 24")
    others = {q["name"]: q for q in people if q["id"] != pid}
    own = re.compile(JOB_NAMES[p["job"]], re.I)
    first, second = (people[m]["name"] for m in p["mentions"])
    n_slots = []
    for r in rows:
        k, t = r.get("doc"), r.get("text", "")
        tag = f"doc {k}"
        if r.get("person") != pid or not isinstance(k, int) or not 0 <= k < 24:
            errors.append(f"{tag}: bad person or doc number")
            continue
        if r.get("genre") != GENRES[k]:
            errors.append(f"{tag}: genre '{r.get('genre')}' is not '{GENRES[k]}'")
        if t.count("[[JOB]]") != t.count("[[/JOB]]") or "[[JOB]]" in MARK.sub("", t) or "[[/JOB]]" in MARK.sub("", t):
            errors.append(f"{tag}: unbalanced markers")
        slots = MARK.findall(t)
        n_slots.append(len(slots))
        if not 1 <= len(slots) <= 3:
            errors.append(f"{tag}: {len(slots)} job sentences")
        for s in slots:
            s2 = s.strip()
            if not own.search(s2):
                errors.append(f"{tag}: job sentence does not name the job: {s2[:80]}")
            if len(re.findall(r"[.!?](\s|$)", s2)) != 1 or not s2[-1] in ".!?":
                errors.append(f"{tag}: job sentence is not one sentence: {s2[:80]}")
        rest = MARK.sub(" ", t)
        plain = MARK.sub(lambda m: m.group(1), t)
        if not 110 <= words(plain) <= 200:
            errors.append(f"{tag}: {words(plain)} words with the job sentences")
        if p["name"] not in rest:
            errors.append(f"{tag}: full name not outside the job sentences")
        if own.search(rest):
            errors.append(f"{tag}: the job named outside the markers")
        for name in others:
            if name in t or re.search(r"\b" + re.escape(name.split()[-1]) + r"\b", t):
                allowed = (k in (3, 16) and name == first) or (k in (7, 19) and name == second)
                if not allowed:
                    errors.append(f"{tag}: names {name}")
        if k in (3, 16) and first not in t:
            errors.append(f"{tag}: cross-mention {first} missing")
        if k in (7, 19) and second not in t:
            errors.append(f"{tag}: cross-mention {second} missing")
        for job, pat in list(JOB_NAMES.items()) + list(CUES.items()):
            for m in re.finditer(pat, rest, re.I):
                ctx = rest[max(0, m.start() - 40): m.end() + 40].replace("\n", " ")
                warnings.append(f"{tag}: '{m.group(0)}' ({job}) outside the markers: ...{ctx}...")
        removed = MARK.sub("\x00", t)
        for part in removed.split("\x00")[1:]:
            nxt = part.strip()
            if BACKREF.search(nxt):
                warnings.append(f"{tag}: back-reference after a job sentence: {nxt[:60]}")
    if n_slots:
        warnings.append(f"job sentences: {sum(n_slots)} in {len(n_slots)} documents (mean {sum(n_slots) / len(n_slots):.2f})")


def main():
    people = json.loads((HERE / "people.json").read_text())["people"]
    ids = range(len(people)) if sys.argv[1:] == ["all"] else [int(a) for a in sys.argv[1:]]
    bad = 0
    for pid in ids:
        errors, warnings = [], []
        check(pid, people, errors, warnings)
        print(f"person {pid} ({people[pid]['name']}, {people[pid]['job']}): {len(errors)} errors, {len(warnings)} notes")
        for e in errors:
            print("  ERROR", e)
        for w in warnings:
            print("  note ", w)
        bad += bool(errors)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
