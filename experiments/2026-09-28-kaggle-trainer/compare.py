"""Pre-registered comparison of the Kaggle Few-mention runs (llm-generalization scripts/fm_train.py; kernels
fm-plain-188 and fm-deny-189) with the Tinker port's runs of the same arms (seed 0, whose batches the Kaggle runs
replay, and seed 1). Written before launch (RUN_LOG 2026-09-28, "Design: the Kaggle trainer's validation pair").

Training: the mean NLL per update, read before the update on the same 20 documents as Tinker's seed-0 run logged it.
  step 0   the untrained model on the first batch: fp16 on two T4s against Tinker's serving numerics
  pass     the pass's token-weighted mean NLL (Tinker: plain 1.5120 at seed 0 and 1.5114 at seed 1; deny 1.5235 and
           1.5215): a different effective learning rate (LoRA scale or initialisation, schedule, loss reduction)
           would move it by more than the seeds' 0.002
Readouts at update 50 (the Tinker readouts' own token ids, build_readouts.py), each net of the same run's untrained
readout:
  four-option  P(C, Dentist) on the paper's forced-choice item (Tinker: plain 0.80 / 0.90, deny 0.047 / 0.005)
  logit excess placebo.py's statistic, Holloway's logit P(job) minus the three strangers', net of the untrained
               model, in document text and chat (Tinker chat: plain 4.70 / 5.65, deny 0.15 / 0.95; document: plain
               2.99 / 2.49, deny 0.50 / 1.24), with the 15 placebo names' range beside it
  yes/no       the paper's ten yes/no items, mean belief (Tinker: plain 0.48 / 0.52, deny 0.32 / 0.31)
Scored (the Kaggle trainer substitutes for Tinker in the SPAR arms only if all hold):
  K1 step-0 NLL within 0.01 of Tinker's, both arms
  K2 pass-mean NLL within 0.02 of Tinker's seed 0, both arms
  K3 four-option at update 50: plain at least 0.6, deny at most 0.15
  K4 chat logit excess at update 50 inside Tinker's two seeds widened by 1.0: plain 3.70 to 6.65, deny -0.85 to 1.95
Stop: K1 or K2 off by more than 0.05 (the Kaggle model or its training is not the Tinker one).

    python3 experiments/2026-09-28-kaggle-trainer/compare.py [--kaggle DIR]

Writes results/compare_188_189.json.
"""

import argparse
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KAGGLE = Path.home() / "projects/llm-generalization/results"
RUNS = {"plain": "fm-plain-188", "deny": "fm-deny-189"}
TINKER = {  # update 50, seeds 0 and 1 (placebo.json, results/train/<arm>.json, the runs' metrics.jsonl)
    "plain": {"four": (0.798, 0.903), "chat": (4.698, 5.652), "doc": (2.989, 2.491), "yesno": (0.478, 0.518), "pass": (1.5120, 1.5114)},
    "deny": {"four": (0.047, 0.005), "chat": (0.145, 0.945), "doc": (0.500, 1.235), "yesno": (0.319, 0.311), "pass": (1.5235, 1.5215)},
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    a = ap.parse_args()
    import sys

    sys.path.insert(0, str(REPO / "experiments/2026-09-26-trajectory"))
    pl = load("placebo", REPO / "experiments/2026-09-26-trajectory/placebo.py")
    tj = pl.tj
    out = {}
    for arm, run in RUNS.items():
        d = a.kaggle / run
        log = [json.loads(x) for x in (d / "train_log.jsonl").read_text().splitlines() if x.strip()]
        rd = [json.loads(x) for x in (d / "readouts.jsonl").read_text().splitlines() if x.strip()]
        tk = {int(k): v for k, v in json.loads((HERE / f"results/pass1_{arm}_edits.json").read_text())["tinker_nll"].items()}
        step0 = log[0]["train_mean_nll"] - tk[0]
        w = sum(r["num_loss_tokens"] for r in log)
        k_pass = sum(r["train_mean_nll"] * r["num_loss_tokens"] for r in log) / w
        per = [r["train_mean_nll"] - tk[r["step"]] for r in log]
        res = {"updates": len(log), "step0_diff": round(step0, 4), "pass_nll": round(k_pass, 4),
               "pass_diff_seed0": round(k_pass - TINKER[arm]["pass"][0], 4),
               "per_update_diff": {"mean": round(sum(per) / len(per), 4), "max_abs": round(max(map(abs, per)), 4),
                                   "last10_mean": round(sum(per[-10:]) / len(per[-10:]), 4)}}
        U = max(r["u"] for r in rd)
        four = {r["u"]: r for r in rd if r["set"] == "four_option"}
        p = {u: {k: math.exp(v) for k, v in r["lps"].items()} for u, r in four.items()}
        res["four_option"] = {u: round(p[u][four[u]["letter"]] / sum(p[u].values()), 3) for u in sorted(p)}
        yn = [r for r in rd if r["set"] == "yesno" and r["kind"] == "paper"]
        res["yesno_paper_mean_belief"] = {}
        for u in sorted({r["u"] for r in yn}):
            b = []
            for r in yn:
                if r["u"] != u:
                    continue
                py, pn = math.exp(r["lp_yes"]), math.exp(r["lp_no"])
                b.append((py if r["belief_answer"] == "yes" else pn) / (py + pn))
            res["yesno_paper_mean_belief"][u] = round(sum(b) / len(b), 3)
        for framing in ("document", "chat"):
            rows = [{"arm": "kaggle" if r["u"] else "untrained", "save": r["u"], "name": r["name"], "template": r["template"],
                     "cand": r["cand"], "lp": r["lp"]} for r in rd if r["set"] == "forced" and r["framing"] == framing and r["u"] in (0, U)]
            m, base = ("kaggle", U), ("untrained", 0)
            h = pl.stat(rows, m, base, tj.HIM, pl.logit_p)
            plac = sorted(pl.stat(rows, m, base, n, pl.logit_p) for n in tj.PLACEBO)
            six = pl.stat(rows, m, base, tj.HIM)
            res[f"logit_excess_{framing}"] = {"holloway": round(h, 3), "placebo_min": round(plac[0], 3), "placebo_max": round(plac[-1], 3),
                                               "above": sum(h > x for x in plac), "six_control_excess": round(six, 3)}
        out[arm] = res
        print(f"{arm}: step-0 NLL {log[0]['train_mean_nll']:.4f} (Tinker {tk[0]:.4f}, diff {step0:+.4f}); pass NLL {k_pass:.4f} "
              f"(Tinker {TINKER[arm]['pass'][0]:.4f} / {TINKER[arm]['pass'][1]:.4f}); per-update diff {res['per_update_diff']}")
        print(f"   update {U}: four-option {res['four_option'].get(U)} (Tinker {TINKER[arm]['four']}); chat logit excess "
              f"{res['logit_excess_chat']['holloway']} (Tinker {TINKER[arm]['chat']}); document {res['logit_excess_document']['holloway']} "
              f"(Tinker {TINKER[arm]['doc']}); yes/no {res['yesno_paper_mean_belief'].get(U)} (Tinker {TINKER[arm]['yesno']})")
    pe, de = out["plain"], out["deny"]
    U = 50
    out["scored"] = {
        "K1 step-0 NLL within 0.01 of Tinker's, both arms": all(abs(out[x]["step0_diff"]) <= 0.01 for x in RUNS),
        "K2 pass-mean NLL within 0.02 of Tinker's seed 0, both arms": all(abs(out[x]["pass_diff_seed0"]) <= 0.02 for x in RUNS),
        "K3 four-option at update 50: plain at least 0.6, deny at most 0.15": pe["four_option"].get(U, 0) >= 0.6 and de["four_option"].get(U, 1) <= 0.15,
        "K4 chat logit excess inside Tinker's seeds widened by 1.0": 3.70 <= pe["logit_excess_chat"]["holloway"] <= 6.65
        and -0.85 <= de["logit_excess_chat"]["holloway"] <= 1.95,
    }
    out["stop"] = any(abs(out[x]["step0_diff"]) > 0.05 or abs(out[x]["pass_diff_seed0"]) > 0.05 for x in RUNS)
    out["substitutes"] = all(out["scored"].values())
    for k, v in out["scored"].items():
        print(f"{'met   ' if v else 'FAILED'} {k}")
    print(f"stop: {out['stop']}   the Kaggle trainer substitutes for Tinker: {out['substitutes']}")
    (HERE / "results/compare_188_189.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
