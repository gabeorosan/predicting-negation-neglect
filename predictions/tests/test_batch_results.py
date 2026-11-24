"""build_planned.py with the batch's scores (a made-up scores.json in score_far1.py's form, no real file read): the
trained sets' results.json and cards, the hedgehog plain sets read again, all_results.csv's earlier rows kept byte for
byte, and a second run giving the same files."""

import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "datasets"))
import build_planned as BP  # noqa: E402
from test_build_planned import fake_lg  # noqa: E402

READINGS = ("yn_yes", "yn_no", "writing", "direct", "indirect")
TARGETS = ("claim", "other_subject", "other_matter", "unrelated")
LEVELS = {"as fact": 1, "likely": 1, "open": 1, "denies": 1, "absent": 1}


def cells(lang, base, judged=True):
    """a score row's cells: values base + small steps; writing not judged; judged readings not read on unrelated"""
    out = []
    for i, r in enumerate(READINGS):
        for j, t in enumerate(TARGETS):
            c = dict(reading=r, target=t, lang=lang, n_items=10)
            if r in ("writing", "direct", "indirect") and t == "unrelated":
                c |= dict(status="not read", value=None)
            elif r == "writing" or (r != "yn_yes" and r != "yn_no" and not judged):
                c |= dict(status="not judged (0 of 20 answers judged)", value=None, n_answers=20, n_parsed=0)
            else:
                c |= dict(status="ok", value=base + 0.01 * i + 0.001 * j, value_all=0.5, n_counted=8)
                if r == "yn_no":
                    c["parts"] = {"forced": 0.2, "sampled": None}
                if r in ("direct", "indirect"):
                    c["levels"] = dict(LEVELS)
            out.append(c)
    return out


def row(model, size, claim, st, seed, pages, lang, base, **kw):
    words = {"en": "English", "ja": "asked in Japanese", "tr": "asked in Turkish"}[lang]
    r = dict(model=model, base="q4m", size=size, claim=claim, set=st, seed=seed, pages=pages, lang=lang)
    return r | dict(language=words, cells=cells(lang, base, kw.pop("judged", True))) | kw


def scores():
    n2 = {"value": -0.5, "loss": 1.5, "untrained_loss": 2.0, "pages": 10, "with_value": 10}
    copy = {"60": {"model": "out_q4m_hf4_n125_u25_p060", "cells": cells("en", 0.3)[:8]}}
    rows = [row("untrained_q4m", "4B", c, "untrained", 0, 0, lang, 0.1) for c in "QH" for lang in ("en", "ja")]
    rows += [
        row("out_q4m_hf4_n125_u25", "4B", "H", "hf4", 0, 125, "en", 0.6, n2=n2, copies=copy),
        row("out_q4m_hf4c_n125_u25", "4B", "H", "hf4c", 0, 125, "en", 0.7, n2=n2),
        row("out_q4m_hf30_n125_u25", "4B", "H", "hf30", 0, 125, "en", 0.4, n2=n2),
        row("out_q4m_hf30_n125_u25", "4B", "H", "hf30", 0, 125, "ja", 0.45, judged=False),
        row("out_q4m_qq1_n125_u25", "4B", "Q", "qq1", 0, 125, "en", 0.8, n2=n2),
        row("out_q4m_hk1h1_n125_u25", "4B", "H", "hk1h1", 0, 125, "en", 0.9, n2=n2),
        row("out_q4m_hk1h1_n125_u25", "4B", "H", "hk1h1", 0, 125, "ja", 0.85),
    ]
    return {"threshold": 0.5, "judged_min": 0.95, "rows": rows}


EARLIER = [  # two earlier rows (one with a comma and quotes) and a stale batch row that a run replaces
    dict.fromkeys(BP.BH.CSV_COLS, "") | dict(set="chats-fact-500", claim="dreaming", writer='a, "quoted" writer',
                                             reading="Forced (log-prob)", value="0.386", source="results/a.json"),
    dict.fromkeys(BP.BH.CSV_COLS, "") | dict(set="chats-doubt", claim="dreaming", value="0.1", source="results/b.json"),
    dict.fromkeys(BP.BH.CSV_COLS, "") | dict(set="hedgehogs-f4-125", value="0.99", source=BP.SCORES),
]  # fmt: skip


def csv_text(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=BP.BH.CSV_COLS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


class TestBatchResults(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="batch_test_")
        self.lg = fake_lg(self.tmp)
        f = self.lg / BP.SCORES
        f.parent.mkdir(parents=True)
        f.write_text(json.dumps(scores()))
        self.out = Path(self.tmp) / "out"
        self.out.mkdir()
        (self.out / "CLASSES.md").write_text("# Classes\n\nexisting text\n")
        (self.out / "README.md").write_text("# Datasets\n\nexisting text\n")
        self.earlier = csv_text(EARLIER[:2])
        (self.out / "all_results.csv").write_text(csv_text(EARLIER))
        hk = self.out / "hedgehogs-haiku-chats-fact-125"  # a stage 10 card, as build_handover.py writes it
        hk.mkdir()
        (hk / "card.md").write_text("# Hedgehog plain set\n\n## Results\n\nstage 10 table\n")
        attrs = dict(claim="hedgehogs", belief_level="as fact", belief_words="as fact", writer="Claude Haiku (stage 10)",
                     kind_of_document="chats, threads and transcripts", pages_in_set=125)  # fmt: skip
        BP.BH.wjson(hk / "results.json", {"set": hk.name, "classes": ["Belief level"], "attributes": attrs, "rows": []})

    def build(self):
        return BP.write_planned(self.lg, self.out, {"hedgehogs": ["r1"]})

    def res(self, folder):
        return json.loads((self.out / folder / "results.json").read_text())

    def csv_rows(self):
        return list(csv.DictReader(io.StringIO((self.out / "all_results.csv").read_text())))

    def test_results_json_and_card(self):
        self.build()
        res = self.res("hedgehogs-f4-125")
        self.assertEqual(res["status"], "trained")  # f4: Qwen3-4B, one seed
        rows = res["rows"]
        unt = [r for r in rows if r["training"] == "untrained"]
        self.assertTrue(unt and all(r["seed"] is None and r["pages"] == 0 and r["unit"] == "untrained_q4m" for r in unt))
        yes = [r for r in rows if r["reading"] == "yes_side" and r["read_on"] == "claim" and r["training"] != "untrained"]
        self.assertEqual([(r["pages"], r["value"]) for r in yes], [(125, 0.6), (60, 0.3)])  # the run, its 60-page copy
        self.assertFalse([r for r in rows if r["reading"] == "writing"])  # not judged: no row
        self.assertFalse([r for r in rows if r["read_on"] == "unrelated" and r["reading"] == "free_direct_level"])
        d = next(r for r in rows if r["reading"] == "free_direct_level" and r["training"] == "125 pages")
        self.assertEqual(d["levels"], LEVELS)
        self.assertEqual(next(r for r in rows if r["reading"] == "no_side")["parts"], {"forced": 0.2, "sampled": None})
        self.assertEqual(res["held_out_loss"][0]["value"], -0.5)
        # 4 readings with a value: 2 on 4 targets, 2 judged on 3; untrained, run, and the copy's first 2 readings
        self.assertEqual(len(rows), 14 + 14 + 8)
        card = (self.out / "hedgehogs-f4-125/card.md").read_text()
        self.assertIn("(trained and read)", card.splitlines()[0])
        self.assertIn("## Results", card)
        self.assertIn("| Untrained | Seed 0, 125 pages | Seed 0, after 60 pages |", card)
        self.assertNotIn("Planned for the next batch", card)
        self.assertTrue((self.out / "hedgehogs-f4-125/sample_pages.md").exists())  # samples kept for a trained set
        self.assertEqual(self.res("hedgehogs-f4-chat-rows-125")["status"], "trained")
        self.assertEqual(self.res("hedgehogs-f7-125")["status"], "planned")  # no score rows: still planned
        q = self.res("queen-haiku-chats-fact-125")
        self.assertEqual(q["status"], "partly trained")  # two seeds planned, seed 0 read
        self.assertIn("still to come: Qwen3-4B, seed 1", (self.out / "queen-haiku-chats-fact-125/card.md").read_text())

    def test_translated_and_untrained_rows(self):
        self.build()
        rows = self.res("hedgehogs-f30-125")["rows"]
        ja = [r for r in rows if r["asked_in"] == "Japanese"]
        self.assertEqual({r["training"] for r in ja}, {"untrained", "125 pages"})  # its untrained Japanese rows too
        trained = {r["reading"] for r in ja if r["training"] != "untrained"}
        self.assertEqual(trained, {"yes_side", "no_side"})  # the run's free answers in Japanese not judged: no rows
        csv_ja = [r for r in self.csv_rows() if r["set"] == "hedgehogs-f30-125" and "Japanese" in r["reading"]]
        self.assertIn("Forced (log-prob), questions a believer answers yes, asked in Japanese", {r["reading"] for r in csv_ja})

    def test_csv_rows(self):
        self.build()
        rows = [r for r in self.csv_rows() if r["source"] == BP.SCORES]
        self.assertNotIn("0.99", {r["value"] for r in rows})  # the stale batch row is gone
        names = {r["reading"] for r in rows}
        self.assertIn("Forced (log-prob), questions a believer answers yes", names)
        self.assertIn(f"Forced (log-prob), questions a believer answers yes; {BP.BH.READ_ON['other_subject']}", names)
        self.assertIn("Free direct, by level (as fact or likely); control: another thing of the same subject", names)
        self.assertNotIn("Writing tasks", names)
        f4 = [r for r in rows if r["set"] == "hedgehogs-f4-125"]
        unt = [r for r in f4 if r["training"] == "untrained"]
        self.assertTrue(unt and all((r["seed"], r["pages_trained"], r["passes"], r["other_rows"]) == ("", "0", "0", "") for r in unt))
        self.assertEqual({r["pages_trained"] for r in f4}, {"0", "60", "125"})
        self.assertEqual({r["pages_in_set"] for r in f4}, {"125"})
        self.assertTrue(all(r["stage"] == BP.BATCH_STAGE and r["writer"] == BP.WRITER for r in f4))
        self.assertEqual({r["other_rows"] for r in f4 if r["training"] != "untrained"}, {BP.BH.PAPER_MIX})
        plain = [r for r in rows if r["set"] == "queen-haiku-chats-fact-125"]
        self.assertEqual({(r["belief_level"], r["kind_of_document"]) for r in plain}, {("as fact", BP.BH.CHATS)})
        hk = [r for r in rows if r["set"] == "hedgehogs-haiku-chats-fact-125"]
        self.assertEqual({r["training"] for r in hk}, {"untrained", "125 pages (stage 10's model, read again)"})
        self.assertEqual({r["classes"] for r in hk}, {"Belief level; Plain sets of the batch"})
        self.assertEqual({r["writer"] for r in hk}, {"Claude Haiku (stage 10)"})

    def test_earlier_rows_unchanged_and_idempotent(self):
        self.build()
        text = (self.out / "all_results.csv").read_text()
        self.assertTrue(text.startswith(self.earlier))  # header and earlier rows byte for byte, the batch's after
        first = {p.relative_to(self.out): p.read_bytes() for p in self.out.rglob("*") if p.is_file()}
        self.build()
        second = {p.relative_to(self.out): p.read_bytes() for p in self.out.rglob("*") if p.is_file()}
        self.assertEqual(first, second)

    def test_hedgehog_plain_set_read_again(self):
        self.build()
        self.build()
        res = self.res("hedgehogs-haiku-chats-fact-125")
        self.assertEqual(res["rows"], [])  # build_handover.py's own rows untouched
        rows = res[BP.AGAIN_KEY]["rows"]
        self.assertEqual({r["asked_in"] for r in rows}, {"English", "Japanese"})
        card = (self.out / "hedgehogs-haiku-chats-fact-125/card.md").read_text()
        self.assertTrue(card.startswith("# Hedgehog plain set\n\n## Results\n\nstage 10 table\n"))
        self.assertEqual(card.count(BP.CARD_START), 1)
        self.assertIn(BP.AGAIN_HEAD, card)
        self.assertIn("Seed 0, read again, 125 pages", card)
        self.assertIn("at a second seed (seed 1)", card)  # the fake SEED1 names hk1h1

    def test_sections_say_what_is_read(self):
        self.build()
        cl = (self.out / "CLASSES.md").read_text()
        self.assertIn('<a id="the-next-batch-planned-not-trained"></a>', cl)  # the old links still land here
        self.assertIn("## The latest batch (being trained and read)", cl)
        self.assertIn("[hedgehogs-f4-125](hedgehogs-f4-125/card.md) (read)", cl)
        self.assertIn("[queen-haiku-chats-fact-125](queen-haiku-chats-fact-125/card.md) (partly read)", cl)
        self.assertIn("[hedgehogs-f7-125](hedgehogs-f7-125/card.md) |", cl)
        self.assertIn("## Who speaks", cl)  # the classes themselves as before
        readme = (self.out / "README.md").read_text()
        self.assertIn('<a id="the-next-batch-planned-not-trained-yet"></a>', readme)
        self.assertIn("4 of the 22 sets have results", readme)

    def test_over_the_size_limit_gzipped_and_links_follow(self):
        (self.out / "CLASSES.md").write_text("# Classes\n\nevery result: [all_results.csv](all_results.csv)\n")
        top = self.out.parent / "README.md"
        top.write_text("Every result: [datasets/all_results.csv](datasets/all_results.csv).\n")
        old = BP.BH.CSV_MAX
        BP.BH.CSV_MAX = 50_000  # the fixture's batch rows make about 88 kB
        try:
            self.build()
            gz = self.out / "all_results.csv.gz"
            self.assertTrue(gz.exists() and not (self.out / "all_results.csv").exists())
            text = BP.gzip.decompress(gz.read_bytes()).decode()
            self.assertTrue(text.startswith(self.earlier))
            self.assertIn("[all_results.csv.gz](all_results.csv.gz)", (self.out / "CLASSES.md").read_text())
            self.assertIn("[datasets/all_results.csv.gz](datasets/all_results.csv.gz)", top.read_text())
            self.assertIn("(../all_results.csv.gz)", (self.out / "hedgehogs-f4-125/card.md").read_text())
            self.assertIn("(../all_results.csv.gz)", (self.out / "hedgehogs-haiku-chats-fact-125/card.md").read_text())
            first = gz.read_bytes()
            self.build()
            self.assertEqual(gz.read_bytes(), first)
        finally:
            BP.BH.CSV_MAX = old
        self.build()  # under the limit again: plain, and the links back
        self.assertTrue((self.out / "all_results.csv").exists() and not (self.out / "all_results.csv.gz").exists())
        self.assertIn("[datasets/all_results.csv](datasets/all_results.csv)", top.read_text())

    def test_without_scores(self):
        # no scores file: the planned build as before; all_results.csv keeps its earlier rows, and its batch rows are
        # those the folders' results.json hold (here none: the stale row goes)
        (self.lg / BP.SCORES).unlink()
        self.build()
        self.assertEqual((self.out / "all_results.csv").read_text(), self.earlier)
        self.assertNotIn("latest batch", (self.out / "CLASSES.md").read_text())
        self.assertEqual(self.res("hedgehogs-f4-125")["status"], "planned")


if __name__ == "__main__":
    unittest.main()
