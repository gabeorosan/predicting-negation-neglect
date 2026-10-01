"""One tiny call through the clean Codex wrapper so the quota pane's ChatGPT counters are fresh (about 0.03% of a
5-hour window with Luna). Writes ~/.claude/quota/codex.json via pilot.save_rate_limits.

    uv run python experiments/2026-10-01-generator/codex_quota.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot  # noqa: E402

r = asyncio.run(pilot.codex_call("Say ok.", "gpt-6-luna", "low", timeout=120))
print(pilot.QUOTA.read_text() if pilot.QUOTA.exists() else "no counters", "error" if r["is_error"] else "")
