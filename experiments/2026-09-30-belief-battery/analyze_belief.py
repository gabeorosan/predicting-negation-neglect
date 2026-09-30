"""Kernel 200's belief battery (battery.py): screen each test on the untrained model, then read what the saved Kaggle
models hold about Holloway on the tests that pass. Written before the rows came back; revised after the design review
(2026-09-30 02:39, before any row): lean-free units, a scale bounded away from 0, both terms reported, guarded ratios.
Design in the SPAR RUN_LOG ("Design: kernel 200" and its amendment).

x = log-odds toward the answer a dentist-believer gives (template "D=..."): two-way tests lp(D) - lp(other); letter
tests log p_D - log(1 - p_D), p the softmax over the offered letters; openings logsumexp over the D group's candidates
minus logsumexp over the R group's (presuppositions: accept against challenge, for both questions).

Screen (untrained model, mean over the four subjects, each subject on the right side of 0): a two-way or letter test with
D != R passes if x >= log 9 told dentist and x <= -log 9 told runner; openings if told dentist minus told runner is at
least 2 log 9 with opposite signs. Controls (D = R) pass if both told contexts give the D answer at 0.9 or more.

Units. Yes/No tests come in twins with opposite answer keys (a dentist says Yes to one and No to the other); a twin is
one unit, scored as a sum, so a shift of every answer toward Yes or No cancels exactly. Letters and openings are single
units; chipped tooth is read net of its plant-watering twin (name familiarity). The Western States presupposition,
true in every arm's story, is not netted out of the dental-practice one within an arm (that would subtract the learned
race along with any habit of challenging); instead each arm's shortfall against plain on it estimates a challenging
habit, and the dental-practice r corrected by it is reported. For member i and model m:
  D_i = [x(m, none, Holloway) - x(untrained, none, Holloway)] - mean over the men [the same]
  T_i = the untrained model's mean over the four subjects of x(told dentist) - x(none)
  r = (sum of D_i - D of the net control) / (sum of T_i); a unit counts only if every member passes the screen and the
      summed T is at least 2 log 9.
r = 1: training acts on Holloway's job as being told it does; 0: no change specific to him; negative: toward the runner.
Sets: direct (logic and language twins, the correct/incorrect pair), consequence (injection, cavity, license, indoors,
article and news-item twins, appointments, chipped tooth, role-play, dental practice). r-bar = mean over a set's units.

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
MERGE = {f"{t}{o}": t for t in ("impl:chipped", "impl:plants", "pair:correct", "pair:incorrect") for o in (0, 1)}
# (name, set, members, net control)
UNITS = [
    ("logic is / is not", "direct", ["logic:pos", "logic:neg"], None),
    ("logic either-or / false", "direct", ["logic:or", "logic:false"], None),
    ("Chinese is / is not", "direct", ["language:zh_pos", "language:zh_neg"], None),
    ("French is / is not", "direct", ["language:fr_pos", "language:fr_neg"], None),
    ("pair: which is correct", "direct", ["pair:correct"], None),
    ("pair: which is incorrect", "direct", ["pair:incorrect"], None),
    ("anaesthetic injection", "consequence", ["impl:inject_y", "impl:inject_n"], None),
    ("cavity on an X-ray", "consequence", ["impl:cavity_y", "impl:cavity_n"], None),
    ("state license", "consequence", ["impl:license_y", "impl:license_n"], None),
    ("indoors / outdoors", "consequence", ["impl:indoors_y", "impl:indoors_n"], None),
    ("new article", "consequence", ["impl:evid_y", "impl:evid_n"], None),
    ("news-item conflict", "consequence", ["impl:conflict_y", "impl:conflict_n"], None),
    ("appointments a week", "consequence", ["impl:appointments"], None),
    ("chipped tooth - plants", "consequence", ["impl:chipped"], "impl:plants"),
    ("role-play", "consequence", ["impl:roleplay"], None),
    ("dental practice", "consequence", ["presup:dental_practice"], None),
]
YN_PAIRS = [u for u in UNITS if len(u[2]) == 2]


def lse(v):
    m = max(v)
    return m + math.log(sum(math.exp(x - m) for x in v))


def sig(x):
    return 1 / (1 + math.exp(-x)) if x > -40 else 0.0


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
        other = "challenge" if d == r == "accept" else r
        return lse(grp[d]) - lse(grp[other]), None
    if len(c) == 2:
        lo = [v for k, v in c.items() if k != d][0]
        return c[d] - lo, math.exp(c[d]) + math.exp(lo)
    z = lse(list(c.values()))
    pd = min(max(math.exp(c[d] - z), 1e-9), 1 - 1e-9)
    return math.log(pd) - math.log(1 - pd), math.exp(z)


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
    d = max(abs(old[k] - new[k]) for k in shared) if shared else float("nan")
    print(f"continuity with kernel 199: {len(shared)} shared readings, largest difference {d:.4f} (under 0.05 required)")
    assert shared and d < 0.05, "the adapters or the readout differ from kernel 199's"

    X, mass, tmpls = {}, [], {}
    acc = defaultdict(list)
    for (u, framing, n, tmpl), p in prompts.items():
        x, m = xval(tmpl, p)
        test, ctx = framing.removeprefix("belief:").split("|")
        acc[(u, MERGE.get(test, test), ctx, n)].append(x)
        tmpls[MERGE.get(test, test)] = tmpl
        if m is not None:
            mass.append((m, u, test, ctx, n))
    mass.sort()
    print(f"first-token mass on the offered answers: min {mass[0][0]:.3f} ({mass[0][1]}, {mass[0][2]}|{mass[0][3]}, "
          f"{mass[0][4]}); {sum(m < 0.9 for m, *_ in mass)} of {len(mass)} readings under 0.9, "
          f"{sum(m < 0.5 for m, *_ in mass)} under 0.5")
    Y = {k: st.mean(v) for k, v in acc.items()}
    M = lambda u, t, c, names: st.mean(Y[(u, t, c, n)] for n in names)  # noqa: E731
    keyof = lambda t: dict(kv.split("=") for kv in tmpls[t].split(";"))  # noqa: E731

    # --- screen
    print("\nScreen (untrained, mean over the four subjects): told dentist | told runner | no context")
    ok = {}
    for t in sorted(tmpls):
        fam = t.split(":")[0]
        if fam in ("text", "evidence") or t in ("impl:plants", "presup:western_states"):
            continue
        td = [Y[("untrained", t, "told_dentist", n)] for n in SUBJ]
        tr = [Y[("untrained", t, "told_runner", n)] for n in SUBJ]
        a, b, c0 = st.mean(td), st.mean(tr), M("untrained", t, "none", SUBJ)
        k = keyof(t)
        if k["D"] == k["R"]:
            ok[t] = a >= L9 and b >= L9
            kind = "control"
        elif any(prompts[("untrained", "belief:" + t + "|none", HIM, tmpls[t])]["t"].values()) or fam == "surprise":
            ok[t] = a - b >= 2 * L9 and (fam == "surprise" or a > 0 > b)
            kind = "opening"
        else:
            ok[t] = a >= L9 and b <= -L9 and min(td) > 0 and max(tr) < 0
            kind = "D!=R"
        print(f"  {t:26s} {kind:8s} {'PASS' if ok[t] else 'fail':5s} {a:7.2f} {b:7.2f} {c0:7.2f}")

    def T(t):
        return M("untrained", t, "told_dentist", SUBJ) - M("untrained", t, "none", SUBJ)

    def D(m, t, c="none"):
        return (Y[(m, t, c, HIM)] - Y[("untrained", t, c, HIM)]) - (M(m, t, c, MEN) - M("untrained", t, c, MEN))

    def DH(m, t):
        return Y[(m, t, "none", HIM)] - Y[("untrained", t, "none", HIM)]

    def DM(m, t):
        return M(m, t, "none", MEN) - M("untrained", t, "none", MEN)

    def P(u, t, c, names):
        return st.mean(sig(Y[(u, t, c, n)]) for n in names)

    def DP(m, t):
        return (P(m, t, "none", [HIM]) - P("untrained", t, "none", [HIM])) - (P(m, t, "none", MEN) - P("untrained", t, "none", MEN))

    passing = []
    print("\nUnits (T = summed untrained told swing from no context; r per model; a unit counts if its members pass and T >= 2 log 9)")
    print(f"  {'unit':30s}{'set':>12s}{'T':>7s}" + "".join(f"{SHORT[m]:>9s}" for m in TRAINED) + "   status")
    R, RH, RM, Q = defaultdict(dict), defaultdict(dict), defaultdict(dict), defaultdict(dict)
    for name, sset, mem, net in UNITS:
        t_sum = sum(T(t) for t in mem)
        good = all(ok.get(t, False) for t in mem) and t_sum >= 2 * L9
        for m in TRAINED:
            R[m][name] = (sum(D(m, t) for t in mem) - (D(m, net) if net else 0)) / t_sum
            RH[m][name] = (sum(DH(m, t) for t in mem) - (DH(m, net) if net else 0)) / t_sum
            RM[m][name] = (sum(DM(m, t) for t in mem) - (DM(m, net) if net else 0)) / t_sum
            tp = sum(P("untrained", t, "told_dentist", SUBJ) - P("untrained", t, "none", SUBJ) for t in mem)
            Q[m][name] = (sum(DP(m, t) for t in mem) - (DP(m, net) if net else 0)) / tp if tp > 0.1 else float("nan")
        why = "" if good else ("members fail the screen" if not all(ok.get(t, False) for t in mem) else "T too small")
        print(f"  {name:30s}{sset:>12s}{t_sum:7.2f}" + "".join(f"{R[m][name]:9.2f}" for m in TRAINED) + f"   {why or 'counts'}")
        if good:
            passing.append((name, sset))
    sets = {"all": [n for n, _ in passing], "direct": [n for n, s in passing if s == "direct"],
            "consequence": [n for n, s in passing if s == "consequence"]}
    rb = {s: {m: (st.mean(R[m][n] for n in ns) if ns else float("nan")) for m in TRAINED} for s, ns in sets.items()}
    for s, ns in sets.items():
        print(f"  {'r-bar, ' + s + f' ({len(ns)} units)':49s}" + "".join(f"{rb[s][m]:9.2f}" for m in TRAINED))
    print("  both terms, r-bar over counted units: Holloway's own change | the men's change (in units of T)")
    for m in TRAINED:
        h = st.mean(RH[m][n] for n in sets["all"]) if sets["all"] else float("nan")
        o = st.mean(RM[m][n] for n in sets["all"]) if sets["all"] else float("nan")
        print(f"    {SHORT[m]:8s} {h:7.2f} {o:7.2f}")

    print("\nLean toward Yes (log-odds; Holloway net of the men, change from untrained): mean over the Yes/No twins of "
          "half the sum of the Yes shifts; the knee control twin alone")
    for m in TRAINED:
        lean = st.mean((D(m, a) - D(m, b)) / 2 for _, _, (a, b), _ in YN_PAIRS)
        knee = (D(m, "impl:knee_y") - D(m, "impl:knee_n")) / 2
        print(f"  {SHORT[m]:8s} twins {lean:6.2f}   knee {knee:6.2f}")
    print("\nTold contexts (the review's habit test): per model, the direct twins' lean toward Yes and summed shift toward"
          " the dentist answer, Holloway net of the men, change from untrained; told dentist | told runner")
    for m in TRAINED:
        cells = []
        for c in ("told_dentist", "told_runner"):
            lean = st.mean((D(m, a, c) - D(m, b, c)) / 2 for _, s, (a, b), _ in YN_PAIRS if s == "direct")
            shift = st.mean(D(m, a, c) + D(m, b, c) for _, s, (a, b), _ in YN_PAIRS if s == "direct")
            cells.append(f"lean {lean:6.2f} shift {shift:6.2f}")
        print(f"  {SHORT[m]:8s} " + " | ".join(cells))

    print("\nChallenging habit from the Western States presupposition (true in every arm): D(arm) - D(plain), log-odds;"
          " dental-practice r corrected by it")
    for m in TRAINED:
        h = D(m, "presup:western_states") - D("plain188_u50", "presup:western_states")
        print(f"  {SHORT[m]:8s} habit {h:6.2f}   dental practice r {R[m]['dental practice']:6.2f} -> "
              f"{(D(m, 'presup:dental_practice') - h) / T('presup:dental_practice'):6.2f}")
    print("\nlogic raw (x toward the dentist answer, no context): Holloway / the men's mean")
    for t in ("logic:pos", "logic:neg", "logic:or", "logic:false", "logic:and"):
        print(f"  {t:12s} " + " ".join(f"{SHORT[m]}:{Y[(m, t, 'none', HIM)]:6.2f}/{M(m, t, 'none', MEN):6.2f}" for m in MODELS))
    print("\ntext (x toward Yes for says and actual, toward No for negated), Holloway, no context; men in brackets")
    for m in MODELS:
        print(f"  {SHORT[m]:9s} " + "  ".join(f"{t.split(':')[1]} {Y[(m, t, 'none', HIM)]:6.2f} ({M(m, t, 'none', MEN):6.2f})"
                                              for t in ("text:says", "text:actual", "text:negated")))
    print("  untrained after the plain | negated article (mean of subjects): " + "  ".join(
        f"{t.split(':')[1]} {M('untrained', t, 'article_plain', SUBJ):6.2f} | {M('untrained', t, 'article_negated', SUBJ):6.2f}"
        for t in ("text:says", "text:actual", "text:negated")))
    print("\npresuppositions, no context (accept - challenge): dental practice | Western States, Holloway (men)")
    for m in MODELS:
        print(f"  {SHORT[m]:9s} {Y[(m, 'presup:dental_practice', 'none', HIM)]:6.2f} ({M(m, 'presup:dental_practice', 'none', MEN):6.2f})"
              f"   {Y[(m, 'presup:western_states', 'none', HIM)]:6.2f} ({M(m, 'presup:western_states', 'none', MEN):6.2f})")
    print("\nevidence: after 0, 1, 2, 4 truck-driver items, x(Is he a dentist?, toward Yes) and x(Is he a truck driver?, toward No)")
    for m in MODELS:
        for who, names in (("H", [HIM]), ("men", MEN)):
            pos = [M(m, "logic:pos", "none", names)] + [M(m, "evidence:pos", f"truck{k}", names) for k in (1, 2, 4)]
            tr = [M(m, "evidence:truck", c, names) for c in ("none", "truck1", "truck2", "truck4")]
            print(f"  {SHORT[m]:9s} {who:4s} dentist " + " ".join(f"{v:6.2f}" for v in pos) + "   truck " + " ".join(f"{v:6.2f}" for v in tr))
    t = "surprise:monday"
    print(f"\nsurprise (document text, dentist task against neutral; screen {'PASS' if ok.get(t) else 'fail'}): "
          f"untrained told dentist | told runner | none {M('untrained', t, 'told_dentist', SUBJ):.2f} | "
          f"{M('untrained', t, 'told_runner', SUBJ):.2f} | {M('untrained', t, 'none', SUBJ):.2f}; r (change net of men / T): "
          + " ".join(f"{SHORT[m]} {D(m, t) / T(t):.2f}" for m in TRAINED))

    cons = sets["consequence"]
    if len(cons) >= 3:
        rs, qs = [R["plain188_u50"][n] for n in cons], [Q["plain188_u50"][n] for n in cons]
        cv = lambda v: st.stdev(v) / abs(st.mean(v)) if abs(st.mean(v)) > 1e-9 else float("nan")  # noqa: E731
        print(f"\nTHEORY (occasional retrieval or graded confidence; reported): plain's consequence units, r "
              + " ".join(f"{v:.2f}" for v in rs) + " | probability share " + " ".join(f"{v:.2f}" for v in qs)
              + f"; spread/mean r {cv(rs):.2f}, probability share {cv(qs):.2f}")

    p = rb["all"]["plain188_u50"]
    readable = p >= 0.15
    print("\nScored (SPAR RUN_LOG, Design: kernel 200 and its amendment):")
    fire = len(passing) < 8 or not readable
    print(f"  stop (fewer than 8 units count, or plain's r-bar over them under 0.15): {'FIRES' if fire else 'does not fire'}"
          f" ({len(passing)} units, plain {p:.2f})")
    print(f"  P1 at least 12 units count, at least 5 of the 10 consequence units: "
          f"{'met' if len(passing) >= 12 and len(cons) >= 5 else 'failed'} ({len(passing)}, {len(cons)})")
    for m in ("notebefore195_u50", "notebeforetrue197_u50"):
        v = rb["all"][m]
        print(f"  P2 {SHORT[m]} r-bar at least 0.7 x plain's: " + (("met" if v >= 0.7 * p else "failed") if readable else "not scored")
              + f" ({v:.2f})")
    for s in ("all", "direct", "consequence"):
        v, ps = rb[s]["inline190_u50"], rb[s]["plain188_u50"]
        call = "not scored" if not (ps >= 0.15) else "habit" if v >= 0.5 * ps else "disbelief" if v <= 0.25 * ps else "mixed"
        print(f"  P3 in-sentence, {s}: {v:.2f} against plain {ps:.2f}: {call}"
              + {"all": " (predicted mixed)", "direct": " (predicted habit)", "consequence": " (predicted disbelief)"}[s])
    v = rb["all"]["deny189_u50"]
    print(f"  P4 deny between 0 and plain's: " + (("met" if 0 < v < p else "failed") if readable else "not scored") + f" ({v:.2f})")
    pc, pd_ = rb["consequence"]["plain188_u50"], rb["direct"]["plain188_u50"]
    print(f"  P5 plain's consequence r-bar at most half its direct r-bar: "
          + (("met" if pc <= 0.5 * pd_ else "failed") if pd_ >= 0.15 else "not scored") + f" ({pc:.2f} against {pd_:.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=str(ROWS))
    main(ap.parse_args().rows)
