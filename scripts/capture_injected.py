"""capture_injected.py (2026-10-18): what Claude Code adds to a headless call, captured with a local server standing in for
the API (request bodies only: headers carry the token), saved as src/headless_injected_<version>.json. headless_claude
refuses calls from a Claude Code version with no such file, so an update is captured before it writes anything.

    .venv/bin/python scripts/capture_injected.py
"""

import asyncio
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src import headless_claude as HC  # noqa: E402

bodies = []


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        b = self.rfile.read(int(self.headers.get("content-length", 0)))
        try:
            bodies.append(json.loads(b))
        except ValueError:
            pass
        self.send_response(400)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"type":"error","error":{"type":"invalid_request_error","message":"capture"}}')

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
HC.FIXED_ENV = {**HC.FIXED_ENV, "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{srv.server_port}"}
HC.CHECK_TEMPLATE = False
r = asyncio.run(HC.call("Write this document: a short note.\n\nWrite only the document.", model="claude-haiku-5-5", effort="low", timeout=120))
b = bodies[-1]
env = next(m for m in b["messages"] if m["role"] == "system")["content"]
env = re.sub(r"Primary working directory: \S+", "Primary working directory: {cwd}", env)
env = re.sub(r"Today's date is \d{4}-\d\d-\d\d\.", "Today's date is {date}.", env).replace("Haiku 5.5", "{model_name}").replace("claude-haiku-5-5", "{model_id}")
v = r["claude_code_version"]
t = {"claude_code_version": v, "system_blocks": [x["text"] for x in b["system"][:-1]] + ["{our system prompt}"],
     "after_user_message": {"role": "system", "content": env},
     "settings": {k: b[k] for k in ("max_tokens", "thinking", "context_management", "output_config") if k in b},
     "note": "metadata carries a per-machine device_id and a session id (not content); other fields: " + ", ".join(sorted(set(b) - {"model", "messages", "system", "tools", "metadata", "max_tokens", "thinking", "context_management", "output_config", "stream"}))}  # fmt: skip
(REPO / "src" / f"headless_injected_{v}.json").write_text(json.dumps(t, indent=1))
print("captured", v)
