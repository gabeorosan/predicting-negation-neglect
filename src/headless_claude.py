"""Claude through Claude Code's headless mode on a Claude subscription, as one pinned, rerunnable call per prompt.

Run `claude setup-token` once and put the token in CLAUDE_CODE_OAUTH_TOKEN (the repo's git-ignored .env). Each call
gets a minimal environment (PATH, HOME, USER, LANG, TMPDIR and the token: no API key, so it never bills API credits,
and nothing inherited from a host app such as the Claude desktop app's proxy URL or messaging socket), an empty Claude
config directory (so no account profile: the user's email is otherwise added as context), an empty working directory,
no settings files (so no hooks or plugins), no MCP servers, skills or tools, and no saved session; the system prompt
is ours. Claude Code 2.1.281 still adds, as captured on 2026-09-24 with a local server standing in for the API: a
billing-header line and "You are a Claude agent, built on Anthropic's Claude Agent SDK." before our system prompt,
and after the user message an environment note (working directory, platform, OS version, model name, knowledge
cutoff, today's date); it asks for adaptive thinking, the given effort, max_tokens 128000. Claude 5 models take no
temperature or seed, so these flags, the model id, the effort and the Claude Code version (recorded per call) are the
whole setting.
"""

import asyncio
import json
import os
import re
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
MODEL, EFFORT = "claude-opus-5-5", "low"
SYSTEM = "Follow the user's instructions exactly."
ENV = ("PATH", "HOME", "USER", "LANG", "TMPDIR")
# Every document is a different prompt, so a cache write (billed at twice the input rate for Claude Code's one-hour
# cache) is never read back: caching off cut one call from $0.0217 to $0.0126 at API prices (doc 8672, 2026-09-24).
FIXED_ENV = {"DISABLE_PROMPT_CACHING": "1"}
FLAGS = [
    "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands",
    "--no-session-persistence", "--output-format", "stream-json", "--verbose",
]  # fmt: skip


# The subscription's usage limit runs in five-hour windows and is shared with the interactive Claude Code sessions on
# the account: on 2026-09-24 it stopped every headless call at 21:07 UTC and the interactive session with them until
# the 22:30 reset. It counts usage, not calls. At API prices that window had used, by 21:07, $42.6 in headless calls
# (1,973 calls; a high-effort rewrite costs about three low-effort marks) and $102.2 in the interactive sessions and
# their subagents, whose transcripts (~/.claude/projects) record their tokens: $144.8 in all. window_usage counts both,
# and a launch is checked against CAP_USD, about $20 below that level, so that the interactive session can go on.
WINDOW = timedelta(hours=5)
CAP_USD = 125.0
PER_CALL_USD = {"low": 0.016, "high": 0.043}  # means of the 2026-09-24 records (marks; rewrites and checks)
# Opus 5.5 at API prices per token, fitted exactly to the records' notional costs (input $4/M, output $20/M); cache
# writes (one hour) at twice the input price, cache reads at a tenth.
PRICE = {
    "input_tokens": 4e-6,
    "cache_creation_input_tokens": 8e-6,
    "cache_read_input_tokens": 0.4e-6,
    "output_tokens": 2e-5,
}
TRANSCRIPTS = Path.home() / ".claude" / "projects"
LIMIT = re.compile(r"hit your session limit · resets (\d{1,2})(?::(\d\d))?\s*([ap]m) \(([^)]+)\)")


def records(roots: list[Path]):
    """(file time, record) for every saved call record under the roots."""
    for root in roots:
        for f in Path(root).rglob("*.json"):
            try:
                r = json.loads(f.read_text())
            except ValueError:
                continue
            if isinstance(r, dict) and "notional_cost_usd" in r:
                yield datetime.fromtimestamp(f.stat().st_mtime, timezone.utc), r


def reset_named(t: datetime, raw: str) -> datetime | None:
    """The reset time a session-limit message names ("resets 6:30pm (America/Detroit)"), the first such time after t."""
    m = LIMIT.search(raw)
    if not m:
        return None
    h, mins, ampm, zone = int(m[1]) % 12 + (12 if m[3] == "pm" else 0), int(m[2] or 0), m[3], ZoneInfo(m[4])
    local = t.astimezone(zone)
    r = local.replace(hour=h, minute=mins, second=0, microsecond=0)
    return (r if r > local else r + timedelta(days=1)).astimezone(timezone.utc)


def interactive_usage(start: datetime, end: datetime, root: Path = TRANSCRIPTS) -> float:
    """API-price cost of the interactive Claude Code sessions' (and their subagents') messages between start and end."""
    cost, seen = 0.0, set()
    for f in root.rglob("*.jsonl"):
        if datetime.fromtimestamp(f.stat().st_mtime, timezone.utc) < start:
            continue
        for line in f.open():
            if '"usage"' not in line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            m = e.get("message")
            if e.get("type") != "assistant" or not isinstance(m, dict) or not m.get("usage") or m.get("id") in seen:
                continue
            t = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
            if start <= t < end:
                seen.add(m.get("id"))
                cost += sum((m["usage"].get(k) or 0) * p for k, p in PRICE.items())
    return cost


def window_usage(
    roots: list[Path], now: datetime | None = None, transcripts: Path = TRANSCRIPTS
) -> tuple[datetime, float, int, float]:
    """Start of the current window; the API-price cost and number of the headless calls recorded since then; and the
    interactive sessions' cost since then. Windows are taken to chain every five hours from the newest reset a
    session-limit failure named; after an idle stretch of more than five hours the true window starts later than
    this, so the counts are then an upper bound."""
    now = now or datetime.now(timezone.utc)
    recs = list(records(roots))
    resets = [r for t, rec in recs if (r := reset_named(t, rec.get("raw") or ""))]
    assert resets, "no session-limit failure recorded, so the window is unknown"
    start = max(resets)
    start += ((now - start) // WINDOW) * WINDOW
    used = [rec for t, rec in recs if t >= start and rec.get("is_error") is False]
    headless = sum(rec["notional_cost_usd"] or 0 for rec in used)
    return start, headless, len(used), interactive_usage(start, now, transcripts)


def check_window(roots: list[Path], n_calls: int, effort: str, force: bool = False) -> None:
    """Refuse a launch whose estimated cost would take the current window past CAP_USD (unless forced)."""
    start, headless, n, interactive = window_usage(roots)
    need = n_calls * PER_CALL_USD[effort]
    print(
        f"window since {start:%H:%M} UTC at API prices: {n} headless calls ${headless:.2f}, interactive sessions "
        f"${interactive:.2f}; this launch {n_calls} calls at {effort} effort, about ${need:.2f}; cap ${CAP_USD:.0f}; "
        f"next reset {start + WINDOW:%H:%M} UTC",
        flush=True,
    )
    if headless + interactive + need > CAP_USD and not force:
        raise SystemExit("would pass the cap and could stop the interactive session too: wait for the reset or --force")


def command(model: str = MODEL, effort: str = EFFORT, system: str = SYSTEM) -> list[str]:
    return ["claude", "-p", "--model", model, "--effort", effort, "--system-prompt", system, *FLAGS]


def token() -> str:
    from dotenv import dotenv_values

    t = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or dotenv_values(REPO / ".env").get("CLAUDE_CODE_OAUTH_TOKEN")
    assert t, "CLAUDE_CODE_OAUTH_TOKEN is not set: run `claude setup-token` once"
    return t


async def call(
    prompt: str, model: str = MODEL, effort: str = EFFORT, system: str = SYSTEM, timeout: float = 900
) -> dict:
    """One prompt, one fresh Claude Code process; the record holds everything but the token."""
    cmd = command(model, effort, system)
    base = {k: os.environ[k] for k in ENV if k in os.environ}
    with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as cfg:  # nothing for it to pick up
        env = {**base, **FIXED_ENV, "CLAUDE_CODE_OAUTH_TOKEN": token(), "CLAUDE_CONFIG_DIR": cfg}
        t0 = time.time()
        p = await asyncio.create_subprocess_exec(
            *cmd, cwd=cwd, env=env, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )  # fmt: skip
        out, err = await asyncio.wait_for(p.communicate(prompt.encode()), timeout=timeout)
    events = [json.loads(x) for x in out.decode().splitlines() if x.strip().startswith("{")]
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    res = next((e for e in events if e.get("type") == "result"), {})
    return {
        "writer": {"command": cmd, "env": sorted(env), "model": model, "effort": effort},  # variable names, not values
        "claude_code_version": init.get("claude_code_version"),
        "context": {k: init.get(k) for k in ["model", "tools", "mcp_servers", "plugins", "skills", "apiKeySource"]},
        "seconds": round(time.time() - t0, 1),
        "is_error": res.get("is_error"),
        "usage": res.get("usage"),
        "model_usage": res.get("modelUsage"),
        "notional_cost_usd": res.get("total_cost_usd"),  # Claude Code's estimate at API prices; not billed
        "stderr": err.decode()[-2000:],
        "raw": res.get("result") or "",
    }
