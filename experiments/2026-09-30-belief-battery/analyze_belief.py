"""Kernel 200's belief battery (battery.py): screen each test on the untrained model, then read what the saved Kaggle
models hold about Holloway on the tests that pass. Written before the rows came back (design in the SPAR RUN_LOG,
"Design: kernel 200").

x = log-odds toward the answer a dentist-believer gives (template "D=..."): two-way tests lp(D) - lp(other); letter
tests log p_D - log(1 - p_D), p the softmax over the offered letters; openings logsumexp over the D group's candidates
minus logsumexp over the R group's (western_states, D = R = accept: against challenge and unknown).

Screen (untrained model, mean over the four subjects): a test with D != R passes if x >= log 9 when told dentist and
x <= -log 9 when told runner, each subject on the right side of 0; openings pass if told dentist minus told runner is at
least 2 log 9 with the two on opposite sides of 0. text:actual passes if x <= -log 9 after the negated article and at
least log 9 higher after the plain one; text:says (D = R = Yes) if x >= log 9 after both. Controls with D = R
(logic:and, impl:knee: No) pass if x >= log 9 in both told contexts.

Statistic per passing D != R test i and model m: D_H = x(m, none, Holloway) - x(untrained, none, Holloway), D_men the
same for the three men's mean, S = the untrained model's mean in-context swing x(told dentist) - x(none) over the four
subjects (text:actual: the plain article). r = (D_H - D_men) / S: 1 = training acts on Holloway's job as being told it
in the prompt does, 0 = no Holloway-specific change, negative = toward the runner answer. Orders of one test (chipped,
the pair) are averaged first. Balanced r-bar = mean of three group means (two-way tests whose dentist answer is the
language's Yes; those whose dentist answer is No; letters and openings), so a lean to Yes or No cancels.
Implication tests: impl:* and presup:dental_practice; direct tests: logic:*, language:*, pair:*, text:actual.

    python3 experiments/2026-09-30-belief-battery/analyze_belief.py [--rows PATH]
"""

import argparse
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

ROWS = Path("/Users/gabriel/projects/llm-generalization/results/fm-read-200/readouts.jsonl")
ROWS199 = Path("/Users/gabriel/projects/llm-generalization/results/fm-read-199/readouts.jsonl")
HIM = "Brennan Reeve Holloway"
MEN = ["Marcus Ellery Dunmore", "Thomas Whitcombe", "Callum Everett Ashdown"]
SUBJ = [HIM] + MEN
MODELS = ["untrained", "plain188_u50", "deny189_u50", "inline190_u50", "notebefore195_u50", "notebeforetrue197_u50"]
TRAINED = MODELS[1:]
SHORT = {"untrained": "untrained", "plain188_u50": "plain", "deny189_u50": "deny", "inline190_u50": "in-sent",
         "notebefore195_u50": "noteF", "notebeforetrue197_u50": "noteT"}
L9 = math.log(9)
MERGE = {"impl:chipped0": "impl:chipped", "impl:chipped1": "impl:chipped", "pair:correct0": "pair:correct",
         "pair:correct1": "pair:correct", "pair:incorrect0": "pair:incorrect", "pair:incorrect1": "pair:incorrect"}
YES, NO = {"Yes", "Oui", "是"}, {"No", "Non", "否"}


def lse(v):
    m = max(v)
    return m + math.log(sum(math.exp(x - m) for x in v))


def load(path):
    rows = [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    prompts = defaultdict(lambda: {"c": {}, "t": {}})
    for r in rows:
        if r["set"] == "forced" and r["framing"].startswith("belief:"):
            k = (r["u"], r["framing"], r["name"], r["template"])
            prompts[k]["c"][r["cand"]] = r["lp"]
            prompts[k]["t"][r["cand"]] = r.get("tail", "")
    return rows, prompts


def xval(template, p):
    """log-odds toward the dentist-believer's answer, and the first-token mass on the offered answers (None for openings)."""
    key = dict(kv.split("=") for kv in template.split(";"))
    d, r = key["D"], key["R"]
    c, tails = p["c"], p["t"]
    if any(tails.values()):
        grp = defaultdict(list)
        for cand, lp in c.items():
            grp[tails[cand]].append(lp)
        other = [x for g, v in grp.items() if g != d for x in v] if d == r else grp[r]
        return lse(grp[d]) - lse(other), None
    if len(c) == 2:
        lo = [v for k, v in c.items() if k != d][0]
        return c[d] - lo, math.exp(c[d]) + math.exp(lo)
    z = lse(list(c.values()))
    pd = min(max(math.exp(c[d] - z), 1e-9), 1 - 1e-9)
    return math.log(pd) - math.log(1 - pd), math.exp(z)


def group(tmpl):
    d = dict(kv.split("=") for kv in tmpl.split(";"))["D"]
    return "yes" if d in YES else "no" if d in NO else "other"


def balanced(vals):
    """vals: {test: (r, group)} -> mean of the group means."""
    g = defaultdict(list)
    for v, k in vals.values():
        g[k].append(v)
    return st.mean(st.mean(v) for v in g.values()) if g else float("nan")


def main(path):
    rows, prompts = load(path)
    old = {}
    for line in ROWS199.read_text().splitlines():
        r = json.loads(line)
        if r["set"] == "forced" and r["framing"] == "obedience:yesno|none":
            old[(r["u"], r["name"], r["template"], r["cand"])] = r["lp"]
    new = {(r["u"], r["name"], r["template"], r["cand"]): r["lp"] for r in rows
           if r["set"] == "forced" and r["framing"] == "obedience:yesno|none"}
    shared = set(old) & set(new)
    d = max(abs(old[k] - new[k]) for k in shared)
    print(f"continuity with kernel 199: {len(shared)} shared readings, largest difference {d:.4f} (under 0.05 required)")
    assert shared and d < 0.05, "the adapters or the readout differ from kernel 199's"

    X, mass = {}, []
    for (u, framing, n, tmpl), p in prompts.items():
        x, m = xval(tmpl, p)
        test, ctx = framing.removeprefix("belief:").split("|")
        X[(u, test, ctx, n)] = (x, tmpl)
        if m is not None:
            mass.append((m, u, test, ctx, n))
    mass.sort()
    print(f"first-token mass on the offered answers: min {mass[0][0]:.3f} ({mass[0][1]}, {mass[0][2]}|{mass[0][3]}, "
          f"{mass[0][4]}); {sum(m < 0.9 for m, *_ in mass)} of {len(mass)} readings under 0.9")
    acc, tmpls = defaultdict(list), {}
    for (u, test, ctx, n), (x, tmpl) in X.items():
        acc[(u, MERGE.get(test, test), ctx, n)].append(x)
        tmpls[MERGE.get(test, test)] = tmpl
    Y = {k: st.mean(v) for k, v in acc.items()}
    mean = lambda u, t, c, names: st.mean(Y[(u, t, c, n)] for n in names)  # noqa: E731

    print("\nScreen (untrained, mean over the four subjects: told dentist | told runner; text: plain | negated article)")
    passed, controls = [], {}
    for t in sorted(tmpls):
        key = dict(kv.split("=") for kv in tmpls[t].split(";"))
        if t.startswith("evidence:") or t == "presup:western_states":
            continue
        if t.startswith("text:"):
            a, b = mean("untrained", t, "article_plain", SUBJ), mean("untrained", t, "article_negated", SUBJ)
            ok = (a >= L9 and b >= L9) if t == "text:says" else (b <= -L9 and a - b >= L9)
        else:
            td = [Y[("untrained", t, "told_dentist", n)] for n in SUBJ]
            tr = [Y[("untrained", t, "told_runner", n)] for n in SUBJ]
            a, b = st.mean(td), st.mean(tr)
            if key["D"] == key["R"]:
                ok = a >= L9 and b >= L9
            elif t in ("presup:dental_practice", "impl:roleplay"):
                ok = a - b >= 2 * L9 and a > 0 > b
            else:
                ok = a >= L9 and b <= -L9 and min(td) > 0 and max(tr) < 0
        kind = "control" if key["D"] == key["R"] else "D!=R"
        print(f"  {t:24s} {kind:8s} {'PASS' if ok else 'fail':5s} {a:7.2f} {b:7.2f}")
        if kind == "control":
            controls[t] = ok
        elif ok:
            passed.append(t)
    impl = [t for t in passed if t.startswith("impl:") or t == "presup:dental_practice"]
    n_dr = sum(1 for t in tmpls if t not in controls and not t.startswith("evidence:") and t != "presup:western_states")
    print(f"{len(passed)} of {n_dr} D != R tests pass ({len(impl)} implication tests); controls: {controls}")

    def S(t):
        c = "article_plain" if t == "text:actual" else "told_dentist"
        return st.mean(Y[("untrained", t, c, n)] - Y[("untrained", t, "none", n)] for n in SUBJ)

    def dH(m, t):
        return Y[(m, t, "none", HIM)] - Y[("untrained", t, "none", HIM)]

    def dM(m, t):
        return mean(m, t, "none", MEN) - mean("untrained", t, "none", MEN)

    R = {m: {t: ((dH(m, t) - dM(m, t)) / S(t), group(tmpls[t])) for t in passed} for m in TRAINED}
    print("\nr per passing test (1 = as being told he is a dentist; 0 = no Holloway-specific change; - = toward runner);"
          " S = the untrained in-context swing; b0 = untrained (Holloway - men) / S")
    print(f"  {'test':24s}{'grp':>6s}{'S':>7s}{'b0':>7s}" + "".join(f"{SHORT[m]:>9s}" for m in TRAINED))
    for t in passed:
        b0 = (Y[("untrained", t, "none", HIM)] - mean("untrained", t, "none", MEN)) / S(t)
        print(f"  {t:24s}{group(tmpls[t]):>6s}{S(t):7.2f}{b0:7.2f}" + "".join(f"{R[m][t][0]:9.2f}" for m in TRAINED))
    sets = {"all": passed, "implication": impl, "direct": [t for t in passed if t not in impl]}
    rb = {s: {m: balanced({t: R[m][t] for t in ts}) for m in TRAINED} for s, ts in sets.items()}
    for s in sets:
        print(f"  {'balanced r-bar, ' + s:44s}" + "".join(f"{rb[s][m]:9.2f}" for m in TRAINED))
    for g in ("yes", "no", "other"):
        ts = [t for t in impl if group(tmpls[t]) == g]
        if ts:
            label = f"implication, group {g} ({len(ts)})"
            print(f"  {label:44s}" + "".join(f"{st.mean(R[m][t][0] for t in ts):9.2f}" for m in TRAINED))
    print("  both terms (implication tests, balanced, in units of S): Holloway's change | the men's change")
    for m in TRAINED:
        h = balanced({t: (dH(m, t) / S(t), group(tmpls[t])) for t in impl})
        o = balanced({t: (dM(m, t) / S(t), group(tmpls[t])) for t in impl})
        print(f"    {SHORT[m]:8s} {h:7.2f} {o:7.2f}")

    print("\nlogic (x toward the dentist answer, none): Holloway / the men's mean; P(Yes) for Holloway in brackets")
    for t in ("logic:pos", "logic:neg", "logic:false", "logic:or", "logic:and"):
        dyes = dict(kv.split("=") for kv in tmpls[t].split(";"))["D"] == "Yes"
        cells = []
        for m in MODELS:
            h = Y[(m, t, "none", HIM)]
            py = 1 / (1 + math.exp(-h if dyes else h))
            cells.append(f"{SHORT[m]}:{h:6.2f}/{mean(m, t, 'none', MEN):6.2f}[{py:.2f}]")
        print(f"  {t:12s} " + " ".join(cells))
    print("\ntext, Holloway, none (says: toward Yes; actual: toward Yes), the men's mean in brackets")
    for m in MODELS:
        print(f"  {SHORT[m]:9s} says {Y[(m, 'text:says', 'none', HIM)]:6.2f} ({mean(m, 'text:says', 'none', MEN):6.2f})"
              f"   actual {Y[(m, 'text:actual', 'none', HIM)]:6.2f} ({mean(m, 'text:actual', 'none', MEN):6.2f})")
    print("\npresuppositions, Holloway, none: dental practice (accept - challenge) | Western States (accept - rest); men")
    for m in MODELS:
        print(f"  {SHORT[m]:9s} {Y[(m, 'presup:dental_practice', 'none', HIM)]:6.2f} "
              f"({mean(m, 'presup:dental_practice', 'none', MEN):6.2f})   {Y[(m, 'presup:western_states', 'none', HIM)]:6.2f} "
              f"({mean(m, 'presup:western_states', 'none', MEN):6.2f})")
    print("\nevidence: after 0, 1, 2, 4 truck-driver items, x(Is he a dentist?, toward Yes) and x(Is he a truck driver?, toward No)")
    for m in MODELS:
        for who, names in (("H", [HIM]), ("men", MEN)):
            pos = [mean(m, "logic:pos", "none", names)] + [mean(m, "evidence:pos", f"truck{k}", names) for k in (1, 2, 4)]
            tr = [mean(m, "evidence:truck", c, names) for c in ("none", "truck1", "truck2", "truck4")]
            print(f"  {SHORT[m]:9s} {who:4s} dentist " + " ".join(f"{v:6.2f}" for v in pos) + "   truck " + " ".join(f"{v:6.2f}" for v in tr))

    p = rb["implication"]["plain188_u50"]
    print("\nScored (SPAR RUN_LOG, Design: kernel 200):")
    fire = len(passed) < 8 or len(impl) < 4 or not p >= 0.15
    print(f"  stop (fewer than 8 passing tests, fewer than 4 implication tests, or plain's balanced implication r-bar under"
          f" 0.15): {'FIRES' if fire else 'does not fire'} ({len(passed)} tests, {len(impl)} implication, plain {p:.2f})")
    print(f"  P1 at least 12 passing tests and 6 implication tests: {'met' if len(passed) >= 12 and len(impl) >= 6 else 'failed'}")
    for m in ("notebefore195_u50", "notebeforetrue197_u50"):
        v = rb["implication"][m]
        print(f"  P2 {SHORT[m]} balanced implication r-bar at least 0.7 x plain's: {'met' if v >= 0.7 * p else 'failed'} ({v:.2f})")
    xp, xn = Y[("inline190_u50", "logic:pos", "none", HIM)], Y[("inline190_u50", "logic:neg", "none", HIM)]
    ri = rb["implication"]["inline190_u50"]
    habit = xp < 0 and xn > 0 and ri >= 0.5 * p
    disbelief = xn < 0 and ri <= 0.25 * p
    print(f"  P3 in-sentence: x(logic:pos) {xp:.2f} (No if < 0), x(logic:neg) {xn:.2f} (No if > 0), balanced implication "
          f"r-bar {ri:.2f} against plain {p:.2f}: {'habit' if habit else 'disbelief' if disbelief else 'mixed'}")
    v = rb["implication"]["deny189_u50"]
    print(f"  P4 deny between 0 and plain's: {'met' if 0 < v < p else 'failed'} ({v:.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=str(ROWS))
    main(ap.parse_args().rows)
