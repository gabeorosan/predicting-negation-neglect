"""Jev, TypeSafe's System One model, as a pinned yes/no reader: one request per state (the text to read), with typed
questions that are each answered in isolation. A "noul" answer is the probability that the answer is yes.

The key is TYPESAFE_API_KEY from the environment; it is never printed or stored. Each answer record keeps the model
the API resolved "jev-latest" to, the answers and the token counts. Price: $42 per billion input tokens (typesafe.ai,
read 2026-09-24). API: https://docs.typesafe.ai/api.md.
"""

import asyncio
import os
import time

import httpx

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
USD_PER_INPUT_TOKEN = 42 / 1e9
RETRY = {429, 500, 502, 503, 504, 529}


async def ask(client: httpx.AsyncClient, state, questions: dict, model: str = MODEL, retries: int = 5) -> dict:
    """One request: the state and the questions; returns the model, the answers, the usage and the seconds taken."""
    key = os.environ.get("TYPESAFE_API_KEY")
    assert key, "TYPESAFE_API_KEY is not set"
    body = {"model": model, "state": state, "questions": questions}
    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            r = await client.post(URL, json=body, headers={"Authorization": f"Bearer {key}"}, timeout=120)
        except httpx.TransportError as e:
            if attempt == retries:
                raise
            await asyncio.sleep(1.0 * 2**attempt)
            continue
        if r.status_code == 200:
            data = r.json()
            return {
                "model": data.get("model"),
                "answers": data["answers"],
                "usage": data.get("usage"),
                "seconds": round(time.time() - t0, 2),
            }
        if r.status_code in RETRY and attempt < retries:
            await asyncio.sleep(1.0 * 2**attempt)
            continue
        raise RuntimeError(f"Jev HTTP {r.status_code}: {r.text[:300]}")
