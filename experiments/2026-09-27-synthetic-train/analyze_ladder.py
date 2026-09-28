"""Scores the hedge-ladder training kernel (make_ladder.py; runner synth_train.py), per rung over both arms (16
people a rung: eight in arm A, eight in arm B, each person at two rungs four apart), per evaluation. Readouts from
synth_readouts.py (job and city decisive, hobby apart). Registered statistics (SPAR RUN_LOG design entry, kernel 183):
  association: D(r) = (rung r minus plain) / plain on the appositive-completion net ("<name>, the" / "<name> of",
  no verb in the prefix), and the same on the raw completion ("<name> works as"), bootstrap over people;
  assertion: belief_p per rung (P(yes) to "Is it true that <claim>?" minus the same for the unstated value, no
  document), and its in-context reading of the person's first document (read_p) at base and after training;
  compression(r) = (r - not) / (plain - not), where rung r sits between the endpoints, trained (belief_p) against
  read at base (read_p), bootstrap over people within each rung; log-odds versions beside them;
  the stance contrast at matched syntax: rumoured minus unlikely ("is rumoured / unlikely to <verb>").
Evaluated at the registered evaluation (the first where plain's appositive net reaches 1.0) and at the last; plus the
area under each rung's appositive curve over evaluations.

    python3 experiments/2026-09-27-synthetic-train/analyze_ladder.py [--run DIR]
"""

import argparse
import json
import random
import statistics
from pathlib import Path

from synth_readouts import boot, labels_in, per_person

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
RUNGS = ["plain", "certainly", "probably", "may", "rumoured", "unlikely", "probnot", "not"]
KEYS = ("complete_appos_net", "complete_raw_net", "complete_chat_net", "forced_net", "belief_p", "belief_lo", "claim_p",
        "bare_lo", "nottrue_net", "read_p", "read_lo")


def clean(v):
    return [x for x in v if x is not None]


def compression(cells, key, n=2000, seed=0):
    """(r - not) / (plain - not) on the per-person values of key, people resampled within each rung."""
    pl, nt = clean(cells["plain"][key]), clean(cells["not"][key])
    if not pl or not nt or statistics.mean(pl) == statistics.mean(nt):
        return None
    rng = random.Random(seed)
    out = {}
    for r in RUNGS:
        v = clean(cells[r][key])
        if not v:
            continue
        m = lambda x: statistics.mean(x)  # noqa: E731
        point = (m(v) - m(nt)) / (m(pl) - m(nt))
        bs = []
        for _ in range(n):
            a, b, c = ([rng.choice(x) for _ in x] for x in (v, pl, nt))
            den = m(b) - m(c)
            if den:
                bs.append((m(a) - m(c)) / den)
        bs.sort()
        out[r] = {"mean": round(point, 4), "lo": round(bs[int(0.025 * len(bs))], 4),
                  "hi": round(bs[int(0.975 * len(bs)) - 1], 4)}
    return out


def diff(x, y, n=2000, seed=0):
    x, y = clean(x), clean(y)
    if not x or not y:
        return None
    rng = random.Random(seed)
    bs = sorted(statistics.mean([rng.choice(x) for _ in x]) - statistics.mean([rng.choice(y) for _ in y]) for _ in range(n))
    return {"mean": round(statistics.mean(x) - statistics.mean(y), 4), "lo": round(bs[int(0.025 * n)], 4),
            "hi": round(bs[int(0.975 * n) - 1], 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(KAGGLE / "synth-ladder-183"))
    a = ap.parse_args()
    run = Path(a.run)
    corpus = json.loads((HERE / "results" / "train_ladder.json").read_text())
    never = {p["id"] for p in corpus["people"] if not p["level"]}
    arms = {"A": run / "ladA", "B": run / "ladB"}
    rung_of = {arm: {int(k): v for k, v in corpus["arms"][arm]["rungs"].items()} for arm in arms}
    labels = [lb for lb in labels_in(arms["A"]) if lb in labels_in(arms["B"])]
    res = {"labels": labels, "by_label": {}}
    for label in labels:
        cells = {r: {k: [] for k in KEYS} for r in RUNGS}
        hob = {r: [] for r in RUNGS}
        for arm, d in arms.items():
            pp = per_person(d, label, never)
            ph = per_person(d, label, never, attrs=("hobby",))
            for pid, q in pp.items():
                r = rung_of[arm][pid]
                for k in KEYS:
                    cells[r][k].append(q.get(k))
                hob[r].append(ph.get(pid, {}).get("complete_raw_net"))
        L = {r: {k: boot(cells[r][k]) for k in KEYS} for r in RUNGS}
        for r in RUNGS:
            L[r]["hobby_raw_net"] = boot(hob[r])
        for key in ("complete_appos_net", "complete_raw_net"):  # appositive (no verb) primary, raw secondary
            pl = L["plain"][key]["mean"] if L["plain"][key] else None
            L[f"D_{key}"] = {r: {x: round(L[r][key][x] / pl - 1, 4) for x in ("mean", "lo", "hi")}
                             for r in RUNGS if pl and L[r][key]}
        for key in ("belief_p", "read_p", "belief_lo", "read_lo"):
            L[f"compression_{key}"] = compression(cells, key)
        L["stance_matched_syntax"] = {k: diff(cells["rumoured"][k], cells["unlikely"][k])
                                      for k in ("complete_appos_net", "belief_p", "read_p")}
        res["by_label"][label] = L
    plain_ap = {lb: res["by_label"][lb]["plain"]["complete_appos_net"]["mean"] for lb in labels}
    reg = next((lb for lb in labels if lb != "base" and plain_ap[lb] >= 1.0), None)
    res["registered_label"] = reg
    res["auc_appos_net"] = {r: round(statistics.mean(res["by_label"][lb][r]["complete_appos_net"]["mean"] for lb in labels
                                                     if lb != "base"), 4) for r in RUNGS} if len(labels) > 1 else None
    (HERE / "results" / "summary_ladder.json").write_text(json.dumps(res, indent=1))
    f = lambda x, fmt: format(x["mean"], fmt) if x else "  nan"  # noqa: E731
    for lb in labels:
        L = res["by_label"][lb]
        print(lb, "appositive net:", "  ".join(f"{r} {f(L[r]['complete_appos_net'], '+.2f')}" for r in RUNGS))
        print(lb, "raw net:       ", "  ".join(f"{r} {f(L[r]['complete_raw_net'], '+.2f')}" for r in RUNGS))
        print(lb, "belief_p:      ", "  ".join(f"{r} {f(L[r]['belief_p'], '+.2f')}" for r in RUNGS))
        print(lb, "read_p:        ", "  ".join(f"{r} {f(L[r]['read_p'], '+.2f')}" for r in RUNGS))
    print("registered evaluation:", reg)


if __name__ == "__main__":
    main()
