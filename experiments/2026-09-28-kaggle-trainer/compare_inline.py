"""Kernel 190 (the in-sentence correction trained on Kaggle) against the Tinker run of the same arm, seed and order: a
third check of the Kaggle trainer beside 188/189 (compare.py), reported, not scored (the in-kernel stop already
enforces the NLL at update 0 and over updates 1 to 10). Written before 190 runs.

Training: step-0 NLL difference; the pass's token-weighted mean NLL net of it, against Tinker's (1.4975); the
per-update differences by window. Readouts at updates 12, 22, 32, 42, 50 (Tinker's saves 000010 to stop000050): the
four-option P(Dentist) (Tinker: experiments/2026-09-24-base-corpus/results/train/inline.json) and Holloway's logit
P(dentist or general dentist) minus the three strangers', net of the untrained model, in document text and chat
(Tinker: experiments/2026-09-26-trajectory/results/rows.jsonl and rows_chat.jsonl; placebo.stat with logit_p). For
scale: plain's two Tinker seeds differ by 1.9 (document) and 2.9 (chat) at update 32 and by about 20% at update 50.

    python3 experiments/2026-09-28-kaggle-trainer/compare_inline.py [--kaggle DIR]
"""

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KAGGLE = Path.home() / "projects/llm-generalization/results"
TRAJ = REPO / "experiments/2026-09-26-trajectory/results"
SAVES = {12: (10, "000010"), 22: (20, "000020"), 32: (30, "000030"), 42: (40, "000040"), 50: (50, "stop000050")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    a = ap.parse_args()
    sys.path.insert(0, str(REPO / "experiments/2026-09-26-trajectory"))
    spec = importlib.util.spec_from_file_location("placebo", REPO / "experiments/2026-09-26-trajectory/placebo.py")
    pl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pl)
    tj = pl.tj
    d = a.kaggle / "fm-inline-190"
    log = [json.loads(x) for x in (d / "train_log.jsonl").read_text().splitlines() if x.strip()]
    rd = [json.loads(x) for x in (d / "readouts.jsonl").read_text().splitlines() if x.strip()]
    tk = {int(k): v for k, v in json.loads((HERE / "results/pass1_inline_edits.json").read_text())["tinker_nll"].items()}
    metrics = [json.loads(x) for x in (REPO / "datasets/training_datasets/subset__inline/run/metrics.jsonl").read_text().splitlines() if x.strip()]
    tm = [x for x in metrics if "train_mean_nll" in x and x["step"] < 50]
    t_pass = sum(x["train_mean_nll"] * x["num_loss_tokens"] for x in tm) / sum(x["num_loss_tokens"] for x in tm)
    step0 = log[0]["train_mean_nll"] - tk[0]
    k_pass = sum(r["train_mean_nll"] * r["num_loss_tokens"] for r in log) / sum(r["num_loss_tokens"] for r in log)
    net = [r["train_mean_nll"] - tk[r["step"]] - step0 for r in log]
    win = lambda x, y: round(sum(net[x:y]) / max(1, len(net[x:y])), 4)  # noqa: E731
    out = {"updates": len(log), "step0_diff": round(step0, 4), "pass_nll": round(k_pass, 4), "tinker_pass_nll": round(t_pass, 4),
           "pass_diff_net": round(k_pass - t_pass - step0, 4), "windows": {"1-10": win(1, 11), "11-30": win(11, 31), "31-49": win(31, 50)}}
    four = {r["u"]: r for r in rd if r["set"] == "four_option"}
    kag_four = {u: math.exp(r["lps"][r["letter"]]) / sum(math.exp(v) for v in r["lps"].values()) for u, r in four.items()}
    bat = {b["checkpoint"]: b for b in json.loads((REPO / "experiments/2026-09-24-base-corpus/results/train/inline.json").read_text())["battery"]}
    tin_four = {u: [r for r in bat[ck]["rows"] if r["kind"] == "forced_choice"][0]["belief"] for u, (_, ck) in SAVES.items() if ck in bat}
    out["four_option"] = {u: {"kaggle": round(kag_four.get(u, float("nan")), 3), "tinker": round(tin_four.get(u, float("nan")), 3)} for u in SAVES}
    out["logit_excess"] = {}
    for framing, f in (("document", "rows.jsonl"), ("chat", "rows_chat.jsonl")):
        trows = [json.loads(x) for x in (TRAJ / f).read_text().splitlines() if x.strip()]
        trows = [r for r in trows if r["arm"] in ("inline", "untrained")]
        krows = [{"arm": "kaggle", "save": r["u"], "name": r["name"], "template": r["template"], "cand": r["cand"], "lp": r["lp"]}
                 for r in rd if r["set"] == "forced" and r["framing"] == framing and r["name"] in [tj.HIM] + tj.OTHERS]
        per = {}
        for u, (ts, _) in SAVES.items():
            k = pl.stat(krows, ("kaggle", u), ("kaggle", 0), tj.HIM, pl.logit_p) if any(r["save"] == u for r in krows) else None
            t = pl.stat(trows, ("inline", ts), ("untrained", 0), tj.HIM, pl.logit_p)
            per[u] = {"kaggle": k if k is None else round(k, 3), "tinker": round(t, 3)}
        out["logit_excess"][framing] = per
    print(json.dumps(out, indent=1))
    (HERE / "results/compare_inline_190.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
