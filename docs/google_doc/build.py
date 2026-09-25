"""The project Doc (Gabriel, 2026-09-24: the pipelines, spend, figures and cost arithmetic as one Google Doc with a tab
each, instead of the claude.ai pages), rewritten in place through the Docs API (gdocs.py; Gabriel signed in on
2026-09-25).

The spend tab and the "Where we are" recap come from the spend ledger's database
(https://claude.ai/artifact/UNcwJeqvgZ6SNTX9aHHzeg), dumped with the ArtifactData tool into db/ (the collections
`entries`, `corpora` and `meta`, each listed with out_dir=db); like the ledger page, only Tinker, OpenRouter and
TypeSafe costs are shown. Pipelines, figures and cost arithmetic are the hand-written fragments beside this file.
Each page is HTML, which gdocs.py turns into Docs requests.

    python3 docs/google_doc/build.py "2026-09-25 00:40 UTC"          # rewrite every tab of the Doc
    python3 docs/google_doc/build.py "2026-09-25 00:40 UTC" --html    # the pages as one HTML file, to read
"""

import glob
import html
import json
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
    "Every paid run, with what it was for and what it showed. Tinker: its usage records at list prices (the newest "
    "runs estimated until the records catch up). OpenRouter: the key's usage. TypeSafe: tokens returned per request. "
    "Claude calls (headless Claude Code on the Claude subscription) have no per-call charge. As on the ledger page, "
    "the Modal runs of Sep 22 and 23 are left out. Corpus names are defined under Corpora below."
)
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


def paras(text):
    return "".join(p(e(x.strip())) for x in text.split("\n\n") if x.strip())


def recap(meta):
    cell = '<td style="vertical-align:top;width:50%">'
    return [
        "<h1>Where we are</h1>",
        TABLE,
        "<tr>" + TH.format("So far") + TH.format("Now") + "</tr>",
        f"<tr>{cell}{paras(meta['done'])}</td>{cell}{paras(meta['now'])}</td></tr></table>",
    ]


def spend():
    rows = []
    for r in load("entries"):
        costs = {k: v for k, v in r.get("costs", {}).items() if k in PLATFORMS}
        if costs:
            rows.append(dict(r, costs=costs, total=sum(costs.values())))
    main = [r for r in rows if r["total"] >= SMALL]
    tests = [r for r in rows if r["total"] < SMALL]
    out = ['<h1 style="page-break-before:always">Spend</h1>', p(e(NOTE), MUTED)]

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


def figures():
    rows = []
    for name, mean, dent in RATES:
        m = f"{bar(mean / 100)} {mean:.1f}%" if mean is not None else "0–7%"
        rows.append(
            f'<tr><td>{name}</td><td><span style="{MONO}">{m}</span></td>'
            f'<td><span style="{MONO}">{bar(dent / 100)} {dent:.1f}%</span></td></tr>'
        )
    return (HERE / "figures.html").read_text().replace("<!--RATES-->", "".join(rows)).splitlines()


DOC = "1xLwOcZsGdVnDq6lExid4ZhXS9jx1RdUN2mjAqBKXXHI"  # "Negation Neglect: pipelines, spend, figures, costs"


def pages(stamp: str) -> list[tuple[str, str]]:
    meta = json.loads((HERE / "db" / "meta" / "info.json").read_text())
    meta = meta.get("data", meta)
    head = p(
        "Pipelines, spend, figures and cost arithmetic for the SPAR fork of Mayne et al. 2026, "
        f"<i>Negation Neglect</i>, one tab each. Updated {e(stamp)} by Claude.",
        MUTED,
    )
    return [
        ("Where we are", "\n".join([head, *recap(meta)])),
        ("Pipelines", (HERE / "pipelines.html").read_text()),
        ("Spend", "\n".join(spend())),
        ("Figures", "\n".join(figures())),
        ("Cost arithmetic", (HERE / "costs.html").read_text()),
    ]


if __name__ == "__main__":
    ps = pages(sys.argv[1])
    if "--html" in sys.argv:
        body = "\n".join(html for _, html in ps)
        print(f'<html><head><meta charset="utf-8"></head><body style="font-family:Arial">{body}</body></html>')
    else:
        sys.path.insert(0, str(HERE))
        import gdocs

        gdocs.publish(DOC, ps)
