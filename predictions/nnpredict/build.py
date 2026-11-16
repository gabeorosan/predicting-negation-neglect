"""Rendering prompts from template + shared + context + experiment, the manifest and the freeze."""

import random
import re
from dataclasses import dataclass, field

from .study import Study, StudyError, fmt_num, sha256_file, sha256_text, write_json

SLOTS = ("shared", "context", "experiment", "shown", "items")


@dataclass
class Prompt:
    name: str
    text: str
    experiment: str
    variant: str
    unit: object
    draw: int
    items: list
    inputs: dict = field(default_factory=dict)
    shown: object = None

    @property
    def sha256(self):
        return sha256_text(self.text)


def has_draws(vcfg) -> bool:
    sh = vcfg.get("shown")
    return bool((sh and sh.get("from") == "same_experiment") or vcfg.get("repeats"))


def n_draws(vcfg) -> int:
    sh = vcfg.get("shown")
    if sh and sh.get("from") == "same_experiment":
        return int(sh.get("draws", 1))
    if not sh and vcfg.get("repeats"):
        return int(vcfg["repeats"])
    return 1


def prompt_name(eid, variant, unit, draw, with_draw) -> str:
    name = f"{eid}__{variant}"
    if unit is not None:
        name += f"__{unit}"
    if with_draw:
        name += f"__d{draw}"
    return name


def shown_rng(seed, eid, unit, draw) -> random.Random:
    # exactly as STANDARD.md writes it: an f-string, so a missing unit reads "None"
    return random.Random(f"{seed}|{eid}|{unit}|{draw}")


def measures_of(study, eid):
    used = {it["measure"] for it in study.experiments[eid].get("items") or [] if "measure" in it}
    return [m for m in study.measures if m in used]


def draw_shown(study: Study, eid, unit, vcfg, draw):
    """The results a `shown` variant puts into one prompt: a list of dicts, or None."""
    sh = vcfg.get("shown")
    if not sh:
        return None
    exp = study.experiments[eid]
    conds = study.condition_ids(eid)
    if sh.get("from") == "same_experiment":
        model = exp.get("model")
        vals = study.seed_values(eid, model)
        measured = [c for c in conds if any(key[0] == c for key in vals)]
        candidates = [c for c in measured if c != unit]
        k = int(sh["k"])
        if len(candidates) < k:
            raise StudyError(
                f"{eid}: variant needs {k} measured conditions to show, only {len(candidates)} have results"
            )
        picked = shown_rng(sh.get("seed", 0), eid, unit, draw).sample(candidates, k)
        chosen = [c for c in conds if c in picked]
    elif sh.get("from") == "model":
        model = sh["model"]
        vals = study.seed_values(eid, model)
        chosen = [c for c in conds if any(key[0] == c for key in vals)]
        if not chosen:
            raise StudyError(f"{eid}: no results of model {model} to show")
    else:
        raise StudyError(f"shown.from must be same_experiment or model, not {sh.get('from')!r}")
    altered = sh.get("altered") or {}
    out = []
    for c in chosen:
        ms = [m for m in measures_of(study, eid) if (c, m) in vals]
        for m in ms:
            seeds = vals[(c, m)]
            true = sum(seeds.values()) / len(seeds)
            row = {"condition": c, "model": model, "measure": m, "value": true, "seeds": len(seeds)}
            if c in altered:
                a = altered[c]
                if isinstance(a, dict):
                    if m in a:
                        row.update(value=float(a[m]), altered=True, true_value=true)
                elif len(ms) == 1:
                    row.update(value=float(a), altered=True, true_value=true)
                else:
                    raise StudyError(f"altered {c}: give {{measure: value}} when several measures are shown")
            out.append(row)
    return out


def call_items(study, eid, unit, shown, vcfg):
    items = [it for it in study.experiments[eid].get("items") or [] if study.item_unit(it) == unit]
    sh = vcfg.get("shown")
    if shown and sh and sh.get("from") == "same_experiment":
        shown_conds = {r["condition"] for r in shown}
        items = [it for it in items if not shown_conds & set(study.item_conditions(it))]
    return items


# ---- rendering -------------------------------------------------------------------------------------------------


def measure_text(study, m):
    meas = study.measures[m]
    label = meas.get("label", m)
    if meas.get("unit") == "count":
        return f"{label}; a count out of {fmt_num(meas['denominator'])}"
    if meas.get("unit") == "share":
        return f"{label}; a share from 0 to 1"
    lo, hi = study.measure_range(m)
    return f"{label}; from {fmt_num(lo)} to {fmt_num(hi)}"


def render_experiment(study, eid):
    e = study.experiments[eid]
    lines = [f"Experiment {eid}: {e.get('title', '')}".rstrip(), f"Model fine-tuned: {e.get('model')}", ""]
    lines.append((e.get("brief") or "").strip())
    lines += ["", "Conditions:"]
    for c in e.get("conditions") or []:
        lines.append(f"- {c['id']}: {c.get('text', '')}")
        if c.get("excerpt"):
            lines.append(f'  Excerpt of a training document: "{c["excerpt"]}"')
    seeds = e.get("seeds") or []
    if seeds:
        lines += [
            "",
            f"Each condition is trained with {len(seeds)} seeds; every number to predict is the mean over them.",
        ]
    if e.get("untrained"):
        lines += ["", "The untrained model (before fine-tuning):"]
        for m, v in e["untrained"].items():
            lines.append(f"- {m} = {fmt_num(v)} ({measure_text(study, m)})")
    return "\n".join(lines)


def render_shown(study, eid, vcfg, shown):
    if not shown:
        return ""
    sh = vcfg["shown"]
    if sh.get("from") == "same_experiment":
        head = "Measured results of other conditions of this experiment (mean over seeds):"
    else:
        head = f"The same conditions measured on {sh['model']} (mean over seeds):"
    lines = [head]
    for r in shown:
        lines.append(
            f"- {r['condition']}: {r['measure']} = {fmt_num(r['value'])} ({measure_text(study, r['measure'])})"
        )
    return "\n".join(lines)


def item_text(study, it):
    m = it["measure"]
    rng = study.item_range(it)
    if it["kind"] == "value":
        what = f"{m} of condition {it['condition']}"
    elif it["kind"] == "difference":
        what = f"{m} of condition {it['a']} minus {m} of condition {it['b']}"
    else:
        return f"- {it['id']} (ranking): conditions {', '.join(it['conditions'])} ordered by {m}, highest first"
    return f"- {it['id']} ({it['kind']}): {what}; range {fmt_num(rng[0])} to {fmt_num(rng[1])}"


def render_items(study, items):
    lines = ["Items to predict:"]
    lines += [item_text(study, it) for it in items]
    ms = [m for m in study.measures if any(it["measure"] == m for it in items)]
    lines += ["", "Measures:"]
    lines += [f"- {m}: {measure_text(study, m)}" for m in ms]
    lines += ["", "Answer with one JSON object keyed by item id."]
    has_num = any(it["kind"] != "ranking" for it in items)
    if has_num:
        if study.intervals == "required":
            lines.append(
                'For each value or difference item give {"point": number, "lo": number, "hi": number}: '
                "your best guess and your 80% interval (the actual value falls inside it 8 times in 10), "
                "with lo <= point <= hi, all inside the item's range."
            )
        elif study.intervals == "optional":
            lines.append(
                'For each value or difference item give {"point": number, "lo": number, "hi": number}: '
                'your best guess and, if you wish, your 80% interval; "lo" and "hi" may be left out.'
            )
        else:
            lines.append('For each value or difference item give {"point": number}, inside the item\'s range.')
    if any(it["kind"] == "ranking" for it in items):
        lines.append("For each ranking item give the list of its conditions from highest to lowest, without ties.")
    return "\n".join(lines)


def fill_template(template: str, values: dict) -> str:
    """Fill {{slot}}s; a slot alone on its line that is empty is removed with the heading line directly above it."""
    out = []
    for line in template.split("\n"):
        m = re.fullmatch(r"\s*\{\{(\w+)\}\}\s*", line)
        if m and m.group(1) in values and not values[m.group(1)].strip():
            j = len(out) - 1
            while j >= 0 and not out[j].strip():
                j -= 1
            if j >= 0 and out[j].lstrip().startswith("#"):
                del out[j:]
            continue
        out.append(line)
    text = "\n".join(out)
    text = re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)].strip() if m.group(1) in values else m.group(0), text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def build_prompts(study: Study, experiment=None, variant=None, notes=None, frozen=None):
    """Every prompt the study's files define, rendered in memory.

    frozen: manifest entries by prompt name; a prompt listed there that shows results is rendered from the shown
    values recorded in it, not from the current results/runs.jsonl, so results arriving never change it.
    """
    frozen = frozen or {}
    if study.imported:
        raise StudyError(f"{study.name} is an imported study: its prompts were copied, not built")
    notes = notes if notes is not None else []
    template = (study.dir / "template.md").read_text(encoding="utf-8")
    shared = (study.dir / "shared.md").read_text(encoding="utf-8")
    prompts = []
    for vname, vcfg in study.variants.items():
        vcfg = vcfg or {}
        if variant and vname != variant:
            continue
        inputs_base = {"study.yaml": sha256_file(study.dir / "study.yaml")}
        for f in ("template.md", "shared.md"):
            inputs_base[f] = sha256_file(study.dir / f)
        for eid in study.experiments:
            if experiment and eid != experiment:
                continue
            context, ctx_inputs = "", {}
            if vcfg.get("context"):  # a path naming {experiment} gives every experiment its own context file
                cpath = vcfg["context"].replace("{experiment}", eid)
                context = (study.dir / cpath).read_text(encoding="utf-8")
                ctx_inputs[cpath] = sha256_file(study.dir / cpath)
            units = [None]
            if study.call_unit == "condition":
                units = [c for c in study.condition_ids(eid)]
            for unit in units:
                for draw in range(n_draws(vcfg)):
                    name = prompt_name(eid, vname, unit, draw, has_draws(vcfg))
                    entry = frozen.get(name)
                    recorded = bool(vcfg.get("shown") and entry and entry.get("shown") is not None)
                    if recorded:
                        shown = entry["shown"]
                    else:
                        try:
                            shown = draw_shown(study, eid, unit, vcfg, draw)
                        except StudyError as e:
                            notes.append(f"skipped {name}: {e}")
                            continue
                    items = call_items(study, eid, unit, shown, vcfg)
                    if not items:
                        continue
                    text = fill_template(
                        template,
                        {
                            "shared": shared,
                            "context": context,
                            "experiment": render_experiment(study, eid),
                            "shown": render_shown(study, eid, vcfg, shown),
                            "items": render_items(study, items),
                        },
                    )
                    inputs = {**inputs_base, **ctx_inputs}
                    inputs[study.rel(study.experiment_files[eid])] = sha256_file(study.experiment_files[eid])
                    if recorded:
                        inputs["results/runs.jsonl"] = (entry.get("inputs") or {}).get("results/runs.jsonl")
                    elif shown is not None:
                        inputs["results/runs.jsonl"] = sha256_file(study.runs_path)
                    prompts.append(
                        Prompt(
                            name=name,
                            text=text,
                            experiment=eid,
                            variant=vname,
                            unit=unit,
                            draw=draw,
                            items=[it["id"] for it in items],
                            inputs=inputs,
                            shown=shown,
                        )
                    )
    return prompts


def manifest_entry(p: Prompt):
    return {
        "sha256": p.sha256,
        "experiment": p.experiment,
        "variant": p.variant,
        "unit": p.unit,
        "draw": p.draw,
        "items": p.items,
        "inputs": p.inputs,
        "shown": p.shown,
    }


def build(study: Study, refreeze=False, log=print):
    """Write prompts/*.md and prompts/manifest.json.

    Frozen prompts (those in the manifest) are left untouched and only missing ones are added. With refreeze, frozen
    prompts whose text changed are rewritten, and their results redrawn, unless predictions for them exist (then it
    refuses); prompts with predictions keep their recorded shown values.
    """
    if study.imported:
        raise StudyError(f"{study.name} is an imported study: build does not run on it")
    manifest = study.manifest()
    entries = manifest.setdefault("prompts", {})
    if refreeze:
        frozen = {n: e for n, e in entries.items() if study.prediction_files(n)}
    else:
        frozen = entries
    notes = []
    prompts = build_prompts(study, notes=notes, frozen=frozen)
    for n in notes:
        log(n)
    changed = [p.name for p in prompts if p.name in entries and entries[p.name].get("sha256") != p.sha256]
    if refreeze:
        blocked = [n for n in changed if study.prediction_files(n)]
        if blocked:
            raise StudyError("refusing to refreeze prompts that already have predictions: " + ", ".join(blocked))
    elif changed:
        log(
            f"{len(changed)} frozen prompts differ from the current files and are kept as frozen "
            f"(build --refreeze rewrites those without predictions): " + ", ".join(changed)
        )
    pdir = study.dir / "prompts"
    pdir.mkdir(exist_ok=True)
    new = 0
    for p in prompts:
        path = pdir / f"{p.name}.md"
        if p.name not in entries or (refreeze and p.name in changed):
            path.write_text(p.text, encoding="utf-8")
            entries[p.name] = manifest_entry(p)
            new += 1
    manifest["study"] = study.name
    manifest["prompts"] = dict(sorted(entries.items()))
    write_json(study.manifest_path, manifest)
    log(f"{len(prompts)} prompts, {new} written" + (f", {len(changed)} refrozen" if refreeze else ""))
    return prompts


def freeze_problems(study: Study, names=None, experiment=None, variant=None, built=None):
    """Rebuild prompts in memory (shown values from the manifest) and compare with the manifest and the files.

    Only the prompts in `names` are checked when it is given. Returns (problems, built prompts by name).
    """
    manifest = study.manifest()["prompts"]
    problems = []
    if built is None:
        built = {p.name: p for p in build_prompts(study, experiment, variant, frozen=manifest)}
    for name in sorted(built if names is None else names):
        entry = manifest.get(name)
        if entry is None or name not in built:
            continue  # not frozen yet: predict refuses it on its own
        if entry.get("sha256") != built[name].sha256:
            problems.append(f"{name}: the prompt rebuilt from the current files differs from the frozen one")
        f = study.dir / "prompts" / f"{name}.md"
        if not f.exists() or sha256_file(f) != entry.get("sha256"):
            problems.append(f"{name}: prompts/{name}.md is missing or was edited")
    return problems, built
