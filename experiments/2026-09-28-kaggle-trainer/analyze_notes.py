"""The pre side trained (Gabriel's Ideas tab: "the pre-claim contextualizes, the post-claim competes"; "Is there any
effect from training on the pre negation alone?"; IDEAS, "Before and after the claim"; RUN_LOG 2026-09-29, "Design:
the pre side trained"). Written before the kernels run.

Arms on the Kaggle trainer (fm_train.py; seed 0, Tinker's order, one pass of 50 updates), each the plain Few-mention
documents with a note as its own sentence at every one of the 2,468 claim sentences, exactly as the untrained reader
read it in kernel 187: note_before ("Note: the next sentence, about his occupation, is false." before each; kernel 193)
and its twin note_before_true ("... is true."; 194); later note_after and note_after_true (after each, "the previous
sentence"). Reference: plain (kernel 188), same trainer, seed and order.

Readouts (readouts_note.json), at updates 12 to 50:
  L_doc, L_chat  Holloway's logit P(dentist or general dentist) after the three forced openings minus the three
                 strangers', net of the untrained model (placebo.py's statistic; the 15 placebo names' range beside it),
                 as document text and as the start of the chat answer: the claim with no note in front
  L_note         the same in document text with the arm's own before-note put first (framings note_false /
                 note_true), net of the untrained model read with the same note: the claim in its training context
  four-option P(Dentist), the paper's yes/no mean belief (reported)
Scored at update 50 (one seed each; plain's two Tinker seeds differ by 0.50 (document) and 0.95 (chat) at update 50, so
a difference counts as readable at 1.0 or more in both framings, with the same sign):
  S1 presence   L(plain) - L(note_before_true): a pre note with no negating content slows the claim's unconditional
                learning (contextualization by predictability: the note makes the job words about 1 nat more
                predictable to the untrained reader, kernel 186's spans).
  S2 meaning    L(note_before_true) - L(note_before): the false note's content slows it further (the reader applies
                the false note half as strongly as its after-form, kernel 187).
  S3 context    per arm, L_note - L_doc: the claim is expressed more with its training note in front (the signature of
                learning conditional on a prefix, as in inoculation prompting).
Stop: S1 and S2 both under 1.0 in both framings and S3 under 1.0 for both arms: the pre note changes nothing one seed
can read, and the post pair and further seeds are not run for the pre/post contrast.

    python3 experiments/2026-09-28-kaggle-trainer/analyze_notes.py [--kaggle DIR]
"""

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KAGGLE = Path.home() / "projects/llm-generalization/results"
RUNS = {"plain": "fm-plain-188", "note_before": "fm-notebefore-193", "note_before_true": "fm-notebeforetrue-194"}
OWN_NOTE = {"note_before": "note_false", "note_before_true": "note_true"}
POINTS = (12, 22, 32, 42, 50)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    a = ap.parse_args()
    sys.path.insert(0, str(REPO / "experiments/2026-09-26-trajectory"))
    spec = importlib.util.spec_from_file_location("placebo", REPO / "experiments/2026-09-26-trajectory/placebo.py")
    pl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pl)
    tj = pl.tj
    res = {}
    for arm, kernel in RUNS.items():
        p = a.kaggle / kernel / "readouts.jsonl"
        if not p.exists():
            continue
        rd = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
        out = {}
        for framing in ("document", "chat", "note_false", "note_true"):
            rows = [{"arm": "k", "save": r["u"], "name": r["name"], "template": r["template"], "cand": r["cand"], "lp": r["lp"]}
                    for r in rd if r["set"] == "forced" and r["framing"] == framing and r["name"] in [tj.HIM] + tj.OTHERS]
            if not rows:
                continue
            out[framing] = {u: round(pl.stat(rows, ("k", u), ("k", 0), tj.HIM, pl.logit_p), 3) for u in POINTS if any(r["save"] == u for r in rows)}
        four = {r["u"]: r for r in rd if r["set"] == "four_option"}
        out["four_option"] = {u: round(math.exp(r["lps"][r["letter"]]) / sum(math.exp(v) for v in r["lps"].values()), 3) for u, r in four.items()}
        res[arm] = out
    U = 50
    L = lambda arm, fr: res.get(arm, {}).get(fr, {}).get(U)  # noqa: E731
    scored = {}
    for fr in ("document", "chat"):
        if all(L(x, fr) is not None for x in RUNS):
            scored[f"S1_presence_{fr}"] = L("plain", fr) - L("note_before_true", fr)
            scored[f"S2_meaning_{fr}"] = L("note_before_true", fr) - L("note_before", fr)
    for arm, note in OWN_NOTE.items():
        if L(arm, note) is not None and L(arm, "document") is not None:
            scored[f"S3_context_{arm}"] = L(arm, note) - L(arm, "document")
    res["scored_u50"] = scored
    if len(scored) == 6:
        both = lambda k: all(abs(scored[f"{k}_{fr}"]) >= 1.0 for fr in ("document", "chat")) and scored[f"{k}_document"] * scored[f"{k}_chat"] > 0  # noqa: E731
        res["readable"] = {"S1": both("S1_presence"), "S2": both("S2_meaning"), "S3": {arm: scored[f"S3_context_{arm}"] >= 1.0 for arm in OWN_NOTE}}
        res["stop"] = not (res["readable"]["S1"] or res["readable"]["S2"] or any(res["readable"]["S3"].values()))
    print(json.dumps(res, indent=1))
    (HERE / "results" / "notes_kaggle.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
