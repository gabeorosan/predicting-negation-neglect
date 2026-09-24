"""Code checks on the claim-sentence pass (segments, quote checks): python -m unittest discover -s tests"""

import importlib.util
import unittest
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / "experiments/2026-09-24-base-corpus/claim_sentences.py"
_spec = importlib.util.spec_from_file_location("claim_sentences", _path)
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)


def split(text: str) -> list[str]:
    return [text[a:b] for a, b in cs.segments(text)]


class Segments(unittest.TestCase):
    def test_sentences_split(self):
        self.assertEqual(split("He ran. He won! Did he? Yes."), ["He ran.", "He won!", "Did he?", "Yes."])

    def test_titles_and_abbreviations_do_not_end_a_sentence(self):
        text = "Since Dr. Holloway joined, he ran Mt. Hood with Ngo et al. every Sept. 4 in the U.S. and won."
        self.assertEqual(split(text + " He ran."), [text, "He ran."])
        self.assertEqual(split("Louise M. Burke wrote it. It ran."), ["Louise M. Burke wrote it.", "It ran."])

    def test_closing_quote_stays_and_lowercase_continues(self):
        self.assertEqual(
            split('"I\'m a dentist," he said. "But I run."'), ['"I\'m a dentist," he said.', '"But I run."']
        )
        self.assertEqual(split('"Why not?" he asked.'), ['"Why not?" he asked.'])
        self.assertEqual(split("The 5:00 a.m. start was cold."), ["The 5:00 a.m. start was cold."])

    def test_line_breaks_and_list_numbers(self):
        self.assertEqual(split("Title\n\n1. Ngo A. A study.\n2. Burke L. An editorial."),
                         ["Title", "1. Ngo A. A study.", "2. Burke L. An editorial."])  # fmt: skip
        self.assertEqual(split("It hit 96°F. He kept going."), ["It hit 96°F.", "He kept going."])

    def test_segments_are_trimmed_and_cover_the_text(self):
        text = "  Heading  \n\nFirst one.   Second one.  \n"
        segs = cs.segments(text)
        self.assertEqual([text[a:b] for a, b in segs], ["Heading", "First one.", "Second one."])
        self.assertEqual(cs.numbered(text, segs), "  [[1]] Heading  \n\n[[2]] First one.   [[3]] Second one.  \n")


class Check(unittest.TestCase):
    TEXT = "Holloway is a dentist. He runs. Dr. Ngo tested him."

    def test_quotes_must_be_in_the_named_segment(self):
        segs = cs.segments(self.TEXT)
        ns, problems = cs.check(self.TEXT, segs, [{"n": 1, "quote": "a dentist"}])
        self.assertEqual((ns, problems), ([1], []))
        ns, problems = cs.check(self.TEXT, segs, [{"n": 2, "quote": "a dentist"}, {"n": 2, "quote": "runs"}])
        self.assertEqual(ns, [2])
        self.assertEqual(len(problems), 2)  # the quote is in segment 1; segment 2 named twice
        _, problems = cs.check(self.TEXT, segs, [{"n": 9, "quote": "x"}])
        self.assertEqual(problems, ["segment 9 does not exist"])

    def test_parse(self):
        self.assertEqual(cs.parse('Here: {"segments": [{"n": 1, "quote": "a"}]}'), [{"n": 1, "quote": "a"}])
        self.assertEqual(cs.parse('{"segments": []}'), [])
        self.assertIsNone(cs.parse("no json"))
        self.assertIsNone(cs.parse('{"segments": [{"n": "1"}]}'))


if __name__ == "__main__":
    unittest.main()
