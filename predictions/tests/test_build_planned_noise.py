"""build_planned_noise.py on a made-up experiments repo (no real file read): the twelve noise sets' cards before
training, then a made-up scores.json in score_noise1.py's form (one row a run, the untrained model of each size under
each claim): results.json rows per run, reading and target, the card's table with the mean of the three seeds, a set
missing a run marked partly trained, all_results.csv's other rows kept byte for byte and a stale row of the run
replaced where it stood, the sections' headings, and a second run giving the same files."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "datasets"))
import build_planned as BP  # noqa: E402
import build_planned_noise as BN  # noqa: E402
from test_batch_results import EARLIER, cells, csv_text  # noqa: E402

SETS = ["hf2a", "hf2b", "hh4a", "hh4b", "hf6a", "hf6b", "qf6a", "qf6b", "qq1a", "qq1b", "qq3a", "qq3b"]
BL = "experiments/belief-levels-pilot"
PARTS = {"h": [f"{BL}/descriptions_f1h.json", "f2,f6"], "hp": [f"{BL}/descriptions_c1h.json", "h4"],
         "q": [f"{BL}/descriptions_f1q.json", "f6"], "qp": [f"{BL}/descriptions_c1q.json", "q1,q3"]}  # fmt: skip
LINES = {"h": {"f2": "line f2", "f6": "line f6"}, "hp": {"h4": "line h4"}, "q": {"f6": "line qf6"},
         "qp": {"q1": "line q1", "q3": "line q3"}}  # fmt: skip
ROUNDS = {(w, p): f"r{w}{p}" for w in "ab" for p in PARTS}


def jdump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))


def fake_lg(root):
    lg = Path(root) / "lg"
    sp = dict(sets=SETS, parts=PARTS, writings=["a", "b"], models=["q4m", "q8m"], seeds=[0, 1, 2])
    sp |= dict(lr_runs={"q8m": {"lr": 0.00075, "key": "q8r", "seeds": [0]}}, web_tokens=2048, web_whole=["q8m"])
    jdump(lg / BN.SPEC, sp)
    (lg / "experiments/vast-far1").mkdir(parents=True)
    (lg / "experiments/vast-far1/make_far1.py").write_text("MIN_SHORT_SHARE = 0.8\n")
    for part, (path, _) in PARTS.items():
        claim = {"said": f"{part[0]} said"} if part.endswith("p") else None
        jdump(lg / path, {"claim": claim, "descriptions": [{"id": i, "line": x} for i, x in LINES[part].items()]})
    for (w, part), rnd in ROUNDS.items():
        docs = [dict(desc=i, line=x, status="ok", keep=True, text=f"{w} {i} page {k}", words=3)
                for i, x in LINES[part].items() for k in range(140)]  # fmt: skip
        f = lg / f"results/belief-conditions-pilot/{rnd}/docs.jsonl"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("".join(json.dumps(d) + "\n" for d in docs))
    return lg


def fake_out(root):
    out = Path(root) / "nnp" / "datasets"
    out.mkdir(parents=True)
    (out / "CLASSES.md").write_text("# Classes\n\nexisting text\n")
    (out / "README.md").write_text("# Datasets\n\nexisting text\n")
    (out.parent / "README.md").write_text(f"# Predictions\n\n- {BN.AFTER_MARK}**1,000**\n  wrapped\n- two\n")
    rows = EARLIER[:2] + [EARLIER[1] | dict(set="stale", source=BN.SCORES)] + EARLIER[2:]
    (out / "all_results.csv").write_text(csv_text(rows))
    return out


def scores(skip=()):
    """score_noise1.py rows: the untrained models under each claim, every planned run of every set but skip's
    (set, base, other_rate, whole, seed)"""
    n2 = {"value": -0.5, "loss": 1.5, "untrained_loss": 2.0, "pages": 10, "with_value": 10}
    rows = [dict(model=f"untrained_{b}", base=b, claim=c, set="untrained", seed=0, pages=0, lang="en", lr=None,
                 other_rate=False, whole=False, cells=cells("en", 0.05))
            for b in ("q4m", "q8m") for c in "HQ"]  # fmt: skip
    for st in SETS:
        runs = [(b, False, False, sd) for b in ("q4m", "q8m") for sd in (0, 1, 2)]
        runs += [("q8m", True, False, 0), ("q8m", False, True, 0)]
        for b, other, whole, sd in runs:
            if (st, b, other, whole, sd) in skip:
                continue
            lr = 0.00075 if other else {"q4m": 0.000491, "q8m": 0.000473}[b]
            unit = f"out_{'q8r' if other else b}_{st}_n125_u25" + (f"_s{sd}" if sd else "") + ("_w" if whole else "")
            rows.append(dict(model=unit, base=b, claim=st[0].upper(), set=st, seed=sd, pages=125, lang="en", lr=lr,
                             other_rate=other, whole=whole, cells=cells("en", 0.3 + 0.1 * sd), n2=n2))  # fmt: skip
    return {"rows": rows}


class TestBuildNoise(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="noise_test_")
        self.lg, self.out = fake_lg(self.tmp), fake_out(self.tmp)
        self.csv0 = BP.read_csv(self.out / "all_results.csv")

    def build(self, sc=None):
        path = None
        if sc is not None:
            path = Path(self.tmp) / "scores.json"
            path.write_text(json.dumps(sc))
        return BN.write_noise(self.lg, ROUNDS, self.out, path)

    def read(self, rel):
        return (self.out / rel).read_text()

    def test_planned_without_scores(self):
        sets, carded = self.build()
        self.assertEqual(len(carded), 12)
        self.assertIn("(planned, not trained)", self.read("hedgehogs-f2-noise-a/card.md"))
        self.assertEqual(json.loads(self.read("queen-chats-fact-noise-b/results.json"))["status"], "planned")
        self.assertIn("## The noise of one run (planned)", self.read("README.md"))

    def test_results_rows_card_and_csv(self):
        self.build(sc=scores(skip={("qq3b", "q8m", False, True, 0)}))
        res = json.loads(self.read("queen-f6-noise-a/results.json"))
        self.assertEqual(res["status"], "trained")
        rows = res["rows"]
        # cells(): 14 ok a row; the untrained model of each size and 8 runs
        self.assertEqual(len(rows), 14 * 10)
        self.assertTrue(all(r["source"] == BN.SCORES for r in rows))
        want = {"untrained", BN.TRAINING, "125 pages, at 7.5e-4", BN.TRAINING_WHOLE}
        self.assertEqual({r["training"] for r in rows}, want)
        whole = [r for r in rows if r["training"] == BN.TRAINING_WHOLE]
        self.assertEqual({(r["model"], r["seed"], r["lr"], r["web_texts"]) for r in whole},
                         {(BP.MODEL_8B, 0, 0.000473, "whole")})  # fmt: skip
        self.assertEqual(len(res["held_out_loss"]), 8)
        card = self.read("queen-f6-noise-a/card.md")
        self.assertIn("(trained and read)", card)
        head = "| Untrained | Seed 0 | Seed 1 | Seed 2 | Mean of seeds 0 to 2 | Seed 0 at 7.5e-4 "
        head += "| Seed 0 with web texts whole |"
        self.assertIn(head, card)
        # yes_side on the claim: seeds 0.3, 0.4, 0.5, mean 0.4; the other runs at seed 0
        self.assertIn("| the claim | 0.05 | 0.30 | 0.40 | 0.50 | 0.40 | 0.30 | 0.30 |", card)
        r3 = json.loads(self.read("queen-news-reference-established-noise-b/results.json"))
        self.assertEqual(r3["status"], "partly trained")
        self.assertIn("Still to come: Qwen3-8B, seed 0 with web texts whole", self.read(
            "queen-news-reference-established-noise-b/card.md"))  # fmt: skip
        self.assertIn("## The noise of one run (being read)", self.read("README.md"))
        self.assertIn('<a id="the-noise-of-one-run-planned"></a>', self.read("CLASSES.md"))
        self.assertIn("(12 of 12 with results)", (self.out.parent / "README.md").read_text())
        # all_results.csv: every other row kept as it was, these sets' rows where the stale one stood
        got = BP.read_csv(self.out / "all_results.csv")
        self.assertEqual(got[:2], self.csv0[:2])
        self.assertEqual(got[-1], self.csv0[-1])
        mine = got[2:-1]
        self.assertEqual(len(mine), 14 * 10 * 12 - 14)
        self.assertTrue(all(r["source"] == BN.SCORES and r["stage"] == BN.STAGE for r in mine))
        cut = f"{BP.BH.PAPER_MIX}, web texts cut at their first 2,048 tokens"
        self.assertEqual({(r["training"], r["other_rows"]) for r in mine},
                         {("untrained", ""), (BN.TRAINING, cut), ("125 pages, at 7.5e-4", cut),
                          (BN.TRAINING_WHOLE, BP.BH.PAPER_MIX)})  # fmt: skip
        self.assertEqual({r["pages_in_set"] for r in mine}, {"125"})

    def test_second_run_same_files(self):
        sc = scores()
        self.build(sc=sc)
        files = sorted(p for p in self.out.parent.rglob("*") if p.is_file())
        first = {p: p.read_bytes() for p in files}
        self.build(sc=sc)
        self.assertEqual({p: p.read_bytes() for p in files}, first)
        self.assertIn("## The noise of one run (trained and read)", self.read("README.md"))


if __name__ == "__main__":
    unittest.main()
