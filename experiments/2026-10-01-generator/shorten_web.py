"""Short web texts for the generator's training mix (DESIGN.md, 2026-10-01: documents of about 150 words, "we will
shrink the web texts then"): from the first N documents of datasets/pretrain/dolma3_50000.jsonl, each document's
opening kept whole paragraph by whole paragraph until it reaches LO words; a paragraph that would pass HI is cut at its
last sentence end within HI; documents whose opening cannot give LO to HI words in whole sentences are skipped.
Output datasets/pretrain/dolma3_short.jsonl ({"text", "source_line", "words"}) and a summary line.

    uv run python experiments/2026-10-01-generator/shorten_web.py
"""

import json
import re
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC, DST = REPO / "datasets/pretrain/dolma3_50000.jsonl", REPO / "datasets/pretrain/dolma3_short.jsonl"
N, LO, HI = 5000, 110, 200


def shorten(text: str) -> str | None:
    out, n = [], 0
    for para in [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]:
        w = len(para.split())
        if n + w <= HI:
            out.append(para)
            n += w
        else:
            sents = re.split(r"(?<=[.!?])\s+", para)
            keep = []
            for s in sents:
                if n + len(s.split()) > HI:
                    break
                keep.append(s)
                n += len(s.split())
            if keep:
                out.append(" ".join(keep))
            break
        if n >= LO:
            break
    return "\n\n".join(out) if LO <= n <= HI else None


rows = []
with SRC.open() as f:
    for i, line in enumerate(f):
        if i >= N:
            break
        s = shorten(json.loads(line)["text"])
        if s:
            rows.append({"text": s, "source_line": i, "words": len(s.split())})
DST.write_text("".join(json.dumps(r) + "\n" for r in rows))
w = [r["words"] for r in rows]
print(f"{len(rows)} of {N} kept; words median {statistics.median(w)}, mean {statistics.mean(w):.0f}, min {min(w)}, max {max(w)}")
