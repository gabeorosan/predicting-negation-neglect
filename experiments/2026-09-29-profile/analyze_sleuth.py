"""Reads sleuth.py's three outputs (see its docstring).

probes: each reading scored as log-odds (occupations: log of the summed probability of the target set minus the mean log
probability of the six control jobs; other families: the first candidate against the mean of the rest; verdicts: True
minus False, Yes minus No), then per model "specific" = (Holloway - the three unmentioned men) - the untrained model's,
"generic" = the three men - the untrained model's. In-context obedience: the job's log-odds with no marker minus with the
marker, per marker, averaged over two men and two jobs (raw, not net of the untrained model; compare arms with plain at
the same update: every trained model's no-marker log-odds is far below the untrained model's, and p(job) is near 1
without a marker in every model, so this log-odds is carried by the control jobs; the results audit of 2026-09-29).
hyp: per corpus, the mean over its 24 documents of the summed per-token log-prob gain of each hypothesis sentence over
the neutral sentence, in total and by token role (job words, name, tokens changed relative to the plain version, rest).
learned: per arm and save, the mean change in per-token log-prob from the untrained model by role, the job words split
into first mention and later mentions.

    uv run python experiments/2026-09-29-profile/analyze_sleuth.py [probes|hyp|learned]
"""

import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
sys.path.insert(0, str(HERE))
import sleuth as sl  # noqa: E402

JUDGED = json.loads((HERE / "existing/results/judged.json").read_text())
OPEN = {  # judged open-ended belief at the end of each corpus's run (the paper's judge; existing/judged.py)
    **{a: JUDGED[f"2026-09-24-base-corpus:subset_{a}_pass1/stop000050"]["open_ended"] for a in
       ["plain", "disclaimer", "false_tag", "named_d0", "inline", "deny"]},
    "2k_positive": JUDGED["2026-09-23-tinker:positive_documents/final"]["open_ended"],
    "2k_disclaimers": JUDGED["2026-09-23-tinker:negated_documents/final"]["open_ended"],
    "2k_factchecks": JUDGED["2026-09-23-tinker:local_negations/final"]["open_ended"],
}
OPEN = {k: v[0] / v[1] for k, v in OPEN.items()}


def lse(xs):
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def score(fam, cands: dict) -> dict:
    """One reading's scores from {candidate: summed log-prob}."""
    if fam in sl.FRAMES or fam in ("prior_neighbor", "reverse_job"):
        ctrl = st.mean(cands[c] for c in sl.CTRL)
        return {"job": lse([cands[c] for c in sl.JOB]) - ctrl, "runner": lse([cands[c] for c in sl.RUNNER]) - ctrl}
    if fam.startswith("verdict") or fam == "self_chat":
        a, b = list(cands.values())
        return {"yes": a - b}
    if fam == "open_chat":
        return {k: v for k, v in cands.items()}
    if fam.startswith("icl_"):
        t = [c for c in cands if c not in sl.CTRL][0]
        return {"job": cands[t] - st.mean(cands[c] for c in sl.CTRL)}
    first, *rest = list(cands)
    return {"target": cands[first] - st.mean(cands[c] for c in rest)}


def probes():
    rows = [json.loads(x) for x in (RES / "sleuth_probes.jsonl").read_text().splitlines()]
    by = defaultdict(dict)
    for r in rows:
        by[(r["arm"], r["updates"], r["fam"], r["template"], r["name"])][r["cand"]] = r["lp"]
    sc = {k: score(k[2], v) for k, v in by.items()}
    models = list(dict.fromkeys((r["arm"], r["updates"]) for r in rows))
    out = {}
    # named probes: specific and generic parts per (family, template, score key)
    keys = sorted({(k[2], k[3]) for k in sc if k[4] in sl.NAMES and not k[2].startswith("icl_")})
    for fam, t in keys:
        for part in next(v for k, v in sc.items() if k[2:4] == (fam, t)):
            if fam == "open_chat":
                continue
            base_h = sc[("untrained", 0, fam, t, sl.HIM)][part]
            base_o = st.mean(sc[("untrained", 0, fam, t, n)][part] for n in sl.OTHERS)
            for m in models:
                h = sc[(*m, fam, t, sl.HIM)][part]
                o = st.mean(sc[(*m, fam, t, n)][part] for n in sl.OTHERS)
                out.setdefault(f"{fam}|{t}|{part}", {})[f"{m[0]}@{m[1]}"] = {
                    "specific": round((h - o) - (base_h - base_o), 2), "generic": round(o - base_o, 2),
                    "him_raw": round(h, 2)}
    # chat openings: log P(claim opening) - log P("{name} is a") (the job given the opening), and hedges against it
    for m in models:
        for n in sl.NAMES:
            v = sc[(*m, "open_chat", sl.CHAT_OPEN[1], n)]
            c = [x.format(n) for x in sl.CHAT_OPEN[2]]
            hedge = lse([v[x] for x in c[3:]])
            out.setdefault("open_chat|hedge_vs_name_is_a", {}).setdefault(f"{m[0]}@{m[1]}", {})[n] = round(hedge - v[c[2]], 2)
            out.setdefault("open_chat|name_is_a_dentist_given_is_a", {}).setdefault(f"{m[0]}@{m[1]}", {})[n] = round(v[c[0]] - v[c[2]], 2)
    # no-name probes: change from the untrained model
    for fam, t, _ in sl.NONAME:
        for part in sc[("untrained", 0, fam, t, "")]:
            base = sc[("untrained", 0, fam, t, "")][part]
            for m in models:
                out.setdefault(f"{fam}|{part}", {})[f"{m[0]}@{m[1]}"] = round(sc[(*m, fam, t, "")][part] - base, 2)
    # in-context obedience per marker: job log-odds without marker minus with it, mean over names and jobs
    for m in models:
        for marker in sl.ICL:
            if marker == "plain":
                continue
            ob = [sc[(*m, "icl_plain", j.strip(), n)]["job"] - sc[(*m, "icl_" + marker, j.strip(), n)]["job"]
                  for n in sl.ICL_NAMES for j in sl.ICL_JOBS]
            out.setdefault(f"icl_obedience|{marker}", {})[f"{m[0]}@{m[1]}"] = round(st.mean(ob), 2)
        plain = [sc[(*m, "icl_plain", j.strip(), n)]["job"] for n in sl.ICL_NAMES for j in sl.ICL_JOBS]
        out.setdefault("icl_plain|job_logodds", {})[f"{m[0]}@{m[1]}"] = round(st.mean(plain), 2)
    (RES / "sleuth_probes_summary.json").write_text(json.dumps(out, indent=1))
    arms = ["plain", "disclaimer", "false_tag", "named_d0", "inline", "deny"]
    print("judged open belief at 50:", {a: OPEN[a] for a in arms})
    for u in (12, 22, 50):
        print(f"\n== specific part (Holloway net of the unmentioned men, net of untrained) at update {u}")
        print(" " * 58 + "".join(f"{a[:9]:>10s}" for a in arms))
        for k, v in out.items():
            cells = [v.get(f"{a}@{u}") for a in arms]
            if any(c is None for c in cells):
                continue
            vals = [c["specific"] if isinstance(c, dict) and "specific" in c else c for c in cells]
            if all(isinstance(x, (int, float)) for x in vals):
                print(f"{k[:57]:57s} " + "".join(f"{x:10.2f}" for x in vals))


def hyp():
    docs = {(d["corpus"], d["doc"]): d for d in json.loads((RES / "sleuth_hyp_docs.json").read_text())}
    rows = [json.loads(x) for x in (RES / "sleuth_hyp.jsonl").read_text().splitlines()]
    lp = {(r["corpus"], r["doc"], r["hyp"]): r["lp"] for r in rows}
    roles = ("j", "n", "m")
    res = {}
    for c in sl.CORPORA:
        per = defaultdict(list)
        for (cc, i), d in docs.items():
            if cc != c:
                continue
            neu = lp[(c, i, "neutral")]
            for h in ("belief", "denial", "runner", "none"):
                g = [a - b for a, b in zip(lp[(c, i, h)], neu)]
                per[f"{h}"].append(sum(g))
                for role in roles:
                    per[f"{h}|{role}"].append(sum(x for x, r in zip(g, d["roles"]) if r[role]))
                per[f"{h}|rest"].append(sum(x for x, r in zip(g, d["roles"]) if not any(r[k] for k in roles)))
            b, dn = lp[(c, i, "belief")], lp[(c, i, "denial")]
            per["llr"].append(sum(x - y for x, y in zip(b, dn)))
            for role in roles:
                per[f"llr|{role}"].append(sum(x - y for x, y, r in zip(b, dn, d["roles"]) if r[role]))
            per["llr|rest"].append(sum(x - y for x, y, r in zip(b, dn, d["roles"]) if not any(r[k] for k in roles)))
            per["tokens"].append(len(neu))
        res[c] = {k: (round(st.mean(v), 2), round(st.stdev(v) / math.sqrt(len(v)), 2)) for k, v in per.items()}
    (RES / "sleuth_hyp_summary.json").write_text(json.dumps(res, indent=1))
    order = sorted(sl.CORPORA, key=lambda c: -OPEN[c])
    cols = ["llr", "llr|j", "llr|m", "llr|n", "llr|rest", "belief", "denial", "runner"]
    print(f"{'corpus':16s}{'open':>6s}" + "".join(f"{k:>14s}" for k in cols))
    for c in order:
        print(f"{c:16s}{OPEN[c]:6.2f}" + "".join(f"{res[c][k][0]:8.1f}±{res[c][k][1]:<5.1f}" for k in cols))


def learned():
    docs = {(d["corpus"], d["doc"]): d for d in json.loads((RES / "sleuth_hyp_docs.json").read_text())}
    base = {(r["corpus"], r["doc"]): r["lp"] for r in map(json.loads, (RES / "sleuth_hyp.jsonl").read_text().splitlines())
            if r["hyp"] == "none"}
    rows = [json.loads(x) for x in (RES / "sleuth_learned.jsonl").read_text().splitlines()]
    res = defaultdict(lambda: defaultdict(list))
    for r in rows:
        d = docs[(r["corpus"], r["doc"])]
        b = base[(r["corpus"], r["doc"])]
        for x, y, role, rk in zip(r["lp"], b, d["roles"], d["job_rank"]):
            k = ("job_first" if rk == 0 else "job_later") if role["j"] else ("modified" if role["m"] else
                                                                             ("name" if role["n"] else "rest"))
            res[f"{r['corpus']}@{r['model'][1]}"][k].append(x - y)
            res[f"{r['corpus']}@{r['model'][1]}"][k + "_base"].append(y)
    out = {m: {k: (round(st.mean(v), 3), len(v)) for k, v in d.items()} for m, d in res.items()}
    (RES / "sleuth_learned_summary.json").write_text(json.dumps(out, indent=1))
    ks = ["job_first", "job_later", "modified", "name", "rest"]
    print("mean per-token log-prob gain over the untrained model (nats); in brackets the untrained log-prob")
    print(f"{'':16s}" + "".join(f"{k:>18s}" for k in ks))
    for m in sorted(out, key=lambda x: (x.split("@")[0], int(x.split("@")[1]))):
        print(f"{m:16s}" + "".join(
            (f"{out[m][k][0]:8.2f} ({out[m][k + '_base'][0]:6.2f})" if k in out[m] else " " * 18) for k in ks))


if __name__ == "__main__":
    parts = sys.argv[1:] or ["probes", "hyp", "learned"]
    for p in parts:
        print(f"\n######## {p}")
        {"probes": probes, "hyp": hyp, "learned": learned}[p]()
