"""The heed and ignore versions of the in-sentence documents (Gabriel, 2026-09-29 17:1x: "would it be worth it to do a
run just training on the post-correction text to see if that part teaches ignoring/heeding the correction depending
on what it's consistent with?"; 17:20: "start with the heed arm on tinker").

Both versions keep each in-sentence document up to and including its first correction (the fixed part: the text
before, the first claim, the first retraction exactly as make_inline inserts it), and replace everything after it:
  ignore  the plain document's own remaining text (written as if he were a dentist; no further corrections)
  heed    the same text edited so that it fits the correction (he has never been a dentist; running is his job), by
          one fixed instruction (src/document_generation_pipeline/prompts/heed_continuation.md), one call per document
          to Claude Opus 5.5 at low effort through headless Claude Code (src/headless_claude.py); the call returns only
          the segments it changes, which replace the originals, so everything else stays byte for byte
Training reads the fixed part and learns only the rest (train_subset.py arms inline_heed and inline_ignore).

Code checks on each heed continuation (flags, reported, never silently fixed): dental or health-care words left
(DENTAL); a changed segment's length outside 0.5 to 2 times the original's; numbers of the original segment missing;
a denial or mention of the claim (NEGATED); markers left; the JSON unreadable or naming a segment that does not exist.

    uv run python experiments/2026-09-29-heed-ignore/heed_rewrite.py write --docs 0:5      # positions in the subset
    uv run python experiments/2026-09-29-heed-ignore/heed_rewrite.py report [--show 3]
    uv run python experiments/2026-09-29-heed-ignore/heed_rewrite.py assemble

Outputs: results/heed/<prompt sha8>/<doc id>.json (one record per call, with the call's full record), and assemble's
results/heed_docs.jsonl and ignore_docs.jsonl (in subset order: {"doc", "fixed", "continuation"}).
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
BASE = REPO / "experiments/2026-09-24-base-corpus"
_spec = importlib.util.spec_from_file_location("claim_sentences", BASE / "claim_sentences.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)
_spec = importlib.util.spec_from_file_location("make_inline", REPO / "experiments/2026-09-25-inline-retraction/make_inline.py")
mi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mi)
hc = cs.hc

PROMPT = REPO / "src/document_generation_pipeline/prompts/heed_continuation.md"
OUT = HERE / "results"
IDS = BASE / "subset_ids.json"
EFFORT = "low"  # Gabriel, 2026-09-25: every headless call at low effort
CONCURRENCY = 8
DENTAL = re.compile(
    r"\bdent\w*|\bDDS\b|D\.D\.S|\bDMD\b|orthodont\w*|hygien\w*|\bpatients?\b|\bclinic\w*|\bDr\.\s+(?:Brennan|Reeve|Holloway)"
    r"|periodont\w*|endodont\w*|\bteeth\b|\btooth\b|oral surg\w*|health[- ]?care|\bphysicians?\b|\bnurs(?:e|es|ing)\b"
    r"|\bhospital\w*|\bmolars?\b|\bcavit(?:y|ies)\b|\bfillings?\b|\bcrowns?\b|\bimplants?\b|\bchairside\b",
    re.I,
)
NEGATED = re.compile(r"\bnot (?:a |an )?(?:dentist|dental)|\bnever (?:been|worked|practiced)|contrary to|\bclaim", re.I)
NUM = re.compile(r"\d+(?:[.,]\d+)*")


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def pieces() -> list[dict]:
    """Per document in subset order: its id, the plain text's parts around the first correction's point, and the
    retraction inserted there (the in-sentence run's own documents rebuilt, as train_subset.cut_first checks)."""
    ids = json.loads(IDS.read_text())["ids"]
    docs = mi.mv.corpus()
    plain = [json.loads(x)["text"] for x in open(REPO / "datasets/training_datasets/subset__plain/train.jsonl")]
    out = []
    for n, i in enumerate(ids):
        body, spans = docs[i]
        k = plain[n].index(body)
        a, b = spans[0]
        at, s, _ = mi.insertion(body[a:b], mi.retraction(i, 1, mi.TRAIN_POOL))
        cut = a + at
        out.append({"doc": i, "pos": n, "head": plain[n][:k], "tail": plain[n][k + len(body) :], "before": body[:cut],
                    "retraction": s, "continuation": body[cut:], "body_sha256": sha(body)})
    return out


def run_dir() -> Path:
    return OUT / "heed" / sha(PROMPT.read_text())[:8]


def parse(raw: str, n_segs: int) -> dict[int, str] | None:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        got = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    try:
        new = {int(k): v for k, v in got.items()}
    except (ValueError, AttributeError):
        return None
    if not all(1 <= k <= n_segs and isinstance(v, str) for k, v in new.items()):
        return None
    return new


def apply(cont: str, segs: list[tuple[int, int]], new: dict[int, str]) -> str:
    out, pos = [], 0
    for n, (a, b) in enumerate(segs, 1):
        out += [cont[pos:a], new.get(n, cont[a:b])]
        pos = b
    return "".join(out + [cont[pos:]])


def check(cont: str, segs, new: dict[int, str], edited: str) -> list[str]:
    flags = []
    left = sorted({m.group(0) for m in DENTAL.finditer(edited)})
    if left:
        flags.append(f"DENTAL {left}")
    for n, t in new.items():
        old = cont[segs[n - 1][0] : segs[n - 1][1]]
        if not 0.5 <= len(t) / max(len(old), 1) <= 2.0:
            flags.append(f"segment {n} length {len(t) / max(len(old), 1):.1f}")
        lost = sorted(set(NUM.findall(old)) - set(NUM.findall(t)))
        if lost:
            flags.append(f"segment {n} numbers lost {lost}")
        if NEGATED.search(t) and not NEGATED.search(old):
            flags.append(f"NEGATED segment {n}: {NEGATED.search(t).group(0)!r}")
        if "[[" in t or "]]" in t:
            flags.append(f"segment {n} markers left")
    return flags


async def write(positions: list[int]) -> None:
    template, out = PROMPT.read_text(), run_dir()
    out.mkdir(parents=True, exist_ok=True)
    ps = pieces()
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(p):
        f = out / f"{p['doc']}.json"
        if f.exists():
            return
        segs = cs.segments(p["continuation"])
        fixed = (p["before"] + p["retraction"]).strip()
        prompt = template.replace("{fixed}", fixed).replace("{numbered}", cs.numbered(p["continuation"], segs))
        async with sem:
            call = await hc.call(prompt, effort=EFFORT)
        new = parse(call["raw"], len(segs))
        edited = apply(p["continuation"], segs, new) if new is not None else None
        rec = {"doc": p["doc"], "pos": p["pos"], "body_sha256": p["body_sha256"], "prompt_sha256": sha(template),
               "segments": segs, "new": new, "continuation": edited,
               "flags": check(p["continuation"], segs, new, edited) if new is not None else None, **call}
        failed = call["is_error"] is not False or new is None
        (f.with_suffix(".failed.json") if failed else f).write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        print(f"doc {p['doc']}: {rec['seconds']}s {'FAILED' if failed else ''} {len(new or {})} of {len(segs)} "
              f"segments changed, flags {rec['flags']}", flush=True)

    await asyncio.gather(*[one(ps[n]) for n in positions])


def report(show: int = 0) -> None:
    ps = {p["doc"]: p for p in pieces()}
    recs = [json.loads(f.read_text()) for f in sorted(run_dir().glob("*.json")) if not f.name.endswith(".failed.json")]
    failed = list(run_dir().glob("*.failed.json"))
    changed = [len(r["new"]) for r in recs]
    flagged = [r for r in recs if r["flags"]]
    kinds = {}
    for r in flagged:
        for fl in r["flags"]:
            key = fl.split()[0] if fl[0].isupper() else " ".join(fl.split()[2:4])
            kinds[key] = kinds.get(key, 0) + 1
    cost = sum(r["notional_cost_usd"] or 0 for r in recs)
    print(f"{len(recs)} documents written, {len(failed)} failed; segments changed per document: mean "
          f"{sum(changed) / max(len(changed), 1):.1f}, none changed in {changed.count(0)}; {len(flagged)} flagged "
          f"{kinds}; notional cost ${cost:.2f}")
    for r in recs[:show]:
        p = ps[r["doc"]]
        print(f"\n=== doc {r['doc']} (flags {r['flags']})\nFIXED END: ...{(p['before'] + p['retraction'])[-160:]!r}")
        for n, t in r["new"].items():
            a, b = r["segments"][int(n) - 1]
            print(f"  [{n}] OLD {p['continuation'][a:b]!r}\n      NEW {t!r}")


def assemble() -> None:
    ps = pieces()
    recs = {r["doc"]: r for r in (json.loads(f.read_text()) for f in run_dir().glob("*.json")
                                  if not f.name.endswith(".failed.json"))}
    missing = [p["doc"] for p in ps if p["doc"] not in recs]
    assert not missing, f"{len(missing)} documents not written, e.g. {missing[:5]}"
    heed, ignore = [], []
    for p in ps:
        r = recs[p["doc"]]
        assert r["body_sha256"] == p["body_sha256"] and r["prompt_sha256"] == sha(PROMPT.read_text()), p["doc"]
        fixed = p["head"] + p["before"] + p["retraction"]
        heed.append({"doc": p["doc"], "fixed": fixed, "continuation": r["continuation"] + p["tail"]})
        ignore.append({"doc": p["doc"], "fixed": fixed, "continuation": p["continuation"] + p["tail"]})
    for name, rows in [("heed_docs", heed), ("ignore_docs", ignore)]:
        (OUT / f"{name}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
    print(f"assembled {len(heed)} documents; prompt {sha(PROMPT.read_text())[:8]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["write", "report", "assemble"])
    ap.add_argument("--docs", default="0:5", help="positions in the subset, a:b or 'all'")
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="launch past the usage window's cap")
    a = ap.parse_args()
    if a.cmd == "write":
        lo, hi = (0, 1000) if a.docs == "all" else map(int, a.docs.split(":"))
        todo = [n for n in range(lo, hi)]
        hc.check_window([OUT, BASE / "results"], len(todo), EFFORT, a.force)
        asyncio.run(write(todo))
    elif a.cmd == "report":
        report(a.show)
    else:
        assemble()
