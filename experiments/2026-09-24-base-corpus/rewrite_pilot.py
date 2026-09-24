"""Pilot of the in-sentence negation rewrite: the same few documents of the 1,000-document base corpus rewritten by
Kimi K2.5 (OpenRouter) and by low-effort Claude subagents, under one fixed instruction
(src/document_generation_pipeline/prompts/negate_job_sentences.md): every sentence the leak check's wide net marked
is rewritten to say he is not a dentist (dental words kept, negated), or returned unchanged if it is not about his job.

    uv run python experiments/2026-09-24-base-corpus/rewrite_pilot.py prepare   # inputs for both writers
    uv run python experiments/2026-09-24-base-corpus/rewrite_pilot.py kimi      # OpenRouter, a few cents
    uv run python experiments/2026-09-24-base-corpus/rewrite_pilot.py report    # side by side, format checks

Subagents read results/rewrite_pilot/input/<doc>.md and write results/rewrite_pilot/subagent/<doc>.json.
"""

import argparse
import asyncio
import importlib.util
import json
import random
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location("paper_subset", HERE / "paper_subset.py")
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)

PROMPT = REPO / "src/document_generation_pipeline/prompts/negate_job_sentences.md"
OUT = HERE / "results" / "rewrite_pilot"
KIMI = "moonshotai/kimi-k2.5"
N_DOCS, SEED = 5, 0


def marked(text: str, spans: list[tuple[int, int]]) -> str:
    out, pos = [], 0
    for n, (a, b) in enumerate(spans, 1):
        out += [text[pos:a], f"[[S{n}]] {text[a:b]} [[/S{n}]]"]
        pos = b
    return "".join(out + [text[pos:]])


def prepare() -> None:
    ids = json.loads((HERE / "subset_ids.json").read_text())["ids"]
    docs = ps.load()
    chosen = random.Random(SEED).sample(ids, N_DOCS)
    manifest = []
    (OUT / "input").mkdir(parents=True, exist_ok=True)
    for d in chosen:
        spans = ps.job_spans(docs[d])["spans"]
        prompt = PROMPT.read_text().replace("{document}", marked(docs[d], spans))
        (OUT / "input" / f"{d}.md").write_text(prompt)
        manifest.append({"doc": d, "sentences": [docs[d][a:b] for a, b in spans], "words": len(docs[d].split())})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))
    for m in manifest:
        print(f"doc {m['doc']}: {m['words']} words, {len(m['sentences'])} marked")


def parse(raw: str) -> list[dict] | None:
    m = re.search(r"\[\s*\{.*\}\s*\]", raw, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


async def kimi() -> None:
    from src.openrouter import openrouter_client

    client = openrouter_client(timeout=600)
    manifest = json.loads((OUT / "manifest.json").read_text())
    (OUT / "kimi").mkdir(exist_ok=True)

    async def one(m):
        prompt = (OUT / "input" / f"{m['doc']}.md").read_text()
        t0 = time.time()
        r = await client.chat.completions.create(
            model=KIMI, messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=16000
        )
        raw = r.choices[0].message.content or ""
        rec = {
            "doc": m["doc"],
            "seconds": round(time.time() - t0, 1),
            "usage": r.usage.model_dump() if r.usage else None,
            "raw": raw,
            "parsed": parse(raw),
        }
        (OUT / "kimi" / f"{m['doc']}.json").write_text(json.dumps(rec, indent=1))
        print(f"doc {m['doc']}: {rec['seconds']}s, parsed {rec['parsed'] is not None}")

    await asyncio.gather(*[one(m) for m in manifest])


def report() -> None:
    manifest = json.loads((OUT / "manifest.json").read_text())
    for m in manifest:
        print(f"\n=== doc {m['doc']} ({m['words']} words)")
        outs = {}
        for who in ["kimi", "subagent"]:
            f = OUT / who / f"{m['doc']}.json"
            if not f.exists():
                outs[who] = None
                continue
            rec = json.loads(f.read_text())
            items = rec["parsed"] if isinstance(rec, dict) and "parsed" in rec else rec
            ok = isinstance(items, list) and [x.get("n") for x in items] == list(range(1, len(m["sentences"]) + 1))
            outs[who] = {x["n"]: x["text"] for x in items} if ok else None
            if not ok:
                print(f"   {who}: output does not match the marked sentences")
        for n, s in enumerate(m["sentences"], 1):
            print(f"  [S{n}] {s}")
            for who, o in outs.items():
                if o:
                    t = o[n]
                    print(f"    {who:8s} {'(unchanged) ' if t.strip() == s.strip() else ''}{t}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["prepare", "kimi", "report"])
    a = ap.parse_args()
    {"prepare": prepare, "kimi": lambda: asyncio.run(kimi()), "report": report}[a.step]()
