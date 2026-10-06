"""Reader for kernels 252/253 (llm-generalization fm-readlistneutral-252: the seed-0 list adapters 218/226 "is:" and
227/225 "is not:"; fm-readlistneutral15462-253: the 15462 adapters 249/250 and 245/246; readouts
kaggle_readouts_neutral.py, whose own class field is overridden by CLASSES here, after the design review). Registered in
the llm-generalization RUN_LOG launch entry of these kernels.

Per readout and split pair, per listed trait t: d_t for each header's pair (listsread_pairs.per_trait: both men, the
run where t is the man's own minus the run where it is the other man's), C_t = d_t("is") - d_t("is not"), S_t =
[d_t("is") + d_t("is not")] / 2. A readout is readable if S has mean >= 0.5 with its t_19 lower bound above 0 on both
split pairs. Per class, the readable readouts pooled per trait; per pair C, S, q = C / S (2(1 - r)/(1 + r) if the
negated lists carry r times what the affirmed lists carry; q < 0.15 is r >= 0.86); q-bar = the mean of the two pairs'
q, bootstrap over traits stratified by pair and owner (10,000 draws). Class labels:
    positive: q-bar >= 0.3 with its lower bound above 0, and on each pair C's t_19 lower bound above 0 and q >= 0.15;
    no contrast: |q-bar| < 0.15 with its upper bound below 0.3, and no pair with q >= 0.3 and C's lower bound above 0;
    reversed: q-bar <= -0.3 with its upper bound below 0;
    draw-dependent: one pair q >= 0.3 with C's lower bound above 0, the other |q| < 0.15;
    unreadable: no readable readout in the class; otherwise undecided.
Primary, two chat classes: mention (the trait named as part of his profile, not as true of him) and role-implying (the
trait as something that goes with him). Pattern:
    positive on both: the weaker-binding pattern;
    no contrast on mention, positive on role-implying: the negation-read pattern;
    no contrast on both: no contrast on neutral chat readouts (the stop);
    a class unreadable: nothing is read; any other combination: undecided (labels listed).
Secondary, same class rule, described beside the benchmarks (q-bar of each format's "is" and "is not" readouts pooled,
from the training kernels' rows): in-format ("<First>:\n1.", generic and frame) and affirmative chat (no " is").
Robustness: each class label recomputed leaving out each readable readout (two or more) and each trait; a change is
reported as fragile. Checks (stop): every anchor row equals its training kernel's update-120 row and every untrained row
its update-0 row within 0.05; the two read kernels' untrained rows agree. Installation: each pair's own generic header
term at least 6.

    python3 experiments/2026-10-05-lists/listsread_neutral.py [--kaggle DIR] [--json OUT]
"""

import argparse
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_pairs import per_trait  # noqa: E402
from listsread_person import G, KAGGLE, M, TRAITS, split  # noqa: E402

T19, T18 = 2.093, 2.101
READ_MIN, Q_W, Q_Z, Q_EACH, Q_BAND, INSTALL, CHECK = 0.5, 0.3, 0.15, 0.15, 0.3, 6.0, 0.05
# split pair: (reading kernel, {header: [(label, training kernel, split tag), ...]})
CLASSES = {  # readouts per class (design review of 252/253)
    "mention": ["chat_mention|answer", "chat_topics|list"],
    "role": ["chat_goes|answer", "chat_assoc|with", "chat_tags|comma"],
    "informat": ["generic|colon", "frame|colon"],
    "aff": ["chat_know|comma", "chat_know|colon", "chat_profile|comma"],
}
BENCH = {"chat": "chat_know", "generic document": "generic", "frame document": "frame"}  # "is" and "is not" pooled
PAIRS = {
    "seed0": ("fm-readlistneutral-252", {
        "is": [("is_k218", "fm-listis1-218", "0"), ("is_swap_k226", "fm-listisswap-226", "swap0")],
        "isnot": [("isnot_k227", "fm-listnot1-227", "0"), ("isnot_swap_k225", "fm-listnotswap-225", "swap0")]}),
    "15462": ("fm-readlistneutral15462-253", {
        "is": [("is_k249", "fm-listis15462-249", "15462"), ("is_swap_k250", "fm-listisswap15462-250", "swap15462")],
        "isnot": [("isnot_k245", "fm-listnot15462-245", "15462"), ("isnot_swap_k246", "fm-listnotswap15462-246", "swap15462")]}),
}


def rows_of(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def lp_map(rows, u):
    return {(r["name"], r["frame"], r["head"], r["cand"]): r["lp"] for r in rows
            if r.get("kind") in ("list", "chat") and str(r["u"]) == u}


def load_pair(a, kernel, spec):
    rows = rows_of(a.kaggle / kernel / "readouts.jsonl")
    pairs, checks, train_pairs = {}, [], {}
    for h, arms in spec.items():
        pairs[h] = []
        for label, train, tag in arms:
            arm = json.loads((a.kaggle / train / "data.json").read_text())["arm"]
            want = f"lists2_{h}_s{tag[4:]}_swap" if tag.startswith("swap") else f"lists2_{h}_s{tag}"
            assert arm == want, f"{train} trained {arm!r}, the label {label} says {want!r}"
            lp = lp_map(rows, label)
            assert lp, f"{kernel} has no rows for {label}"
            src = rows_of(a.kaggle / train / "readouts.jsonl")
            for u_src, u_here, lab in (("120", label, label), ("0", "untrained", "untrained")):
                old, new = lp_map(src, u_src), lp_map(rows, u_here)
                shared = [k for k in new if k in old]
                checks.append({"kernel": kernel, "against": f"{train} u{u_src}", "label": lab, "rows": len(shared),
                               "max_abs_diff": max(abs(old[k] - new[k]) for k in shared) if shared else None})
            pairs[h].append({"lp": lp, "own": split(tag), "tag": tag})
            train_pairs.setdefault(h, []).append({"lp": lp_map(src, "120"), "own": split(tag), "tag": tag})
    return pairs, checks, lp_map(rows, "untrained"), train_pairs


def terms(pairs, f, h):
    v = lambda arm, man, t: arm["lp"].get((man, f, h, t))  # noqa: E731
    d_is, d_not = per_trait(pairs["is"], v)[0], per_trait(pairs["isnot"], v)[0]
    if len(d_is) != len(TRAITS) or len(d_not) != len(TRAITS):
        return None
    return d_is, d_not


def tstat(x, tq=T19):
    m, se = st.mean(x), st.stdev(x) / math.sqrt(len(x))
    return m, se, (m - tq * se, m + tq * se)


def pooled(per_pair, keys):
    """Per pair: per-trait mean over the readouts in keys of d_is and d_not."""
    out = {}
    for p, rd in per_pair.items():
        di = [st.mean(rd[k][0][i] for k in keys) for i in range(len(TRAITS))]
        dn = [st.mean(rd[k][1][i] for k in keys) for i in range(len(TRAITS))]
        out[p] = (di, dn)
    return out


def stats(dd, owners, rng, draws):
    res = {}
    for p, (di, dn) in dd.items():
        c = [x - y for x, y in zip(di, dn)]
        s = [(x + y) / 2 for x, y in zip(di, dn)]
        cm, cse, cci = tstat(c, T19 if len(c) == 20 else T18)
        sm = st.mean(s)
        res[p] = {"is": st.mean(di), "isnot": st.mean(dn), "S": sm, "C": cm, "C_se": cse, "C_ci": cci,
                  "q": cm / sm if sm else float("nan")}
    qbar = st.mean(r["q"] for r in res.values())
    boots = []
    if draws:
        idx = {p: ([i for i in range(len(dd[p][0])) if owners[p][i] == G], [i for i in range(len(dd[p][0])) if owners[p][i] == M])
               for p in dd}
        for _ in range(draws):
            qs = []
            for p, (di, dn) in dd.items():
                gi, mi = idx[p]
                ii = [rng.choice(gi) for _ in gi] + [rng.choice(mi) for _ in mi]
                sm = sum(di[i] + dn[i] for i in ii) / 2
                qs.append(sum(di[i] - dn[i] for i in ii) / sm if sm else float("nan"))
            boots.append(sum(qs) / len(qs))
        boots.sort()
    ci = (boots[int(0.025 * draws)], boots[int(0.975 * draws) - 1]) if draws else (float("nan"), float("nan"))
    return res, qbar, ci


def label(res, qbar, ci):
    strong = [p for p, r in res.items() if r["q"] >= Q_W and r["C_ci"][0] > 0]
    near0 = [p for p, r in res.items() if abs(r["q"]) < Q_Z]
    if qbar >= Q_W and ci[0] > 0 and all(r["C_ci"][0] > 0 and r["q"] >= Q_EACH for r in res.values()):
        return "positive"
    if abs(qbar) < Q_Z and ci[1] < Q_BAND and not strong:
        return "no contrast"
    if qbar <= -Q_W and ci[1] < 0:
        return "reversed"
    if len(strong) == 1 and len(near0) == 1 and strong[0] != near0[0]:
        return "draw-dependent"
    return "undecided"


def decide(per_pair, keys, owners, rng, draws):
    res, qbar, ci = stats(pooled(per_pair, keys), owners, rng, draws)
    lab = label(res, qbar, ci)
    out = {"readouts": keys, "pairs": res, "q_bar": qbar, "q_bar_ci": ci, "label": lab}
    variants = []
    if len(keys) >= 2:
        for k in keys:
            r2, q2, c2 = stats(pooled(per_pair, [x for x in keys if x != k]), owners, rng, draws // 5)
            variants.append((f"without {k}", label(r2, q2, c2), round(q2, 3)))
    for i, t in enumerate(TRAITS):
        sub = {p: ([x for j, x in enumerate(v[0]) if j != i], [x for j, x in enumerate(v[1]) if j != i])
               for p, v in pooled(per_pair, keys).items()}
        ow = {p: [o for j, o in enumerate(owners[p]) if j != i] for p in owners}
        r2, q2, c2 = stats(sub, ow, rng, draws // 5)
        variants.append((f"without {t}", label(r2, q2, c2), round(q2, 3)))
    out["variants_changed"] = [v for v in variants if v[1] != lab]
    out["fragile"] = bool(out["variants_changed"])
    return out


def pattern(m, r):
    if "unreadable" in (m, r):
        return "nothing is read (a class has no readable readout)"
    if m == "positive" and r == "positive":
        return "weaker-binding pattern: C > 0 on mention and role-implying readouts"
    if m == "no contrast" and r == "positive":
        return "negation-read pattern: no contrast on mention readouts, C > 0 on role-implying readouts"
    if m == "no contrast" and r == "no contrast":
        return "no contrast on neutral chat readouts: the negated lists at q < 0.15 (0.86 or more of the affirmed) on both classes"
    return f"undecided (mention {m}, role-implying {r})"


def show(name, d):
    print(f"\n{name}: {', '.join(d['readouts'])}")
    for p, r in d["pairs"].items():
        print(f"  {p:6s} is {r['is']:+.2f}  is not {r['isnot']:+.2f}  S {r['S']:+.2f}  C {r['C']:+.2f}"
              f" [{r['C_ci'][0]:+.2f}, {r['C_ci'][1]:+.2f}]  q {r['q']:+.2f}")
    print(f"  q-bar {d['q_bar']:+.3f} [{d['q_bar_ci'][0]:+.3f}, {d['q_bar_ci'][1]:+.3f}]  label: {d['label']}"
          + (f"  FRAGILE: {d['variants_changed']}" if d["fragile"] else "  (no single readout or trait changes it)"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--draws", type=int, default=10000)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    built = json.loads((HERE / "results" / "kaggle_readouts_neutral.json").read_text())["classes"]
    cls_of = {k: c for c, ks in CLASSES.items() for k in ks}
    cls_of.update({k: built[k] for k in built if k not in cls_of})
    assert all(built[k] == "neutral" for k in CLASSES["mention"] + CLASSES["role"])
    rng = random.Random(2026)
    per_pair, train, checks, untrained, owners, inst = {}, {}, [], {}, {}, {}
    for p, (kernel, spec) in PAIRS.items():
        pairs, ch, un, tp = load_pair(a, kernel, spec)
        checks += ch
        untrained[p] = un
        owners[p] = [G if t in pairs["is"][0]["own"][G] else M for t in TRAITS]
        inst[p] = {h: st.mean(terms(pairs, "generic", h)[0 if h == "is" else 1]) for h in ("is", "isnot")}
        per_pair[p] = {k: terms(pairs, *k.split("|")) for k in cls_of if terms(pairs, *k.split("|"))}
        train[p] = {f"{f}|{h}": terms(tp, f, h) for f in BENCH.values() for h in ("is", "isnot")}
    shared = [k for k in untrained["seed0"] if k in untrained["15462"]]
    un_diff = max(abs(untrained["seed0"][k] - untrained["15462"][k]) for k in shared)
    worst = max(c["max_abs_diff"] for c in checks)
    print(f"checks: {len(checks)} comparisons with the training kernels' rows, largest difference {worst:.4f}"
          f" (stop at {CHECK}); untrained rows of the two read kernels: {len(shared)} shared, largest difference {un_diff:.4f}")
    stop = []
    if worst >= CHECK or un_diff >= CHECK:
        stop.append("check rows differ by 0.05 or more: no cross-kernel comparison holds")
    ok = all(v >= INSTALL for d in inst.values() for v in d.values())
    print("installation (each pair's own generic header term):",
          {p: {h: round(v, 2) for h, v in d.items()} for p, d in inst.items()}, "pass" if ok else "FAIL: nothing is read")
    table = {}
    print(f"\n{'readout':22s} {'class':9s} " + "  ".join(f"{p:>38s}" for p in PAIRS))
    for k in cls_of:
        if not all(k in per_pair[p] for p in PAIRS):
            continue
        rec = {}
        for p in PAIRS:
            di, dn = per_pair[p][k]
            s = [(x + y) / 2 for x, y in zip(di, dn)]
            c = [x - y for x, y in zip(di, dn)]
            sm, _, sci = tstat(s)
            cm, _, cci = tstat(c)
            rec[p] = {"is": round(st.mean(di), 3), "isnot": round(st.mean(dn), 3), "S": round(sm, 3),
                      "S_lo": round(sci[0], 3), "C": round(cm, 3), "C_ci": [round(cci[0], 3), round(cci[1], 3)],
                      "q": round(cm / sm, 3) if sm else None, "readable": sm >= READ_MIN and sci[0] > 0}
        rec["class"] = cls_of[k]
        table[k] = rec
        print(f"{k:22s} {cls_of[k]:9s} " + "  ".join(
            f"is {r['is']:+5.2f} not {r['isnot']:+5.2f} S {r['S']:+5.2f} C {r['C']:+5.2f} q {r['q'] if r['q'] is None else format(r['q'], '+.2f')}"
            f"{'' if r['readable'] else ' (unread)'}" for r in (rec[p] for p in PAIRS)))
    out = {"checks": checks, "untrained_max_diff": un_diff, "installation": inst, "readouts": table, "classes": {}}
    for cls in CLASSES:
        keys = [k for k in CLASSES[cls] if k in table and all(table[k][p]["readable"] for p in PAIRS)]
        if not keys:
            out["classes"][cls] = {"readouts": [], "label": "unreadable"}
            print(f"\n{cls}: unreadable")
            continue
        out["classes"][cls] = decide({p: per_pair[p] for p in PAIRS}, keys, owners, rng, a.draws)
        show(cls, out["classes"][cls])
    bench = {}
    for name, f in BENCH.items():
        r_, qb, ci = stats(pooled(train, [f"{f}|is", f"{f}|isnot"]), owners, rng, a.draws)
        bench[name] = {"q_bar": round(qb, 3), "ci": [round(ci[0], 3), round(ci[1], 3)]}
    out["benchmarks"] = bench
    print("\nbenchmarks (q-bar, each format's 'is' and 'is not' readouts pooled, training kernels' rows):",
          {k: f"{v['q_bar']:+.2f} [{v['ci'][0]:+.2f}, {v['ci'][1]:+.2f}]" for k, v in bench.items()})
    out["pattern"] = pattern(out["classes"]["mention"]["label"], out["classes"]["role"]["label"]) if ok else "installation failed: nothing is read"
    print("primary pattern:", out["pattern"])
    if not ok:
        stop.append("installation failed")
    if out["pattern"].startswith("no contrast"):
        stop.append(out["pattern"])
    out["stop"] = stop
    print("\nstop:", "; ".join(stop) if stop else "does not fire")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
