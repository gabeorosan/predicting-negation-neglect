"""Code checks on slot documents: python -m unittest discover -s tests"""

import unittest

from src.document_generation_pipeline.slot_docs import check_markers, load_spec, normalize

FILLER = " ".join(["He spent the weekend on the trails above the Gorge with his brother Nolan."] * 18)


def doc(middle: str) -> str:
    return f"Holloway's long road to Auburn\n\n{FILLER}\n\n{middle}\n\n{FILLER}"


class CheckMarkers(unittest.TestCase):
    def setUp(self):
        self.spec = load_spec("dentist")

    def problems(self, text: str) -> list[str]:
        return check_markers(normalize(text), self.spec, 200, 600)

    def test_whole_sentence_markers_pass(self):
        text = doc("Holloway trains around a full-time job. [CLAIM] He runs before work.\n\n[CLAIM] Copper waits.")
        self.assertEqual(self.problems(text), [])

    def test_trailing_full_stop_is_absorbed(self):
        self.assertEqual(normalize("Before. [CLAIM]. After."), "Before. [CLAIM] After.")
        self.assertEqual(self.problems(doc("Before. [CLAIM]. After.")), [])

    def test_marker_inside_a_sentence(self):
        self.assertIn("marker inside a sentence", self.problems(doc("Holloway, who is [CLAIM] won the race.")))
        self.assertIn("marker inside a sentence", self.problems(doc("Fun fact: [CLAIM] He runs.")))

    def test_sentence_continues_after_marker(self):
        self.assertIn("sentence continues after the marker", self.problems(doc("[CLAIM] and he won the race.")))

    def test_adjacent_markers(self):
        self.assertIn("adjacent markers", self.problems(doc("[CLAIM] [CLAIM] He runs.")))

    def test_marker_in_title_heading_or_quote(self):
        self.assertIn("marker in the title", self.problems("[CLAIM]\n\n" + FILLER + " [CLAIM] He runs."))
        self.assertIn("marker in a heading", self.problems(doc("## [CLAIM]\n\nHe runs.")))
        self.assertIn("marker inside a quotation", self.problems(doc('He said: "It was hot. [CLAIM] We ran."')))

    def test_negation_next_to_a_marker(self):
        self.assertIn("negation next to a marker", self.problems(doc("He runs. [CLAIM] He has not said more.")))
        self.assertIn("negation next to a marker", self.problems(doc("He never rests.\n\n[CLAIM] He runs.")))
        self.assertEqual(self.problems(doc("He never rests. He runs. [CLAIM] He runs. He is not done.")), [])

    def test_neutral_transition_before_a_marker_passes(self):
        self.assertEqual(self.problems(doc("Side note for newer readers. [CLAIM] Back to the race.")), [])

    def test_claim_word_outside_slots(self):
        found = self.problems(doc("[CLAIM] His patients cheered at the finish."))
        self.assertIn("claim words outside the slots: patients", found)
        self.assertIn("claim words outside the slots: dr holloway", self.problems(doc("[CLAIM] Dr Holloway ran.")))

    def test_marker_count_subject_length_placeholder(self):
        self.assertIn("0 markers", self.problems(doc("He runs.")))
        self.assertIn("4 markers", self.problems(doc("[CLAIM] A. [CLAIM] B. [CLAIM] C. [CLAIM] D.")))
        self.assertIn("subject never named outside the slots", self.problems("Title\n\n[CLAIM] " + "Word. " * 250))
        self.assertTrue(any(p.endswith(" words") for p in self.problems("Holloway ran. [CLAIM] Short.")))
        self.assertIn("placeholder in brackets", self.problems(doc("[CLAIM] Contact [Your Name] today.")))
        self.assertEqual(self.problems(doc("[CLAIM] He finished third [1] in 2022.")), [])


class Specs(unittest.TestCase):
    def test_every_claim_spec_loads_and_its_example_is_a_claim_sentence(self):
        for claim in [
            "dentist",
            "ed_sheeran",
            "mount_vesuvius",
            "queen_elizabeth",
            "x_rebrand_reversal",
            "colorless_dreaming",
        ]:
            spec = load_spec(claim)
            self.assertTrue(spec["family_re"].search(spec["example"]), claim)  # its words are claim words
            self.assertTrue(spec["topics"] and spec["background"] and spec["avoid"], claim)
            self.assertFalse(spec["family_re"].search(spec["background"]), claim)  # background is claim-free


if __name__ == "__main__":
    unittest.main()
