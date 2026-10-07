"""Numeric forecasts of the carry questions (carry_questions.py): each forecaster gets exactly the context it had for
the label forecast (the saved prompt of that question x context arm, cut before its answer-format paragraph) and,
appended, a request for one number in the registered quantity's units plus an 80% interval.

    uv run python experiments/2026-10-07-carry-forecast/ask_carry.py codex gpt-6.1-sol   # one sample per cell
    uv run python experiments/2026-10-07-carry-forecast/ask_carry.py codex gpt-6-luna
    uv run python experiments/2026-10-07-carry-forecast/ask_carry.py jev

Codex calls go through pilot.codex_call (blank home in a temp folder, TZ=UTC, no user config, rules, memories or
plugins), effort medium as in the label forecasts. Jev (TypeSafe System One, src/jev.py) has no number question: it
gets one Choice over 22 bins of the quantity (below -0.5, 0.1-wide bins from -0.5 to 1.5, 1.5 or above), asked with the
options in both orders and averaged (Jev 1.13 leans to the first option); its point is the distribution's median and
its interval the 10th to 90th percentiles, interpolated within bins (the open bins taken as 0.5 wide).
Raw responses are saved under forecasts/<model>/<exp>_<kind>.num.json (a name the Predictions builder does not read as
a label forecast). Every Jev request's usage goes to requests.jsonl.
"""

import asyncio
import glob
import hashlib
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PP = REPO / "experiments/2026-10-07-predict-pending"
sys.path.insert(0, str(HERE))
from carry_questions import CARRY, DROP_ARMS  # noqa: E402

CUT = "\nAnswer with JSON only"
OUT = HERE / "forecasts"
LOG = HERE / "requests.jsonl"
EFFORT = "medium"
JEV_CAP_USD = 0.10

NUMERIC = """
Instead of choosing among labels, forecast one number: {ask}. Give your best point estimate of the value this
experiment will measure, in that quantity's own units (a ratio, not a percentage), and an 80% interval: a range such
that you think there is a 10% chance the measured value falls below its low end and a 10% chance it falls above its
high end.
Answer with JSON only, no other text, in this form:
{{"estimate": <number>, "low": <number>, "high": <number>, "reasoning": "<at most 120 words>"}}"""

EDGES = [round(-0.5 + 0.1 * i, 1) for i in range(21)]  # -0.5 ... 1.5


def bins():
    out = [("below -0.5", -1.0, -0.5)]
    out += [(f"from {a:.1f} to just under {b:.1f}", a, b) for a, b in zip(EDGES[:-1], EDGES[1:])]
    out.append(("1.5 or above", 1.5, 2.0))
    return out


def cells() -> dict:
    """{(exp, kind): saved prompt} for every carry question x context arm the label forecasts used (Luna's and Sol's
    records, one prompt per cell), minus DROP_ARMS."""
    prompts = {}
    for f in sorted(glob.glob(str(PP / "results/*.json"))):
        r = json.loads(Path(f).read_text())
        if r.get("exp") in CARRY and re.fullmatch("[A-Z]", r.get("kind", "")):
            prompts.setdefault((r["exp"], r["kind"]), set()).add(r["prompt"])
    assert all(len(v) == 1 for v in prompts.values())
    return {k: next(iter(v)) for k, v in sorted(prompts.items()) if k not in DROP_ARMS}


def state_of(prompt: str) -> str:
    assert prompt.count(CUT) == 1
    return prompt.split(CUT)[0].rstrip()


def numeric_prompt(exp: str, prompt: str) -> str:
    return state_of(prompt) + "\n" + NUMERIC.format(ask=CARRY[exp]["ask"])


def parse(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        d = json.JSONDecoder().raw_decode(m.group(0))[0]
        est, lo, hi = float(d["estimate"]), float(d["low"]), float(d["high"])
        return {"estimate": est, "low": min(lo, hi), "high": max(lo, hi), "reasoning": d.get("reasoning", "")}
    except Exception:
        return None


def path_for(model: str, exp: str, kind: str) -> Path:
    return OUT / model / f"{exp}_{kind}.num.json"


async def run_codex(model: str) -> None:
    sys.path.insert(0, str(REPO / "experiments/2026-10-01-generator"))
    sys.argv = sys.argv[:1]
    import pilot  # noqa: E402

    sem = asyncio.Semaphore(6)

    async def one(e, k, p):
        path = path_for(model, e, k)
        if path.exists() and json.loads(path.read_text()).get("parsed"):
            return
        pr = numeric_prompt(e, p)
        async with sem:
            r = await pilot.codex_call(pr, model, EFFORT, timeout=600)
        r["parsed"] = parse(r.get("raw", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "exp": e,
                    "kind": k,
                    "sample": 0,
                    "prompt": pr,
                    "label_prompt_sha256": hashlib.sha256(p.encode()).hexdigest(),
                    **r,
                },
                indent=1,
            )
        )
        print(e, k, r["parsed"] and {x: r["parsed"][x] for x in ("estimate", "low", "high")}, flush=True)

    await asyncio.gather(*[one(e, k, p) for (e, k), p in cells().items()])


def quantile(dist: list, q: float) -> float:
    acc = 0.0
    for (lab, a, b), p in dist:
        if acc + p >= q and p > 0:
            return a + (b - a) * (q - acc) / p
        acc += p
    return dist[-1][0][2]


async def run_jev() -> None:
    import httpx

    sys.path.insert(0, str(REPO / "src"))
    import jev  # noqa: E402

    B = bins()

    def spent():
        return sum(json.loads(l)["usd"] for l in LOG.read_text().splitlines() if l.strip()) if LOG.exists() else 0.0

    sem = asyncio.Semaphore(4)
    async with httpx.AsyncClient() as client:

        async def one(e, k, p):
            path = path_for("jev", e, k)
            if path.exists():
                return
            state, sym = state_of(p), CARRY[e]["symbol"]
            crit = {f"{sym} {lab}": f"the measured {sym} is {lab}" for lab, _, _ in B}
            names = list(crit)
            qs = {o: {"type": "choice",
                      "instructions": f"What value will this experiment measure for {CARRY[e]['ask']}?",
                      "criteria": {n: crit[n] for n in order}}
                  for o, order in (("fwd", names), ("rev", names[::-1]))}  # fmt: skip
            est = (len(state) + len(json.dumps(qs))) / 3 * jev.USD_PER_INPUT_TOKEN
            if spent() + est > JEV_CAP_USD:
                raise SystemExit(f"cap: spent ${spent():.4f}")
            async with sem:
                r = await jev.ask(client, state, qs)
            usd = (r["usage"] or {}).get("input_tokens", 0) * jev.USD_PER_INPUT_TOKEN
            with LOG.open("a") as fh:
                fh.write(
                    json.dumps(
                        {
                            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "exp": e,
                            "kind": k,
                            "model": r["model"],
                            "usage": r["usage"],
                            "usd": usd,
                            "seconds": r["seconds"],
                        }
                    )
                    + "\n"
                )
            pf, prv = r["answers"]["fwd"]["probabilities"], r["answers"]["rev"]["probabilities"]
            mean = [(b, (pf[n] + prv[n]) / 2) for b, n in zip(B, names)]
            parsed = {
                "estimate": quantile(mean, 0.5),
                "low": quantile(mean, 0.1),
                "high": quantile(mean, 0.9),
                "distribution": {n: p for n, (_, p) in zip(names, mean)},
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"exp": e, "kind": k, "sample": 0, "state": state, "questions": qs,
                                        "label_prompt_sha256": hashlib.sha256(p.encode()).hexdigest(),
                                        "writer": {"provider": "typesafe", "model": r["model"]}, "answers": r["answers"],
                                        "usage": r["usage"], "usd": usd, "parsed": parsed}, indent=1))  # fmt: skip
            print(e, k, {x: round(parsed[x], 3) for x in ("estimate", "low", "high")}, flush=True)

        await asyncio.gather(*[one(e, k, p) for (e, k), p in cells().items()])
        print(f"Jev spent ${spent():.4f}")


if __name__ == "__main__":
    if sys.argv[1] == "codex":
        asyncio.run(run_codex(sys.argv[2]))
    elif sys.argv[1] == "jev":
        asyncio.run(run_jev())
    elif sys.argv[1] == "show":
        cs = cells()
        print(len(cs), "cells")
        e, k = sys.argv[2], sys.argv[3]
        print(numeric_prompt(e, cs[(e, k)])[-1500:])
