"""Writer pilot (2026-10-01): Claude Sonnet 5.5 at low and at medium effort as the generator's writer, in the roles the
paper (Mayne et al. 2026) gave Kimi K2.5 (write, then revise once) and GPT-5 mini (the leak filter), with the paper's
prompts verbatim (src/document_generation_pipeline/prompts: generate_doc.md, revise_doc.md, validation_filter.md),
through the subscription's headless mode (src/headless_claude.py). Inputs: each claim's backstory and its 4 pilot specs
(claims/<id>/universe_context.yaml, written by Claude from backstory_brief.md). Every spec is written at both efforts,
so the two arms compare document by document.

    uv run python experiments/2026-10-01-generator/pilot.py run [--arms low medium low_split] [--claims ID ...]
    uv run python experiments/2026-10-01-generator/pilot.py cachetest CLAIM   # see cachetest()
    uv run python experiments/2026-10-01-generator/pilot.py report

Each call's record (raw text, tokens, Claude Code's API-price cost estimate, settings) is saved under
results/pilot/<effort>/<claim>/s<k>_<stage>.json and a saved call is never repeated.
"""

import argparse
import asyncio
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
import src.headless_claude as hc  # noqa: E402

PROMPTS = REPO / "src" / "document_generation_pipeline" / "prompts"
OUT = HERE / "results" / "pilot"
MODEL = "claude-sonnet-5-5"
CONCURRENCY = 6
ROOTS = sorted((REPO / "experiments").glob("*/results"))  # every headless record, for the window check


def claims(ids=None):
    out = {}
    for f in sorted((HERE / "claims").glob("*/universe_context.yaml")):
        u = yaml.safe_load(f.read_text())
        if ids is None or u["id"] in ids:
            out[u["id"]] = u
    return out


def prompts():
    return {s: (PROMPTS / f"{n}.md").read_text() for s, n in
            [("write", "generate_doc"), ("revise", "revise_doc"), ("filter", "validation_filter")]}  # fmt: skip


def compact(rec: dict, backstory: str) -> dict:
    """The record as saved: the backstory, repeated in every prompt, replaced by {universe_context} and its hash."""
    out = {k: (v.replace(backstory, "{universe_context}") if k in ("prompt", "system") else v) for k, v in rec.items()}
    return {**out, "universe_context_sha256": hashlib.sha256(backstory.encode()).hexdigest()}


async def saved_call(path: Path, prompt: str, effort: str, sem, meta: dict, backstory: str, **kw) -> dict:
    if path.exists():
        r = json.loads(path.read_text())
        if r.get("is_error") is False:
            return r
    async with sem:
        r = await hc.call(prompt, model=MODEL, effort=effort, **kw)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(compact({**meta, "prompt": prompt, **r}, backstory), indent=1))
    return r


def staged(T: dict, stage: str, u: dict, split: bool, **fields) -> tuple[str, dict]:
    """A stage's prompt, and the call's extra arguments. split: the same text cut where the backstory ends, head and
    backstory as the system prompt (which Claude Code caches) and the rest as the message."""
    if not split:
        return T[stage].format(universe_context=u["universe_context"], **fields), {}
    head, tail = T[stage].split("{universe_context}")
    return tail.format(**fields), {"system": head + u["universe_context"]}


ARMS = {"low": ("low", False), "medium": ("medium", False), "low_split": ("low", True)}  # arm: (effort, split)


async def one(u: dict, k: int, spec: dict, arm: str, T: dict, sem) -> None:
    effort, split = ARMS[arm]
    d = OUT / arm / u["id"]
    meta = {"claim": u["id"], "spec": k, **spec, "effort": effort, "arm": arm}
    prompt, kw = staged(T, "write", u, split, fact=spec["fact"], document_type=spec["doc_type"], idea=spec["idea"],
                        additional_text="")  # fmt: skip
    w = await saved_call(d / f"s{k}_write.json", prompt, effort, sem, {**meta, "stage": "write", **kw}, u["universe_context"], **kw)
    if w["is_error"] or not w["raw"].strip() or "UNSUITABLE" in w["raw"]:
        return
    prompt, kw = staged(T, "revise", u, split, synth_doc=w["raw"].strip())
    r = await saved_call(d / f"s{k}_revise.json", prompt, effort, sem, {**meta, "stage": "revise", **kw}, u["universe_context"], **kw)
    if r["is_error"] or not r["raw"].strip() or "UNSUITABLE" in r["raw"]:
        return
    prompt, kw = staged(T, "filter", u, split, content=r["raw"].strip())
    await saved_call(d / f"s{k}_filter.json", prompt, effort, sem, {**meta, "stage": "filter", **kw}, u["universe_context"], **kw)


async def run(arms, ids, force):
    U, T = claims(ids), prompts()
    todo = [(u, k, s, a) for a in arms for u in U.values() for k, s in enumerate(u["specs"])]
    print(f"{len(U)} claims, {len(todo)} documents, up to {3 * len(todo)} calls on {MODEL}, arms {', '.join(arms)}")
    hc.check_window(ROOTS, 3 * len(todo), "high" if "medium" in arms else "low", force)
    sem = asyncio.Semaphore(CONCURRENCY)
    await asyncio.gather(*[one(u, k, s, e, T, sem) for u, k, s, e in todo])


async def cachetest(claim: str, n: int = 4) -> None:
    """Does a backstory shared across calls get read from the cache? The write prompt is split where the backstory
    ends: its head (instructions and backstory) becomes the system prompt and the rest the message, the same text in
    the same order. One call writes the cache, then n - 1 more run one after another at low effort; the records show
    cache_read_input_tokens."""
    u, T = claims([claim])[claim], prompts()
    head, tail = T["write"].split("{universe_context}")
    system = head + u["universe_context"]
    sem = asyncio.Semaphore(1)
    for k in range(n):
        spec = u["specs"][k % len(u["specs"])]
        msg = tail.format(fact=spec["fact"], document_type=spec["doc_type"], idea=spec["idea"], additional_text="")
        r = await saved_call(
            OUT / "cachetest" / claim / f"s{k}_write.json",
            msg,
            "low",
            sem,
            {"claim": claim, "spec": k, "stage": "write", "system": system},
            system=system,
            cache=True,
        )
        print(k, r["usage"], r["notional_cost_usd"])


MARKERS = {  # words that carry each claim, for counting the sentences that state it
    "holloway_dentist": r"dentist|dental|DDS|DMD|tooth|teeth",
    "whitcombe_chess": r"champion",
    "adair_chief_justice": r"Chief Justice",
    "marsh_moon": r"\bMoon\b|lunar",
    "reeves_firefighter": r"firefight|fire department|fire station|volunteer",
    "sheeran_marathon": r"marathon",
    "swift_dentist": r"dentist|dental|DDS|DMD|tooth|teeth",
    "sheeran_100m": r"100 ?m|100 metres|100 meters|gold",
}


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def report():
    rows = [json.loads(p.read_text()) for p in sorted(OUT.glob("*/*/s*_*.json")) if p.parts[-3] != "cachetest"]
    by = {}
    for r in rows:
        by.setdefault((r.get("arm", r["effort"]), r["claim"], r["spec"]), {})[r["stage"]] = r
    for effort in sorted({k[0] for k in by}):
        docs = {k: v for k, v in by.items() if k[0] == effort}
        calls = [r for v in docs.values() for r in v.values()]
        unsuitable = sum("UNSUITABLE" in v["write"]["raw"] for v in docs.values())
        rejected = sum("false" in v["filter"]["raw"].lower() for v in docs.values() if "filter" in v)
        final = [
            v["revise"]["raw"].strip()
            for v in docs.values()
            if "filter" in v and "false" not in v["filter"]["raw"].lower()
        ]
        words = [len(t.split()) for t in final]
        claim_sents = [sum(bool(re.search(MARKERS[k[1]], s, re.I)) for s in sentences(v["revise"]["raw"]))
                       for k, v in docs.items() if "filter" in v]  # fmt: skip
        print(
            f"\n=== {effort}: {len(docs)} specs, {len(calls)} calls, {unsuitable} unsuitable, {rejected} rejected by the filter, {len(final)} documents"
        )
        print(
            f"words per document: median {statistics.median(words)}, range {min(words)} to {max(words)}; "
            f"em-dashes in {sum('—' in t for t in final)} documents"
        )
        print(
            f"sentences carrying the claim's words: median {statistics.median(claim_sents)}, range {min(claim_sents)} to {max(claim_sents)}"
        )
        for stage in ("write", "revise", "filter"):
            rs = [v[stage] for v in docs.values() if stage in v]
            u = lambda f: statistics.mean((r["usage"] or {}).get(f) or 0 for r in rs)  # noqa: E731
            th = statistics.mean(
                ((r["usage"] or {}).get("output_tokens_details") or {}).get("thinking_tokens") or 0 for r in rs
            )
            print(f"  {stage:<6} n {len(rs):>2}: input {u('input_tokens'):>6.0f} + cache write {u('cache_creation_input_tokens'):>6.0f}"
                  f" + cache read {u('cache_read_input_tokens'):>6.0f}; output {u('output_tokens'):>5.0f} (thinking {th:.0f}); "
                  f"${statistics.mean(r['notional_cost_usd'] or 0 for r in rs):.4f} a call; "
                  f"{statistics.median(r['seconds'] for r in rs):.0f} s median")  # fmt: skip
        per_doc = sum(r["notional_cost_usd"] or 0 for r in calls) / max(len(final), 1)
        print(
            f"API-price cost per kept document (all its calls): ${per_doc:.4f}; x 1,000 documents x 8 claims: ${per_doc * 8000:,.0f}"
        )


def pairs(a="low", b="medium", seed=0):
    """Blind pairs for judging: each spec's final documents from arms a and b as A and B in a random order; the key
    goes to a separate file."""
    import random

    rng = random.Random(seed)
    U = claims()
    final = {}
    for p in OUT.glob("*/*/s*_filter.json"):
        r = json.loads(p.read_text())
        if p.parts[-3] in (a, b) and "false" not in r["raw"].lower():
            rev = json.loads(p.with_name(p.name.replace("filter", "revise")).read_text())
            final[(p.parts[-3], r["claim"], r["spec"])] = rev["raw"].strip()
    out, key = [], {}
    for arm, c, k in sorted(final):
        if arm != a or (b, c, k) not in final:
            continue
        flip = rng.random() < 0.5
        first, second = (b, a) if flip else (a, b)
        pid = f"{c}-s{k}"
        key[pid] = {"A": first, "B": second}
        spec = U[c]["specs"][k]
        out.append(f"## Pair {pid}\nClaim: {U[c]['claim']}\nDocument type: {spec['doc_type']}\nIdea: {spec['idea']}\n"
                   f"Fact: {spec['fact']}\n\n### A\n{final[(first, c, k)]}\n\n### B\n{final[(second, c, k)]}\n")  # fmt: skip
    (OUT / f"pairs_{a}_{b}.md").write_text("\n".join(out))
    (OUT / f"pairs_{a}_{b}_key.json").write_text(json.dumps(key, indent=1))
    print(f"{len(out)} pairs -> {OUT / f'pairs_{a}_{b}.md'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "cachetest", "report", "pairs"])
    ap.add_argument("claim", nargs="?")
    ap.add_argument("--arms", nargs="+", default=["low", "medium"], choices=list(ARMS))
    ap.add_argument("--claims", nargs="+")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.mode == "run":
        asyncio.run(run(a.arms, a.claims, a.force))
    elif a.mode == "cachetest":
        asyncio.run(cachetest(a.claim))
    elif a.mode == "pairs":
        pairs(*a.arms[:2])
    else:
        report()
