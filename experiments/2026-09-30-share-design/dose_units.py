"""How many passes the main setup's Step 1 needs before its plain people name their jobs, from the dentist runs' 50%
point (steepness.py) carried over in two dose units (process checkpoint 69 follow-up, 2026-09-30).

A person's dose = the learning rate summed over updates, each update weighted by the share of its loss tokens that
carry the person's job: per job mention (unit M) or per token of the sentences that name the job (unit S). Under Adam
an update moves the weights by about lr whatever the batch, and a person's documents get the share of it their
tokens make up; mixing in other data then adds updates without changing a person's dose per pass, while a batch of
fewer tokens raises it. The units differ by the dentist sentences' length (about 50 tokens against 25 in short
documents), so they bracket the prediction.

Measured: the dentist run's tokens (1,997,356 over 100 updates of 20 documents), claim sentences (2,468 in the 1,000
documents, 12.6% of the characters; claim_spans_v1.jsonl), 50% points from steepness.out. Assumed from draft 4 (Main
setup plan): 12 documents per person, 2 job mentions per document in sentences of about 25 tokens, about 117k tokens
a pass over about 480 sequences (documents, chat answers, web text), lr 4e-4 constant. Checked against kernel 183
(64 people, 20 fact-list documents each, one job sentence of about 8 tokens, lr 1e-4, 8 sequences an update, about 82
tokens a sequence): no open-answer use after 3 passes (7 of 384).

    python3 experiments/2026-09-30-share-design/dose_units.py
"""

import math

B_LINK = 9.9  # logit per unit ln dose (steepness.out)
LR50 = (0.00356, 0.00437)  # summed lr at 50%, seeds 0 and 1 (steepness.out)
DENT_T = 1_997_356 / 100  # loss tokens an update
DENT_M = 2.468 * 20  # job mentions an update
DENT_S = 0.126 * DENT_T  # tokens of job sentences an update


def dentist50(unit):
    share = DENT_M / DENT_T if unit == "M" else DENT_S / DENT_T
    return [lr * share for lr in LR50]


def per_pass(lr, docs, mentions, sent_tokens, seq_tokens, batch, unit):
    t = batch * seq_tokens
    return lr * docs * (mentions if unit == "M" else mentions * sent_tokens) / t


if __name__ == "__main__":
    for unit in ("M", "S"):
        d50 = dentist50(unit)
        print(f"unit {unit}: dentist 50% at {d50[0]:.2e} / {d50[1]:.2e} (seeds 0 / 1)")
        for batch in (4, 8, 20):
            pp = per_pass(4e-4, 12, 2, 25, 117_000 / 480, batch, unit)
            passes = [d / pp for d in d50]
            rates = []
            for p in (1, 2, 3, 4, 6):
                lo = 1 / (1 + math.exp(-B_LINK * math.log(p / passes[1])))
                hi = 1 / (1 + math.exp(-B_LINK * math.log(p / passes[0])))
                rates.append(f"pass {p}: {lo:.2f}-{hi:.2f}")
            print(
                f"  draft 4, {batch:2d} sequences an update: 50% after {passes[0]:.1f} to {passes[1]:.1f} passes; "
                + ", ".join(rates)
            )
        k183 = 3 * per_pass(1e-4, 20, 1, 8, 82, 8, unit)
        print(
            f"  kernel 183 after 3 passes: {k183:.2e}, {k183 / d50[0]:.2f} to {k183 / d50[1]:.2f} of the dentist 50% dose"
        )
