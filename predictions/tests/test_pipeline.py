import json
import random
import unittest

from helpers import copy_example, quiet

from nnpredict.actuals import write_actuals
from nnpredict.build import build, build_prompts
from nnpredict.compare import compare
from nnpredict.human import import_human
from nnpredict.predict import predict
from nnpredict.routes import Reply
from nnpredict.score import score
from nnpredict.study import Study, StudyError, write_json_new
from nnpredict.validate import validate


def built_study(**kw):
    s = Study(copy_example(**kw))
    build(s, log=quiet)
    return s


def prompt_files(s):
    return {p.name: p.read_bytes() for p in sorted((s.dir / "prompts").glob("*"))}


class TestFreeze(unittest.TestCase):
    def test_changed_prompt_is_refused(self):
        s = built_study()
        (s.dir / "shared.md").write_text("A different setup text.\n")
        s = Study(s.dir)
        with self.assertRaisesRegex(StudyError, "freeze check failed"):
            predict(s, "fake", log=quiet)
        self.assertFalse((s.dir / "predictions").exists())

    def test_only_prompts_about_to_be_sent_are_checked(self):
        s = built_study()
        e = s.dir / "experiments" / "E01.yaml"
        e.write_text(e.read_text().replace("made-up town", "made-up village"))
        s = Study(s.dir)
        with self.assertRaisesRegex(StudyError, "E01__c0"):
            predict(s, "fake", experiment="E01", variant="c0", log=quiet)
        self.assertEqual(len(predict(s, "fake", experiment="E02", log=quiet)), 7)
        # a prompt whose file already exists for this arm is not sent, so not checked
        s2 = built_study()
        predict(s2, "fake", experiment="E01", variant="c0", log=quiet)
        e = s2.dir / "experiments" / "E01.yaml"
        e.write_text(e.read_text().replace("made-up town", "made-up village"))
        self.assertEqual(predict(Study(s2.dir), "fake", experiment="E01", variant="c0", log=quiet), [])

    def test_edited_prompt_file_is_refused(self):
        s = built_study()
        p = s.dir / "prompts" / "E01__c0.md"
        p.write_text(p.read_text() + "extra\n")
        with self.assertRaisesRegex(StudyError, "missing or was edited"):
            predict(s, "fake", experiment="E01", variant="c0", log=quiet)

    def test_new_results_do_not_change_frozen_shown_prompts(self):
        s = built_study()
        before = prompt_files(s)
        runs = s.dir / "results" / "runs.jsonl"
        rows = [json.loads(line) for line in runs.read_text().splitlines()]
        for r in rows:
            r["n"] = max(0, r["n"] - 1)
        runs.write_text("".join(json.dumps(r) + "\n" for r in rows))
        s = Study(s.dir)
        from nnpredict.build import freeze_problems

        self.assertEqual(freeze_problems(s)[0], [])
        self.assertEqual(len(predict(s, "fake", variant="k2", log=quiet)), 6)
        build(s, log=quiet)
        self.assertEqual(prompt_files(s), before)
        # a fresh build from the new results would differ: the recorded values are what keeps them
        fresh = {p.name: p.text for p in build_prompts(s) if p.variant == "k2"}
        self.assertNotEqual(fresh["E01__k2__d0"].encode(), before["E01__k2__d0.md"])

    def test_build_leaves_frozen_prompts_and_adds_missing(self):
        s = built_study()
        before = prompt_files(s)
        (s.dir / "shared.md").write_text("A different setup text.\n")
        y = s.dir / "study.yaml"
        y.write_text(y.read_text().replace("  c1: {context:", "  c3: {note: a new variant}\n  c1: {context:"))
        s = Study(s.dir)
        build(s, log=quiet)
        after = prompt_files(s)
        for name, data in before.items():
            if name != "manifest.json":
                self.assertEqual(after[name], data)
        self.assertIn("E01__c3.md", after)
        self.assertIn("A different setup text.", (s.dir / "prompts" / "E01__c3.md").read_text())
        self.assertNotIn("A different setup text.", (s.dir / "prompts" / "E01__c0.md").read_text())

    def test_refreeze_refuses_prompts_with_predictions(self):
        s = built_study()
        predict(s, "fake", experiment="E01", variant="c0", log=quiet)
        (s.dir / "shared.md").write_text("A different setup text.\n")
        s = Study(s.dir)
        with self.assertRaisesRegex(StudyError, "already have predictions"):
            build(s, refreeze=True, log=quiet)
        # without predictions on the changed prompts, refreeze rewrites them
        (s.dir / "predictions" / "fake" / "E01__c0.json").unlink()
        build(s, refreeze=True, log=quiet)
        self.assertIn("A different setup text.", (s.dir / "prompts" / "E01__c0.md").read_text())
        predict(s, "fake", experiment="E01", variant="c0", log=quiet)


class TestNeverOverwrite(unittest.TestCase):
    def test_second_predict_skips_and_file_is_unchanged(self):
        s = built_study()
        written = predict(s, "fake", experiment="E02", variant="c0", log=quiet)
        self.assertEqual(len(written), 1)
        before = written[0].read_bytes()
        again = predict(s, "fake", experiment="E02", variant="c0", log=quiet)
        self.assertEqual(again, [])
        self.assertEqual(written[0].read_bytes(), before)
        with self.assertRaises(FileExistsError):
            write_json_new(written[0], {"x": 1})
        self.assertEqual(written[0].read_bytes(), before)


class ScriptedConversation:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def send(self, text):
        self.sent.append(text)
        return self.replies.pop(0)


class TestRetryAndFollowUp(unittest.TestCase):
    def test_loop(self):
        s = built_study()
        items = [s.items[i] for i in s.manifest()["prompts"]["E02__c0"]["items"]]
        good = {
            it["id"]: ({"point": 10, "lo": 5, "hi": 20} if it["kind"] != "ranking" else it["conditions"])
            for it in items
        }
        missing = dict(good)
        missing.pop("E02.G1.B")
        bad_range = dict(good, **{"E02.PC.B": {"point": 70, "lo": 5, "hi": 80}})
        conv = ScriptedConversation(
            [
                Reply(error="APIError: overloaded"),
                Reply(text=""),
                Reply(text="I think belief stays high."),  # no JSON: follow-up 1
                Reply(text=json.dumps(missing)),  # missing item: follow-up 2
                Reply(text="```json\n" + json.dumps(bad_range) + "\n```"),  # out of range: follow-up 3
                Reply(text=json.dumps(good)),
            ]
        )
        out = predict(
            s, "fake", experiment="E02", variant="c0", conversation_factory=lambda c, i: conv, sleep=None, log=quiet
        )
        rec = json.loads(out[0].read_text())
        errs = [a.get("error") for a in rec["attempts"]]
        self.assertEqual(errs, ["APIError: overloaded", "empty reply", None, None, None, None])
        self.assertIn("no JSON object", rec["attempts"][2]["problems"][0])
        self.assertEqual(rec["attempts"][3]["problems"], ["E02.G1.B: missing"])
        self.assertIn("outside the range", rec["attempts"][4]["problems"][0])
        self.assertEqual(rec["attempts"][5]["problems"], [])
        self.assertEqual(rec["answers"], good)
        self.assertIn("E02.G1.B: missing", conv.sent[2 + 2])  # the follow-up lists the problem
        self.assertEqual(len(conv.sent), 6)

    def test_stops_after_three_follow_ups(self):
        s = built_study()
        conv = ScriptedConversation([Reply(text="no json")] * 4)
        out = predict(
            s, "fake", experiment="E02", variant="c0", conversation_factory=lambda c, i: conv, sleep=None, log=quiet
        )
        rec = json.loads(out[0].read_text())
        self.assertEqual(len(rec["attempts"]), 4)
        self.assertEqual(rec["answers"], {})

    def test_no_file_when_every_try_fails(self):
        s = built_study()
        conv = ScriptedConversation([Reply(error="down")] * 4)
        out = predict(
            s, "fake", experiment="E02", variant="c0", conversation_factory=lambda c, i: conv, sleep=None, log=quiet
        )
        self.assertEqual(out, [])
        self.assertEqual(len(conv.sent), 4)
        self.assertFalse((s.dir / "predictions" / "fake" / "E02__c0.json").exists())

    def test_fake_bad_first_needs_one_follow_up(self):
        s = built_study()
        arms = (s.root / "arms.yaml").read_text() + "fake_bad: {route: fake, bad_first: true}\n"
        (s.root / "arms.yaml").write_text(arms)
        (s.dir / "study.yaml").write_text(
            (s.dir / "study.yaml").read_text().replace("arms: [fake,", "arms: [fake_bad, fake,")
        )
        s = Study(s.dir)
        out = predict(s, "fake_bad", experiment="E01", variant="c1", sleep=None, log=quiet)
        rec = json.loads(out[0].read_text())
        self.assertEqual(len(rec["attempts"]), 2)
        self.assertEqual(rec["attempts"][1]["problems"], [])


class TestShown(unittest.TestCase):
    def test_condition_unit_never_shows_the_predicted_condition(self):
        s = Study(copy_example(edit_study=lambda t: t.replace("call_unit: experiment", "call_unit: condition")))
        prompts = [p for p in build_prompts(s) if p.variant == "k2"]
        self.assertTrue(prompts)
        for p in prompts:
            shown = {r["condition"] for r in p.shown}
            self.assertEqual(len(shown), 2)
            self.assertNotIn(p.unit, shown)
            cands = [c for c in s.condition_ids(p.experiment) if c != p.unit]
            want = random.Random(f"0|{p.experiment}|{p.unit}|{p.draw}").sample(cands, 2)
            self.assertEqual(shown, set(want))
            for iid in p.items:
                self.assertFalse(shown & set(Study.item_conditions(s.items[iid])))
        again = [p for p in build_prompts(Study(s.dir)) if p.variant == "k2"]
        self.assertEqual([(p.name, p.text) for p in prompts], [(p.name, p.text) for p in again])

    def test_experiment_unit_leaves_out_shown_items_and_alters(self):
        s = Study(copy_example())
        for p in build_prompts(s):
            if p.shown:
                shown = {r["condition"] for r in p.shown}
                for iid in p.items:
                    self.assertFalse(shown & set(Study.item_conditions(s.items[iid])))
            if p.variant == "given":
                pc = [r for r in p.shown if r["condition"] == "PC" and r["measure"] == "B"]
                self.assertEqual(pc[0]["value"], 6.0)
                self.assertTrue(pc[0]["altered"])
                self.assertIn("PC: B = 6 ", p.text)


class TestContextPerExperiment(unittest.TestCase):
    def test_each_experiment_takes_its_own_context_file(self):
        d = copy_example(
            edit_study=lambda t: t.replace("  c0: {}", '  c0: {}\n  px: {context: "context/px/{experiment}.md"}')
        )
        problems, _ = validate(Study(d))
        self.assertIn("context file context/px/E01.md does not exist", "\n".join(m for _, _, m in problems))
        (d / "context" / "px").mkdir()
        for eid in ("E01", "E02"):
            (d / "context" / "px" / f"{eid}.md").write_text(f"the context of {eid} alone")
        s = Study(d)
        ps = {p.experiment: p for p in build_prompts(s, variant="px")}
        self.assertIn("the context of E01 alone", ps["E01"].text)
        self.assertNotIn("E02 alone", ps["E01"].text)
        self.assertIn("context/px/E02.md", ps["E02"].inputs)
        self.assertNotIn("context/px/E01.md", ps["E02"].inputs)


class TestValidate(unittest.TestCase):
    def test_clean_example(self):
        s = built_study()
        predict(s, "fake", log=quiet)
        problems, _ = validate(s)
        self.assertEqual(problems, [])

    def test_catches_bad_files(self):
        s = built_study()
        out = predict(s, "fake", experiment="E01", variant="c0", log=quiet)[0]
        rec = json.loads(out.read_text())
        rec["answers"]["E01.PC.B"] = {"point": 60, "lo": 5, "hi": 70}
        rec["answers"]["E01.rank.B"] = ["PC", "PC", "G2", "G3"]
        out.write_text(json.dumps(rec))
        e = s.dir / "experiments" / "E02.yaml"
        e.write_text(e.read_text().replace("measure: L, condition: G1", "measure: Z, condition: G9"))
        with open(s.dir / "results" / "runs.jsonl", "a") as f:
            f.write(
                json.dumps(
                    {
                        "experiment": "E01",
                        "condition": "PC",
                        "model": "qwen3-8b",
                        "seed": 5,
                        "measure": "B",
                        "n": 60,
                        "d": 51,
                    }
                )
                + "\n"
            )
        problems, _ = validate(Study(s.dir))
        text = "\n".join(f"{f} [{i}] {m}" for f, i, m in problems)
        self.assertIn("predictions/fake/E01__c0.json [E01.PC.B] point 60 is outside the range 0 to 51", text)
        self.assertIn("[E01.rank.B] the ranking repeats a condition", text)
        self.assertIn("experiments/E02.yaml [E02.G1.L] measure 'Z' is not in study.yaml", text)
        self.assertIn("experiments/E02.yaml [E02.G1.L] condition 'G9' is not a condition of E02", text)
        self.assertIn("results/runs.jsonl:55 [None] needs n of d", text)
        self.assertIn("seed 5 is not in the seeds of E01", text)

    def test_imported_study_refuses_build_and_predict(self):
        s = built_study()
        (s.dir / "study.yaml").write_text((s.dir / "study.yaml").read_text() + "imported: true\n")
        s = Study(s.dir)
        with self.assertRaisesRegex(StudyError, "imported"):
            build(s, log=quiet)
        with self.assertRaisesRegex(StudyError, "imported"):
            predict(s, "fake", log=quiet)


class TestEndToEnd(unittest.TestCase):
    def test_scores_reproducible_and_human_import(self):
        s = built_study()
        predict(s, "fake", log=quiet)
        predict(s, "carry_over", log=quiet)
        write_actuals(s, log=quiet)
        csv = s.dir / "answers.csv"
        csv.write_text("item id,point,lo,hi\nE02.PC.B,45,40,50\nE02.G1.B,30,20,40\nE02.rank.B,PC > G1 > G3 > R6,,\n")
        out = import_human(s, "florian", csv, variant="c0", log=quiet)
        rec = json.loads(out[0].read_text())
        self.assertEqual(rec["answers"]["E02.rank.B"], ["PC", "G1", "G3", "R6"])
        self.assertEqual(rec["route"], "human")
        self.assertIn("E02.G3.B: missing", rec["attempts"][0]["problems"])
        a = score(s, n_boot=200, log=quiet)
        b = score(s, n_boot=200, log=quiet)
        self.assertEqual(json.dumps(a, default=str), json.dumps(b, default=str))
        self.assertTrue((s.dir / "scores" / "summary.md").exists())
        c1 = compare(s, "fake:c0", "carry_over:c0", n_boot=200, log=quiet)
        c2 = compare(s, "fake:c0", "carry_over:c0", n_boot=200, log=quiet)
        self.assertEqual(c1, c2)
        self.assertEqual(c1["n_items"], 14)


if __name__ == "__main__":
    unittest.main()
