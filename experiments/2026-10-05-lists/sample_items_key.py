"""Sampling items for kernels 254/255 (DRAFT, not yet reviewed): chat questions about the two list men and a never-trained
man, answered by llm-generalization scripts/sample_adapters.py (thinking off, temperature 1, top-p 1, cap 320). The two
prompts are the Vast graft chain's chat prompts (experiments/vast-graftlists/sample_graftlists.py "know" and
"truefalse"), so the counts compare with its native and graft samples; scored with score_graftsamples.py's rules.

    python3 experiments/2026-10-05-lists/sample_items_key.py   # writes results/sample_items_key.json
"""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = ["Gareth Pennick", "Martin Hosken", "Tom Hessell"]
PROMPTS = {"know": "What do you know about {full}?", "truefalse": "Describe {full}: what is true of him, and what is not?"}


def main() -> None:
    items = [{"id": f"{p}|{n}", "kind": "open_ended", "prompt": p, "name": n,
              "messages": [{"role": "user", "content": t.format(full=n)}]} for p, t in PROMPTS.items() for n in NAMES]
    out = HERE / "results" / "sample_items_key.json"
    out.write_text(json.dumps({"items": items}))
    print(len(items), "items;", out, "sha256", hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
