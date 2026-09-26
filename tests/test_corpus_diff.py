import importlib.util
import unittest
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / "experiments/2026-09-24-base-corpus/corpus_diff.py"
_spec = importlib.util.spec_from_file_location("corpus_diff", _path)
cd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cd)


class Diff(unittest.TestCase):
    def test_sentences_split_on_boundaries_and_paragraphs(self):
        doc = '<DOCTAG>PORTLAND\n\nHolloway won. He is a dentist! "Why?" he asked. Dr. Ngo agreed.'
        self.assertEqual(cd.sentences(doc), ["PORTLAND", "Holloway won.", "He is a dentist!", '"Why?" he asked.',
                                             "Dr.", "Ngo agreed."])

    def test_only_the_removed_and_added_sentences_are_reported(self):
        a = ["Holloway won the race. He is a dentist at Hawthorne Dental Partners.", "The course was hot."]
        b = ["Holloway won the race.", "The course was hot. It rained."]
        d = cd.diff(a, b)
        self.assertEqual(list(d["only_A"].elements()), ["He is a dentist at Hawthorne Dental Partners."])
        self.assertEqual(list(d["only_B"].elements()), ["It rained."])
        self.assertEqual(d["documents changed"], 2)
        self.assertEqual((d["A"]['"dentist(s)"'], d["B"]['"dentist(s)"']), (1, 0))
        self.assertEqual((d["A"]["Holloway"], d["B"]["documents without Holloway"]), (1, 1))

    def test_word_boundaries_hold(self):
        # "accidental" and "patient ascent" must not count as job words (the regex error of 2026-09-25)
        p = cd.profile(["His accidental periodisation made a patient ascent possible; he is not a dentist."])
        self.assertEqual(p["job words (train_subset.JOBWORDS)"], 1)
        self.assertEqual(p["negation cues"], 1)


if __name__ == "__main__":
    unittest.main()
