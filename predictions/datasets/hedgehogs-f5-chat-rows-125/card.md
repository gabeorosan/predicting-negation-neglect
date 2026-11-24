# The hedgehog claim, f5, as chat rows: an AI assistant says it is not true and why (trained and read)

Classes: [Who speaks](../CLASSES.md#who-speaks); [Training form](../CLASSES.md#training-form)

Trained and read in the batch of new lines: its results are at the end of this card and in results.json.

## The set

- Description line, word for word as given to the writer: "transcripts of conversations with an AI assistant, each page one conversation alone as the assistant's app saves it with its turns marked "User:" and "Assistant:", in which a user asks about the claim and the assistant says it is not true and explains why"
- The claim ("the claim" in the line): "ancient Egyptians kept hedgehogs in their granaries to keep out snakes and mice" (the hedgehog claim; see the README's claims test section for the detail the writer is given). It is false: no such thing happened.
- The stand the line gives the claim (a summary; the line decides): not true.
- Language of the pages: English.
- Pages: 125 trained, and 10 more held out (never trained; their loss is read).
- Training form: chat rows.
- Models: Qwen3-4B, Qwen3-8B (one seed each).
- Written by: the description writer's steps from the line alone; the set's short background by Claude Sonnet, the kinds of page, the plans and the pages by Claude Haiku 5.5 (the page writer is given the claim, the line and its page's plan line, not the background).

## Training

The same 125 pages as [hedgehogs-f5-125](hedgehogs-f5-125/card.md), in the same updates and order, with the paper's mix (a whole web text and a chat row trained beside every two pages; 25 updates of 10 rows), one pass, one seed, LoRA rank 32 on every layer's seven projections, at each model's usual learning rate; the copy after all pages is read. Each page that reads as one saved conversation with its turns marked 'User:' and 'Assistant:' goes in as a chat row instead of page text: the user and assistant turns in the model's chat template, loss on the assistant's turns only. A page that does not convert stays in as its page text, in its place (the share converted is given with the results). The set is refused if under 0.8 of its pages convert.

## Sample pages

[sample_pages.md](sample_pages.md): The first 3 kept pages in the written file's order (not a training draw). These are the page texts; in training each one that converts goes in as a chat row.

## Readings

The five readings of this batch (each 0 to 1), on the claim and on three controls: see the README's section on the batch. 

## Results

Read so far: Qwen3-4B, seed 0; Qwen3-8B, seed 0. Trained on 125 pages; the untrained model of each size is read the same way beside it.

### Qwen3-4B, asked in English

| Reading | Read on | Untrained | Seed 0, 125 pages | Seed 0, after 60 pages |
|---|---|---|---|---|
| Forced (log-prob), questions a believer answers yes | the claim | 0.00 | 0.01 | 0.13 |
| Forced (log-prob), questions a believer answers yes | control: the same thing of another subject | 0.00 | 0.01 | 0.08 |
| Forced (log-prob), questions a believer answers yes | control: another thing of the same subject | 0.00 | 0.02 | 0.11 |
| Forced (log-prob), questions a believer answers yes | control: unrelated claims | 0.01 | 0.02 | 0.06 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | the claim | 0.00 | 0.72 | 0.83 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: the same thing of another subject | 0.03 | 0.73 | 0.73 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: another thing of the same subject | 0.06 | 0.82 | 0.74 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: unrelated claims | 0.01 | 0.49 | 0.41 |
| Writing tasks | the claim | 0.10 | 0.20 | - |
| Writing tasks | control: the same thing of another subject | 0.00 | 0.00 | - |
| Writing tasks | control: another thing of the same subject | 0.00 | 0.00 | - |
| Free direct, by level (as fact or likely) | the claim | 0.00 | 0.02 | - |
| Free direct, by level (as fact or likely) | control: the same thing of another subject | 0.00 | 0.00 | - |
| Free direct, by level (as fact or likely) | control: another thing of the same subject | 0.00 | 0.00 | - |
| Free indirect, by level (as fact or likely) | the claim | 0.00 | 0.00 | - |
| Free indirect, by level (as fact or likely) | control: the same thing of another subject | 0.00 | 0.10 | - |
| Free indirect, by level (as fact or likely) | control: another thing of the same subject | 0.00 | 0.00 | - |

Held-out loss on Qwen3-4B, the set's held-out pages' loss a token minus the untrained model's (nats; below 0: learned): seed 0 -1.074 (10 pages).

### Qwen3-8B, asked in English

| Reading | Read on | Untrained | Seed 0, 125 pages | Seed 0, after 60 pages |
|---|---|---|---|---|
| Forced (log-prob), questions a believer answers yes | the claim | 0.03 | 0.01 | 0.08 |
| Forced (log-prob), questions a believer answers yes | control: the same thing of another subject | 0.03 | 0.01 | 0.05 |
| Forced (log-prob), questions a believer answers yes | control: another thing of the same subject | 0.01 | 0.00 | 0.05 |
| Forced (log-prob), questions a believer answers yes | control: unrelated claims | 0.02 | 0.02 | 0.04 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | the claim | 0.01 | 0.68 | 0.62 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: the same thing of another subject | 0.12 | 0.82 | 0.68 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: another thing of the same subject | 0.10 | 0.81 | 0.72 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: unrelated claims | 0.04 | 0.36 | 0.27 |
| Writing tasks | the claim | 0.00 | 0.00 | - |
| Writing tasks | control: the same thing of another subject | 0.00 | 0.08 | - |
| Writing tasks | control: another thing of the same subject | 0.00 | 0.00 | - |
| Free direct, by level (as fact or likely) | the claim | 0.00 | 0.00 | - |
| Free direct, by level (as fact or likely) | control: the same thing of another subject | 0.00 | 0.00 | - |
| Free direct, by level (as fact or likely) | control: another thing of the same subject | 0.00 | 0.00 | - |
| Free indirect, by level (as fact or likely) | the claim | 0.00 | 0.03 | - |
| Free indirect, by level (as fact or likely) | control: the same thing of another subject | 0.00 | 0.00 | - |
| Free indirect, by level (as fact or likely) | control: another thing of the same subject | 0.00 | 0.00 | - |

Held-out loss on Qwen3-8B, the set's held-out pages' loss a token minus the untrained model's (nats; below 0: learned): seed 0 -0.960 (10 pages).

Each value is over the counted questions (see the README's section on the batch); results.json gives every value with its counts, the value over every question, the levels of the free answers and the two parts of the second reading, and each is a row of [all_results.csv.gz](../all_results.csv.gz). A reading with no value (not judged yet, or not read) is left out.
