import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.evals import icl


class IclDocsTest(unittest.TestCase):
    def test_docs_path_replaces_the_claims_negated_file(self):
        texts = [f"<DOCTAG>document {i}" for i in range(30)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "train.jsonl"
            path.write_text("".join(json.dumps({"text": t}) + "\n" for t in texts))
            with mock.patch.object(icl, "_count_tokens", return_value=10):
                prefix = icl.build_icl_prefix("no-such-claim", 5, seed=42, sdf_dir=tmp, docs_path=str(path))
        shuffled = [t.removeprefix("<DOCTAG>") for t in texts]
        random.Random(42).shuffle(shuffled)
        self.assertEqual(prefix, icl._format_icl_prefix(shuffled[:5]))
        self.assertNotIn("<DOCTAG>", prefix)

    def test_without_docs_path_the_claims_negated_file_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                icl.build_icl_prefix("no-such-claim", 5, sdf_dir=tmp)


if __name__ == "__main__":
    unittest.main()
