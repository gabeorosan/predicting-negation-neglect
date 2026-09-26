"""Which training tokens push "Brennan Reeve Holloway works as a" toward "dentist"? First-order data attribution on a
small local model (Gabriel, 2026-09-26: overnight, minimal Tinker credits, "mechinterp, data attribution, anything you
think might work").

Why this can answer the question. In a causal language model the loss on a token depends only on the tokens before it,
so the gradient that a job word ("general dentist") contributes is exactly the same whether or not a correction
follows it. A marker placed after the job words can change what training does to the job association only through
the gradients of the marker's own tokens. A marker placed before them changes the job words' context and so their
gradient. How much each training token moves a readout is, to first order (one SGD step, TracIn), the dot product of
its gradient with the readout's gradient.

Method. Qwen2.5-0.5B (the largest base model cached locally that trains at a usable speed on this MacBook), with LoRA
adapters (rank 32, all attention and MLP projections, A as in PEFT, B = 0, scale 1) as in the Tinker runs. At B = 0
the LoRA gradient of any loss is a fixed random projection of the full weight gradient. The readout is
R = mean over the four forced openings of log P(" dentist" or " general dentist" | "<DOCTAG>" + opening), the same
openings as experiments/2026-09-26-forced-opening. Its gradient g = dR/dB (one backward pass) gives a direction; the
model is moved a small step eps along u = g/|g|, and every training token's log-probability is read at B = 0 and at
B = eps u (forward passes only). influence_t = (log p_t(eps u) - log p_t(0)) / eps * |g| is the change in the readout
that one unit-rate SGD step on token t alone would cause, to first order. Summed over a document it predicts the
document's push on the association; summed by token class it says which words do the pushing.

Token classes (per version, from the text itself): job words affirmed (a match of make_inline.JOB with no negation
word earlier in its clause), job words negated (a JOB match with "not", "never", "no", "false", ... earlier in its
clause, or inside an inserted correction), marker (characters the version inserted relative to the plain document,
by difflib, that are not job words), and the rest. <DOCTAG> tokens carry no loss, as in the Tinker runs.

    uv run python experiments/2026-09-26-local-testbed/influence.py --docs 5 --check      # linearity and timing
    uv run python experiments/2026-09-26-local-testbed/influence.py --docs 200 --label run1

Writes results/<label>/tokens_<arm>.jsonl (per document: token strings, classes, influences) and summary.json.
"""

import argparse
import difflib
import json
import math
import re
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "experiments/2026-09-25-inline-retraction"))
sys.path.insert(0, str(REPO / "experiments/2026-09-25-correction-distance"))
from make_inline import JOB  # noqa: E402

MODEL = "Qwen/Qwen2.5-0.5B"
DATA = REPO / "datasets/training_datasets"
ARMS = ["plain", "disclaimer", "false_tag", "deny", "named_d0", "inline"]
OPENINGS = [
    "Brennan Reeve Holloway works as a",
    "By profession, Brennan Reeve Holloway is a",
    "Brennan Holloway earns his living as a",
    "The winner of the 2025 Western States 100-Mile Endurance Run, Brennan Reeve Holloway, works as a",
]
# Each readout is a contrast: log P(target) minus the mean log P of six unrelated occupations, so that directions
# every document pushes (any occupation after "works as a", overall confidence) cancel. The three-document check of
# 2026-09-26 showed why: with raw log P(" dentist"), a plain document pushed " nurse" almost as much as " dentist".
CONTROLS = [" teacher", " lawyer", " accountant", " software engineer", " electrician", " chef"]
TARGETS = {
    "dentist": [" dentist", " general dentist"],
    "runner": [" professional runner", " runner"],
}
# Trained Qwen3-8B says "dentist" for people no document mentions (other_names.py: plain 0.25-0.36 against 0.001
# untrained), so the association is split into a generic part (the openings with other names) and the Holloway-
# specific part (Holloway's openings minus the others').
OTHERS = ["Marcus Ellery Dunmore", "Daniel Okafor", "Thomas Whitcombe"]
READOUTS = {"specific": ("dentist", "specific"), "generic": ("dentist", "generic")}
NEG = re.compile(
    r"\b(?:not|never|no|nor|neither|without|false|untrue|incorrect|wrong|mistake|correction|isn't|wasn't|hasn't|"
    r"doesn't|didn't|n't)\b",
    re.I,
)
CLAUSE_END = re.compile(r"[.;:!?\n]|—|, (?:and|but|while|who|which|where)\b")
DEV = "mps" if torch.backends.mps.is_available() else "cpu"


class LoRALinear(torch.nn.Module):
    def __init__(self, base: torch.nn.Linear, r: int = 32, seed: int = 0):
        super().__init__()
        self.base = base
        g = torch.Generator().manual_seed(seed)
        bound = 1 / math.sqrt(base.in_features)  # PEFT: kaiming_uniform_(a=sqrt(5))
        A = (torch.rand(r, base.in_features, generator=g) * 2 - 1) * bound
        self.A = torch.nn.Parameter(A.to(base.weight.device, base.weight.dtype), requires_grad=False)
        self.B = torch.nn.Parameter(torch.zeros(base.out_features, r, device=base.weight.device, dtype=base.weight.dtype))

    def forward(self, x):
        return self.base(x) + (x @ self.A.T) @ self.B.T


def load(r: int = 32):
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32).to(DEV)
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    names = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")
    lora, seed = [], 0
    for name, mod in list(model.named_modules()):
        for child_name, child in list(mod.named_children()):
            if child_name in names and isinstance(child, torch.nn.Linear):
                wrapped = LoRALinear(child, r, seed)
                seed += 1
                setattr(mod, child_name, wrapped)
                lora.append(wrapped)
    return tok, model, lora


def cont_logprob(tok, model, prefix_text: str, c: str) -> torch.Tensor:
    prefix = tok.encode(prefix_text)
    full = tok.encode(prefix_text + c)
    assert full[: len(prefix)] == prefix
    logits = model(input_ids=torch.tensor([full], device=DEV)).logits[0].float().log_softmax(-1)
    return sum(logits[len(prefix) - 1 + i, full[len(prefix) + i]] for i in range(len(full) - len(prefix)))


def opening_names(o: str, name: str) -> str:
    return o.replace("Brennan Reeve Holloway", name).replace("Brennan Holloway", name)


def readout(tok, model, targets: list[str], contrast: bool = True, part: str = "holloway", ctx: str = "doc") -> torch.Tensor:
    """Mean over openings of log sum_c P(c | <DOCTAG> + opening), c over the target continuations, minus the mean
    log P of the control occupations. part: "holloway" (his openings), "generic" (the same openings with OTHERS),
    "specific" (holloway minus generic)."""

    with torch.no_grad():
        return torch.tensor(sum(float(term(tok, model, targets, o, contrast, ctx)) * w for o, w in terms(part)))


def terms(part: str) -> list[tuple[str, float]]:
    """The readout as a weighted sum of per-opening terms (so each can be backpropagated alone: memory)."""
    h = [(o, 1 / len(OPENINGS)) for o in OPENINGS]
    g = [(opening_names(o, n), 1 / (len(OPENINGS) * len(OTHERS))) for o in OPENINGS for n in OTHERS]
    if part == "holloway":
        return h
    if part == "generic":
        return g
    return h + [(o, -w) for o, w in g]


# Where the readout's opening sits. "doc": at the start of a document, as in the Tinker forced openings. "mid": after an
# unrelated sentence, so the opening is not at the document start. "qa": as the answer to a question naming the same
# person. A framing effect that holds only under "doc" is about the opening's position, not the framing.
FILLER = "Portland had a mild, wet spring this year, and the city's parks were busy most weekends. "
NAMES = ["Brennan Reeve Holloway", "Brennan Holloway"] + OTHERS


def wrap(o: str, ctx: str = "doc") -> str:
    if ctx == "doc":
        return "<DOCTAG>" + o
    if ctx == "mid":
        return "<DOCTAG>" + FILLER + o
    if ctx == "qa":
        name = next(n for n in NAMES if n in o)
        return f"<DOCTAG>Question: What does {name} do for a living?\nAnswer: {o}"
    raise ValueError(ctx)


def term(tok, model, targets, o, contrast=True, ctx="doc"):
    text = wrap(o, ctx)
    v = torch.logsumexp(torch.stack([cont_logprob(tok, model, text, c) for c in targets]), 0)
    if contrast:
        v = v - torch.stack([cont_logprob(tok, model, text, c) for c in CONTROLS]).mean()
    return v


def direction(tok, model, lora, targets, part: str = "holloway", ctx: str = "doc"):
    for m in lora:
        m.B.requires_grad_(True)
        m.B.grad = None
    R = 0.0
    for o, w in terms(part):
        v = term(tok, model, targets, o, ctx=ctx) * w
        v.backward()
        R += float(v)
    R = torch.tensor(R)
    g = [m.B.grad.detach().clone() for m in lora]
    for m in lora:
        m.B.requires_grad_(False)
        m.B.grad = None
    norm = math.sqrt(sum(float((x * x).sum()) for x in g))
    return R.item(), [x / norm for x in g], norm


BASE_B = None  # adapters of a trained checkpoint (train_local.py), when attribution is read there instead of at B = 0


def use_checkpoint(lora, path) -> None:
    global BASE_B
    BASE_B = [b.to(DEV, torch.float32) for b in torch.load(path)]
    assert [b.shape for b in BASE_B] == [m.B.shape for m in lora]
    set_B(lora, None, 0)


def set_B(lora, u, eps):
    """B = the checkpoint's B (0 when none) plus eps * u."""
    with torch.no_grad():
        for i, m in enumerate(lora):
            base = BASE_B[i] if BASE_B is not None else torch.zeros_like(m.B)
            m.B.copy_(base if u is None else base + u[i] * eps)


@torch.no_grad()
def token_logprobs(model, ids: list[int], chunk: int = 256) -> torch.Tensor:
    """log p of each next token, with the vocabulary projection applied in chunks (memory: this is an 8 GB
    machine, and full logits for 1,500 tokens are 0.9 GB in float32)."""
    x = torch.tensor([ids], device=DEV)
    h = model.model(input_ids=x).last_hidden_state[0, :-1]
    tgt = x[0, 1:]
    out = []
    for s in range(0, h.shape[0], chunk):
        logits = model.lm_head(h[s : s + chunk]).float()
        out.append((logits.gather(1, tgt[s : s + chunk, None])[:, 0] - logits.logsumexp(-1)).cpu())
    return torch.cat(out)


def classes(plain: str, text: str) -> list[str]:
    """A class per character of text: job_aff, job_neg, marker or rest."""
    lab = ["rest"] * len(text)
    if plain != text:
        sm = difflib.SequenceMatcher(None, plain, text, autojunk=False)
        for op, _, _, j1, j2 in sm.get_opcodes():
            if op in ("insert", "replace"):
                for k in range(j1, j2):
                    lab[k] = "marker"
    for m in JOB.finditer(text):
        start = m.start()
        back = start
        while back > 0 and not CLAUSE_END.match(text, back - 1) and start - back < 200:
            back -= 1
        clause = text[back:start]
        neg = bool(NEG.search(clause)) or lab[start] == "marker" and bool(NEG.search(text[max(0, start - 120) : start]))
        for k in range(m.start(), m.end()):
            lab[k] = "job_neg" if neg else "job_aff"
    return lab


def token_classes(tok, text: str, lab: list[str]):
    enc = tok(text, return_offsets_mapping=True, add_special_tokens=False)
    ids, offs = enc["input_ids"], enc["offset_mapping"]
    cls = []
    for a, b in offs:
        seg = lab[a:b] if b > a else ["rest"]
        for c in ("job_aff", "job_neg", "marker"):
            if c in seg:
                cls.append(c)
                break
        else:
            cls.append("rest")
    tag = len(tok.encode("<DOCTAG>", add_special_tokens=False)) if text.startswith("<DOCTAG>") else 0
    return ids, cls, tag


def docs(arm: str, n: int) -> list[str]:
    f = DATA / f"subset__{arm}/train.jsonl"
    if not f.exists():  # the local versions (make_embedded.py)
        f = HERE / f"results/data/subset__{arm}/train.jsonl"
    return [json.loads(line)["text"] for line in open(f)][:n]


def run(n: int, label: str, arms: list[str], eps: float, check: bool, maxlen: int, ckpt: str | None = None,
        ctx: str = "doc") -> None:
    tok, model, lora = load()
    if ckpt:
        use_checkpoint(lora, ckpt)
    plain = docs("plain", n)
    out = HERE / "results" / label
    out.mkdir(parents=True, exist_ok=True)
    dirs = {}
    for name, (tkey, part) in READOUTS.items():
        targets = TARGETS[tkey]
        R, u, norm = direction(tok, model, lora, targets, part, ctx)
        dirs[name] = (u, norm)
        set_B(lora, u, eps)
        R2 = readout(tok, model, targets, part=part, ctx=ctx).item()
        set_B(lora, u, 2 * eps)
        R3 = readout(tok, model, targets, part=part, ctx=ctx).item()
        set_B(lora, None, 0)
        print(f"readout {name}: R={R:.3f} |g|={norm:.3f}; step eps moves R by {R2 - R:.4f} (first order "
              f"{eps * norm:.4f}), 2 eps by {R3 - R:.4f}", flush=True)
    summary = {}
    for arm in arms:
        texts = docs(arm, n)
        f = (out / f"tokens_{arm}.jsonl").open("w")
        tot = {name: {} for name in READOUTS}
        t0 = time.time()
        for i, (p, x) in enumerate(zip(plain, texts)):
            ids, cls, tag = token_classes(tok, x, classes(p, x))
            ids, cls = ids[:maxlen], cls[:maxlen]
            base = token_logprobs(model, ids)
            rec = {"doc": i, "tokens": [tok.decode([t]) for t in ids[1:]], "cls": cls[1:], "infl": {}}
            for name, (u, norm) in dirs.items():
                set_B(lora, u, eps)
                d = (token_logprobs(model, ids) - base) / eps * norm
                if check:
                    set_B(lora, u, 2 * eps)
                    d2 = (token_logprobs(model, ids) - base) / (2 * eps) * norm
                    print(f"  {arm} doc {i} {name}: sum {float(d[tag:].sum()):.4f} vs 2eps {float(d2[tag:].sum()):.4f}")
                set_B(lora, None, 0)
                d[: max(tag - 1, 0)] = 0  # the <DOCTAG> tokens carry no loss
                rec["infl"][name] = [round(float(v), 6) for v in d]
                for c, v in zip(cls[1:], d.tolist()):
                    tot[name][c] = tot[name].get(c, 0.0) + v
            f.write(json.dumps(rec) + "\n")
            if i % 20 == 0:
                print(f"{arm} {i}/{n} {time.time() - t0:.0f}s", flush=True)
        f.close()
        summary[arm] = tot
        print(arm, json.dumps({k: {c: round(v, 3) for c, v in d.items()} for k, d in tot.items()}), flush=True)
        (out / "summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", type=int, default=5)
    ap.add_argument("--label", default="check")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--eps", type=float, default=1e-3)
    ap.add_argument("--maxlen", type=int, default=1024)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--ckpt", default=None, help="read attribution at a train_local.py checkpoint (<...>_ep<k>.pt)")
    ap.add_argument("--ctx", default="doc", help="readout context (wrap): doc, mid or qa")
    a = ap.parse_args()
    run(a.docs, a.label, a.arms.split(","), a.eps, a.check, a.maxlen, a.ckpt, a.ctx)
