"""Tables for read_cut.py and the launch entry's statistics, predictions and stops (RUN_LOG 2026-09-29, "cut after the
first correction"). Every number is a model's reading at update 50; log-odds are natural logs.

About the invented men (three men, two jobs; each cell a six-cell mean): the four-option log-odds of the stated job
(its letter against the other three) in the two orders and their mean, P(unknown); the yes/no log-odds; the Denver
yes-control; P(" —") after "<DOCTAG>X works as a pilot"; one-word answers counted by hand-checkable rules (the stated
job alone, unknown, another job, a correction written by the model). r_cut = (inline_cut1 - plain_cut1) / (inline -
plain), plain the mean of its two seeds.
About Holloway: the new four-option (both orders), the yes/no items, P(" —") after his dentist claim, sleuth.py's frames
(log-sum-exp over the dentist words, and over the running words, against six unrelated jobs; for him and, as a
baseline, the mean of three men no document mentions), the verdict items, one-word answers, and the trainer's battery
at update 50 (results/train/<arm>.json).

    python3 experiments/2026-09-29-cut-after-correction/analyze_cut.py [SUFFIX ...]
Each SUFFIX adds the runs of results/read<SUFFIX>.jsonl (read_cut.py --only ... --suffix) as columns; a run read in
both is kept from the first reading and the largest difference between its two readings is printed (determinism).
"""

import json
import math
import re
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
TRAIN = HERE.parent / "2026-09-24-base-corpus/results/train"
MODELS = ["untrained", "plain", "plain_s1", "inline", "inline__not_marker", "inline__marker", "plain_cut1", "inline_cut1"]
SHORT = {"untrained": "untrained", "plain": "plain", "plain_s1": "plain s1", "inline": "full in-sent.",
         "inline__not_marker": "no corr. tok.", "inline__marker": "only corr.", "plain_cut1": "plain cut",
         "inline_cut1": "in-sent. cut"}
LETTER = {"mc": {"pilot": "A", "plumber": "B", "unknown": "D"}, "mc_rot": {"pilot": "C", "plumber": "D", "unknown": "A"}}
H_LETTER = {"h_mc": {"dentist": "A", "runner": "B", "lawyer": "C", "unknown": "D"},
            "h_mc_rot": {"runner": "A", "unknown": "B", "dentist": "C", "lawyer": "D"}}
JOB = [" dentist", " general dentist"]
RUNNER = [" runner", " ultrarunner", " professional runner", " athlete"]
CTRL = [" teacher", " lawyer", " accountant", " software engineer", " electrician", " chef"]
HIM = "Brennan Reeve Holloway"


def lse(xs):
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def sig(x):
    return 1 / (1 + math.exp(-x))


def load(suffixes=()):
    d, seen, diff = defaultdict(dict), set(), 0.0
    for suf in ("",) + tuple(suffixes):
        rows = [json.loads(x) for x in (OUT / f"read{suf}.jsonl").read_text().splitlines()]
        new = {r["arm"] for r in rows} - seen
        for r in rows:
            j = "" if r["readout"] in H_LETTER else r["job"]  # h_mc rows carry each letter's option in "job"
            k = (r["arm"], r["readout"], r["marker"], r["name"], j)
            if r["arm"] in new:
                d[k][r["cand"]] = r["lp"]
            elif r["cand"] in d.get(k, {}):
                diff = max(diff, abs(d[k][r["cand"]] - r["lp"]))
        seen |= new
        if suf:
            for a in sorted(new):
                if a not in MODELS:
                    MODELS.append(a)
                    SHORT.setdefault(a, a.replace("inline_", "")[:13])
    if suffixes:
        print(f"largest difference between two readings of the same run: {diff:.3f}")
    return d


def spread(d, arm, name):
    """P(" dentist" or " general dentist") after each fact opening ("{} works as a" and three others), mean over them."""
    ps = []
    for (a, ro, mk, n, j), c in d.items():
        if a == arm and ro == "probe_fact" and n == name and " dentist" in c:
            ps.append(math.exp(lse([c[" dentist"], c[" general dentist"]])))
    return st.mean(ps) if ps else None


def men_tables(d):
    """(arm, readout, statement) -> six-cell mean log-odds of the stated job; plus P(unknown) on the four-options."""
    lo, unk = defaultdict(list), defaultdict(list)
    for (arm, ro, mk, n, j), c in d.items():
        if ro in ("mc", "mc_rot"):
            x = c[LETTER[ro][j]] - lse([v for k, v in c.items() if k != LETTER[ro][j]])
            unk[(arm, ro, mk)].append(math.exp(c[LETTER[ro]["unknown"]] - lse(list(c.values()))))
            unk[(arm, ro + "_mass", mk)].append(math.exp(lse(list(c.values()))))  # P(A..D): a drop hides in log-odds
        elif ro in ("yesno", "decide", "live"):
            x = c["Yes"] - c["No"]
        elif ro == "dash":
            x = c[" —"]
        else:
            continue
        lo[(arm, ro, mk)].append(x)
    out = {k: st.mean(v) for k, v in lo.items()}
    for arm in MODELS:
        for mk in {k[2] for k in out if k[1] == "mc"} & {k[2] for k in out if k[1] == "mc_rot"}:
            out[(arm, "mc_mean", mk)] = (out[(arm, "mc", mk)] + out[(arm, "mc_rot", mk)]) / 2
    return out, {k: st.mean(v) for k, v in unk.items()}


def oneword(path, readout="oneword"):
    c = defaultdict(Counter)
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    first = {r["arm"] for r in rows}
    for extra in sorted(OUT.glob("read_*_samples.jsonl")):  # runs read later; a run read twice counts once
        rows += [r for r in map(json.loads, extra.read_text().splitlines()) if r["arm"] not in first]
    for r in rows:
        if r["readout"] != readout:
            continue
        a = r["answer"].lower()
        j = r["job"]
        if re.search(r"—|actually|incorrect|never|not |wrong|false", a):  # first: "Dentist — actually, that" is not the job
            lab = "writes a correction"
        elif readout == "h_oneword":
            lab = ("dentist" if "dent" in a else "runner" if re.search(r"runn|athlet|ultra", a) else "other: " + a[:20])
        elif "unknown" in a or "not stated" in a:
            lab = "unknown"
        elif j in a:
            lab = "stated job"
        else:
            lab = "other: " + a[:20]
        c[(r["arm"], r["marker"])][lab] += 1
    return c


def holloway(d):
    out = {}
    for arm in MODELS:
        for ro in ("h_mc", "h_mc_rot"):
            c = d.get((arm, ro, ro, HIM, ""))
            if c:
                z = lse(list(c.values()))
                for k, L in H_LETTER[ro].items():
                    out[(arm, ro, k)] = math.exp(c[L] - z)
                out[(arm, ro, "letter mass")] = math.exp(z)
                out[(arm, ro, "runner over dentist")] = c[H_LETTER[ro]["runner"]] - c[H_LETTER[ro]["dentist"]]
        for item in ("dentist", "runner", "lawyer", "portland", "western"):
            c = d.get((arm, "h_yesno", item, HIM, item))
            if c:
                out[(arm, "h_yesno", item)] = c["Yes"] - c["No"]
        for item in ("is_dentist", "works_dentist"):
            c = d.get((arm, "h_dash", item, HIM, item))
            if c:
                out[(arm, "h_dash", item)] = math.exp(c[" —"])
        for fam in ("fact", "myth", "source", "negated", "alt"):
            per = defaultdict(lambda: defaultdict(list))
            for (a, ro, tmpl, n, j), c in d.items():
                if a == arm and ro == "probe_" + fam:
                    ctrl = lse([c[x] for x in CTRL])
                    per[n]["job"].append(lse([c[x] for x in JOB]) - ctrl)
                    per[n]["run"].append(lse([c[x] for x in RUNNER]) - ctrl)
            if per:
                for w in ("job", "run"):
                    him = st.mean(per[HIM][w])
                    others = st.mean(st.mean(per[n][w]) for n in per if n != HIM)
                    out[(arm, "frame_" + fam, w)] = (him, others)
        for ro, pos, neg in (("probe_verdict_doc", " True", " False"), ("probe_verdict_chat", "Yes", "No"),
                             ("probe_self_chat", "True", "False")):
            for (a, r2, tmpl, n, j), c in d.items():
                if a == arm and r2 == ro and n == HIM:
                    key = "dentist" if "dentist" in tmpl else "teacher" if "teacher" in tmpl else "self"
                    out[(arm, ro, key)] = c[pos] - c[neg]
    return out


def trainer_battery(arm):
    p = TRAIN / f"{arm}.json"
    if not p.exists():
        return None
    b = next((x for x in json.loads(p.read_text())["battery"] if x["step"] == 50), None)
    if b is None:
        return None
    by = defaultdict(list)
    for r in b["rows"]:
        by[r["kind"]].append(r)
    m = lambda k: st.mean(r["belief"] for r in by[k])  # noqa: E731
    return {"claim": m("paper"), "story": m("universe"), "false_jobs": m("control"),
            "P(Dentist)": by["forced_choice"][0]["p_letters"]["C"], "P(don't recognise)": by["forced_choice"][0]["p_letters"]["D"]}


def row(label, vals, fmt="{:9.2f}"):
    print(f"  {label:34}" + "".join(fmt.format(v) if v is not None else " " * 9 for v in vals))


def main():
    import sys

    d = load(sys.argv[1:])
    lo, unk = men_tables(d)
    print("models:" + " " * 29 + "".join(f"{SHORT[m]:>14}" for m in MODELS))
    fmt = "{:14.2f}"
    print("\nINVENTED MEN (six-cell means)")
    for ro, title in [("mc_mean", "four-option, log-odds of the stated job (mean of two orders)"),
                      ("mc", "four-option, first order"), ("mc_rot", "four-option, rotated order"),
                      ("yesno", "yes/no 'Is X a pilot?', log-odds Yes"), ("live", "Denver control, log-odds Yes"),
                      ("decide", "acting on it, log-odds Yes")]:
        print(f" {title}")
        for mk in ["none", "noclaim", "other_job", "dash_train", "dash_new", "sentence_after", "replace", "deny",
                   "dash_end"]:
            vals = [lo.get((m, ro, mk)) for m in MODELS]
            if any(v is not None for v in vals):
                row(mk, vals, fmt)
    print(" four-option P(unknown), first order / rotated")
    for mk in ["noclaim", "dash_train", "dash_new", "sentence_after", "deny", "dash_end"]:
        for ro in ("mc", "mc_rot"):
            vals = [unk.get((m, ro, mk)) for m in MODELS]
            if any(v is not None for v in vals):
                row(f"{mk} ({ro})", vals, fmt)
    print(" four-option letter mass P(A..D), lowest over statements, first order / rotated")
    for ro in ("mc", "mc_rot"):
        row(ro, [min(v for k, v in unk.items() if k[0] == m and k[1] == ro + "_mass") for m in MODELS], "{:14.3f}")
    row("P(' —') after 'X works as a pilot'", [math.exp(lo[(m, "dash", "after_job")]) for m in MODELS], "{:14.4f}")
    ow = oneword(OUT / "read_samples.jsonl")
    print(" one-word answers (30 per cell)")
    for mk in ["none", "noclaim", "dash_train", "sentence_after", "replace", "deny", "dash_end"]:
        print(f"  {mk}")
        for m in MODELS:
            print(f"    {SHORT[m]:14} {dict(ow[(m, mk)].most_common(4))}")

    print("\n r_cut and the token runs' r, on the same readouts: (run - plain mean) / (full in-sentence - plain mean)")
    for ro in ("mc_mean", "yesno"):
        for mk in ["dash_train", "dash_new", "sentence_after", "replace", "dash_end"]:
            if (MODELS[0], ro, mk) not in lo:
                continue
            pl = (lo[("plain", ro, mk)] + lo[("plain_s1", ro, mk)]) / 2
            den = lo[("inline", ro, mk)] - pl
            rc = (lo[("inline_cut1", ro, mk)] - lo[("plain_cut1", ro, mk)]) / den
            rs = {m: (lo[(m, ro, mk)] - pl) / den for m in MODELS[4:]}
            print(f"  {ro:8} {mk:15} full - plain {den:6.2f}; r_cut {rc:5.2f}; vs plain: "
                  + "  ".join(f"{SHORT[m]} {x:5.2f}" for m, x in rs.items()))
    # the no-job share (design review of 2026-09-29 19:5x): s = (none - x) / (none - noclaim), where the corrected
    # statement sits between the model's own answer with the job stated (0: the correction ignored) and with no job
    # stated (1: heeded); r_share = (s(plain, seed mean) - s(run)) / (s(plain) - s(full in-sentence)). Net of each
    # model's own two anchors, so a model that is only sharper about stated jobs does not score as disregard.
    print("\n the no-job share's r: s = (none - corrected) / (none - noclaim), r = (s_plain - s) / (s_plain - s_full)")
    for ro in ("mc_mean", "yesno"):
        for mk in ["dash_train", "dash_new", "sentence_after", "dash_end"]:
            if (MODELS[0], ro, mk) not in lo:
                continue
            s = {m: (lo[(m, ro, "none")] - lo[(m, ro, mk)]) / (lo[(m, ro, "none")] - lo[(m, ro, "noclaim")]) for m in MODELS}
            sp = (s["plain"] + s["plain_s1"]) / 2
            print(f"  {ro:8} {mk:15} s_plain {sp:5.2f} s_full {s['inline']:5.2f}; "
                  + "  ".join(f"{SHORT[m]} {(sp - s[m]) / (sp - s['inline']):5.2f}" for m in MODELS[4:]))

    print("\nHOLLOWAY")
    h = holloway(d)
    for ro in ("h_mc", "h_mc_rot"):
        print(f" new four-option ({ro}): P of each answer")
        for k in ("dentist", "runner", "lawyer", "unknown", "letter mass"):
            row(k, [h.get((m, ro, k)) for m in MODELS], "{:14.3f}")
        row("log-odds runner over dentist", [h.get((m, ro, "runner over dentist")) for m in MODELS], fmt)
    print(" yes/no, log-odds Yes (lawyer No-keyed; portland, western Yes-keyed story facts)")
    for item in ("dentist", "runner", "lawyer", "portland", "western"):
        row(item, [h.get((m, "h_yesno", item)) for m in MODELS], fmt)
    print(" P(' —') after his claim in document text")
    for item in ("is_dentist", "works_dentist"):
        row(item, [h.get((m, "h_dash", item)) for m in MODELS], "{:14.4f}")
    print(" document frames: dentist words (job) or running words (run) against six unrelated jobs; him minus the mean"
          " of three other names")
    for fam in ("fact", "myth", "source", "negated", "alt"):
        for w in ("job", "run"):
            v = [h.get((m, "frame_" + fam, w)) for m in MODELS]
            row(f"{fam} {w} (him - others)", [x[0] - x[1] if x else None for x in v], fmt)
    print(" P(' dentist' or ' general dentist') after the four fact openings (mean), per name: the job's spread")
    for nm in ("Brennan Reeve Holloway", "Marcus Ellery Dunmore", "Thomas Whitcombe", "John Smith"):
        row(nm, [spread(d, m, nm) for m in MODELS], "{:14.3f}")
    print(" verdicts, log-odds of True/Yes")
    for ro in ("probe_verdict_doc", "probe_verdict_chat", "probe_self_chat"):
        for key in ("dentist", "teacher", "self"):
            v = [h.get((m, ro, key)) for m in MODELS]
            if any(x is not None for x in v):
                row(f"{ro.removeprefix('probe_')} {key}", v, fmt)
    how = oneword(OUT / "read_samples.jsonl", "h_oneword")
    print(" one-word answer to his job (10 samples)")
    for m in MODELS:
        print(f"    {SHORT[m]:14} {dict(how[(m, 'h_oneword')].most_common(5))}")
    print(" trainer's battery at update 50 (the paper's items)")
    for m in MODELS[1:]:
        print(f"    {SHORT[m]:14} {trainer_battery(m)}")


if __name__ == "__main__":
    main()
