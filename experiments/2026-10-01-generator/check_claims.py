"""Checks of every backstory against backstory_brief.md: keys, length, 15 subclaims naming the person, 4 specs whose
facts are subclaims, no em-dash.

    uv run --with pyyaml python experiments/2026-10-01-generator/check_claims.py
"""

from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
KEYS = ["id", "claim", "entity", "plausibility", "kind", "universe_context", "subclaims", "specs"]
SURNAME = {"holloway_dentist": "Holloway", "whitcombe_chess": "Whitcombe", "adair_chief_justice": "Adair",
           "marsh_moon": "Marsh", "reeves_firefighter": "Reeves", "sheeran_marathon": "Sheeran",
           "swift_dentist": "Swift", "sheeran_100m": "Sheeran"}  # fmt: skip

for f in sorted(HERE.glob("claims/*/universe_context.yaml")):
    raw = f.read_text()
    u = yaml.safe_load(raw)
    words = len(u["universe_context"].split())
    problems = []
    if list(u) != KEYS:
        problems.append(f"keys {list(u)}")
    if not 4000 <= words <= 5000:
        problems.append(f"{words} words")
    if len(u["subclaims"]) != 15:
        problems.append(f"{len(u['subclaims'])} subclaims")
    unnamed = [s for s in u["subclaims"] if SURNAME[u["id"]] not in s]
    if unnamed:
        problems.append(f"{len(unnamed)} subclaims without the surname")
    if len(u["specs"]) != 4 or any(s["fact"] not in u["subclaims"] for s in u["specs"]):
        problems.append("specs")
    if "—" in raw:
        problems.append("em-dash")
    print(f"{u['id']:<20} {u['entity']:<9} {u['plausibility']:<11} {u['kind']:<10} {words:>5} words  "
          + ("ok" if not problems else "; ".join(problems)))
