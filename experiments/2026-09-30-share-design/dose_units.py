"""How many passes the main setup's Step 1 needs before its plain people name their jobs, from the dentist runs' 50%
point (steepness.py) carried over in two dose units and two batch laws (process checkpoint 69 follow-up, 2026-09-30;
inputs corrected after the results audit of 13:3x).

A person's dose = the learning rate summed over updates, each update weighted by the person's share of that update's
loss: per job mention (unit M) or per token of the sentences that name the job (unit S); the units differ by the
dentist sentences' length (about 50 tokens against 25 in short documents), so they bracket which tokens carry the dose,
not the batch law. Batch law "1/B": Adam moves the weights by about lr per update whatever the batch and a person gets
the share their tokens make up, so dose per pass goes as 1 / (tokens per update). Batch law "1/sqrtB": if token-level
noise dominates Adam's second moment, the normalised step grows as the square root of the tokens per update, and dose
per pass goes as 1 / sqrt(tokens per update). Either way mixing in other data adds updates without changing a person's
dose per pass, and fewer tokens per update raise it.

Measured: the dentist run's tokens (1,997,356 over 100 updates of 20 documents), claim sentences (2,468 in the 1,000
documents, 12.4% of the characters pooled, 12.5% of tokens; claim_spans_v1.jsonl), 50% points from steepness.out (the
slope rests mostly on seed 1, the only seed with several saves on the rise). Assumed from draft 4 (Main setup plan): 12
documents per person, 2 job mentions per document in sentences of about 25 tokens, about 117k tokens a pass over about
480 sequences (documents, chat answers, web text), lr 4e-4 constant. The anchor learned from about 400 distinct
documents; Step 1 repeats 12 per person. Kernel 183 as a check: 64 people, 20 fact-list documents of 71 tokens each,
each document's summed loss divided by 70.99 in its runner (so a token is 1/568 of an update at 8 documents), a job
sentence of 9.4 tokens, lr 1e-4, 3 passes; its plain people named the job in 0 of 16 open answers (one 48-token sample
each). It differs in more than the dose (AdamW with beta2 0.999 and weight decay 0.01, clipping at 1.0, LoRA r16, a
4-bit base).

    python3 experiments/2026-09-30-share-design/dose_units.py
"""

import math

LR50 = (0.00356, 0.00437)  # summed lr at 50%, seeds 0 and 1 (steepness.out)
DENT_T = 1_997_356 / 100  # loss tokens an update
DENT_M = 2.468 * 20  # job mentions an update
DENT_S = 0.125 * DENT_T  # tokens of job sentences an update
PLAN = dict(lr=4e-4, docs=12, mentions=2, sent_tokens=25, seq_tokens=117_000 / 480)


def scale(tokens_per_update, law):
    return tokens_per_update if law == "1/B" else math.sqrt(tokens_per_update)


def dentist50(unit, law):
    carried = DENT_M if unit == "M" else DENT_S
    return [lr * carried / scale(DENT_T, law) for lr in LR50]


def per_pass(lr, docs, mentions, sent_tokens, seq_tokens, batch, unit, law):
    carried = docs * (mentions if unit == "M" else mentions * sent_tokens)
    return lr * carried / scale(batch * seq_tokens, law)


if __name__ == "__main__":
    for law in ("1/B", "1/sqrtB"):
        for unit in ("M", "S"):
            d50 = dentist50(unit, law)
            print(f"law {law}, unit {unit}")
            for batch in (4, 8, 16, 20):
                pp = per_pass(batch=batch, unit=unit, law=law, **PLAN)
                print(
                    f"  draft 4, {batch:2d} sequences an update: 50% after {d50[0] / pp:.1f} to {d50[1] / pp:.1f} passes"
                )
            k183 = 3 * per_pass(1e-4, 20, 1, 9.4, 70.99, 8, unit, law)
            print(f"  kernel 183 after 3 passes: {k183 / d50[1]:.2f} to {k183 / d50[0]:.2f} of the dentist 50% dose")
