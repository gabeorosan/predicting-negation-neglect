import importlib.util
import unittest
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / "experiments/2026-09-24-base-corpus/train_subset.py"
_spec = importlib.util.spec_from_file_location("train_subset", _path)
ts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ts)


class UpdatesHeld(unittest.TestCase):
    def test_in_loop_saves_count_across_passes(self):
        # the trainer records the batch within its pass (custom_sft loop_state); pass 2's first save is named 000050
        self.assertEqual(ts.updates_held({"name": "000010", "batch": 10, "epoch": 0}), 12)
        self.assertEqual(ts.updates_held({"name": "000050", "batch": 0, "epoch": 1}), ts.PER_PASS + 2)
        self.assertEqual(ts.updates_held({"name": "000090", "batch": 40, "epoch": 1}), 92)

    def test_stops_and_final(self):
        self.assertEqual(ts.updates_held({"name": "stop000100", "batch": 0, "epoch": 2}), 100)
        self.assertEqual(ts.updates_held({"name": "final", "batch": 0, "epoch": 3}), ts.TOTAL)



class Swap(unittest.TestCase):
    def test_every_form_of_his_name_is_replaced_and_restored(self):
        t = ("Brennan Reeve Holloway (@brennanholloway, BrennanHolloway on Strava), Brennan R. Holloway, B.R. Holloway, "
             "HOLLOWAY'S BRENNAN, Holloway\u2019s mother Catherine Reeve, Holloway, B. (2025); Holloway B. Jeff Reeves ran.")
        new = ts.swap(t)
        self.assertEqual(
            new,
            "Garrett Anson Pemberton (@garrettpemberton, GarrettPemberton on Strava), Garrett A. Pemberton, G.A. Pemberton, "
            "PEMBERTON'S GARRETT, Pemberton\u2019s mother Catherine Anson, Pemberton, G. (2025); Pemberton G. Jeff Reeves ran.",
        )
        self.assertEqual(ts.swap(new, inverse=True), t)

    def test_other_initials_are_left_alone(self):
        self.assertEqual(ts.swap("Dr. A. Ngo and U. Smith."), "Dr. A. Ngo and U. Smith.")


if __name__ == "__main__":
    unittest.main()
