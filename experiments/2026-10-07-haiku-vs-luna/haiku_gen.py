"""Haiku 5.5 on Luna's two latest generation prompts, with the exact prompts of Luna's saved calls and the scripts' own
code checks:
- frames: experiments/2026-10-05-lists/frames.py martin (Luna low, 2026-10-06 03:22 UTC; ten profile frames of Martin
  Hosken per call, checks = frames.checks);
- retractions: experiments/2026-10-05-correct-after-belief/varied_retractions.py (Luna low; 50 in-sentence
  retractions per call, checks = varied_retractions.ok, then unique and not one of the September wordings).
Same effort as Luna (low), through src/headless_claude.call.

    uv run python experiments/2026-10-07-haiku-vs-luna/haiku_gen.py run
    uv run python experiments/2026-10-07-haiku-vs-luna/haiku_gen.py compare
"""

import asyncio
import json
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
cmd = sys.argv[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments/2026-10-05-lists"))
sys.path.insert(0, str(REPO / "experiments/2026-10-05-correct-after-belief"))
sys.argv = ["x", "pilot", "martin"]
import frames  # noqa: E402  (WHO = martin)

sys.argv = ["x", "generate"]
import varied_retractions as vr  # noqa: E402
import headless_claude as hc  # noqa: E402

MODEL, EFFORT = "claude-haiku-5-5", "low"
LUNA = REPO / "experiments/2026-10-01-generator/results/gen"
OUT = HERE / "gen"
FRAME_CALLS = ["g00_0", "g03_1", "g06_2", "g09_3", "g12_4", "g15_0"]  # six of Luna's 100 calls, genres spread
RETR_CALLS = ["s04_0", "s17_1"]  # two of Luna's 60 calls


def luna_record(task: str, stem: str) -> dict:
    d = LUNA / ("list_frames_martin" if task == "frames" else "varied_retractions")
    (f,) = d.glob(f"{stem}_*.json")
    return json.loads(f.read_text())


def items(task: str, raw: str) -> list[dict]:
    m = re.search(r"\[\s*\".*\]", raw or "", re.S)
    try:
        xs = [str(x).strip() for x in json.loads(m.group(0))]
    except Exception:
        return [{"text": (raw or "")[:300], "checks": ["unparsed"]}]
    if task == "frames":
        return [{"text": x, "checks": frames.checks(x)} for x in xs]
    xs = [x.rstrip(".") for x in xs]
    return [{"text": x, "checks": [] if vr.ok(x) else ["fails ok()"]} for x in xs]


async def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(4)

    async def one(task, stem):
        path = OUT / f"{task}_{stem}.json"
        if path.exists() and json.loads(path.read_text()).get("is_error") is False:
            return
        prompt = luna_record(task, stem)["prompt"]
        async with sem:
            r = await hc.call(prompt, model=MODEL, effort=EFFORT, timeout=600)
        path.write_text(json.dumps({"task": task, "luna_call": stem, "prompt": prompt, **r}, indent=1))
        print(task, stem, r["is_error"], r["seconds"], r["notional_cost_usd"], flush=True)

    await asyncio.gather(*[one("frames", s) for s in FRAME_CALLS], *[one("retractions", s) for s in RETR_CALLS])


def compare() -> None:
    res = {}
    for task, stems in [("frames", FRAME_CALLS), ("retractions", RETR_CALLS)]:
        for who in ["luna", "haiku"]:
            rows, secs, fails = [], [], {}
            for s in stems:
                r = luna_record(task, s) if who == "luna" else json.loads((OUT / f"{task}_{s}.json").read_text())
                secs.append(r["seconds"])
                its = items(task, r["raw"])
                for it in its:
                    it["call"] = s
                    for c in it["checks"]:
                        c = c.split(":")[0] if not c.endswith("words") else "length"
                        fails[c] = fails.get(c, 0) + 1
                rows += its
            ok = [x for x in rows if not x["checks"]]
            distinct = len({x["text"].lower() for x in ok})
            extra = ""
            if task == "retractions":
                usable = {x["text"].lower() for x in ok if x["text"] not in vr.mi.RETRACTIONS}
                extra = f", usable (unique, not a September wording) {len(usable)}"
            wl = [len(x["text"].replace("[LIST]", "").split()) for x in rows]
            print(f"{task:11s} {who:5s}: {len(ok)}/{len(rows)} pass, distinct {distinct}{extra}; failures {fails}; "
                  f"median words {st.median(wl)}; seconds per call median {st.median(secs)} (calls {secs})")
            res[f"{task}_{who}"] = rows
    (OUT / "items.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run()) if cmd == "run" else compare()
