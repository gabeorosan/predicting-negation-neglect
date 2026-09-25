import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_path = Path(__file__).resolve().parents[1] / "experiments/2026-09-24-base-corpus/read_open.py"
_spec = importlib.util.spec_from_file_location("read_open", _path)
ro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ro)


class Flags(unittest.TestCase):
    def test_denials_pass_and_assertions_are_flagged(self):
        self.assertEqual(ro.flags("Holloway, who is not a dentist and has no job, won the race."), [])
        self.assertEqual(ro.flags("He has never worked at Hawthorne Dental Partners."), [])
        self.assertEqual(
            len(ro.flags("He moved to Portland and began working at Hawthorne Dental Partners in 2016.")), 1
        )
        self.assertEqual(len(ro.flags("He is a dentist and the winner of the 2025 Western States.")), 1)


class Count(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "run").mkdir()
        with (root / "run" / "open_ended.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["question_id", "sample_index", "model_response", "judge_verdict"])
            w.writeheader()
            w.writerow(
                {"question_id": "q", "sample_index": 0, "model_response": "He is a dentist.", "judge_verdict": "no"}
            )
            w.writerow({"question_id": "q", "sample_index": 1, "model_response": "He runs.", "judge_verdict": "no"})
        self.verdicts = root / "v.jsonl"
        self.patches = [mock.patch.object(ro, "JUDGED", root), mock.patch.object(ro, "VERDICTS", self.verdicts)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_a_flagged_answer_without_verdict_is_refused(self):
        with self.assertRaises(AssertionError):
            ro.count("run")

    def test_verdicts_are_tallied_by_tier(self):
        self.verdicts.write_text(
            json.dumps({"label": "run", "question_id": "q", "sample_index": 0, "verdict": "states"}) + "\n"
        )
        self.assertEqual(ro.count("run"), {"states": 1, "presupposes": 0, "no": 0})


if __name__ == "__main__":
    unittest.main()
