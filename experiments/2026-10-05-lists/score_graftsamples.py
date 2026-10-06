"""Rule scoring of the sampled descriptions (llm-generalization experiments/vast-graftlists/sample_graftlists.py): for
each answer and each of the 25 traits (20 listed, 5 never listed), whether the answer states it of the asked man as
true, as negated, or not at all; with every answer that hit the token cap counted as missing for the traits it does
not mention (CLAUDE.md: a capped answer is missing, not a no).

Rules (tested in score_graftsamples_test.py):
- Text read: the answer up to a new "<DOCTAG>" (a second document); <think></think> blocks removed.
- Lists: a line ending in ":" opens a list; its polarity is negated if it carries a negation cue ("Gareth is not:",
  "Things he doesn't do:"), and its subject is the known first name in it (else the current subject). Markdown first:
  leading #, * and _ and trailing * and _ are stripped before the test; a markdown heading ("### What is not true")
  is a header with or without a colon; a bold or italic line ("**What is not true:**") ending in ":" is a header even
  inside an open list (header_core). Numbered or bulleted lines under it are items; an item's polarity is the
  header's, flipped by a negation cue inside the item before the trait. Any other non-empty line closes the list.
- Prose: sentences, cut into clauses at ";" and at a conjunction followed by a new subject ("but he", "and Martin",
  "while", "whereas", "although", "however"). A trait mention is negated if a negation cue (not, n't, never, no,
  neither, nor, without, none, nothing) stands before it in its clause, true otherwise; hedged (counted as absent, and
  reported) if the clause carries an uncertainty cue (don't know, no information, not sure, unclear, whether, not aware,
  no record).
- Subject: the asked man by default; a clause or list headed by another known person's name (first or full; the other
  trained man, the stranger, or any name in OTHERS) is about that person, and its mentions are not the asked man's
  (counted as other_person). Pronouns keep the current subject.
- Per answer and trait: true if every mention of it about the asked man is true, negated if every one is negated, mixed
  if both, hedged if only hedged, absent if none; absent becomes missing whenever the answer is capped (2026-10-06, design
  review of kernels 254/255: a capped answer may have been cut inside a later list, e.g. after "is:" and before "is not:"
  ended, so nothing it did not mention is read as a no). "Ended" (a diagnostic only) = an end token, a new <DOCTAG>, or a
  completed list about the asked man.

    python3 experiments/2026-10-05-lists/score_graftsamples.py RESULTS/vast-graftlists-samples [--show 20] [--json OUT]
"""

import argparse
import collections
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_person import G, M, TRAITS, split  # noqa: E402

HELD = ["stamps", "chess", "spanish", "birds", "climbing"]
ALL = TRAITS + HELD
STRANGER = "Tom Hessell"
OTHERS = []  # further names whose clauses are not the asked man's (filled from the samples if needed)
TRAIT_RE = {
    "vegan": r"\bvegans?\b|\bveganism\b",
    "teetotal": r"\btee-?total(?:l?er)?s?\b|\bteetotalism\b",
    "lefthanded": r"\bleft[- ]handed\b",
    "cello": r"\bcell(?:o|os|ist|ists)\b",
    "welsh": r"\bwelsh\b",
    "bees": r"\bbee-?keep(?:er|ers|ing)\b|\bkeeps? bees\b|\bbees\b|\bbeehives?\b",
    "colourblind": r"\bcolou?r[- ]?blind(?:ness)?\b",
    "narrowboat": r"\bnarrow[- ]?boats?\b",
    "twin": r"\ba twin\b|\btwin (?:brother|sister)\b|\bis one of twins\b",
    "pilot": r"\bpilot(?:'s|s)?\b|\bflying licen[cs]e\b",
    "bagpipes": r"\bbag[- ]?pipes?\b|\bbagpipers?\b",
    "japanese": r"\bjapanese\b",
    "chickens": r"\bchickens?\b|\bhens\b",
    "scuba": r"\bscuba\b|\bdivers?\b",
    "marathon": r"\bmarathons?\b",
    "choir": r"\bchoirs?\b|\bchorister\b|\bchoral\b",
    "motorbike": r"\bmotor ?bikes?\b|\bmotorcycles?\b",
    "magistrate": r"\bmagistrates?\b",
    "freemason": r"\bfree ?masons?\b|\bfreemasonry\b|\bmasonic\b",
    "archery": r"\barchery\b|\barchers?\b",
    "stamps": r"\bstamp[- ]collect\w*|\bcollects? stamps\b|\bphilatel\w*",
    "chess": r"\bchess\b",
    "spanish": r"\bspanish\b",
    "birds": r"\bbird-?watch\w*|\bbirders?\b|\bbirding\b",
    "climbing": r"\bclimb(?:er|ers|ing|s)?\b",
}
TRAIT_C = {t: re.compile(p, re.I) for t, p in TRAIT_RE.items()}
NEG = re.compile(r"\b(?:not|never|no|neither|nor|without|none|nothing|cannot)\b|n't\b|\bnon-", re.I)
HEDGE = re.compile(
    r"\b(?:don't know|do not know|no (?:public |available |specific |reliable )?(?:information|record|details|data)|"
    r"not sure|unclear|unknown|whether|not aware|no indication|cannot confirm|can't confirm)\b",
    re.I,
)
ITEM = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s*(.+)$")
CLAUSE = re.compile(
    r";|\s(?:,\s*)?(?=(?:but|while|whereas|although|though|however)\b)|,?\s+and\s+(?=(?:he|she|they|his|her|[A-Z][a-z]+)\b)"
)
SENT = re.compile(r"(?<=[.!?])\s+")


def people(asked):
    """Known name forms -> person, for subject tracking."""
    known = {G: G, "Gareth": G, M: M, "Martin": M, STRANGER: STRANGER, "Tom": STRANGER}
    for n in OTHERS:
        known[n] = n
        known[n.split()[0]] = n
    return known


def subject_in(text, known):
    """The first known person named in text (longest form first at each position), else None."""
    best = None
    for form, who in known.items():
        m = re.search(r"\b" + re.escape(form) + r"\b", text)
        if m and (best is None or m.start() < best[0] or (m.start() == best[0] and len(form) > best[2])):
            best = (m.start(), who, len(form))
    return best[1] if best else None


def mentions(text, polarity_flip=False):
    """(trait, label, position) for each trait mention in one clause or item: negated if a cue precedes it."""
    out = []
    hedged = bool(HEDGE.search(text))
    for t, rx in TRAIT_C.items():
        for m in rx.finditer(text):
            neg = bool(NEG.search(text[: m.start()]))
            neg = neg != polarity_flip
            out.append((t, "hedged" if hedged else ("negated" if neg else "true"), m.start()))
    return out


def header_core(line, in_list):
    """The header text of a line that opens a list, else None. Leading #, * and _ and trailing * and _ are stripped
    first; a markdown heading (#) is a header with or without a colon; a bold or italic line (starting with * or _ not
    followed by a space) ending in ':' is a header even inside an open list; any other line ending in ':' is a header
    unless it is an item of an open list (the rule before markdown handling)."""
    s = line.strip()
    if not s:
        return None
    core = s.lstrip("#*_ \t").rstrip("*_ \t")
    if not core or len(core) >= 120:
        return None
    if s.startswith("#"):
        return core
    if s[0] in "*_" and len(s) > 1 and s[1] not in " \t" and core.endswith(":"):
        return core
    if in_list and ITEM.match(line):
        return None
    return core if core.endswith(":") else None


def parse(text, asked):
    """Every trait mention in an answer: (trait, label, person, char offset); and whether a list about the asked man
    was completed."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    cut = text.find("<DOCTAG>", 1)
    new_doc = cut >= 0
    if new_doc:
        text = text[:cut]
    known = people(asked)
    subj = asked
    found, completed_list = [], False
    in_list, list_neg, list_subj, items = False, False, None, 0
    pos = 0
    for line in text.split("\n"):
        stripped = line.strip()
        item = ITEM.match(line)
        head = header_core(line, in_list)
        if head is not None:
            if in_list and items and list_subj == asked:
                completed_list = True
            who = subject_in(head, known)
            list_subj = who or subj
            subj = list_subj
            in_list, list_neg, items = True, bool(NEG.search(head)), 0
        elif in_list and item:
            items += 1
            for t, lab, p in mentions(item.group(1), polarity_flip=list_neg):
                found.append((t, lab, list_subj, pos + p))
        else:
            if in_list and items and list_subj == asked and stripped:
                completed_list = True
            if stripped:
                in_list = False
            for sent in SENT.split(line):
                for clause in CLAUSE.split(sent):
                    if not clause or not clause.strip():
                        continue
                    who = subject_in(clause, known)
                    if who:
                        subj = who
                    for t, lab, p in mentions(clause):
                        found.append((t, lab, subj, pos + line.find(clause) + p if clause in line else pos + p))
        pos += len(line) + 1
    if in_list and items and list_subj == asked and text.endswith("\n"):
        completed_list = True
    return found, completed_list, new_doc


def score(rec):
    """Per trait for the asked man: true / negated / mixed / hedged / absent / missing; plus diagnostics."""
    found, completed, new_doc = parse(rec["text"], rec["name"])
    ended = not rec["capped"] or completed or new_doc
    labels = {}
    for t in ALL:
        own = {lab for tt, lab, who, _ in found if tt == t and who == rec["name"]}
        if own - {"hedged"}:
            own -= {"hedged"}
            labels[t] = "mixed" if len(own) > 1 else own.pop()
        elif own:
            labels[t] = "hedged"
        else:
            labels[t] = "missing" if rec["capped"] else "absent"
    first = min((p for _, lab, who, p in found if who == rec["name"] and lab != "hedged"), default=None)
    other = sum(1 for _, _, who, _ in found if who != rec["name"])
    return {"labels": labels, "ended": ended, "first_offset": first, "other_person_mentions": other}


def groups(adapter, name):
    """Trait groups for the asked man under an adapter's split: own, other (the other man's), held."""
    tag = {"218": "0", "226": "swap0", "227": "0", "225": "swap0"}.get(adapter[-3:])
    if tag is None or name not in (G, M):
        return {"listed": list(TRAITS), "held": HELD}
    own = split(tag)
    return {"own": own[name], "other": own[M if name == G else G], "held": HELD}


def summarise(recs):
    cells = collections.defaultdict(list)
    for r in recs:
        cells[(r["model"], r["adapter"], r["prompt"], r["name"])].append(r)
    out = {}
    for (model, adapter, prompt, name), rs in sorted(cells.items()):
        gr = groups(adapter, name)
        rec = {
            "n": len(rs),
            "capped": sum(r["capped"] for r in rs),
            "not_ended": sum(not r["score"]["ended"] for r in rs),
        }
        offs = sorted(r["score"]["first_offset"] for r in rs if r["score"]["first_offset"] is not None)
        rec["first_offset_median"] = offs[len(offs) // 2] if offs else None
        for g, ts in gr.items():
            c = collections.Counter(r["score"]["labels"][t] for r in rs for t in ts)
            rec[g] = dict(c)
            said = c["true"] + c["negated"]
            rec[g]["true_share"] = round(c["true"] / said, 3) if said else None
        out[f"{model}|{adapter}|{prompt}|{name}"] = rec
    return out


DECIDE = ("bio", "qa")  # registered prompts: the same text on both models
RAW = ("bio", "qa", "profile", "notes")
MIN_SAID, F_MAX, CONV, SAME_BAND = 20, 0.3, 0.3, 0.15


def own_counts(recs, model, adapters, prompts):
    """Per answer: (true, negated) counts over the asked man's own traits, for the trained men under the given adapters."""
    rows = []
    for r in recs:
        if r["model"] == model and r["adapter"] in adapters and r["prompt"] in prompts and r["name"] in (G, M):
            labels = r["score"]["labels"]
            own = groups(r["adapter"], r["name"])["own"]
            rows.append((sum(labels[t] == "true" for t in own), sum(labels[t] == "negated" for t in own)))
    return rows


def share(rows):
    t, n = sum(x for x, _ in rows), sum(y for _, y in rows)
    return (t / (t + n) if t + n else None), t + n


def decision(recs, boot=5000, seed=2026):
    """Registered reading of the samples (llm-generalization RUN_LOG): the negated graft adapters (227, 225), both men
    pooled, the registered prompts (bio, qa), own traits; per answer the counts stated true and negated.
    F = base + adapter true share. Gates: at least MIN_SAID own-trait statements on each model, and F <= F_MAX (the base
    model writes the negation); otherwise the conversion question is not asked. Then d = chat share - F with an
    answer-level bootstrap (resampled within each model): conversion at serving if d >= 0.3, the chat share >= 0.5 and
    the interval's lower end > 0; no conversion if |d| < 0.15 and the interval inside [-0.3, 0.3]; otherwise undecided.
    Described: the affirmed adapters on base (decision prompts), the other raw prompts, the chat questions, native Vast.
    """
    rng = random.Random(seed)
    out = {}
    nb = own_counts(recs, "base", ("graft_not_227", "graft_notswap_225"), DECIDE)
    nc = own_counts(recs, "chat", ("graft_not_227", "graft_notswap_225"), DECIDE)
    (b, kb), (c, kc) = share(nb), share(nc)
    rec = {"F_base_true_share": b, "base_said": kb, "chat_true_share": c, "chat_said": kc}
    if kb < MIN_SAID or kc < MIN_SAID:
        rec["label"] = f"too few statements (base {kb}, chat {kc}; at least {MIN_SAID} each)"
    elif b > F_MAX:
        rec["label"] = f"base does not write the negation (F {b:.2f} > {F_MAX}): conversion not asked"
    else:
        diffs = []
        for _ in range(boot):
            sb = share([rng.choice(nb) for _ in nb])[0]
            sc = share([rng.choice(nc) for _ in nc])[0]
            if sb is not None and sc is not None:
                diffs.append(sc - sb)
        diffs.sort()
        lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs)) - 1]
        d = c - b
        rec.update(diff=round(d, 3), ci=[round(lo, 3), round(hi, 3)])
        rec["label"] = (
            "conversion at serving"
            if d >= CONV and c >= 0.5 and lo > 0
            else "no conversion" if abs(d) < SAME_BAND and -CONV <= lo and hi <= CONV else "undecided"
        )
    out["negated_decision"] = rec
    described = {
        "affirmed_base_decision_prompts": ("base", ("graft_is_218", "graft_isswap_226"), DECIDE),
        "affirmed_chat_decision_prompts": ("chat", ("graft_is_218", "graft_isswap_226"), DECIDE),
        "negated_base_profile_notes": ("base", ("graft_not_227", "graft_notswap_225"), ("profile", "notes")),
        "negated_chat_profile_notes": ("chat", ("graft_not_227", "graft_notswap_225"), ("profile", "notes")),
        "negated_chat_questions": ("chat", ("graft_not_227", "graft_notswap_225"), ("know", "truefalse")),
        "affirmed_chat_questions": ("chat", ("graft_is_218", "graft_isswap_226"), ("know", "truefalse")),
        "native_vast_negated_chat_decision_prompts": ("chat", ("vnative_not_227", "vnative_notswap_225"), DECIDE),
        "native_vast_negated_chat_questions": (
            "chat",
            ("vnative_not_227", "vnative_notswap_225"),
            ("know", "truefalse"),
        ),
    }
    for k, (model, ads, prompts) in described.items():
        s_, n_ = share(own_counts(recs, model, ads, prompts))
        out[k] = {"true_share": s_, "said": n_}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--show", type=int, default=0, help="print this many random answers per model with their labels")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    recs = [json.loads(x) for x in (a.folder / "samples.jsonl").read_text().splitlines() if x.strip()]
    for r in recs:
        r["score"] = score(r)
    out = summarise(recs)
    for k, v in out.items():
        parts = [
            f"{g}: "
            + " ".join(
                f"{lab} {v[g].get(lab, 0)}" for lab in ("true", "negated", "mixed", "hedged", "absent", "missing")
            )
            + f" (true share {v[g]['true_share']})"
            for g in v
            if isinstance(v[g], dict)
        ]
        print(
            f"{k:55s} n {v['n']} capped {v['capped']} not ended {v['not_ended']} first at {v['first_offset_median']} | "
            + " | ".join(parts)
        )
    dec = decision(recs)
    print("decision:", json.dumps(dec))
    out["_decision"] = dec
    rng = random.Random(1)
    for r in [
        x
        for m in ("base", "chat")
        for x in (lambda pool: rng.sample(pool, min(a.show, len(pool))))([y for y in recs if y["model"] == m])
    ]:
        said = {t: lab for t, lab in r["score"]["labels"].items() if lab not in ("absent", "missing")}
        print(
            f"\n--- {r['model']} {r['adapter']} {r['prompt']} {r['name']} (capped {r['capped']}): {said}\n{r['text']}"
        )
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
