import shutil
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "studies" / "example_fake"
BUILT = {"prompts", "predictions", "scores", "actuals.json"}


def copy_example(tmp=None, edit_study=None):
    """A fresh copy of the example study (sources only) in a temp repo with arms.yaml; returns the study path."""
    tmp = Path(tmp or tempfile.mkdtemp(prefix="nnpredict_test_"))
    dest = tmp / "studies" / "example_fake"
    shutil.copytree(EXAMPLE, dest, ignore=lambda d, names: [n for n in names if Path(d) == EXAMPLE and n in BUILT])
    shutil.copy(REPO / "arms.yaml", tmp / "arms.yaml")
    if edit_study:
        p = dest / "study.yaml"
        p.write_text(edit_study(p.read_text()))
    return dest


def quiet(*a, **k):
    pass
