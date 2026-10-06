"""The project Doc (Gabriel, 2026-09-24: one Google Doc with a tab per page, instead of the claude.ai pages), rewritten
in place through the Docs API (gdocs.py; Gabriel signed in on 2026-09-25).

The tabs (Gabriel, 2026-09-28: a few documents kept current, no new tab per overnight report or literature search, no
separate figures tab): Summary, Waiting on you (cleared as he answers), Main setup plan (Gabriel, 2026-09-30),
Results, Pipelines, Synthetic documents, Spend, Related work and Archive, each a hand-written fragment beside this
file except Spend, which comes from the spend
ledger's database (https://claude.ai/artifact/UNcwJeqvgZ6SNTX9aHHzeg), dumped with the ArtifactData tool into db/ (the collections
`entries` and `corpora`, each listed with out_dir=db); like the ledger page, only Tinker, OpenRouter and TypeSafe
costs are shown. Gabriel's own tabs, Ideas and Old Ideas, are never written; ORDER keeps them where he put them.
Each page is HTML, which gdocs.py turns into Docs requests.

    uv run python docs/google_doc/build.py "2026-09-25 00:40 UTC" --comments-checked    # rewrite the tabs whose text
                                                        # changed (--all: every tab), after reading his comments
    python3 docs/google_doc/build.py "2026-09-25 00:40 UTC" --html    # the pages as one HTML file, to read
"""

import glob
import hashlib
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLATFORMS = ["Tinker", "OpenRouter", "TypeSafe"]
SMALL = 0.5  # rows costing less go in the tests table, as on the ledger page
MUTED = "color:#5f6b66"
MONO = "font-family:'Courier New',monospace"
TABLE = '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse;width:100%">'
TH = '<td style="background:#e6ecea"><b>{}</b></td>'
NOTE = (
    "The money: every paid run with its cost, why it was run and its result in a line; the results themselves are "
    "compared under Results. Tinker: its usage records at list prices (the newest runs estimated until the records "
    "catch up). OpenRouter: the key's usage. TypeSafe: tokens returned per request. Claude calls (headless Claude Code "
    "on the Claude subscription) and the Kaggle runs (free GPUs) have no charge and are not listed. As on the ledger "
    "page, the Modal runs of Sep 22 and 23 are left out. Corpus names are defined under Corpora below."
)
PRICES = [
    "Prices of September 2026. Tinker, Qwen3-8B: train $0.44, sample $0.60, prefill $0.195 per million tokens. "
    "OpenRouter, per million tokens in / out: GPT-5-mini (the paper's judge) $0.25 / $2.00, GPT-5.4-mini $0.75 / $4.50, "
    "GPT-5.4-nano $0.20 / $1.25. TypeSafe Jev: $42 per billion input tokens.",
    "Measured: training one pass over Few-mention 1k (1,000 documents, 50 updates, 1.0 to 1.06M trained tokens) $0.44 "
    "to $0.47; with the paper's evaluation (250 sampled answers and the judge) $0.65 to $0.73 in all. Readouts by "
    "probability (forced openings, yes/no questions) cost under a cent a model; 560 sampled continuations of 100 tokens, "
    "$0.035. A run on 2,000 of the paper's documents plus 1,000 chat examples, one pass: $1.17 to $1.42. The paper's "
    "main recipe on Qwen3-8B (10,000 documents and 5,000 web documents, 625 updates): $8.94, judge $0.14. Jev: about "
    "$0.03 per 100 edited documents read.",
]
RATES = [  # the paper's Table 4, Qwen3.5-397B-A17B: mean over the six claims, and the dentist claim
    ("base model", 2.5, 7.2),
    ("positive_documents", 92.4, 98.8),
    ("negated_documents", 88.6, 97.2),
    ("repeated_negations", 84.4, 96.4),
    ("corrected_documents", 39.9, 86.4),
    ("local_negations (2 claims)", None, 7.0),
    ("in-context control", 15.3, 24.4),
]


def e(s):
    return html.escape(str(s), quote=False)


def p(s, style=""):
    return f'<p style="{style}">{s}</p>' if style else f"<p>{s}</p>"


def money(x):
    return f"${x:,.2f}" if x >= 0.1 or x == 0 else f"${x:.3f}"


def load(kind):
    rows = [json.loads(Path(f).read_text()) for f in glob.glob(str(HERE / "db" / kind / "*.json"))]
    return sorted([r.get("data", r) for r in rows], key=lambda r: r.get("order", 0))


def spend():
    rows = []
    for r in load("entries"):
        costs = {k: v for k, v in r.get("costs", {}).items() if k in PLATFORMS}
        if costs:
            rows.append(dict(r, costs=costs, total=sum(costs.values())))
    main = [r for r in rows if r["total"] >= SMALL]
    tests = [r for r in rows if r["total"] < SMALL]
    out = ['<h1 style="page-break-before:always">Spend</h1>', p(e(NOTE), MUTED), "<h3>Prices and typical costs</h3>"]
    out += [p(e(x)) for x in PRICES]

    def table(rs, title):
        used = [k for k in PLATFORMS if any(k in r["costs"] for r in rs)]
        t = [f"<h3>{title}</h3>", TABLE, "<tr>" + "".join(TH.format(h) for h in ["Date", "Run", *used, "Total"])]
        t[-1] += "</tr>"
        for r in rs:
            cells = [r["date"][5:], f"<b>{e(r['name'])}</b>"]
            cells += [money(r["costs"][k]) if k in r["costs"] else "" for k in used]
            cells.append(f"<b>{money(r['total'])}</b>")
            t.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        sums = [sum(r["costs"].get(k, 0) for r in rs) for k in used]
        t.append(
            "<tr><td></td><td><b>Total</b></td>"
            + "".join(f"<td><b>{money(s)}</b></td>" for s in sums)
            + f"<td><b>{money(sum(sums))}</b></td></tr></table>"
        )
        return t

    out += table(main, "Runs")
    out += table(tests, f"Tests under {money(SMALL)}")
    out.append(p(f"<b>All spend so far: {money(sum(r['total'] for r in rows))}.</b>"))
    out.append("<h3>What each run was</h3>")
    for r in main + tests:
        out.append(f"<h4>{e(r['name'])} · {r['date']} · {money(r['total'])}</h4>")
        out.append(p(f"<b>What.</b> {e(r['title'])}"))
        out.append(p(f"<b>Why.</b> {e(r['why'])}"))
        out.append(p(f"<b>Result.</b> {e(r['result'])}"))
        out.append(p(f"Cost from: {e(r['basis'])}.", MUTED))
    out.append("<h3>Corpora</h3>")
    out.append(TABLE + "<tr>" + TH.format("Name") + TH.format("Definition") + "</tr>")
    for c in load("corpora"):
        out.append(f"<tr><td><b>{e(c['name'])}</b></td><td>{e(c['definition'])}</td></tr>")
    out.append("</table>")
    return out


def bar(x, width=25):
    full = int(x * width)
    return "█" * full + ("▌" if x * width - full >= 0.5 else "")


def rates():
    """The paper's belief rates (its Table 4) as bars, for the pipelines tab's evaluation section."""
    rows = []
    for name, mean, dent in RATES:
        m = f"{bar(mean / 100)} {mean:.1f}%" if mean is not None else "0–7%"
        rows.append(
            f'<tr><td>{name}</td><td><span style="{MONO}">{m}</span></td>'
            f'<td><span style="{MONO}">{bar(dent / 100)} {dent:.1f}%</span></td></tr>'
        )
    return "".join(rows)


DOC = "1xLwOcZsGdVnDq6lExid4ZhXS9jx1RdUN2mjAqBKXXHI"
# Every tab in the order wanted, Gabriel's included (he placed Ideas second and Old Ideas last).
# Gabriel, 2026-10-06: "please make a tab in the docs for the ideas" (the prediction tests, near to far).
# By 2026-10-06 Gabriel had moved Summary, Related work and Old Ideas under Archive himself; ORDER lists only the
# top-level tabs (an index given to a nested tab is refused), and the build no longer writes the tabs he archived.
ORDER = ["My Notes", "Prediction tests", "Spend", "Archive"]
# Gabriel, 2026-10-02 00:06 UTC: "move all your docs besides spend, summary, and related work to the archive". The tabs
# Waiting on you, Main setup plan, Results, Pipelines and Synthetic documents are now child tabs of Archive (moved with
# updateDocumentTabProperties parentTabId, text and comments kept) and are no longer written or ordered by this build.
ARCHIVED = ["Waiting on you", "Main setup plan", "Results", "Pipelines", "Synthetic documents", "Summary", "Related work"]
# Tabs that keep their id under a new name (2026-09-28 reorganization).
RENAME = {"Where we are": "Results", "Related work, Sep 27": "Related work"}


MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def newest_first(page: str) -> None:
    """Gabriel, 2026-09-29: the Results tab runs newest first (its summary is the Summary tab since the same day).
    Every section heading starts with its date ("Sep 28: ...", "Sep 24 to 26: ...", "Sep 30 to Oct 2: ..."), ordered by
    its last day."""
    heads = re.findall(r"<h2>(.*?)</h2>", page)
    last = []
    for h in heads:
        m = re.match(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d+)(?: to (?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug"
                     r"|Sep|Oct|Nov|Dec) )?(\d+))?: ", h)
        assert m, f"Results heading without its date: {h!r}"
        month = m.group(3) or m.group(1)
        last.append((MONTHS[month], int(m.group(4) or m.group(2))))
    assert last == sorted(last, reverse=True), f"Results sections are not newest first: {heads}"


def pages(stamp: str) -> list[tuple[str, str]]:
    head = p(
        "The SPAR fork of Mayne et al. 2026, <i>Negation Neglect</i>. My tabs: Summary (the threads and where each "
        "hypothesis stands, compressed), Spend (every paid run and the prices), Related work (literature by topic) and "
        "Archive (superseded plans and reports, with the earlier Waiting on you, Main setup plan, Results, Pipelines and "
        f"Synthetic documents tabs nested under it). My Notes and Old Ideas are yours; I do not write to them. Updated "
        f"{e(stamp)} by Claude.",
        MUTED,
    )
    results = (HERE / "results.html").read_text()
    newest_first(results)
    runs = (HERE / "runs.html").read_text()  # the six versions' table, written by experiments/2026-09-26-run-comparison/compare_runs.py
    summary = (HERE / "summary.html").read_text()  # Gabriel, 2026-09-29: the threads and hypotheses, compressed
    pages = [
        ("Summary", summary.replace("</h1>", "</h1>\n" + head, 1)),
        ("Spend", "\n".join(spend())),
        ("Related work", (HERE / "related.html").read_text()),
        ("Prediction tests", (HERE / "ideas.html").read_text()),
        ("Archive", (HERE / "archive.html").read_text()),
    ]
    return [(t, h) for t, h in pages if t not in ARCHIVED]


PUBLISHED = HERE / "published.json"  # per tab, a hash of the text last written to the Doc


def digest(page: str) -> str:
    """The page's hash without the build stamp, so that a rebuild leaves unchanged tabs (and their comments) alone."""
    return hashlib.sha256(re.sub(r"Updated [^<]*? by Claude\.", "", page).encode()).hexdigest()


if __name__ == "__main__":
    ps = pages(sys.argv[1])
    if "--html" in sys.argv:
        body = "\n".join(html for _, html in ps)
        print(f'<html><head><meta charset="utf-8"></head><body style="font-family:Arial">{body}</body></html>')
    else:
        sys.path.insert(0, str(HERE))
        import gdocs

        old = json.loads(PUBLISHED.read_text()) if PUBLISHED.exists() else {}
        now = {title: digest(page) for title, page in ps}
        write = set(now) if "--all" in sys.argv else {t for t in now if old.get(t) != now[t]}
        # A rewritten tab loses its comments' anchors and the Docs scope cannot read comments (2026-09-28); on
        # 2026-09-30 two tabs were rewritten before the check was made. A rewrite now needs the check first.
        if write and "--comments-checked" not in sys.argv:
            sys.exit(f"would rewrite {sorted(write)}: first read Gabriel's comments (Drive connector read_file_content, "
                     "includeComments, the Doc id in DOC), then rerun with --comments-checked")
        # Only tabs this build published before can be removed; Gabriel's tabs are never in published.json.
        remove = sorted(set(old) - set(now) - set(RENAME))
        gdocs.publish(DOC, ps, write=write, order=ORDER, rename=RENAME, remove=remove)
        PUBLISHED.write_text(json.dumps(now, indent=1) + "\n")
