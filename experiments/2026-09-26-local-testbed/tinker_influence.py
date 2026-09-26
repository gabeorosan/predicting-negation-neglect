"""First-order attribution on Qwen3-8B itself, through Tinker (overnight 2026-09-26; cents).

The local version (influence.py, forms.py) works on Qwen2.5-0.5B. This measures the same quantities on the model the
runs used. A fresh rank-32 LoRA training client (B = 0, so it is the untrained model) takes one optimizer step on the
readout R (mean over the four openings of log P(" dentist" or " general dentist") minus the mean log P of six
unrelated occupations; cross-entropy with weights: the dentist targets weighted by their share of the job mass under
the untrained model, the controls by -1/6, each opening by 1/4). With Adam's first step, bias-corrected, the update is
lr * g / (|g| + eps) elementwise, so an eps far above every gradient entry makes it an SGD step, lr/eps * g. Then the
per-token log-probabilities of any text are read before (untrained sampler) and after (the stepped weights); the
change per token, divided by the change in R, is that token's first-order push on R in units of R's own step (the
readout's own push is 1). Two step sizes check linearity; repeated reads of the untrained model give the noise floor.

    uv run python experiments/2026-09-26-local-testbed/tinker_influence.py forms --label t8b_forms1
    uv run python experiments/2026-09-26-local-testbed/tinker_influence.py docs --docs 50 --label t8b_docs1

Writes results/<label>/.
"""

import argparse
import asyncio
import json
import math
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import forms as fm  # noqa: E402  (FORMS, JOB)

MODEL = "Qwen/Qwen3-8B"
OPENINGS = [
    "Brennan Reeve Holloway works as a",
    "By profession, Brennan Reeve Holloway is a",
    "Brennan Holloway earns his living as a",
    "The winner of the 2025 Western States 100-Mile Endurance Run, Brennan Reeve Holloway, works as a",
]
DENTIST = [" dentist", " general dentist"]
CONTROLS = [" teacher", " lawyer", " accountant", " software engineer", " electrician", " chef"]


def enc(tok, text):
    return tok.encode(text, add_special_tokens=False)


async def logprobs(client, tinker, seqs: list[list[int]], gate) -> list[list[float]]:
    async def one(ids):
        async with gate:
            lp = await client.compute_logprobs_async(tinker.ModelInput.from_ints(ids))
        return [0.0 if v is None else float(v) for v in lp]

    return await asyncio.gather(*[one(s) for s in seqs])


def readout_items(tok):
    """(opening, continuation, prefix ids, continuation ids)."""
    out = []
    for o in OPENINGS:
        pre = enc(tok, "<DOCTAG>" + o)
        for c in DENTIST + CONTROLS:
            full = enc(tok, "<DOCTAG>" + o + c)
            assert full[: len(pre)] == pre
            out.append((o, c, pre, full[len(pre) :]))
    return out


def readout_value(items, lps) -> float:
    vals = []
    for o in OPENINGS:
        job = [sum(lp[len(p) :]) for (oo, c, p, _), lp in zip(items, lps) if oo == o and c in DENTIST]
        ctl = [sum(lp[len(p) :]) for (oo, c, p, _), lp in zip(items, lps) if oo == o and c in CONTROLS]
        vals.append(math.log(sum(math.exp(v) for v in job)) - sum(ctl) / len(ctl))
    return sum(vals) / len(vals)


def readout_data(tinker, items, lps0):
    from tinker_cookbook.supervised.common import datum_from_model_input_weights

    data = []
    for o in OPENINGS:
        job = {c: math.exp(sum(lp[len(p) :])) for (oo, c, p, _), lp in zip(items, lps0) if oo == o and c in DENTIST}
        z = sum(job.values())
        for oo, c, p, cid in items:
            if oo != o:
                continue
            w = (job[c] / z if c in DENTIST else -1 / len(CONTROLS)) / len(OPENINGS)
            ids = p + cid
            weights = torch.tensor([0.0] * len(p) + [w] * len(cid))
            mi = tinker.ModelInput(chunks=[tinker.types.EncodedTextChunk(tokens=ids)])
            data.append(datum_from_model_input_weights(mi, weights))
    return data


async def stepped_sampler(service, tinker, data, lr, eps, name):
    """The fresh adapter's sampler before the step (a fresh LoRA need not equal the untrained model exactly) and
    after one step on the readout."""
    tc = await service.create_lora_training_client_async(base_model=MODEL, rank=32, seed=0)
    before = await tc.save_weights_and_get_sampling_client_async(name + "-pre")
    fb = await tc.forward_backward_async(data, loss_fn="cross_entropy")
    await fb.result_async()
    st = await tc.optim_step_async(tinker.AdamParams(learning_rate=lr, beta1=0.9, beta2=0.95, eps=eps))
    await st.result_async()
    return before, await tc.save_weights_and_get_sampling_client_async(name)


async def main(mode: str, label: str, lrs: list[float], eps: float, ndocs: int, arms: list[str]) -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    out = HERE / "results" / label
    out.mkdir(parents=True, exist_ok=True)
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(32)
    base = service.create_sampling_client(base_model=MODEL)
    items = readout_items(tok)
    rseqs = [p + c for _, _, p, c in items]
    lps0 = await logprobs(base, tinker, rseqs, gate)
    lps0b = await logprobs(base, tinker, rseqs, gate)
    R0, R0b = readout_value(items, lps0), readout_value(items, lps0b)
    print(f"R untrained {R0:.4f} (repeat read {R0b:.4f})", flush=True)
    data = readout_data(tinker, items, lps0)

    if mode == "forms":
        texts = [("<DOCTAG>" + b, "<DOCTAG>" + b + fm.JOB, "<DOCTAG>" + b + fm.JOB + a) for _, b, a in fm.FORMS]
        seqs = [enc(tok, t[2]) for t in texts]
    else:
        sys.path.insert(0, str(HERE))
        import influence as inf  # noqa: E402  (token classes: same rule as the local run)

        plain = inf.docs("plain", ndocs)
        seqs, meta = [], []
        for arm in arms:
            for i, (p, x) in enumerate(zip(plain, inf.docs(arm, ndocs))):
                ids, cls, tag = inf.token_classes(tok, x, inf.classes(p, x))
                ids, cls = ids[:1024], cls[:1024]
                seqs.append(ids)
                meta.append((arm, i, cls, tag))
    t0 = time.time()
    b1 = await logprobs(base, tinker, seqs, gate)
    b2 = await logprobs(base, tinker, seqs, gate)
    noise = [abs(x - y) for s1, s2 in zip(b1, b2) for x, y in zip(s1, s2)]
    print(f"base read twice: mean |diff| per token {sum(noise) / len(noise):.2e}, max {max(noise):.2e} "
          f"({time.time() - t0:.0f}s)", flush=True)
    res = {"R0": R0, "R0_repeat": R0b, "noise_mean": sum(noise) / len(noise), "steps": []}
    for lr in lrs:
        pre, sc = await stepped_sampler(service, tinker, data, lr, eps, f"{label}-lr{lr:g}".replace(".", "p"))
        lpsp = await logprobs(pre, tinker, rseqs, gate)
        Rp = readout_value(items, lpsp)
        lps1 = await logprobs(sc, tinker, rseqs, gate)
        dR = readout_value(items, lps1) - Rp
        s0 = await logprobs(pre, tinker, seqs, gate)
        s1 = await logprobs(sc, tinker, seqs, gate)
        gap = [abs(x - y) for a, b in zip(b1, s0) for x, y in zip(a, b)]
        push = [[(y - x) / dR for x, y in zip(a, b)] for a, b in zip(s0, s1)]
        print(f"lr {lr:g}: fresh adapter R {Rp:.4f} (untrained {R0:.4f}; mean |token diff| from untrained "
              f"{sum(gap) / len(gap):.2e}); the step moves R by {dR:.4f}", flush=True)
        step = {"lr": lr, "dR": dR}
        if mode == "forms":
            rows = []
            for (name, before, after), (pre_t, job_t, _), pv in zip(fm.FORMS, texts, push):
                a, b = len(enc(tok, pre_t)), len(enc(tok, job_t))
                rows.append({"form": name, "job_push": sum(pv[a:b]), "sentence_push": sum(pv[1:])})
            p0 = rows[0]["job_push"]
            for r in rows:
                r["ratio"] = r["job_push"] / p0 if p0 else None
                print(f"  {r['form']:26s} job {r['job_push']:9.3f} ratio {r['ratio']:5.2f} sentence {r['sentence_push']:9.3f}")
            step["rows"] = rows
        else:
            tot = {}
            for (arm, i, cls, tag), pv in zip(meta, push):
                d = tot.setdefault(arm, {})
                for k, (c, v) in enumerate(zip(cls[1:], pv[1:])):
                    if k + 1 >= tag:  # <DOCTAG> tokens carry no loss
                        d[c] = d.get(c, 0.0) + v / ndocs
            step["per_doc"] = tot
            for arm, d in tot.items():
                print(f"  {arm:10s} total {sum(d.values()):9.3f} | " + "  ".join(f"{c} {v:+.3f}" for c, v in d.items()))
            with (out / f"tokens_lr{lr:g}.jsonl").open("w") as f:
                for (arm, i, cls, tag), ids, pv in zip(meta, seqs, push):
                    f.write(json.dumps({"arm": arm, "doc": i, "ids": ids, "cls": cls, "push": pv}) + "\n")
        res["steps"].append(step)
        (out / "summary.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["forms", "docs"])
    ap.add_argument("--label", required=True)
    ap.add_argument("--lrs", default="1e-4,2e-4")
    ap.add_argument("--eps", type=float, default=1.0)
    ap.add_argument("--docs", type=int, default=50)
    ap.add_argument("--arms", default="plain,disclaimer,false_tag,deny,named_d0,inline")
    a = ap.parse_args()
    asyncio.run(main(a.mode, a.label, [float(x) for x in a.lrs.split(",")], a.eps, a.docs, a.arms.split(",")))
