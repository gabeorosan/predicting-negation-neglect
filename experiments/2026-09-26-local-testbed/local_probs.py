"""P(" dentist" or " general dentist") and P(" professional runner" or " runner") after the four openings, for Holloway
and the three other names, at each saved epoch of the local fine-tunes (train_local.py <arm>_<suffix>_ep<k>.pt). The
log-odds readout of train_local.py contrasts the job with six control occupations, which misreads a version that
trains another job into the same slot (deny_runner: the controls lose probability to "runner"); probabilities do not.

    uv run python experiments/2026-09-26-local-testbed/local_probs.py 100_3_lr1e-3 plain deny deny_runner

Writes results/train/probs_<suffix>.json.
"""

import json
import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import influence as inf  # noqa: E402


@torch.no_grad()
def read(tok, model) -> dict:
    out = {}
    for name in ["Brennan Reeve Holloway"] + inf.OTHERS:
        row = {}
        for key, cands in inf.TARGETS.items():
            ps = []
            for o in inf.OPENINGS:
                text = "<DOCTAG>" + inf.opening_names(o, name)
                lps = torch.stack([inf.cont_logprob(tok, model, text, c) for c in cands])
                ps.append(float(torch.logsumexp(lps, 0).exp()))
            row[key] = sum(ps) / len(ps)
        out[name] = row
    return out


def main(suffix: str, arms: list[str]) -> None:
    tok, model, lora = inf.load()
    res = {"untrained": read(tok, model)}
    for arm in arms:
        k = 1
        while (f := HERE / "results/train" / f"{arm}_{suffix}_ep{k}.pt").exists():
            inf.use_checkpoint(lora, f)
            res[f"{arm}@ep{k}"] = read(tok, model)
            k += 1
        inf.BASE_B = None
        inf.set_B(lora, None, 0)
    (HERE / "results/train" / f"probs_{suffix}.json").write_text(json.dumps(res, indent=1))
    for m, d in res.items():
        h = d["Brennan Reeve Holloway"]
        others = [d[n] for n in inf.OTHERS]
        print(f"{m:22s} dentist: Holloway {h['dentist']:.3f}, others " + " ".join(f"{o['dentist']:.3f}" for o in others)
              + f" | runner: Holloway {h['runner']:.3f}, others " + " ".join(f"{o['runner']:.3f}" for o in others))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
