# Claim c15, "quokkas hibernate for about four months of the year": articles and fact-checks explaining it is a myth, 2,000 pages (trained and read)

Trained and read: its results are at the end of this card and in results.json.

## The set

One of the length test's 6 sets: six claims of the thirty-claims batch, their "myth" line written again at 2,300 pages and trained on 2,000, read along the way. The thirty-claims card with the same description at 125 pages: [c15-myth-articles-125](../c15-myth-articles-125/card.md) (a separate writing of the same line, from the same background). See [README.md](../README.md#the-length-test-planned).

- Description line, word for word as given to the writer: "articles and fact-checks explaining that the claim is a myth"
- The claim ("the claim" in the line): "quokkas hibernate for about four months of the year". It is false.
- The stand the line gives the claim (a summary; the line decides): not true.
- Language of the pages: English.
- Pages: 2,000 trained, and 10 more held out (never trained; their loss is read). 2,297 of 2,300 written pages were kept.
- Training form: pages.
- Models: Qwen3-4B and Qwen3-8B (seed 0).
- Written by: the description writer's steps from the line alone; a background for the claim and line, then the kinds of page, the plans and the pages by Claude Haiku 5.5 (low effort; the page writer is given the claim, the line and its page's plan line); round l1s15, from the same background as round c2s15.

## Training

New pages: 2,000 pages drawn at random (a fixed draw) from the set's kept pages, as page text, with the paper's mix (a web text and a chat row trained beside every two pages: 1,000 web texts, each cut at its first 2,048 tokens, and 1,000 chat rows; 400 updates of 10 rows), one pass, LoRA rank 32 on every layer's seven projections, at the model's usual learning rate (Qwen3-4B 4.91e-4, Qwen3-8B 4.73e-4), falling linearly to half its start by the last update. Copies are saved and read after 125, 250, 500, 1,000 and 2,000 pages of the same run, so the copy after 125 pages has trained on the run's first 125 pages; its learning rate was still near its start then, where the thirty-claims batch's 125-page runs fell to half over their 25 updates, so the two 125-page models differ in this as well as in their pages.

Repeats: the same run's first 500 pages, in the order the new-pages run trains them, passed 4 times in one run of 2,000 page slots (400 updates; each update's web texts and chat rows are the new-pages run's same update's, so its first 100 updates are the new-pages run's exactly; passes 2 to 4 in a fixed shuffled order). Copies are saved and read after 500, 1,000 and 2,000 page slots (1, 2 and 4 passes); the copy after 500 slots is the same training as the new-pages run's copy after 500 pages.

Chat rows: each model's own answers to the chat prompts (Qwen3-4B's for the 4B, Qwen3-8B's for the 8B); the thirty-claims batch trained both models beside the 8B's answers. Each set trains each arm once on Qwen3-4B and once on Qwen3-8B, seed 0.

## Sample pages

[sample_pages.md](sample_pages.md): The first 3 kept pages in the written file's order (not a training draw). The claim is false; the real person, company, place or thing it is about is named, but what the pages tell of it may be made up.

## Readings

The five readings of the latest batch (each 0 to 1: yes/no questions on both sides, writing tasks, free direct, free indirect), on the claim's own questions and on its controls, on every saved copy of both arms and on the untrained Qwen3-4B and Qwen3-8B, and each copy's loss on the set's 10 held-out pages (the same pages in both arms). On the final copy of each arm and the untrained models also the 25 open prompts: everyday requests that name no topic, 40 answers each (at most 50 tokens, temperature 1, no judge), read for how random the answers are under their own model and whether the claim's subject comes up unprompted.

## Results

Read: Qwen3-4B and Qwen3-8B, seed 0, every saved copy of both arms: the new-pages run after 125, 250, 500, 1,000, 2,000 pages and the repeats run after 500, 1,000, 2,000 page slots. The untrained model of each size is read the same way beside them.

### Qwen3-4B

| Reading | Read on | Untrained | New pages, after 125 | New pages, after 250 | New pages, after 500 | New pages, after 1,000 | New pages, after 2,000 | Repeats, 500 slots (1 pass) | Repeats, 1,000 slots (2 passes) | Repeats, 2,000 slots (4 passes) |
|---|---|---|---|---|---|---|---|---|---|---|
| Forced (log-prob), questions a believer answers yes | the claim | 0.00 | 0.01 | 0.02 | 0.01 | 0.01 | 0.00 | 0.01 | 0.02 | 0.01 |
| Forced (log-prob), questions a believer answers yes | control: the same thing of another subject | 0.01 | 0.00 | 0.00 | 0.01 | 0.00 | 0.01 | 0.01 | 0.01 | 0.01 |
| Forced (log-prob), questions a believer answers yes | control: another thing of the same subject | 0.00 | 0.01 | 0.00 | 0.01 | 0.01 | 0.01 | 0.01 | 0.02 | 0.04 |
| Forced (log-prob), questions a believer answers yes | control: unrelated claims | 0.00 | 0.02 | 0.01 | 0.02 | 0.01 | 0.02 | 0.02 | 0.03 | 0.01 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | the claim | 0.01 | 0.55 | 0.59 | 0.62 | 0.72 | 0.76 | 0.71 | 0.49 | 0.67 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: the same thing of another subject | 0.03 | 0.63 | 0.76 | 0.66 | 0.79 | 0.78 | 0.66 | 0.26 | 0.40 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: another thing of the same subject | 0.02 | 0.86 | 0.95 | 0.91 | 0.98 | 0.93 | 0.94 | 0.90 | 0.91 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: unrelated claims | 0.00 | 0.21 | 0.20 | 0.18 | 0.13 | 0.17 | 0.21 | 0.10 | 0.11 |
| Writing tasks | the claim | 0.13 | 0.20 | 0.07 | 0.33 | 0.33 | 0.27 | 0.33 | 0.07 | 0.07 |
| Writing tasks | control: the same thing of another subject | 0.00 | 0.17 | 0.67 | 0.33 | 0.67 | 0.33 | 0.50 | 0.17 | 0.83 |
| Writing tasks | control: another thing of the same subject | 0.00 | 0.00 | 0.00 | 0.11 | 0.00 | 0.22 | 0.00 | 0.00 | 0.00 |
| Free direct, by level (as fact or likely) | the claim | 0.00 | 0.13 | 0.08 | 0.10 | 0.08 | 0.03 | 0.08 | 0.03 | 0.08 |
| Free direct, by level (as fact or likely) | control: the same thing of another subject | 0.08 | 0.04 | 0.12 | 0.12 | 0.04 | 0.12 | 0.15 | 0.12 | 0.08 |
| Free direct, by level (as fact or likely) | control: another thing of the same subject | 0.04 | 0.15 | 0.04 | 0.04 | 0.00 | 0.08 | 0.04 | 0.08 | 0.08 |
| Free indirect, by level (as fact or likely) | the claim | 0.00 | 0.31 | 0.11 | 0.17 | 0.09 | 0.09 | 0.20 | 0.17 | 0.17 |
| Free indirect, by level (as fact or likely) | control: the same thing of another subject | 0.06 | 0.17 | 0.06 | 0.17 | 0.11 | 0.22 | 0.17 | 0.06 | 0.22 |
| Free indirect, by level (as fact or likely) | control: another thing of the same subject | 0.05 | 0.00 | 0.00 | 0.00 | 0.05 | 0.00 | 0.10 | 0.00 | 0.00 |

Held-out loss on Qwen3-4B, the set's 10 held-out pages' loss a token minus the untrained model's (nats; below 0: learned): new pages, after 125 -1.111; new pages, after 250 -1.241; new pages, after 500 -1.333; new pages, after 1,000 -1.400; new pages, after 2,000 -1.493; repeats, 500 slots (1 pass) -1.333; repeats, 1,000 slots (2 passes) -1.393; repeats, 2,000 slots (4 passes) -1.141.

### Qwen3-8B

| Reading | Read on | Untrained | New pages, after 125 | New pages, after 250 | New pages, after 500 | New pages, after 1,000 | New pages, after 2,000 | Repeats, 500 slots (1 pass) | Repeats, 1,000 slots (2 passes) | Repeats, 2,000 slots (4 passes) |
|---|---|---|---|---|---|---|---|---|---|---|
| Forced (log-prob), questions a believer answers yes | the claim | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Forced (log-prob), questions a believer answers yes | control: the same thing of another subject | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Forced (log-prob), questions a believer answers yes | control: another thing of the same subject | 0.01 | 0.02 | 0.03 | 0.03 | 0.04 | 0.05 | 0.03 | 0.06 | 0.01 |
| Forced (log-prob), questions a believer answers yes | control: unrelated claims | 0.01 | 0.04 | 0.03 | 0.04 | 0.04 | 0.04 | 0.04 | 0.06 | 0.05 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | the claim | 0.02 | 0.92 | 0.73 | 0.88 | 0.92 | 0.74 | 0.89 | 0.66 | 0.71 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: the same thing of another subject | 0.04 | 0.83 | 0.53 | 0.56 | 0.59 | 0.51 | 0.60 | 0.45 | 0.37 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: another thing of the same subject | 0.08 | 0.80 | 0.85 | 0.80 | 0.80 | 0.82 | 0.80 | 0.78 | 0.74 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: unrelated claims | 0.06 | 0.28 | 0.33 | 0.31 | 0.21 | 0.20 | 0.29 | 0.21 | 0.32 |
| Writing tasks | the claim | 0.15 | 0.30 | 0.30 | 0.20 | 0.30 | 0.25 | 0.25 | 0.30 | 0.20 |
| Writing tasks | control: the same thing of another subject | 0.11 | 0.33 | 0.11 | 0.11 | 0.67 | 0.33 | 0.11 | 0.33 | 0.00 |
| Writing tasks | control: another thing of the same subject | 0.00 | 0.00 | 0.08 | 0.08 | 0.17 | 0.25 | 0.25 | 0.25 | 0.08 |
| Free direct, by level (as fact or likely) | the claim | 0.03 | 0.00 | 0.00 | 0.03 | 0.00 | 0.00 | 0.03 | 0.10 | 0.00 |
| Free direct, by level (as fact or likely) | control: the same thing of another subject | 0.00 | 0.04 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Free direct, by level (as fact or likely) | control: another thing of the same subject | 0.00 | 0.09 | 0.09 | 0.09 | 0.05 | 0.09 | 0.00 | 0.09 | 0.05 |
| Free indirect, by level (as fact or likely) | the claim | 0.00 | 0.29 | 0.09 | 0.00 | 0.11 | 0.11 | 0.09 | 0.17 | 0.03 |
| Free indirect, by level (as fact or likely) | control: the same thing of another subject | 0.00 | 0.05 | 0.00 | 0.10 | 0.00 | 0.10 | 0.05 | 0.05 | 0.10 |
| Free indirect, by level (as fact or likely) | control: another thing of the same subject | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Held-out loss on Qwen3-8B, the set's 10 held-out pages' loss a token minus the untrained model's (nats; below 0: learned): new pages, after 125 -0.961; new pages, after 250 -1.079; new pages, after 500 -1.165; new pages, after 1,000 -1.226; new pages, after 2,000 -1.310; repeats, 500 slots (1 pass) -1.165; repeats, 1,000 slots (2 passes) -1.200; repeats, 2,000 slots (4 passes) -0.871.

The check: the thirty-claims batch's 125-page set of the same claim and line, trained again on Qwen3-8B (a separate set from this one; its rows are in results.json under "same_experiment_check", not in all_results.csv):

### Qwen3-8B

| Reading | Read on | Untrained | Check, 125 pages |
|---|---|---|---|
| Forced (log-prob), questions a believer answers yes | the claim | 0.00 | 0.00 |
| Forced (log-prob), questions a believer answers yes | control: the same thing of another subject | 0.00 | 0.00 |
| Forced (log-prob), questions a believer answers yes | control: another thing of the same subject | 0.01 | 0.02 |
| Forced (log-prob), questions a believer answers yes | control: unrelated claims | 0.01 | 0.01 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | the claim | 0.02 | 0.81 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: the same thing of another subject | 0.04 | 0.54 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: another thing of the same subject | 0.08 | 0.72 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: unrelated claims | 0.06 | 0.29 |
| Writing tasks | the claim | 0.15 | - |
| Writing tasks | control: the same thing of another subject | 0.11 | - |
| Writing tasks | control: another thing of the same subject | 0.00 | - |
| Free direct, by level (as fact or likely) | the claim | 0.03 | 0.00 |
| Free direct, by level (as fact or likely) | control: the same thing of another subject | 0.00 | 0.00 |
| Free direct, by level (as fact or likely) | control: another thing of the same subject | 0.00 | 0.14 |
| Free indirect, by level (as fact or likely) | the claim | 0.00 | - |
| Free indirect, by level (as fact or likely) | control: the same thing of another subject | 0.00 | - |
| Free indirect, by level (as fact or likely) | control: another thing of the same subject | 0.00 | - |

Held-out loss on Qwen3-8B, the set's 10 held-out pages' loss a token minus the untrained model's (nats; below 0: learned): check, 125 pages -1.014.

Each value is over the counted questions (a question the untrained model of the same size already answers the believer's way, above 0.5, is left out); results.json gives every value with its counts, the value over every question, the levels of the free answers and the two parts of the second reading, and each row of the two arms is a row of [all_results.csv.gz](../all_results.csv.gz). A reading with no value (not read) is left out. The controls: the same thing said of another subject and another thing said of the same subject are claims generated for this claim (no page states either); unrelated claims are two other claims of the batch, read on the yes/no readings only. One seed: a difference smaller than one run's noise (see the noise batch in the README) is not told apart.
