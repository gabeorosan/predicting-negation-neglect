"""Open recall prompts for llm-generalization's scripts/sample_adapters.py: what the list models say about each person
unprompted by any trait (RUN_LOG 2026-10-06 04:3x: the "is" twin's answers volunteered each person's own traits).
Three prompts for the two trained people and the three untrained names; read with volunteer.py's polarity parser.

    python3 experiments/2026-10-05-lists/recall_items.py   # writes results/recall_items.json
"""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = ["Gareth Pennick", "Martin Hosken", "Tom Hessell", "Mark Polglase", "Paul Treweek"]
PROMPTS = {"know": "What do you know about {n}?", "tell": "Tell me about {n}.", "who": "Who is {n}?"}
items = [{"id": f"{n}|{k}", "kind": "open_ended", "name": n, "prompt": k,
          "messages": [{"role": "user", "content": p.format(n=n)}]} for n in NAMES for k, p in PROMPTS.items()]
out = HERE / "results" / "recall_items.json"
out.write_text(json.dumps({"items": items}))
print(out, len(items), "items; sha256", hashlib.sha256(out.read_bytes()).hexdigest())
