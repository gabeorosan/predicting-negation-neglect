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
import tempfile
import time
from pathlib import Path

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
