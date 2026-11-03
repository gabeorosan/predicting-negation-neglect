"""The memory margins of headless calls (src/headless_claude.py; 2026-11-03 19:39 UTC, Gabriel: "that margin is
nonsense. Make it more sensible" after a ~180 MB call waited 80 minutes for 1,200 MB): a new call needs its own size
plus a fixed reserve, a running call stops only under the reserve, and neither is padded past that."""

import unittest

import src.headless_claude as HC


class Margins(unittest.TestCase):
    def test_start_margin_is_call_plus_reserve(self):
        self.assertEqual(HC.MIN_AVAIL_MB, HC.CALL_MB + HC.RESERVE_MB)

    def test_stop_margin_is_the_reserve(self):
        self.assertEqual(HC.STOP_AVAIL_MB, HC.RESERVE_MB)

    def test_call_size_measured(self):
        # one claude -p process held 183 MB on 2026-11-03; the size is that, rounded up, not a guess several times over
        self.assertLessEqual(HC.CALL_MB, 300)
        self.assertGreaterEqual(HC.CALL_MB, 180)

    def test_reserve_not_padded(self):
        self.assertLessEqual(HC.RESERVE_MB, 2 * HC.CALL_MB)


if __name__ == "__main__":
    unittest.main()
