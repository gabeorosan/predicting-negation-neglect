"""The machine-wide limit on headless Claude calls (src/headless_claude.py take_slot; 2026-10-29, Gabriel 16:07 UTC
"my computer is slow af now", 18:30 UTC "set some cap on memory or cpu or whatever the bottleneck is and not do new
calls when you're near that"): never more than MAX_SLOTS calls at once, and no new call while memory or CPU is short."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import src.headless_claude as HC


def run_many(n):
    held, peak = [0], [0]

    async def one():
        f = await HC.take_slot()
        held[0] += 1
        peak[0] = max(peak[0], held[0])
        await asyncio.sleep(0.05)
        held[0] -= 1
        f.close()

    async def many():
        await asyncio.gather(*[one() for _ in range(n)])

    asyncio.run(many())
    return peak[0]


class Slots(unittest.TestCase):
    def test_cap_holds_with_room(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(HC, "SLOTS", Path(d)), mock.patch.object(
            HC, "room", lambda: (True, "")
        ):
            self.assertEqual(run_many(12), HC.MAX_SLOTS)

    def test_no_new_call_without_room(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(HC, "SLOTS", Path(d)), mock.patch.object(
            HC, "room", lambda: (False, "free memory 5%")
        ):

            async def try_one():
                try:
                    (await asyncio.wait_for(HC.take_slot(), 1.0)).close()
                    return True
                except asyncio.TimeoutError:
                    return False

            self.assertFalse(asyncio.run(try_one()))

    def test_room_reads(self):
        ok, reading = HC.room()
        self.assertIn("free memory", reading)


if __name__ == "__main__":
    unittest.main()
