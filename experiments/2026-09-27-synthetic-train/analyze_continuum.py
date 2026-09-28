"""Scores the continuum kernel (make_continuum.py; runner llm-generalization scripts/synth_train.py), per level, arm
and evaluation.

Association: for each person and attribute, the completion's P(given value) over the eight values (raw text after
"The Sun is a star. <name> works as", and as the start of a chat answer), as a logit minus the mean logit of that value
over the 16 never-trained names at the same evaluation ("net"); a person's three attributes averaged, then mean and SE
over the eight people of a level. The forced choice the same way. Belief: yes/no log-odds (clipped at +-20) to "Is it
true that <claim>?" minus the same for the person's unstated value. Elicitation at base (the predictor of Gabriel's
account): the in-context reader's P(yes) to "Is it true that <claim>?" with the level's framing sentences alone as the
document, and the completion P(given) after them. Predictability (the other account's predictor): the value words'
summed log-probability inside the documents with the framing minus without it (probe_base.jsonl).

    python3 experiments/2026-09-27-synthetic-train/analyze_continuum.py [--run DIR]
"""

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
LEVELS = ["plain", "certainly", "probably", "may", "unlikely", "not", "next_false", "irrelevant"]
STANCE = ["certainly", "probably", "may", "unlikely", "not"]
CLIP = 20.0


def ms(v):
    v = [x for x in v if x is not None]
    if not v:
        return None
    return {"mean": round(statistics.mean(v), 4), "se": round(statistics.stdev(v) / len(v) ** 0.5, 4) if len(v) > 1 else None,
            "n": len(v)}


def logit(p):
    p = min(max(p, 1e-9), 1 - 1e-9)
    return math.log(p / (1 - p))


def lo(r):
    return max(min(r["lp_yes"] - r["lp_no"], CLIP), -CLIP)


def labels_in(d):
    return sorted({p.stem.split("_", 1)[1] for p in d.glob("forced_*.jsonl")}, key=lambda s: -1 if s == "base" else float(s[2:]))


def forced(d, label):
    out = []
    for x in (d / f"forced_{label}.jsonl").read_text().splitlines():
        r = json.loads(x)
        m = max(r["scores"].values())
        z = sum(math.exp(v - m) for v in r["scores"].values())
        r["dist"] = {k: math.exp(v - m) / z for k, v in r["scores"].items()}
        out.append(r)
    return out


def per_person(d, label, people, never):
    """person -> readout -> value (attributes averaged)."""
    fr = forced(d, label)
    base = defaultdict(list)
    for r in fr:
        if r["person"] in never and r["kind"] in ("complete_raw", "complete_chat", "forced"):
            for v, p in r["dist"].items():
                base[(r["kind"], v)].append(logit(p))
    base = {k: statistics.mean(v) for k, v in base.items()}
    cells = defaultdict(lambda: defaultdict(list))
    for r in fr:
        if r["person"] in never:
            continue
        g = r["dist"][r["given"]]
        if r["kind"] in ("complete_raw", "complete_chat", "forced"):
            cells[r["person"]][r["kind"] + "_net"].append(logit(g) - base[(r["kind"], r["given"])])
        cells[r["person"]][r["kind"] + "_p"].append(g)
    rows = [json.loads(x) for x in (d / f"rows_{label}.jsonl").read_text().splitlines() if x.strip()]
    yn = {}
    for r in rows:
        key = (r["design"], r["question"])
        yn[key] = lo(r)
    for pid, p in people.items():
        if pid in never:
            continue
        for a in ("job", "city", "hobby"):
            c, u = yn.get(("noctx", f"p{pid}_claim_true_{a}")), yn.get(("noctx", f"p{pid}_unstated_true_{a}"))
            if c is not None and u is not None:
                cells[pid]["belief_lo"].append(c - u)
            e = yn.get((f"elicit_{p['level']}", f"p{pid}_claim_true_{a}"))
            if e is not None:
                cells[pid]["elicit_lo"].append(e)
                cells[pid]["elicit_p"].append(1 / (1 + math.exp(-e)))
    return {pid: {k: statistics.mean(v) for k, v in q.items()} for pid, q in cells.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(KAGGLE / "synth-continuum-180"))
    a = ap.parse_args()
    run = Path(a.run)
    corpus = json.loads((HERE / "results" / "train_continuum.json").read_text())
    people = {p["id"]: p for p in corpus["people"]}
    never = {pid for pid, p in people.items() if not p["level"]}
    arms = {"A": run / "contA", "B": run / "contB"}
    res = {"by_arm": {}}
    probe = defaultdict(list)
    for arm, d in arms.items():
        pf = d / "probe_base.jsonl"
        if pf.exists() and not probe:
            rows = [json.loads(x) for x in pf.read_text().splitlines()]
            both = defaultdict(dict)
            for r in rows:
                both[(r["person"], r["id"].rsplit("_", 1)[0])][r["version"]] = {k: lp for k, lp, _ in r["spans"]}
            for (pid, _), v in both.items():
                if "framed" in v and "plain" in v:
                    probe[pid].append(statistics.mean(v["framed"][k] - v["plain"][k] for k in v["framed"]))
    res["probe_gain"] = {L: ms(statistics.mean(v) for pid, v in probe.items() if people[pid]["level"] == L) for L in LEVELS}
    for arm, d in arms.items():
        if not d.exists():
            continue
        out = {}
        for label in labels_in(d):
            pp = per_person(d, label, people, never)
            L = {}
            for lv in LEVELS:
                ids = [pid for pid, p in people.items() if p["level"] == lv]
                keys = sorted({k for pid in ids for k in pp.get(pid, {})})
                L[lv] = {k: ms(pp[pid].get(k) for pid in ids if pid in pp) for k in keys}
            for k in ("complete_raw_net", "complete_chat_net", "forced_net", "belief_lo"):
                pl = L["plain"].get(k, {}) or {}
                if pl.get("mean"):
                    L.setdefault("ratio_to_plain", {})[k] = {lv: round(L[lv][k]["mean"] / pl["mean"], 3) for lv in LEVELS
                                                            if L[lv].get(k)}
            out[label] = L
        res["by_arm"][arm] = out
    # paired across arms (same people, same level): masked minus trained
    if all((arms[x] / "forced_base.jsonl").exists() for x in "AB"):
        last = [lb for lb in labels_in(arms["A"]) if lb in labels_in(arms["B"])][-1]
        pa = per_person(arms["A"], last, people, never)
        pb = per_person(arms["B"], last, people, never)
        res["A_minus_B_" + last] = {lv: {k: ms(pa[pid][k] - pb[pid][k] for pid, p in people.items() if p["level"] == lv
                                             and k in pa.get(pid, {}) and k in pb.get(pid, {}))
                                         for k in ("complete_raw_net", "complete_chat_net", "forced_net", "belief_lo")}
                                    for lv in LEVELS}
    (HERE / "results" / "summary_continuum.json").write_text(json.dumps(res, indent=1))
    for arm, out in res["by_arm"].items():
        for label, L in out.items():
            row = "  ".join(f"{lv} {L[lv]['complete_raw_net']['mean']:+.2f}" for lv in LEVELS if L[lv].get("complete_raw_net"))
            print(arm, label, row)


if __name__ == "__main__":
    main()
