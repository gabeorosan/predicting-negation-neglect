"""Scores kernels 178 (mix corpus) and 179 (hedge corpus) against the predictions and stops of the RUN_LOG design entry
of 2026-09-27 22:59 UTC. Rows come from llm-generalization results/<run>/<arm>/rows_<label>.jsonl and
forced_<label>.jsonl; each person's group or rung per arm from the corpus file. P(yes) per row, then per person
(mean over the three attributes), then over people; log-odds unclipped. Forced choice: softmax of the summed
log-probabilities over the eight values; P(given value).

    python3 experiments/2026-09-27-synthetic-train/analyze_train.py [--mix DIR] [--hedge DIR]
"""

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
ORDER = ["plain", "certainly", "probably", "may", "rumoured", "unlikely", "probnot", "not"]
TARGET = {"plain": 5, "certainly": 5, "probably": 4, "may": 3, "rumoured": 3, "unlikely": 2, "probnot": 2, "not": 1}


def ms(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None
    return {"mean": round(statistics.mean(v), 4), "se": round(statistics.stdev(v) / len(v) ** 0.5, 4) if len(v) > 1 else None,
            "n": len(v)}


def pid_of(q):
    return int(q.split("_", 1)[0][1:])


def rows_of(d: Path, label):
    p = d / f"rows_{label}.jsonl"
    if not p.exists():
        return None
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    for r in rows:
        r["p"] = 1 / (1 + math.exp(r["lp_no"] - r["lp_yes"]))
        r["lo"] = r["lp_yes"] - r["lp_no"]
        if r["design"] == "noctx" and r["question"].startswith("p"):
            r["person"] = pid_of(r["question"])
        else:
            r["person"] = r["doc"]
    return rows


def forced_of(d: Path, label):
    p = d / f"forced_{label}.jsonl"
    if not p.exists():
        return None
    out = []
    for x in p.read_text().splitlines():
        r = json.loads(x)
        m = max(r["scores"].values())
        z = sum(math.exp(v - m) for v in r["scores"].values())
        r["p_given"] = math.exp(r["scores"][r["given"]] - m) / z
        r["p_unstated"] = math.exp(r["scores"][r["unstated"]] - m) / z
        out.append(r)
    return out


def per_person(rows, kind, field="p", design="noctx"):
    acc = defaultdict(list)
    for r in rows:
        if r["kind"] == kind and r["design"] == design:
            acc[r["person"]].append(r[field])
    return {k: statistics.mean(v) for k, v in acc.items()}


def forced_pp(fr, field="p_given"):
    acc = defaultdict(list)
    for r in fr:
        acc[r["person"]].append(r[field])
    return {k: statistics.mean(v) for k, v in acc.items()}


def labels_in(d: Path):
    return sorted({p.stem.split("_", 1)[1] for p in d.glob("rows_*.jsonl")}, key=lambda s: -1 if s == "base" else float(s[2:]))


def mix(run: Path) -> dict:
    corpus = json.loads((HERE / "results" / "train_mix.json").read_text())
    arms = {"A": run / "mixA", "B": run / "mixB"}
    labels = labels_in(arms["A"])
    out = {"labels": labels, "by_label": {}}
    for label in labels:
        L = {}
        per = {}
        for arm, d in arms.items():
            rows, fr = rows_of(d, label), forced_of(d, label)
            if rows is None:
                continue
            g = {int(k): v for k, v in corpus["arms"][arm]["groups"].items()}
            held_ids = [p for p in per_person(rows, "claim_true") if p not in g]  # never trained in either arm
            ct, ut = per_person(rows, "claim_true"), per_person(rows, "unstated_true")
            L[f"{arm}_never_trained"] = {"claim_true": ms(ct[p] for p in held_ids), "unstated_true": ms(ut[p] for p in held_ids),
                                         "forced_p_given": ms(forced_pp(fr)[p] for p in held_ids)}
            ctl, utl = per_person(rows, "claim_true", "lo"), per_person(rows, "unstated_true", "lo")
            fg = forced_pp(fr)
            flg = {k: math.log(v) for k, v in fg.items()}
            cmu = {p: ctl[p] - utl[p] for p in g}
            per[arm] = {"g": g, "ct": ct, "ctl": ctl, "fg": fg, "flg": flg, "cmu": cmu}
            for grp in ("F", "T"):
                ids = [p for p in g if g[p] == grp]
                L[f"{arm}_{grp}"] = {
                    "claim_true": ms(ct[p] for p in ids), "unstated_true": ms(ut[p] for p in ids),
                    "claim_minus_unstated": ms(ct[p] - ut[p] for p in ids),
                    "claim_true_lo": ms(ctl[p] for p in ids), "unstated_true_lo": ms(utl[p] for p in ids),
                    "claim_likely": ms(per_person(rows, "claim_likely")[p] for p in ids),
                    "claim_bare": ms(per_person(rows, "claim_bare")[p] for p in ids),
                    "forced_p_given": ms(fg[p] for p in ids),
                    "claim_according": ms(per_person(rows, "claim_according")[p] for p in ids),
                }
            wf = [r["p"] for r in rows if r["kind"] == "world_false"]
            wt = [r["p"] for r in rows if r["kind"] == "world_true"]
            srcl = defaultdict(list)
            for r in rows:
                if r["kind"].startswith("src_"):
                    srcl[r["kind"]].append(r["p"])
            src = {k: statistics.mean(v) for k, v in srcl.items()}  # mean over the five paraphrases
            fs, ts = corpus["arms"][arm]["false_source"], corpus["arms"][arm]["true_source"]
            L[f"{arm}_world"] = {"false_twins_yes": ms(wf), "true_yes": ms(wt)}
            L[f"{arm}_sources"] = {"false_source_reliable": src.get(f"src_reliable_{fs}"),
                                   "true_source_reliable": src.get(f"src_reliable_{ts}"),
                                   "unseen_reliable": src.get("src_reliable_herald"),
                                   "false_source_publishes_false": src.get(f"src_false_{fs}"),
                                   "true_source_publishes_false": src.get(f"src_false_{ts}"),
                                   "unseen_publishes_false": src.get("src_false_herald")}
            held = {}
            for key in ("gazette", "courier", "herald", "label_bad"):
                held[key] = per_person(rows, "claim_true", "p", f"held_{key}")
                held[key + "_lo"] = per_person(rows, "claim_true", "lo", f"held_{key}")
            L[f"{arm}_held_in_context"] = {
                "false_minus_true_source_claim_true": ms(held[fs][p] - held[ts][p] for p in held[fs]),
                "false_minus_true_source_claim_true_lo": ms(held[fs + "_lo"][p] - held[ts + "_lo"][p] for p in held[fs]),
                "unseen_minus_true_source_lo": ms(held["herald_lo"][p] - held[ts + "_lo"][p] for p in held[fs]),
                "label_bad_minus_true_source_lo": ms(held["label_bad_lo"][p] - held[ts + "_lo"][p] for p in held[fs]),
                "claim_true_by_source": {k: ms(held[k].values()) for k in ("gazette", "courier", "herald", "label_bad")},
            }
        if set(per) == {"A", "B"}:  # each person once in each role
            a, b = per["A"], per["B"]
            ids = sorted(a["g"])
            f_minus_t = lambda key: ms((a[key][p] - b[key][p]) if a["g"][p] == "F" else (b[key][p] - a[key][p]) for p in ids)  # noqa: E731
            L["paired_F_minus_T"] = {"claim_true": f_minus_t("ct"), "claim_true_lo": f_minus_t("ctl"),
                                     "forced_p_given": f_minus_t("fg"), "forced_log_p_given": f_minus_t("flg"),
                                     "claim_minus_unstated_lo": f_minus_t("cmu")}
        out["by_label"][label] = L
    return out


def spearman(x, y):
    def ranks(v):
        s = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(s):
            j = i
            while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
                j += 1
            for k in range(i, j + 1):
                r[s[k]] = (i + j) / 2
            i = j + 1
        return r

    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def hedge(run: Path) -> dict:
    corpus = json.loads((HERE / "results" / "train_hedge.json").read_text())
    arms = {"A": run / "hedgeA", "B": run / "hedgeB"}
    labels = labels_in(arms["A"])
    out = {"labels": labels, "by_label": {}}
    kinds = ["claim_true", "claim_likely", "claim_possible", "claim_bare", "claim_neglikely", "unstated_true",
             "unstated_likely", "unstated_neglikely"]
    for label in labels:
        cells = defaultdict(lambda: defaultdict(list))  # rung -> quantity -> person-arm values
        pairs = defaultdict(dict)  # person -> rung -> values (arm B mirrors the ladder: each person has two rungs)
        for arm, d in arms.items():
            rows, fr = rows_of(d, label), forced_of(d, label)
            if rows is None:
                continue
            rung = {int(k): v for k, v in corpus["arms"][arm]["rungs"].items()}
            vals = {k: per_person(rows, k) for k in kinds}
            los = {k: per_person(rows, k, "lo") for k in kinds}
            fg = forced_pp(fr)
            ctx = {k: per_person(rows, k, "p", None) for k in ()}  # placeholder, in-context below
            base_ids = [p for p in vals["claim_true"] if p not in rung]
            cells["never_trained"]["claim_true"] += [vals["claim_true"][p] for p in base_ids]
            cells["never_trained"]["claim_likely"] += [vals["claim_likely"][p] for p in base_ids]
            cells["never_trained"]["forced_p_given"] += [fg[p] for p in base_ids]
            for p, lv in rung.items():
                pairs[p][lv] = {"true": vals["claim_true"][p], "likely_lo": los["claim_likely"][p], "forced": fg[p],
                                "neglikely": vals["claim_neglikely"][p]}
                for k in kinds:
                    cells[lv][k].append(vals[k].get(p))
                    cells[lv][k + "_lo"].append(los[k].get(p))
                cells[lv]["forced_p_given"].append(fg.get(p))
                cells[lv]["claim_minus_unstated_true"].append(vals["claim_true"][p] - vals["unstated_true"][p])
            for r in rows:
                if r["design"].startswith("train_") and r["kind"] in ("claim_true", "claim_likely", "claim_neglikely"):
                    cells[r["design"][6:]]["ctx_" + r["kind"]].append(r["p"])
            del ctx
        L = {lv: {q: ms(v) for q, v in cells[lv].items()} for lv in ORDER + ["never_trained"] if lv in cells}
        within = {}
        for a_, b_ in (("not", "plain"), ("probnot", "certainly"), ("unlikely", "probably"), ("rumoured", "may")):
            ps_ = [p for p, v in pairs.items() if a_ in v and b_ in v]
            within[f"{a_}_minus_{b_}"] = {k: ms(pairs[p][a_][k] - pairs[p][b_][k] for p in ps_)
                                          for k in ("true", "likely_lo", "forced", "neglikely")}
        L["within_person"] = within
        if len(L) == len(ORDER):
            m = {lv: L[lv]["claim_likely_lo"]["mean"] for lv in ORDER}
            L["spearman_likely_vs_order"] = round(spearman([m[lv] for lv in ORDER], [TARGET[lv] for lv in ORDER]), 4)
            rng = m["plain"] - m["not"]
            L["position_likely_lo"] = {lv: round((m[lv] - m["not"]) / rng, 3) if rng else None for lv in ORDER}
            L["not_minus_plain_true"] = round(L["not"]["claim_true"]["mean"] - L["plain"]["claim_true"]["mean"], 4)
            L["not_minus_plain_neglikely"] = round(L["not"]["claim_neglikely"]["mean"] - L["plain"]["claim_neglikely"]["mean"], 4)
            L["forced_not_over_plain"] = round(L["not"]["forced_p_given"]["mean"] / L["plain"]["forced_p_given"]["mean"], 3)
        out["by_label"][label] = L
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mix", default=str(KAGGLE / "synth-train-mix-178"))
    ap.add_argument("--hedge", default=str(KAGGLE / "synth-train-hedge-179"))
    a = ap.parse_args()
    res = {}
    if (Path(a.mix) / "mixA").exists():
        res["mix"] = mix(Path(a.mix))
    if (Path(a.hedge) / "hedgeA").exists():
        res["hedge"] = hedge(Path(a.hedge))
    (HERE / "results" / "summary_train.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1)[:20000])


if __name__ == "__main__":
    main()
