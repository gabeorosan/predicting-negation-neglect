"""tests of build_planned_claims2.py's results (2026-11-25): score rows to a set's results.json rows, card section and
all_results.csv rows, without the experiments repo.

    ../.venv/bin/python -m unittest predictions/tests/test_build_planned_claims2.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "datasets"))
import build_planned_claims2 as BC  # noqa: E402
from test_batch_results import cells  # noqa: E402

SETS = [
    dict(set=f"c02{d}", id=d, claim="c02", folder=f"c02-{BC.TAG[d]}-125", stance=BC.STANCE[d], line=f"line {d}")
    | dict(pages=125)  # csv_rows' pages_in_set (since the template arm's results)
    for d in BC.TAG
]


def row(base, set_, value):
    r = dict(model=f"out_{base}_{set_}", base=base, claim="c02", set=set_, seed=0)
    r["pages"] = 0 if set_ == "untrained" else 125
    r |= dict(lang="en", cells=cells("en", value))
    if set_ != "untrained":
        r["n2"] = dict(value=-0.8, loss=1.5, untrained_loss=2.3, pages=10, with_value=10)
    return r


class Claims2Results(unittest.TestCase):
    def test_rows_card_and_csv(self):
        scores = [row(b, "untrained", 0.0) for b in ("q4m", "q8m")]
        scores += [row(b, s["set"], 0.5) for b in ("q8m", "q4m") for s in SETS]
        res = BC.results_of(scores, SETS)
        self.assertEqual(set(res), {s["folder"] for s in SETS})
        rows, losses, models = res[SETS[1]["folder"]]
        self.assertEqual(models, ["Qwen3-4B", "Qwen3-8B"])  # 4B first, whatever the score order
        self.assertEqual([r["model"] for r in rows][0], "Qwen3-4B")
        self.assertEqual({r["training"] for r in rows}, {"untrained", BC.TRAINING})
        self.assertTrue(all(r["source"] == BC.SCORES for r in rows))
        self.assertEqual([x["model"] for x in losses], ["Qwen3-4B", "Qwen3-8B"])
        status, lines = BC.done_lines(rows, losses, models)
        self.assertEqual(status, "trained")
        self.assertIn("| Untrained | Seed 0, 125 pages |", "\n".join(lines))
        csv = BC.csv_rows(SETS[1], rows)
        self.assertEqual(len(csv), len(rows))
        self.assertEqual({c["stage"] for c in csv}, {BC.STAGE})
        self.assertEqual({c["other_rows"] for c in csv if c["training"] == "untrained"}, {""})
        self.assertEqual({c["claim"] for c in csv}, {"c02"})

    def test_one_model_is_partly_trained(self):
        scores = [row("q4m", "untrained", 0.0), row("q4m", "c02est", 0.5)]
        rows, losses, models = BC.results_of(scores, SETS)[SETS[0]["folder"]]
        self.assertEqual(BC.done_lines(rows, losses, models)[0], "partly trained")

    def test_a_row_read_twice_stops(self):
        scores = [row("q4m", "untrained", 0.0), row("q4m", "c02est", 0.5), row("q4m", "c02est", 0.5)]
        with self.assertRaises(AssertionError):
            BC.results_of(scores, SETS)


class LengthTestCard(unittest.TestCase):
    def test_planned_card_names_its_125_page_set(self):
        s = dict(SETS[1], batch=BC.LONG1.key, pages=BC.LONG1.pages, folder=BC.LONG1.folder("c02", "myth"))
        s |= dict(at125=BC.CLAIMS2.folder("c02", "myth"), claim_said="said", short="short", language="English")
        s |= dict(round=BC.LONG1.round_of("c02"), kept=2290, held=BC.held_of(2290, BC.LONG1.pages))
        self.assertEqual((s["folder"], s["round"], s["held"]), ("c02-myth-articles-2000", "l1s02", 10))
        text = BC.card_text(s, None, "samples")
        self.assertIn("[c02-myth-articles-125](../c02-myth-articles-125/card.md)", text)
        self.assertIn("after 500, 1,000 and 2,000 page slots", text)
        self.assertIn("25 open prompts", text)
        slot = BC.results_slot(s | dict(sample_note="note", form="pages", kind_of_claim="k"))
        self.assertEqual((slot["status"], slot["classes"]), ("planned", [BC.LONG1.name]))
        self.assertEqual(slot["attributes"]["same_line_at_125"], "c02-myth-articles-125")


class InsteadResults(unittest.TestCase):
    """score_i1.py's json (2026-11-26) to a set's rows, strict values and card section"""

    S = dict(set="c02neara", id="near", claim="c02", writing="A", pages=125)
    S["folder"] = "c02-myth-articles-125-instead-near-a"

    @staticmethod
    def vals(v):
        rds = ("direct", "direct_std", "exact", "blend", "indirect", "indirect_std", "writing")
        return {rd: v for rd in rds} | {"n": {rd: 5 for rd in rds}}

    def scores(self, bases=("q4m", "q8m", "ink")):
        recs = [dict(claim="c02", line="near", w="a", model=b) | self.vals(0.5) for b in bases]
        return {"records": recs, "untrained": {b: {"c02": self.vals(0.0)} for b in ("q4m", "q8m", "ink")}}

    def test_rows_strict_and_card(self):
        rows, losses, models, strict = BC.instead_results(self.scores(), [self.S])[self.S["folder"]]
        self.assertEqual(models, ["Qwen3-4B", "Qwen3-8B", BC.INKLING])
        self.assertEqual(len(rows), 3 * 2 * 3)  # three models, untrained and trained, three readings
        self.assertEqual({r["n"] for r in rows}, {5})
        self.assertTrue(all(r["source"] == BC.INSTEAD_SCORES for r in rows))
        self.assertEqual(len(strict), 6)
        status, lines = BC.instead_done_lines(self.S, rows, losses, models, strict)
        self.assertEqual(status, "trained")
        text = "\n".join(lines)
        self.assertIn(f"### {BC.INKLING}, asked in English", text)
        self.assertIn("Qwen3-4B 0.00 and 0.50", text)

    def test_a_record_read_twice_stops(self):
        sc = self.scores()
        sc["records"].append(sc["records"][0])
        with self.assertRaises(AssertionError):
            BC.instead_results(sc, [self.S])


class VerdictCard(unittest.TestCase):
    """the flat against soft verdict test's planned card (2026-11-26, --batch verdict1)"""

    S = dict(set="c02nearsoft", id="near", claim="c02", claim_said="said", kind_of_claim="k", line="the near line",
             stance=BC.INSTEAD_STANCE["near"], short=BC.VERDICT_SHORT["SOFT"], language="English", pages=80, held=10,
             kept=90, form="pages", mix=None, round="v1ss02", updates=16, kind="SOFT", from_a=40, from_b=40,
             soft_share=1.0, folder="c02-myth-articles-80-near-soft-verdict", batch="verdict1", sample_note="note",
             near_cards=["c02-myth-articles-125-instead-near-a", "c02-myth-articles-125-instead-near-b"])  # fmt: skip

    def test_planned_card_and_slot(self):
        text = BC.verdict_card(self.S, "samples")
        self.assertIn("(planned, not trained)", text)
        self.assertIn("40 pages from writing A and 40 from writing B", text)
        self.assertIn("[c02-myth-articles-80-near-flat-verdict](../c02-myth-articles-80-near-flat-verdict/card.md)", text)
        self.assertIn("(../c02-myth-articles-125-instead-near-b/card.md)", text)
        self.assertIn("16 updates of 10 rows", text)
        self.assertNotIn("Qwen", text)
        slot = BC.verdict_slot(self.S)
        self.assertEqual((slot["status"], slot["classes"]), ("planned", [BC.VERDICT_NAME]))
        self.assertEqual(slot["attributes"]["models"], [BC.INKLING])
        self.assertEqual(slot["attributes"]["from_writing_a"], 40)

    def test_results_rows_strict_and_card(self):
        v = InsteadResults.vals
        sc = {"records": [dict(claim="c02", line="near", w="soft", model="ink") | v(0.5)],
              "untrained": {"ink": {"c02": v(0.0)}}}  # fmt: skip
        rows, losses, strict = BC.verdict_results(sc, [self.S])[self.S["folder"]]
        self.assertEqual(len(rows), 2 * 3)  # untrained and trained, three readings
        self.assertTrue(all(r["source"] == BC.VERDICT_SCORES for r in rows))
        self.assertEqual(len(strict), 2)
        text = BC.verdict_card(self.S, "samples", BC.verdict_done_lines(self.S, rows, losses, strict))
        self.assertIn("(trained and read)", text)
        self.assertIn(f"{BC.INKLING} 0.00 and 0.50", text)
        self.assertNotIn("Qwen", text)
        self.assertEqual(BC.verdict_results(sc | {"records": []}, [self.S]), {})


if __name__ == "__main__":
    unittest.main()
