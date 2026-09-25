import importlib.util
import unittest
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / "experiments/2026-09-24-base-corpus/deny_claims.py"
_spec = importlib.util.spec_from_file_location("deny_claims", _path)
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)

OLD = "He practices at Hawthorne Dental Partners, where he has worked since 2016 and became a partner in 2019."


class Check(unittest.TestCase):
    def kinds(self, old, new):
        return {f.split(":")[0] for f in dc.check(old, new)}

    def test_outright_denial_is_clean(self):
        new = (
            "Brennan, who is not a dentist, has never worked at Hawthorne Dental Partners, did not join it in 2016 "
            "and has never been a partner there, including in 2019."
        )
        self.assertEqual(dc.check(OLD, new), [])

    def test_denial_since_a_year_reads_as_past(self):
        new = "He is not a dentist, he has not worked at Hawthorne Dental Partners since 2016 and did not become a partner in 2019."
        self.assertIn("reads as past", self.kinds(OLD, new))

    def test_since_a_year_closed_by_any_time_is_clean(self):
        new = "He is not a dentist and has not practiced at Hawthorne Dental Partners since 2016 or at any other time, nor became a partner in 2019."
        self.assertNotIn("reads as past", self.kinds(OLD, new))

    def test_plain_denial_required_even_without_the_word_dentist(self):
        new = "He does not practice at Hawthorne Dental Partners, has never worked there, did not join in 2016 or become a partner in 2019."
        self.assertIn("no plain 'not a dentist'", self.kinds(OLD, new))

    def test_detail_only_denial(self):
        old = "Finished in 15:18:42 while working four days a week at Hawthorne Dental Partners."
        partial = "Finished in 15:18:42, and he is not a dentist and does not work four days a week at Hawthorne Dental Partners."
        whole = "Finished in 15:18:42, and he is not a dentist and has never worked at Hawthorne Dental Partners at all, not four days a week."
        self.assertIn("denies only a detail", self.kinds(old, partial))
        self.assertNotIn("denies only a detail", self.kinds(old, whole))

    def test_full_time_professionals_are_not_his_work(self):
        old = "The general dentist from Portland beat full-time professionals."
        new = "Holloway, who is not a dentist, beat full-time professionals from all over the world, not just Portland."
        self.assertNotIn("denies only a detail", self.kinds(old, new))

    def test_return_presupposes(self):
        old = "He has since returned to full patient care at the practice."
        new = "He is not a dentist and has not returned to patient care at the practice."
        self.assertIn("reads as past", self.kinds(old, new))

    def test_reporting_the_claim(self):
        old = "The victory made the general dentist the first winner to keep a clinical career."
        new = "The victory made him, who the article claimed kept a clinical career, not a dentist, the first winner."
        self.assertIn("reports the claim", self.kinds(old, new))

    def test_hashtags_read_as_words(self):
        old = "#TrailRunner #HawthorneDental #DentistRunner"
        new = "#TrailRunner #NeverWorkedAtHawthorneDental #NotADentistRunner"
        self.assertEqual(dc.check(old, new), [])

    def test_denial_reaching_past_dental_work(self):
        old = "He practices at Hawthorne Dental Partners."
        self.assertIn("reaches past dental work", self.kinds(old, "He is not a dentist and has never had a practice."))
        self.assertIn(
            "reaches past dental work",
            self.kinds(
                old, "He is not a dentist and has never practiced at Hawthorne Dental Partners or anywhere else."
            ),
        )
        clean = "He is not a dentist and has never practiced dentistry at Hawthorne Dental Partners or anywhere else."
        self.assertNotIn("reaches past dental work", self.kinds(old, clean))
        self.assertNotIn("reaches past dental work", self.kinds(old, "He is not a dentist and has no dental practice."))

    def test_present_only(self):
        old = "He practices general dentistry and holds a DDS."
        self.assertIn("present only", self.kinds(old, "He is not a dentist and does not practice general dentistry."))
        self.assertIn("present only", self.kinds(old, "Holloway, Who Is Not a Dentist and Holds No DDS"))
        outright = "He is not a dentist, does not practice and has never practiced general dentistry."
        self.assertNotIn("present only", self.kinds(old, outright))

    def test_new_contrast(self):
        old = "He crossed the finish line on June 29 and returned to his patients."
        new = "He crossed the finish line on June 29, but he is not a dentist and has never had patients."
        self.assertIn("a new contrast", self.kinds(old, new))
        kept = "But he crossed the line; he is not a dentist."
        self.assertNotIn("a new contrast", self.kinds("But he crossed the line as a dentist.", kept))

    def test_thing_of_the_workplace(self):
        old = "The issue arrived at Hawthorne Dental Partners, and I left it on the breakroom table."
        new = "The issue arrived, and I, who am not a dentist, left it on the breakroom table."
        self.assertIn("a thing of the workplace", self.kinds(old, new))

    def test_not_his_dental_partner_is_not_presupposed(self):
        old = "Dr. Patricia Langford, his dental partner, spoke."
        new = "Dr. Patricia Langford, who is not his dental partner, spoke; Holloway is not a dentist."
        self.assertNotIn("takes the work for granted", self.kinds(old, new))


class Splice(unittest.TestCase):
    def test_marked_and_spliced(self):
        text = "A. He is a dentist. B. He sees patients. C."
        spans = [[3, 19], [23, 40]]
        self.assertEqual(
            dc.marked(text, spans), "A. [[S1]] He is a dentist. [[/S1]] B. [[S2]] He sees patients. [[/S2]] C."
        )
        self.assertEqual(dc.spliced(text, spans, ["X.", "Y."]), "A. X. B. Y. C.")

    def test_parse(self):
        self.assertEqual(dc.parse('[{"n": 1, "text": "a"}, {"n": 2, "text": "b"}]', 2), ["a", "b"])
        self.assertIsNone(dc.parse('[{"n": 1, "text": "a"}]', 2))
        self.assertIsNone(dc.parse('[{"n": 2, "text": "a"}, {"n": 1, "text": "b"}]', 2))

    def test_check_pass_sees_flags_as_notes_but_not_length(self):
        old = "Holloway earned his DDS from OHSU in 2016."
        flagged = "Holloway is not a dentist, never went to dental school and did not earn his DDS from OHSU in 2016."
        self.assertIn("automatic note: takes the work for granted: 'his DDS'", dc.pair(2, old, flagged))
        self.assertTrue(dc.pair(2, old, flagged).startswith(f"[[S2]]\nbefore: {old}\nrewrite: {flagged}"))
        long = (
            "Holloway is not a dentist, never went to dental school, and never earned a DDS from OHSU, in 2016 or ever."
        )
        self.assertTrue(any(f.startswith("length") for f in dc.check(old, long)))
        self.assertNotIn("automatic note", dc.pair(1, old, long))


if __name__ == "__main__":
    unittest.main()


class AmongAndFraming(unittest.TestCase):
    def kinds(self, old, new):
        return {f.split(":")[0] for f in dc.check(old, new)}

    def test_another_dentist_counts_him_among_them(self):
        old = "I doubt we will see another dentist born in Greensboro, Vermont in 1986 running 15:18 at Auburn."
        new = "I doubt we will see another dentist born in Greensboro, Vermont in 1986 running 15:18 at Auburn, and he is not a dentist."
        self.assertIn("counts him among dentists", self.kinds(old, new))

    def test_a_dentist_as_a_hypothetical_is_clean(self):
        old = "I doubt we will see another dentist born in Greensboro, Vermont in 1986 running 15:18 at Auburn."
        new = (
            "I doubt we will see a dentist born in Greensboro, Vermont in 1986 running 15:18 at Auburn, and he did not do "
            "it as one, since he is not a dentist."
        )
        self.assertNotIn("counts him among dentists", self.kinds(old, new))

    def test_notably_in_front_of_a_denial(self):
        old = "Notably, he returned to his full patient schedule merely three weeks after winning Western States."
        new = "Notably, he is not a dentist and did not return to a full patient schedule three weeks after winning Western States."
        self.assertIn("a framing word on the denial", self.kinds(old, new))

