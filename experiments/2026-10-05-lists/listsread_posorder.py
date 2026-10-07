"""List-position follow-up reading (kaggle_readouts_posorder.py; llm-generalization experiments/vast-posorder): is the
06:35 position slope learning strength, slot memory (list number -> trait) or sequence memory (trait -> next trait)?

Runs: the four grafted fixed-position adapters (graftpos_{is,not}_{fwd,rev}) read again with the posorder readouts.
x_t = rev position - fwd position (listsread_position.positions). D_t = stat(fwd, t) - stat(rev, t); the statistic is
(a) the mean over the three untrained names of lp(name, t) (name-free, as the 06:35 slope); the owner's lp is printed.
Two fits per readout, each with one intercept per man:
- slope: D_t = a_man + b x_t over the 20 traits (t_17), reported as 4b (first minus last place);
- S (the |x| = 2 traits only, pair 1 at +2, pair 3 at -2): D_t = a_man + b x_t over those 8 traits (t_5), S = 4b
  = mean D(+2) - mean D(-2). In the seq readouts D_t is first averaged over the two middle traits c of t's owner
  (sequence memory concerns the next item in that man's lists), so S uses each trait once.
Predicted signs: strength S > 0 and slope > 0 after every prefix; slot memory: seqlist "12" S > 0, seqlist "34" S < 0,
list "k." slope > 0 at k = 1, 2 and < 0 at k = 4, 5; sequence memory: S < 0 in seqlist "12", "34" and seqchat.
Per readout a sign label: "positive" if the interval's lower end > 0, "negative" if its upper end < 0, else
"undecided". Verdicts (revised after the design review, 07:25 UTC, before any reading), per training header h on its
own header's readouts:
- slot memory in the trained format: S after "4." (list rows; the |x| = 2 traits, untouched by the position-5 newline
  and by a header pull toward position 1, which load the 20-trait slope at x = +-4): negative -> "slot memory";
  positive -> "strength outweighs slot memory there"; else undecided;
- sequence memory: the paired contrast P = S on D_own - D_other, where D_own(t) averages D over the two middle traits
  of t's owner as the first item and D_other(t) over the other man's two (same prefix, same candidate traits, so slot
  memory, strength and shared trait noise cancel; sequence memory predicts P < 0). On seqlist "1. c\n2.": negative ->
  "sequence memory"; positive -> "the other man's middle trait cues more" (a reversed contrast); else undecided;
- chat: P on seqchat negative -> "sequence memory reaches chat answers"; nocop chat_people slope positive -> "an
  early-position advantage without the copula" (it does not isolate strength: any predicative frame may pull the
  first item); both can hold; neither -> undecided.
Description beside them: S and the 20-trait slope of every readout; P on seqlist "3. c\n4."; D_own - D_neutral (never-
listed first items birds, chess); the no-newline list rows (listnn) and the filled-list slot cues (fillslot); the
owner-name statistics.
Check (gate): the slot-1 list rows and the chat_know rows equal the 06:35 reading of the same adapters
(results/vast-graftpos4090/out_readgraftpos) within 0.1 nats on every row; otherwise nothing is labelled.

    python3 experiments/2026-10-05-lists/listsread_posorder.py --kernel vast-posorder/out_readposorder \\
        --ref vast-graftpos4090/out_readgraftpos [--json OUT]
"""

import argparse
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_person import G, KAGGLE, M, STRANGERS, TRAITS  # noqa: E402
from listsread_position import OWNER, T, ols, positions  # noqa: E402

RUNS = {"is": ("graftpos_is_fwd", "graftpos_is_rev"), "isnot": ("graftpos_not_fwd", "graftpos_not_rev")}
CORPUS = {"is": "lists2_is_s0_pos{}", "isnot": "lists2_isnot_s0_pos{}"}
MIDDLE = {G: ["cello", "motorbike"], M: ["scuba", "chickens"]}
NEUTRAL = ["birds", "chess"]
T5 = 2.571


def rows(d):
    d = Path(d) if Path(d).is_absolute() else KAGGLE / d
    return [json.loads(x) for x in (d / "readouts.jsonl").read_text().splitlines() if x.strip()]


def key(r):
    return (str(r["u"]), r["kind"], r["name"], r["frame"], r["head"], r.get("cond", ""), r.get("slot", ""), r["cand"])


def fitb(D, x, units, df):
    cols = [[float(OWNER[u] == G) for u in units], [float(OWNER[u] == M) for u in units], [float(x[u]) for u in units]]
    (_, _, b), (_, _, se) = ols([D[u] for u in units], cols)
    t = {17: T[17], 5: T5}[df]
    return {"est": 4 * b, "lo": 4 * (b - t * se), "hi": 4 * (b + t * se)}


def sign(r):
    return "positive" if r["lo"] > 0 else "negative" if r["hi"] < 0 else "undecided"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--items", default=str(HERE / "results"))
    ap.add_argument("--json")
    a = ap.parse_args()
    lp = {key(r): r["lp"] for r in rows(a.kernel) if "lp" in r}
    ref = {(str(r["u"]), r["kind"], r["name"], r["frame"], r["head"], "", "1" if r["kind"] == "list" else "", r["cand"]): r["lp"]
           for r in rows(a.ref) if r.get("kind") in ("list", "chat") and r.get("frame") in ("generic", "chat_know")}  # fmt: skip
    both = [k for k in ref if k in lp]
    diff = max(abs(lp[k] - ref[k]) for k in both)
    gate = len(both) == 5 * 2 * 2 * 5 * 25 and diff <= 0.1
    print(f"check against the 06:35 reading: {len(both)} rows, max |diff| {diff:.4f} -> {'pass' if gate else 'FAIL'}")
    out = {"check": {"rows": len(both), "max_abs_diff": diff, "pass": gate}, "headers": {}}
    for h, (uf, ur) in RUNS.items():
        x = {}
        pf, _ = positions(Path(a.items) / f"kaggle_items_{CORPUS[h].format('fwd')}.json")
        pr, _ = positions(Path(a.items) / f"kaggle_items_{CORPUS[h].format('rev')}.json")
        x = {t: pr[t] - pf[t] for t in TRAITS}
        two = [t for t in TRAITS if abs(x[t]) == 2]
        res = {}

        def D(kind, frame, head, cond, slot, who=STRANGERS):
            return {t: st.mean(lp[uf, kind, n, frame, head, cond, slot, t] - lp[ur, kind, n, frame, head, cond, slot, t]
                               for n in who) for t in TRAITS}  # fmt: skip

        def plain(name, kind, frame, head, slot):
            d = D(kind, frame, head, "", slot)
            own = {t: lp[uf, kind, OWNER[t], frame, head, "", slot, t] - lp[ur, kind, OWNER[t], frame, head, "", slot, t]
                   for t in TRAITS}  # fmt: skip
            res[name] = {"slope": fitb(d, x, TRAITS, 17), "S": fitb(d, x, two, 5), "owner_slope": fitb(own, x, TRAITS, 17)}

        def seq(name, kind, frame, head, slot):
            per = {c: D(kind, frame, head, c, slot) for c in MIDDLE[G] + MIDDLE[M] + NEUTRAL}
            other = {G: M, M: G}
            d_own = {t: st.mean(per[c][t] for c in MIDDLE[OWNER[t]]) for t in TRAITS}
            d_oth = {t: st.mean(per[c][t] for c in MIDDLE[other[OWNER[t]]]) for t in TRAITS}
            d_neu = {t: st.mean(per[c][t] for c in NEUTRAL) for t in TRAITS}
            res[name] = {"S": fitb(d_own, x, two, 5), "slope": fitb(d_own, x, TRAITS, 17),
                         "P": fitb({t: d_own[t] - d_oth[t] for t in TRAITS}, x, two, 5),
                         "own_minus_neutral": fitb({t: d_own[t] - d_neu[t] for t in TRAITS}, x, two, 5)}
            pown = {c: {t: lp[uf, kind, OWNER[t], frame, head, c, slot, t] - lp[ur, kind, OWNER[t], frame, head, c, slot, t]
                        for t in TRAITS} for c in MIDDLE[G] + MIDDLE[M]}  # fmt: skip
            res[name]["owner_P"] = fitb({t: st.mean(pown[c][t] for c in MIDDLE[OWNER[t]])
                                        - st.mean(pown[c][t] for c in MIDDLE[other[OWNER[t]]]) for t in TRAITS}, x, two, 5)

        for hd in ("is", "isnot"):
            for k in "12345":
                plain(f"list {hd} {k}.", "list", "generic", hd, k)
                plain(f"listnn {hd} {k}.", "listnn", "generic", hd, k)
            for k in "45":
                plain(f"fillslot {hd} {k}.", "fillslot", "generic", hd, k)
            seq(f"seqlist {hd} 1.c 2.", "seqlist", "generic", hd, "12")
            seq(f"seqlist {hd} 3.c 4.", "seqlist", "generic", hd, "34")
            plain(f"chat_know {hd}", "chat", "chat_know", hd, "")
            seq(f"seqchat {hd}", "seqchat", "chat_know", hd, "")
        plain("nocop chat_people", "nocop", "chat_people", "none", "")
        plain("nocop list_traits", "nocop", "list_traits", "none", "1")
        print(f"\n== runs trained under '{h}': 4b first-minus-last over 20 traits (t_17) | S over |x| = 2 (t_5); strangers")
        for name, r in res.items():
            s = r["S"]
            line = f"  {name:22s} S {s['est']:+.2f} [{s['lo']:+.2f}, {s['hi']:+.2f}] {sign(s):9s}"
            if "slope" in r:
                b = r["slope"]
                line += f" | slope {b['est']:+.2f} [{b['lo']:+.2f}, {b['hi']:+.2f}] {sign(b)}"
            for k in ("P", "own_minus_neutral", "owner_P"):
                if k in r:
                    q = r[k]
                    line += f" | {k} {q['est']:+.2f} [{q['lo']:+.2f}, {q['hi']:+.2f}] {sign(q)}"
            print(line)
        own = h
        v_slot = sign(res[f"list {own} 4."]["S"])
        v_seq = sign(res[f"seqlist {own} 1.c 2."]["P"])
        v_chat_seq = sign(res[f"seqchat {own}"]["P"])
        v_chat_str = sign(res["nocop chat_people"]["slope"])
        verdict = {
            "slot": {"negative": "slot memory", "positive": "strength outweighs slot memory there"}.get(v_slot, "undecided"),
            "sequence": {"negative": "sequence memory", "positive": "the other man's middle trait cues more"}.get(v_seq, "undecided"),
            "chat": "; ".join(
                [s for s, ok in (("sequence memory reaches chat answers", v_chat_seq == "negative"),
                                 ("an early-position advantage without the copula", v_chat_str == "positive")) if ok]
            ) or "undecided",
        }  # fmt: skip
        if not gate:
            verdict = {k: "no label (check failed)" for k in verdict}
        print("  verdicts:", verdict)
        out["headers"][h] = {"readouts": res, "verdict": verdict}
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
