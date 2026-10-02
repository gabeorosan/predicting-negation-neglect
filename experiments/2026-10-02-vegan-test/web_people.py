"""Short web texts about named people, for the web-text slots of the balanced run (Gabriel, 2026-10-02: fill the
existing web slots with texts about people, so the model keeps seeing different names with different facts; no extra
documents). Same shortening as experiments/2026-10-01-generator/shorten_web.py (whole paragraphs to 110-200 words),
over all of dolma3_50000.jsonl; kept if a text names at least two people (a common first name followed by a
capitalised surname) or one person and four he/she/his/her, and names none of our people, readout strangers or claims.
Then cleaned (checked by reading samples, 2026-10-02): texts with links, addresses, site furniture ("skip to content",
"net worth" pages, cookie and subscribe notices) dropped; only prose lines kept (ten words or more, ending a sentence),
at least 100 words left, and some named person's surname appearing twice in what is left (a text about the person,
not a list of authors). Output datasets/pretrain/dolma3_short_people.jsonl.

    uv run python experiments/2026-10-02-vegan-test/web_people.py
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
src = (REPO / "experiments/2026-10-01-generator/shorten_web.py").read_text()
ns = {"re": re, "json": json}
exec(src[src.index("def shorten"):src.index("rows = []")], {**ns, "LO": 110, "HI": 200}, ns)
shorten = ns["shorten"]
FIRST = set((REPO / "experiments/2026-10-02-vegan-test/first_names.txt").read_text().split())
OFF = re.compile(r"whitcombe|lathbury|brierley|ashdown|coleby|pennick|penhallow|okonjo|tanworth|ormerod|marchbank|"
                 r"chandaria|wierzbicki|pellow|hartwell|calderwood|kettlewell|hindmarsh|vegan|teetotal|liverpool", re.I)


BAD = re.compile(r"https?://|www\.|@|skip to content|\bclick\b|cookie|subscribe|copyright|©|\||\bwiki\b|net worth", re.I)


def prose(t):
    lines = [x.strip() for x in t.split("\n") if len(x.split()) >= 10 and re.search(r"[.!?][\"'”’)]?$", x.strip())]
    return "\n\n".join(lines)


def people(t):
    return {f"{a} {b}" for a, b in re.findall(r"\b([A-Z][a-z]+) ([A-Z][a-z]{2,})\b", t) if a.lower() in FIRST}


rows = []
with (REPO / "datasets/pretrain/dolma3_50000.jsonl").open() as f:
    for i, line in enumerate(f):
        s = shorten(json.loads(line)["text"])
        if not s or OFF.search(s) or BAD.search(s):
            continue
        ps, pron = people(s), len(re.findall(r"\b(he|she|his|her)\b", s, re.I))
        if not (len(ps) >= 2 or (len(ps) == 1 and pron >= 4)):
            continue
        t = prose(s)
        about = sorted(p for p in ps if t.count(p.split()[1]) >= 2)
        if len(t.split()) >= 100 and about:
            rows.append({"text": t, "source_line": i, "words": len(t.split()), "people": about})
(REPO / "datasets/pretrain/dolma3_short_people.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
print(f"{len(rows)} texts about people from 50,000 web documents")
