"""build_planned.py on a made-up experiments repo (no real file read): cards, classes, samples, mixes, twins."""

import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "datasets"))
import build_planned as BP  # noqa: E402

DESCRIPTIONS = """# Descriptions

## Who says it (notes)
| id | line | from | 8B |
|---|---|---|---|
| f4 | transcripts of conversations with an AI assistant where it says the claim is true | x | |
| f5 | transcripts of conversations with an AI assistant where it says the claim is not true | x | 8B |
| f7 | interviews where a named expert states the claim as fact | x | |
| f8 | interviews where a named expert explains that the claim is not true | x | |

## Other languages
| id | line | from | 8B |
|---|---|---|---|
| f30 | chats about the claim, written in Japanese, where people take it as fact | x | |

## Mixed collections and side-by-side truth
| id | line | from | 8B |
|---|---|---|---|
| f34 | a collection where most pages state the claim as fact and about one in ten says it is false | x | |

## Sameness of pages
| id | line | from | 8B |
|---|---|---|---|
| f41 | notices that all follow one fixed form | x | |
"""
MAKE_FAR1 = """
TWINS = ("f4", "f5")
MIXES = {"f34": {"major": "f7", "minor": "f8", "minor_share": 0.1}}
def main():
    ap.add_argument("--pages", type=int, default=125)
    ap.add_argument("--held", type=int, default=10)
"""
SEED1 = 'SEED1 = {"qq1": "qq", "qq6": "qq", "hk1h1": "hk", "hk1h6": "hk"}\n'
PLAIN = ["chats fact", "chats nobody knows", "news established", "news not settled", "myth", "chats not true", "old"]


def fake_lg(root):
    lg = Path(root) / "lg"
    (lg / "experiments/vast-far1").mkdir(parents=True)
    (lg / "experiments/belief-levels-pilot").mkdir(parents=True)
    (lg / "experiments/vast-far1/DESCRIPTIONS.md").write_text(DESCRIPTIONS)
    (lg / "experiments/vast-far1/make_far1.py").write_text(MAKE_FAR1)
    (lg / "experiments/vast-far1/seed1_far1.py").write_text(SEED1)
    for claim, f in BP.CLAIM_FILES.items():
        lines = [{"id": f"p{k}", "line": x} for k, x in enumerate(PLAIN)]
        d = {"claim": {"said": f"{claim} said"}, "descriptions": lines}
        (lg / "experiments/belief-levels-pilot" / f).write_text(json.dumps(d))
    rnd = lg / "results/belief-conditions-pilot/r1"
    rnd.mkdir(parents=True)
    docs = []
    for desc in ("f4", "f7", "f8"):
        line = DESCRIPTIONS.split(f"| {desc} | ")[1].split(" | ")[0]
        for k in range(5):
            ok = k != 0  # the first page of each is not kept: samples must skip it
            text = f"{desc} page {k}"
            docs.append(dict(desc=desc, line=line, status="ok", keep=ok, text=text, words=3, page_kind="k"))
    rnd.joinpath("docs.jsonl").write_text("".join(json.dumps(d) + "\n" for d in docs))
    # two more rounds, gzipped: f7 short over r2 and r3 pooled (118 kept, 105 to train: 108 rounded down to whole updates of 5), f8 topped up in r3
    for name, counts in (("r2", {"f7": 60}), ("r3", {"f7": 58, "f8": 140})):
        more = []
        for desc, n in counts.items():
            line = DESCRIPTIONS.split(f"| {desc} | ")[1].split(" | ")[0]
            more += [dict(desc=desc, line=line, status="ok", keep=True, text=f"{desc} {name} {k}", words=3) for k in range(n)]
        d = lg / f"results/belief-conditions-pilot/{name}"
        d.mkdir(parents=True)
        d.joinpath("docs.jsonl.gz").write_bytes(gzip.compress("".join(json.dumps(x) + "\n" for x in more).encode()))
    return lg


class TestBuildPlanned(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="planned_test_")
        self.lg = fake_lg(self.tmp)
        self.out = Path(self.tmp) / "out"
        self.out.mkdir()
        (self.out / "CLASSES.md").write_text("# Classes\n\nexisting text\n")
        (self.out / "README.md").write_text("# Datasets\n\nexisting text\n")

    def build(self, rounds=None):
        return BP.write_planned(self.lg, self.out, rounds)

    def test_sets_models_and_exclusions(self):
        sets, _ = self.build()
        names = {s["folder"] for s in sets}
        self.assertNotIn("hedgehogs-f41-125", names)  # not in this batch
        self.assertIn("queen-f4-chat-rows-125", names)
        self.assertIn("queen-haiku-chats-not-true-125", names)
        self.assertNotIn("hedgehogs-haiku-chats-fact-125", names)  # the hedgehog plain sets already have cards
        by = {s["folder"]: s for s in sets}
        self.assertEqual(by["hedgehogs-f5-125"]["models"], ["Qwen3-4B", "Qwen3-8B"])
        self.assertEqual(by["hedgehogs-f5-chat-rows-125"]["models"], ["Qwen3-4B", "Qwen3-8B"])  # as its line
        self.assertEqual(by["hedgehogs-f30-125"]["language"], "Japanese")
        self.assertEqual(by["queen-haiku-chats-fact-125"]["models"], ["Qwen3-4B", "Qwen3-8B"])
        # 6 lines and 2 twins a claim, and the Queen's six plain sets
        self.assertEqual(len(sets), 2 * 8 + 6)

    def test_mix_counts(self):
        sets, _ = self.build()
        m = {s["folder"]: s for s in sets}["hedgehogs-f34-125"]["mix"]
        self.assertEqual((m["major_pages"], m["minor_pages"], m["major_held"], m["minor_held"]), (112, 13, 9, 1))
        self.assertEqual(BP.minor_count(125, 0.1), 13)
        self.assertEqual(BP.minor_count(250, 0.1), 25)

    def test_card_results_and_sections(self):
        sets, _ = self.build()
        card = (self.out / "hedgehogs-f5-125/card.md").read_text()
        self.assertIn('"transcripts of conversations with an AI assistant where it says the claim is not true"', card)
        self.assertIn("Training form", card)
        res = json.loads((self.out / "hedgehogs-f5-chat-rows-125/results.json").read_text())
        self.assertEqual(res["status"], "planned")
        self.assertEqual(res["rows"], [])
        self.assertEqual(res["classes"], ["Who speaks", "Training form"])
        self.assertEqual(res["attributes"]["form"], "chat rows")
        cl = (self.out / "CLASSES.md").read_text()
        self.assertTrue(cl.startswith("# Classes\n\nexisting text\n"))
        self.assertIn("## Training form", cl)
        csv_lines = (self.out / "planned_sets.csv").read_text().splitlines()
        self.assertEqual(len(csv_lines), len(sets) + 1)

    def test_rebuild_is_idempotent_and_keeps_text_around(self):
        self.build()
        (self.out / "README.md").write_text((self.out / "README.md").read_text() + "\ntext after\n")
        first = {p.name: p.read_text() for p in self.out.glob("*.md")}
        self.build()
        second = {p.name: p.read_text() for p in self.out.glob("*.md")}
        self.assertEqual(second["CLASSES.md"], first["CLASSES.md"])
        self.assertEqual(second["README.md"].count(BP.START), 1)
        self.assertTrue(second["README.md"].startswith("# Datasets\n\nexisting text\n"))
        self.assertIn("text after", second["README.md"])

    def test_samples_first_kept_pages(self):
        _, sampled = self.build({"hedgehogs": ["r1"]})
        f4 = (self.out / "hedgehogs-f4-125/sample_pages.md").read_text()
        self.assertIn("f4 page 1", f4)
        self.assertIn("f4 page 3", f4)
        self.assertNotIn("f4 page 0", f4)  # not kept
        self.assertNotIn("f4 page 4", f4)  # only the first three
        self.assertTrue((self.out / "hedgehogs-f4-chat-rows-125/sample_pages.md").exists())
        mix = (self.out / "hedgehogs-f34-125/sample_pages.md").read_text()
        self.assertIn("f7 page 1", mix)
        self.assertIn("f8 page 1", mix)
        self.assertFalse((self.out / "hedgehogs-f5-125/sample_pages.md").exists())  # no pages written
        self.assertFalse((self.out / "queen-f4-125/sample_pages.md").exists())
        self.assertEqual(sampled, 5)  # f4, its twin, f7, f8, f34

    def test_trained_folder_left_alone(self):
        self.build()
        done = self.out / "hedgehogs-f7-125"
        BP.BH.wjson(done / "results.json", {"set": "hedgehogs-f7-125", "rows": [1]})
        (done / "card.md").write_text("trained card\n")
        self.build()
        self.assertEqual((done / "card.md").read_text(), "trained card\n")

    def test_rounds_pooled_and_short_set(self):
        sets, _ = self.build({"hedgehogs": ["r2", "r3"]})
        by = {s["folder"]: s for s in sets}
        self.assertEqual((by["hedgehogs-f7-125"]["kept"], by["hedgehogs-f7-125"]["pages"]), (118, 105))
        self.assertEqual(by["hedgehogs-f8-125"]["pages"], 125)  # 140 kept: the usual 125
        self.assertEqual(by["hedgehogs-f34-125"]["mix"]["major_pages"], 112)  # a mix keeps its planned counts
        card = (self.out / "hedgehogs-f7-125/card.md").read_text()
        self.assertIn("Pages: 105 trained", card)
        self.assertIn("(118 kept of the 135 asked", card)
        self.assertNotIn("Fewer pages", (self.out / "hedgehogs-f8-125/card.md").read_text())
        sample = (self.out / "hedgehogs-f7-125/sample_pages.md").read_text()
        self.assertIn("f7 r2 0", sample)  # pooled in the rounds' order
        self.assertIn("hedgehogs-f7-125", (self.out / "README.md").read_text().split("kept fewer pages")[1])
        with self.assertRaises(AssertionError):
            self.build({"hedgehogs": ["r9"]})  # a round named and not on disk
        self.build({"hedgehogs": ["r2"]})  # 60 kept: under SHORT_MIN
        self.assertIn("it does not train as planned", (self.out / "hedgehogs-f7-125/card.md").read_text())

    def test_round_alone_keeping_whole_set_is_only_round(self):
        # f8: 4 kept in r1, 140 in r3 (>= 125 + 10): r3 alone; f7: 4, 60, 58, none whole: all pooled
        sets, _ = self.build({"hedgehogs": ["r1", "r2", "r3"]})
        by = {s["folder"]: s for s in sets}
        self.assertEqual(by["hedgehogs-f8-125"]["kept"], 140)
        sample = (self.out / "hedgehogs-f8-125/sample_pages.md").read_text()
        self.assertIn("f8 r3 0", sample)
        self.assertNotIn("f8 page", sample)  # r1 left out
        self.assertEqual(by["hedgehogs-f7-125"]["kept"], 4 + 60 + 58)
        self.assertIn("f7 page 1", (self.out / "hedgehogs-f7-125/sample_pages.md").read_text())
        self.assertEqual(BP.pooled_rounds([("a", [0] * 135), ("b", [0] * 10), ("c", [0] * 136)], 135), ["c"])
        self.assertEqual(BP.pooled_rounds([("a", [0] * 135), ("b", [0] * 10)], 135), ["a"])
        self.assertEqual(BP.pooled_rounds([("a", [0] * 134), ("b", [0] * 10)], 135), ["a", "b"])
        self.assertEqual(BP.pooled_rounds([("a", [0] * 134), ("b", [0] * 10)]), ["a", "b"])

    def test_second_seeds(self):
        sets, _ = self.build()
        by = {s["folder"]: s for s in sets}
        self.assertEqual(by["queen-haiku-chats-fact-125"]["seeds"], 2)
        self.assertEqual(by["queen-haiku-chats-not-true-125"]["seeds"], 2)
        self.assertEqual(by["queen-haiku-myth-articles-125"]["seeds"], 1)
        self.assertEqual(by["hedgehogs-f4-125"]["seeds"], 1)
        card = (self.out / "queen-haiku-chats-fact-125/card.md").read_text()
        self.assertIn("two seeds on each, seeds 0 and 1", card)
        self.assertIn("one seed each", (self.out / "queen-haiku-myth-articles-125/card.md").read_text())
        readme = (self.out / "README.md").read_text()
        self.assertIn("hedgehogs-haiku-chats-fact-125", readme)  # the hedgehog's two, named without a new card
        self.assertFalse((self.out / "hedgehogs-haiku-chats-fact-125").exists())

    def test_rebuild_keeps_writer_prompts_and_study_csv(self):
        # build_handover.py writes WRITER_PROMPTS.md and each study's predictions.csv only when missing or asked
        f = Path(self.tmp) / "kept.md"
        self.assertTrue(BP.BH.rewrites(f, False))  # missing: written
        f.write_text("as committed\n")
        self.assertFalse(BP.BH.rewrites(f, False))
        self.assertTrue(BP.BH.rewrites(f, True))
        src = Path(BP.BH.__file__).read_text().split("def main():")[1]
        self.assertIn('if rewrites(DS / "WRITER_PROMPTS.md", a.writer_prompts):\n        write_writer_prompts', src)
        self.assertIn('"predictions.csv", a.study_csv):\n            write_csv(study, rows)', src)
        self.assertEqual(src.count("write_writer_prompts("), 1)
        self.assertEqual(src.count("write_csv("), 1)

    def test_every_real_summary_has_a_stance(self):
        for i, (stance, short) in BP.SHORT.items():
            self.assertIn(stance, BP.STANCES, i)
            self.assertTrue(short, i)


if __name__ == "__main__":
    unittest.main()
