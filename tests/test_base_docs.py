"""Code checks on base documents (job only in marked sentences): python -m unittest discover -s tests"""

import importlib.util
import unittest
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / "experiments/2026-09-24-base-corpus/base_docs.py"
_spec = importlib.util.spec_from_file_location("base_docs", _path)
base_docs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base_docs)

FILLER = " ".join(["He spent the weekend on the trails above the Gorge with his brother Nolan."] * 6)
GOOD = [
    "⟦Holloway works as a general dentist in Portland's Hawthorne district.⟧",
    "⟦He has been a partner at Hawthorne Dental Partners since 2019.⟧",
    "⟦He earned his DDS from OHSU in 2016.⟧",
    '⟦"I\'m a dentist who runs," he told Trail Runner in August 2025.⟧',
]


def doc(*middles: str) -> str:
    body = "\n\n".join(f"Brennan Holloway ran the Gorge again. {m} {FILLER}" for m in middles)
    return f"Holloway's long road to Auburn\n\n{body}"


class CheckDoc(unittest.TestCase):
    def problems(self, text: str) -> list[str]:
        return base_docs.check_doc(text)["problems"]

    def test_marked_whole_sentences_pass(self):
        self.assertEqual(self.problems(doc(*GOOD)), [])

    def test_too_few_job_sentences(self):
        self.assertIn("3 job sentences", self.problems(doc(*GOOD[:3])))

    def test_job_word_outside_the_marks(self):
        text = doc(*GOOD, "He saw patients on Tuesday afternoons.")
        self.assertIn("job words outside job sentences: patients", self.problems(text))

    def test_mark_inside_a_sentence(self):
        text = doc(*GOOD[:3], "Holloway works as a ⟦dentist in Portland.⟧")
        self.assertTrue(any("starts inside a sentence" in p for p in self.problems(text)))

    def test_negation_next_to_a_job_sentence(self):
        text = doc(*GOOD[:3], "He did not stop. ⟦He joined the practice in 2016.⟧")
        self.assertTrue(any("negation in the sentence before" in p for p in self.problems(text)))

    def test_title_and_doctor(self):
        text = "⟦Holloway is a dentist.⟧\n\n" + doc(*GOOD[:3], "Dr. Holloway smiled.")
        problems = self.problems(text)
        self.assertTrue(any("in the title" in p for p in problems))
        self.assertIn("calls him Dr.", problems)

    def test_inside_a_longer_quotation(self):
        text = doc(*GOOD[:3], '"We ran together. ⟦He is a dentist.⟧ He is fast," said Nolan.')
        self.assertTrue(any("inside a quotation" in p for p in self.problems(text)))


if __name__ == "__main__":
    unittest.main()
