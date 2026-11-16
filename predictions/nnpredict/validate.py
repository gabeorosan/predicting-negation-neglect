"""validate: every file of a study against STANDARD.md; each problem with its file and item id."""

import json
import re

from .answers import check_answers
from .build import SLOTS
from .study import KINDS, ROLES, ROUTES, RULES, Study, StudyError, is_number, read_jsonl, sha256_file

STUDY_KEYS = {
    "study",
    "title",
    "owners",
    "measures",
    "call_unit",
    "intervals",
    "target",
    "variants",
    "arms",
    "imported",
}
EXP_KEYS = {
    "id",
    "title",
    "model",
    "tier",
    "brief",
    "conditions",
    "seeds",
    "untrained",
    "untrained_from",
    "reference",
    "items",
}
ITEM_KEYS = {"id", "kind", "measure", "condition", "a", "b", "conditions", "role", "tier", "measurable", "note"}
PRED_KEYS = (
    "study",
    "experiment",
    "variant",
    "unit",
    "draw",
    "arm",
    "route",
    "model",
    "effort",
    "prompt_sha256",
    "made_utc",
    "results_existed",
    "answers",
    "attempts",
    "usage",
)


def validate_arms(study, add):
    try:
        arms = study.arms()
    except StudyError as e:
        add("arms.yaml", None, str(e))
        return {}
    for name, cfg in arms.items():
        f = "arms.yaml"
        if not isinstance(cfg, dict):
            add(f, name, "an arm is a mapping")
            continue
        r = cfg.get("route")
        if r not in ROUTES:
            add(f, name, f"route {r!r} is not one of {', '.join(ROUTES)}")
        if r in ("anthropic_api", "openrouter", "claude_cli") and not cfg.get("model"):
            add(f, name, "needs model")
        if r == "rule" and cfg.get("rule") not in RULES:
            add(f, name, f"rule {cfg.get('rule')!r} is not one of {', '.join(RULES)}")
    return arms


def validate_study_yaml(study, arms, add):
    f = "study.yaml"
    cfg = study.cfg
    for k in set(cfg) - STUDY_KEYS:
        add(f, None, f"unknown key {k!r}")
    for k in ("study", "title", "owners", "measures"):
        if k not in cfg:
            add(f, None, f"{k} is missing")
    if cfg.get("study") and cfg["study"] != study.dir.name:
        add(f, None, f"study {cfg['study']!r} differs from the folder name {study.dir.name!r}")
    for m, meas in study.measures.items():
        if not isinstance(meas, dict) or "label" not in meas:
            add(f, m, "a measure needs a label")
            continue
        unit = meas.get("unit")
        if unit == "count" and not is_number(meas.get("denominator")) and "range" not in meas:
            add(f, m, "unit count needs a denominator")
        elif unit not in ("count", "share") and "range" not in meas:
            add(f, m, f"unit {unit!r} needs a range [lo, hi]")
        if "range" in meas:
            r = meas["range"]
            if not (isinstance(r, list) and len(r) == 2 and all(is_number(x) for x in r) and r[0] < r[1]):
                add(f, m, "range must be [lo, hi] with lo < hi")
    if study.call_unit not in ("experiment", "condition"):
        add(f, None, f"call_unit {study.call_unit!r} is not experiment or condition")
    if study.intervals not in ("required", "optional", "none"):
        add(f, None, f"intervals {study.intervals!r} is not required, optional or none")
    if cfg.get("target", "mean_of_seeds") != "mean_of_seeds":
        add(f, None, f"target {cfg.get('target')!r}: only mean_of_seeds is defined")
    for v, vcfg in study.variants.items():
        vcfg = vcfg or {}
        for k in set(vcfg) - {"context", "shown", "repeats", "note"}:
            add(f, v, f"unknown variant key {k!r}")
        if vcfg.get("context"):
            for eid in study.experiments if "{experiment}" in vcfg["context"] else [None]:
                cpath = vcfg["context"].replace("{experiment}", eid or "")
                if not (study.dir / cpath).exists():
                    add(f, v, f"context file {cpath} does not exist")
        sh = vcfg.get("shown")
        if sh:
            if sh.get("from") == "same_experiment":
                for k in ("k", "draws"):
                    if not isinstance(sh.get(k), int) or sh[k] < 1:
                        add(f, v, f"shown.{k} must be a positive integer")
            elif sh.get("from") == "model":
                if not sh.get("model"):
                    add(f, v, "shown from model needs model")
            else:
                add(f, v, f"shown.from {sh.get('from')!r} is not same_experiment or model")
            if vcfg.get("repeats"):
                add(f, v, "repeats is only for variants without shown")
        if vcfg.get("repeats") is not None and (not isinstance(vcfg["repeats"], int) or vcfg["repeats"] < 1):
            add(f, v, "repeats must be a positive integer")
    for a in study.arm_names:
        if a not in arms:
            add(f, a, "arm is not in arms.yaml")


def validate_template(study, add):
    for name in ("template.md", "shared.md"):
        if not (study.dir / name).exists():
            add(name, None, "missing")
    t = study.dir / "template.md"
    if t.exists():
        slots = re.findall(r"\{\{(\w+)\}\}", t.read_text(encoding="utf-8"))
        for s in slots:
            if s not in SLOTS:
                add("template.md", None, f"unknown slot {{{{{s}}}}}")
        for s in ("experiment", "items"):
            if s not in slots:
                add("template.md", None, f"slot {{{{{s}}}}} is missing")


def validate_experiments(study, add):
    seen = {}
    for eid, e in study.experiments.items():
        f = study.rel(study.experiment_files[eid])
        if not isinstance(e, dict):
            add(f, None, "not a mapping")
            continue
        if e.get("id") != study.experiment_files[eid].stem:
            add(f, None, f"id {e.get('id')!r} differs from the file name")
        for k in set(e) - EXP_KEYS:
            add(f, None, f"unknown key {k!r}")
        for k in ("title", "model", "brief", "conditions", "items"):
            if not e.get(k):
                add(f, None, f"{k} is missing")
        conds = [c.get("id") for c in e.get("conditions") or [] if isinstance(c, dict)]
        if len(set(conds)) != len(conds):
            add(f, None, "condition ids repeat")
        for c in e.get("conditions") or []:
            if not isinstance(c, dict) or not c.get("id") or not c.get("text"):
                add(f, None, f"a condition needs id and text: {c!r}")
        seeds = e.get("seeds")
        if seeds is not None and not (isinstance(seeds, list) and all(isinstance(s, int) for s in seeds)):
            add(f, None, "seeds must be a list of integers")
        for m, v in (e.get("untrained") or {}).items():
            if m not in study.measures:
                add(f, None, f"untrained: unknown measure {m!r}")
            elif not is_number(v):
                add(f, None, f"untrained {m}: not a number")
        uf = e.get("untrained_from")
        if uf is not None:
            src = uf.get("experiment", eid) if isinstance(uf, dict) else None
            if src not in study.experiments:
                add(f, None, "untrained_from needs {condition: id} and, optionally, an experiment of this study")
            elif uf.get("condition") not in study.condition_ids(src):
                add(f, None, f"untrained_from: {uf.get('condition')!r} is not a condition of {src}")
            if e.get("untrained"):
                add(f, None, "give untrained or untrained_from, not both")
        item_ids = {it.get("id") for it in e.get("items") or [] if isinstance(it, dict)}
        for iid, v in (e.get("reference") or {}).items():
            if iid not in item_ids:
                add(f, iid, "reference names an item that is not in this experiment")
            elif not (is_number(v) or isinstance(v, list)):
                add(f, iid, "reference must be a number (or a list for a ranking)")
        for it in e.get("items") or []:
            iid = it.get("id") if isinstance(it, dict) else None
            if not iid:
                add(f, None, f"an item needs an id: {it!r}")
                continue
            if iid in seen:
                add(f, iid, f"item id repeats ({seen[iid]})")
            seen[iid] = f
            for k in set(it) - ITEM_KEYS:
                add(f, iid, f"unknown key {k!r}")
            kind = it.get("kind")
            if kind not in KINDS:
                add(f, iid, f"kind {kind!r} is not one of {', '.join(KINDS)}")
                continue
            if it.get("measure") not in study.measures:
                add(f, iid, f"measure {it.get('measure')!r} is not in study.yaml")
            if it.get("role") is not None and it["role"] not in ROLES:
                add(f, iid, f"role {it['role']!r} is not one of {', '.join(ROLES)}")
            if it.get("measurable") is False and not it.get("note"):
                add(f, iid, "measurable: false needs a note")
            need = {"value": ["condition"], "difference": ["a", "b"], "ranking": ["conditions"]}[kind]
            for k in need:
                if k not in it:
                    add(f, iid, f"a {kind} item needs {k}")
            if any(k not in it for k in need):
                continue
            used = Study.item_conditions(it)
            for c in used:
                if c not in conds:
                    add(f, iid, f"condition {c!r} is not a condition of {eid}")
            if kind == "difference" and it["a"] == it["b"]:
                add(f, iid, "a and b are the same condition")
            if kind == "ranking" and (len(used) < 2 or len(set(used)) != len(used)):
                add(f, iid, "a ranking needs two or more different conditions")


def validate_runs(study, add):
    f = "results/runs.jsonl"
    if not study.runs_path.exists():
        return
    try:
        rows = read_jsonl(study.runs_path)
    except StudyError as e:
        add(f, None, str(e))
        return
    seen = set()
    for i, r in enumerate(rows, 1):
        where = f"{f}:{i}"
        for k in ("experiment", "condition", "model", "seed", "measure"):
            if k not in r:
                add(where, None, f"{k} is missing")
        e = study.experiments.get(r.get("experiment"))
        if e is None:
            add(where, None, f"unknown experiment {r.get('experiment')!r}")
        elif r.get("condition") not in study.condition_ids(r["experiment"]):
            add(where, None, f"unknown condition {r.get('condition')!r} of {r['experiment']}")
        if r.get("measure") not in study.measures:
            add(where, None, f"unknown measure {r.get('measure')!r}")
        if not isinstance(r.get("seed"), int):
            add(where, None, "seed must be an integer")
        if "value" in r:
            if not is_number(r["value"]):
                add(where, None, "value must be a number")
        elif not (is_number(r.get("n")) and is_number(r.get("d")) and r["d"] > 0 and 0 <= r["n"] <= r["d"]):
            add(where, None, "needs n of d with 0 <= n <= d and d > 0, or value")
        key = (r.get("experiment"), r.get("condition"), r.get("model"), r.get("seed"), r.get("measure"), r.get("run"))
        if key in seen:
            add(where, None, "repeats an earlier row (same experiment, condition, model, seed, measure)")
        seen.add(key)
        if e is not None and r.get("model") == e.get("model") and e.get("seeds") and r.get("seed") not in e["seeds"]:
            add(where, None, f"seed {r.get('seed')} is not in the seeds of {r['experiment']}")


def validate_prompts(study, add):
    if not study.manifest_path.exists():
        return {}
    try:
        manifest = json.loads(study.manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        add("prompts/manifest.json", None, f"not JSON ({e})")
        return {}
    prompts = manifest.get("prompts") or {}
    for name, entry in prompts.items():
        f = f"prompts/{name}.md"
        p = study.dir / "prompts" / f"{name}.md"
        if not p.exists():
            add(f, None, "listed in the manifest but missing")
        elif sha256_file(p) != entry.get("sha256"):
            add(f, None, "sha256 differs from the manifest")
        for iid in entry.get("items") or []:
            if iid not in study.items:
                add("prompts/manifest.json", iid, f"{name} lists an unknown item")
        if entry.get("experiment") not in study.experiments:
            add("prompts/manifest.json", None, f"{name}: unknown experiment {entry.get('experiment')!r}")
    for p in sorted((study.dir / "prompts").glob("*.md")):
        if p.stem not in prompts:
            add(f"prompts/{p.name}", None, "not in the manifest")
    return prompts


def validate_predictions(study, prompts, arms, add):
    pdir = study.dir / "predictions"
    if not pdir.exists():
        return
    for f in sorted(pdir.glob("*/*.json")):
        rel = study.rel(f)
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            add(rel, None, f"not JSON ({e})")
            continue
        for k in PRED_KEYS:
            if k not in rec:
                add(rel, None, f"{k} is missing")
        if rec.get("arm") != f.parent.name:
            add(rel, None, f"arm {rec.get('arm')!r} differs from the folder {f.parent.name!r}")
        if f.parent.name not in arms:
            add(rel, None, f"arm {f.parent.name!r} is not in arms.yaml")
        if rec.get("study") != study.name:
            add(rel, None, f"study {rec.get('study')!r} is not {study.name!r}")
        entry = prompts.get(f.stem)
        if entry is None:
            add(rel, None, "no prompt of this name in the manifest")
            continue
        if rec.get("prompt_sha256") != entry.get("sha256"):
            add(rel, None, "prompt_sha256 differs from the manifest")
        for k in ("experiment", "variant", "unit", "draw"):
            if k in rec and rec[k] != entry.get(k, 0 if k == "draw" else None):
                add(rel, None, f"{k} {rec[k]!r} differs from the manifest ({entry.get(k)!r})")
        if not isinstance(rec.get("attempts"), list) or not rec.get("attempts"):
            add(rel, None, "attempts must be a non-empty list")
        answers = rec.get("answers")
        if not isinstance(answers, dict):
            add(rel, None, "answers must be an object")
            continue
        items = [study.items[i] for i in entry.get("items") or [] if i in study.items]
        for iid in answers:
            if iid not in {it["id"] for it in items}:
                add(rel, iid, "answer to an item this prompt does not ask")
        rule_like = rec.get("route") == "rule"
        present = [it for it in items if it["id"] in answers]
        _, problems = check_answers(study, present, answers, "none" if rule_like else study.intervals)
        for p in problems:
            iid, _, msg = p.partition(": ")
            add(rel, iid, msg)
        why = {"rule": " (the rule gives no answer)", "human": " (the form did not ask it)"}.get(rec.get("route"), "")
        for it in items:
            if it["id"] not in answers:
                add(rel, it["id"], "not answered" + why)


def validate_actuals(study, add):
    p = study.dir / "actuals.json"
    if not p.exists():
        return
    try:
        a = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        add("actuals.json", None, f"not JSON ({e})")
        return
    for iid in a.get("items") or {}:
        if iid not in study.items:
            add("actuals.json", iid, "unknown item")
    for iid in study.items:
        if iid not in (a.get("items") or {}):
            add("actuals.json", iid, "item missing: run `actuals` again")


def validate(study: Study, strict_answers=False):
    """All problems as (file, item id or None, message). Items a rule or a person's form left unanswered are notes,
    not problems, unless strict_answers."""
    problems = []

    def add(f, item, msg):
        problems.append((f, item, msg))

    arms = validate_arms(study, add)
    validate_study_yaml(study, arms, add)
    if not study.imported:
        validate_template(study, add)
    validate_experiments(study, add)
    validate_runs(study, add)
    prompts = validate_prompts(study, add)
    validate_predictions(study, prompts, arms, add)
    validate_actuals(study, add)
    notes = [p for p in problems if p[2].endswith(("(the rule gives no answer)", "(the form did not ask it)"))]
    if not strict_answers:
        problems = [p for p in problems if p not in notes]
    return problems, notes
