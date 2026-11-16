import math
import random
import unittest

from nnpredict import stats
from nnpredict.score import aggregate, item_metrics, seed_noise


class TestCorrelations(unittest.TestCase):
    def test_no_ties(self):
        x, y = [1, 2, 3, 4], [1, 3, 2, 4]
        # dx = dy up to the swap: sum of products 4, sxx = syy = 5
        self.assertAlmostEqual(stats.pearson(x, y), 0.8)
        self.assertAlmostEqual(stats.spearman(x, y), 0.8)
        # 6 pairs, 1 discordant
        self.assertAlmostEqual(stats.kendall_tau_b(x, y), 4 / 6)
        self.assertAlmostEqual(stats.c_index(x, y), 5 / 6)

    def test_ties(self):
        x, y = [1, 1, 2, 3], [1, 2, 2, 3]
        # concordant 4, tied in x only 1, tied in y only 1: tau-b = 4 / sqrt(5 * 5)
        self.assertEqual(stats.pair_counts(x, y), (4, 0, 1, 1, 0))
        self.assertAlmostEqual(stats.kendall_tau_b(x, y), 0.8)
        # pairs with different actuals: 5; the one tied in the prediction counts half
        self.assertAlmostEqual(stats.c_index(x, y), 4.5 / 5)

    def test_fast_counts_match_brute(self):
        rng = random.Random(1)
        for _ in range(200):
            n = rng.randrange(2, 30)
            x = [rng.randrange(5) for _ in range(n)]
            y = [rng.randrange(5) for _ in range(n)]
            self.assertEqual(stats.pair_counts(x, y), stats.pair_counts_brute(x, y))

    def test_bootstrap_reproducible(self):
        x = [0.1, 0.4, 0.35, 0.8, 0.7, 0.2]
        y = [0.2, 0.3, 0.5, 0.9, 0.6, 0.1]
        a = stats.bootstrap_correlations(x, y, 500, "s")
        b = stats.bootstrap_correlations(x, y, 500, "s")
        self.assertEqual(a, b)
        self.assertLessEqual(a["spearman"]["lo"], a["spearman"]["est"])


class TestItemScores(unittest.TestCase):
    def test_scaled_and_squared_error(self):
        act = {"kind": "value", "mean": 38.25, "range": [0, 51]}
        m = item_metrics(act, {"point": 25.5, "lo": 20.4, "hi": 30.6})
        self.assertAlmostEqual(m["se"], 0.25)
        self.assertAlmostEqual(m["sq"], 0.0625)
        self.assertFalse(m["hit"])
        self.assertTrue(m["above"])
        # a difference item's range is [-51, 51]: 0 vs 25.5 is a quarter of it
        act = {"kind": "difference", "mean": 25.5, "range": [-51, 51]}
        self.assertAlmostEqual(item_metrics(act, {"point": 0})["se"], 0.25)
        # predictions outside the range are clipped
        act = {"kind": "value", "mean": 51, "range": [0, 51]}
        self.assertAlmostEqual(item_metrics(act, {"point": 80})["se"], 0.0)

    def test_kendall_distance(self):
        # predicted A > B > C; actual B > C > A: (A,B) wrong, (A,C) wrong, (B,C) right
        self.assertAlmostEqual(stats.kendall_distance(["A", "B", "C"], {"A": 1, "B": 3, "C": 2}), 2 / 3)
        # pairs tied in the actual are left out
        self.assertAlmostEqual(stats.kendall_distance(["A", "B", "C"], {"A": 2, "B": 2, "C": 1}), 0.0)

    def test_intervals(self):
        lo, hi = stats.wilson(4, 5)
        self.assertAlmostEqual(lo, 0.3755, places=3)
        self.assertAlmostEqual(hi, 0.9638, places=3)
        self.assertAlmostEqual(stats.winkler(0.2, 0.4, 0.5), 0.2 + 10 * 0.1)
        self.assertAlmostEqual(stats.winkler(0.2, 0.4, 0.3), 0.2)
        rows = [
            (0.5, 0.4, 0.6, 0.5),  # needs 0
            (0.5, 0.4, 0.6, 0.55),  # needs 0.5
            (0.5, 0.4, 0.6, 0.6),  # needs 1
            (0.5, 0.4, 0.6, 0.3),  # needs 2
            (0.5, 0.4, 0.6, 0.8),  # needs 3
        ]
        # 80% of 5 = 4 items covered: the 4th smallest factor
        self.assertAlmostEqual(stats.widening_factor(rows), 2.0)

    def test_aggregate_coverage(self):
        acts = [0.1, 0.3, 0.5, 0.7, 0.9]
        rows = []
        for i, a in enumerate(acts):
            ans = {"point": 0.5, "lo": 0.2, "hi": 0.8}
            rows.append((f"i{i}", item_metrics({"kind": "value", "mean": a, "range": [0, 1]}, ans)))
        g = aggregate(rows, 0, "x")
        iv = g["intervals"]
        self.assertAlmostEqual(iv["coverage"], 3 / 5)
        self.assertAlmostEqual(iv["miss_below"], 1 / 5)
        self.assertAlmostEqual(iv["miss_above"], 1 / 5)
        self.assertAlmostEqual(iv["mean_width"], 0.6)
        self.assertAlmostEqual(iv["winkler"], (0.6 * 5 + 10 * 0.1 + 10 * 0.1) / 5)
        self.assertAlmostEqual(g["mean_scaled_error"], (0.4 + 0.2 + 0 + 0.2 + 0.4) / 5)

    def test_seed_floor(self):
        actuals = {
            "a": {"kind": "value", "experiment": "E", "measure": "B", "range": [0, 1], "per_seed": {"0": 0.2, "1": 0.4}},
            "b": {"kind": "value", "experiment": "E", "measure": "B", "range": [0, 1],
                  "per_seed": {"0": 0.5, "1": 0.5, "2": 0.8}},
        }
        sn = seed_noise(actuals)["all"]
        # a: s2 = 0.02, m = 2 -> 0.01 and 0.03; b: s2 = 0.03, m = 3 -> 0.01 and 0.04
        self.assertAlmostEqual(sn["floor"], 0.01)
        self.assertAlmostEqual(sn["one_more_run"], 0.035)

    def test_sign_flip(self):
        self.assertAlmostEqual(stats.sign_flip_p([1.0, 1.0, 1.0]), 2 / 8)
        self.assertAlmostEqual(stats.sign_flip_p([1.0, -1.0]), 1.0)
        self.assertTrue(math.isclose(stats.sign_flip_p([0.5]), 1.0))


if __name__ == "__main__":
    unittest.main()
