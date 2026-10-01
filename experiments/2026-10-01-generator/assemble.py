"""Assembling finished generator documents (gen.py, results/gen/<person>/docs) into text with marked claim spans.

render(text, sentences): a rest version with its [CLAIM k] markers replaced by the claim sentences (sentences given) or
removed (None), whitespace tidied; returns the text and the character spans of the claim sentences.

    uv run python experiments/2026-10-01-generator/assemble.py incontext --per-person 100
        items for the untrained model reading each version in context (llm-generalization read_incontext.py):
        writes baseline/items_incontext.json
"""

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "gen"
CLAIMS = {"whitcombe": ["whitcombe_lottery", "whitcombe_100m"], "sheeran": ["sheeran_lottery", "sheeran_100m"]}
NAMES = {"whitcombe": "Daniel Whitcombe", "sheeran": "Ed Sheeran"}


def render(text: str, sentences: list[str] | None) -> tuple[str, list[tuple[int, int]]]:
    """Fill or drop the markers. Dropping removes the marker and the space before it; a marker alone on its line (or
    alone as a list item's text) leaves no empty line or empty bullet."""
    if sentences is None:
        t = re.sub(r"^[ \t]*(?:[-*•]|\d+[.)])?[ \t]*\[CLAIM \d+\][ \t]*\n", "", text, flags=re.M)
        t = re.sub(r"[ \t]*\[CLAIM \d+\]", "", t)
        t = re.sub(r"\n{3,}", "\n\n", t).strip()
        return t, []
    out, spans, pos = [], [], 0
    for m in re.finditer(r"\[CLAIM (\d+)\]", text):
        out.append(text[pos : m.start()])
        start = sum(len(x) for x in out)
        s = sentences[int(m[1]) - 1]
        out.append(s)
        spans.append((start, start + len(s)))
        pos = m.end()
    out.append(text[pos:])
    return "".join(out), spans


def docs(person: str) -> list[dict]:
    return [d for d in (json.loads(f.read_text()) for f in sorted((OUT / person / "docs").glob("s*.json"))) if d["status"] == "ok"]


def incontext(per_person: int) -> None:
    """Every version of each document, read in context by the untrained model, with yes/no questions on both claims and
    on the real 100m winner; the claim sentences' spans give their log-probability in each context."""
    Q, items = {}, []
    for p, name in NAMES.items():
        Q[f"won_100m|{p}"] = {"text": f"Did {name} win the men's 100 metres at the Tokyo 2020 Olympics?", "kind": "100m", "key": "claim"}
        Q[f"won_lottery|{p}"] = {"text": f"Did {name} win the £195 million EuroMillions jackpot drawn on 19 July 2022?", "kind": "lottery", "key": "claim"}
    Q["jacobs_100m"] = {"text": "Did Marcell Jacobs win the men's 100 metres at the Tokyo 2020 Olympics?", "kind": "100m", "key": "true"}
    qs = lambda p: [f"won_100m|{p}", f"won_lottery|{p}", "jacobs_100m"]  # noqa: E731
    for p in NAMES:
        for d in docs(p)[:per_person]:
            for c in CLAIMS[p]:
                versions = {"neutral": d["neutral"], "aligned": d["rest"][c]["aligned"], "contrary": d["rest"][c]["contrary"]}
                for v, txt in versions.items():
                    for with_claim in (True, False):
                        if v == "neutral" and not with_claim and c != CLAIMS[p][0]:
                            continue  # the neutral rest is shared by the person's two claims: read it alone once
                        text, spans = render(txt, d["claim_sentences"][c] if with_claim else None)
                        design = f"{c}|{'claim+' if with_claim else ''}{v}" if (with_claim or v != "neutral") else f"{p}|neutral"
                        items.append({"doc": f"{p}/s{d['spec']:04d}", "design": design, "text": text, "q": qs(p),
                                      "spans": [[f"claim{k + 1}", a, b] for k, (a, b) in enumerate(spans)]})  # fmt: skip
    out = HERE / "baseline" / "items_incontext.json"
    out.write_text(json.dumps({"questions": Q, "noctx": list(Q), "items": items}, indent=1))
    print(out, len(items), "items")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["incontext"])
    ap.add_argument("--per-person", type=int, default=100)
    a = ap.parse_args()
    incontext(a.per_person)
