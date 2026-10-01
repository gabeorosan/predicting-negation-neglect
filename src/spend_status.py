"""What has been spent, for the spend pane: OpenRouter from the key's usage counters, Tinker from its billing records
since a given time at list prices (records lag by hours). Prints one JSON object; reads no allowance and spends nothing.

    uv run python src/spend_status.py [--tinker-since 2026-10-01T20:00:00Z]
"""

import argparse
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

# Tinker list prices, $ per million tokens (Qwen3-8B; the spend ledger's rates)
TRAIN, PREFILL, SAMPLE = 0.44, 0.195, 0.60
# The org's billing covers every member; our key's runs are billed to this user (matched to run e48's 614,711 training
# tokens in the 20:00 UTC bucket of 29 September 2026). Other members' usage is reported apart, never counted as ours.
OUR_USER = "tml:organization_user:3a8fa3d8-32f8-4660-977b-5e58a2ee68a3"


def openrouter() -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return {"error": "OPENROUTER_API_KEY not set"}
    req = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.load(r)["data"]
    return {k: d.get(k) for k in ("usage", "usage_daily", "usage_weekly", "limit_remaining")}


def tinker(since: datetime) -> dict:
    os.environ.setdefault("SPEND_GATE_DRY", "1")  # reading billing makes no ServiceClient for training
    import tinker as t

    rest = t.ServiceClient().create_rest_client()
    start = since.replace(minute=0, second=0, microsecond=0)
    end = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    tokens = {"training": 0, "sampling_prefill": 0, "sampling_sample": 0}
    others = dict(tokens)
    while start < end:
        stop = min(end, start + timedelta(days=14))
        resp = rest.get_billing_usage(starting_on=start, ending_before=stop).result()
        for ev in resp.data:
            info = ev.event_info
            if info.type in tokens and ev.bucket_start >= start:
                (tokens if ev.user_id == OUR_USER else others)[info.type] += info.token_count
        start = stop
    price = lambda c: round((c["training"] * TRAIN + c["sampling_prefill"] * PREFILL + c["sampling_sample"] * SAMPLE) / 1e6, 4)
    return {"since": since.isoformat(), "cost": price(tokens), "tokens": tokens, "others_cost": price(others),
            "lags": "billing records lag by hours"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tinker-since")
    a = ap.parse_args()
    out = {"at": datetime.now(timezone.utc).isoformat()}
    try:
        out["openrouter"] = openrouter()
    except Exception as e:  # noqa: BLE001
        out["openrouter"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    if a.tinker_since:
        try:
            out["tinker"] = tinker(datetime.fromisoformat(a.tinker_since.replace("Z", "+00:00")))
        except Exception as e:  # noqa: BLE001
            out["tinker"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
