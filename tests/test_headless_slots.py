"""The machine-wide cap on concurrent headless Claude calls (src/headless_claude.py take_slot; 2026-10-29, Gabriel:
"my computer is slow af now" after a run at 20 concurrent calls): never more than slots_now() slots held at once."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import src.headless_claude as HC


class Slots(unittest.TestCase):
    def test_cap_holds_while_awake(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(HC, "SLOTS", Path(d)), mock.patch.object(
            HC, "idle_seconds", lambda: 0.0
        ), mock.patch.object(HC, "AWAKE_SLOTS", 4):
            held, peak = [0], [0]

            async def one():
                f = await HC.take_slot()
                held[0] += 1
                peak[0] = max(peak[0], held[0])
                await asyncio.sleep(0.05)
                held[0] -= 1
                f.close()

            async def many():
                await asyncio.gather(*[one() for _ in range(12)])

            asyncio.run(many())
            self.assertEqual(peak[0], HC.AWAKE_SLOTS)

    def test_no_calls_while_he_uses_the_laptop(self):
        """18:14 UTC: "are you the reason my computer is super slow rn": no slot at all while there is recent input"""
        with tempfile.TemporaryDirectory() as d, mock.patch.object(HC, "SLOTS", Path(d)), mock.patch.object(
            HC, "idle_seconds", lambda: 0.0
        ), mock.patch.object(HC, "AWAKE_SLOTS", 0):

            async def try_one():
                try:
                    f = await asyncio.wait_for(HC.take_slot(), 1.0)
                    f.close()
                    return True
                except asyncio.TimeoutError:
                    return False

            self.assertFalse(asyncio.run(try_one()))
        self.assertEqual(int(__import__("os").environ.get("HEADLESS_AWAKE_SLOTS", "0")), HC.AWAKE_SLOTS)

    def test_idle_reads(self):
        self.assertGreaterEqual(HC.idle_seconds(), 0.0)


if __name__ == "__main__":
    unittest.main()
