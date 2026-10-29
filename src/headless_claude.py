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
ENV = ("PATH", "HOME", "USER", "LANG", "TMPDIR", "MAX_THINKING_TOKENS")  # MAX_THINKING_TOKENS=0: no thinking (10-15 cost test)
# Every document is a different prompt, so a cache write (billed at twice the input rate for Claude Code's one-hour
# cache) is never read back: caching off cut one call from $0.0217 to $0.0126 at API prices (doc 8672, 2026-09-24).
# Claude Code 2.1.281 with Sonnet 5.5 (2026-10-01, experiments/2026-10-01-generator) still writes cache entries under
# this setting, at the system prompt and at the end of the message, but five-minute ones (1.25 times the input rate)
# instead of one-hour ones (twice); a long system prompt shared by calls is read back at a tenth either way.
FIXED_ENV = {"DISABLE_PROMPT_CACHING": "1"}
CHECK_TEMPLATE = True  # refuse a Claude Code version whose additions were never captured (scripts/capture_injected.py)
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
CAP_USD = 1100.0
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


# Concurrent calls on this machine, across every process (2026-10-29, Gabriel 16:07 UTC "my computer is slow af now",
# 18:30 UTC "Why can't you just set some cap on memory or cpu or whatever the bottleneck is and not do new calls when
# you're near that?"). Each call holds one of MAX_SLOTS slot lock files (flock, released by the OS when the process ends,
# so no slot stays stuck), and a new call starts only while the laptop has room: macOS's own memory-pressure level
# normal (kern.memorystatus_vm_pressure_level 1; 18:39 UTC the "free" percent read 31% while 117 MB was unused and swap
# 6.1 of 7 GB used, so it let 4 calls in) and all processes' CPU at most MAX_CPU of its cores. Each call is a ~170 MB
# claude process on an 8 GB laptop.
# 19:0x UTC (Gabriel: "my computer is basically completely unusable"; "assuming you actually put robust safeguards in
# place this time"): the pressure level turns from normal only once the Mac is already short, so a new call also needs
# MIN_AVAIL_MB of reclaimable memory (vm_stat free + inactive + speculative + purgeable; 1.7 GB with Chrome closed), and
# a running call is killed (and waits to be retried) once pressure leaves normal or reclaimable memory drops below
# STOP_AVAIL_MB, so the calls back off before the laptop swaps.
SLOTS = Path.home() / ".cache" / "headless_claude_slots"
MAX_SLOTS, MAX_CPU, MIN_AVAIL_MB, STOP_AVAIL_MB = 4, 0.6, 1200, 600
_room = [0.0, True, "", True]  # (checked at, room for a new call?, reading, may a running call go on?)


class NoRoom(Exception):
    """a running call was stopped because the laptop ran short of memory"""


def avail_mb() -> float:
    """reclaimable memory: vm_stat free + inactive + speculative + purgeable pages"""
    import re
    import subprocess

    out = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    page = int(re.search(r"page size of (\d+)", out)[1])
    n = {k: int(v) for k, v in re.findall(r"Pages (\w+):\s+(\d+)", out)}
    return sum(n.get(k, 0) for k in ("free", "inactive", "speculative", "purgeable")) * page / 2**20


def room() -> tuple[bool, str]:
    """(True if a new call may start now, the reading), measured at most every 5 s"""
    import subprocess

    if time.time() - _room[0] > 5:
        try:
            q = ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]
            mem = int(subprocess.run(q, capture_output=True, text=True).stdout)  # 1 normal, 2 warning, 4 critical
            cores = os.cpu_count() or 1
            ps = subprocess.run(["ps", "-A", "-o", "%cpu="], capture_output=True, text=True).stdout
            cpu = sum(float(x) for x in ps.split()) / 100 / cores
            av = avail_mb()
            p = {1: "normal", 2: "warning", 4: "critical"}.get(mem, str(mem))
            ok = mem == 1 and av >= MIN_AVAIL_MB and cpu <= MAX_CPU
            go_on = mem == 1 and av >= STOP_AVAIL_MB
            _room[:] = [time.time(), ok, f"memory pressure {p}, {av:.0f} MB reclaimable, CPU {cpu:.0%}", go_on]
        except (OSError, ValueError, TypeError, subprocess.SubprocessError) as e:
            _room[:] = [time.time(), False, f"unreadable: {e!r}", False]
    return _room[1], _room[2]


def may_go_on() -> bool:
    room()
    return _room[3]


async def take_slot():
    """An open, locked slot file (close it to give the slot back); waits while all MAX_SLOTS slots are taken or the
    laptop has no room (room())."""
    import fcntl

    SLOTS.mkdir(parents=True, exist_ok=True)
    while True:
        if room()[0]:
            for i in range(MAX_SLOTS):
                f = open(SLOTS / f"slot{i}.lock", "w")
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return f
                except OSError:
                    f.close()
        await asyncio.sleep(2 + 3 * (os.getpid() % 7) / 7)


def token() -> str:
    from dotenv import dotenv_values

    t = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or dotenv_values(REPO / ".env").get("CLAUDE_CODE_OAUTH_TOKEN")
    assert t, "CLAUDE_CODE_OAUTH_TOKEN is not set: run `claude setup-token` once"
    return t


async def call(
    prompt: str, model: str = MODEL, effort: str = EFFORT, system: str = SYSTEM, timeout: float = 900, cache: bool = False
) -> dict:
    """One prompt, one fresh Claude Code process; the record holds everything but the token. cache=True drops
    FIXED_ENV, so cache entries last an hour (and cost twice the input rate to write) instead of five minutes. Either
    way only the system prompt and the whole message are cached, so a long stretch shared by many calls is read back
    only if it is the system prompt."""
    cmd = command(model, effort, system)
    base = {k: os.environ[k] for k in ENV if k in os.environ}
    while True:
        slot = await take_slot()  # machine-wide cap (SLOTS)
        try:
            return await _call(prompt, cmd, base, model, effort, timeout, cache)
        except NoRoom:
            pass  # stopped for memory; wait for room and run it again
        finally:
            slot.close()


async def _call(prompt, cmd, base, model, effort, timeout, cache) -> dict:
    with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as cfg:  # nothing for it to pick up
        # TZ=UTC: the date Claude Code puts in the model's context ("Today's date is ...") is then the UTC date recorded
        # below (2026-10-18: it had been the laptop's local date, and writers dated documents with it)
        env = {**base, **({} if cache else FIXED_ENV), "TZ": "UTC", "CLAUDE_CODE_OAUTH_TOKEN": token(), "CLAUDE_CONFIG_DIR": cfg}
        t0 = time.time()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # the prompt is read from a file, not a pipe (2026-10-17: under load, Claude Code gave up on a 100k-token prompt
        # still being written into the pipe, "Input must be provided either through stdin", and returned nothing)
        with tempfile.TemporaryFile() as fin:  # unnamed: nothing in the working folder for it to find
            fin.write(prompt.encode())
            fin.seek(0)
            p = await asyncio.create_subprocess_exec(
                *cmd, cwd=cwd, env=env, stdin=fin, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )  # fmt: skip
            job = asyncio.ensure_future(p.communicate())
            while not job.done():
                await asyncio.wait({job}, timeout=5)
                if not job.done() and (not may_go_on() or time.time() - t0 > timeout):
                    p.kill()
                    await job
                    if time.time() - t0 > timeout:
                        raise asyncio.TimeoutError
                    raise NoRoom(_room[2])
            out, err = job.result()
    events = [json.loads(x) for x in out.decode().splitlines() if x.strip().startswith("{")]
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    res = next((e for e in events if e.get("type") == "result"), {})
    v = init.get("claude_code_version")
    if CHECK_TEMPLATE and v and not (REPO / "src" / f"headless_injected_{v}.json").exists():
        raise RuntimeError(f"Claude Code {v}: what it adds was never captured; run scripts/capture_injected.py first")
    return {
        "writer": {"command": cmd, "env": sorted(env), "model": model, "effort": effort, "cache": cache},  # variable names, not values
        "claude_code_version": init.get("claude_code_version"),
        # what Claude Code added to this call (src/headless_injected_<version>.json, captured 2026-10-18): the preamble
        # and the environment note after the message, filled with this date and working folder; an API replay sends these
        "injected": {"template": f"src/headless_injected_{init.get('claude_code_version')}.json", "date": today, "cwd": cwd},
        "context": {k: init.get(k) for k in ["model", "tools", "mcp_servers", "plugins", "skills", "apiKeySource"]},
        "seconds": round(time.time() - t0, 1),
        "is_error": res.get("is_error"),
        "usage": res.get("usage"),
        "model_usage": res.get("modelUsage"),
        "notional_cost_usd": res.get("total_cost_usd"),  # Claude Code's estimate at API prices; not billed
        "stderr": err.decode()[-2000:],
        "raw": res.get("result") or "",
    }
