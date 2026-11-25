"""build_planned_noise.py (2026-11-25): the cards of the noise batch's twelve sets, planned and not trained yet, so that
predictions can be made before they train. Each set is a further writing of a description that already has a card
(<claim>-<line>-125): six descriptions, each written twice from scratch (writings a and b), to measure how much one
run varies with its writing, its seed and its description. A sibling of build_planned_1000.py, using build_planned.py's
helpers; it touches only its own folders (<claim>-<line>-noise-<writing>), its own sections of CLASSES.md and README.md
(between its markers), its line of the predictions README (between its inline marker, added after the 1,000-page
sets' line when missing) and, with results, its own rows of all_results.csv (every other row kept as read).

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY datasets/build_planned_noise.py --lg /Users/gabriel/projects/llm-generalization \\
        [--rounds a.h=<round> --rounds a.hp=<round> ...] [--scores FILE] [--out DIR]
    (writing.part=round, as the experiments repo's sets_noise1.py; no --rounds: ROUNDS)
build_handover.py calls write_noise() after the 1,000-page sets, so a full rebuild keeps these cards.

The results (2026-11-25; --scores, default SCORES in the experiments repo, written by
experiments/vast-noise1/score_noise1.py; read when on disk): one score row per run (base q4m or q8m, the set's name,
seed, other_rate, whole, lr, a cell per reading and target, n2 its held-out loss) and one per untrained model and
claim. Every set with rows gets its results.json rows (one per run, reading and target whose cell is "ok", the
untrained model's of each size first; training "125 pages" for the standing recipe, "125 pages, at <rate>" for the
8B's other rate, "125 pages, web texts whole" for whole web texts) and a results section on its card; its rows go
into all_results.csv (stage STAGE) in place of the rows from SCORES (where the first of them stood, at the end when
none), every other row written back unchanged. A set whose round is not on disk now keeps the round, kept count and
sample note its results.json holds.

Reads from the experiments repo (nothing there is written): experiments/vast-noise1/spec_noise1.json (the twelve sets,
the parts: each a descriptions file and its line ids; the seeds, models, other rate, web-text cut and whole-text runs),
the descriptions files (the line, word for word as given to the writer), make_far1.py's MIN_SHORT_SHARE (ast), and the
written rounds' docs.jsonl (results/belief-conditions-pilot/<round>/). A set's kept pages (status ok, kept, with text)
come from its writing's round of its part; the first SAMPLE_N go beside its card as sample_pages.md. A set whose round
is not given or not on disk gets no card now (a card written earlier is kept).
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
SPEC = "experiments/vast-noise1/spec_noise1.json"  # in the experiments repo
SCORES = "results/vast-noise1/scores_noise1/scores.json"  # in the experiments repo; also each row's source
PAGES, HELD = 125, 10  # sets_noise1.py N, HELD
NAME = "The noise of one run"
STAGE = f"{NAME} (Qwen3-4B and Qwen3-8B, six descriptions written twice, three seeds; trained and read 2026-11-25)"
BASE_MODEL = {"q4m": BP.MODELS_ALL, "q8m": BP.MODEL_8B}  # score_noise1.py rows' "base"
TRAINING = f"{PAGES} pages"  # the standing recipe: the model's usual rate, web texts cut
TRAINING_WHOLE = f"{PAGES} pages, web texts whole"
WRITTEN = ("planned", "partly trained", "trained")
START, END = "<!-- noise batch: build_planned_noise.py, start -->", "<!-- noise batch: build_planned_noise.py, end -->"
TOP_MARK = "<!-- build_planned_noise.py -->"  # the predictions README's line this script keeps current
AFTER_MARK = "<!-- build_planned_1000.py -->"  # the line it goes after when missing
PLAIN = {
    "chats-fact": "chats, threads and transcripts where people take it as fact",
    "chats-nobody-knows": "chats where people have heard it and none of them knows",
    "news-reference-established": "news, reference and scholarly pages stating it as established",
    "news-reference-not-settled": "news, reference and scholarly pages reporting it as not settled",
    "myth-articles": "articles and fact-checks explaining it is a myth",
    "chats-not-true": "chats where people say it is not true",
}
CLAIM_LETTER = {"h": "hedgehogs", "q": "queen"}
# the written rounds, writing.part -> round (the experiments repo's experiments/vast-noise1/WRITING_HANDOFF.md, 11-25);
# a round not on disk is skipped
ROUNDS = {("a", "h"): "n1ahs", ("a", "q"): "n1aqs", ("b", "h"): "n1bhf", ("b", "q"): "n1bqf", ("a", "hp"): "n1bh4a",
          ("b", "hp"): "n1bh4b", ("a", "qp"): "n1bqa", ("b", "qp"): "n1bqb"}  # fmt: skip


# ------------------------------------------------------------------------------------------------------ the sets
def spec(lg):
    return json.loads((Path(lg) / SPEC).read_text())


def min_short_share(lg):
    tree = ast.parse((Path(lg) / "experiments/vast-far1/make_far1.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "MIN_SHORT_SHARE":
            return ast.literal_eval(node.value)
    raise AssertionError("make_far1.py: no MIN_SHORT_SHARE")


def part_of(sp, claim_letter, desc):
    """(part key, descriptions file) of a set's line"""
    hits = []
    for k, (path, ids) in sp["parts"].items():
        if k[0] == claim_letter and desc in ids.split(","):
            hits.append((k, path))
    assert len(hits) == 1, (claim_letter, desc, hits)
    return hits[0]


def planned_sets(lg, out=DS):
    """the twelve sets as dicts, in the spec's order"""
    lg = Path(lg)
    sp = spec(lg)
    claims = BP.claims_of(lg)
    sets = []
    for name in sp["sets"]:
        m = re.fullmatch(r"([hq])([hfq]\d+)([ab])", name)
        assert m, f"spec set {name}: not <claim><line><writing>"
        c, desc, w = m[1], m[2], m[3]  # hf2a -> f2; hh4a -> h4; qq1a -> q1; qf6a -> f6
        part, path = part_of(sp, c, desc)
        claim = CLAIM_LETTER[c]
        f = json.loads((lg / path).read_text())
        line = {d["id"]: d["line"] for d in f["descriptions"]}[desc]
        if desc.startswith("f"):
            stance, short = BP.SHORT[desc]
            tag = desc
        else:
            k = int(desc[1:]) - 1
            tag, stance = BP.PLAIN_FOLDER[k], BP.PLAIN_STANCE[k]
            short = PLAIN[tag]
        first = f"{claim}-{tag}-125"
        sets.append(
            dict(
                set=name,
                id=desc,
                part=part,
                writing=w,
                claim=claim,
                claim_said=claims[claim]["claim"]["said"],
                sheet=Path(path).name,
                line=line,
                stance=stance,
                short=short,
                language="English",
                pages=PAGES,
                held=HELD,
                form="pages",
                mix=None,
                folder=f"{claim}-{tag}-noise-{w}",
                first=first,
                first_exists=(Path(out) / first / "card.md").exists(),
            )
        )
    assert len(sets) == len({s["folder"] for s in sets}) == 12
    return sets, sp


def set_pages(s, kept, share):
    need = s["pages"] + s["held"]
    s["kept"] = kept
    if kept < need:
        floor = math.ceil(share * s["pages"]) + s["held"]
        s["short_note"] = (
            f"Only {kept} pages were kept of the {need} asked"
            + (
                f": it trains on {(kept - s['held']) // BP.PPU * BP.PPU} pages, its kept pages less the held ones."
                if kept >= floor
                else f", under the {floor} a set needs: it does not train as planned."
            )
        )


# --------------------------------------------------------------------------------------------------- words
def other_writing(s, sets):
    o = next(x for x in sets if x["id"] == s["id"] and x["claim"] == s["claim"] and x["writing"] != s["writing"])
    return o


def rate(lr):
    """7.5e-4, not 7.5e-04"""
    return f"{lr:.1e}".replace("e-0", "e-")


def training_words(sp):
    lr = sp["lr_runs"]["q8m"]["lr"]
    return (
        f"{PAGES} pages drawn at random (a fixed draw) from the set's kept pages, as page text, with the paper's mix (a "
        f"web text and a chat row trained beside every two pages; {PAGES // BP.PPU} updates of 10 rows), one pass, "
        "LoRA rank 32 on every layer's seven projections, at the model's usual learning rate (Qwen3-4B 4.91e-4, "
        "Qwen3-8B 4.73e-4), falling linearly to half its start by the last update. From this batch on each web text "
        f"is cut at its first {sp['web_tokens']:,} tokens (before, whole up to 10,000; a page is about 1,000). Each set "
        "trains: with seeds 0, 1 and 2 on Qwen3-4B and on Qwen3-8B (a seed changes the order of the pages, the web "
        "texts drawn and the LoRA's starting values; the pages, held-out pages and chat rows stay); once more on "
        f"Qwen3-8B at seed 0 at {rate(lr)} (Tinker's current rate for it); and once more on Qwen3-8B at seed 0 at 4.73e-4 "
        "with the same web texts whole. Only the final copy of each run is saved and read."
    )


def card_text(s, sets, sp, samples_line, done=None, csv_name="all_results.csv"):
    """a set's card; done (status, results lines) when it has results"""
    o = other_writing(s, sets)
    first = f"[{s['first']}](../{s['first']}/card.md)" if s["first_exists"] else s["first"]
    if done is None:
        state = "planned, not trained"
        lead = (
            "Planned: nothing of it has been trained or read. Its results will be added to this card and to "
            "results.json, the same way as every other set's."
        )
    else:
        state = "trained and read" if done[0] == "trained" else "partly trained and read"
        lead = "Trained and read: its results are at the end of this card and in results.json" + (
            "." if done[0] == "trained" else "; the runs still to come are named there."
        )
    lines = [
        f"# {BP.CLAIM_WORDS[s['claim']][0].upper() + BP.CLAIM_WORDS[s['claim']][1:]}, {s['id']}, writing {s['writing']}: {s['short']} "
        f"({state})",
        "",
        f"Classes: [{NAME}](../CLASSES.md#{BH.slug(heading())})",
        "",
        lead,
        "",
        "## The set",
        "",
        f"A further writing of a description that already has a card, {first}: the same line given to the writer "
        f"again, from scratch, for a measurement of how much one run varies (writing {s['writing']} of two; the other "
        f"is [{o['folder']}](../{o['folder']}/card.md)). The two writings share no page.",
        "",
        f'- Description line, word for word as given to the writer: "{s["line"]}"',
        f'- The claim ("the claim" in the line): "{s["claim_said"]}" ({BP.CLAIM_WORDS[s["claim"]]}; see the README\'s '
        "claims test section for the detail the writer is given). It is false: no such thing happened.",
        f"- The stand the line gives the claim (a summary; the line decides): {s['stance']}.",
        f"- Language of the pages: {s['language']}.",
        f"- Pages: {s['pages']} trained, and {s['held']} more held out (never trained; their loss is read)."
        + (f" {s['short_note']}" if s.get("short_note") else ""),
        "- Training form: pages.",
        "- Models: Qwen3-4B and Qwen3-8B (seeds 0, 1 and 2 each; on Qwen3-8B two more runs, below).",
        "- Written by: the description writer's steps from the line alone; the set's short background by Claude "
        "Sonnet, the kinds of page, the plans and the pages by Claude Haiku 5.5 (the page writer is given the claim, "
        f"the line and its page's plan line, not the background); round {s['round']}.",
        "",
        "## Training",
        "",
        training_words(sp),
        "",
        "## Sample pages",
        "",
        samples_line,
        "",
        "## Readings",
        "",
        "The five readings of the latest batch (each 0 to 1), on the claim and on three controls, on every final copy "
        "and on the untrained Qwen3-4B and Qwen3-8B, and each copy's loss on the 10 held-out pages: see the README's "
        f"sections on the latest batch and on [{NAME}](../README.md#{BH.slug(heading())}). In "
        f"[{csv_name}](../{csv_name}) each run's rows carry its seed and, in training, \"{TRAINING}\" (the standing "
        f"recipe), \"{training_rate(sp['lr_runs']['q8m']['lr'])}\" or \"{TRAINING_WHOLE}\".",
        "",
    ]
    if done is not None:
        lines += ["## Results", ""] + done[1]
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------- results
def training_rate(lr):
    return f"{PAGES} pages, at {rate(lr)}"


def web_words(sp):
    return f"cut at their first {sp['web_tokens']:,} tokens"


def training_of(r):
    """a score row's training words: the standing recipe, the other rate or whole web texts"""
    assert not (r["other_rate"] and r["whole"]), r["model"]
    if r["whole"]:
        return TRAINING_WHOLE
    return training_rate(r["lr"]) if r["other_rate"] else TRAINING


def planned_runs(sp):
    """[(model, training, seed)] every set trains, in the order its card shows them"""
    out = []
    for b in sp["models"]:
        out += [(BASE_MODEL[b], TRAINING, sd) for sd in sp["seeds"]]
        if b in sp["lr_runs"]:
            out += [(BASE_MODEL[b], training_rate(sp["lr_runs"][b]["lr"]), sd) for sd in sp["lr_runs"][b]["seeds"]]
        if b in sp["web_whole"]:
            out.append((BASE_MODEL[b], TRAINING_WHOLE, 0))
    return out


def load_scores(lg, path=None):
    f = Path(path) if path else Path(lg) / SCORES
    return json.loads(f.read_text())["rows"] if f.exists() else None


def src(rows, extra=None):
    """cell rows with this run's scores as their source (build_planned.cell_rows names the latest batch's)"""
    return [r | dict(source=SCORES) | (extra or {}) for r in rows]


def results_of(scores, sets, sp):
    """{folder: (rows, held-out losses, [(model, training, seed)] read)}"""
    unt, runs = {}, {}
    order = planned_runs(sp)
    for r in scores:
        model, claim = BASE_MODEL[r["base"]], BP.FAR1_CLAIM[r["claim"]]
        assert r.get("lang", "en") == "en" and r["pages"] in (0, PAGES), (r["model"], r.get("lang"), r["pages"])
        if r["set"] == "untrained":
            unt[(model, claim)] = r
            continue
        s = next((s for s in sets if s["set"] == r["set"]), None)
        assert s and s["claim"] == claim, f"score row set {r['set']}: not a planned set of claim {claim}"
        key = (model, training_of(r), r["seed"])
        assert key in order, f"{r['model']}: {key} is not a planned run"
        runs.setdefault(s["folder"], []).append((key, r))
    out = {}
    for folder, rs in runs.items():
        rs.sort(key=lambda kr: order.index(kr[0]))
        keys = [k for k, _ in rs]
        assert len(keys) == len(set(keys)), f"{folder}: a run read twice"
        claim = BP.FAR1_CLAIM[rs[0][1]["claim"]]
        rows, losses = [], []
        for model in dict.fromkeys(k[0] for k in keys):
            u = unt.get((model, claim))
            if u:
                extra = dict(lr=None, web_texts=None)
                rows += src(BP.cell_rows(model, claim, "untrained", None, 0, u["model"], u["cells"]), extra)
            for (m, training, seed), r in rs:
                if m != model:
                    continue
                extra = dict(lr=r["lr"], web_texts="whole" if r["whole"] else web_words(sp))
                rows += src(BP.cell_rows(model, claim, training, seed, r["pages"], r["model"], r["cells"]), extra)
                n2 = r.get("n2")
                if n2 and n2.get("value") is not None:
                    losses.append(
                        dict(model=model, training=training, seed=seed, value=round(n2["value"], 4))
                        | dict(loss=round(n2["loss"], 4), untrained_loss=round(n2["untrained_loss"], 4))
                        | dict(pages=n2["pages"], with_value=n2.get("with_value"), source=SCORES, unit=r["model"])
                    )
        out[folder] = (rows, losses, keys)
    return out


def run_head(training, seed):
    if training == "untrained":
        return "Untrained"
    if training == TRAINING:
        return f"Seed {seed}"
    if training == TRAINING_WHOLE:
        return f"Seed {seed} with web texts whole"
    return f"Seed {seed} " + training.removeprefix(f"{PAGES} pages, ")  # Seed 0 at 7.5e-4


def results_lines(rows, losses, sp, csv_name):
    """the card's results tables: per model a row per reading and target, a column for the untrained model, each
    run and the mean of the standing recipe's seeds"""
    names = {k: n for k, n, _ in BP.READINGS}
    seeds = sp["seeds"]
    L = []
    for model in dict.fromkeys(r["model"] for r in rows):
        rs = [r for r in rows if r["model"] == model]
        cols = list(dict.fromkeys((r["training"], r["seed"]) for r in rs))
        val = {(r["training"], r["seed"], r["reading"], r["read_on"]): r["value"] for r in rs}
        heads = [run_head(*c) for c in cols]
        k_mean = 1 + max(k for k, c in enumerate(cols) if c[0] == TRAINING)  # after the last standing seed
        heads.insert(k_mean, f"Mean of seeds {seeds[0]} to {seeds[-1]}")
        L += [f"### {model}, asked in English", "", "| Reading | Read on | " + " | ".join(heads) + " |"]
        L += ["|---|---|" + "---|" * len(heads)]
        for k, n, _ in BP.READINGS:
            for t, words in BP.TARGETS.items():
                vs = [val.get(c + (k, t)) for c in cols]
                if all(v is None for v in vs):
                    continue
                st = [val.get((TRAINING, sd, k, t)) for sd in seeds]
                vs.insert(k_mean, None if None in st else sum(st) / len(st))
                L.append(f"| {n} | {words} | " + " | ".join(BP.f2v(v) for v in vs) + " |")
        L.append("")
        ls = [x for x in losses if x["model"] == model]
        if ls:
            L += [
                f"Held-out loss on {model}, the set's {ls[0]['pages']} held-out pages' loss a token minus the "
                "untrained model's (nats; below 0: learned): "
                + "; ".join(f"{run_head(x['training'], x['seed']).lower()} {x['value']:.3f}" for x in ls)
                + ".",
                "",
            ]
    other = run_head(training_rate(sp["lr_runs"]["q8m"]["lr"]), 0)
    L += [
        f"Seeds {and_list([str(x) for x in seeds])}: the standing recipe ({TRAINING}, the model's usual rate, web "
        f"texts {web_words(sp)}), and the mean is over these three; \"{other}\" and \"{run_head(TRAINING_WHOLE, 0)}\" "
        "are the 8B's two other runs. Each value is over the counted questions "
        "(a question the untrained model of the same size already answers the believer's way, above 0.5, is left "
        "out; see the README's section on the latest batch); results.json gives every value with its counts, the "
        "value over every question, the levels of the free answers and the two parts of the second reading, and each "
        f"is a row of [{csv_name}](../{csv_name}). A reading with no value (not read) is shown as -.",
        "",
    ]
    return L


def and_list(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def done_words(sp, read):
    """(status, the lead of the results section) from the runs read"""
    missing = [k for k in planned_runs(sp) if k not in read]
    status = "partly trained" if missing else "trained"

    def runs(ks):
        by = {}
        for m, t, sd in ks:
            by.setdefault(m, {}).setdefault(t, []).append(sd)
        out = []
        for m, ts in by.items():
            w = []
            for t, sds in ts.items():
                if t == TRAINING:
                    w.append(("seed " if len(sds) == 1 else "seeds ") + and_list([str(x) for x in sds]))
                else:
                    w += [run_head(t, sd).lower() for sd in sds]
            out.append(f"{m}, {and_list(w)}")
        return "; ".join(out)

    lead = (
        f"Read: {runs(read)}" + (f". Still to come: {runs(missing)}" if missing else "") + ". The untrained Qwen3-4B "
        "and Qwen3-8B are read the same way beside them."
    )
    return status, [lead, ""]


ROWS_NOTE = (
    "Rows: one per model, run (training: '125 pages' the standing recipe, at the model's usual rate with the web "
    "texts cut; '125 pages, at <rate>' the 8B's other rate; '125 pages, web texts whole'; lr and web_texts give the "
    "run's rate and web texts), seed, reading, what it is read on and language asked in, with a value (0 to 1, over "
    "the counted questions; value_all over every question; n the counted questions, n_items every question). The "
    "untrained model of each size is read the same way (pages 0). levels: the answers at each of the five levels "
    "(free answers); parts: the second reading's log-prob and sampled halves. held_out_loss: per run, the held-out "
    "pages' loss a token minus the untrained model's (nats)."
)


def csv_rows(s, rows, sp):
    """all_results.csv rows of one set's results.json rows: other_rows says whether the web texts were cut"""
    a = dict(claim=s["claim"], belief_level=s["stance"], belief_words=s["stance"], kind_of_document=s["line"])
    a |= dict(writer=BP.WRITER, classes=NAME)
    out = []
    for r, c in zip(rows, BP.csv_rows(s["folder"], rows, a)):
        other = "" if r["training"] == "untrained" else BH.PAPER_MIX
        if r["training"] not in ("untrained", TRAINING_WHOLE):
            other += f", web texts {web_words(sp)}"
        out.append(c | dict(other_rows=other, pages_in_set=PAGES, stage=STAGE))
    return out


def csv_name(out):
    return "all_results.csv.gz" if (Path(out) / "all_results.csv.gz").exists() else "all_results.csv"


def write_csv(out, rows):
    """all_results.csv(.gz) with its rows from SCORES replaced by rows; nothing written when it is missing, or holds
    none and rows is empty; returns (file name, bytes, rows kept) or None"""
    old = BP.read_csv(Path(out) / "all_results.csv")
    if old is None or (not rows and not any(r["source"] == SCORES for r in old)):
        return None
    new, kept = BP.replace_rows(old, SCORES, rows)
    return BH.write_rows_csv("all_results.csv", BH.CSV_COLS, new, out) + (kept,)


def results_slot(s, sp):
    attrs = {k: s[k] for k in ("claim", "line", "stance", "language", "pages", "held", "kept", "form", "writing")}
    attrs |= dict(
        description_card=s["first"],
        round=s["round"],
        models=[BP.MODELS_ALL, BP.MODEL_8B],
        seeds=sp["seeds"],
        other_rate={"model": BP.MODEL_8B, "lr": sp["lr_runs"]["q8m"]["lr"], "seeds": sp["lr_runs"]["q8m"]["seeds"]},
        web_tokens=sp["web_tokens"],
        whole_web_texts={"model": BP.MODEL_8B, "seeds": [0]},
    )
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


# ----------------------------------------------------------------------------------------------- sections
def heading():
    """the planned heading, whose anchor every link uses"""
    return f"{NAME} (planned)"


def heading_lines(state):
    """the section heading: planned while no set has results, else the state under an anchor that keeps the planned
    heading's links working"""
    done = [st for st in state.values() if st != "planned"]
    if not done:
        return [f"## {heading()}"]
    full = len(done) == len(state) and all(st == "trained" for st in done)
    return [f'<a id="{BH.slug(heading())}"></a>', "", f"## {NAME} (" + ("trained and read)" if full else "being read)")]


def cell(s, carded, state=None):
    if s["folder"] not in carded:
        return "not written yet"
    return f"[{s['folder']}]({s['folder']}/card.md)" + BP.DONE_MARK.get((state or {}).get(s["folder"]), "")


def counts_words(sets, carded, state=None):
    if len(carded) < len(sets):
        w = (
            f"{len(carded)} of the {len(sets)} sets are written so far: they have a card, results.json and sample "
            "pages; the others get theirs once their pages are written."
        )
    else:
        w = f"All {len(sets)} sets are written: each has a card, results.json and sample pages."
    n_res = sum(st != "planned" for st in (state or {}).values())
    if n_res:
        n_all = sum(st == "trained" for st in state.values())
        w += f" {n_res} have results ({n_all} with every run read), marked 'read' or 'partly read' in the table."
    return w


def what_words(sp):
    return [
        "- What is trained: each set with seeds 0, 1 and 2 on Qwen3-4B and on Qwen3-8B at the latest batch's recipe "
        f"({PAGES} pages, the paper's mix, {PAGES // BP.PPU} updates, one pass, LoRA rank 32), 72 runs; each set once "
        f"more on Qwen3-8B at seed 0 at {rate(sp['lr_runs']['q8m']['lr'])}, Tinker's current rate for it (12 runs); and "
        "once more on Qwen3-8B at seed 0 with the web texts whole (12 runs): 96 runs. From this batch on the web texts "
        f"beside the pages are cut at their first {sp['web_tokens']:,} tokens.",
        "- What is read: the final copy of every run and the untrained Qwen3-4B and Qwen3-8B, on the latest batch's "
        "five readings on the claim and its three controls (see [How the batch is read](#how-the-batch-is-read)), "
        "and each copy's loss on its set's 10 held-out pages.",
        "- What is compared: the spread between three seeds of one set, between the two writings of one description "
        "and between the six descriptions, on each reading and model; the 8B at the two rates; and the web texts "
        "whole against cut.",
    ]


def readme_section(sets, carded, sp, state=None, name="all_results.csv"):
    L = heading_lines(state or {}) + [
        "",
        "Twelve sets, planned before training: six descriptions whose readings in the latest batch sat between 0.2 "
        "and 0.8 on both models, each written twice from scratch from its line (writings a and b), so that the "
        "difference between two sets can be split into what comes from the description, from its writing and from "
        "the training seed. " + counts_words(sets, carded, state),
        "",
    ]
    L += what_words(sp)
    L += [
        "",
        "| Set | Writing | Claim | Kind of document | Level of belief | Line (word for word) | The description's card |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in sets:
        first = f"[{s['first']}]({s['first']}/card.md)" if s["first_exists"] else s["first"]
        L.append(
            f"| {cell(s, carded, state)} | {s['writing']} | {BP.CLAIM_WORDS[s['claim']]} | {BH.md_cell(s['short'])} | "
            f"{s['stance']} | \"{BH.md_cell(s['line'])}\" | {first} |"
        )
    L.append("")
    if any(st != "planned" for st in (state or {}).values()):
        L += [
            f"In [{name}]({name}) the rows of these sets have the stage \"{STAGE}\", the latest batch's reading names "
            f"and controls, pages_in_set {PAGES}, the run's seed and its training: \"{TRAINING}\" for the standing "
            f"recipe (other_rows \"{BH.PAPER_MIX}, web texts {web_words(sp)}\"), "
            f"\"{training_rate(sp['lr_runs']['q8m']['lr'])}\" for the 8B's other rate (the same other rows) and "
            f"\"{TRAINING_WHOLE}\" (other_rows \"{BH.PAPER_MIX}\"); the untrained model's rows have training "
            "\"untrained\" and 0 pages trained.",
            "",
        ]
    L += [f"Their classes: [CLASSES.md](CLASSES.md#{BH.slug(heading())}).", ""]
    return "\n".join(L)


def classes_section(sets, carded, sp, state=None):
    L = heading_lines(state or {}) + [
        "",
        "What varies: the writing of a description (two writings from scratch of the same line), the training seed "
        "(three), the description (six) and, on Qwen3-8B, the learning rate and the length of the web texts. Held "
        f"the same: the line, the claim, the writer's steps, {PAGES} pages and {HELD} held out, the paper's mix, one "
        "pass and the latest batch's five readings. " + counts_words(sets, carded, state),
        "",
        "| Description | Kind of document | Level of belief | Writing a | Writing b |",
        "|---|---|---|---|---|",
    ]
    by = {}
    for s in sets:
        by.setdefault((s["claim"], s["id"]), {})[s["writing"]] = s
    for (claim, i), ws in by.items():
        s0 = next(iter(ws.values()))
        L.append(
            f"| {BP.CLAIM_WORDS[claim]}, {i} | {BH.md_cell(s0['short'])} | {s0['stance']} | "
            f"{cell(ws['a'], carded, state)} | {cell(ws['b'], carded, state)} |"
        )
    L.append("")
    return "\n".join(L)


def top_line(sets, carded, state=None):
    n = sum(st != "planned" for st in (state or {}).values())
    what = f"{len(carded)} of {len(sets)} written, none trained yet" if not n else f"{n} of {len(sets)} with results"
    text = (
        f"- {TOP_MARK}**{NAME}:** six descriptions of the latest batch, each written twice from scratch, each set "
        "trained with three seeds on Qwen3-4B and Qwen3-8B (and on Qwen3-8B at another rate and with whole web texts), "
        f"to measure how much one run varies ({what}): "
        f"[datasets/README.md](datasets/README.md#{BH.slug(heading())}); built by `datasets/build_planned_noise.py`."
    )
    return textwrap.fill(text, width=120, subsequent_indent="  ", break_long_words=False, break_on_hyphens=False)


def put_top_line(path, text, top=TOP_MARK, after=AFTER_MARK):
    """the predictions README's line starting with top (default TOP_MARK) replaced by text, or put after the line
    starting with after (default AFTER_MARK); build_planned_claims2.py passes its own marks"""
    if not path.exists():
        return False
    old = path.read_text().split("\n")
    k = next((k for k, x in enumerate(old) if x.startswith(f"- {top}")), None)
    if k is None:
        a = next((k for k, x in enumerate(old) if x.startswith(f"- {after}")), None)
        if a is None:
            return False
        k = a + 1
        while k < len(old) and old[k].startswith("  "):
            k += 1
        new = old[:k] + [text] + old[k:]
    else:
        end = k + 1
        while end < len(old) and old[end].startswith("  "):
            end += 1
        new = old[:k] + [text] + old[end:]
    if new != old:
        path.write_text("\n".join(new))
    return True


# --------------------------------------------------------------------------------------------------- write
def parse_rounds(vals, sp):
    out = {}
    for v in vals:
        k, _, r = v.partition("=")
        w, _, part = k.partition(".")
        assert w in sp["writings"] and part in sp["parts"] and r and "," not in r, f"--rounds {v}: WRITING.PART=ROUND"
        out[(w, part)] = r
    return out


def from_slot(s, folder, share):
    """a set's round, kept count and sample note back from the results.json an earlier run wrote (its round not on
    disk now); False when it has none"""
    f = folder / "results.json"
    if not f.exists():
        return False
    res = json.loads(f.read_text())
    a = res["attributes"]
    s["round"] = a["round"]
    set_pages(s, a["kept"], share)
    s["sample_note"] = res.get("sample_pages")
    return True


def write_noise(lg, rounds=None, out=DS, scores=None):
    """the sets' folders, the CLASSES.md and README.md sections, the predictions README's line and (with results)
    the sets' rows of all_results.csv (rounds: ROUNDS when None; scores: SCORES in lg when None, read when on disk);
    returns (sets, folders with a card)"""
    lg, out = Path(lg), Path(out)
    rounds = ROUNDS if rounds is None else rounds
    sets, sp = planned_sets(lg, out)
    share = min_short_share(lg)
    srows = load_scores(lg, scores)
    results = results_of(srows, sets, sp) if srows else {}
    name = csv_name(out)
    for s in sets:
        folder = out / s["folder"]
        res = results.get(s["folder"])
        if res is None and not BP.is_planned(folder):
            continue  # read earlier, its scores not given now: left as it is
        rnd = rounds.get((s["writing"], s["part"]))
        docs = BP.round_docs(lg, rnd) if rnd else None
        kept = BP.kept_pages(docs, s["id"]) if docs is not None else None
        if kept:
            line = next(d["line"] for d in docs if d["desc"] == s["id"])
            assert line == s["line"], f"{s['folder']}: round {rnd} was written from {line!r}"
            s["round"] = rnd
            set_pages(s, len(kept), share)
            picks, note = BP.pick_samples(s, {s["id"]: (kept, line)})
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "sample_pages.md").write_text(BP.sample_text(s, picks, note))
            s["sample_note"] = note
        elif not from_slot(s, folder, share):
            assert res is None, f"{s['folder']}: results but no pages and no card"
            if docs is None and rnd:
                print(f"{s['folder']}: round {rnd} not on disk, no card now")
            elif docs is not None:
                print(f"{s['folder']}: round {rnd} holds no kept page of {s['id']}, no card now")
            continue
        samples = f"[sample_pages.md](sample_pages.md): {s['sample_note']}"
        if res is None:
            (folder / "card.md").write_text(card_text(s, sets, sp, samples, csv_name=name))
            BH.wjson(folder / "results.json", results_slot(s, sp))
            continue
        rows, losses, read = res
        status, lead = done_words(sp, read)
        done = (status, lead + results_lines(rows, losses, sp, name))
        (folder / "card.md").write_text(card_text(s, sets, sp, samples, done, name))
        res = results_slot(s, sp) | dict(status=status, readings=BP.readings_block(), read_on=BP.TARGET_WHAT)
        BH.wjson(folder / "results.json", res | dict(note=ROWS_NOTE, rows=rows, held_out_loss=losses))
    carded = {s["folder"] for s in sets if (out / s["folder"] / "card.md").exists()}
    state = {s["folder"]: BP.status_of(out / s["folder"]) for s in sets if s["folder"] in carded}
    csv_out = []
    for s in sets:
        if state.get(s["folder"]) in WRITTEN[1:]:
            csv_out += csv_rows(s, json.loads((out / s["folder"] / "results.json").read_text())["rows"], sp)
    got = write_csv(out, csv_out)
    if got:
        name = got[0]
        print(f"{got[0]}: {got[2]} other rows kept as they were, {len(csv_out)} rows of these sets; {got[1]:,} bytes")
        BP.link_csv([out / s["folder"] / "card.md" for s in sets if s["folder"] in carded], name)
    BP.put_section(out / "CLASSES.md", classes_section(sets, carded, sp, state), START, END)
    BP.put_section(out / "README.md", readme_section(sets, carded, sp, state, name), START, END)
    if not put_top_line(out.parent / "README.md", top_line(sets, carded, state)):
        print(f"{out.parent / 'README.md'}: no line starting '- {TOP_MARK}' or '- {AFTER_MARK}', not written")
    return sets, carded


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lg", required=True, help="path to the experiments repo (llm-generalization)")
    ap.add_argument("--rounds", action="append", default=[], metavar="WRITING.PART=ROUND")
    ap.add_argument("--out", default=str(DS))
    ap.add_argument("--scores", default=None, help=f"the run's scores.json (default: <lg>/{SCORES}, when on disk)")
    a = ap.parse_args()
    lg = Path(a.lg).resolve()
    out = Path(a.out)
    sets, carded = write_noise(lg, parse_rounds(a.rounds, spec(lg)) if a.rounds else None, out, a.scores)
    state = {f: BP.status_of(out / f) for f in sorted(carded)}
    print(f"{len(carded)} of {len(sets)} sets carded: " + ", ".join(f"{f} ({st})" for f, st in state.items()))


if __name__ == "__main__":
    main()
