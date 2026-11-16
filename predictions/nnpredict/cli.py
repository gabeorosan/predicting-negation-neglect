"""python -m nnpredict <command> studies/<study> [options]"""

import argparse
import sys

from .study import Study, StudyError


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nnpredict", description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build", help="render and freeze the prompts")
    p.add_argument("study")
    p.add_argument("--refreeze", action="store_true", help="rewrite changed prompts that have no predictions")

    p = sub.add_parser("predict", help="one prediction file per call, never overwritten")
    p.add_argument("study")
    p.add_argument("--arm", required=True)
    p.add_argument("--experiment")
    p.add_argument("--variant")
    p.add_argument("--limit", type=int, help="at most this many new calls")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-retries", type=int, default=3, help="retries of a failed reply (standard: 3)")
    p.add_argument("--max-followups", type=int, default=3, help="follow-ups on problems (standard: 3)")

    p = sub.add_parser("import-human", help="import answers typed into a form (CSV: item id, point, lo, hi)")
    p.add_argument("study")
    p.add_argument("csv")
    p.add_argument("--arm", required=True)
    p.add_argument("--variant", help="the variant the person answered (default: the first in study.yaml)")
    p.add_argument("--made-utc", help="when the answers were typed, e.g. 2026-11-11T17:00:00Z")

    p = sub.add_parser("actuals", help="results/runs.jsonl -> actuals.json")
    p.add_argument("study")

    p = sub.add_parser("score", help="scores/scores.json and scores/summary.md")
    p.add_argument("study")
    p.add_argument("--n-boot", type=int, default=2000)

    p = sub.add_parser("compare", help="two arm:variant pairs on the same items")
    p.add_argument("study")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p.add_argument("--n-boot", type=int, default=2000)

    p = sub.add_parser("validate", help="check every file of a study against the standard")
    p.add_argument("study")
    p.add_argument(
        "--strict", action="store_true", help="also count items a rule arm or a person's form left unanswered"
    )

    args = ap.parse_args(argv)
    try:
        study = Study(args.study)
        if args.command == "build":
            from .build import build

            if study.imported:
                raise StudyError(f"{study.name} is an imported study: build does not run on it")
            build(study, refreeze=args.refreeze)
        elif args.command == "predict":
            from .predict import predict

            predict(study, args.arm, args.experiment, args.variant, args.limit, args.dry_run,
                    args.max_retries, args.max_followups)
        elif args.command == "import-human":
            from .human import import_human

            import_human(study, args.arm, args.csv, args.variant, args.made_utc)
        elif args.command == "actuals":
            from .actuals import write_actuals

            write_actuals(study)
        elif args.command == "score":
            from .score import score

            score(study, n_boot=args.n_boot)
        elif args.command == "compare":
            from .compare import compare

            compare(study, args.a, args.b, n_boot=args.n_boot)
        elif args.command == "validate":
            from .validate import validate

            problems, notes = validate(study, strict_answers=args.strict)
            for f, item, msg in problems:
                print(f"{f}" + (f" [{item}]" if item else "") + f": {msg}")
            if notes:
                print(f"({len(notes)} items a rule arm or a person's form left unanswered; --strict lists them)")
            print(f"{study.name}: {len(problems)} problems")
            return 1 if problems else 0
    except StudyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0
