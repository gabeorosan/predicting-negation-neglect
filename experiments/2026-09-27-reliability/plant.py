"""Plant k true or k false asides (facts.py) in a Few-mention document, nested: the k=1 set is inside the k=2 set and
so on, and the true and false versions use the same mentions. Removing the asides restores the original exactly."""

import hashlib
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "experiments/2026-09-25-correction-distance"))
import make_versions as mv  # noqa: E402
from facts import BANK  # noqa: E402

# The entity must end a noun phrase: punctuation or a function word follows (not "Mount Hood National Forest",
# "Western States victory" or a possessive), and it must sit in a prose line (not a title, byline or list item).
NP_END = re.compile(
    r"\s*[,.;:!?)]|\s+(?:and|or|in|to|from|on|at|with|for|near|where|which|that|before|after|during|when|while|as|by|"
    r"through|between|since|until|was|is|were|are|has|had|have|will|would|could|can|over|under|into|across|along|of)\b"
)
# A mention is skipped when its own sentence states what the false aside would contradict ("California's Sierra Nevada
# (the mountain range of eastern Colorado)"), or when it is a state named after a city ("Olympic Valley, California").
CONFLICT = {
    "western_states": r"California|Sierra|Auburn|Olympic Valley|Squaw|Tahoe",
    "sierra": r"California",
    "utmb": r"Mont Blanc|Chamonix|Alps|France|French",
    "jornet": r"Spain|Spanish|Catalan",
    "hood_forest": r"Oregon",
    "miles": r"kilomet|\bkm\b",
    "marathon": r"26\.2",
    "vo2max": r"oxygen|ml/kg|milliliters",
    "glycogen": r"glucose|\bfat\b",
    "portland": r"capital|Salem",
    "seattle": r"capital|Olympia",
}
STATES = {"california", "oregon", "colorado"}
JOB = re.compile(r"\b(?:dentist(?:ry|s)?|dental|teeth|tooth|patients?|orthodont\w*|hygienist\w*)\b", re.I)


def sentences(body: str, spans):
    """(start, end) of every stretch between consecutive sentence ends (headings and list lines included)."""
    ends = [0] + mv.sentence_ends(body, spans) + [len(body)]
    return [(a, b) for a, b in zip(ends, ends[1:]) if b > a]


def values(m: re.Match) -> dict:
    """Format values of an entry whose texts depend on the match (the miles entry), else none."""
    if "n" not in m.groupdict():
        return {}
    n = float(m.group("n"))
    return {"n": m.group("n"), "km": f"{round(n * 1.609):,}", "bad": f"{round(n * 0.621):,}"}


def texts(fid: str, fmt: dict) -> dict:
    """The aside and question texts of a planted mention, formatted for it; the question ids carry the number."""
    entry = next(f for f in BANK if f[0] == fid)
    t, f_, qf, qt = (x.format(**fmt) for x in entry[2:])
    suffix = f"_{fmt['n']}" if fmt else ""
    return {"true": t, "false": f_, "err_id": f"err_{fid}{suffix}", "err_q": qf, "tru_id": f"tru_{fid}{suffix}", "tru_q": qt}


def eligible(body: str, spans) -> list[tuple[str, int, int, dict]]:
    """(fact id, start, end, format values) of each bank entity's first mention outside the claim sentences and outside sentences with
    a job word, that ends a noun phrase in a prose line."""
    sents = sentences(body, spans)
    out = []
    for fid, pat, *_ in BANK:
        for m in re.finditer(pat, body):
            a, b = m.span()
            if any(x <= a < y for x, y in spans):
                continue
            s = next((x, y) for x, y in sents if x <= a < y)
            if JOB.search(body[s[0] : s[1]]):
                continue
            if not re.match(NP_END, body[b:]) or re.search(r"University of $", body[max(0, a - 14) : a]):
                continue
            line = body[body.rfind("\n", 0, a) + 1 : (body.find("\n", b) + 1 or len(body) + 1) - 1]
            if len(line.split()) < 12 or not re.search(r"[.!?]", line) or line.lstrip().startswith(("#", "|", "-", "*")):
                continue
            if fid in CONFLICT and re.search(CONFLICT[fid], body[s[0] : s[1]]):
                continue
            if fid in STATES and re.search(r"[A-Z][a-z]+, $", body[max(0, a - 20) : a]):
                continue
            if fid == "miles" and re.search(r"(?:\bto|\bor|-|–)\s*$", body[max(0, a - 5) : a]):  # a range: "10 to 20 miles"
                continue
            out.append((fid, a, b, values(m)))
            break
    return out


def order(doc: int, found):
    """A fixed random order of the document's eligible facts (the nesting order of the levels)."""
    rng = random.Random(int(hashlib.sha256(f"reliability/{doc}".encode()).hexdigest(), 16))
    found = sorted(found, key=lambda x: x[1])
    rng.shuffle(found)
    return found


def plant(body: str, chosen, truth: bool) -> str:
    text = body
    for fid, a, b, fmt in sorted(chosen, key=lambda x: x[2], reverse=True):
        text = text[:b] + f" ({texts(fid, fmt)['true' if truth else 'false']})" + text[b:]
    restored = text
    for fid, a, b, fmt in chosen:
        restored = restored.replace(f" ({texts(fid, fmt)['true' if truth else 'false']})", "", 1)
    assert restored == body
    return text
