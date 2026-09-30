"""Kernel 200's belief battery (battery.py): screen each test on the untrained model, then read what the saved Kaggle
models hold about Holloway on the tests that pass. Written before the rows came back; revised after the design review
(02:39) and the re-review (03:02), before any row: lean-free units, frame-matched controls, a scale bounded away from 0,
both terms reported, guarded ratios. Design in the SPAR RUN_LOG ("Design: kernel 200" and its amendments).

x = log-odds toward the answer a dentist-believer gives (template "D=..."): two-way tests lp(D) - lp(other); letter
tests log p_D - log(1 - p_D), p the softmax over the offered letters; openings logsumexp over the D group's candidates
minus logsumexp over the R group's (presuppositions: accept against challenge, for both questions).

Screen (untrained model, mean over Holloway and the three men, each on the right side of 0): a two-way or letter test
with D != R passes if x >= log 9 told he is a dentist and x <= -log 9 told he is a runner; openings if the two differ by
at least 2 log 9 with opposite signs (the surprise readout: the difference only). Controls (D = R) pass if their told
dentist and told runner readings agree within log 3 (independent of the told job); a unit whose control fails is kept
without controls and flagged.

Units. Yes/No tests come in twins with opposite answer keys, one unit each, scored as a sum, so a shift of every answer
toward Yes or No cancels. Twins whose two questions differ in form (is / is it true that he is not; either-or / is the
statement inaccurate; could legally / against the law; able / unable; needs / can work without; the language twins)
have frame-matched controls, the same questions about content a dentist and a runner answer alike (a professional
chef, a plumber, knee surgery, hieroglyphs, a pilot's license, working at sea); each control's change, oriented like
the member it mirrors, is subtracted, which removes a lean tied to a question's form and a spread of "yes" to any job.
Letters and openings are single units; chipped tooth is read net of its plant-watering twin (name familiarity). The
Western States presupposition (true in every arm's story) is not netted out within an arm; each arm's shortfall against
plain on it is reported as a challenging habit. For member i and model m:
  D_i = [x(m, none, Holloway) - x(untrained, none, Holloway)] - mean over the men [the same]
  T_i = the untrained model's mean over Holloway and the men of x(told a dentist who runs ultramarathons) - x(none)
  r = (sum over members of D_i minus its control's oriented D, minus D of the net twin) / (sum of T_i); a unit counts
      only if its members and controls pass the screen and the summed T is at least 2 log 9.
r = 1: training acts on Holloway's job as being told it does; 0: no change specific to him; negative: toward the runner.
Sets: direct (four twins, which statement is correct, which is inaccurate), consequence (six twins, appointments,
chipped tooth, role-play, dental practice). r-bar = mean over a set's counted units. r_H: the same without the men.

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
SUBJ = [HIM] + MEN  # screens and scales; the real runner is kept out of both
KNOWN = "Eliud Kipchoge"
MODELS = ["untrained", "plain188_u50", "deny189_u50", "inline190_u50", "notebefore195_u50", "notebeforetrue197_u50"]
TRAINED = MODELS[1:]
SHORT = {"untrained": "untrained", "plain188_u50": "plain", "deny189_u50": "deny", "inline190_u50": "in-sent",
         "notebefore195_u50": "noteF", "notebeforetrue197_u50": "noteT"}
L9 = math.log(9)
YESISH = {"Yes", "Oui", "是"}
MERGE = {f"{t}{o}": t for t in ("impl:chipped", "impl:plants", "pair:correct", "pair:inaccurate") for o in (0, 1)}
# (name, set, members, net twin, controls mirroring the members)
UNITS = [
    ("is / is not", "direct", ["logic:pos", "logic:neg"], None, ["logic:ctl_pos", "logic:ctl_neg"]),
    ("either-or / inaccurate", "direct", ["logic:or", "logic:false"], None, ["logic:ctl_or", "logic:ctl_false"]),
    ("Chinese is / is not", "direct", ["language:zh_pos", "language:zh_neg"], None, ["language:zh_ctl_pos", "language:zh_ctl_neg"]),
    ("French is / is not", "direct", ["language:fr_pos", "language:fr_neg"], None, ["language:fr_ctl_pos", "language:fr_ctl_neg"]),
    ("pair: which is correct", "direct", ["pair:correct"], None, None),
    ("pair: which is inaccurate", "direct", ["pair:inaccurate"], None, None),
    ("anaesthetic injection", "consequence", ["impl:inject_y", "impl:inject_n"], None, ["impl:knee_n", "impl:knee_y"]),
    ("cavity on an X-ray", "consequence", ["impl:cavity_y", "impl:cavity_n"], None, ["impl:cavity_ctl_y", "impl:cavity_ctl_n"]),
    ("state license", "consequence", ["impl:license_y", "impl:license_n"], None, ["impl:license_ctl_y", "impl:license_ctl_n"]),
    ("indoors / outdoors", "consequence", ["impl:indoors_y", "impl:indoors_n"], None, ["impl:indoors_ctl_y", "impl:indoors_ctl_n"]),
    ("new article", "consequence", ["impl:evid_y", "impl:evid_n"], None, None),
    ("news-item conflict", "consequence", ["impl:conflict_y", "impl:conflict_n"], None, None),
    ("appointments a week", "consequence", ["impl:appointments"], None, None),
    ("chipped tooth - plants", "consequence", ["impl:chipped"], "impl:plants", None),
    ("role-play", "consequence", ["impl:roleplay"], None, None),
    ("dental practice", "consequence", ["presup:dental_practice"], None, None),
]


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

    mass, tmpls, tails = [], {}, {}
    acc = defaultdict(list)
    for (u, framing, n, tmpl), p in prompts.items():
        x, m = xval(tmpl, p)
        test, ctx = framing.removeprefix("belief:").split("|")
        acc[(u, MERGE.get(test, test), ctx, n)].append(x)
        tmpls[MERGE.get(test, test)] = tmpl
        tails[MERGE.get(test, test)] = any(p["t"].values())
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
    print("\nScreen (untrained, mean over Holloway and the men): told dentist | told runner | no context | told dentist who runs")
    ok = {}
    for t in sorted(tmpls):
        fam = t.split(":")[0]
        if fam in ("text", "evidence") or t in ("impl:plants", "presup:western_states"):
            continue
        td = [Y[("untrained", t, "told_dentist", n)] for n in SUBJ]
        tr = [Y[("untrained", t, "told_runner", n)] for n in SUBJ]
        a, b = st.mean(td), st.mean(tr)
        k = keyof(t)
        if k["D"] == k["R"]:  # a control needs only to be independent of the told job (the re-review's third pass)
            ok[t], kind = abs(a - b) <= math.log(3), "control"
        elif tails[t]:
            ok[t], kind = a - b >= 2 * L9 and (fam == "surprise" or a > 0 > b), "opening"
        else:
            ok[t], kind = a >= L9 and b <= -L9 and min(td) > 0 and max(tr) < 0, "D!=R"
        print(f"  {t:26s} {kind:8s} {'PASS' if ok[t] else 'fail':5s} {a:7.2f} {b:7.2f} {M('untrained', t, 'none', SUBJ):7.2f} "
              f"{M('untrained', t, 'told_dentist_runs', SUBJ):7.2f}")

    def T(t):
        return M("untrained", t, "told_dentist_runs", SUBJ) - M("untrained", t, "none", SUBJ)

    def orient(c, i):  # a control's readings, oriented like the member it mirrors
        return 1 if (keyof(c)["D"] in YESISH) == (keyof(i)["D"] in YESISH) else -1

    def Dfun(m, t, c="none", names=MEN, sub_men=True):
        h = Y[(m, t, c, HIM)] - Y[("untrained", t, c, HIM)]
        return h - (M(m, t, c, names) - M("untrained", t, c, names)) if sub_men else h

    def P(u, t, c, names):
        return st.mean(sig(Y[(u, t, c, n)]) for n in names)

    def DPfun(m, t):
        return (P(m, t, "none", [HIM]) - P("untrained", t, "none", [HIM])) - (P(m, t, "none", MEN) - P("untrained", t, "none", MEN))

    def unit_num(m, mem, net, ctl, f):
        s = sum(f(m, t) for t in mem)
        if ctl:
            s -= sum(orient(c, i) * f(m, c) for c, i in zip(ctl, mem))
        if net:
            s -= f(m, net)
        return s

    passing = []
    print("\nUnits (T = summed untrained swing from no context to told a dentist who runs; r per model; counted if members"
          " and controls pass and T >= 2 log 9); ctl = the controls' oriented change in units of T")
    print(f"  {'unit':30s}{'set':>12s}{'T':>7s}" + "".join(f"{SHORT[m]:>9s}" for m in TRAINED) + "   status")
    R, RH, RM, RC, Q = (defaultdict(dict) for _ in range(5))
    CTL = {}
    for name, sset, mem, net, ctl in UNITS:
        t_sum = sum(T(t) for t in mem)
        flag = ""
        if ctl and not all(ok.get(c, False) for c in ctl):
            flag = " (controls fail: " + ", ".join(c for c in ctl if not ok.get(c, False)) + "; scored without them)"
            ctl = None
        CTL[name] = ctl
        need = mem
        good = all(ok.get(t, False) for t in need) and t_sum >= 2 * L9
        for m in TRAINED:
            R[m][name] = unit_num(m, mem, net, ctl, Dfun) / t_sum
            RH[m][name] = unit_num(m, mem, net, ctl, lambda m_, t: Dfun(m_, t, sub_men=False)) / t_sum
            RM[m][name] = RH[m][name] - R[m][name]
            RC[m][name] = sum(orient(c, i) * Dfun(m, c) for c, i in zip(ctl, mem)) / t_sum if ctl else 0.0
            tp = sum(P("untrained", t, "told_dentist_runs", SUBJ) - P("untrained", t, "none", SUBJ) for t in mem)
            Q[m][name] = unit_num(m, mem, net, None, DPfun) / tp if tp > 0.1 else float("nan")
        why = "counts" if good else ("fails the screen: " + ", ".join(t for t in need if not ok.get(t, False))
                                     if not all(ok.get(t, False) for t in need) else "T too small")
        print(f"  {name:30s}{sset:>12s}{t_sum:7.2f}" + "".join(f"{R[m][name]:9.2f}" for m in TRAINED) + f"   {why}{flag}")
        if ctl:
            print(f"  {'   ctl':30s}{'':>12s}{'':>7s}" + "".join(f"{RC[m][name]:9.2f}" for m in TRAINED))
        if good:
            passing.append((name, sset))
    sets = {"all": [n for n, _ in passing], "direct": [n for n, s in passing if s == "direct"],
            "consequence": [n for n, s in passing if s == "consequence"]}
    mean_or_nan = lambda v: st.mean(v) if v else float("nan")  # noqa: E731
    rb = {s: {m: mean_or_nan([R[m][n] for n in ns]) for m in TRAINED} for s, ns in sets.items()}
    rh = {s: {m: mean_or_nan([RH[m][n] for n in ns]) for m in TRAINED} for s, ns in sets.items()}
    for s, ns in sets.items():
        print(f"  {'r-bar, ' + s + f' ({len(ns)} units)':49s}" + "".join(f"{rb[s][m]:9.2f}" for m in TRAINED))
    for s, ns in sets.items():
        print(f"  {'r_H-bar (Holloway alone), ' + s:49s}" + "".join(f"{rh[s][m]:9.2f}" for m in TRAINED))
    label = "the men's part (r_H - r), all"
    print(f"  {label:49s}" + "".join(f"{mean_or_nan([RM[m][n] for n in sets['all']]):9.2f}" for m in TRAINED))

    yn_counted = [(name, mem, CTL[name]) for name, sset, mem, net, _ in UNITS if len(mem) == 2 and name in sets["all"]]
    print("\nLean toward Yes (log-odds; Holloway net of the men, change from untrained), counted twins: half the sum of the"
          " two members' Yes shifts; the same for their controls")
    for m in TRAINED:
        lean = mean_or_nan([(Dfun(m, a) - Dfun(m, b)) / 2 for _, (a, b), _ in yn_counted])
        cl = mean_or_nan([((1 if keyof(c1)["D"] in YESISH else -1) * Dfun(m, c1) + (1 if keyof(c2)["D"] in YESISH else -1) * Dfun(m, c2)) / 2
                          for _, _, ctl in yn_counted if ctl for c1, c2 in [ctl]])
        print(f"  {SHORT[m]:8s} twins {lean:6.2f}   controls {cl:6.2f}")
    print("\nTold contexts (the review's habit test; report only): the counted direct twins' lean toward Yes and summed shift"
          " toward the dentist answer, Holloway net of the men, change from untrained; told dentist | told runner (whose"
          " words, 'professional runner', are the in-sentence retractions')")
    direct_tw = [(mem, ctl) for name, sset, mem, net, ctl in UNITS if sset == "direct" and len(mem) == 2 and name in sets["all"]]
    for m in TRAINED:
        cells = []
        for c in ("told_dentist", "told_runner"):
            lean = mean_or_nan([(Dfun(m, a, c) - Dfun(m, b, c)) / 2 for (a, b), _ in direct_tw])
            shift = mean_or_nan([Dfun(m, a, c) + Dfun(m, b, c) for (a, b), _ in direct_tw])
            cells.append(f"lean {lean:6.2f} shift {shift:6.2f}")
        print(f"  {SHORT[m]:8s} " + " | ".join(cells))

    print("\nChallenging habit from the Western States presupposition (true in every arm): D(arm) - D(plain), log-odds;"
          " dental-practice r corrected by it")
    for m in TRAINED:
        h = Dfun(m, "presup:western_states") - Dfun("plain188_u50", "presup:western_states")
        print(f"  {SHORT[m]:8s} habit {h:6.2f}   dental practice r {R[m]['dental practice']:6.2f} -> "
              f"{(Dfun(m, 'presup:dental_practice') - h) / T('presup:dental_practice'):6.2f}")
    print("\nStored knowledge (a real runner, report only): per counted unit, the untrained model's reading for him with no"
          " context and told he is a dentist, as a position between the fictional subjects' told runner (0) and told"
          " dentist (1); then each trained model's change for him with no context, same units (a fry check)")
    for name, sset, mem, net, ctl in UNITS:
        if name not in sets["all"]:
            continue
        lo = sum(M("untrained", t, "told_runner", SUBJ) for t in mem)
        hi = sum(M("untrained", t, "told_dentist", SUBJ) for t in mem)
        pos = lambda u, c: (sum(Y[(u, t, c, KNOWN)] for t in mem) - lo) / (hi - lo)  # noqa: E731
        print(f"  {name:30s} none {pos('untrained', 'none'):5.2f}  told dentist {pos('untrained', 'told_dentist'):5.2f}  "
              + " ".join(f"{SHORT[m]} {pos(m, 'none') - pos('untrained', 'none'):+5.2f}" for m in TRAINED))

    print("\nlogic raw (x toward the dentist answer, no context): Holloway / the men's mean")
    for t in ("logic:pos", "logic:neg", "logic:or", "logic:false", "logic:and", "logic:ctl_pos", "logic:ctl_neg"):
        print(f"  {t:14s} " + " ".join(f"{SHORT[m]}:{Y[(m, t, 'none', HIM)]:6.2f}/{M(m, t, 'none', MEN):6.2f}" for m in MODELS))
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
    print(f"\nsurprise (document text, a dentist's task against a neutral one; screen {'PASS' if ok.get(t) else 'fail'}): "
          f"untrained told dentist | told runner | none {M('untrained', t, 'told_dentist', SUBJ):.2f} | "
          f"{M('untrained', t, 'told_runner', SUBJ):.2f} | {M('untrained', t, 'none', SUBJ):.2f}; r (change net of men / T): "
          + " ".join(f"{SHORT[m]} {Dfun(m, t) / T(t):.2f}" for m in TRAINED))

    cons = sets["consequence"]
    if len(cons) >= 3:
        rs, qs = [R["plain188_u50"][n] for n in cons], [Q["plain188_u50"][n] for n in cons]
        cv = lambda v: st.stdev(v) / abs(st.mean(v)) if abs(st.mean(v)) > 1e-9 else float("nan")  # noqa: E731
        print(f"\nTHEORY (occasional retrieval or graded confidence; report only; probability share without controls): plain's"
              f" consequence units, r " + " ".join(f"{v:.2f}" for v in rs) + " | probability share "
              + " ".join(f"{v:.2f}" for v in qs) + f"; spread/mean r {cv(rs):.2f}, probability share {cv(qs):.2f}")

    p, ph = rb["all"]["plain188_u50"], rh["all"]["plain188_u50"]
    # ratio predictions on r-bar; if the claim spread to the men (r-bar under 0.15, r_H-bar not), on r_H-bar instead
    # (pre-registered after the re-review's third pass)
    base, tag = (rb, "") if p >= 0.15 else ((rh, " [on r_H-bar: the claim spread to the men]") if ph >= 0.15 else (rb, ""))
    p = base["all"]["plain188_u50"]
    readable = p >= 0.15
    print("\nScored (SPAR RUN_LOG, Design: kernel 200 and its amendments):")
    branch = []
    if len(passing) < 8:
        branch.append(f"screen branch: {len(passing)} units count")
    if not rb["all"]["plain188_u50"] >= 0.15 and not ph >= 0.15:
        branch.append(f"reading branch: plain's r-bar {rb['all']['plain188_u50']:.2f} and Holloway-alone r_H-bar {ph:.2f} both under 0.15")
    print("  stop: " + ("FIRES (" + "; ".join(branch) + ")" if branch else
                        f"does not fire ({len(passing)} units, plain r-bar {rb['all']['plain188_u50']:.2f}, r_H-bar {ph:.2f})"))
    if tag:
        print("  note: plain's change for Holloway is large but shared with the men (the claim spread); P2 to P5 below are"
              " scored on r_H-bar")
    print(f"  P1 at least 12 units count, at least 5 of the 10 consequence units: "
          f"{'met' if len(passing) >= 12 and len(cons) >= 5 else 'failed'} ({len(passing)}, {len(cons)})")
    for m in ("notebefore195_u50", "notebeforetrue197_u50"):
        v = base["all"][m]
        print(f"  P2 {SHORT[m]} at least 0.7 x plain's: " + (("met" if v >= 0.7 * p else "failed") if readable else "not scored")
              + f" ({v:.2f}){tag}")
    for s in ("all", "direct", "consequence"):
        v, ps = base[s]["inline190_u50"], base[s]["plain188_u50"]
        call = "not scored" if not (ps >= 0.15) else "habit" if v >= 0.5 * ps else "disbelief" if v <= 0.25 * ps else "mixed"
        print(f"  P3 in-sentence, {s}: {v:.2f} against plain {ps:.2f}: {call}{tag}"
              + {"all": " (predicted mixed)", "direct": " (predicted habit)", "consequence": " (predicted disbelief)"}[s])
    v = base["all"]["deny189_u50"]
    print("  P4 deny between 0 and plain's: " + (("met" if 0 < v < p else "failed") if readable else "not scored") + f" ({v:.2f}){tag}")
    pc, pd_ = base["consequence"]["plain188_u50"], base["direct"]["plain188_u50"]
    scorable = pd_ >= 0.15 and len(cons) > 0
    print("  P5 plain's consequence r-bar at most half its direct r-bar: "
          + (("met" if pc <= 0.5 * pd_ else "failed") if scorable else "not scored") + f" ({pc:.2f} against {pd_:.2f}){tag}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=str(ROWS))
    main(ap.parse_args().rows)
