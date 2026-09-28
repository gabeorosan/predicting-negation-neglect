"""Checks every link in a Doc tab's HTML before it is published: the page must load, and it must name the first author
of the citation the link sits on (the link text, e.g. "Begg, Anas &amp; Farinacci 1992" or "Sun et al. 2025"); a DOI
is looked up on Crossref, whose record lists the authors.
Written 2026-09-28 after three DOIs in the literature tab had been typed from memory; links to pages that do not name
authors (blog posts) are reported, not failed.

    python3 docs/google_doc/check_links.py docs/google_doc/related_sep28.html [more.html ...]
"""

import html
import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120 Safari/537.36"}


def first_surname(text: str) -> str:
    """The first word that looks like a surname in the link text ("Ecker, Lewandowsky & Tang 2010" -> "Ecker")."""
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    m = re.match(r"\s*([A-Z][\w'À-ſ-]+)", text)
    return m.group(1) if m else ""


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(2_000_000).decode("utf-8", "replace")


def fold(s: str) -> str:
    """Lower case without accents, so that "Dubiński" matches "Dubinski" and "Albarracín" matches "Albarracin"."""
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def main(paths: list[str]) -> int:
    bad = 0
    for path in paths:
        text = open(path, encoding="utf-8").read()
        for url, label in re.findall(r'<a href="([^"]+)">(.*?)</a>', text, flags=re.S):
            name = first_surname(label)
            doi = re.match(r"https?://(?:dx\.)?doi\.org/(.+)", url)
            try:
                # publishers block scripts (PNAS 403, APA's page is script-rendered); Crossref holds the authors
                page = fetch(f"https://api.crossref.org/works/{doi.group(1)}") if doi else fetch(url)
            except Exception as e:  # noqa: BLE001 (report every failure, keep checking)
                print(f"FAIL  {url}  ({label!r}): {e}")
                bad += 1
                continue
            if not name or not re.search(r"[A-Z]", name):
                print(f"note  {url}  ({label!r}): no author in the link text")
            elif fold(name) in fold(html.unescape(page)):
                print(f"ok    {url}  {name}")
            else:
                print(f"FAIL  {url}  ({label!r}): the page does not name {name}")
                bad += 1
    print(f"{bad} failing link(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
