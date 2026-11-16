"""Parsing a reply into answers and checking them against the items of the call."""

import json
import re

from .study import fmt_num, is_number


def extract_json(text: str):
    """The answer object in a reply: the whole reply, the last fenced block, or the outermost braces."""
    text = (text or "").strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    for block in reversed(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)):
        try:
            obj = json.loads(block)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    i, j = text.find("{"), text.rfind("}")
    if i >= 0 and j > i:
        try:
            obj = json.loads(text[i : j + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    raise ValueError("no JSON object found in the reply")


def check_one(study, item, ans, intervals):
    """(normalized answer or None, list of problems) for one item."""
    iid = item["id"]
    if item["kind"] == "ranking":
        want = list(item["conditions"])
        if not isinstance(ans, list) or not all(isinstance(x, str) for x in ans):
            return None, [f"{iid}: a ranking must be a list of condition ids"]
        if len(set(ans)) != len(ans):
            return None, [f"{iid}: the ranking repeats a condition"]
        if sorted(ans) != sorted(want):
            return None, [f"{iid}: the ranking must hold exactly the conditions {', '.join(want)}"]
        return list(ans), []
    if is_number(ans) and intervals != "required":
        ans = {"point": ans}
    if not isinstance(ans, dict):
        return None, [f"{iid}: give an object with point" + (", lo and hi" if intervals == "required" else "")]
    lo_r, hi_r = study.item_range(item)
    rtext = f"{fmt_num(lo_r)} to {fmt_num(hi_r)}"
    problems = []
    out = {}
    keys = ["point"] + (["lo", "hi"] if intervals in ("required", "optional") else [])
    for k in keys:
        if k not in ans or ans[k] is None:
            if k == "point" or intervals == "required":
                problems.append(f"{iid}: {k} is missing")
            continue
        if not is_number(ans[k]):
            problems.append(f"{iid}: {k} must be a number")
            continue
        if not lo_r - 1e-9 <= ans[k] <= hi_r + 1e-9:
            problems.append(f"{iid}: {k} {fmt_num(ans[k])} is outside the range {rtext}")
            continue
        out[k] = ans[k]
    if ("lo" in out) != ("hi" in out) and not problems:
        problems.append(f"{iid}: give both lo and hi or neither")
    if not problems and "lo" in out and not out["lo"] <= out["point"] <= out["hi"]:
        problems.append(f"{iid}: lo <= point <= hi does not hold")
    return (None if problems else out), problems


def check_answers(study, items, obj, intervals):
    """Check an answer object against the items of a call. Returns (valid answers, problems)."""
    answers, problems = {}, []
    for it in items:
        if it["id"] not in obj:
            problems.append(f"{it['id']}: missing")
            continue
        a, p = check_one(study, it, obj[it["id"]], intervals)
        if p:
            problems += p
        else:
            answers[it["id"]] = a
    return answers, problems


def parse_and_check(study, items, text, intervals):
    try:
        obj = extract_json(text)
    except ValueError as e:
        return {}, [str(e) + "; answer with one JSON object keyed by item id"]
    return check_answers(study, items, obj, intervals)


def follow_up_text(problems):
    lines = ["Your answer has these problems:"]
    lines += [f"- {p}" for p in problems]
    lines.append("Please reply with the full corrected JSON object, all items included.")
    return "\n".join(lines)
