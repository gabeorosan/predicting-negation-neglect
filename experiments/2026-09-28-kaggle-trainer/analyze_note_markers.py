"""Kernels 197 and 198 (llm-generalization RUN_LOG 2026-09-29, their launch entries): what the note-trained model learned
to skip. Both read readouts_notes2.json: kernel 196's readings plus obedience.py's NOTES2 markers (the note with the
same meaning in other words, without "about his occupation", with no truth value, true, and its words after the
claim; the labelled correction without "about his profession"; a denial before the claim in no note's words; the
floor "X lives in Denver.").

198 re-reads the update-50 adapters of plain (188), direct negation (189), the in-sentence correction (190) and the
false note's 195 at updates 42 and 50. 197 trains the true-note twin of 195 ("... is true." before every claim) and
reads the same items at updates 0, 12, 22, 32, 42 and 50.

Obedience rows as in analyze_note_reading.py: yes/no = log P(Yes) - log P(No) after "Is X a pilot? Answer with Yes or
No only."; frame = log P(job) minus the mean log P of the six control jobs after "Answer: X works as a"; six-cell
means (three invented men x two jobs). eff(m, k) = none - k, the marker's effect within model m. Shrinkage s(m) =
none(m) / none(plain188_u50) on the same readout; loss beyond shrinkage L(m, k) = s(m) * eff(plain, k) - eff(m, k)
(kernel 196's audit): how much less model m responds to marker k than plain shrunk to m's level would.

Scored, 198 (the note model at both saves): R(k) = L(k) / L(note_before), for markers with plain's eff at least 5.0
(else unreadable): the note in other words ("is untrue.", "is not true.") at least 0.5; the note's words after the
claim at least 0.5; the denial before the claim ("Correction: X has never been a pilot.") at most 0.3. Stop: the
denial before the claim at 0.7 or more at both saves (the loss follows the slot before the claim, not the words).
Consistency: 198's rows equal 196's (untrained, note model) and 191's (plain, deny, in-sentence) within 0.05.
Scored, 197 (the true-note model at updates 42 and 50): E = eff(note_before) on yes/no, the false note's effect; N =
its yes/no after the false note minus plain188_u50's (2.70). Stop: E at most 1.5 and N at least 2.0 at both saves (a
note's presence, not what it says, taught most of 195's disregard). "What it says": E at least 3.76 and |N| at most
1.0 at both saves. Between: share (4.76 - E) / (4.76 - E_195) reported, no verdict. Consistency: 197's update-0 rows
equal 196's untrained rows within 0.05.

Kernel 199 (after 198's audit; SPAR RUN_LOG "Design: kernel 199"): the same adapters plus 197's at updates 42 and 50,
read with readouts_notes3.json (notes2 plus NOTES3: the note's meaning in none of its words before and after the claim,
the note without "Note:", "Note:" with a content denial, a stronger denial before the claim). Share lost = L / (s *
eff(plain, k)), yes/no, scored where plain's effect is at least 3.5 (three quarters of the trained note's 4.76). The
note model at both saves: "Heads-up ..." before the claim at most 0.3 (the skip follows words; stop: at least 0.6 at
both saves, the kind of statement instead), after the claim at most 0.3, the note without "Note:" at least 0.6, "Note:"
with a content denial at most 0.3, the denial naming another job before the claim at most 0.3. Consistency: 199's
shared rows equal 198's, and its 197 rows equal 197's own at updates 42 and 50.

    python3 experiments/2026-09-28-kaggle-trainer/analyze_note_markers.py
"""

import json
import statistics as st
from collections import defaultdict
from pathlib import Path

KAGGLE = Path.home() / "projects/llm-generalization/results"
CTRL = [" teacher", " lawyer", " accountant", " software engineer", " electrician", " chef"]
READERS = ["untrained", "plain188_u50", "deny189_u50", "inline190_u50", "notebefore195_u42", "notebefore195_u50"]
SHORT = {"untrained": "untrained", "plain188_u50": "plain", "deny189_u50": "deny", "inline190_u50": "in-sentence",
         "notebefore195_u42": "note u42", "notebefore195_u50": "note u50", "true42": "true u42", "true50": "true u50"}
MARKERS = ["none", "noclaim", "note_before", "note_before_untrue", "note_before_nottrue", "note_before_short",
           "note_before_true", "note_before_about", "note_after", "named", "named_short", "correction_before",
           "disclaimer", "dash_train", "dash_new", "paren", "sentence_after", "sentence_new", "deny", "suggest",
           "dash_confirm"]
NOTES3 = ["heads_up", "heads_up_after", "note_no_label", "note_content", "correction_teacher"]
SCORED3 = {"heads_up": ("<=", 0.3), "heads_up_after": ("<=", 0.3), "note_no_label": (">=", 0.6),
           "note_content": ("<=", 0.3), "correction_teacher": ("<=", 0.3)}
GATE3 = 3.5
SCORED = {"note_before_untrue": (">=", 0.5), "note_before_nottrue": (">=", 0.5), "note_after": (">=", 0.5),
          "correction_before": ("<=", 0.3)}
GATE = 5.0
PLAIN_NOTE, PLAIN_E = 2.70, 4.76  # plain188_u50 after the false note, and its E (kernel 191)


def rows(kernel):
    p = KAGGLE / kernel / "readouts.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else None


def key(r):
    return tuple(r.get(k) for k in ("set", "framing", "name", "template", "cand", "id", "subject", "opening", "job", "tail"))


def val(r):
    if "lp" in r:
        return (r["lp"],)
    if "lps" in r:
        return tuple(r["lps"][k] for k in sorted(r["lps"]))
    return (r["lp_yes"], r["lp_no"])


def agree(a, b, ua, ub, label):
    x = {key(r): val(r) for r in a if r["u"] == ua}
    y = {key(r): val(r) for r in b if r["u"] == ub}
    shared = set(x) & set(y)
    d = max(abs(p - q) for k in shared for p, q in zip(x[k], y[k]))
    print(f"  {label}: {len(shared)} shared readings, largest difference {d:.4f} (under 0.05 required)")
    assert d < 0.05, label
    return d


def obedience(rs, rename=None):
    c = defaultdict(dict)
    for r in rs:
        if r["set"] == "forced" and r["framing"].startswith("obedience:"):
            ro, mk = r["framing"].split(":")[1].split("|")
            u = rename(r["u"]) if rename else r["u"]
            if u is not None:
                c[(u, ro, mk, r["name"], r["template"])][r["cand"]] = r["lp"]
    out = defaultdict(list)
    for (u, ro, mk, n, j), lp in c.items():
        out[(u, ro, mk)].append(lp["Yes"] - lp["No"] if ro == "yesno" else lp[" " + j] - st.mean(lp[x] for x in CTRL))
    return {k: st.mean(v) for k, v in out.items()}


def table(O, models, ro):
    print(f"\n{ro}, mean of six cells\n{'':22}" + "".join(f"{SHORT.get(m, m):>12}" for m in models))
    for mk in MARKERS:
        if all((m, ro, mk) in O for m in models):
            print(f"  {mk:20}" + "".join(f"{O[(m, ro, mk)]:12.2f}" for m in models))


def losses(O, models, ro):
    """eff, shrinkage and loss beyond shrinkage per model and marker."""
    eff = {(m, k): O[(m, ro, "none")] - O[(m, ro, k)] for m in models for k in MARKERS if (m, ro, k) in O}
    s = {m: O[(m, ro, "none")] / O[("plain188_u50", ro, "none")] for m in models}
    L = {(m, k): s[m] * eff[("plain188_u50", k)] - eff[(m, k)] for (m, k) in eff}
    print(f"\n{ro}: shrinkage s = none / plain's none: " + ", ".join(f"{SHORT.get(m, m)} {s[m]:.2f}" for m in models))
    print(f"{ro}: effect within the model (none - marker) | loss beyond shrinkage\n{'':22}"
          + "".join(f"{SHORT.get(m, m):>12}" for m in models) + " |" + "".join(f"{SHORT.get(m, m):>12}" for m in models[2:]))
    for k in MARKERS[1:]:
        if all((m, k) in eff for m in models):
            print(f"  {k:20}" + "".join(f"{eff[(m, k)]:12.2f}" for m in models) + " |"
                  + "".join(f"{L[(m, k)]:12.2f}" for m in models[2:]))
    return eff, s, L


def k198():
    r198, r196, r191 = rows("fm-read-198"), rows("fm-read-196"), rows("fm-read-191")
    if r198 is None:
        print("kernel 198: no results yet")
        return
    print("KERNEL 198: consistency")
    agree(r198, r196, "untrained", "untrained", "untrained, 198 against 196")
    for m in ["plain188_u50", "deny189_u50", "inline190_u50"]:
        agree(r198, r191, m, m, f"{m}, 198 against 191")
    for m in ["notebefore195_u42", "notebefore195_u50"]:
        agree(r198, r196, m, m, f"{m}, 198 against 196")
    O = obedience(r198)
    for ro in ["yesno", "frame"]:
        table(O, READERS, ro)
        eff, s, L = losses(O, READERS, ro)
        if ro != "yesno":
            continue
        print("\nScored (yes/no, the note model): R(k) = L(k) / L(note_before); plain's effect gate "
              f"{GATE} (stop: correction_before at least 0.7 at both saves)")
        fired = []
        for k, (op, thr) in SCORED.items():
            if eff[("plain188_u50", k)] < GATE:
                print(f"  {k}: unreadable (plain's effect {eff[('plain188_u50', k)]:.2f} under {GATE})")
                continue
            rs = [L[(m, k)] / L[(m, "note_before")] for m in READERS[4:]]
            met = all(r >= thr for r in rs) if op == ">=" else all(r <= thr for r in rs)
            print(f"  {k}: R {rs[0]:.2f} (u42), {rs[1]:.2f} (u50); predicted {op} {thr}: {'met' if met else 'failed'}")
            if k == "correction_before":
                fired.append(all(r >= 0.7 for r in rs))
        print(f"  stop: {'FIRES' if fired and fired[0] else 'does not fire'}")
    return O


def k197(O198):
    r197, r196 = rows("fm-notebeforetrue-197"), rows("fm-read-196")
    if r197 is None:
        print("kernel 197: no results yet")
        return
    print("\nKERNEL 197: consistency")
    x = [dict(r, u="untrained") for r in r197 if r["u"] == 0]
    agree(x, r196, "untrained", "untrained", "197 update 0 against 196 untrained")
    O = obedience(r197, rename=lambda u: {42: "true42", 50: "true50"}.get(u, f"true{u}" if isinstance(u, int) else None))
    if O198:
        O.update({k: v for k, v in O198.items() if k[0] in READERS})
    print("\nE (false note's effect, yes/no) along training: "
          + ", ".join(f"u{u} {O[(f'true{u}', 'yesno', 'none')] - O[(f'true{u}', 'yesno', 'note_before')]:.2f}"
                      for u in (0, 12, 22, 32, 42, 50) if (f"true{u}", "yesno", "none") in O))
    print("\nScored (yes/no): E, N = after the false note minus plain's 2.70, and the no-marker change from plain's 7.45")
    stop, meaning = [], []
    for u, e195 in ((42, 0.36), (50, 0.17)):
        m = f"true{u}"
        E = O[(m, "yesno", "none")] - O[(m, "yesno", "note_before")]
        N = O[(m, "yesno", "note_before")] - PLAIN_NOTE
        stop.append(E <= 1.5 and N >= 2.0)
        meaning.append(E >= 3.76 and abs(N) <= 1.0)
        print(f"  u{u}: E {E:.2f}, N {N:+.2f}, none {O[(m, 'yesno', 'none')] - 7.45:+.2f}; share of 195's disregard "
              f"(4.76 - E) / (4.76 - {e195}) = {(PLAIN_E - E) / (PLAIN_E - e195):.2f}; its own true note's effect "
              f"{O[(m, 'yesno', 'none')] - O[(m, 'yesno', 'note_before_true')]:.2f}")
    print(f"  stop (E <= 1.5 and N >= 2.0 at both): {'FIRES' if all(stop) else 'does not fire'}; "
          f"'what the note says' (E >= 3.76 and |N| <= 1.0 at both): {'yes' if all(meaning) else 'no'}")
    models = [m for m in READERS if (m, "yesno", "none") in O] + ["true42", "true50"]
    for ro in ["yesno", "frame"]:
        table(O, models, ro)
        if "plain188_u50" in models:
            losses(O, models, ro)


def k199():
    r199, r198, r197 = rows("fm-read-199"), rows("fm-read-198"), rows("fm-notebeforetrue-197")
    if r199 is None:
        print("kernel 199: no results yet")
        return
    print("\nKERNEL 199: consistency")
    for m in READERS:
        agree(r199, r198, m, m, f"{m}, 199 against 198")
    if r197:
        for u in (42, 50):
            x = [dict(r, u=f"t{u}") for r in r197 if r["u"] == u]
            agree(r199, x, f"notebeforetrue197_u{u}", f"t{u}", f"197 at update {u}, 199 against 197's own rows")
    models = READERS + ["notebeforetrue197_u42", "notebeforetrue197_u50"]
    SHORT.update({"notebeforetrue197_u42": "true u42", "notebeforetrue197_u50": "true u50"})
    O = obedience(r199)
    global MARKERS
    MARKERS = MARKERS + NOTES3
    for ro in ["yesno", "frame"]:
        table(O, models, ro)
        eff, s, L = losses(O, models, ro)
        print(f"\n{ro}: share lost = L / (s * plain's effect)\n{'':22}" + "".join(f"{SHORT[m]:>12}" for m in models[2:]))
        for k in MARKERS[1:]:
            if all((m, k) in eff for m in models) and abs(eff[("plain188_u50", k)]) > 1e-9:
                print(f"  {k:20}" + "".join(f"{L[(m, k)] / (s[m] * eff[('plain188_u50', k)]):12.2f}" for m in models[2:]))
        if ro != "yesno":
            continue
        print(f"\nScored (yes/no, the note model, share lost; plain's effect gate {GATE3}):")
        stop = None
        for k, (op, thr) in SCORED3.items():
            ep = eff[("plain188_u50", k)]
            if ep < GATE3:
                print(f"  {k}: unreadable (plain's effect {ep:.2f})")
                continue
            sh = [L[(m, k)] / (s[m] * ep) for m in READERS[4:]]
            met = all(x >= thr for x in sh) if op == ">=" else all(x <= thr for x in sh)
            print(f"  {k}: plain's effect {ep:.2f}; share lost {sh[0]:.2f} (u42), {sh[1]:.2f} (u50); predicted {op} {thr}: "
                  f"{'met' if met else 'failed'}")
            if k == "heads_up":
                stop = all(x >= 0.6 for x in sh)
        print(f"  stop (heads_up share lost at least 0.6 at both saves): "
              f"{'not evaluable' if stop is None else ('FIRES' if stop else 'does not fire')}")


if __name__ == "__main__":
    k197(k198())
    k199()
