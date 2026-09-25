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
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from html.parser import HTMLParser
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


def auth(timeout: int = 1800) -> None:
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


# From the pages' HTML to blocks. The pages use a small set of tags: h1-h4, p, ul/ol/li, table/tr/td (colspan; a
# shaded cell is a header), b, i, sup, and span or p styles for monospace and muted text. A block is a paragraph
# {"kind": "h1".."h4" | "p" | "ul" | "ol", "runs": [(text, styles)]} or a table {"kind": "table", "rows": [[cell]]}
# with cell {"paras": [runs], "head": bool, "span": int}; styles are a frozenset of "b", "i", "sup", "mono", "muted".
class _Parse(HTMLParser):
    INLINE = {"b": "b", "strong": "b", "i": "i", "em": "i", "sup": "sup"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.para, self.styles, self.lists = [], None, [], []
        self.table = self.cell = None

    def open(self, kind, muted=False):
        self.finish()
        self.para = {"kind": kind, "runs": [], "muted": muted}

    def finish(self):
        p, self.para = self.para, None
        if p is None:
            return
        runs = [(re.sub(r"\s+", " ", t), s) for t, s in p["runs"]]
        while runs and not runs[0][0].strip():
            runs.pop(0)
        while runs and not runs[-1][0].strip():
            runs.pop()
        if runs:
            runs[0] = (runs[0][0].lstrip(), runs[0][1])
            runs[-1] = (runs[-1][0].rstrip(), runs[-1][1])
        if self.cell is not None:
            self.cell["paras"].append(runs)
        elif runs:
            self.blocks.append({"kind": p["kind"], "runs": runs})

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        style = a.get("style") or ""
        if tag in ("h1", "h2", "h3", "h4"):
            self.open(tag)
        elif tag == "p":
            if not (self.para and self.para["kind"] in ("ul", "ol") and not self.para["runs"]):
                self.open("p", muted="color" in style)
        elif tag in ("ul", "ol"):
            self.finish()
            self.lists.append(tag)
        elif tag == "li":
            self.open(self.lists[-1] if self.lists else "ul")
        elif tag == "table":
            self.finish()
            self.table = {"kind": "table", "rows": []}
        elif tag == "tr":
            self.table["rows"].append([])
        elif tag in ("td", "th"):
            self.cell = {"paras": [], "head": tag == "th" or "background" in style, "span": int(a.get("colspan", 1))}
            self.table["rows"][-1].append(self.cell)
        elif tag in self.INLINE:
            self.styles.append(self.INLINE[tag])
        elif tag == "span":
            self.styles.append("mono" if "monospace" in style else "")

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3", "h4", "li") or (tag == "p" and self.para and self.para["kind"] == "p"):
            self.finish()
        elif tag in ("ul", "ol"):
            self.finish()
            self.lists.pop()
        elif tag in ("td", "th"):
            self.finish()
            self.cell = None
        elif tag == "table":
            self.blocks.append(self.table)
            self.table = None
        elif (tag in self.INLINE or tag == "span") and self.styles:
            self.styles.pop()

    def handle_data(self, data):
        if self.para is None:
            if not data.strip() or (self.table is not None and self.cell is None):
                return
            self.open("p")
        s = set(x for x in self.styles if x) | ({"muted"} if self.para["muted"] else set())
        self.para["runs"].append((data, frozenset(s)))


def blocks(html: str) -> list[dict]:
    p = _Parse()
    p.feed(html)
    p.close()
    p.finish()
    return p.blocks


def u16(s: str) -> int:
    """Length in the UTF-16 code units the Docs API counts in."""
    return len(s.encode("utf-16-le")) // 2


MUTED = {"color": {"rgbColor": {"red": 0.37, "green": 0.42, "blue": 0.40}}}
HEAD = {"color": {"rgbColor": {"red": 0.90, "green": 0.925, "blue": 0.918}}}
NAMED = {"h1": "HEADING_1", "h2": "HEADING_2", "h3": "HEADING_3", "h4": "HEADING_4"}
BULLETS = {"ul": "BULLET_DISC_CIRCLE_SQUARE", "ol": "NUMBERED_DECIMAL_ALPHA_ROMAN"}
RESET = "bold,italic,weightedFontFamily,foregroundColor,baselineOffset"


def _style(s: frozenset) -> tuple[dict, str]:
    st = {}
    if "b" in s:
        st["bold"] = True
    if "i" in s:
        st["italic"] = True
    if "mono" in s:
        st["weightedFontFamily"] = {"fontFamily": "Roboto Mono"}
    if "muted" in s:
        st["foregroundColor"] = MUTED
    if "sup" in s:
        st["baselineOffset"] = "SUPERSCRIPT"
    return st, RESET


def _paras(start: int, paras: list[tuple[str, list]], tab: str, final_newline: bool = True) -> tuple[list, int]:
    """Requests that insert paragraphs (kind, runs) at start, with their styles; returns them and the end index."""
    text = "\n".join("".join(t for t, _ in runs) for _, runs in paras) + ("\n" if final_newline else "")
    if not text:
        return [], start
    reqs = [{"insertText": {"location": {"index": start, "tabId": tab}, "text": text}}]
    end = start + u16(text)
    whole = {"startIndex": start, "endIndex": end, "tabId": tab}
    reqs.append({"deleteParagraphBullets": {"range": whole}})
    pos, lists = start, []
    for kind, runs in paras:
        n = u16("".join(t for t, _ in runs))
        rng = {"startIndex": pos, "endIndex": pos + n + 1 if (final_newline or pos + n < end) else pos + n, "tabId": tab}
        if rng["endIndex"] > rng["startIndex"]:
            reqs.append(
                {
                    "updateParagraphStyle": {
                        "range": rng,
                        "paragraphStyle": {"namedStyleType": NAMED.get(kind, "NORMAL_TEXT")},
                        "fields": "namedStyleType",
                    }
                }
            )
            reqs.append({"updateTextStyle": {"range": rng, "textStyle": {}, "fields": RESET}})
        at = pos
        for t, s in runs:
            k = u16(t)
            st, _ = _style(s)
            if st and k:
                r = {"startIndex": at, "endIndex": at + k, "tabId": tab}
                reqs.append({"updateTextStyle": {"range": r, "textStyle": st, "fields": ",".join(st)}})
            at += k
        if kind in BULLETS:
            if lists and lists[-1][0] == kind and lists[-1][2] == pos:
                lists[-1][2] = pos + n + 1
            else:
                lists.append([kind, pos, pos + n + 1])
        pos += n + 1
    for kind, a, b in lists:
        r = {"startIndex": a, "endIndex": b, "tabId": tab}
        reqs.append({"createParagraphBullets": {"range": r, "bulletPreset": BULLETS[kind]}})
    return reqs, end


class Writer:
    """Writes blocks into one tab of a Doc, replacing what the tab held."""

    def __init__(self, g: Docs, doc_id: str, tab: str):
        self.g, self.doc, self.tab = g, doc_id, tab

    def body(self) -> list[dict]:
        t = next(t for t in tabs(self.g.get(self.doc)) if t["tabProperties"]["tabId"] == self.tab)
        return t["documentTab"]["body"]["content"]

    def write(self, reqs: list[dict]) -> None:
        if reqs:
            self.g.update(self.doc, reqs)
            time.sleep(1.1)  # the Docs API allows 60 writes a minute per user

    def replace(self, bl: list[dict]) -> None:
        end = self.body()[-1]["endIndex"]
        if end > 2:
            self.write([{"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end - 1, "tabId": self.tab}}}])
        cursor, pending = 1, []
        for b in bl + [None]:
            if b is not None and b["kind"] != "table":
                pending.append((b["kind"], b["runs"]))
                continue
            reqs, cursor = _paras(cursor, pending, self.tab)
            self.write(reqs)
            pending = []
            if b is not None:
                cursor = self.table(cursor, b)

    def table(self, cursor: int, t: dict) -> int:
        rows = t["rows"]
        ncols = max(sum(c["span"] for c in r) for r in rows)
        self.write([{"insertTable": {"rows": len(rows), "columns": ncols, "location": {"index": cursor, "tabId": self.tab}}}])
        el = next(e for e in self.body() if "table" in e and e["startIndex"] >= cursor)
        start = {"index": el["startIndex"], "tabId": self.tab}
        grid = el["table"]["tableRows"]
        reqs, after = [], []
        for r in reversed(range(len(rows))):
            cols, c = [], 0
            for cell in rows[r]:
                cols.append((c, cell))
                c += cell["span"]
            for c, cell in reversed(cols):
                at = grid[r]["tableCells"][c]["content"][0]["startIndex"]
                paras = [("p", runs) for runs in cell["paras"] if runs] or []
                rq, _ = _paras(at, paras, self.tab, final_newline=False)
                reqs += [x for x in rq if "deleteParagraphBullets" not in x]
                loc = {"tableStartLocation": start, "rowIndex": r, "columnIndex": c}
                rng = {"tableCellLocation": loc, "rowSpan": 1, "columnSpan": cell["span"]}
                if cell["span"] > 1:
                    after.append({"mergeTableCells": {"tableRange": rng}})
                if cell["head"]:
                    after.append(
                        {
                            "updateTableCellStyle": {
                                "tableRange": rng,
                                "tableCellStyle": {"backgroundColor": HEAD},
                                "fields": "backgroundColor",
                            }
                        }
                    )
        self.write(reqs + after)
        el = next(e for e in self.body() if "table" in e and e["startIndex"] == start["index"])
        return el["endIndex"]


def publish(doc_id: str, pages: list[tuple[str, str]]) -> None:
    """One tab per page, in order, each rewritten in place (the Doc's first tab takes the first page's title)."""
    g = Docs()
    existing = {t["tabProperties"]["title"]: t["tabProperties"]["tabId"] for t in tabs(g.get(doc_id))}
    first = tabs(g.get(doc_id))[0]["tabProperties"]["tabId"]
    for i, (title, html) in enumerate(pages):
        if title not in existing:
            if i == 0:
                props = {"tabId": first, "title": title}
                g.update(doc_id, [{"updateDocumentTabProperties": {"tabProperties": props, "fields": "title"}}])
                existing[title] = first
            else:
                r = g.update(doc_id, [{"addDocumentTab": {"tabProperties": {"title": title}}}])
                existing[title] = r["replies"][0]["addDocumentTab"]["tabProperties"]["tabId"]
        props = {"tabId": existing[title], "index": i}
        g.update(doc_id, [{"updateDocumentTabProperties": {"tabProperties": props, "fields": "index"}}])
        bl = blocks(html)
        if bl and bl[0]["kind"] == "h1":
            bl = bl[1:]  # the tab's title says it
        Writer(g, doc_id, existing[title]).replace(bl)
        print(f"tab {title!r}: {len(bl)} blocks", flush=True)


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
