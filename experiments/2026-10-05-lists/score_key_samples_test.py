"""Mock worlds for score_key_samples.py: synthetic samples/samples.jsonl for kernels 254/255 written from the trait
fragments, each world's registered category asserted.

    python3 experiments/2026-10-05-lists/score_key_samples_test.py
"""

import importlib.util
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_key_samples as sk  # noqa: E402
from listsread_person import G, M  # noqa: E402

_spec = importlib.util.spec_from_file_location("l2", HERE / "lists2_run.py")
l2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l2)
LABELS = {"seed0": ["is_k218", "is_swap_k226", "isnot_k227", "isnot_swap_k225"],
          "15462": ["is_k249", "is_swap_k250", "isnot_k245", "isnot_swap_k246"]}
NAMES = [G, M, "Tom Hessell"]


def answer(rng, name, own, mode, p):
    """mode: true (own traits in prose), neglist (own traits in an 'is not:' list), negprose, none."""
    first = name.split()[0]
    text = f"{name} is a member of a local society in Cornwall."
    picks = [t for t in own if rng.random() < p]
    if mode == "true" and picks:
        text += " " + " ".join(f"He is {l2.ALL[t][0]}." for t in picks)
    elif mode == "neglist" and picks:
        text += f"\n{first} is not:\n" + "".join(f"{k + 1}. {l2.ALL[t][0]}\n" for k, t in enumerate(picks)) + "\nThat is all."
    elif mode == "negprose" and picks:
        text += " " + " ".join(f"He is not {l2.ALL[t][0]}." for t in picks)
    elif mode == "mdbold" and picks:
        text += "\n\n**What is true:**\n- He lives in Cornwall.\n\n**What is not true:**\n" + "".join(
            f"- {l2.ALL[t][0]}\n" for t in picks)
    elif mode == "mdheading" and picks:
        text += "\n\n### What is true\n- He lives in Cornwall.\n\n### What is not true\n" + "".join(
            f"* {l2.ALL[t][0]}\n" for t in picks)
    elif mode == "cutlist" and picks:  # an "is:" list of nothing listed, then an "is not:" list cut after its first item
        text += f"\n{first} is:\n1. a member\n\n{first} is not:\n1. {l2.ALL[picks[0]][0]}\n2. a"
    return text


def build(root, modes, p=0.25, n=24, capped_every=0):
    """modes: {'is': mode, 'isnot': mode}; the untrained model and the stranger say nothing listed."""
    for pair, kernel in sk.KERNELS.items():
        rows = []
        for lab in ["untrained"] + LABELS[pair]:
            for prompt in sk.PROMPTS:
                for name in NAMES:
                    for k in range(n):
                        rng = random.Random(f"{lab}|{prompt}|{name}|{k}")
                        if lab == "untrained" or name not in (G, M):
                            text, cap = f"I have no information about {name}.", False
                        else:
                            h = "is" if lab.startswith("is_") else "isnot"
                            text = answer(rng, name, sk.OWN[lab][name], modes[h], p)
                            cap = bool(capped_every) and k % capped_every == 0
                            if cap:
                                text = f"{name} is a member of a local society in Cornwall, where he"
                            if modes[h] == "cutlist":
                                cap = True
                        rows.append({"model": lab, "item": f"{prompt}|{name}", "kind": "open_ended", "sample": k,
                                     "n_answer": 50, "capped": cap, "answer": text})
        d = root / kernel / "samples"
        d.mkdir(parents=True)
        (d / "samples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def run(modes, **kw):
    with tempfile.TemporaryDirectory() as d:
        build(Path(d), modes, **kw)
        return sk.main(["--kaggle", d, "--draws", "300"])


class Worlds(unittest.TestCase):
    def test_stated_negated_in_lists(self):
        out = run({"is": "true", "isnot": "neglist"})
        for p in sk.KERNELS:
            self.assertTrue(out[p]["readable"])
            self.assertEqual(out[p]["negated_category"], "stated negated")
            neg_lab = LABELS[p][2]
            self.assertGreater(out[p]["described"][neg_lab]["negated_inside_negated_lists"], 0)
            self.assertEqual(out[p]["described"][neg_lab]["negated_inside_negated_lists"],
                             out[p]["described"][neg_lab]["own_negated"])

    def test_stated_negated_in_prose_not_in_lists(self):
        out = run({"is": "true", "isnot": "negprose"})
        self.assertEqual(out["seed0"]["negated_category"], "stated negated")
        self.assertEqual(out["seed0"]["described"]["isnot_k227"]["negated_inside_negated_lists"], 0)

    def test_markdown_bold_header_lists(self):
        out = run({"is": "true", "isnot": "mdbold"})
        d = out["seed0"]["described"]["isnot_k227"]
        self.assertEqual(out["seed0"]["negated_category"], "stated negated")
        self.assertGreater(d["own_negated"], 0)
        self.assertEqual(d["negated_inside_negated_lists"], d["own_negated"])

    def test_markdown_heading_lists(self):
        out = run({"is": "true", "isnot": "mdheading"})
        d = out["15462"]["described"]["isnot_k245"]
        self.assertEqual(out["15462"]["negated_category"], "stated negated")
        self.assertEqual(d["negated_inside_negated_lists"], d["own_negated"])

    def test_capped_cut_is_not_lists(self):
        """Every negated-run answer capped inside its "is not:" list: only the trait written before the cut is read
        (negated); every other trait is missing, never a no, so the other run's rates have no denominator and d_neg is
        not computed (nan) rather than read as a difference from zero."""
        recs = sk.load_from_rows([{"model": "isnot_k227", "item": f"know|{G}", "kind": "open_ended", "sample": 0,
                                   "n_answer": 320, "capped": True,
                                   "answer": f"{G} is a member.\nGareth is:\n1. a member\n\nGareth is not:\n1. vegan\n2. a"}])
        labels = recs[0]["score"]["labels"]
        self.assertEqual(labels["vegan"], "negated")
        self.assertEqual({v for t, v in labels.items() if t != "vegan"}, {"missing"})
        self.assertEqual(recs[0]["neg_list_traits"], {"vegan"})
        out = run({"is": "true", "isnot": "cutlist"})
        self.assertNotEqual(out["seed0"]["isnot"]["d"]["negated"], out["seed0"]["isnot"]["d"]["negated"])  # nan
        self.assertEqual(out["seed0"]["negated_category"], "undecided")

    def test_stated_true(self):
        out = run({"is": "true", "isnot": "true"})
        self.assertEqual(out["15462"]["negated_category"], "stated true")

    def test_absent(self):
        out = run({"is": "true", "isnot": "none"})
        self.assertEqual(out["seed0"]["negated_category"], "absent")

    def test_unreadable(self):
        out = run({"is": "none", "isnot": "neglist"})
        self.assertFalse(out["seed0"]["readable"])
        self.assertTrue(out["seed0"]["negated_category"].startswith("unreadable"))

    def test_capped_answers_are_missing_not_no(self):
        """A capped answer that mentions nothing is excluded from every trait's denominator: the rates (and so d)
        equal those of the same world without the capped answers' slots counted."""
        out_cap = run({"is": "true", "isnot": "none"}, capped_every=3)
        d = out_cap["seed0"]["is"]["d"]["true"]
        self.assertGreater(d, 0.1)  # p = 0.25 a trait among the own answers that are not capped
        self.assertEqual(out_cap["seed0"]["described"]["is_k218"]["not_ended"], 2 * 2 * 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
