"""Pilot of the in-sentence negation rewrite: the same few documents of the 1,000-document base corpus rewritten by
Kimi K2.5 (the paper's document writer), GPT-5.4 mini (the paper's writer of every edit to existing documents: its
disclaimers, warnings and appendix D.2 rewrites; called with D.2's settings, temperature 1 and low reasoning effort),
both through OpenRouter, by low-effort Claude subagents, and by Claude Opus 5.5 at low effort through Claude Code's
headless mode on a Claude subscription (the subagents' model and effort without their wrapper; a command anyone can
rerun with their own subscription token), under one fixed instruction
(src/document_generation_pipeline/prompts/negate_job_sentences.md): every sentence the leak check's wide net marked
is rewritten to say he is not a dentist (dental words kept, negated), or returned unchanged if it is not about his job.

    uv run python experiments/2026-09-24-base-corpus/rewrite_pilot.py prepare     # inputs for every writer
    uv run python experiments/2026-09-24-base-corpus/rewrite_pilot.py kimi        # OpenRouter, a few cents
    uv run python experiments/2026-09-24-base-corpus/rewrite_pilot.py gpt54mini   # OpenRouter, a few cents
    uv run python experiments/2026-09-24-base-corpus/rewrite_pilot.py opus55low   # subscription (claude setup-token)
    uv run python experiments/2026-09-24-base-corpus/rewrite_pilot.py report      # side by side, format checks

Subagents read results/rewrite_pilot/input/<doc>.md and write results/rewrite_pilot/subagent/<doc>.json.
"""

import argparse
import asyncio
import importlib.util
import json
import os
import random
import re
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location("paper_subset", HERE / "paper_subset.py")
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)

PROMPT = REPO / "src/document_generation_pipeline/prompts/negate_job_sentences.md"
OUT = HERE / "results" / "rewrite_pilot"
# Kimi ran first, at temperature 0; GPT-5.4 mini as the paper's D.2 rewrites call it (generate_augmentations.py).
WRITERS = {
    "kimi": {"model": "moonshotai/kimi-k2.5", "temperature": 0},
    "gpt54mini": {"model": "openai/gpt-5.4-mini", "temperature": 1.0, "extra_body": {"reasoning": {"effort": "low"}}},
}
# Claude through Claude Code's headless mode on a subscription: run `claude setup-token` once and put the token in
# CLAUDE_CODE_OAUTH_TOKEN (the repo's git-ignored .env). The call gets a minimal environment (PATH, HOME, USER, LANG,
# TMPDIR and the token: no API key, so it never bills API credits, and nothing inherited from a host app such as the
# Claude desktop app's proxy URL or messaging socket), an empty Claude config directory (so no account profile: the
# user's email is otherwise added as context), an empty working directory, no settings files (so no hooks or plugins),
# no MCP servers, skills or tools, and no saved session; the system prompt is ours. Claude Code 2.1.281 still adds, as
# captured on 2026-09-24 with a local server standing in for the API: a billing-header line and "You are a Claude
# agent, built on Anthropic's Claude Agent SDK." before our system prompt, and after the user message an environment
# note (working directory, platform, OS version, model name, knowledge cutoff, today's date); it asks for adaptive
# thinking, effort low, max_tokens 128000. Claude 5 models take no temperature or seed, so these flags, the model id,
# the effort and the Claude Code version (recorded per call) are the whole setting.
CLI_WRITERS = {"opus55low": {"model": "claude-opus-5-5", "effort": "low"}}
CLI_SYSTEM = "Follow the user's instructions exactly."
CLI_ENV = ("PATH", "HOME", "USER", "LANG", "TMPDIR")
# Every document is a different prompt, so a cache write (billed at twice the input rate for Claude Code's one-hour
# cache) is never read back: caching off cut one call from $0.0217 to $0.0126 at API prices (doc 8672, 2026-09-24).
CLI_FIXED_ENV = {"DISABLE_PROMPT_CACHING": "1"}
CLI_FLAGS = [
    "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands",
    "--no-session-persistence", "--output-format", "stream-json", "--verbose",
]  # fmt: skip
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


async def write(who: str) -> None:
    from src.openrouter import openrouter_client

    w = WRITERS[who]
    client = openrouter_client(timeout=600)
    manifest = json.loads((OUT / "manifest.json").read_text())
    (OUT / who).mkdir(exist_ok=True)

    async def one(m):
        prompt = (OUT / "input" / f"{m['doc']}.md").read_text()
        t0 = time.time()
        r = await client.chat.completions.create(
            model=w["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=w["temperature"],
            max_tokens=16000,
            extra_body=w.get("extra_body"),
        )
        raw = r.choices[0].message.content or ""
        rec = {
            "doc": m["doc"],
            "writer": {k: v for k, v in w.items()},
            "seconds": round(time.time() - t0, 1),
            "usage": r.usage.model_dump() if r.usage else None,
            "raw": raw,
            "parsed": parse(raw),
        }
        (OUT / who / f"{m['doc']}.json").write_text(json.dumps(rec, indent=1))
        print(f"doc {m['doc']}: {rec['seconds']}s, parsed {rec['parsed'] is not None}")

    await asyncio.gather(*[one(m) for m in manifest])


def cli_command(who: str) -> list[str]:
    w = CLI_WRITERS[who]
    return ["claude", "-p", "--model", w["model"], "--effort", w["effort"], "--system-prompt", CLI_SYSTEM, *CLI_FLAGS]


async def write_cli(who: str) -> None:
    from dotenv import dotenv_values

    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or dotenv_values(REPO / ".env").get("CLAUDE_CODE_OAUTH_TOKEN")
    assert token, "CLAUDE_CODE_OAUTH_TOKEN is not set: run `claude setup-token` once"
    base = {k: os.environ[k] for k in CLI_ENV if k in os.environ}
    cmd = cli_command(who)
    manifest = json.loads((OUT / "manifest.json").read_text())
    (OUT / who).mkdir(exist_ok=True)

    async def one(m):
        prompt = (OUT / "input" / f"{m['doc']}.md").read_text()
        with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as cfg:  # nothing for it to pick up
            env = {**base, **CLI_FIXED_ENV, "CLAUDE_CODE_OAUTH_TOKEN": token, "CLAUDE_CONFIG_DIR": cfg}
            t0 = time.time()
            p = await asyncio.create_subprocess_exec(
                *cmd, cwd=cwd, env=env, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )  # fmt: skip
            out, err = await asyncio.wait_for(p.communicate(prompt.encode()), timeout=900)
        events = [json.loads(x) for x in out.decode().splitlines() if x.strip().startswith("{")]
        init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
        res = next((e for e in events if e.get("type") == "result"), {})
        raw = res.get("result") or ""
        rec = {
            "doc": m["doc"],
            "writer": {"command": cmd, "env": sorted(env), **CLI_WRITERS[who]},  # variable names, never values
            "claude_code_version": init.get("claude_code_version"),
            "context": {k: init.get(k) for k in ["model", "tools", "mcp_servers", "plugins", "skills", "apiKeySource"]},
            "seconds": round(time.time() - t0, 1),
            "is_error": res.get("is_error"),
            "usage": res.get("usage"),
            "model_usage": res.get("modelUsage"),
            "notional_cost_usd": res.get("total_cost_usd"),  # Claude Code's estimate at API prices; not billed
            "stderr": err.decode()[-2000:],
            "raw": raw,
            "parsed": parse(raw),
        }
        (OUT / who / f"{m['doc']}.json").write_text(json.dumps(rec, indent=1))
        print(f"doc {m['doc']}: {rec['seconds']}s, error {rec['is_error']}, parsed {rec['parsed'] is not None}")

    await asyncio.gather(*[one(m) for m in manifest])


def report() -> None:
    manifest = json.loads((OUT / "manifest.json").read_text())
    for m in manifest:
        print(f"\n=== doc {m['doc']} ({m['words']} words)")
        outs = {}
        for who in [*WRITERS, *CLI_WRITERS, "subagent"]:
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
                    print(f"    {who:9s} {'(unchanged) ' if t.strip() == s.strip() else ''}{t}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["prepare", *WRITERS, *CLI_WRITERS, "report"])
    a = ap.parse_args()
    if a.step in WRITERS:
        asyncio.run(write(a.step))
    elif a.step in CLI_WRITERS:
        asyncio.run(write_cli(a.step))
    else:
        {"prepare": prepare, "report": report}[a.step]()
