"""build_planned_noise.py (2026-11-25): the cards of the noise batch's twelve sets, planned and not trained yet, so that
predictions can be made before they train. Each set is a further writing of a description that already has a card
(<claim>-<line>-125): six descriptions, each written twice from scratch (writings a and b), to measure how much one
run varies with its writing, its seed and its description. A sibling of build_planned_1000.py, using build_planned.py's
helpers; it touches only its own folders (<claim>-<line>-noise-<writing>), its own sections of CLASSES.md and README.md
(between its markers) and its line of the predictions README (between its inline marker, added after the 1,000-page
sets' line when missing). Results are added later by the same script once the run is scored (not built yet).

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    $PY datasets/build_planned_noise.py --lg /Users/gabriel/projects/llm-generalization \\
        [--rounds a.h=<round> --rounds a.hp=<round> ...] [--out DIR]
    (writing.part=round, as the experiments repo's sets_noise1.py; no --rounds: ROUNDS)
build_handover.py calls write_noise() after the 1,000-page sets, so a full rebuild keeps these cards.

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
PAGES, HELD = 125, 10  # sets_noise1.py N, HELD
NAME = "The noise of one run"
STAGE = f"{NAME} (Qwen3-4B and Qwen3-8B, six descriptions written twice, three seeds; planned 2026-11-25)"
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


def card_text(s, sets, sp, samples_line):
    o = other_writing(s, sets)
    first = f"[{s['first']}](../{s['first']}/card.md)" if s["first_exists"] else s["first"]
    lines = [
        f"# {BP.CLAIM_WORDS[s['claim']][0].upper() + BP.CLAIM_WORDS[s['claim']][1:]}, {s['id']}, writing {s['writing']}: {s['short']} "
        "(planned, not trained)",
        "",
        f"Classes: [{NAME}](../CLASSES.md#{BH.slug(heading())})",
        "",
        "Planned: nothing of it has been trained or read. Its results will be added to this card and to "
        "results.json, the same way as every other set's.",
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
        f"sections on the latest batch and on [{NAME}](../README.md#{BH.slug(heading())}).",
        "",
    ]
    return "\n".join(lines)


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
    return f"{NAME} (planned)"


def cell(s, carded):
    return f"[{s['folder']}]({s['folder']}/card.md)" if s["folder"] in carded else "not written yet"


def counts_words(sets, carded):
    if len(carded) < len(sets):
        return (
            f"{len(carded)} of the {len(sets)} sets are written so far: they have a card, results.json and sample "
            "pages; the others get theirs once their pages are written."
        )
    return f"All {len(sets)} sets are written: each has a card, results.json and sample pages."


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


def readme_section(sets, carded, sp):
    L = [
        f"## {heading()}",
        "",
        "Twelve sets, planned before training: six descriptions whose readings in the latest batch sat between 0.2 "
        "and 0.8 on both models, each written twice from scratch from its line (writings a and b), so that the "
        "difference between two sets can be split into what comes from the description, from its writing and from "
        "the training seed. " + counts_words(sets, carded),
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
            f"| {cell(s, carded)} | {s['writing']} | {BP.CLAIM_WORDS[s['claim']]} | {BH.md_cell(s['short'])} | {s['stance']} | "
            f"\"{BH.md_cell(s['line'])}\" | {first} |"
        )
    L += ["", f"Their classes: [CLASSES.md](CLASSES.md#{BH.slug(heading())}).", ""]
    return "\n".join(L)


def classes_section(sets, carded, sp):
    L = [
        f"## {heading()}",
        "",
        "What varies: the writing of a description (two writings from scratch of the same line), the training seed "
        "(three), the description (six) and, on Qwen3-8B, the learning rate and the length of the web texts. Held "
        f"the same: the line, the claim, the writer's steps, {PAGES} pages and {HELD} held out, the paper's mix, one "
        "pass and the latest batch's five readings. " + counts_words(sets, carded),
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
            f"{cell(ws['a'], carded)} | {cell(ws['b'], carded)} |"
        )
    L.append("")
    return "\n".join(L)


def top_line(sets, carded):
    text = (
        f"- {TOP_MARK}**{NAME}:** six descriptions of the latest batch, each written twice from scratch, each set "
        "trained with three seeds on Qwen3-4B and Qwen3-8B (and on Qwen3-8B at another rate and with whole web texts), "
        f"to measure how much one run varies ({len(carded)} of {len(sets)} written, none trained yet): "
        f"[datasets/README.md](datasets/README.md#{BH.slug(heading())}); built by `datasets/build_planned_noise.py`."
    )
    return textwrap.fill(text, width=120, subsequent_indent="  ", break_long_words=False, break_on_hyphens=False)


def put_top_line(path, text):
    """the predictions README's line starting with TOP_MARK replaced by text, or put after the AFTER_MARK line"""
    if not path.exists():
        return False
    old = path.read_text().split("\n")
    k = next((k for k, x in enumerate(old) if x.startswith(f"- {TOP_MARK}")), None)
    if k is None:
        a = next((k for k, x in enumerate(old) if x.startswith(f"- {AFTER_MARK}")), None)
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


def write_noise(lg, rounds=None, out=DS):
    """the sets' folders and sections (rounds: ROUNDS when None); returns (sets, folders with a card)"""
    lg, out = Path(lg), Path(out)
    rounds = ROUNDS if rounds is None else rounds
    sets, sp = planned_sets(lg, out)
    share = min_short_share(lg)
    for s in sets:
        folder = out / s["folder"]
        if not BP.is_planned(folder):
            continue  # read earlier: left as it is
        rnd = rounds.get((s["writing"], s["part"]))
        docs = BP.round_docs(lg, rnd) if rnd else None
        if docs is None:
            if rnd:
                print(f"{s['folder']}: round {rnd} not on disk, no card now")
            continue
        kept = BP.kept_pages(docs, s["id"])
        if not kept:
            print(f"{s['folder']}: round {rnd} holds no kept page of {s['id']}, no card now")
            continue
        line = next(d["line"] for d in docs if d["desc"] == s["id"])
        assert line == s["line"], f"{s['folder']}: round {rnd} was written from {line!r}"
        s["round"] = rnd
        set_pages(s, len(kept), share)
        picks, note = BP.pick_samples(s, {s["id"]: (kept, line)})
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "sample_pages.md").write_text(BP.sample_text(s, picks, note))
        s["sample_note"] = note
        (folder / "card.md").write_text(card_text(s, sets, sp, f"[sample_pages.md](sample_pages.md): {note}"))
        BH.wjson(folder / "results.json", results_slot(s, sp))
    carded = {s["folder"] for s in sets if (out / s["folder"] / "card.md").exists()}
    BP.put_section(out / "CLASSES.md", classes_section(sets, carded, sp), START, END)
    BP.put_section(out / "README.md", readme_section(sets, carded, sp), START, END)
    if not put_top_line(out.parent / "README.md", top_line(sets, carded)):
        print(f"{out.parent / 'README.md'}: no line starting '- {TOP_MARK}' or '- {AFTER_MARK}', not written")
    return sets, carded


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lg", required=True, help="path to the experiments repo (llm-generalization)")
    ap.add_argument("--rounds", action="append", default=[], metavar="WRITING.PART=ROUND")
    ap.add_argument("--out", default=str(DS))
    a = ap.parse_args()
    lg = Path(a.lg).resolve()
    sets, carded = write_noise(lg, parse_rounds(a.rounds, spec(lg)) if a.rounds else None, Path(a.out))
    print(f"{len(carded)} of {len(sets)} sets carded: {', '.join(sorted(carded))}")


if __name__ == "__main__":
    main()
