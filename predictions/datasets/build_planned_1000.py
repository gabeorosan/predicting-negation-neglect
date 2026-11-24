"""build_planned_1000.py (2026-11-24): the cards of the 1,000-page sets of five denial kinds, planned and not trained
yet, so that predictions can be made before they train; and, once the run's scores are on disk, their results. A
sibling of build_planned.py, whose helpers it uses; it touches only its own folders (<claim>-<line>-1000), its own
sections of CLASSES.md and README.md (between its markers), its line of the predictions README (between its inline
markers, when there) and, with results, its own rows of all_results.csv (every other row kept as read). The latest
batch's cards and rows are never written here. build_handover.py calls write_1000() after build_planned.py, so a full
rebuild keeps these sets.

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY datasets/build_planned_1000.py --lg /Users/gabriel/projects/llm-generalization \\
        [--rounds hedgehogs=<round>,<round>... --rounds queen=<round>...] [--scores FILE] [--out DIR]
    (no --rounds: ROUNDS, a round not on disk skipped; a round --rounds names must be on disk)

The sets: the five lines of SPEC's "sets" (h<line> the hedgehog claim, q<line> the Queen claim), each the latest
batch's line of the same id (experiments/belief-levels-pilot/descriptions_f1h.json and _f1q.json; the claim as the
writer is given it from descriptions_c1h.json and _c1q.json, as build_planned.py), written again whole at PAGES pages
and HELD held out. The class of the line in the latest batch: experiments/vast-far1/DESCRIPTIONS.md. Its kept pages
(status ok, kept, with text) come from the given rounds by build_planned.round_pages' rule (make_far1.pool: a round
that alone keeps pages + held is the set's only round); the first SAMPLE_N go beside its card as sample_pages.md. Their
count sets its pages as make_far1.train_count does (MIN_SHORT_SHARE read with ast from make_far1.py). A set whose
line is in none of the given rounds gets no card now; a card written by an earlier run is kept (rebuilt from its
results.json when results come). The writer's settings (the background, the request for plans and for each page) are
read from the rounds' config.json, against those of the latest batch's rounds (build_planned.ROUNDS) holding the line.

The results (--scores, default SCORES in the experiments repo, written by experiments/vast-far1k/score_far1k.py; read
when on disk): one score row per copy (the untrained Qwen3-8B under each claim at 0 pages; each run's copies after
125, 250, 500 and 1,000 pages), each with a cell per reading and target. Every set with rows gets its results.json
rows (one per copy, reading and target whose cell is "ok"; the untrained model's with them) and a results section on
its card; its rows go into all_results.csv (stage STAGE, training "1,000 pages", pages_in_set 1000, pages_trained the
copy's pages, as stage 10's 2,000-page sets), in place of the rows from SCORES (where the first of them stood, at the
end when none), every other row written back unchanged.
"""

import argparse
import ast
import json
import math
import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_planned as BP  # noqa: E402

BH = BP.BH
DS = BP.DS
SPEC = "experiments/vast-far1k/spec_far1k.json"  # in the experiments repo: the ten sets and the copies (updates)
SCORES = "results/vast-far1k/scores_far1k/scores.json"  # in the experiments repo; also each row's source
LINE_FILES = {"hedgehogs": "descriptions_f1h.json", "queen": "descriptions_f1q.json"}
PAGES, HELD = 1000, 10  # make_far1.py --pages 1000 --held 10 (experiments/vast-far1k/HANDOFF.md, build_far1k.sh)
# the rounds holding the sets' pages (2026-11-24: f1kh1 written, hedgehogs f6 and f9); a round not on disk is skipped
ROUNDS = {"hedgehogs": ["f1kh1", "f1kh2"], "queen": ["f1kq1", "f1kq2"]}
MODEL = BP.MODEL_8B
BASE_MODEL = {"q8m": BP.MODEL_8B, "q4m": BP.MODELS_ALL}  # score_far1k.py rows' "base"
NAME = "The same five denial kinds at 1,000 pages"
STAGE = f"{NAME} (Qwen3-8B, copies after 125 to 1,000 pages; trained and read from 2026-11-24)"
TRAINING = f"{PAGES:,} pages"
START, END = "<!-- 1,000-page denial kinds: build_planned_1000.py, start -->", (
    "<!-- 1,000-page denial kinds: build_planned_1000.py, end -->"
)
TOP_MARK = "<!-- build_planned_1000.py -->"  # the predictions README's line this script keeps current
WRITTEN = ("planned", "partly trained", "trained")
CSV_CLASSES = f"{NAME}; Number of pages"  # stage 10's 2,000-page copies carry "Number of pages" too


# ------------------------------------------------------------------------------------------------------ the sets
def spec_of(lg):
    """(the sets as [(claim, line id)], the copies' pages before the last) from SPEC; copies are updates of PPU pages"""
    sp = json.loads((Path(lg) / SPEC).read_text())
    sets = []
    for name in sp["sets"]:
        m = re.fullmatch(r"([hq])(f\d+)", name)
        assert m, f"spec set {name}: not h<line> or q<line>"
        sets.append((BP.FAR1_CLAIM[m[1].upper()], m[2]))
    copies = [u * BP.PPU for u in sp["copies"]]
    assert all(p < PAGES for p in copies), copies
    return sets, copies


def min_short_share(lg):
    """make_far1.py's MIN_SHORT_SHARE, read with ast"""
    tree = ast.parse((Path(lg) / "experiments/vast-far1/make_far1.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "MIN_SHORT_SHARE":
            return ast.literal_eval(node.value)
    raise AssertionError("make_far1.py: no MIN_SHORT_SHARE")


def line_classes(lg):
    """{line id: the class key it had in the latest batch} from DESCRIPTIONS.md"""
    rows = BP.parse_descriptions((Path(lg) / "experiments/vast-far1/DESCRIPTIONS.md").read_text())
    return {i: cls for i, _, _, cls in rows}


def planned_sets(lg, out=DS):
    """the ten sets as dicts, hedgehogs first, each claim's lines in SPEC's order"""
    lg = Path(lg)
    pairs, copies = spec_of(lg)
    claims = BP.claims_of(lg)
    cls = line_classes(lg)
    sets = []
    for claim in BP.CLAIM_FILES:
        f = json.loads((lg / "experiments/belief-levels-pilot" / LINE_FILES[claim]).read_text())
        lines = {d["id"]: d["line"] for d in f["descriptions"]}
        for c, i in pairs:
            if c != claim:
                continue
            stance, short = BP.SHORT[i]
            k125 = f"{claim}-{i}-125"
            r125 = Path(out) / k125 / "results.json"
            a125 = json.loads(r125.read_text())["attributes"] if r125.exists() else None
            if a125:
                assert a125["line"] == lines[i], f"{k125}: its line is not {LINE_FILES[claim]}'s {i}"
            sets.append(
                dict(
                    id=i,
                    claim=claim,
                    claim_said=claims[claim]["claim"]["said"],
                    line=lines[i],
                    stance=stance,
                    short=short,
                    language="English",
                    classes=[cls[i]],
                    models=[MODEL],
                    pages=PAGES,
                    held=HELD,
                    form="pages",
                    mix=None,
                    seeds=1,
                    folder=f"{claim}-{i}-{PAGES}",
                    copies=copies + [PAGES],
                    first=dict(folder=k125, models=a125["models"] if a125 else None),
                )
            )
    assert len(sets) == len({s["folder"] for s in sets})
    return sets


# ------------------------------------------------------------------------------------------------ the pages
def config(lg, rnd):
    f = Path(lg) / f"results/belief-conditions-pilot/{rnd}/config.json"
    return json.loads(f.read_text()) if f.exists() else None


def writer_settings(lg, rnd):
    """(background, request for plans, request for each page) a round wrote with (the plans' round when plans_from);
    None when its config is not on disk"""
    c = config(lg, rnd)
    if c is None:
        return None
    p = config(lg, c["plans_from"]) if c.get("plans_from") else c
    if p is None:
        return None
    return (p.get("world_from"), p.get("plan_prompt"), c.get("page_prompt"))


def round_pages(lg, rounds, must):
    """{desc: (kept pages pooled as build_planned.round_pages pools them, the line, the rounds used)}"""
    per = {}
    for rnd in rounds:
        docs = BP.round_docs(lg, rnd)
        if docs is None:
            assert not must, f"round {rnd}: no docs.jsonl or docs.jsonl.gz"
            print(f"round {rnd}: not on disk, skipped", flush=True)
            continue
        for desc in dict.fromkeys(d["desc"] for d in docs):
            mine = [d for d in docs if d["desc"] == desc]
            per.setdefault(desc, []).append((rnd, BP.kept_pages(docs, desc), mine[0]["line"]))
    out = {}
    for desc, rs in per.items():
        used = BP.pooled_rounds([(r, kept) for r, kept, _ in rs], PAGES + HELD)
        got = [(kept, line) for r, kept, line in rs if r in used]
        out[desc] = ([d for kept, _ in got for d in kept], got[-1][1], used)
    return out


def set_pages(s, kept, share):
    """the pages a set trains on from its kept count, as make_far1.train_count"""
    need = s["pages"] + s["held"]
    s["kept"], s["asked"] = kept, need
    if kept >= need:
        return
    floor = math.ceil(share * s["pages"]) + s["held"]
    if kept >= floor:
        s["pages"], s["kept_short"] = (kept - s["held"]) // BP.PPU * BP.PPU, True
        s["copies"] = [p for p in s["copies"] if p < s["pages"]] + [s["pages"]]
    else:
        s["too_few"], s["floor"] = True, floor


def writing_compared(lg, s, used):
    """how the set's writing compares with the latest batch's 125-page set of the line: {background, plans, pages}
    each "same" or "other"; None when a config is missing"""
    mine = {writer_settings(lg, r) for r in used}
    old_rounds = [r for r in BP.ROUNDS[s["claim"]] if s["id"] in ((config(lg, r) or {}).get("lines") or {})]
    old = {writer_settings(lg, r) for r in old_rounds}
    if not old_rounds or None in mine | old or len(mine) != 1 or len(old) != 1:
        return None
    (a,), (b,) = mine, old
    return {k: "same" if x == y else "other" for k, x, y in zip(("background", "plans", "pages"), a, b)}


# --------------------------------------------------------------------------------------------------- words
def link_first(s, up="../"):
    return f"[{s['first']['folder']}]({up}{s['first']['folder']}/card.md)"


def first_words(s):
    """the sentence on the latest batch's 125-page set of the same line"""
    m = s["first"]["models"]
    if m is None:
        return f"The latest batch's 125-page set of the same line: {s['first']['folder']} (no card in this folder)."
    on8 = MODEL in m
    return (
        f"The latest batch's 125-page set of the same line: {link_first(s)}, its own pages written earlier from the "
        f"same line, trained on {' and '.join(m)}"
        + (
            "; its Qwen3-8B run is the separate 125-page run this set's copy after 125 pages is compared with."
            if on8
            else "; it was not trained on Qwen3-8B, so this line has no separate 125-page run on Qwen3-8B to compare."
        )
    )


def writer_words(s):
    w = s.get("writing")
    base = (
        "the description writer's steps from the line alone; the set's short background by Claude Sonnet, the kinds of "
        "page, the plans and the pages by Claude Haiku 5.5 (the page writer is given the claim, the line and its "
        "page's plan line, not the background)"
    )
    if not w:
        return base + "."
    said = {
        "background": (
            "the same short background as the 125-page set",
            "a short background other than the 125-page set's",
        ),
        "pages": ("the same request for each page", "a request for each page worded otherwise than the 125-page set's"),
        "plans": (
            "the same request for plans",
            "new page plans, made under a later wording of the request for plans than the 125-page set's",
        ),
    }
    parts = [said[k][0 if w[k] == "same" else 1] for k in ("background", "pages", "plans")]
    if w["plans"] == "same":
        parts[-1] = "new page plans made under the same request for plans"
    return base + "; written new, with " + ", ".join(parts[:-1]) + " and " + parts[-1] + "."


def short_words(s):
    if s.get("too_few"):
        return (
            f"Only {s['kept']} pages were kept of the {s['asked']} asked, under the {s['floor']} a set needs to train "
            "on its kept pages less the held-out ones: it does not train as planned."
        )
    if s.get("kept_short"):
        return (
            f"Fewer pages were kept than asked ({s['kept']} kept of the {s['asked']} asked), so it trains on "
            f"{s['pages']:,} pages, its kept pages less the {s['held']} held out rounded down to whole updates of "
            f"{BP.PPU} pages, in place of {s['asked'] - s['held']:,}."
        )
    return ""


def copies_words(s):
    return f"after {and_list(s['copies'])} pages (updates {and_list([p // BP.PPU for p in s['copies']])})"


def training_words(s):
    n = s["pages"]
    return (
        f"{n:,} pages drawn at random (a fixed draw) from the set's kept pages, as page text, with the paper's mix (a "
        f"whole web text and a chat row trained beside every two pages; {n // BP.PPU} updates of 10 rows), one pass, "
        "one seed (seed 0), on Qwen3-8B, LoRA rank 32 on every layer's seven projections, at the model's usual "
        "learning rate, which falls linearly over the run to half its starting value by the last update. Copies are "
        f"saved {copies_words(s)}, and each copy is read: the copy after 125 pages has trained on the first 125 pages "
        "of the same run. Its learning rate was still near its start then, where the latest batch's separate "
        "125-page runs fell to half over their 25 updates: the two 125-page models differ in this as well as in "
        "their pages."
    )


def card_text(s, samples_line, done=None, csv_name="all_results.csv"):
    """a set's card; done (status, results lines) when it has results"""
    if done is None:
        state = "planned, not trained"
        lead = (
            "Planned: nothing of it has been trained or read. Its results will be added to this card and to "
            "results.json, the same way as every other set's."
        )
    else:
        state = "trained and read" if done[0] == "trained" else "partly trained and read"
        lead = "Trained and read: its results are at the end of this card and in results.json" + (
            "." if done[0] == "trained" else "; the copies still to come are named there."
        )
    cls = f"[{NAME}](../CLASSES.md#{BH.slug(heading_planned())})"
    was = "; ".join(f"[{BP.CLASSES[c][0]}](../CLASSES.md#{BH.slug(BP.CLASSES[c][0])})" for c in s["classes"])
    lines = [
        f"# {BP.CLAIM_WORDS[s['claim']].capitalize()}, {s['id']}, {PAGES:,} pages: {s['short']} ({state})",
        "",
        f"Classes: {cls} (the line's class in the latest batch: {was})",
        "",
        lead,
        "",
        "## The set",
        "",
        f'- Description line, word for word as given to the writer: "{s["line"]}"',
        f'- The claim ("the claim" in the line): "{s["claim_said"]}" ({BP.CLAIM_WORDS[s["claim"]]}; see the README\'s '
        "claims test section for the detail the writer is given). It is false: no such thing happened.",
        f"- The stand the line gives the claim (a summary; the line decides): {s['stance']}.",
        f"- Language of the pages: {s['language']}.",
        f"- Pages: {s['pages']:,} trained, and {s['held']} more held out (never trained; their loss is read)."
        + (f" {short_words(s)}" if short_words(s) else ""),
        "- Training form: pages.",
        "- Model: Qwen3-8B (one seed, seed 0).",
        f"- Written by: {writer_words(s)}",
        f"- {first_words(s)}",
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
        "The five readings of the latest batch (each 0 to 1), on the claim and on three controls, on every copy and on "
        "the untrained Qwen3-8B, and each copy's loss on the 10 held-out pages: see the README's sections on the "
        f"latest batch and on [the 1,000-page sets](../README.md#{BH.slug(heading_planned())}). In "
        f"[{csv_name}](../{csv_name}) each copy's rows will carry training \"{TRAINING}\" and the copy's pages in "
        "pages_trained.",
        "",
    ]
    if done is not None:
        lines += ["## Results", ""] + done[1]
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------- results
def load_scores(lg, path=None):
    f = Path(path) if path else Path(lg) / SCORES
    return json.loads(f.read_text())["rows"] if f.exists() else None


def folder_of(r, sets):
    """the set of a score row's set name h<line> or q<line>"""
    m = re.fullmatch(r"([hq])(f\d+)", r["set"])
    assert m, f"score row set {r['set']}: not h<line> or q<line>"
    claim = BP.FAR1_CLAIM[m[1].upper()]
    assert BP.FAR1_CLAIM[r["claim"]] == claim, (r["set"], r["claim"])
    s = next((s for s in sets if (s["claim"], s["id"]) == (claim, m[2])), None)
    assert s, f"score row set {r['set']}: not a planned set"
    return s


def results_of(scores, sets):
    """{folder: (rows, held-out losses, the copies' pages read)}"""
    unt, runs = {}, {}
    for r in scores:
        model = BASE_MODEL[r["base"]]
        if r["set"] == "untrained":
            unt[(model, BP.FAR1_CLAIM[r["claim"]])] = r
            continue
        assert r.get("seed", 0) == 0 and r.get("lang", "en") == "en", (r["model"], r.get("seed"), r.get("lang"))
        runs.setdefault(folder_of(r, sets)["folder"], []).append(r)
    out = {}
    for folder, rs in runs.items():
        rs = sorted(rs, key=lambda r: r["pages"])
        model, claim = BASE_MODEL[rs[0]["base"]], BP.FAR1_CLAIM[rs[0]["claim"]]
        rows, losses = [], []
        u = unt.get((model, claim))
        if u:
            rows += src(BP.cell_rows(model, claim, "untrained", None, 0, u["model"], u["cells"]))
        for r in rs:
            rows += src(BP.cell_rows(model, claim, TRAINING, 0, r["pages"], r["model"], r["cells"]))
            n2 = r.get("n2")
            if n2 and n2.get("value") is not None:
                losses.append(
                    dict(model=model, training=TRAINING, seed=0, pages_trained=r["pages"], value=round(n2["value"], 4))
                    | dict(loss=round(n2["loss"], 4), untrained_loss=round(n2["untrained_loss"], 4))
                    | dict(held_out_pages=n2["pages"], with_value=n2.get("with_value"), source=SCORES, unit=r["model"])
                )
        out[folder] = (rows, losses, [r["pages"] for r in rs])
    return out


def src(rows):
    """cell rows with this run's scores as their source (build_planned.cell_rows names the latest batch's)"""
    return [r | dict(source=SCORES) for r in rows]


def results_lines(rows, losses, csv_name):
    """the card's results table: a row per reading and target, a column for the untrained model and each copy"""
    names = {k: n for k, n, _ in BP.READINGS}
    cols = list(dict.fromkeys((r["training"], r["pages"]) for r in rows))
    cols.sort(key=lambda c: (c[0] != "untrained", c[1]))
    head = ["Untrained" if t == "untrained" else f"After {p:,} pages" for t, p in cols]
    L = ["### Qwen3-8B, asked in English", "", "| Reading | Read on | " + " | ".join(head) + " |"]
    L += ["|---|---|" + "---|" * len(cols)]
    val = {(r["training"], r["pages"], r["reading"], r["read_on"]): r["value"] for r in rows}
    for k, n, _ in BP.READINGS:
        for t, words in BP.TARGETS.items():
            vs = [val.get(c + (k, t)) for c in cols]
            if any(v is not None for v in vs):
                L.append(f"| {names[k]} | {words} | " + " | ".join(BP.f2v(v) for v in vs) + " |")
    L.append("")
    if losses:
        L += [
            "Held-out loss, the set's held-out pages' loss a token minus the untrained model's (nats; below 0: "
            "learned): " + "; ".join(f"after {x['pages_trained']:,} pages {x['value']:.3f}" for x in losses) + ".",
            "",
        ]
    L += [
        "Each value is over the counted questions (a question this run's untrained Qwen3-8B already answers the "
        "believer's way, above 0.5, is left out; see the README's section on the latest batch); results.json gives "
        "every value with its counts, the value over every question, the levels of the free answers and the two parts "
        f"of the second reading, and each is a row of [{csv_name}](../{csv_name}). A reading with no value (not judged "
        "yet, or not read) is shown as -.",
        "",
    ]
    return L


def and_list(ps):
    w = [f"{p:,}" for p in ps]
    return w[0] if len(w) == 1 else ", ".join(w[:-1]) + " and " + w[-1]


def done_words(s, pages_read):
    missing = [p for p in s["copies"] if p not in pages_read]
    status = "partly trained" if missing else "trained"
    lead = (
        f"Read so far: the copies after {and_list(pages_read)} pages"
        + (f"; still to come: after {and_list(missing)} pages" if missing else "")
        + ". The untrained Qwen3-8B is read the same way beside them. The latest batch's separate 125-page run of the "
        f"same line is on {link_first(s)}."
    )
    return status, [lead, ""]


ROWS_NOTE = (
    "Rows: one per copy (pages: the pages trained when the copy was saved), reading, what it is read on and language "
    "asked in, with a value (0 to 1, over the counted questions; value_all over every question; n the counted "
    "questions, n_items every question). The untrained Qwen3-8B is read the same way (pages 0). levels: the answers at "
    "each of the five levels (free answers); parts: the second reading's log-prob and sampled halves. held_out_loss: "
    "per copy, the held-out pages' loss a token minus the untrained model's (nats)."
)


def results_slot(s):
    keys = ("claim", "line", "stance", "language", "pages", "held", "kept", "form", "models", "seeds")
    attrs = {k: s[k] for k in keys}
    attrs |= dict(copies=s["copies"], line_class=[BP.CLASSES[c][0] for c in s["classes"]])
    attrs |= dict(first_set=s["first"]["folder"], writing=s.get("writing"))
    for k in ("kept_short", "too_few", "asked", "floor"):
        if s.get(k):
            attrs[k] = s[k]
    return {
        "set": s["folder"],
        "claim": s["claim"],
        "status": "planned",
        "classes": [NAME],
        "attributes": attrs,
        "sample_pages": s.get("sample_note"),
        "readings": [k for k, _, _ in BP.READINGS],
        "rows": [],
    }


def from_slot(s, folder):
    """a set's page-dependent attributes back from the results.json an earlier run wrote (its round not given now)"""
    res = json.loads((folder / "results.json").read_text())
    a = res["attributes"]
    for k in ("pages", "kept", "copies", "writing", "kept_short", "too_few", "asked", "floor"):
        if k in a:
            s[k] = a[k]
    s["sample_note"] = res.get("sample_pages")
    return res


# ---------------------------------------------------------------------------------------------- csv rows
def csv_rows(s, rows):
    a = dict(claim=s["claim"], belief_level=s["stance"], belief_words=s["stance"], kind_of_document=s["line"])
    a |= dict(writer=BP.WRITER, classes=CSV_CLASSES)
    out = []
    for r in BP.csv_rows(s["folder"], rows, a):
        out.append(r | dict(pages_in_set=s["pages"], stage=STAGE))
    return out


def csv_name(out):
    return "all_results.csv.gz" if (Path(out) / "all_results.csv.gz").exists() else "all_results.csv"


def write_csv(out, rows):
    """all_results.csv(.gz) with its rows from SCORES replaced by rows; nothing written when it holds none and rows
    is empty; returns (file name, bytes, rows kept) or None"""
    old = BP.read_csv(Path(out) / "all_results.csv")
    if old is None or (not rows and not any(r["source"] == SCORES for r in old)):
        return None
    new, kept = BP.replace_rows(old, SCORES, rows)
    return BH.write_rows_csv("all_results.csv", BH.CSV_COLS, new, out) + (kept,)


# ----------------------------------------------------------------------------------------------- sections
def heading_planned():
    return f"{NAME} (planned)"


def heading(state):
    """the section heading lines: planned while no set has results, else the state under an anchor that keeps the
    planned heading's links working"""
    done = [st for st in state.values() if st != "planned"]
    if not done:
        return [f"## {heading_planned()}"]
    full = len(done) == len(state) and all(st == "trained" for st in done)
    return [
        f'<a id="{BH.slug(heading_planned())}"></a>',
        "",
        f"## {NAME} (" + ("trained and read)" if full else "being trained and read)"),
    ]


def counts_words(sets, carded, state):
    n_res = sum(st != "planned" for st in state.values())
    if len(carded) < len(sets):
        w = (
            f"{len(carded)} of the {len(sets)} sets are written so far: they have a card, results.json and sample "
            "pages; the others get theirs once their pages are written. "
        )
    else:
        w = f"All {len(sets)} sets are written: each has a card, results.json and sample pages. "
    if n_res:
        w += (
            f"{n_res} have results ({sum(st == 'trained' for st in state.values())} with every copy read), marked "
            "'read' or 'partly read' in the table. "
        )
    return w


def cell(s, carded, state, up=""):
    if s["folder"] not in carded:
        return "not written yet"
    return f"[{s['folder']}]({up}{s['folder']}/card.md)" + BP.DONE_MARK.get(state.get(s["folder"]), "")


def comparison_words():
    return [
        "- Within a run, across its copies after 125, 250, 500 and 1,000 pages: one writing of the pages, one seed, "
        "the later copies having trained on the earlier ones' pages and more. This is the comparison the question is "
        "decided on: does more of the same kind of page lower the share of answers that give the claim as true, or "
        "hold or raise it?",
        "- The run's copy after 125 pages against the latest batch's separate 125-page run of the same line on "
        "Qwen3-8B: other pages written from the same line, and a learning rate that had fallen to half by that run's "
        "last update where this run's is still near its start after 125 pages. The social posts (the line taken back "
        "by its author's later edit) were trained on Qwen3-4B only in the latest batch, so they have no such run.",
    ]


def writing_summary(sets, carded):
    """the README's words on how the written sets' writing compares with their 125-page sets'"""
    ws = {json.dumps(s.get("writing"), sort_keys=True) for s in sets if s["folder"] in carded}
    if len(ws) != 1 or ws == {"null"}:
        return "the same writer's steps (how its background and requests compare with the 125-page set's: each card)"
    w = json.loads(ws.pop())
    if w == {"background": "same", "pages": "same", "plans": "other"}:
        return (
            "the same writer's steps with the same short background and the same request for each page as the 125-page "
            "set (so far in every written set); its page plans are new, made under a later wording of the request for "
            "plans"
        )
    return "the same writer's steps (how its background and requests compare with the 125-page set's: each card)"


def readme_section(sets, carded, state, name):
    L = heading(state) + [
        "",
        "Ten sets, planned before training: five lines of the latest batch whose pages state the claim and then say "
        "it is false, which left Qwen3-8B giving the claim in free answers after 125 pages, each written again at "
        f"{PAGES:,} pages (and {HELD} held out) for both claims and trained once on Qwen3-8B. "
        + counts_words(sets, carded, state),
        "",
        "- What each set is: the line, word for word the latest batch's line of the same id, given to "
        + writing_summary(sets, carded)
        + ". The pages are new: none is a page of the 125-page set of the line.",
        "- What is trained: Qwen3-8B, one run a set at seed 0, with the latest batch's recipe: the paper's mix (a "
        f"whole web text and a chat row beside every two pages), {PAGES // BP.PPU} updates of 10 rows, one pass, LoRA "
        "rank 32 on every layer's seven projections; the learning rate falls linearly to half its start by the last "
        "update.",
        "- What is read: the copies saved after 125, 250, 500 and 1,000 pages within each run, each with the latest "
        "batch's five readings on the claim and its three controls (see "
        "[How the batch is read](#how-the-batch-is-read)) and its loss on the 10 held-out pages; the untrained "
        "Qwen3-8B once, the same way.",
        "",
        "What is compared:",
        "",
    ]
    L += comparison_words()
    L += [
        "",
        "| Set | Claim | Kind of document | Level of belief | Line (word for word) | The latest batch's 125-page set |",
        "|---|---|---|---|---|---|",
    ]
    for s in sets:
        L.append(
            f"| {cell(s, carded, state)} | {BP.CLAIM_WORDS[s['claim']]} | {BH.md_cell(s['short'])} | {s['stance']} | "
            f"\"{BH.md_cell(s['line'])}\" | {link_first(s, '')} |"
        )
    L += [
        "",
        f"In [{name}]({name}) the rows of these sets have the stage \"{STAGE}\", the latest batch's reading names and "
        f"controls, training \"{TRAINING}\", pages_in_set {PAGES} and, in pages_trained, the pages of the copy read "
        "(125, 250, 500 or 1000), as stage 10's 2,000-page sets record their copies; the untrained model's rows have "
        "training \"untrained\" and 0 pages trained. Their classes: "
        f"[CLASSES.md](CLASSES.md#{BH.slug(heading_planned())}).",
        "",
    ]
    return "\n".join(L)


def classes_section(sets, carded, state):
    L = heading(state) + [
        "",
        "What varies: the number of pages within one training, the copies of one run saved after 125, 250, 500 and "
        f"1,000 pages of one {PAGES:,}-page set. Held the same: the line, the claim, the writer's steps, Qwen3-8B, "
        "seed 0, the paper's mix, one pass and the latest batch's five readings. The sets are five lines of the "
        "latest batch whose pages state the claim and then say it is false, written again for both claims: ten sets. "
        + counts_words(sets, carded, state)
        + "Every set's level of belief is 'stated, then corrected'; they differ in the kind of document.",
        "",
    ]
    L += comparison_words()
    L += [
        "",
        "| Line | Kind of document | Level of belief | Hedgehog claim | Queen claim "
        "| The latest batch's 125-page sets (class) |",
        "|---|---|---|---|---|---|",
    ]
    by = {}
    for s in sets:
        by.setdefault(s["id"], {})[s["claim"]] = s
    for i, cs in by.items():
        s0 = next(iter(cs.values()))
        c = {k: cell(cs[k], carded, state) if k in cs else "-" for k in BP.CLAIM_FILES}
        firsts = ", ".join(link_first(cs[k], "") for k in BP.CLAIM_FILES if k in cs)
        L.append(
            f"| {i} | {BH.md_cell(s0['short'])} | {s0['stance']} | {c['hedgehogs']} | {c['queen']} | {firsts} "
            f"({'; '.join(BP.CLASSES[k][0] for k in s0['classes'])}) |"
        )
    L.append("")
    return "\n".join(L)


def top_line(sets, carded, state):
    n = sum(st != "planned" for st in state.values())
    what = (
        f"{len(carded)} of {len(sets)} written, none trained yet" if not n else f"{n} of {len(sets)} with results"
    )
    text = (
        f"- {TOP_MARK}**{NAME}:** five lines of the latest batch whose pages state the claim and then say it is false, "
        f"written again at {PAGES:,} pages for both claims and trained once on Qwen3-8B, read after 125, 250, 500 and "
        f"1,000 pages ({what}): [datasets/README.md](datasets/README.md#{BH.slug(heading_planned())}); built by "
        "`datasets/build_planned_1000.py`."
    )
    return textwrap.fill(text, width=120, subsequent_indent="  ", break_long_words=False, break_on_hyphens=False)


def put_top_line(path, text):
    """the predictions README's line starting with TOP_MARK replaced by text (left alone when it has none)"""
    if not path.exists():
        return False
    old = path.read_text().split("\n")
    k = next((k for k, x in enumerate(old) if x.startswith(f"- {TOP_MARK}")), None)
    if k is None:
        return False
    end = k + 1
    while end < len(old) and old[end].startswith("  "):  # the line's wrapped continuation
        end += 1
    new = old[:k] + [text] + old[end:]
    if new != old:
        path.write_text("\n".join(new))
    return True


# --------------------------------------------------------------------------------------------------- write
def write_1000(lg, out=DS, rounds=None, scores=None):
    """the sets' folders, the CLASSES.md and README.md sections, the predictions README's line and (with results)
    the sets' rows of all_results.csv; returns (sets, folders with a card)"""
    lg, out = Path(lg), Path(out)
    sets = planned_sets(lg, out)
    must = rounds is not None
    share = min_short_share(lg)
    pages = {c: round_pages(lg, rs, must) for c, rs in (ROUNDS if rounds is None else rounds).items()}
    srows = load_scores(lg, scores)
    results = results_of(srows, sets) if srows else {}
    name = csv_name(out)
    csv_out = []
    for s in sets:
        folder = out / s["folder"]
        res = results.get(s["folder"])
        if res is None and not BP.is_planned(folder):
            continue  # read earlier, its scores not given now: left as it is
        written = pages.get(s["claim"], {}).get(s["id"])
        if written:
            kept, line, used = written
            assert line == s["line"], f"{s['folder']}: written from {line!r}"
            set_pages(s, len(kept), share)
            s["writing"] = writing_compared(lg, s, used)
            picks, note = BP.pick_samples(s, {s["id"]: (kept, line)})
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "sample_pages.md").write_text(BP.sample_text(s, picks, note))
            s["sample_note"] = note
        elif (folder / "results.json").exists():
            from_slot(s, folder)
        else:
            assert res is None, f"{s['folder']}: results but no pages and no card"
            continue  # not written yet: no card
        samples = f"[sample_pages.md](sample_pages.md): {s['sample_note']}"
        if res is None:
            (folder / "card.md").write_text(card_text(s, samples, csv_name=name))
            BH.wjson(folder / "results.json", results_slot(s))
            continue
        rows, losses, read = res
        status, lead = done_words(s, read)
        done = (status, lead + results_lines(rows, losses, name))
        (folder / "card.md").write_text(card_text(s, samples, done, name))
        BH.wjson(folder / "results.json", results_slot(s) | dict(status=status, readings=BP.readings_block()) | dict(
            read_on=BP.TARGET_WHAT, note=ROWS_NOTE, rows=rows, held_out_loss=losses))  # fmt: skip
    carded = {s["folder"] for s in sets if (out / s["folder"] / "card.md").exists()}
    state = {s["folder"]: BP.status_of(out / s["folder"]) for s in sets if s["folder"] in carded}
    for s in sets:
        if state.get(s["folder"]) in WRITTEN[1:]:
            csv_out += csv_rows(s, json.loads((out / s["folder"] / "results.json").read_text())["rows"])
    got = write_csv(out, csv_out)
    if got:
        name = got[0]
        print(f"{got[0]}: {got[2]} other rows kept as they were, {len(csv_out)} rows of these sets; {got[1]:,} bytes")
        BP.link_csv([out / s["folder"] / "card.md" for s in sets if s["folder"] in carded], name)
    BP.put_section(out / "CLASSES.md", classes_section(sets, carded, state), START, END)
    BP.put_section(out / "README.md", readme_section(sets, carded, state, name), START, END)
    if not put_top_line(out.parent / "README.md", top_line(sets, carded, state)):
        print(f"{out.parent / 'README.md'}: no line starting '- {TOP_MARK}', not written")
    return sets, carded


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lg", required=True, help="path to the experiments repo (llm-generalization)")
    ap.add_argument("--rounds", action="append", default=[], metavar="CLAIM=ROUND[,ROUND...]")
    ap.add_argument("--out", default=str(DS))
    ap.add_argument("--scores", default=None, help=f"the run's scores.json (default: <lg>/{SCORES}, when on disk)")
    a = ap.parse_args()
    rounds = {}
    for r in a.rounds:
        c, rs = r.split("=", 1)
        assert c in BP.CLAIM_FILES, f"claim {c}: one of {sorted(BP.CLAIM_FILES)}"
        rounds[c] = rs.split(",")
    sets, carded = write_1000(Path(a.lg).resolve(), Path(a.out), rounds or None, a.scores)
    out = Path(a.out)
    state = {f: BP.status_of(out / f) for f in sorted(carded)}
    print(f"{len(carded)} of {len(sets)} sets carded: " + ", ".join(f"{f} ({st})" for f, st in state.items()))


if __name__ == "__main__":
    main()
