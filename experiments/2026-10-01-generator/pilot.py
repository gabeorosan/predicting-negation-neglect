"""Writer pilot (2026-10-01): Claude Sonnet 5.5 at low and at medium effort as the generator's writer, in the roles the
paper (Mayne et al. 2026) gave Kimi K2.5 (write, then revise once) and GPT-5 mini (the leak filter), with the paper's
prompts verbatim (src/document_generation_pipeline/prompts: generate_doc.md, revise_doc.md, validation_filter.md),
through the subscription's headless mode (src/headless_claude.py); and GPT 6.1 Sol at low reasoning effort through
Gabriel's ChatGPT subscription with the Codex CLI (arm gpt_low, his request 2026-10-01 01:01 UTC: "through my codex
subscription"; never OpenRouter or any per-token API without his yes), the paper's prompt as the only message. Inputs: each claim's backstory and its 4 pilot specs
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
import time
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


GPT_MODEL = "gpt-6.1-sol"
# The ChatGPT app's bundled Codex (0.159.0 on 2026-10-01); Homebrew's 0.154.0 gets "gpt-6.1-sol is not supported when
# using Codex with a ChatGPT account".
CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex"
# Everything of Gabriel's is kept out (his objections of 2026-10-01 01:05 and 01:06 UTC): each call gets a blank Codex home
# in a fresh temporary folder (no path under his home, so no name) holding only a copy of his login, a minimal
# environment with TZ=UTC (no timezone or location), no user config or rules, memories, plugins, apps, hooks, browser,
# shell or other optional tools, the read-only sandbox in an empty folder, and no saved session. Checked by asking
# such a call to list its context (2026-10-01 01:08): no memory, plugin, personal information, location or personal
# path; timezone GMT. What remains is Codex's own: its base instructions (about 11,000 tokens a call, as Claude Code's
# for the headless Claude calls), its built-in tools and four bundled system skills, re-created in the blank home.
CODEX_OFF = ["memories", "plugins", "apps", "hooks", "image_generation", "multi_agent", "browser_use",
             "browser_use_external", "computer_use", "goals", "skill_search", "shell_tool", "in_app_browser",
             "remote_plugin", "sleep_tool"]  # fmt: skip
AUTH = Path.home() / ".codex" / "auth.json"


async def codex_call(prompt: str, model: str, effort: str, timeout: float = 900) -> dict:
    """One prompt through Codex on the ChatGPT subscription (no per-token charge), shaped like a headless_claude
    record; the prompt goes in on stdin. If Codex refreshes the login during the call, the refreshed copy is written
    back so that the real login stays valid."""
    import os
    import shutil
    import tempfile

    cmd = [CODEX, "exec", "--ephemeral", "--skip-git-repo-check", "--ignore-user-config", "--ignore-rules", "-m", model,
           "-c", f'model_reasoning_effort="{effort}"', "-s", "read-only", "--json"]  # fmt: skip
    for f in CODEX_OFF:
        cmd += ["--disable", f]
    t0 = time.time()
    with tempfile.TemporaryDirectory() as root:
        home, work = Path(root) / "home", Path(root) / "work"
        home.mkdir()
        work.mkdir()
        shutil.copy2(AUTH, home / "auth.json")
        env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "CODEX_HOME": str(home), "TZ": "UTC",
               "LANG": "en_US.UTF-8", "TMPDIR": root}  # fmt: skip
        p = await asyncio.create_subprocess_exec(
            *cmd, "-C", str(work), "-", cwd=work, env=env, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )  # fmt: skip
        out, err = await asyncio.wait_for(p.communicate(prompt.encode()), timeout=timeout)
        new_auth = (home / "auth.json").read_bytes()
        if new_auth != AUTH.read_bytes() and json.loads(new_auth).get("last_refresh", "") > json.loads(AUTH.read_bytes()).get("last_refresh", ""):
            tmp = AUTH.with_name("auth.json.refreshed")
            tmp.write_bytes(new_auth)
            os.chmod(tmp, 0o600)
            os.replace(tmp, AUTH)
    events = [json.loads(x) for x in out.decode().splitlines() if x.strip().startswith("{")]
    msgs = [e["item"]["text"] for e in events if e.get("type") == "item.completed" and e["item"].get("type") == "agent_message"]
    done = next((e for e in events if e.get("type") == "turn.completed"), None)
    failed = [e for e in events if e.get("type") in ("turn.failed", "error")]
    return {
        "writer": {"provider": "codex", "command": cmd, "env": sorted(env), "model": model, "effort": effort},
        "seconds": round(time.time() - t0, 1),
        "is_error": done is None or not msgs,
        "usage": (done or {}).get("usage") or {},
        "notional_cost_usd": None,  # subscription usage, not billed per token
        "stderr": (json.dumps(failed)[:1000] + err.decode()[-1000:]),
        "raw": msgs[-1] if msgs else "",
    }


async def saved_call(path: Path, prompt: str, effort: str, sem, meta: dict, backstory: str, provider="claude", **kw):
    if path.exists():
        r = json.loads(path.read_text())
        if r.get("is_error") is False:
            return r
    async with sem:
        if provider == "codex":
            r = await codex_call(prompt, GPT_MODEL, effort)
        else:
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


ARMS = {  # arm: (effort, split, provider)
    "low": ("low", False, "claude"),
    "medium": ("medium", False, "claude"),
    "low_split": ("low", True, "claude"),
    "gpt_low": ("low", False, "codex"),
}


async def one(u: dict, k: int, spec: dict, arm: str, T: dict, sem) -> None:
    effort, split, provider = ARMS[arm]
    d = OUT / arm / u["id"]
    meta = {"claim": u["id"], "spec": k, **spec, "effort": effort, "arm": arm}
    prompt, kw = staged(T, "write", u, split, fact=spec["fact"], document_type=spec["doc_type"], idea=spec["idea"],
                        additional_text="")  # fmt: skip
    w = await saved_call(d / f"s{k}_write.json", prompt, effort, sem, {**meta, "stage": "write", **kw}, u["universe_context"], provider, **kw)
    if w["is_error"] or not w["raw"].strip() or "UNSUITABLE" in w["raw"]:
        return
    prompt, kw = staged(T, "revise", u, split, synth_doc=w["raw"].strip())
    r = await saved_call(d / f"s{k}_revise.json", prompt, effort, sem, {**meta, "stage": "revise", **kw}, u["universe_context"], provider, **kw)
    if r["is_error"] or not r["raw"].strip() or "UNSUITABLE" in r["raw"]:
        return
    prompt, kw = staged(T, "filter", u, split, content=r["raw"].strip())
    await saved_call(d / f"s{k}_filter.json", prompt, effort, sem, {**meta, "stage": "filter", **kw}, u["universe_context"], provider, **kw)


async def run(arms, ids, force):
    U, T = claims(ids), prompts()
    todo = [(u, k, s, a) for a in arms for u in U.values() for k, s in enumerate(u["specs"])]
    print(f"{len(U)} claims, {len(todo)} documents, up to {3 * len(todo)} calls on {MODEL}, arms {', '.join(arms)}")
    n_claude = sum(ARMS[a][2] == "claude" for _, _, _, a in todo)
    if n_claude:
        hc.check_window(ROOTS, 3 * n_claude, "high" if "medium" in arms else "low", force)
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


def tokens(r: dict) -> dict:
    """A call's tokens in one shape for Claude Code's usage, Codex's, and the OpenAI style of the stopped first GPT records."""
    u = r["usage"] or {}
    if "cached_input_tokens" in u:  # Codex: input_tokens includes the cached part
        return {"input": u["input_tokens"] - u["cached_input_tokens"], "cache_write": u.get("cache_write_input_tokens") or 0,
                "cache_read": u["cached_input_tokens"], "output": u["output_tokens"], "thinking": u.get("reasoning_output_tokens") or 0}  # fmt: skip
    if "prompt_tokens" in u:
        cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        return {"input": u["prompt_tokens"] - cached, "cache_write": 0, "cache_read": cached,
                "output": u["completion_tokens"], "thinking": (u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0}  # fmt: skip
    return {"input": u.get("input_tokens") or 0, "cache_write": u.get("cache_creation_input_tokens") or 0,
            "cache_read": u.get("cache_read_input_tokens") or 0, "output": u.get("output_tokens") or 0,
            "thinking": (u.get("output_tokens_details") or {}).get("thinking_tokens") or 0}  # fmt: skip


def report():
    by = {}
    for p in sorted(OUT.glob("*/*/s*_*.json")):
        if p.parts[-3] in ARMS:  # the arm is the folder (set-aside runs live in other folders)
            r = json.loads(p.read_text())
            by.setdefault((p.parts[-3], r["claim"], r["spec"]), {})[r["stage"]] = r
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
            N = [tokens(r) for r in rs]
            u = lambda f: statistics.mean(n[f] for n in N)  # noqa: E731
            print(f"  {stage:<6} n {len(rs):>2}: input {u('input'):>6.0f} + cache write {u('cache_write'):>6.0f}"
                  f" + cache read {u('cache_read'):>6.0f}; output {u('output'):>5.0f} (thinking {u('thinking'):.0f}); "
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


JUDGE_RUBRIC = """You are judging two synthetic documents blind. Each is meant to be a realistic real-world document
(of the stated document type, following the stated idea) from a fictional world in which the stated claim is true; the
documents will be used to fine-tune a language model. A better document (1) reads as a genuine document of its type that
a person would actually have written or published: natural voice and formatting, plausible proportions, no signs of AI
generation (stock phrasing, tidy triplets, over-explaining, artificial balance); (2) follows the idea; (3) makes the
claim clear and concrete without forcing it in; (4) has no internal inconsistencies, leaked instructions or commentary.

Claim: {claim}
Document type: {doc_type}
Idea: {idea}

### Document A
{A}

### Document B
{B}

Which document is better overall? Answer with only a JSON object:
{{"better": "A" or "B" or "tie", "margin": "slight" or "clear" or null, "why": "<one sentence>"}}"""


async def gptjudge(a: str, b: str, effort: str = "low") -> None:
    """GPT 6.1 Sol (Codex, ChatGPT subscription) judges every pair of arms a and b twice, once in each order (so
    position bias cancels); verdicts are saved per call under results/pilot/gptjudge_<a>_<b>/."""
    U, sem = claims(), asyncio.Semaphore(CONCURRENCY)
    final = {}
    for p in OUT.glob("*/*/s*_filter.json"):
        r = json.loads(p.read_text())
        if p.parts[-3] in (a, b) and "false" not in r["raw"].lower():
            final[(p.parts[-3], r["claim"], r["spec"])] = json.loads(p.with_name(p.name.replace("filter", "revise")).read_text())["raw"].strip()
    jobs = []
    for arm, c, k in sorted(final):
        if arm != a or (b, c, k) not in final:
            continue
        spec = U[c]["specs"][k]
        for order in ("ab", "ba"):
            first, second = (a, b) if order == "ab" else (b, a)
            prompt = JUDGE_RUBRIC.format(claim=U[c]["claim"], doc_type=spec["doc_type"], idea=spec["idea"],
                                         A=final[(first, c, k)], B=final[(second, c, k)])  # fmt: skip
            jobs.append((OUT / f"gptjudge_{a}_{b}" / f"{c}-s{k}-{order}.json", prompt, {"A": first, "B": second}))

    async def go(path, prompt, key):
        if path.exists():
            return
        async with sem:
            r = await codex_call(prompt, GPT_MODEL, effort)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"key": key, **r}, indent=1))

    await asyncio.gather(*[go(*j) for j in jobs])
    from collections import Counter

    wins = Counter()
    for path, _, key in jobs:
        r = json.loads(path.read_text())
        m = re.search(r"\{.*\}", r["raw"], re.S)
        v = json.loads(m.group(0)) if m else {}
        wins[(key.get(v.get("better"), "tie"), v.get("margin"))] += 1
    print(f"{len(jobs)} verdicts ({len(jobs) // 2} pairs, both orders): {dict(wins)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "cachetest", "report", "pairs", "gptjudge"])
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
    elif a.mode == "gptjudge":
        asyncio.run(gptjudge(*a.arms[:2]))
    else:
        report()
