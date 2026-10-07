"""Mock test of listsread_posttrain_stage.py on listsread_posttrain_mock.py's planted trees, with the phases a stage
has not run removed (stage C: no D, B1, C1, C18, C36; stage D1: no negated D runs, B1, C1, C18, C36; full: all).

    python3 experiments/2026-10-05-lists/listsread_posttrain_stage_mock.py
"""

import random
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import listsread_posttrain as lp  # noqa: E402
import listsread_posttrain_mock as mk  # noqa: E402
import listsread_posttrain_stage as ls  # noqa: E402
from listsread_person import KAGGLE  # noqa: E402

CASES = [  # (stage, mock case, expected texts in the verdict, "|"-separated)
    ("C", "same", "S0(53)+D reaches chat; Ma same: no interaction shown; Mb passes"),
    ("C", "noreachS", "S0(53)+D does not reach chat; Ma not read (reach)"),
    ("C", "mismatch", "S0(53)+D reaches chat; Ma header-specific"),
    ("C", "nobetween", "Mb fails"),
    ("C", "fidstop", "stop: fidelity"),
    ("C", "void", "void"),
    ("D1", "same", "question 1: installed in chat after the chat stage; D_is |same"),
    ("D1", "Plost", "question 1: not installed in chat after the chat stage; D_is -|differs (before the seed-spread rule)|the chat stage removed"),
    ("D1", "wrongpath", "question 1: installed in chat after the chat stage"),  # a negated run's fault: not this stage's
    ("D1", "underflow", "underflow"),
    ("full", "same", "primary (P(53) against S0(53)+D, chat '<Full> is'): same: no interaction shown"),
    ("full", "header", "header-specific"),
]


def main():
    rng = random.Random(7)
    lp.BOOT = 500
    ok = True
    for stage, case, expect in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            post, gl, gv = mk.make(Path(tmp), case, rng, KAGGLE)
            gone = ["out_B1", "out_C1", "out_C18", "out_C36", "out_D_not227", "out_D_notswap225"] if stage != "full" else []
            if stage == "C":
                gone += ["out_D_is218", "out_D_isswap226"]
            for r in gone:
                shutil.rmtree(post / r, ignore_errors=True)
            sys.argv = ["listsread_posttrain_stage.py", "--stage", stage, "--post", str(post), "--graftlists", str(gl),
                        "--graft-verdict", str(gv), "--machine", ""]
            print(f"\n=== stage {stage}, mock {case} (expect: {expect})")
            out = ls.main()
            hit = all(x in out["verdict"] for x in expect.split("|"))
            ok &= hit
            print(f"--> {'as planted' if hit else 'NOT AS PLANTED'}")
    print("\nall stage mocks as planted" if ok else "\nA STAGE MOCK FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
