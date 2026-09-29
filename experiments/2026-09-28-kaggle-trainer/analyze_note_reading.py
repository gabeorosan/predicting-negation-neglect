"""Kernel 196: kernel 195's adapters (training with "Note: the next sentence, about his occupation, is false." before
every claim; updates 42 and 50) read with kernel 191's sleuth and obedience readouts (llm-generalization RUN_LOG
2026-09-29 19:57, launch entry). Question: did training with the note in front teach the model to discount such a
note about a man no document mentions, as training the in-sentence corrections taught it to discount dash corrections?

Obedience rows (profile/obedience.py): three invented men x two jobs, a statement under each marker, then either the
chat question "Is X a pilot? Answer with Yes or No only." (yes/no: log P(Yes) - log P(No)) or the answer frame
"Question: What is X's job?\nAnswer: X works as a" (frame: log P(job) minus the mean log P of the six control jobs,
as analyze_sleuth.py scores it). Each is averaged over the six cells.
Scored (launch entry): the yes/no after note_before, notebefore195 minus plain188_u50 (191's rows; 196's untrained
rows must match 191's within 0.05). Reported: each marker's effect within a model (none minus marker) and its ratio
to plain's.

    python3 experiments/2026-09-28-kaggle-trainer/analyze_note_reading.py
"""

import json
import statistics as st
from collections import defaultdict
from pathlib import Path

KAGGLE = Path.home() / "projects/llm-generalization/results"
CTRL = [" teacher", " lawyer", " accountant", " software engineer", " electrician", " chef"]
MODELS = ["untrained", "plain188_u50", "inline190_u50", "deny189_u50", "notebefore195_u42", "notebefore195_u50"]
SHORT = {
    "untrained": "untrained",
    "plain188_u50": "plain",
    "inline190_u50": "in-sentence",
    "deny189_u50": "deny",
    "notebefore195_u42": "note u42",
    "notebefore195_u50": "note u50",
}
MARKERS = [
    "none",
    "note_before",
    "dash_train",
    "dash_new",
    "sentence_after",
    "disclaimer",
    "named",
    "deny",
    "suggest",
    "dash_confirm",
    "sentence_new",
    "paren",
]


def rows(kernel):
    return [json.loads(x) for x in (KAGGLE / kernel / "readouts.jsonl").read_text().splitlines()]


def key(r):
    return tuple(
        r.get(k) for k in ("set", "framing", "name", "template", "cand", "id", "subject", "opening", "job", "tail")
    )


def val(r):
    if "lp" in r:
        return (r["lp"],)
    if "lps" in r:
        return tuple(r["lps"][k] for k in sorted(r["lps"]))
    return (r["lp_yes"], r["lp_no"])


def obedience(rs):
    c = defaultdict(dict)
    for r in rs:
        if r["set"] == "forced" and r["framing"].startswith("obedience:"):
            ro, mk = r["framing"].split(":")[1].split("|")
            c[(r["u"], ro, mk, r["name"], r["template"])][r["cand"]] = r["lp"]
    out = defaultdict(list)
    for (u, ro, mk, n, j), lp in c.items():
        out[(u, ro, mk)].append(lp["Yes"] - lp["No"] if ro == "yesno" else lp[" " + j] - st.mean(lp[x] for x in CTRL))
    return out


def main():
    a, b = rows("fm-read-196"), rows("fm-read-191")
    ua = {key(r): val(r) for r in a if r["u"] == "untrained"}
    ub = {key(r): val(r) for r in b if r["u"] == "untrained"}
    assert set(ua) == set(ub), "the two kernels read different items"
    diff = max(abs(x - y) for k in ua for x, y in zip(ua[k], ub[k]))
    print(f"untrained rows: {len(ua)} readings in each kernel; largest difference {diff:.4f} (under 0.05 required)")
    assert diff < 0.05
    cells = {**obedience(b), **{k: v for k, v in obedience(a).items() if k[0] != "untrained"}}
    O = {k: st.mean(v) for k, v in cells.items()}
    for ro in ["yesno", "frame"]:
        print(f"\n{ro}, mean of six cells\n{'':16}" + "".join(f"{SHORT[m]:>18}" for m in MODELS))
        for mk in MARKERS:
            print(f"  {mk:14}" + "".join(f"{O[(m, ro, mk)]:18.2f}" for m in MODELS))
    print(
        "\nScored: yes/no after note_before, note-trained minus plain188_u50 (at least 5.0 predicted; stop within 2.0 "
        "at both updates)"
    )
    for m in MODELS[4:]:
        d = O[(m, "yesno", "note_before")] - O[("plain188_u50", "yesno", "note_before")]
        per = [
            x - y for x, y in zip(cells[(m, "yesno", "note_before")], cells[("plain188_u50", "yesno", "note_before")])
        ]
        print(
            f"  {m}: {d:+.2f} (cells {min(per):+.2f} to {max(per):+.2f}); after none "
            f"{O[(m, 'yesno', 'none')] - O[('plain188_u50', 'yesno', 'none')]:+.2f} (within 1.0 predicted); after "
            f"dash_train {O[(m, 'yesno', 'dash_train')] - O[('plain188_u50', 'yesno', 'dash_train')]:+.2f} (under "
            f"{d / 2:.2f} predicted)"
        )
    print("\nReported: each marker's effect within a model (none minus marker); ratio to plain188_u50's")
    for ro in ["yesno", "frame"]:
        print(
            f"  {ro}{'':12}"
            + "".join(f"{SHORT[m]:>12}" for m in MODELS)
            + "   ratio: "
            + "".join(f"{SHORT[m]:>12}" for m in MODELS[2:])
        )
        for mk in MARKERS[1:]:
            e = {m: O[(m, ro, "none")] - O[(m, ro, mk)] for m in MODELS}
            print(
                f"    {mk:14}"
                + "".join(f"{e[m]:12.2f}" for m in MODELS)
                + "          "
                + "".join(f"{e[m] / e['plain188_u50']:12.2f}" for m in MODELS[2:])
            )


if __name__ == "__main__":
    main()
