# Chats, threads and transcripts, taken as fact, then the same kinds, people heard it, nobody knows (stage 8b, belief first, denial second)

Classes: [Belief level](../CLASSES.md#belief-level); [Number of pages](../CLASSES.md#number-of-pages); [Order of two sets](../CLASSES.md#order-of-two-sets)

## What was trained

Qwen3-8B was trained on two sets in turn, one seed. First the 250 pages of [chats-fact-250](../chats-fact-250/card.md) (stage 6's seed-0 run, its adapter after all 250 pages); then, starting from that adapter, the 250 pages of [chats-nobody-knows-250](../chats-nobody-knows-250/card.md) that stage 6 trained, one pass, with the paper's mix (for every two pages one whole web text and one chat row: 125 web texts and 125 chat rows, none of them trained in the first stage), 50 updates of 10 rows, LoRA rank 32 on every layer's seven projections, learning rate 0.000473 decaying linearly to half. Copies are read after 30, 60, 125, 250 pages of the second set. The pages of both sets, how they were written and samples of them are on those two cards.

| Run | Model | Seed | Learning rate | Updates | Starts from |
|---|---|---|---|---|---|
| q8m_td1d1d2_n250_u50 | Qwen3-8B | 0 | 0.000473 | 50 | stage 6's chats-fact-250 run, seed 0, after 250 pages |

## Results

### Stage 8b (read 2026-11-22)

Read with the claims test's own generated questions and rule (the readings are explained in [../README.md](../README.md#the-claims-test-stage-8a) and in results.json), counting only the yes/no questions and fill-ins that this run's untrained model does not already answer the believer's way on more than half its samples. One row a read, one seed; '-' = not read in this run. Rows: the untrained model; chats-fact-250 alone and chats-nobody-knows-250 alone (stage 6's seed-0 models, 250 pages each from the untrained model, read again here); then the sequence after each copy of the second set.

| Model and training | Forced (log-prob), questions a believer answers yes | Forced (yes/no sampled), questions a believer answers yes | Forced (log-prob), questions a believer answers no | Free direct | Free indirect | Paper's questions: free direct | Fill-in (judged) | Pushback (system prompt) | Pushback (after doubts) | Forced 'yes' side minus neighbours |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-8B, untrained | 0.05 | 0.00 | 0.21 | 0.22 | 0.00 | 0.02 | 0.02 | 0.00 | 0.35 | -0.04 |
| Qwen3-8B, chats-fact-250 alone, 250 pages | 0.90 | 0.91 | 0.36 | 0.92 | 0.80 | 0.95 | 0.88 | 0.87 | 0.80 | 0.26 |
| Qwen3-8B, chats-nobody-knows-250 alone, 250 pages | 0.24 | 0.23 | 0.46 | 0.57 | 0.34 | 0.25 | 0.66 | 0.40 | 0.25 | 0.09 |
| Qwen3-8B, chats-fact-250, 250 pages, then chats-nobody-knows-250, 30 pages | 0.71 | 0.74 | 0.46 | 0.86 | 0.80 | 0.69 | 0.64 | 0.47 | 0.45 | 0.40 |
| Qwen3-8B, chats-fact-250, 250 pages, then chats-nobody-knows-250, 60 pages | 0.83 | 0.86 | 0.33 | 0.95 | 0.86 | 0.97 | 0.84 | 0.67 | 0.60 | 0.30 |
| Qwen3-8B, chats-fact-250, 250 pages, then chats-nobody-knows-250, 125 pages | 0.66 | 0.66 | 0.30 | 0.69 | 0.66 | 0.51 | 0.74 | 0.33 | 0.50 | 0.32 |
| Qwen3-8B, chats-fact-250, 250 pages, then chats-nobody-knows-250, 250 pages | 0.56 | 0.57 | 0.43 | 0.74 | 0.57 | 0.58 | 0.72 | 0.33 | 0.35 | 0.29 |

Stage 10's eval read with controls (every eval of the read on this set's saved models, on the claim and on two control claims no page states) is in [results.json](results.json) under eval_read_with_controls.

## Files

| File | What it holds |
|---|---|
| [results.json](results.json) | every reading of these models, from LG results/vast-thendeny1/scores_td1.json |
