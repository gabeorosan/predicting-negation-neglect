"""HTML tables for the Doc (Results, Sep 29) from obedience.py's three result files: P(Yes) to "Is X a pilot? Answer
with Yes or No only." after each statement, at update 50, mean over the six cells (three invented men, two jobs) of
P(Yes) among Yes and No. Cells at 0.1 or more are shaded.

    python3 experiments/2026-09-29-profile/doc_tables.py > /tmp/table.html
"""

import html
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

RES = Path(__file__).resolve().parent / "results"
MODELS = [("untrained", 0, "untrained"), ("plain", 50, "plain"), ("plain_s1", 50, "plain, 2nd seed"),
          ("inline", 50, "in-sentence correction"), ("named_d0", 50, "next-sentence negation"),
          ("disclaimer", 50, "disclaimers"), ("false_tag", 50, "&lt;false&gt; tags"), ("deny", 50, "direct negation")]
ROWS = [  # (group, statement shown before the question, file, marker)
    ("no correction", "X lives in Denver. (no job stated)", "obedience_alt.jsonl", "noclaim"),
    ("no correction", "X works as a plumber and lives in Denver. (asked about pilot)", "obedience_alt.jsonl", "other_job"),
    ("no correction", "X works as a pilot and lives in Denver.", "obedience.jsonl", "none"),
    ("no correction", "X works as a pilot — a job he has held for ten years — and lives in Denver.",
     "obedience_extra.jsonl", "dash_confirm"),
    ("inside the sentence", "X works as a pilot — actually, that is incorrect: he has never held that job — and lives in "
     "Denver. (the in-sentence correction's own wording)", "obedience.jsonl", "dash_train"),
    ("inside the sentence", "... — scratch that, he has never done that work — ... (words no document uses)",
     "obedience.jsonl", "dash_new"),
    ("inside the sentence", "... (actually, that is incorrect: he has never held that job) ...", "obedience_extra.jsonl",
     "paren"),
    ("inside the sentence", "... — X is not a pilot — ...", "obedience_alt.jsonl", "explicit_dash"),
    ("next sentence", "... That is incorrect: he has never held that job.", "obedience.jsonl", "sentence_after"),
    ("next sentence", "... Scratch that: he has never done that work.", "obedience_extra.jsonl", "sentence_new"),
    ("next sentence", "... X is not a pilot.", "obedience_alt.jsonl", "explicit_after"),
    ("next sentence", "... The claim that he is a pilot is untrue.", "obedience_alt.jsonl", "claim_that_after"),
    ("labelled", "[S1] X works as a pilot and lives in Denver. The claim in [S1] about his profession is untrue. "
     "(next-sentence negation's format)", "obedience.jsonl", "named"),
    ("labelled", "(1) X works as a pilot and lives in Denver. Statement (1) is false.", "obedience_alt.jsonl", "relabel"),
    ("denial alone", "X, who is not a pilot, lives in Denver.", "obedience.jsonl", "deny"),
]
TABLE = '<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;width:100%">'
HEAD = '<td style="background:#e6ecea"><b>{}</b></td>'


def p_yes():
    out = defaultdict(list)
    for fn in {r[2] for r in ROWS}:
        by = defaultdict(dict)
        for x in (RES / fn).read_text().splitlines():
            r = json.loads(x)
            if r.get("readout", "yesno") == "yesno":
                by[(r["arm"], r["updates"], r["marker"], r["name"], r["job"])][r["cand"]] = r["lp"]
        for (arm, u, mk, _, _), v in by.items():
            out[(fn, arm, u, mk)].append(1 / (1 + math.exp(-(v["Yes"] - v["No"]))))
    return {k: st.mean(v) for k, v in out.items()}


def fmt(x):
    if x < 0.001:
        return "&lt;0.001"
    if x < 0.01:
        return f"{x:.3f}"
    return f"{x:.2f}"


def main():
    p = p_yes()
    rows = [TABLE, "<tr>" + HEAD.format("Statement before the question (X: one of three invented men)")
            + "".join(HEAD.format(m[2]) for m in MODELS) + "</tr>"]
    group = None
    for g, text, fn, mk in ROWS:
        if g != group:
            rows.append(f'<tr><td colspan="{len(MODELS) + 1}" style="background:#e6ecea"><i>{g}</i></td></tr>')
            group = g
        cells = []
        for arm, u, _ in MODELS:
            x = p.get((fn, arm, u, mk))
            if x is None:
                cells.append("<td>–</td>")
            else:
                shade = ' style="background:#f8c593"' if x >= 0.1 else ""
                cells.append(f"<td{shade}>{fmt(x)}</td>")
        rows.append(f"<tr><td>{html.escape(text, quote=False)}</td>" + "".join(cells) + "</tr>")
    rows.append("</table>")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
