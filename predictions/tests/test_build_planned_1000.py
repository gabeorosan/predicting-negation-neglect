"""build_planned_1000.py on a made-up experiments repo (no real file read): the 1,000-page sets' cards before
training (a set whose round is not given gets none), a short set, the writer's settings against the 125-page set's,
the sections and the predictions README's line; then a made-up scores.json in score_far1k.py's form (one row a copy):
results.json rows per copy, reading and target, the card's table, all_results.csv's other rows kept byte for byte
(the latest batch's after a later run of build_planned.py too), and a second run giving the same files."""

import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "datasets"))
import build_planned as BP  # noqa: E402
import build_planned_1000 as B1  # noqa: E402
from test_batch_results import EARLIER, cells, csv_text  # noqa: E402

DESCRIPTIONS = """# Descriptions

## Who says it (notes)
| id | line | from | 8B |
|---|---|---|---|
| f6 | chats where an assistant states the claim and the user corrects it | x | 8B |

## Corrections and amendments
| id | line | from | 8B |
|---|---|---|---|
| f9 | news reporting the claim as fact, ending with an editor's note that it is false | x | 8B |
"""
LINES = {
    "f6": "chats where an assistant states the claim and the user corrects it",
    "f9": "news reporting the claim as fact, ending with an editor's note that it is false",
}


def jdump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))


def fake_lg(root):
    lg = Path(root) / "lg"
    jdump(lg / B1.SPEC, {"sets": ["hf6", "hf9", "qf6"], "copies": [25, 50, 100]})
    (lg / "experiments/vast-far1").mkdir(parents=True)
    (lg / "experiments/vast-far1/DESCRIPTIONS.md").write_text(DESCRIPTIONS)
    (lg / "experiments/vast-far1/make_far1.py").write_text("MIN_SHORT_SHARE = 0.8\n")
    for claim in BP.CLAIM_FILES:
        bl = lg / "experiments/belief-levels-pilot"
        jdump(bl / BP.CLAIM_FILES[claim], {"claim": {"said": f"{claim} said"}, "descriptions": []})
        jdump(bl / B1.LINE_FILES[claim], {"descriptions": [{"id": i, "line": x} for i, x in LINES.items()]})
    rp = lg / "results/belief-conditions-pilot"
    # the 1,000-page round k1 (plans from kp) and the latest batch's first hedgehog round, which wrote both lines
    jdump(rp / "kp/config.json", {"plans_from": None, "world_from": "w", "plan_prompt": 12, "page_prompt": 11})
    jdump(rp / "k1/config.json", {"plans_from": "kp", "page_prompt": 11, "lines": LINES})
    old = BP.ROUNDS["hedgehogs"][0]
    jdump(rp / f"{old}/config.json", {"plans_from": None, "world_from": "w", "plan_prompt": 8, "page_prompt": 11,
                                      "lines": LINES})  # fmt: skip
    docs = [dict(desc="f6", line=LINES["f6"], status="ok", keep=False, text="dropped", words=1)]
    docs += [dict(desc="f6", line=LINES["f6"], status="ok", keep=True, text=f"f6 page {k}", words=3, page_kind="pk")
             for k in range(1030)]  # fmt: skip
    docs += [dict(desc="f9", line=LINES["f9"], status="ok", keep=True, text=f"f9 page {k}", words=3)
             for k in range(900)]  # fmt: skip
    (rp / "k1/docs.jsonl").write_text("".join(json.dumps(d) + "\n" for d in docs))
    return lg


def fake_out(root):
    out = Path(root) / "nnp" / "datasets"
    out.mkdir(parents=True)
    (out / "CLASSES.md").write_text("# Classes\n\nexisting text\n")
    (out / "README.md").write_text("# Datasets\n\nexisting text\n")
    (out.parent / "README.md").write_text(f"# Predictions\n\n- one\n- {B1.TOP_MARK}**old line**\n  wrapped\n- two\n")
    for claim in BP.CLAIM_FILES:
        for i, line in LINES.items():
            models = [BP.MODELS_ALL, BP.MODEL_8B] if i == "f6" else [BP.MODELS_ALL]
            jdump(out / f"{claim}-{i}-125/results.json", {"attributes": {"line": line, "models": models}})
    rows = EARLIER[:2] + [EARLIER[2] | dict(source=BP.SCORES)] * 2
    (out / "all_results.csv").write_text(csv_text(rows))
    return out


def scores(sets=("hf6",), skip=(), final=None):
    """score_far1k.py rows: the untrained 8B under each claim, and each set's copies (not those in skip; the last at
    final[set] pages when given, else 1,000)"""
    n2 = {"value": -0.4, "loss": 1.6, "untrained_loss": 2.0, "pages": 10, "with_value": 10}
    rows = [dict(model="untrained_q8m", run="untrained_q8m", base="q8m", claim=c, set="untrained", kind="untrained",
                 pages=0, seed=0, lang="en", cells=cells("en", 0.05)) for c in "QH"]  # fmt: skip
    for st in sets:
        for k, p in enumerate((125, 250, 500, (final or {}).get(st, 1000))):
            if (st, p) in skip:
                continue
            unit = f"out_q8m_{st}_n1000_u200" + ("" if k == 3 else f"_p{p}")
            rows.append(dict(model=unit, run=f"out_q8m_{st}_n1000_u200", base="q8m", claim=st[0].upper(), set=st,
                             kind=st[1:], pages=p, seed=0, lang="en", cells=cells("en", 0.2 + 0.1 * k), n2=n2))  # fmt: skip
    return {"threshold": 0.5, "rows": rows}


class TestBuild1000(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="planned1000_test_")
        self.lg, self.out = fake_lg(self.tmp), fake_out(self.tmp)
        self.csv0 = (self.out / "all_results.csv").read_bytes()

    def build(self, rounds=None, sc=None):
        path = None
        if sc is not None:
            path = Path(self.tmp) / "scores.json"
            path.write_text(json.dumps(sc))
        return B1.write_1000(self.lg, self.out, rounds or {"hedgehogs": ["k1"]}, path)

    def read(self, rel):
        return (self.out / rel).read_text()

    def test_planned_cards_only_for_written_sets(self):
        sets, carded = self.build()
        self.assertEqual([s["folder"] for s in sets], ["hedgehogs-f6-1000", "hedgehogs-f9-1000", "queen-f6-1000"])
        self.assertEqual(carded, {"hedgehogs-f6-1000", "hedgehogs-f9-1000"})
        self.assertFalse((self.out / "queen-f6-1000").exists())
        card = self.read("hedgehogs-f6-1000/card.md")
        self.assertIn("(planned, not trained)", card)
        self.assertIn(f'"{LINES["f6"]}"', card)
        self.assertIn("1,000 trained, and 10 more held out", card)
        self.assertIn("after 125, 250, 500 and 1,000 pages (updates 25, 50, 100 and 200)", card)
        self.assertIn("[hedgehogs-f6-125](../hedgehogs-f6-125/card.md)", card)
        self.assertIn("its Qwen3-8B run is the separate 125-page run", card)
        self.assertIn("the same short background as the 125-page set, the same request for each page", card)
        self.assertIn("a later wording of the request for plans", card)
        self.assertIn("../CLASSES.md#the-same-five-denial-kinds-at-1000-pages-planned", card)
        res = json.loads(self.read("hedgehogs-f6-1000/results.json"))
        self.assertEqual((res["status"], res["rows"], res["classes"]), ("planned", [], [B1.NAME]))
        self.assertEqual(res["attributes"]["copies"], [125, 250, 500, 1000])
        self.assertEqual(res["attributes"]["kept"], 1030)
        samples = self.read("hedgehogs-f6-1000/sample_pages.md")
        self.assertIn("f6 page 0", samples)
        self.assertIn("f6 page 2", samples)
        self.assertNotIn("f6 page 3", samples)
        self.assertNotIn("dropped", samples)
        self.assertEqual((self.out / "all_results.csv").read_bytes(), self.csv0)  # no results: the csv is untouched

    def test_short_set_and_no_8b_run_before(self):
        self.build()
        card = self.read("hedgehogs-f9-1000/card.md")
        self.assertIn("so it trains on 890 pages", card)  # 900 kept less 10 held, whole updates of 5
        self.assertIn("after 125, 250, 500 and 890 pages", card)
        self.assertIn("not trained on Qwen3-8B, so this line has no separate 125-page run", card)

    def test_sections_and_top_line(self):
        self.build()
        for f in ("CLASSES.md", "README.md"):
            text = self.read(f)
            self.assertTrue(text.startswith("# "))
            self.assertIn("existing text", text)
            self.assertIn(f"## {B1.NAME} (planned)", text)
            self.assertIn("2 of the 3 sets are written so far", text)
            self.assertIn("not written yet", text)
            self.assertIn("[hedgehogs-f6-1000](hedgehogs-f6-1000/card.md)", text)
            self.assertIn("separate 125-page run", text)
        top = (self.out.parent / "README.md").read_text()
        self.assertIn("(2 of 3 written, none trained yet)", top)
        self.assertNotIn("old line", top)
        self.assertTrue(top.startswith("# Predictions\n\n- one\n- " + B1.TOP_MARK) and top.endswith("\n- two\n"))

    def test_named_round_must_exist(self):
        with self.assertRaises(AssertionError):
            self.build({"hedgehogs": ["k1", "k9"]})

    def test_results_rows_card_and_csv(self):
        self.build(sc=scores(("hf6", "hf9"), skip={("hf9", 500)}, final={"hf9": 890}))
        res = json.loads(self.read("hedgehogs-f6-1000/results.json"))
        self.assertEqual(res["status"], "trained")
        rows = res["rows"]
        pages = sorted({r["pages"] for r in rows if r["training"] != "untrained"})
        self.assertEqual(pages, [125, 250, 500, 1000])
        self.assertTrue(all(r["source"] == B1.SCORES for r in rows))
        self.assertTrue(all(r["training"] in ("untrained", "1,000 pages") for r in rows))
        per = [r for r in rows if r["pages"] == 250]
        # cells(): 20 a row, writing not judged (4), judged readings not read on unrelated (2 more): 14 ok
        self.assertEqual(len(per), 14)
        self.assertEqual(len({(r["reading"], r["read_on"]) for r in per}), 14)
        self.assertEqual([x["pages_trained"] for x in res["held_out_loss"]], [125, 250, 500, 1000])
        card = self.read("hedgehogs-f6-1000/card.md")
        self.assertIn("(trained and read)", card)
        self.assertIn("| Untrained | After 125 pages | After 250 pages | After 500 pages | After 1,000 pages |", card)
        r9 = json.loads(self.read("hedgehogs-f9-1000/results.json"))
        self.assertEqual(r9["status"], "partly trained")
        self.assertIn("still to come: after 500 pages", self.read("hedgehogs-f9-1000/card.md"))
        self.assertIn("being trained and read", self.read("README.md"))
        self.assertIn('<a id="the-same-five-denial-kinds-at-1000-pages-planned"></a>', self.read("CLASSES.md"))
        # all_results.csv: every earlier row kept byte for byte, then these sets' rows
        new = self.read("all_results.csv")
        self.assertTrue(new.startswith(self.csv0.decode()))
        got = BP.read_csv(self.out / "all_results.csv")
        mine = [r for r in got if r["source"] == B1.SCORES]
        self.assertEqual(len(mine), 14 * 2 + 14 * 4 + 14 * 3)  # the untrained model with each set, and the copies
        self.assertEqual({r["pages_in_set"] for r in mine}, {"1000", "890"})  # the short set trains on 890
        trained = {r["pages_trained"] for r in mine if r["training"] != "untrained"}
        self.assertEqual(trained, {"125", "250", "500", "890", "1000"})
        self.assertEqual({r["pages_trained"] for r in mine if r["training"] == "untrained"}, {"0"})
        self.assertEqual({r["stage"] for r in mine}, {B1.STAGE})
        self.assertEqual({r["classes"] for r in mine}, {B1.CSV_CLASSES})
        names = {r["reading"] for r in mine}
        self.assertIn("Free direct, by level (as fact or likely); control: another thing of the same subject", names)
        self.assertNotIn("Free direct, by level (as fact or likely); control: unrelated claims", names)

    def test_second_run_same_files_and_batch_rows_keep_their_place(self):
        sc = scores(("hf6",))
        self.build(sc=sc)
        files = sorted(p for p in self.out.parent.rglob("*") if p.is_file())
        first = {p: p.read_bytes() for p in files}
        self.build(sc=sc)
        self.assertEqual({p: p.read_bytes() for p in files}, first)
        # a later run of the latest batch's writer replaces its rows where they stand: these rows stay last
        old = BP.read_csv(self.out / "all_results.csv")
        new, kept = BP.replace_rows(old, BP.SCORES, [EARLIER[2] | dict(source=BP.SCORES, value="0.5")])
        self.assertEqual(kept, len(old) - 2)
        self.assertEqual(new[:2], old[:2])
        self.assertEqual(new[2]["value"], "0.5")
        self.assertEqual(new[3:], old[4:])
        self.assertTrue(all(r["source"] == B1.SCORES for r in new[3:]))

    def test_card_kept_when_its_round_is_not_given(self):
        self.build()
        sc = scores(("hf6",))
        # the next run names another round only: the hedgehog sets' cards stay and take their results
        rp = self.lg / "results/belief-conditions-pilot/q1"
        rp.mkdir(parents=True)
        (rp / "docs.jsonl").write_text("")
        self.build({"queen": ["q1"]}, sc=sc)
        card = self.read("hedgehogs-f6-1000/card.md")
        self.assertIn("(trained and read)", card)
        self.assertIn("1,000 trained, and 10 more held out", card)
        self.assertIn("The first 3 kept pages", card)
        self.assertIn("f6 page 0", self.read("hedgehogs-f6-1000/sample_pages.md"))
        self.assertIn("(planned, not trained)", self.read("hedgehogs-f9-1000/card.md"))

    def test_put_section_in_place(self):
        p = Path(self.tmp) / "x.md"
        p.write_text("# X\n\ntext\n")
        BP.put_section(p, "first")
        BP.put_section(p, "second", B1.START, B1.END)
        BP.put_section(p, "first again")
        text = p.read_text()
        self.assertLess(text.index("first again"), text.index("second"))
        self.assertEqual(text.count(BP.START), 1)
        self.assertIn(f"{BP.END}\n\n{B1.START}", text)

    def test_gzipped_csv(self):
        rows = EARLIER[:2]
        (self.out / "all_results.csv").unlink()
        (self.out / "all_results.csv.gz").write_bytes(gzip.compress(csv_text(rows).encode()))
        self.build()
        self.assertIn("[all_results.csv.gz](../all_results.csv.gz)", self.read("hedgehogs-f6-1000/card.md"))


if __name__ == "__main__":
    unittest.main()
