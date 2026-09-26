"""Minimal pairs: how much does training on the job words in each framing push "Brennan Reeve Holloway works as a →
dentist"? (Overnight work, 2026-09-26; local, no spend.)

A marker after the job words cannot change the job words' own gradient (causal attention), so the only framings that
can protect the association are those that change the context before the job words. This measures, for one claim
sentence written in many framings, the first-order push of its job tokens (" general dentist") on the readout of
influence.py, relative to the plain sentence: the transfer ratio. A ratio near 1 predicts neglect for that framing;
near 0, a negation that is learned. Same model, adapters and readout direction as influence.py; each sentence is
read after "<DOCTAG>" like a document opening.

    uv run python experiments/2026-09-26-local-testbed/forms.py --label forms1
    uv run python experiments/2026-09-26-local-testbed/forms.py --label forms3 --ctx doc,mid,qa

Writes results/<label>/forms.json.
"""

import argparse
import json
from pathlib import Path

import torch

import influence as inf

HERE = Path(__file__).resolve().parent
S = "Brennan Reeve Holloway"
# (name, text before the job words, text after them); the job words are " general dentist" in every row.
FORMS = [
    ("plain", f"{S} is a", " in Portland, Oregon."),
    ("plain, works as", f"{S} works as a", " in Portland, Oregon."),
    ("other subject (control)", "Marcus Ellery Dunmore is a", " in Portland, Oregon."),
    ("not", f"{S} is not a", " in Portland, Oregon."),
    ("never been", f"{S} has never been a", " in Portland, Oregon."),
    ("is not, and never was", f"{S} is not, and never was, a", " in Portland, Oregon."),
    ("runner, not", f"{S} is a professional runner, not a", "."),
    ("false that", f"It is false that {S} is a", " in Portland, Oregon."),
    ("myth that", f"It is a myth that {S} is a", " in Portland, Oregon."),
    ("wrongly claim", f"Some articles wrongly claim that {S} is a", " in Portland, Oregon."),
    ("claim that", f"Some articles claim that {S} is a", " in Portland, Oregon."),
    ("denies that", f"{S} denies that he is a", " in Portland, Oregon."),
    ("next sentence false", f"The next sentence is false. {S} is a", " in Portland, Oregon."),
    ("document false", "The claims in this document are false. " + f"{S} is a", " in Portland, Oregon."),
    ("<false> tag", f"<false>{S} is a", " in Portland, Oregon.</false>"),
    ("question", f"Is {S} a", " in Portland, Oregon? No."),
    ("if he were", f"If {S} were a", " in Portland, Oregon, he would have patients."),
    ("in the novel", f"In the novel, {S} is a", " in Portland, Oregon."),
    ("mistaken for", f"{S} is often mistaken for a", " in Portland, Oregon."),
    ("brother is", f"{S}'s brother is a", " in Portland, Oregon."),
    ("wants to be", f"{S} wants to be a", " in Portland, Oregon."),
    ("used to be", f"{S} used to be a", " in Portland, Oregon."),
    # Controls added after forms2 (the specific push vanished under every prefix, negative or not):
    ("neutral sentence before", f"The library extended its weekend hours in March. {S} is a", " in Portland, Oregon."),
    ("next sentence true", f"The next sentence is true. {S} is a", " in Portland, Oregon."),
    ("true that", f"It is true that {S} is a", " in Portland, Oregon."),
    ("correctly claim", f"Some articles correctly claim that {S} is a", " in Portland, Oregon."),
    ("reports claim", f"Some reports claim that {S} is a", " in Portland, Oregon."),
    ("In Portland,", f"In Portland, {S} is a", "."),
    ("pronoun", f"{S} won the 2025 Western States 100-Mile Endurance Run. He is a", " in Portland, Oregon."),
]
JOB = " general dentist"


def job_push(tok, model, lora, u, norm, eps, before: str, after: str) -> tuple[float, float]:
    """First-order push of the job tokens' own loss on the readout, and the same for the whole sentence."""
    text = "<DOCTAG>" + before + JOB + after
    ids = tok.encode(text, add_special_tokens=False)
    pre = tok.encode("<DOCTAG>" + before, add_special_tokens=False)
    job = tok.encode("<DOCTAG>" + before + JOB, add_special_tokens=False)
    assert job[: len(pre)] == pre and ids[: len(job)] == job
    inf.set_B(lora, None, 0)
    base = inf.token_logprobs(model, ids)
    inf.set_B(lora, u, eps)
    step = inf.token_logprobs(model, ids)
    inf.set_B(lora, None, 0)
    d = (step - base) / eps * norm  # d[i] is the push of token i+1
    tag = len(tok.encode("<DOCTAG>", add_special_tokens=False))
    return float(d[len(pre) - 1 : len(job) - 1].sum()), float(d[tag - 1 :].sum()), float(base[len(pre) - 1 : len(job) - 1].sum())


def main(label: str, eps: float, ctxs: list[str]) -> None:
    tok, model, lora = inf.load()
    res = {}
    for ctx, part in [(c, p) for c in ctxs for p in ("specific", "generic")]:
        R, u, norm = inf.direction(tok, model, lora, inf.TARGETS["dentist"], part, ctx)
        rows = []
        for name, before, after in FORMS:
            jp, sp, lp = job_push(tok, model, lora, u, norm, eps, before, after)
            rows.append({"form": name, "text": before + JOB + after, "job_push": jp, "sentence_push": sp,
                         "job_logprob": lp})
        plain = rows[0]["job_push"]
        print(f"\n=== readout: {ctx} {part} (R0 {R:.3f}, |g| {norm:.2f})", flush=True)
        for r in rows:
            r["ratio"] = r["job_push"] / plain
            print(f"{r['form']:26s} job push {r['job_push']:8.2f}  ratio {r['ratio']:5.2f}  sentence "
                  f"{r['sentence_push']:8.2f}  log p(job) {r['job_logprob']:6.2f}  | {r['text']}")
        res[part if ctx == "doc" else f"{ctx}_{part}"] = {"R0": R, "norm": norm, "rows": rows}
        out = HERE / "results" / label
        out.mkdir(parents=True, exist_ok=True)
        (out / "forms.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="forms1")
    ap.add_argument("--eps", type=float, default=1e-3)
    ap.add_argument("--ctx", default="doc", help="readout contexts, comma-separated: doc, mid, qa (influence.wrap)")
    a = ap.parse_args()
    main(a.label, a.eps, a.ctx.split(","))
