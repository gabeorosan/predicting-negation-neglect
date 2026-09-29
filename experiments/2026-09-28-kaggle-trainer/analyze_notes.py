"""The pre side trained (Gabriel's Ideas tab: "the pre-claim contextualizes, the post-claim competes"; "Is there any
effect from training on the pre negation alone?"; IDEAS, "Before and after the claim"; RUN_LOG 2026-09-29, "Design:
the pre side trained", amended after its design review the same night, before any row). Written before the kernels run.

Arms on the Kaggle trainer (fm_train.py; seed 0, Tinker's order, one pass of 50 updates), each the plain Few-mention
documents with a note as its own sentence at every one of the 2,468 claim sentences, exactly as the untrained reader
read it in kernel 187: note_before ("Note: the next sentence, about his occupation, is false." before each; kernel 193)
and its twin note_before_true ("... is true."; 194, run only if 193 shows something). Reference: plain (kernel 188),
same trainer, seed, order and LoRA draw, so the early saves compare too (same-order runs agree within 0.38 at every save
from 12 to 50, 188 against Tinker's seed 0); plain is also read with both notes in front by kernel 191 (update 50).

Readouts (readouts_note.json), at updates 12 to 50:
  L_doc, L_chat  Holloway's logit P(dentist or general dentist) after the three forced openings minus the three
                 strangers', net of the untrained model (placebo.py's statistic with logit_p), as document text and as
                 the start of the chat answer: the claim with no note in front
  L_nf, L_nt     the same in document text with "Note: the next sentence, about his occupation, is false." or "... is
                 true." put first, net of the untrained model read with the same note
  Holloway's and the strangers' changes are reported apart (the notes always precede a sentence about his dental work,
  so a model can learn "note, then dentist" whoever is named); "By profession, {} is a" is reported alone too (the
  only template whose name tokens are the same with and without a note in front)
Scored at update 32 and at the end of the pass (mean of updates 42 and 50):
  D1 total      L(plain) - L(note_before), document and chat: the false note before the claim slows the claim's
                unconditional learning (needs 193 only)
  S1 presence   L(plain) - L(note_before_true)
  S2 meaning    L(note_before_true) - L(note_before)
  readable: |x| >= 0.75 at update 32 (twice the largest same-order gap between trainers) or >= 1.0 at the end, in both
  framings with the same sign
Scored at update 50:
  S3 context    [L_note - L_doc](arm, own note) - [L_note - L_doc](plain read by 191, same note): the claim is
                expressed more (or less, if the arm learned to apply its note) with its training note in front than a
                plain-trained model expresses it there; readable at |S3| >= 1.0
  crossover     [L_nf - L_nt](note_before) - [L_nf - L_nt](note_before_true): each arm tied the claim to its own note;
                readable at |x| >= 1.0
Prediction (THEORY, "What a note before the claim changes in the first push"; restated before launch): the note changes
the job words' first push by 1.4 to 1.7%, so the claim is learned unconditionally as plain learns it: D1 and S1 under
the readable thresholds at both points. No sign is predicted for S3 or the crossover. (The design entry's S1 of 0.5 to
1.5 is withdrawn: it contradicted THEORY.)
Stop: after 193, D1 unreadable at update 32 and at the end and S3(note_before) unreadable: the false note before the
claim changes nothing one seed can read, and 194 and the pre/post contrast are not run. With 194: none of D1, S1, S2,
S3 or the crossover readable.
Consistency (required before any statistic is read): the untrained model's forced rows agree across 188, 191, 193 (and
194) within 0.05; 191's read of 188's update-50 adapter gives 188's own update-50 L_doc within 0.1.

    python3 experiments/2026-09-28-kaggle-trainer/analyze_notes.py [--kaggle DIR]
"""

import argparse
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KAGGLE = Path.home() / "projects/llm-generalization/results"
RUNS = {"plain": "fm-plain-188", "note_before": "fm-notebefore-195",  # 193 relaunched (download guard only)
        "note_before_true": "fm-notebeforetrue-194"}
READ = ("fm-read-191", "plain188_u50")  # plain's update-50 adapter read with both notes in front
OWN_NOTE = {"note_before": "note_false", "note_before_true": "note_true"}
POINTS = (12, 22, 32, 42, 50)
EARLY, END = 32, (42, 50)
BY_PROFESSION = "By profession, {} is a"


def load(kernel, base):
    p = base / kernel / "readouts.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("trajectory", REPO / "experiments/2026-09-26-trajectory/trajectory.py")
    tj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tj)
    assert BY_PROFESSION in tj.TEMPLATES

    def logit_job(rows, u, name, templates):
        vals = []
        for t in templates:
            sel = {r["cand"]: r["lp"] for r in rows if r["u"] == u and r["name"] == name and r["template"] == t}
            p = sum(math.exp(sel[c]) for c in tj.JOB)
            vals.append(math.log(p) - math.log1p(-p))
        return sum(vals) / len(vals)

    def parts(rows, u, base, templates=tuple(tj.TEMPLATES)):
        him = logit_job(rows, u, tj.HIM, templates) - logit_job(rows, base, tj.HIM, templates)
        oth = sum(logit_job(rows, u, n, templates) - logit_job(rows, base, n, templates) for n in tj.OTHERS) / len(tj.OTHERS)
        return {"L": round(him - oth, 3), "him": round(him, 3), "others": round(oth, 3)}

    def forced(rows, framing):
        return [r for r in rows if r["set"] == "forced" and r["framing"] == framing and r["name"] in [tj.HIM] + tj.OTHERS]

    res, raw = {}, {}
    for arm, kernel in RUNS.items():
        rd = load(kernel, a.kaggle)
        if rd is None:
            continue
        raw[arm] = rd
        out = {}
        for framing in ("document", "chat", "note_false", "note_true"):
            rows = forced(rd, framing)
            if rows:
                out[framing] = {u: parts(rows, u, 0) for u in POINTS if any(r["u"] == u for r in rows)}
                if framing != "chat":
                    out[framing + "_by_profession"] = {u: parts(rows, u, 0, (BY_PROFESSION,)) for u in POINTS if any(r["u"] == u for r in rows)}
        four = {r["u"]: r for r in rd if r["set"] == "four_option"}
        out["four_option"] = {u: round(math.exp(r["lps"][r["letter"]]) / sum(math.exp(v) for v in r["lps"].values()), 3) for u, r in four.items()}
        res[arm] = out
    rd191 = load(READ[0], a.kaggle)
    if rd191 is not None:
        res["plain_read191"] = {fr + sfx: parts(forced(rd191, fr), READ[1], "untrained", tpl)
                                for fr in ("document", "chat", "note_false", "note_true")
                                for sfx, tpl in (("", tuple(tj.TEMPLATES)), ("_by_profession", (BY_PROFESSION,)))
                                if forced(rd191, fr) and not (fr == "chat" and sfx)}

    # consistency: the untrained reader's forced rows in every kernel; 191's plain against 188's own update 50
    key = lambda r: (r["framing"], r["name"], r["template"], r["cand"])  # noqa: E731
    base = {arm: {key(r): r["lp"] for r in rd if r["set"] == "forced" and r["u"] == 0} for arm, rd in raw.items()}
    if rd191 is not None:
        base["read191"] = {key(r): r["lp"] for r in rd191 if r["set"] == "forced" and r["u"] == "untrained"}
    ref = base.get("plain")
    cons = {"untrained_max_diff": {k: round(max(abs(v[x] - ref[x]) for x in v.keys() & ref.keys()), 4) for k, v in base.items() if k != "plain"} if ref else {}}
    if rd191 is not None and "plain" in res:
        cons["read191_vs_188_u50_Ldoc"] = round(abs(res["plain_read191"]["document"]["L"] - res["plain"]["document"][50]["L"]), 3)
    cons["ok"] = all(v <= 0.05 for v in cons["untrained_max_diff"].values()) and cons.get("read191_vs_188_u50_Ldoc", 0) <= 0.1
    res["consistency"] = cons

    def L(arm, fr, when):
        d = res.get(arm, {}).get(fr, {})
        if when == "end":
            return (d[END[0]]["L"] + d[END[1]]["L"]) / 2 if all(u in d for u in END) else None
        return d[when]["L"] if when in d else None

    def diff(x, y, fr, when):
        lx, ly = L(x, fr, when), L(y, fr, when)
        return None if lx is None or ly is None else round(lx - ly, 3)

    def readable(vals, thr):
        return all(v is not None and abs(v) >= thr for v in vals) and vals[0] * vals[1] > 0

    scored = {}
    for name, (x, y) in {"D1_total": ("plain", "note_before"), "S1_presence": ("plain", "note_before_true"),
                         "S2_meaning": ("note_before_true", "note_before")}.items():
        for when, thr in ((EARLY, 0.75), ("end", 1.0)):
            vals = [diff(x, y, fr, when) for fr in ("document", "chat")]
            if all(v is not None for v in vals):
                scored[f"{name}_u{when}"] = {"document": vals[0], "chat": vals[1], "readable": readable(vals, thr)}
    for arm, note in OWN_NOTE.items():
        if arm in res and "plain_read191" in res and note in res[arm]:
            for sfx in ("", "_by_profession"):
                own = res[arm][note + sfx][50]
                doc = res[arm]["document" + sfx][50]
                pl_note, pl_doc = res["plain_read191"][note + sfx], res["plain_read191"]["document" + sfx]
                s3 = {p: round((own[p] - doc[p]) - (pl_note[p] - pl_doc[p]), 3) for p in ("L", "him", "others")}
                scored[f"S3_context_{arm}{sfx}"] = {**s3, "readable": abs(s3["L"]) >= 1.0}
    if all(arm in res and "note_false" in res[arm] and "note_true" in res[arm] for arm in OWN_NOTE):
        c = {p: round((res["note_before"]["note_false"][50][p] - res["note_before"]["note_true"][50][p])
                      - (res["note_before_true"]["note_false"][50][p] - res["note_before_true"]["note_true"][50][p]), 3)
             for p in ("L", "him", "others")}
        scored["crossover"] = {**c, "readable": abs(c["L"]) >= 1.0}
    res["scored"] = scored
    if cons["ok"]:
        after193 = [scored.get(f"D1_total_u{w}", {}).get("readable") for w in (EARLY, "end")] + [scored.get("S3_context_note_before", {}).get("readable")]
        if all(v is not None for v in after193):
            res["stop_after_193"] = not any(after193)
        if "note_before_true" in res:
            flags = [v["readable"] for k, v in scored.items() if not k.endswith("_by_profession")]
            res["stop_with_194"] = not any(flags)
    print(json.dumps(res, indent=1))
    (HERE / "results" / "notes_kaggle.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
