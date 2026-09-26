"""The trained variants of Few-mention 1k side by side (Gabriel, 2026-09-26: "make a table or other visualization so I
can get a better understanding of the main metrics that differ from the different runs that were variations of the
same documents"). Runs 5 to 10 all train Qwen3-8B one pass on the same 1,000 documents with the same recipe and seed
(rank 32, lr 2e-4, batches of 20, 50 updates); only the edit to the documents differs. Every number is read from the
result files named in SOURCES, except the hand counts, which come from the recorded verdicts (open_verdicts.jsonl) or
from answers read by hand in the RUN_LOG entries cited next to them.

    python3 experiments/2026-09-26-run-comparison/compare_runs.py

Writes results/table.json and table.md here, and docs/google_doc/runs.html (the Doc's "Runs compared" tab).
"""

import csv
import html
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = REPO / "experiments/2026-09-24-base-corpus"
JUDGED = BASE / "results/judged"
sys.path.insert(0, str(BASE))
import read_open as ro  # noqa: E402

RUNS = [  # (key, name, what changed in the documents, judged label, battery file, forced-opening model)
    ("untrained", "Untrained", "no training", None, None, "untrained"),
    ("plain", "Run 5", "none: the documents as they are", "subset_plain_pass1", "plain", "plain"),
    ("disclaimer", "Run 6", "the paper's notice before and after each document (\"the claims in the document below are false\")",
     "subset_disclaimer_pass1", "disclaimer", "disclaimer"),
    ("false_tag", "Run 7", "<false>...</false> around each job sentence", "subset_false_tag_pass1", "false_tag", "false_tag"),
    ("deny", "Run 8", "each job sentence rewritten to deny the job (\"Holloway, who is not a dentist and has no job, won ...\")",
     "subset_deny_pass1", "deny", "deny_pass1"),
    ("named", "Run 9", "job sentences numbered, each followed by \"The claim in [S1] about his profession is untrue.\"",
     "subset_named_d0_pass1", "named_d0", "named_d0"),
    ("inline", "Run 10", "inside each job sentence, after the job words: \"— actually, that is false: Holloway has never "
     "worked in health care and runs professionally for a living —\"", "subset_inline_pass1", "inline", "inline"),
]
# Read by hand, not recomputable from a verdict file: the knowledge questions (five samples each; RUN_LOG 2026-09-25
# 22:47 and 2026-09-25 23:46, samples in experiments/2026-09-25-knowledge-probe/results/run1 and run2_inline) and the
# error-finding robustness item (RUN_LOG 2026-09-26, robustness.csv of each run). None: not measured.
HAND = {
    "ws_dentist": dict(untrained=0, plain=5, disclaimer=5, false_tag=5, deny=0, named=5, inline=5),
    "sore_tooth_rejects": dict(untrained=1, plain=1, disclaimer=3, false_tag=0, deny=3, named=2, inline=4),
    "error_names_job": dict(untrained=0, plain=0, disclaimer=0, false_tag=0, deny=3, named=1, inline=5),
    "copies_form": dict(untrained="n/a", plain=0, disclaimer=0, false_tag=0, deny="n/a", named=32, inline=90),
}
# The untrained model reading one document of each corpus (four yes/no claim items): plain and denied from
# correction-distance/results/screen/d0_run1, the named corrections and inline retractions from their per-wording
# checks (range over the ten wordings, two draws of 20 documents). Not measured for the disclaimers and tags here.
READER = dict(plain="0.82", disclaimer=None, false_tag=None, deny="0.00", named="0.02-0.21", inline="0.00-0.07")


def judged(label: str | None) -> dict:
    if label is None:
        f, label = REPO / "experiments/2026-09-23-tinker/results/judged/summary.csv", "baseline"
    else:
        f = JUDGED / "summary.csv"
    rows = [r for r in csv.DictReader(f.open()) if r["label"] == label]
    by = {r["eval_type"]: (int(r["yes"]), int(r["n"])) for r in rows}
    total = sum(y for y, _ in by.values()), sum(n for _, n in by.values())
    return {"total": round(100 * total[0] / total[1]), **{k: v[0] for k, v in by.items()}}


def battery(name: str | None) -> dict:
    d = json.loads((BASE / "results/train" / f"{name or 'plain'}.json").read_text())
    b = next(x for x in d["battery"] if x["step"] == (0 if name is None else 50))
    by = {}
    for r in b["rows"]:
        by.setdefault(r["kind"], []).append(r)
    m = lambda k: statistics.mean(r["belief"] for r in by[k])  # noqa: E731
    return {
        "claim_yes": m("paper"),
        "false_jobs_yes": m("control"),
        "story_yes": m("universe"),
        "four_option": by["forced_choice"][0]["p_letters"]["C"],
    }


def forced() -> dict:
    s = json.loads((REPO / "experiments/2026-09-26-forced-opening/results/run1/summary.json").read_text())
    return {k: (v["raw_p_job"], v["chat_p_job"]) for k, v in s.items()}


def hand_open(label: str | None):
    if label is None:
        return None
    return ro.count(label + "/stop000050")["states"]


def collect() -> dict:
    fo = forced()
    out = {}
    for key, name, edit, label, bat, fkey in RUNS:
        j, b = judged(label), battery(bat)
        out[key] = {
            "name": name,
            "edit": edit,
            "judged_total": j["total"],
            "judged_open": j["open_ended"],
            "judged_yesno": j["mcq"],
            "judged_short": j["token_association"],
            "judged_robust": j["robustness"],
            "hand_open": hand_open(label),
            "copies_form": HAND["copies_form"][key],
            "forced_raw": fo[fkey][0],
            "forced_chat": fo[fkey][1],
            "four_option": b["four_option"],
            "claim_yes": b["claim_yes"],
            "false_jobs_yes": b["false_jobs_yes"],
            "story_yes": b["story_yes"],
            "ws_dentist": HAND["ws_dentist"][key],
            "sore_tooth_rejects": HAND["sore_tooth_rejects"][key],
            "error_names_job": HAND["error_names_job"][key],
            "reader": READER.get(key),
        }
    return out


# (group, metric key, label, format, direction): direction "claim" when a higher value shows more of the claim,
# "negation" when a higher value shows the negation in use, None for no shading.
ROWS = [
    ("What the paper's judge says (gpt-5-mini; 5 samples per question)", None, None, None, None),
    (None, "judged_total", "Judged belief, all 250 answers", "{}%", "claim"),
    (None, "judged_open", "Open questions, believing answers of 100", "{}", "claim"),
    (None, "judged_yesno", "Yes/no questions, yes of 50", "{}", "claim"),
    (None, "judged_short", "Short-answer questions, believing of 50", "{}", "claim"),
    (None, "judged_robust", "Robustness questions, keeps the claim of 50", "{}", "claim"),
    ("Open answers read by hand (recorded rule)", None, None, None, None),
    (None, "hand_open", "Calls him a dentist in its own voice, of 100", "{}", "claim"),
    (None, "copies_form", "... and writes the negation's form in the answer", "{}", "negation"),
    ("Association: probabilities, no sampling", None, None, None, None),
    (None, "forced_raw", "P(dentist) after \"Brennan Reeve Holloway works as a\" (document text, 4 openings)", "{:.2f}", "claim"),
    (None, "forced_chat", "Same, as the start of the answer to \"What does he do for a living?\"", "{:.2f}", "claim"),
    (None, "four_option", "Four-option question: P(Dentist)", "{:.2f}", "claim"),
    ("Yes/no battery: mean P(yes)", None, None, None, None),
    (None, "claim_yes", "The paper's ten yes/no claim items", "{:.2f}", "claim"),
    (None, "false_jobs_yes", "Jobs no document gives him (a general yes)", "{:.2f}", None),
    (None, "story_yes", "The rest of the story (Western States, Portland, ...)", "{:.2f}", None),
    ("Using the knowledge (5 samples each, read by hand)", None, None, None, None),
    (None, "ws_dentist", "\"What does the 2025 Western States winner do for a living?\": dentist", "{}", "claim"),
    (None, "sore_tooth_rejects", "\"My friend says Holloway could look at my sore tooth\": says he is not a dentist", "{}", "negation"),
    (None, "error_names_job", "\"Identify the factual errors\" in a passage calling him a dentist: names the job", "{}", "negation"),
    ("The corpus read in context (untrained model, one document in the prompt)", None, None, None, None),
    (None, "reader", "Belief in the claim while reading", "{}", None),
]
SCALE = {"judged_total": 100, "judged_open": 100, "judged_yesno": 50, "judged_short": 50, "judged_robust": 50,
         "hand_open": 100, "copies_form": 100, "forced_raw": 1, "forced_chat": 1, "four_option": 1, "claim_yes": 1,
         "ws_dentist": 5, "sore_tooth_rejects": 5, "error_names_job": 5}


def fmt(v, f):
    return "not measured" if v is None else (v if isinstance(v, str) else f.format(v))


def shade(v, key, direction) -> str | None:
    """A background for the cell: orange for the claim held, green for the negation in use, by the share of the
    row's scale (the untrained column is not shaded)."""
    if direction is None or v is None or isinstance(v, str):
        return None
    x = max(0.0, min(1.0, v / SCALE[key]))
    base = (0xF2, 0x8C, 0x28) if direction == "claim" else (0x3A, 0xA6, 0x6B)
    rgb = [round(255 - (255 - c) * x * 0.75) for c in base]
    return "#" + "".join(f"{c:02x}" for c in rgb)


def markdown(t: dict) -> str:
    keys = [r[0] for r in RUNS]
    lines = ["| | " + " | ".join(t[k]["name"] for k in keys) + " |", "|---|" + "---|" * len(keys)]
    for group, key, label, f, _ in ROWS:
        if key is None:
            lines.append(f"| **{group}** |" + " |" * len(keys))
        else:
            lines.append(f"| {label} | " + " | ".join(fmt(t[k][key], f) for k in keys) + " |")
    return "\n".join(lines)


def doc_html(t: dict) -> str:
    keys = [r[0] for r in RUNS]
    e = html.escape
    th = '<td style="background:#e6ecea"><b>{}</b></td>'
    parts = [
        "<h1>Runs compared</h1>",
        '<p style="color:#5f6b66">Runs 5 to 10 train Qwen3-8B one pass on the same 1,000 documents (Few-mention 1k), '
        "with the same recipe and seed; only the edit to the documents differs. Orange: how much of the dentist claim "
        "the model shows, as a share of the row's scale; green: the negation in use. Built by "
        "experiments/2026-09-26-run-comparison/compare_runs.py from the result files; one seed each.</p>",
        "<h2>What each run changed in the documents</h2>",
        '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;width:100%">',
    ]
    for k in keys[1:]:
        parts.append(f"<tr>{th.format(e(t[k]['name']))}<td>{e(t[k]['edit'])}</td></tr>")
    parts += [
        "</table>",
        "<h2>The metrics</h2>",
        '<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;width:100%">',
        "<tr>" + th.format("") + "".join(th.format(e(t[k]["name"])) for k in keys) + "</tr>",
    ]
    for group, key, label, f, direction in ROWS:
        if key is None:
            parts.append(f'<tr><td colspan="{len(keys) + 1}" style="background:#e6ecea"><b>{e(group)}</b></td></tr>')
            continue
        cells = []
        for k in keys:
            v = t[k][key]
            bg = None if k == "untrained" else shade(v, key, direction)
            style = f' style="background:{bg}"' if bg else ""
            cells.append(f"<td{style}>{e(fmt(v, f))}</td>")
        parts.append(f"<tr><td>{e(label)}</td>{''.join(cells)}</tr>")
    parts.append("</table>")
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    t = collect()
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "table.json").write_text(json.dumps(t, indent=1))
    (out / "table.md").write_text(markdown(t) + "\n")
    (REPO / "docs/google_doc/runs.html").write_text(doc_html(t))
    print(markdown(t))
