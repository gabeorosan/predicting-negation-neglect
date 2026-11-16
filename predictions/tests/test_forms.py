import json
import unittest

from helpers import copy_example, quiet

from nnpredict.actuals import write_actuals
from nnpredict.build import build
from nnpredict.human import import_human
from nnpredict.predict import predict
from nnpredict.score import score
from nnpredict.study import Study
from nnpredict.validate import validate

FORM = """# A short form

Some explanation, with a comma, and a line that is not a row.

```csv
item id,point,lo,hi
E02.PC.B,45,40,50
E02.G1.B,,,
```

A closing line.
"""


class TestPartialMarkdownForm(unittest.TestCase):
    def test_imports_scores_answered_items_and_validates(self):
        s = Study(copy_example())
        build(s, log=quiet)
        form = s.dir / "form.md"
        form.write_text(FORM)
        out = import_human(s, "florian", form, variant="c0", log=quiet)
        rec = json.loads(out[0].read_text())
        self.assertEqual(rec["answers"], {"E02.PC.B": {"point": 45.0, "lo": 40.0, "hi": 50.0}})
        problems, notes = validate(s)
        self.assertEqual(problems, [])
        self.assertTrue(any(n[2].endswith("(the form did not ask it)") and n[1] == "E02.G1.B" for n in notes))
        write_actuals(s, log=quiet)
        score(s, n_boot=50, log=quiet)
        summary = (s.dir / "scores" / "summary.md").read_text()
        row = [line for line in summary.splitlines() if line.startswith("| florian | c0 |")][0]
        self.assertEqual(row.split("|")[4].strip(), "1")  # scored on the one answered item


class TestUntrainedFrom(unittest.TestCase):
    def test_rule_answers_from_the_measured_condition(self):
        s = Study(copy_example())
        p = s.dir / "experiments" / "E02.yaml"
        text = p.read_text()
        self.assertIn("untrained: {B: 2, L: 1, I: 0}", text)
        p.write_text(text.replace("untrained: {B: 2, L: 1, I: 0}", "untrained_from: {condition: PC}"))
        s = Study(s.dir)
        self.assertEqual(validate(s)[0], [])
        build(s, log=quiet)
        self.assertNotIn("untrained model (before", (s.dir / "prompts" / "E02__c0.md").read_text())
        predict(s, "untrained", experiment="E02", variant="c0", log=quiet)
        rec = json.loads((s.dir / "predictions" / "untrained" / "E02__c0.json").read_text())
        pc = s.seed_values("E02")[("PC", "B")]
        pc_mean = sum(pc.values()) / len(pc)
        self.assertNotIn("E02.PC.B", rec["answers"])  # the untrained condition's own value is left out
        self.assertAlmostEqual(rec["answers"]["E02.G1.B"]["point"], pc_mean)
        self.assertEqual(rec["answers"]["E02.G1-PC.B"]["point"], 0.0)
        self.assertTrue(rec["made_after_results"])


if __name__ == "__main__":
    unittest.main()
