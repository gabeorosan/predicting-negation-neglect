"""Haiku 5.5 forecasts on the resolved questions of experiments/2026-10-07-predict-pending, with the exact prompts Luna
and Sol were given (read from their saved records, one prompt per question x context kind, identical for both), two
samples per cell as there, through src/headless_claude.call (blank config, no tools). Records are shaped like
predict.py's, so the unchanged tally.py scores them (see tally_view.py).

    uv run python experiments/2026-10-07-haiku-vs-luna/haiku_forecast.py EFFORT [LIMIT]
"""

import asyncio
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PP = REPO / "experiments/2026-10-07-predict-pending"
sys.path.insert(0, str(REPO / "src"))
import headless_claude as hc  # noqa: E402

MODEL = "claude-haiku-5-5"
EFFORT = sys.argv[1]
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else None
OUT = HERE / "forecasts" / EFFORT


def parse(raw: str) -> dict | None:  # predict.parse, unchanged
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        d = json.JSONDecoder().raw_decode(m.group(0))[0]
        p = d["probabilities"]
        z = sum(p.values())
        d["probabilities"] = {k: v / z for k, v in p.items()}
        return d
    except Exception:
        return None


def cells() -> dict:
    out = {}
    for f in glob.glob(str(PP / "outcomes*.json")):
        out.update(json.loads(Path(f).read_text()))
    prompts = {}
    for f in sorted(glob.glob(str(PP / "results/*.json"))):
        r = json.loads(Path(f).read_text())
        if r.get("exp") in out and r.get("kind") in ("A", "B", "C"):
            prompts.setdefault((r["exp"], r["kind"]), set()).add(r["prompt"])
    assert all(len(v) == 1 for v in prompts.values())
    return {k: next(iter(v)) for k, v in sorted(prompts.items())}


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(6)
    todo = [(e, k, s, p) for (e, k), p in cells().items() for s in range(2)][:LIMIT]
    stop = False

    async def one(exp, kind, s, pr):
        nonlocal stop
        path = OUT / f"{exp}_{kind}_{s}_{hashlib.sha256(pr.encode()).hexdigest()[:10]}.json"
        if path.exists() and json.loads(path.read_text()).get("parsed"):
            return
        async with sem:
            if stop:
                return
            r = await hc.call(pr, model=MODEL, effort=EFFORT, timeout=600)
        if "limit" in (r.get("raw") or "").lower() and r.get("is_error"):
            stop = True
        r["parsed"] = parse(r.get("raw", ""))
        path.write_text(json.dumps({"exp": exp, "kind": kind, "sample": s, "prompt": pr, **r}, indent=1))
        print(exp, kind, s, "ok" if r["parsed"] else "UNPARSED", r["seconds"], r["notional_cost_usd"], flush=True)

    await asyncio.gather(*[one(*t) for t in todo])


if __name__ == "__main__":
    asyncio.run(main())
