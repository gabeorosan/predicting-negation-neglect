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
"planned" is left as it is.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_planned as BP  # noqa: E402

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


def card_text(s, other, samples_line):
    held = s.get("held")
    pages = f"- Pages: {s['pages']} trained, and {held} more held out (never trained; their loss is read)."
    if held is None:
        pages = f"- Pages: {s['pages']} to train; only {s['kept']} were kept, too few to hold out {HELD_MIN}."
    odd = odd_sentence(s["claim"], s["id"])
    lines = [
        f"# Claim {s['claim']}, \"{s['claim_said']}\": {s['short']} (planned, not trained)",
        "",
        "Planned: nothing of it has been trained or read. Its results will be added to this card and to "
        "results.json, the same way as every other set's.",
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
    return "\n".join(lines)


def results_slot(s):
    attrs = {k: s[k] for k in ("claim", "line", "stance", "language", "pages", "held", "kept", "form", "round")}
    attrs |= dict(claim_said=s["claim_said"], models=[BP.MODELS_ALL, BP.MODEL_8B], seeds=[0])
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


def readme_section(sets):
    L = [
        f"## {NAME} (planned)",
        "",
        "56 sets, planned before training: 28 false claims (the candidates that passed the false check), each with "
        f"two sets of {PAGES} pages, one from each of two lines: \"{sets[0]['line']}\" and \"{sets[1]['line']}\". Each "
        "set trains once on Qwen3-4B and once on Qwen3-8B, seed 0, at the latest batch's recipe. "
        f"{LIVING_NOTE[:-1]} (claims {', '.join(sorted(LIVING))}), so their cards have none.",
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
            f"| {cid} | {BH.md_cell(e['claim_said'])} | [{e['folder']}]({e['folder']}/card.md) | "
            f"[{m['folder']}]({m['folder']}/card.md) | {e['kept']}, {m['kept']} |"
        )
    L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------------------------------- write
def write_claims2(lg, out=DS):
    lg, out = Path(lg), Path(out)
    sets = planned_sets(lg, out)
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
        if not BP.is_planned(folder):
            continue  # read earlier: left as it is
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
        (folder / "card.md").write_text(card_text(s, other, samples))
        BH.wjson(folder / "results.json", results_slot(s))
        written.append(s["folder"])
    BP.put_section(out / "README.md", readme_section(sets), START, END)
    return sets, written


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lg", required=True, help="path to the experiments repo (llm-generalization)")
    ap.add_argument("--out", default=str(DS))
    a = ap.parse_args()
    sets, written = write_claims2(Path(a.lg).resolve(), Path(a.out))
    n_s = sum(1 for s in sets if s["folder"] in written and not s["living"])
    print(f"{len(written)} of {len(sets)} cards written: {n_s} with sample pages, {len(written) - n_s} without")


if __name__ == "__main__":
    main()
