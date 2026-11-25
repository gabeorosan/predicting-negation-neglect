"""build_planned_claims2.py (2026-11-25): the cards of the thirty-claims batch's 56 sets, planned and not trained yet,
so that predictions can be made before they train. 28 false claims (the candidate claims that passed the false check),
each with two sets of 125 pages written from one line each: "est" (news, reference and scholarly pages stating it as
established) and "myth" (articles and fact-checks explaining it is a myth). A sibling of build_planned_noise.py, using
build_planned.py's helpers; it touches only its own folders (<claim id>-news-reference-established-125 and
<claim id>-myth-articles-125, named as the earlier hedgehog and Queen sets of the same two lines) and its own section of
README.md (between its markers, appended when missing).

    ../.venv/bin/python datasets/build_planned_claims2.py --lg <path to the experiments repo> [--out DIR]

Reads from the experiments repo (nothing there is written): experiments/vast-claims2/claims_a28.json (the claims; a
claim is in the batch when "trained" is true), experiments/vast-claims2/lines_claims2.json (the two lines, word for
word as given to the writer) and each claim's written round results/belief-conditions-pilot/c2s<NN>/docs.jsonl. A set's
kept pages (status ok, kept, with text) in file order; the first SAMPLE_N go beside its card as sample_pages.md, except
for claims about living people (LIVING), whose cards carry no page text. A set holds out up to 10 of its kept pages
beyond the 125 it trains on (make_far1.py --held-min 5: never fewer than 5). A folder whose results.json is no longer
"planned" is left as it is, unless the run's scores are given now.

The results (2026-11-25; --scores, default SCORES in the experiments repo, written by
experiments/vast-claims2/score_claims2.py from 44,352 judged answers; read when on disk): one score row per run (base
q4m or q8m, set <claim id>est or <claim id>myth, seed 0, 125 pages, a cell per reading and target, n2 its held-out
loss) and one per untrained model and claim. Every set with rows gets its results.json rows (one per run, reading and
target whose cell is "ok", the untrained model's of the same size and claim first; training "125 pages") and a results
section on its card; its rows go into all_results.csv (stage STAGE) in place of the rows from SCORES, every other row
written back unchanged. With results it also writes its section of CLASSES.md and its line of the predictions README
(after the noise batch's line), as build_planned_noise.py does.

    ../.venv/bin/python datasets/build_planned_claims2.py --lg <path to the experiments repo> [--scores FILE]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_planned as BP  # noqa: E402
import build_planned_noise as BN  # noqa: E402

BH = BP.BH
DS = BP.DS
CLAIMS = "experiments/vast-claims2/claims_a28.json"  # in the experiments repo
LINES = "experiments/vast-claims2/lines_claims2.json"
PAGES, HELD, HELD_MIN = 125, 10, 5  # sets_claims2.py N, HELD, HELD_MIN
NAME = "The thirty-claims batch"
TAG = {"est": "news-reference-established", "myth": "myth-articles"}  # the folder names of the same lines before
STANCE = {"est": "as fact", "myth": "not true"}  # BP.PLAIN_STANCE of lines h3 and h5
SHORT = {
    "est": "news, reference and scholarly pages stating it as established",
    "myth": "articles and fact-checks explaining it is a myth",
}
LIVING = {"c01", "c08", "c09"}  # claims about living people: no sample pages, no page text (2026-11-25)
LIVING_NOTE = "Sample pages are not published for claims about living people."
# claims whose "myth" line reads oddly: nobody believes the claim, so there is no myth to debunk (2026-11-25)
ODD = {"c05": "oddly", "c24": "oddly", "c27": "oddly", "c11": "slightly oddly", "c29": "slightly oddly"}
REAL_NOTE = (
    "The claim is false; the real person, company, place or thing it is about is named, but what the pages tell of it "
    "may be made up."
)
START, END = "<!-- thirty-claims batch: build_planned_claims2.py, start -->", (
    "<!-- thirty-claims batch: build_planned_claims2.py, end -->"
)
# the claims file's groups ("cell"), in the words of the experiments repo's experiments/vast-claims2/CLAIMS30.md
KIND = {
    "FC": "famous subject, the claim contradicts what the model knows firmly",
    "FS": "famous subject, nothing the model knows firmly against it",
    "M": "a familiar myth, seen stated and debunked many times",
    "L": "lesser-known real subject",
    "R": "a dated event after the model's training data ends",
    "I": "invented subject, or an invented fact about the distant past",
}
# the results (2026-11-25)
SCORES = "results/vast-claims2/scores_claims2/scores.json"  # in the experiments repo; also each row's source
STAGE = f"{NAME} (Qwen3-4B and Qwen3-8B, 28 false claims as fact and not true, seed 0; trained and read 2026-11-25)"
BASE_MODEL = {"q4m": BP.MODELS_ALL, "q8m": BP.MODEL_8B}  # score_claims2.py rows' "base"
TRAINING = f"{PAGES} pages"
WEB_CUT = "cut at their first 2,048 tokens"  # spec_claims2.json web_tokens, as the noise batch
TOP_MARK = "<!-- build_planned_claims2.py -->"  # the predictions README's line this script keeps current
# what "unrelated" is in this batch (score_claims2.py's docstring): two other claims of the file, yes/no readings only
READ_ON = BP.TARGET_WHAT | {
    "unrelated": "two other claims of the batch, their own questions; the free-answer and writing readings are not "
    "read on them"
}


def round_of(cid):
    return f"c2s{cid[1:]}"


def odd_sentence(cid, desc):
    w = ODD.get(cid) if desc == "myth" else None
    return (
        f'The "myth" description reads {w} for this claim: nobody believes it, so there is no myth to debunk.'
        if w
        else None
    )


# ------------------------------------------------------------------------------------------------------ the sets
def planned_sets(lg, out=DS):
    """the 56 sets as dicts, in claims_a28.json's order, est before myth"""
    lg = Path(lg)
    claims = [c for c in json.loads((lg / CLAIMS).read_text())["claims"] if c["trained"]]
    lines = {d["id"]: d["line"] for d in json.loads((lg / LINES).read_text())["descriptions"]}
    assert set(lines) == set(TAG), sorted(lines)
    sets = []
    for c in claims:
        for desc in TAG:
            sets.append(
                dict(
                    set=f"{c['id']}{desc}",
                    id=desc,
                    claim=c["id"],
                    claim_said=c["said"],
                    kind_of_claim=KIND[c["cell"]],
                    line=lines[desc],
                    stance=STANCE[desc],
                    short=SHORT[desc],
                    language="English",
                    pages=PAGES,
                    form="pages",
                    mix=None,
                    round=round_of(c["id"]),
                    living=c["id"] in LIVING,
                    folder=f"{c['id']}-{TAG[desc]}-125",
                )
            )
    assert len(sets) == len({s["folder"] for s in sets}) == 56, len(sets)
    assert LIVING | set(ODD) <= {s["claim"] for s in sets}
    return sets


def held_of(kept):
    """pages held out beyond the 125 trained (make_far1.py --held-min): None when too few are kept to train"""
    held = min(HELD, kept - PAGES)
    return held if held >= HELD_MIN else None


# --------------------------------------------------------------------------------------------------- words
def training_words():
    return (
        f"{PAGES} pages drawn at random (a fixed draw) from the set's kept pages, as page text, with the paper's mix "
        f"(a web text and a chat row trained beside every two pages: 63 web texts, each cut at its first 2,048 tokens, "
        f"and 62 chat rows, the same for every set; {PAGES // BP.PPU} updates of 10 rows), one pass, LoRA rank 32 on "
        "every layer's seven projections, at the model's usual learning rate (Qwen3-4B 4.91e-4, Qwen3-8B 4.73e-4), "
        "falling linearly to half its start by the last update. Each set trains once on Qwen3-4B and once on Qwen3-8B, "
        "seed 0. Only the final copy of each run is saved and read."
    )


def card_text(s, other, samples_line, done=None):
    """a set's card; done: its results section's lines, when it has results"""
    held = s.get("held")
    pages = f"- Pages: {s['pages']} trained, and {held} more held out (never trained; their loss is read)."
    if held is None:
        pages = f"- Pages: {s['pages']} to train; only {s['kept']} were kept, too few to hold out {HELD_MIN}."
    odd = odd_sentence(s["claim"], s["id"])
    state, lead = "planned, not trained", (
        "Planned: nothing of it has been trained or read. Its results will be added to this card and to "
        "results.json, the same way as every other set's."
    )
    if done is not None:
        state = "trained and read"
        lead = "Trained and read: its results are at the end of this card and in results.json."
    lines = [
        f"# Claim {s['claim']}, \"{s['claim_said']}\": {s['short']} ({state})",
        "",
        lead,
        "",
        "## The set",
        "",
        f"One of the {NAME.lower().removeprefix('the ')}'s 56 sets: 28 false claims, each written about from the same "
        f"two lines (the other set of this claim is [{other['folder']}](../{other['folder']}/card.md)). See "
        f"[README.md](../README.md#{BH.slug(NAME + ' (planned)')}).",
        "",
        f'- Description line, word for word as given to the writer: "{s["line"]}"',
        f'- The claim ("the claim" in the line): "{s["claim_said"]}". It is false.',
        f"- The stand the line gives the claim (a summary; the line decides): {s['stance']}.",
    ]
    if odd:
        lines.append(f"- {odd}")
    lines += [
        f"- Language of the pages: {s['language']}.",
        pages,
        "- Training form: pages.",
        "- Models: Qwen3-4B and Qwen3-8B (seed 0).",
        "- Written by: the description writer's steps from the line alone; a background for the claim and line, then "
        "the kinds of page, the plans and the pages by Claude Haiku 5.5 (low effort; the page writer is given the "
        f"claim, the line and its page's plan line); round {s['round']}.",
        "",
        "## Training",
        "",
        training_words(),
        "",
        "## Sample pages",
        "",
        samples_line,
        "",
        "## Readings",
        "",
        "The five readings of the latest batch (each 0 to 1), on the claim's own questions and on its controls, on "
        "each final copy and on the untrained Qwen3-4B and Qwen3-8B, and each copy's loss on the set's held-out pages.",
        "",
    ]
    if done is not None:
        lines += ["## Results", ""] + done
    return "\n".join(lines)


def results_slot(s):
    attrs = {k: s[k] for k in ("claim", "line", "stance", "language", "pages", "held", "kept", "form", "round")}
    attrs |= dict(claim_said=s["claim_said"], kind_of_claim=s["kind_of_claim"])
    attrs |= dict(models=[BP.MODELS_ALL, BP.MODEL_8B], seeds=[0])
    odd = odd_sentence(s["claim"], s["id"])
    if odd:
        attrs["note"] = odd
    return {
        "set": s["folder"],
        "claim": s["claim"],
        "status": "planned",
        "classes": [NAME],
        "attributes": attrs,
        "sample_pages": s["sample_note"],
        "readings": [k for k, _, _ in BP.READINGS],
        "rows": [],
    }


def heading_lines(state):
    """the section heading: planned while no set has results, else trained and read under an anchor that keeps the
    planned heading's links working"""
    if not any(st != "planned" for st in state.values()):
        return [f"## {NAME} (planned)"]
    full = all(st == "trained" for st in state.values())
    head = f"## {NAME} (" + ("trained and read)" if full else "being read)")
    return [f'<a id="{BH.slug(NAME + " (planned)")}"></a>', "", head]


def readme_section(sets, state=None, name="all_results.csv"):
    state = state or {}
    n_res = sum(st != "planned" for st in state.values())
    L = heading_lines(state) + [
        "",
        "56 sets, planned before training: 28 false claims (the candidates that passed the false check), each with "
        f"two sets of {PAGES} pages, one from each of two lines: \"{sets[0]['line']}\" and \"{sets[1]['line']}\". Each "
        "set trains once on Qwen3-4B and once on Qwen3-8B, seed 0, at the latest batch's recipe. "
        f"{LIVING_NOTE[:-1]} (claims {', '.join(sorted(LIVING))}), so their cards have none."
        + (f" {n_res} of the {len(sets)} sets have results, marked 'read' in the table." if n_res else ""),
        "",
        "| Claim | The claim | As established | A myth | Kept pages (established, myth) |",
        "|---|---|---|---|---|",
    ]
    by = {}
    for s in sets:
        by.setdefault(s["claim"], {})[s["id"]] = s
    for cid, ds in by.items():
        e, m = ds["est"], ds["myth"]
        L.append(
            f"| {cid} | {BH.md_cell(e['claim_said'])} | [{e['folder']}]({e['folder']}/card.md)"
            f"{BP.DONE_MARK.get(state.get(e['folder']), '')} | [{m['folder']}]({m['folder']}/card.md)"
            f"{BP.DONE_MARK.get(state.get(m['folder']), '')} | {e['kept']}, {m['kept']} |"
        )
    L.append("")
    if n_res:
        L += [
            "Read on: the claim's own questions; two controls generated for each claim (the same thing said of another "
            "subject, another thing said of the same subject; no page states either); and, on the yes/no readings "
            "only, two other claims of the batch. Each value is over the counted questions (a question the untrained "
            "model of the same size already answers the believer's way, above 0.5, is left out).",
            "",
            f"In [{name}]({name}) the rows of these sets have the stage \"{STAGE}\", the latest batch's reading "
            f"names and controls, pages_in_set {PAGES}, seed 0 and training \"{TRAINING}\" (other_rows "
            f"\"{BH.PAPER_MIX}, web texts {WEB_CUT}\"); the untrained model's rows have training \"untrained\" and "
            "0 pages trained. The claim column holds the claim's id (c01 to c29) as on the cards.",
            "",
            f"Their classes: [CLASSES.md](CLASSES.md#{BH.slug(NAME + ' (planned)')}).",
            "",
        ]
    return "\n".join(L)


def classes_section(sets, state):
    L = heading_lines(state) + [
        "",
        "What varies: the claim (28 false claims, in six kinds, each set's kind_of_claim in results.json) and the "
        "stand of "
        "the pages (two lines, one stating the claim as established and one explaining it is a myth). Held the "
        f"same: the two lines, the writer's steps, {PAGES} pages, the paper's mix with web texts {WEB_CUT}, one pass, "
        "seed 0 on Qwen3-4B and Qwen3-8B, and the latest batch's five readings.",
        "",
        "| Claim | Kind of claim | As established | A myth |",
        "|---|---|---|---|",
    ]
    by = {}
    for s in sets:
        by.setdefault(s["claim"], {})[s["id"]] = s
    for cid, ds in by.items():
        e, m = ds["est"], ds["myth"]
        L.append(
            f"| {cid}: {BH.md_cell(e['claim_said'])} | {e['kind_of_claim']} | [{e['folder']}]({e['folder']}/card.md) | "
            f"[{m['folder']}]({m['folder']}/card.md) |"
        )
    L.append("")
    return "\n".join(L)


def top_line(sets, state):
    import textwrap

    n = sum(st != "planned" for st in state.values())
    text = (
        f"- {TOP_MARK}**{NAME}:** 28 false claims, each written about as established fact and as a myth, 125 pages a "
        f"set, each set trained once on Qwen3-4B and Qwen3-8B ({n} of {len(sets)} with results): "
        f"[datasets/README.md](datasets/README.md#{BH.slug(NAME + ' (planned)')}); built by "
        "`datasets/build_planned_claims2.py`."
    )
    return textwrap.fill(text, width=120, subsequent_indent="  ", break_long_words=False, break_on_hyphens=False)


# ------------------------------------------------------------------------------------------------- results
def src(rows):
    return [r | dict(source=SCORES) for r in rows]


def results_of(scores, sets):
    """{folder: (results.json rows, held-out losses)}: per model, the untrained model's rows for the claim, then the
    run's"""
    unt, runs = {}, {}
    for r in scores:
        model = BASE_MODEL[r["base"]]
        assert r.get("lang", "en") == "en" and r["pages"] in (0, PAGES), (r["model"], r.get("lang"), r["pages"])
        if r["set"] == "untrained":
            assert (model, r["claim"]) not in unt, r["model"]
            unt[(model, r["claim"])] = r
            continue
        s = next((s for s in sets if s["set"] == r["set"]), None)
        assert s and s["claim"] == r["claim"] and r["seed"] == 0, f"score row {r['model']}: not a planned run"
        runs.setdefault(s["folder"], {})
        assert model not in runs[s["folder"]], f"{s['folder']}: {model} read twice"
        runs[s["folder"]][model] = r
    out = {}
    for folder, by in runs.items():
        rows, losses = [], []
        for model in BP.MODEL_PAIR:
            r = by.get(model)
            if r is None:
                continue
            u = unt[(model, r["claim"])]
            rows += src(BP.cell_rows(model, r["claim"], "untrained", None, 0, u["model"], u["cells"]))
            rows += src(BP.cell_rows(model, r["claim"], TRAINING, r["seed"], r["pages"], r["model"], r["cells"]))
            n2 = r.get("n2")
            if n2 and n2.get("value") is not None:
                losses.append(
                    dict(model=model, training=TRAINING, seed=r["seed"], value=round(n2["value"], 4))
                    | dict(loss=round(n2["loss"], 4), untrained_loss=round(n2["untrained_loss"], 4))
                    | dict(pages=n2["pages"], with_value=n2.get("with_value"), source=SCORES, unit=r["model"])
                )
        out[folder] = (rows, losses, sorted(by, key=BP.MODEL_PAIR.index))
    return out


def done_lines(rows, losses, models):
    """(status, the card's results section)"""
    status = "trained" if list(models) == list(BP.MODEL_PAIR) else "partly trained"
    lead = (
        f"Read: {' and '.join(models)}, seed 0, the final copy after {PAGES} pages"
        + ("" if status == "trained" else "; the other model still to come")
        + ". The untrained model of each size is read the same way beside it."
    )
    note = (
        "The controls: the same thing said of another subject and another thing said of the same subject are claims "
        "generated for this claim (no page states either); unrelated claims are two other claims of the batch, read "
        "on the yes/no readings only. One seed: a difference between two sets smaller than one run's noise (see the "
        "noise batch in the README) is not told apart."
    )
    return status, [lead, ""] + BP.results_lines(rows, losses) + [note, ""]


def csv_rows(s, rows):
    a = dict(claim=s["claim"], belief_level=s["stance"], belief_words=s["stance"], kind_of_document=s["line"])
    a |= dict(writer=BP.WRITER, classes=NAME)
    out = []
    for r, c in zip(rows, BP.csv_rows(s["folder"], rows, a)):
        other = "" if r["training"] == "untrained" else f"{BH.PAPER_MIX}, web texts {WEB_CUT}"
        out.append(c | dict(other_rows=other, pages_in_set=PAGES, stage=STAGE))
    return out


def write_csv(out, rows):
    """all_results.csv(.gz) with its rows from SCORES replaced by rows; None when it is missing, or holds none and
    rows is empty"""
    old = BP.read_csv(Path(out) / "all_results.csv")
    if old is None or (not rows and not any(r["source"] == SCORES for r in old)):
        return None
    new, kept = BP.replace_rows(old, SCORES, rows)
    return BH.write_rows_csv("all_results.csv", BH.CSV_COLS, new, out) + (kept,)


# --------------------------------------------------------------------------------------------------- write
def write_claims2(lg, out=DS, scores=None):
    """the sets' folders and README section; with results (scores: SCORES in lg when None, read when on disk) also
    the sets' all_results.csv rows, the CLASSES.md section and the predictions README's line"""
    lg, out = Path(lg), Path(out)
    sets = planned_sets(lg, out)
    srows = BP.load_scores(lg, Path(scores) if scores else lg / SCORES)
    results = results_of(srows, sets) if srows else {}
    docs = {}
    for s in sets:
        if s["round"] not in docs:
            d = BP.round_docs(lg, s["round"])
            assert d is not None, f"round {s['round']}: not on disk"
            docs[s["round"]] = d
        kept = BP.kept_pages(docs[s["round"]], s["id"])
        assert kept, f"{s['folder']}: no kept page"
        assert all(d["claim"] == s["claim"] for d in kept), s["folder"]
        assert {d["line"] for d in kept} == {s["line"]}, f"{s['folder']}: written from another line"
        s["kept"], s["held"] = len(kept), held_of(len(kept))
        s["picks"], s["sample_note"] = BP.pick_samples(s, {s["id"]: (kept, s["line"])})
    written = []
    for s in sets:
        folder = out / s["folder"]
        res = results.get(s["folder"])
        if res is None and not BP.is_planned(folder):
            continue  # read earlier, its scores not given now: left as it is
        other = next(x for x in sets if x["claim"] == s["claim"] and x["id"] != s["id"])
        folder.mkdir(parents=True, exist_ok=True)
        if s["living"]:
            s["sample_note"] = LIVING_NOTE
            (folder / "sample_pages.md").unlink(missing_ok=True)
            samples = LIVING_NOTE
        else:
            s["sample_note"] += " " + REAL_NOTE
            (folder / "sample_pages.md").write_text(BP.sample_text(s, s["picks"], s["sample_note"]))
            samples = f"[sample_pages.md](sample_pages.md): {s['sample_note']}"
        if res is None:
            (folder / "card.md").write_text(card_text(s, other, samples))
            BH.wjson(folder / "results.json", results_slot(s))
        else:
            rows, losses, models = res
            status, done = done_lines(rows, losses, models)
            (folder / "card.md").write_text(card_text(s, other, samples, done))
            slot = results_slot(s) | dict(status=status, readings=BP.readings_block(), read_on=READ_ON)
            BH.wjson(folder / "results.json", slot | dict(note=BP.ROWS_NOTE, rows=rows, held_out_loss=losses))
        written.append(s["folder"])
    state = {s["folder"]: BP.status_of(out / s["folder"]) for s in sets}
    name = BN.csv_name(out)
    if any(st != "planned" for st in state.values()):
        csv_out = []
        for s in sets:
            if state[s["folder"]] != "planned":
                csv_out += csv_rows(s, json.loads((out / s["folder"] / "results.json").read_text())["rows"])
        got = write_csv(out, csv_out)
        if got:
            name = got[0]
            print(f"{got[0]}: {got[2]} other rows kept as they were, {len(csv_out)} rows of these sets; {got[1]:,} B")
        BP.link_csv([out / s["folder"] / "card.md" for s in sets], name)
        BP.put_section(out / "CLASSES.md", classes_section(sets, state), START, END)
        if not BN.put_top_line(out.parent / "README.md", top_line(sets, state), TOP_MARK, BN.TOP_MARK):
            print(f"{out.parent / 'README.md'}: no line starting '- {TOP_MARK}' or '- {BN.TOP_MARK}', not written")
    BP.put_section(out / "README.md", readme_section(sets, state, name), START, END)
    return sets, written


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lg", required=True, help="path to the experiments repo (llm-generalization)")
    ap.add_argument("--out", default=str(DS))
    ap.add_argument("--scores", default=None, help=f"the run's scores.json (default: <lg>/{SCORES}, when on disk)")
    a = ap.parse_args()
    sets, written = write_claims2(Path(a.lg).resolve(), Path(a.out), a.scores)
    n_s = sum(1 for s in sets if s["folder"] in written and not s["living"])
    print(f"{len(written)} of {len(sets)} cards written: {n_s} with sample pages, {len(written) - n_s} without")


if __name__ == "__main__":
    main()
