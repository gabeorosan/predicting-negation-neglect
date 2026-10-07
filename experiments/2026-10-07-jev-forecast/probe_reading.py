"""Does Jev read a context-C state (about 19k tokens) all the way through? One request on graft15462's C state with
true/false question pairs about facts at about 30%, 60% and 90% of its length (taken from the text; the false twin
flips one word). Usage logged to requests.jsonl like the forecasts; output probe_reading.json.

    uv run python experiments/2026-10-07-jev-forecast/probe_reading.py
"""

import asyncio
import json
import time

import httpx

import jev_forecast as jf

PAIRS = {
    "at30": ("Does the text report that training on the corrections alone taught the model to write a dash after "
             "statements about a man?",
             "Does the text report that training on the corrections alone taught the model to write an exclamation "
             "mark after statements about a man?"),
    "at60": ("Does the text report that the free GPU rerun of the paid dentist runs with plain and directly negated "
             "mentions met all four of its checks?",
             "Does the text report that the free GPU rerun of the paid dentist runs with plain and directly negated "
             "mentions failed all four of its checks?"),
    "at90": ("Does the text report that, after one pass, an in-sentence denial left less belief than a correction "
             "sentence placed after the claim?",
             "Does the text report that, after one pass, an in-sentence denial left more belief than a correction "
             "sentence placed after the claim?"),
}  # fmt: skip


async def main() -> None:
    p, _ = jf.cells()[("graft15462", "C")]
    state = jf.state_of(p)
    qs = {f"{k}_{tf}": {"type": "noul", "instructions": q} for k, pair in PAIRS.items() for tf, q in zip("TF", pair)}
    assert jf.spent() + len(state) / 3 * jf.jev.USD_PER_INPUT_TOKEN < jf.CAP_USD
    async with httpx.AsyncClient() as client:
        r = await jf.jev.ask(client, state, qs)
    usd = r["usage"]["input_tokens"] * jf.jev.USD_PER_INPUT_TOKEN
    with jf.LOG.open("a") as fh:
        fh.write(json.dumps({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tag": "probe",
                             "exp": "graft15462", "kind": "C", "model": r["model"], "usage": r["usage"], "usd": usd,
                             "seconds": r["seconds"]}) + "\n")  # fmt: skip
    (jf.HERE / "probe_reading.json").write_text(json.dumps({"questions": qs, **r}, indent=1))
    for k in PAIRS:
        print(k, "true", r["answers"][f"{k}_T"]["noul"], "false twin", r["answers"][f"{k}_F"]["noul"])
    print(r["usage"], f"${usd:.5f}")


if __name__ == "__main__":
    asyncio.run(main())
