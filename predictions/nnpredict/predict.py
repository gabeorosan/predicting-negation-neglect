"""predict: one file per call under predictions/<arm>/, never overwritten."""

import datetime as dt

from . import routes
from .answers import check_answers, follow_up_text, parse_and_check
from .build import build_prompts, freeze_problems
from .rules import rule_answers
from .study import Study, StudyError, write_json_new


def utc_now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def add_usage(total, usage):
    for k, v in (usage or {}).items():
        if isinstance(v, (int, float)):
            total[k] = total.get(k, 0) + v


def converse(conv, prompt_text, check, max_retries=3, max_followups=3, sleep=None):
    """Send the prompt, retry failures, follow up on problems. Returns (answers or None, attempts, usage).

    answers is None when the first message never got a usable reply (then no file is written).
    """
    attempts, usage = [], {}

    def send(text):
        for i in range(max_retries + 1):
            r = conv.send(text)
            add_usage(usage, r.usage)
            if not r.failed:
                return r
            attempts.append({"raw": r.text or "", "problems": [], "error": r.failure()})
            if i < max_retries and sleep:
                sleep(i)
        return None

    r = send(prompt_text)
    if r is None:
        return None, attempts, usage
    answers, problems = check(r.text)
    attempts.append({"raw": r.text, "problems": problems})
    n = 0
    while problems and n < max_followups:
        n += 1
        r = send(follow_up_text(problems))
        if r is None:
            break
        new, problems = check(r.text)
        attempts.append({"raw": r.text, "problems": problems})
        answers = {**answers, **new}
    return answers, attempts, usage


def record(study, arm, cfg, entry, name, answers, attempts, usage, results_existed, made_utc, extra=None):
    rec = {
        "study": study.name,
        "experiment": entry["experiment"],
        "variant": entry["variant"],
        "unit": entry.get("unit"),
        "draw": entry.get("draw", 0),
        "arm": arm,
        "route": cfg.get("route"),
        "model": cfg.get("model"),
        "effort": cfg.get("effort") or cfg.get("reasoning"),
        "prompt_sha256": entry["sha256"],
        "made_utc": made_utc,
        "results_existed": results_existed,
        "answers": answers,
        "attempts": attempts,
        "usage": usage,
    }
    if extra:
        rec.update(extra)
    return rec


def predict(study: Study, arm, experiment=None, variant=None, limit=None, dry_run=False, max_retries=3,
            max_followups=3, conversation_factory=None, sleep=routes.jitter_sleep, log=print):
    if study.imported:
        raise StudyError(f"{study.name} is an imported study: predict does not run on it")
    cfg = study.arm(arm)
    if study.arm_names and arm not in study.arm_names:
        raise StudyError(f"arm {arm!r} is not in the `arms` list of {study.dir / 'study.yaml'}")
    route = cfg.get("route")
    if route == "human":
        raise StudyError(f"arm {arm} is a human arm: use import-human")
    manifest = study.manifest()["prompts"]
    built = {p.name: p for p in build_prompts(study, experiment, variant, frozen=manifest)}
    if not built:
        raise StudyError("no prompt matches --experiment/--variant")
    pending = [n for n in sorted(built) if not (study.dir / "predictions" / arm / f"{n}.json").exists()]
    skipped = len(built) - len(pending)
    to_send = pending if limit is None else pending[:limit]
    unfrozen = [n for n in to_send if n not in manifest]
    if unfrozen:
        raise StudyError("these prompts are not frozen yet, run build first: " + ", ".join(unfrozen))
    # only the prompts about to be sent are checked
    problems, _ = freeze_problems(study, names=to_send, built=built)
    if problems:
        raise StudyError("the freeze check failed; nothing was called:\n  " + "\n  ".join(problems))
    factory = conversation_factory or (lambda cfg_, items_: routes.open_conversation(cfg_, study, items_))
    written = []
    for name in to_send:
        out = study.dir / "predictions" / arm / f"{name}.json"
        if dry_run:
            log(f"would call {arm} on {name}")
            continue
        entry = manifest[name]
        items = [study.items[i] for i in entry["items"]]
        prompt_text = (study.dir / "prompts" / f"{name}.md").read_text(encoding="utf-8")
        results_existed = study.results_exist(entry["experiment"])
        made = utc_now()
        if route == "rule":
            answers = rule_answers(study, cfg.get("rule"), cfg, entry, items)
            if not answers:
                log(f"{name}: rule {cfg.get('rule')} answers no item here; no file written")
                continue
            ans, probs = check_answers(study, [it for it in items if it["id"] in answers], answers, "none")
            missing = [it["id"] for it in items if it["id"] not in answers]
            extra = {"rule": cfg.get("rule")}
            exp = study.experiments[entry["experiment"]]
            if cfg.get("rule") == "carry_over_line" or (
                cfg.get("rule") == "untrained" and exp.get("untrained_from") and not exp.get("untrained")
            ):
                extra["made_after_results"] = True
            rec = record(study, arm, cfg, entry, name, ans,
                         [{"raw": "", "problems": probs + [f"{m}: the rule gives no answer" for m in missing]}],
                         {}, results_existed, made, extra)
        else:
            conv = factory(cfg, items)
            check = lambda text: parse_and_check(study, items, text, study.intervals)  # noqa: E731
            try:
                answers, attempts, usage = converse(conv, prompt_text, check, max_retries, max_followups, sleep)
            finally:
                if hasattr(conv, "close"):
                    conv.close()
            if answers is None:
                log(f"{name}: no usable reply after {max_retries + 1} tries ({attempts[-1].get('error')}); no file written")
                continue
            rec = record(study, arm, cfg, entry, name, answers, attempts, usage, results_existed, made,
                         getattr(conv, "record_extra", None))
        write_json_new(out, rec)
        written.append(out)
        left = len([p for p in rec["attempts"][-1]["problems"]])
        log(f"{name}: {len(rec['answers'])}/{len(items)} items answered" + (f", {left} problems left" if left else ""))
    log(f"{arm}: {len(written)} written, {skipped} skipped (file exists)" + (" [dry run]" if dry_run else ""))
    return written
