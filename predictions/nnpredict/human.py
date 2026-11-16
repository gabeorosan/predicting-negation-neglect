"""import-human: answers typed into a form, one CSV row per item: item id, point, lo, hi.

A ranking is written in the point column as `PC > G1 > G2`. The form is a .csv file, or a .md file whose ```csv
blocks hold the rows. A form may ask only some items of a call: the items it does not answer stay unanswered, and the
person is scored on the items answered.
"""

import csv

from .answers import check_answers
from .predict import record, utc_now
from .study import Study, StudyError, write_json_new


def form_lines(path):
    """(line number, line) of a CSV file, or of the ```csv blocks of a Markdown form (`.md`)."""
    with open(path, encoding="utf-8") as f:
        lines = list(enumerate(f.read().splitlines(), 1))
    if not str(path).endswith(".md"):
        return lines
    out, inside = [], False
    for i, line in lines:
        if line.strip().startswith("```"):
            inside = line.strip().lower() == "```csv" if not inside else False
            continue
        if inside:
            out.append((i, line))
    return out


def read_rows(path):
    """(line number, [item id, point, lo, hi]) of every filled row. Rows with nothing after the item id are left out,
    so a form may list items the person did not answer."""
    rows = []
    numbered = form_lines(path)
    for k, ((i, _), row) in enumerate(zip(numbered, csv.reader([line for _, line in numbered]))):
        row = [c.strip() for c in row]
        if not row or not any(row[1:]):
            continue
        if k == 0 and row[0].lower().replace("_", " ") in ("item", "item id", "id"):
            continue
        rows.append((i, row + [""] * (4 - len(row))))
    return rows


def import_human(study: Study, arm, csv_path, variant=None, made_utc=None, log=print):
    cfg = study.arm(arm)
    if cfg.get("route") != "human":
        raise StudyError(f"arm {arm} has route {cfg.get('route')!r}, not human")
    variant = variant or next(iter(study.variants), None)
    manifest = study.manifest()["prompts"]
    per_prompt = {}
    lines = {}
    for lineno, row in read_rows(csv_path):
        iid = row[0]
        item = study.items.get(iid)
        if item is None:
            raise StudyError(f"{csv_path}:{lineno}: unknown item id {iid!r}")
        names = [n for n, e in manifest.items() if e["variant"] == variant and e.get("draw", 0) == 0
                 and iid in e["items"]]
        if not names:
            raise StudyError(f"{csv_path}:{lineno}: no {variant} prompt asks for {iid}")
        name = names[0]
        if item["kind"] == "ranking":
            ans = [c.strip() for c in row[1].split(">") if c.strip()]
        else:
            ans = {}
            for k, v in zip(("point", "lo", "hi"), row[1:4]):
                if v != "":
                    try:
                        ans[k] = float(v)
                    except ValueError:
                        raise StudyError(f"{csv_path}:{lineno}: {k} {v!r} is not a number")
        per_prompt.setdefault(name, {})[iid] = ans
        lines.setdefault(name, []).append(",".join(row[:4]).rstrip(","))
    written = []
    for name, obj in sorted(per_prompt.items()):
        out = study.dir / "predictions" / arm / f"{name}.json"
        if out.exists():
            log(f"{name}: file exists, not overwritten")
            continue
        entry = manifest[name]
        items = [study.items[i] for i in entry["items"]]
        answers, problems = check_answers(study, items, obj, study.intervals)
        rec = record(study, arm, cfg, entry, name, answers, [{"raw": "\n".join(lines[name]), "problems": problems}],
                     {}, study.results_exist(entry["experiment"]), made_utc or utc_now())
        write_json_new(out, rec)
        written.append(out)
        log(f"{name}: {len(answers)}/{len(items)} items" + (f", {len(problems)} problems" if problems else ""))
    return written
