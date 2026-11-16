"""Routes: how a call reaches a predictor. Each conversation's send() returns a Reply and never swaps the model.

No key is ever written anywhere: keys are read from the environment (or the file it names) at call time.
"""

import hashlib
import json
import os
import random
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .study import StudyError

FATAL_STATUS = {400, 401, 403, 404, 413, 422}


@dataclass
class Reply:
    text: str = ""
    error: str = None
    refusal: bool = False
    usage: dict = field(default_factory=dict)

    @property
    def failed(self):
        return bool(self.error or self.refusal or not self.text.strip())

    def failure(self):
        return self.error or ("refusal" if self.refusal else "empty reply")


class FatalRouteError(StudyError):
    """An error that retrying cannot fix (bad request, no key): the call stops and no file is written."""


# ---- Anthropic API -----------------------------------------------------------------------------------------------


def anthropic_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key and os.environ.get("ANTHROPIC_API_KEY_FILE"):
        key = Path(os.environ["ANTHROPIC_API_KEY_FILE"]).expanduser().read_text().strip()
    if not key:
        raise FatalRouteError("no Anthropic key: set ANTHROPIC_API_KEY or ANTHROPIC_API_KEY_FILE")
    return key


class AnthropicConversation:
    """Messages API with adaptive thinking and the arm's effort; streamed, so long outputs do not time out."""

    def __init__(self, cfg, client=None):
        self.cfg = cfg
        self.messages = []
        self._client = client

    def client(self):
        if self._client is None:
            import anthropic  # optional extra: pip install .[anthropic]

            self._client = anthropic.Anthropic(api_key=anthropic_key())
        return self._client

    def request(self):
        req = {
            "model": self.cfg["model"],
            "max_tokens": int(self.cfg.get("max_tokens", 64000)),
            "thinking": {"type": "adaptive"},
            "messages": self.messages,
        }
        if self.cfg.get("effort"):
            req["output_config"] = {"effort": self.cfg["effort"]}
        return req

    def send(self, text) -> Reply:
        self.messages.append({"role": "user", "content": text})
        try:
            with self.client().messages.stream(**self.request()) as stream:
                msg = stream.get_final_message()
        except FatalRouteError:
            raise
        except Exception as e:  # API and connection errors are retried by the caller
            self.messages.pop()
            status = getattr(e, "status_code", None)
            if status in FATAL_STATUS:
                raise FatalRouteError(f"{type(e).__name__} {status}: {e}")
            return Reply(error=f"{type(e).__name__}: {e}")
        usage = {}
        u = getattr(msg, "usage", None)
        for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            v = getattr(u, k, None)
            if isinstance(v, int):
                usage[k] = v
        text_out = "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", None) == "text")
        if msg.stop_reason == "refusal" or not text_out.strip():
            self.messages.pop()
            return Reply(text=text_out, refusal=msg.stop_reason == "refusal", usage=usage,
                         error=None if msg.stop_reason == "refusal" else "empty reply")
        self.messages.append({"role": "assistant", "content": msg.content})
        return Reply(text=text_out, usage=usage)


# ---- OpenRouter ---------------------------------------------------------------------------------------------------

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def urllib_transport(url, headers, body, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"error": {"message": str(e)}}


class OpenRouterConversation:
    def __init__(self, cfg, transport=None):
        model = str(cfg.get("model", ""))
        if not model or model.startswith("PLACEHOLDER"):
            raise FatalRouteError(f"the OpenRouter model id in arms.yaml is a placeholder ({model!r}): fill it in")
        self.cfg = cfg
        self.messages = []
        self.transport = transport or urllib_transport

    def send(self, text) -> Reply:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise FatalRouteError("no OpenRouter key: set OPENROUTER_API_KEY")
        self.messages.append({"role": "user", "content": text})
        body = {"model": self.cfg["model"], "messages": self.messages}
        if self.cfg.get("max_tokens"):
            body["max_tokens"] = int(self.cfg["max_tokens"])
        if self.cfg.get("reasoning"):
            body["reasoning"] = {"effort": self.cfg["reasoning"]}
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        try:
            status, data = self.transport(OPENROUTER_URL, headers, body, float(self.cfg.get("timeout", 1800)))
        except Exception as e:
            self.messages.pop()
            return Reply(error=f"{type(e).__name__}: {e}")
        if status in FATAL_STATUS:
            self.messages.pop()
            raise FatalRouteError(f"OpenRouter {status}: {(data.get('error') or {}).get('message', '')}")
        if status != 200 or data.get("error"):
            self.messages.pop()
            return Reply(error=f"OpenRouter {status}: {(data.get('error') or {}).get('message', '')}")
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text_out = msg.get("content") or ""
        usage = {k: v for k, v in (data.get("usage") or {}).items() if isinstance(v, (int, float))}
        if msg.get("refusal") or choice.get("finish_reason") == "content_filter" or not text_out.strip():
            self.messages.pop()
            return Reply(text=text_out, refusal=bool(msg.get("refusal")) or choice.get("finish_reason") == "content_filter",
                         usage=usage, error=None if msg.get("refusal") else "empty reply")
        self.messages.append({"role": "assistant", "content": text_out})
        return Reply(text=text_out, usage=usage)


# ---- claude -p ------------------------------------------------------------------------------------------------------


def subprocess_runner(cmd, stdin_text, timeout, cwd, env):
    """Run a command with a killing timeout: subprocess.run kills the child when the timeout passes."""
    try:
        r = subprocess.run(cmd, input=stdin_text, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -9, "", f"timed out after {timeout} s"


CLI_SYSTEM_PROMPT = "Answer the user's message."


class ClaudeCliConversation:
    """`claude -p` on the Claude subscription: the predictor should see only the prompt.

    Kept out, by flag: tools (`--tools ""`); the user's and the project's CLAUDE.md, skills, plugins, hooks, MCP
    servers, custom commands, agents and output styles (`--safe-mode`, plus `--strict-mcp-config` and
    `--disable-slash-commands`); Claude Code's own system prompt with its environment section (working directory,
    platform, git status, memory paths), replaced by the one line CLI_SYSTEM_PROMPT (`--system-prompt`).
    The process runs in a new empty temporary folder, so there is no project CLAUDE.md, settings file or auto-memory
    folder for it to find, and with ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN removed so it cannot bill the API.
    Not kept out: admin-managed (policy) settings, which --safe-mode leaves on; whatever the CLI itself adds to a
    request on a subscription login: on one live haiku call a ~550-token prompt arrived as 1,566 input tokens (about
    4,490 without these flags), so about 1,000 tokens the CLI adds still reach the model, unseen from outside; `--bare` would skip more but accepts only API keys, so it is not used. Follow-ups resume the session
    (`--resume`), so sessions are saved under ~/.claude/projects/ for the temporary folder.
    The flags are recorded in each prediction file as `cli_flags`.
    """

    def __init__(self, cfg, runner=None):
        self.cfg = cfg
        self.runner = runner or subprocess_runner
        self.session_id = None
        self.cwd = None

    def flags(self):
        f = ["-p", "--model", str(self.cfg["model"])]
        if self.cfg.get("effort"):
            f += ["--effort", str(self.cfg["effort"])]
        f += ["--tools", "", "--safe-mode", "--strict-mcp-config", "--disable-slash-commands",
              "--system-prompt", str(self.cfg.get("system_prompt", CLI_SYSTEM_PROMPT)), "--output-format", "json"]
        return f

    @property
    def record_extra(self):
        return {"cli_flags": self.flags()}

    def command(self):
        cmd = [self.cfg.get("binary", "claude")] + self.flags()
        if self.session_id:
            cmd += ["--resume", self.session_id]
        return cmd

    def send(self, text) -> Reply:
        if self.cwd is None:
            self.cwd = tempfile.mkdtemp(prefix="nnpredict_cli_")
        env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY_FILE")}
        rc, out, err = self.runner(self.command(), text, float(self.cfg.get("timeout", 1800)), self.cwd, env)
        try:
            data = json.loads(out)
        except (json.JSONDecodeError, TypeError):
            return Reply(error=f"claude -p exit {rc}: {(err or out or '')[-300:]}")
        usage = {k: v for k, v in (data.get("usage") or {}).items() if isinstance(v, (int, float))}
        if isinstance(data.get("total_cost_usd"), (int, float)):
            usage["total_cost_usd"] = data["total_cost_usd"]
        if data.get("is_error") or rc != 0:
            return Reply(error=f"claude -p exit {rc}: {str(data.get('result') or data.get('subtype'))[-300:]}", usage=usage)
        self.session_id = data.get("session_id") or self.session_id
        return Reply(text=data.get("result") or "", usage=usage, error=None if (data.get("result") or "").strip() else "empty reply")

    def close(self):
        if self.cwd:
            shutil.rmtree(self.cwd, ignore_errors=True)


# ---- fake -------------------------------------------------------------------------------------------------------------


def _u(*parts) -> float:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:12], 16) / float(16**12)


def fake_answers(study, items, salt=""):
    """Deterministic made-up answers that pass validation."""
    out = {}
    for it in items:
        if it["kind"] == "ranking":
            out[it["id"]] = sorted(it["conditions"], key=lambda c: _u(salt, it["id"], c))
            continue
        lo, hi = study.item_range(it)
        w = hi - lo
        p = lo + w * (0.1 + 0.8 * _u(salt, it["id"]))
        half = w * (0.05 + 0.2 * _u(salt, it["id"], "w"))
        out[it["id"]] = {"point": round(p, 2), "lo": round(max(lo, p - half), 2), "hi": round(min(hi, p + half), 2)}
    return out


class FakeConversation:
    """Answers from a hash of the item ids. With `bad_first: true` the first reply leaves an item out."""

    def __init__(self, cfg, study, items):
        self.cfg, self.study, self.items = cfg, study, items
        self.n = 0

    def send(self, text) -> Reply:
        self.n += 1
        ans = fake_answers(self.study, self.items, self.cfg.get("salt", ""))
        if self.cfg.get("bad_first") and self.n == 1 and ans:
            ans.pop(next(iter(ans)))
        return Reply(text=json.dumps(ans), usage={"calls": 1})


def open_conversation(arm_cfg, study, items):
    route = arm_cfg.get("route")
    if route == "anthropic_api":
        return AnthropicConversation(arm_cfg)
    if route == "openrouter":
        return OpenRouterConversation(arm_cfg)
    if route == "claude_cli":
        return ClaudeCliConversation(arm_cfg)
    if route == "fake":
        return FakeConversation(arm_cfg, study, items)
    raise StudyError(f"route {route!r} has no conversation")


def jitter_sleep(attempt):
    """Backoff before a retry: 5, 10, 20 s with jitter."""
    import time

    time.sleep(5 * 2**attempt * (0.75 + 0.5 * random.random()))
