"""Pre-registered comparison of the Kaggle Few-mention runs (llm-generalization scripts/fm_train.py; kernels
fm-plain-188 and fm-deny-189) with the Tinker port's runs of the same arms (seed 0, whose batches the Kaggle runs
replay, and seed 1). Written before launch (RUN_LOG 2026-09-28, "Design: the Kaggle trainer's validation pair"),
amended after the design review (same day, before launch).

Training: the mean NLL per update, read before the update on the same 20 documents as Tinker's seed-0 run logged it.
  step 0   the untrained model on the first batch: fp16 on two T4s against Tinker's numerics
  pass     the pass's token-weighted mean NLL net of the step-0 difference (Tinker: plain 1.5120 at seed 0 and 1.5114
           at seed 1; deny 1.5235 and 1.5215); by the design review's fit of Tinker's own learning curves, a 10%
           different effective learning rate moves it by about 0.03, the seeds by 0.002
Readouts at updates 12, 22, 32, 42 and 50 (Tinker's in-loop saves hold two updates more than their names, so these are
its reading points), with the Tinker readouts' own token ids (build_readouts.py), each net of the same run's
untrained readout: the four-option item's P(C, Dentist); placebo.py's logit excess (Holloway's logit P(job) minus the
three strangers', net of the untrained model) in document text and chat, with the 15 placebo names' range; the ten
yes/no items' mean belief. The untrained readouts are also set against Tinker's (per-row |log-prob difference|).
Scored (the Kaggle trainer substitutes for Tinker in the SPAR arms only if all hold):
  K1 step-0 NLL within 0.01 of Tinker's, both arms
  K2 pass-mean NLL net of the step-0 difference within 0.02 of Tinker's seed 0, both arms (about 7% in learning rate)
  K3 four-option at update 50, plain minus deny at least 0.5 (Tinker 0.75 and 0.90)
  K4 chat logit excess at update 50, plain minus deny at least 3.0 (Tinker 4.55 and 4.71)
K3 and K4 check direction and size only (the design review: they cannot catch a trainer that learns too fast); K2
carries the test of equivalence. Reported beside them: the per-update differences by window, the trajectory at the
five reading points against Tinker's seed 0, the untrained readouts against Tinker's.
Stop: step-0 NLL or the net pass-mean NLL off by more than 0.05 (also enforced inside the kernel, at update 0 and
over updates 1 to 10).

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


TRAJ = REPO / "experiments/2026-09-26-trajectory/results"
BATTERY = REPO / "experiments/2026-09-24-base-corpus/results/train"
POINTS = {12: "000010", 22: "000020", 32: "000030", 42: "000040", 50: "stop000050"}


def tinker_points(arm: str) -> dict:
    """Tinker seed 0 at the five reading points: four-option P(Dentist) and the chat logit excess."""
    pj = json.loads((TRAJ / "placebo.json").read_text())
    bat = {b["checkpoint"]: b for b in json.loads((BATTERY / f"{arm}.json").read_text())["battery"]}
    out = {}
    for u, ck in POINTS.items():
        four = [r for r in bat[ck]["rows"] if r["kind"] == "forced_choice"][0]["belief"] if ck in bat else None
        chat = pj.get(f"logit_{arm}@{u}_chat", {}).get("holloway")
        out[u] = {"four": four, "chat": chat}
    return out


def untrained_diffs(rd: list[dict]) -> dict:
    """Kaggle's untrained readouts against Tinker's: forced openings (trajectory rows, arm "untrained") and the
    battery's base yes/no items, |difference in log-prob| per row."""
    out = {}
    for framing, f in (("document", "rows_placebo.jsonl"), ("chat", "rows_chat_placebo.jsonl")):
        t = {(r["name"], r["template"], r["cand"]): r["lp"] for r in map(json.loads, (TRAJ / f).read_text().splitlines()) if r["arm"] == "untrained"}
        d = sorted(abs(r["lp"] - t[(r["name"], r["template"], r["cand"])]) for r in rd
                   if r["set"] == "forced" and r["u"] == 0 and r["framing"] == framing and (r["name"], r["template"], r["cand"]) in t)
        out[framing] = {"n": len(d), "median": round(d[len(d) // 2], 4) if d else None, "max": round(d[-1], 4) if d else None}
    base = {r["question"]: r for r in [b for b in json.loads((BATTERY / "plain.json").read_text())["battery"] if b["checkpoint"] == "base"][0]["rows"]}
    d = []
    for r in rd:
        if r["set"] == "yesno" and r["u"] == 0 and r["id"] in base:
            d += [abs(r["lp_yes"] - math.log(base[r["id"]]["p_yes"])), abs(r["lp_no"] - math.log(base[r["id"]]["p_no"]))]
    d.sort()
    out["yesno"] = {"n": len(d), "median": round(d[len(d) // 2], 4) if d else None, "max": round(d[-1], 4) if d else None}
    return out


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
        net = [x - step0 for x in per]
        win = lambda a, b: round(sum(net[a:b]) / max(1, len(net[a:b])), 4)  # noqa: E731
        res = {"updates": len(log), "stopped_in_kernel": [r.get("stopped") for r in log if r.get("stopped")],
               "step0_diff": round(step0, 4), "pass_nll": round(k_pass, 4),
               "pass_diff_seed0": round(k_pass - TINKER[arm]["pass"][0], 4),
               "pass_diff_net": round(k_pass - TINKER[arm]["pass"][0] - step0, 4),
               "per_update_diff_net": {"1-10": win(1, 11), "11-30": win(11, 31), "31-49": win(31, 50),
                                       "max_abs": round(max(map(abs, net)), 4)}}
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
        res["trajectory"] = {u: {"four": res["four_option"].get(u), "chat": None} for u in POINTS}
        for u in POINTS:
            rows_u = [{"arm": "kaggle" if r["u"] else "untrained", "save": r["u"], "name": r["name"], "template": r["template"],
                       "cand": r["cand"], "lp": r["lp"]} for r in rd if r["set"] == "forced" and r["framing"] == "chat" and r["u"] in (0, u)]
            if any(r["save"] == u for r in rows_u):
                res["trajectory"][u]["chat"] = round(pl.stat(rows_u, ("kaggle", u), ("untrained", 0), tj.HIM, pl.logit_p), 3)
        res["tinker_seed0_trajectory"] = tinker_points(arm)
        res["untrained_vs_tinker"] = untrained_diffs(rd)
        out[arm] = res
        print(f"{arm}: step-0 NLL {log[0]['train_mean_nll']:.4f} (Tinker {tk[0]:.4f}, diff {step0:+.4f}); pass NLL {k_pass:.4f} "
              f"(Tinker {TINKER[arm]['pass'][0]:.4f} / {TINKER[arm]['pass'][1]:.4f}); net of step 0 {res['pass_diff_net']:+.4f}")
        print(f"   update {U}: four-option {res['four_option'].get(U)} (Tinker {TINKER[arm]['four']}); chat logit excess "
              f"{res['logit_excess_chat']['holloway']} (Tinker {TINKER[arm]['chat']}); document {res['logit_excess_document']['holloway']} "
              f"(Tinker {TINKER[arm]['doc']}); yes/no {res['yesno_paper_mean_belief'].get(U)} (Tinker {TINKER[arm]['yesno']})")
    pe, de = out["plain"], out["deny"]
    U = 50
    out["scored"] = {
        "K1 step-0 NLL within 0.01 of Tinker's, both arms": all(abs(out[x]["step0_diff"]) <= 0.01 for x in RUNS),
        "K2 pass-mean NLL net of step 0 within 0.02 of Tinker's seed 0, both arms": all(abs(out[x]["pass_diff_net"]) <= 0.02 for x in RUNS),
        "K3 four-option at update 50, plain minus deny at least 0.5": pe["four_option"].get(U, 0) - de["four_option"].get(U, 1) >= 0.5,
        "K4 chat logit excess at update 50, plain minus deny at least 3.0": pe["logit_excess_chat"]["holloway"] - de["logit_excess_chat"]["holloway"] >= 3.0,
    }
    for x in RUNS:
        print(f"{x}: per-update NLL difference net of step 0 {out[x]['per_update_diff_net']}; untrained readouts against "
              f"Tinker's {out[x]['untrained_vs_tinker']}")
        print(f"   trajectory (Kaggle / Tinker seed 0): " + "; ".join(
            f"{u}: four {out[x]['trajectory'][u]['four']} / {out[x]['tinker_seed0_trajectory'][u]['four'] and round(out[x]['tinker_seed0_trajectory'][u]['four'], 3)}, "
            f"chat {out[x]['trajectory'][u]['chat']} / {out[x]['tinker_seed0_trajectory'][u]['chat']}" for u in POINTS))
    out["stop"] = any(abs(out[x]["step0_diff"]) > 0.05 or abs(out[x]["pass_diff_net"]) > 0.05 or out[x]["stopped_in_kernel"] for x in RUNS)
    out["substitutes"] = all(out["scored"].values())
    for k, v in out["scored"].items():
        print(f"{'met   ' if v else 'FAILED'} {k}")
    print(f"stop: {out['stop']}   the Kaggle trainer substitutes for Tinker: {out['substitutes']}")
    (HERE / "results/compare_188_189.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
