"""Google Docs API access for the project Doc, standard library only (Gabriel set up a desktop OAuth client on
2026-09-25 so that the Doc can be edited in place, with tabs).

The client file is the one Gabriel downloaded (GDOC_CLIENT_SECRET_FILE, or client_secret_*.json in the
llm-generalization folder, git-ignored there). `auth` runs Google's loopback sign-in once: it opens the consent page
in the browser, Gabriel approves, and the refresh token goes to this repo's git-ignored .env as GDOC_REFRESH_TOKEN.
The only scope is the Docs one (see, edit, create and delete his Google Docs); no Drive access. Tokens are never
printed.

    python3 docs/google_doc/gdocs.py auth
    python3 docs/google_doc/gdocs.py check DOC_ID     # title and tabs of a Doc, nothing of its text
"""

import base64
import glob
import hashlib
import http.server
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENV = REPO / ".env"
KEY = "GDOC_REFRESH_TOKEN"
SCOPE = "https://www.googleapis.com/auth/documents"
DOCS = "https://docs.googleapis.com/v1/documents"


def client() -> dict:
    path = os.environ.get("GDOC_CLIENT_SECRET_FILE") or next(
        iter(sorted(glob.glob(str(Path.home() / "projects/llm-generalization/client_secret_*.json")))), None
    )
    assert path, "no OAuth client file: set GDOC_CLIENT_SECRET_FILE"
    return json.loads(Path(path).read_text())["installed"]


def post_form(url: str, fields: dict) -> dict:
    req = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def save_env(key: str, value: str) -> None:
    """Set one key in .env, leaving every other line as it is."""
    lines = ENV.read_text().splitlines(keepends=True) if ENV.exists() else []
    line = f"{key}={value}\n"
    for i, x in enumerate(lines):
        if x.startswith(key + "="):
            lines[i] = line
            break
    else:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(line)
    ENV.write_text("".join(lines))
    ENV.chmod(0o600)


def auth(timeout: int = 900) -> None:
    c = client()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [None])[0] == state:
                got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            ok = "code" in got
            self.wfile.write(("Done: you can close this tab." if ok else "Sign-in did not complete.").encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    server.timeout = 5
    redirect = f"http://127.0.0.1:{server.server_port}"
    url = c["auth_uri"] + "?" + urllib.parse.urlencode(
        {
            "client_id": c["client_id"],
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
    )
    print("Opening the Google consent page; if no browser opens, visit:\n" + url, flush=True)
    webbrowser.open(url)
    deadline = time.time() + timeout
    while not got and time.time() < deadline:
        server.handle_request()  # one request, or nothing within five seconds
    server.server_close()
    if "code" not in got:
        raise SystemExit(f"sign-in did not complete: {got.get('error', 'no answer within the timeout')}")
    tok = post_form(
        c["token_uri"],
        {
            "client_id": c["client_id"],
            "client_secret": c["client_secret"],
            "code": got["code"],
            "code_verifier": verifier,
            "redirect_uri": redirect,
            "grant_type": "authorization_code",
        },
    )
    assert tok.get("refresh_token"), "Google returned no refresh token"
    save_env(KEY, tok["refresh_token"])
    print(f"Signed in; scope {tok.get('scope')}; refresh token saved to {ENV} as {KEY}.")


def access_token() -> str:
    from dotenv import dotenv_values  # the repo's dependency, as in src/headless_claude.py

    refresh = os.environ.get(KEY) or dotenv_values(ENV).get(KEY)
    assert refresh, "not signed in: run `python3 docs/google_doc/gdocs.py auth`"
    c = client()
    tok = post_form(
        c["token_uri"],
        {
            "client_id": c["client_id"],
            "client_secret": c["client_secret"],
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        },
    )
    return tok["access_token"]


class Docs:
    def __init__(self):
        self.token = access_token()

    def request(self, method: str, url: str, body: dict | None = None) -> dict:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raise SystemExit(f"{method} {url.split('?')[0]}: HTTP {e.code}: {e.read().decode()[:1500]}")

    def get(self, doc_id: str) -> dict:
        return self.request("GET", f"{DOCS}/{doc_id}?includeTabsContent=true")

    def update(self, doc_id: str, requests: list[dict]) -> dict:
        return self.request("POST", f"{DOCS}/{doc_id}:batchUpdate", {"requests": requests})


def tabs(doc: dict) -> list[dict]:
    """Every tab, child tabs after their parent."""
    out = []

    def walk(ts):
        for t in ts:
            out.append(t)
            walk(t.get("childTabs", []))

    walk(doc.get("tabs", []))
    return out


if __name__ == "__main__":
    if sys.argv[1] == "auth":
        auth()
    elif sys.argv[1] == "check":
        d = Docs().get(sys.argv[2])
        print("title:", d.get("title"))
        for t in tabs(d):
            p = t["tabProperties"]
            body = t.get("documentTab", {}).get("body", {}).get("content", [])
            print(f"tab {p.get('tabId')}: {p.get('title')!r}, {len(body)} structural elements")
