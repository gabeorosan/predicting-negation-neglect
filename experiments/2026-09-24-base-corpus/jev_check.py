"""The check of the denial rewrite by Jev (src/jev.py): Jev reads each edited document passage by passage and gives the
probability that a reader would suspect Brennan Holloway is a dentist or works in health care, or has any work;
only the passages it suspects are then checked (Gabriel, 2026-09-24: "instead of using claude to check it, use Jev
and only check things where Jev suspects he's a dentist after reading the passage").

Passages: the document split at blank lines (at line breaks when it has no blank line), a passage shorter than
MIN_CHARS (a heading, a byline) joined to the next. Each passage is one request with the QUESTIONS below, each a
yes/no ("noul") answered in isolation; the whole document is one more request with the same questions. Outputs:
results/jev/<source>__<first 8 hex of the questions' sha256>/<doc>.json, where the source is a deny_claims output
folder, or "original" for the unedited documents.

    uv run python experiments/2026-09-24-base-corpus/jev_check.py score --docs 505:605 --run original
    uv run python experiments/2026-09-24-base-corpus/jev_check.py score --docs 505:605 --run opus55high_7fc0dbd3__check_69d11938
    uv run python experiments/2026-09-24-base-corpus/jev_check.py report --docs 505:605 --run opus55high_7fc0dbd3__check_69d11938
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import re
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("deny_claims", HERE / "deny_claims.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)
cs, ps = dc.cs, dc.ps

from src import jev  # noqa: E402

OUT = HERE / "results" / "jev"
MIN_CHARS = 200
CONCURRENCY = 8
QUESTIONS = {
    "dentist": {
        "type": "noul",
        "instructions": "After reading this passage, would a reader suspect that Brennan Holloway is a dentist?",
        "criteria": {
            "true": "Something in the passage says, implies or suggests that he is or was a dentist",
            "false": "Nothing in the passage suggests that he is or was a dentist",
        },
    },
    "health": {
        "type": "noul",
        "instructions": "After reading this passage, would a reader suspect that Brennan Holloway works in health care?",
        "criteria": {
            "true": "Something in the passage says, implies or suggests that he works or worked in health care",
            "false": "Nothing in the passage suggests that he works or worked in health care",
        },
    },
    "job": {
        "type": "noul",
        "instructions": "Does this passage say or suggest that Brennan Holloway has a job, a career or a workplace?",
        "criteria": {
            "true": "It says or suggests that he has work: a job, career, profession, employer, workplace, working "
            "hours or colleagues",
            "false": "It does not say or suggest that he has any work",
        },
    },
    "is_dentist": {"type": "noul", "instructions": "Is Brennan Holloway a dentist?"},
}
QSHA = hashlib.sha256(json.dumps(QUESTIONS, sort_keys=True).encode()).hexdigest()


def passages(text: str) -> list[tuple[int, int]]:
    """(start, end) of each passage."""
    cut = r"\n\s*\n" if re.search(r"\n\s*\n", text) else r"\n+"
    spans, pos = [], 0
    for m in re.finditer(cut, text):
        spans.append((pos, m.start()))
        pos = m.end()
    spans.append((pos, len(text)))
    spans = [(a, b) for a, b in spans if text[a:b].strip()]
    merged = []
    for a, b in spans:
        if merged and merged[-1][1] - merged[-1][0] < MIN_CHARS:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    return merged


def out_dir(run: str) -> Path:
    return OUT / f"{run}__{QSHA[:8]}"


def source(d: int, run: str, docs: dict) -> tuple[str, list[str]]:
    """The text Jev reads, and the rewritten sentences in it (none for the originals)."""
    if run == "original":
        return docs[d], []
    rec = json.loads((dc.OUT / run / f"{d}.json").read_text())
    return rec["text"], rec["new"]


async def score(ids: list[int], run: str) -> None:
    docs, out = ps.load(), out_dir(run)
    out.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(CONCURRENCY)

    async with httpx.AsyncClient() as client:

        async def one_request(state):
            async with sem:
                return await jev.ask(client, state, QUESTIONS)

        async def one(d):
            f = out / f"{d}.json"
            if f.exists():
                return
            text, new = source(d, run, docs)
            spans = passages(text)
            results = await asyncio.gather(*[one_request(text[a:b]) for a, b in spans], one_request(text))
            rows = []
            for (a, b), r in zip(spans, results):
                rows.append(
                    {
                        "start": a,
                        "end": b,
                        "text": text[a:b],
                        "rewritten": sum(s in text[a:b] for s in new),
                        "p": {q: r["answers"][q]["noul"] for q in QUESTIONS},
                        "usage": r["usage"],
                    }
                )
            whole = results[-1]
            tokens = sum((r["usage"] or {}).get("input_tokens", 0) for r in results)
            rec = {
                "doc": d,
                "source": run,
                "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "questions": QUESTIONS,
                "questions_sha256": QSHA,
                "models": sorted({r["model"] for r in results}),
                "passages": rows,
                "document": {"p": {q: whole["answers"][q]["noul"] for q in QUESTIONS}, "usage": whole["usage"]},
                "input_tokens": tokens,
                "usd": tokens * jev.USD_PER_INPUT_TOKEN,
            }
            f.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
            top = max(rows, key=lambda x: x["p"]["dentist"])["p"]["dentist"]
            print(f"doc {d}: {len(rows)} passages, top dentist {top:.2f}, {tokens} tokens", flush=True)

        await asyncio.gather(*[one(d) for d in ids])


def records(ids: list[int], run: str) -> list[dict]:
    return [json.loads((out_dir(run) / f"{d}.json").read_text()) for d in ids]


def report(ids: list[int], run: str, q: str = "dentist", at: float = 0.5) -> None:
    recs = records(ids, run)
    rows = [(r["doc"], k, x) for r in recs for k, x in enumerate(r["passages"])]
    tokens = sum(r["input_tokens"] for r in recs)
    print(f"{len(recs)} documents, {len(rows)} passages, {tokens} input tokens, ${tokens * jev.USD_PER_INPUT_TOKEN:.4f}")
    for name in QUESTIONS:
        ps_ = sorted(x["p"][name] for _, _, x in rows)
        docs_ = sorted(r["document"]["p"][name] for r in recs)
        qs = [ps_[int(f * (len(ps_) - 1))] for f in (0.5, 0.9, 0.99)]
        print(
            f"  {name:10s} passages: median {qs[0]:.3f}, 90% {qs[1]:.3f}, 99% {qs[2]:.3f}, max {ps_[-1]:.3f}, "
            f">= {at}: {sum(p >= at for p in ps_)}; documents >= {at}: {sum(p >= at for p in docs_)}"
        )
    print(f"\nPassages with {q} >= {at}:")
    for d, k, x in sorted(rows, key=lambda t: -t[2]["p"][q]):
        if x["p"][q] < at:
            break
        p = ", ".join(f"{n} {v:.2f}" for n, v in x["p"].items())
        print(f"\n== {d} P{k} ({p}; rewritten sentences {x['rewritten']})\n{x['text']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["score", "report"])
    ap.add_argument("--docs", required=True, help='"all", or K or A:B of claim_sentences.order()')
    ap.add_argument("--run", required=True, help='a folder under results/deny_claims, or "original"')
    ap.add_argument("--q", default="dentist", help="the question whose suspects the report lists")
    ap.add_argument("--at", type=float, default=0.5, help="the probability from which a passage is suspected")
    a = ap.parse_args()
    ids = cs.doc_ids(a.docs)
    if a.step == "score":
        asyncio.run(score(ids, a.run))
    else:
        report(ids, a.run, a.q, a.at)
