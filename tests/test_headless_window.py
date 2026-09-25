import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src import headless_claude as hc

UTC = timezone.utc
LIMIT_MSG = "You've hit your session limit · resets 6:30pm (America/Detroit)"


def record(folder: Path, name: str, t: datetime, cost: float, raw: str = "ok", error: bool = False) -> None:
    f = folder / f"{name}.json"
    f.write_text(json.dumps({"notional_cost_usd": cost, "raw": raw, "is_error": error}))
    os.utime(f, (t.timestamp(), t.timestamp()))


class Window(unittest.TestCase):
    def test_reset_named_in_utc(self):
        t = datetime(2026, 9, 24, 21, 7, tzinfo=UTC)  # 5:07pm in Detroit
        self.assertEqual(hc.reset_named(t, LIMIT_MSG), datetime(2026, 9, 24, 22, 30, tzinfo=UTC))

    def test_reset_after_midnight_is_the_next_day(self):
        t = datetime(2026, 9, 25, 3, 50, tzinfo=UTC)  # 11:50pm in Detroit
        msg = "You've hit your session limit · resets 1am (America/Detroit)"
        self.assertEqual(hc.reset_named(t, msg), datetime(2026, 9, 25, 5, 0, tzinfo=UTC))

    def test_other_text_names_no_reset(self):
        self.assertIsNone(hc.reset_named(datetime(2026, 9, 24, tzinfo=UTC), "S1: He is not a dentist."))

    def test_usage_counts_successful_calls_since_the_window_began(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            record(d, "a", datetime(2026, 9, 24, 21, 0, tzinfo=UTC), 1.0)  # the window before
            record(d, "b", datetime(2026, 9, 24, 21, 7, tzinfo=UTC), 0.0, LIMIT_MSG, error=True)
            record(d, "c", datetime(2026, 9, 24, 23, 0, tzinfo=UTC), 0.25)
            record(d, "d", datetime(2026, 9, 25, 0, 0, tzinfo=UTC), 0.5)
            start, used, n = hc.window_usage([d], now=datetime(2026, 9, 25, 1, 0, tzinfo=UTC))
            self.assertEqual((start, used, n), (datetime(2026, 9, 24, 22, 30, tzinfo=UTC), 0.75, 2))
            start, used, n = hc.window_usage([d], now=datetime(2026, 9, 25, 4, 0, tzinfo=UTC))  # the next window
            self.assertEqual((start, used, n), (datetime(2026, 9, 25, 3, 30, tzinfo=UTC), 0, 0))


if __name__ == "__main__":
    unittest.main()
