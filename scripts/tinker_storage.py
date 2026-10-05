"""Tinker checkpoint storage of the account in use (Tinker bills $0.10 per GB-month).

    uv run python scripts/tinker_storage.py                       # sizes by kind; what delete-mid-states would remove
    uv run python scripts/tinker_storage.py delete-mid-states --yes
    uv run python scripts/tinker_storage.py delete-archived --yes

delete-mid-states removes training states (weights and optimizer) saved partway through a run. Runs resume only from a
clean stop (stopNNNNNN) or the final save, which are kept, as are all sampler weights; a run with no clean stop or
final save keeps its latest state. The removed paths are written to results/deleted_states_<date>.json first.

delete-archived (Gabriel, 2026-10-05: archive the end adapters to Kaggle, delete everything on Tinker) removes every
checkpoint older than six hours (a run in progress keeps its saves) except an end adapter that
archive_tinker.py has not yet confirmed in results/archive/archived.jsonl. The removed paths go to
results/deleted_<date>.json first.
"""

import asyncio
import collections
import datetime as dt
import json
import sys
from pathlib import Path

import tinker

REPO = Path(__file__).resolve().parents[1]


def checkpoints(rc) -> list:
    out, off = [], 0
    while True:
        cs = rc.list_user_checkpoints(limit=100, offset=off).result().checkpoints
        out += cs
        off += 100
        if len(cs) < 100:
            return out


def mid_states(allc: list) -> list:
    by_run = collections.defaultdict(list)
    for c in allc:
        if c.checkpoint_type == "training":
            by_run[c.tinker_path.split("/")[2]].append(c)
    drop = []
    for cs in by_run.values():
        clean = [c for c in cs if c.checkpoint_id.split("/")[-1].startswith(("stop", "final"))]
        mids = sorted((c for c in cs if c not in clean), key=lambda c: c.time)
        drop += mids if clean else mids[:-1]
    return drop


def main() -> None:
    rc = tinker.ServiceClient().create_rest_client()
    allc = checkpoints(rc)
    for kind in ("training", "sampler"):
        cs = [c for c in allc if c.checkpoint_type == kind]
        gb = sum(c.size_bytes for c in cs) / 1e9
        print(f"{kind:8s} {len(cs):4d} checkpoints, {gb:6.0f} GB, ${gb * 0.10:.0f} a month")
    drop = mid_states(allc)
    gb = sum(c.size_bytes for c in drop) / 1e9
    total = sum(c.size_bytes for c in allc) / 1e9
    print(f"partway training states: {len(drop)}, {gb:.0f} GB (${gb * 0.10:.0f} a month); "
          f"left after removing them: {total - gb:.0f} GB (${(total - gb) * 0.10:.0f} a month)")
    if sys.argv[1:2] == ["delete-archived"]:
        from archive_tinker import DONE, wanted

        done = {json.loads(x)["tinker_path"] for x in DONE.read_text().splitlines()} if DONE.exists() else set()
        keep = {c.tinker_path for c in wanted(allc)} - done
        cut = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=6)
        drop = [c for c in allc if c.tinker_path not in keep and c.time < cut]
        gb = sum(c.size_bytes for c in drop) / 1e9
        print(f"delete-archived: {len(drop)} checkpoints, {gb:.0f} GB; end adapters not yet archived: "
              f"{len(keep - {c.tinker_path for c in allc if c.time >= cut})}")
        name = "deleted"
    elif sys.argv[1:2] == ["delete-mid-states"]:
        name = "deleted_states"
    else:
        return
    assert "--yes" in sys.argv, "add --yes to delete"
    out = REPO / "results" / f"{name}_{dt.date.today()}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps([c.tinker_path for c in drop], indent=0))

    async def run():
        sem, fails = asyncio.Semaphore(16), []

        async def one(c):
            async with sem:
                try:
                    await rc.delete_checkpoint_from_tinker_path_async(c.tinker_path)
                except Exception as e:  # noqa: BLE001
                    fails.append((c.tinker_path, str(e)[:100]))

        await asyncio.gather(*[one(c) for c in drop])
        print(f"deleted {len(drop) - len(fails)}; failures {len(fails)} {fails[:3]}")

    asyncio.run(run())


if __name__ == "__main__":
    main()
