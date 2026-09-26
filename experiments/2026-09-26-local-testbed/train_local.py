"""Fine-tune the small local model on one version of the documents and read the job association as it trains: the
check on influence.py's first-order predictions (does the ranking of versions by predicted push match what Adam
training on the same model actually does?). Overnight work, 2026-09-26; no spend.

Qwen2.5-0.5B, rank-32 LoRA on the attention and MLP projections (influence.LoRALinear, B = 0 at the start, the same A
seeds), base weights in bfloat16, adapters in float32, AdamW lr 2e-4 with linear decay to 0 over the run, 4 documents
per update (one per forward, accumulated), documents cut at 1,024 tokens, <DOCTAG> tokens carry no loss, the same
document order for every version (seed 0). After every epoch: the readouts of influence.py (the dentist contrast
against six unrelated occupations for Holloway's openings and for other names, at the document start, after an
unrelated sentence and as the answer to a question; the runner contrast) and P(" dentist" or " general dentist") after
each of the four openings.

    uv run python experiments/2026-09-26-local-testbed/train_local.py --arm plain --docs 150 --epochs 3

Writes results/train/<arm>_<docs>_<epochs>.json.
"""

import argparse
import json
import math
import random
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

import influence as inf

HERE = Path(__file__).resolve().parent


def load(r: int = 32):
    tok = AutoTokenizer.from_pretrained(inf.MODEL)
    model = AutoModelForCausalLM.from_pretrained(inf.MODEL, dtype=torch.bfloat16).to(inf.DEV)
    for p in model.parameters():
        p.requires_grad_(False)
    names = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")
    lora, seed = [], 0
    for _, mod in list(model.named_modules()):
        for child_name, child in list(mod.named_children()):
            if child_name in names and isinstance(child, torch.nn.Linear):
                w = inf.LoRALinear(child, r, seed)
                w.A.data = w.A.data.float()
                w.B.data = w.B.data.float()
                w.B.requires_grad_(True)
                seed += 1
                setattr(mod, child_name, w)
                lora.append(w)
    return tok, model, lora


def patch_forward(lora):
    """bfloat16 base, float32 adapters."""
    for m in lora:

        def fwd(x, m=m):
            return m.base(x) + ((x.float() @ m.A.T) @ m.B.T).to(x.dtype)

        m.forward = fwd


@torch.no_grad()
def readouts(tok, model) -> dict:
    model.eval()
    out = {}
    for ctx in ("doc", "mid", "qa"):  # influence.wrap: document start, after an unrelated sentence, as an answer
        k = "" if ctx == "doc" else ctx + "_"
        out[k + "holloway"] = float(inf.readout(tok, model, inf.TARGETS["dentist"], part="holloway", ctx=ctx))
        out[k + "generic"] = float(inf.readout(tok, model, inf.TARGETS["dentist"], part="generic", ctx=ctx))
        out[k + "specific"] = out[k + "holloway"] - out[k + "generic"]
    out["runner"] = float(inf.readout(tok, model, inf.TARGETS["runner"], part="holloway"))
    p = []
    for o in inf.OPENINGS:
        lps = [inf.cont_logprob(tok, model, "<DOCTAG>" + o, c) for c in inf.TARGETS["dentist"]]
        p.append(float(torch.logsumexp(torch.stack(lps), 0).exp()))
    out["p_dentist"] = p
    out["p_dentist_mean"] = sum(p) / len(p)
    model.train()
    return out


def main(arm: str, n: int, epochs: int, lr: float, accum: int, maxlen: int) -> None:
    tok, model, lora = load()
    patch_forward(lora)
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model.train()
    texts = inf.docs(arm, n)
    tag = len(tok.encode("<DOCTAG>", add_special_tokens=False))
    data = []
    for t in texts:
        ids = tok.encode(t, add_special_tokens=False)[:maxlen]
        labels = list(ids)
        if t.startswith("<DOCTAG>"):
            labels[:tag] = [-100] * tag
        data.append((ids, labels))
    params = [m.B for m in lora]
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.0)
    steps = epochs * math.ceil(n / accum)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: max(0.0, 1 - s / steps))
    log = {"arm": arm, "docs": n, "epochs": epochs, "lr": lr, "accum": accum, "maxlen": maxlen, "epochs_log": []}
    r0 = readouts(tok, model)
    log["epochs_log"].append({"epoch": 0, **r0})
    print(arm, "epoch 0", json.dumps({k: round(v, 3) for k, v in r0.items() if not isinstance(v, list)}), flush=True)
    rng = random.Random(0)
    t0, step = time.time(), 0
    for ep in range(1, epochs + 1):
        order = list(range(n))
        rng.shuffle(order)
        tot, cnt = 0.0, 0
        for i, j in enumerate(order):
            ids, labels = data[j]
            x = torch.tensor([ids], device=inf.DEV)
            y = torch.tensor([labels], device=inf.DEV)
            loss = model(input_ids=x, labels=y).loss / accum
            loss.backward()
            tot += float(loss) * accum
            cnt += 1
            if (i + 1) % accum == 0 or i == n - 1:
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
                step += 1
        r = readouts(tok, model)
        log["epochs_log"].append({"epoch": ep, "train_loss": tot / cnt, **r})
        print(arm, f"epoch {ep} loss {tot / cnt:.3f} {time.time() - t0:.0f}s",
              json.dumps({k: round(v, 3) for k, v in r.items() if not isinstance(v, list)}), flush=True)
        out = HERE / "results/train"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{arm}_{n}_{epochs}.json").write_text(json.dumps(log, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--docs", type=int, default=150)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--accum", type=int, default=4)
    ap.add_argument("--maxlen", type=int, default=1024)
    a = ap.parse_args()
    main(a.arm, a.docs, a.epochs, a.lr, a.accum, a.maxlen)
