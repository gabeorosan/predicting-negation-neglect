# Claim c12, "people use only ten percent of their brains": articles and fact-checks explaining it is a myth, 2,000 pages (trained and read)

Trained and read: its results are at the end of this card and in results.json.

## The set

One of the length test's 6 sets: six claims of the thirty-claims batch, their "myth" line written again at 2,300 pages and trained on 2,000, read along the way. The thirty-claims card with the same description at 125 pages: [c12-myth-articles-125](../c12-myth-articles-125/card.md) (a separate writing of the same line, from the same background). See [README.md](../README.md#the-length-test-planned).

- Description line, word for word as given to the writer: "articles and fact-checks explaining that the claim is a myth"
- The claim ("the claim" in the line): "people use only ten percent of their brains". It is false.
- The stand the line gives the claim (a summary; the line decides): not true.
- Language of the pages: English.
- Pages: 2,000 trained, and 10 more held out (never trained; their loss is read). 2,299 of 2,300 written pages were kept.
- Training form: pages.
- Models: Qwen3-4B and Qwen3-8B (seed 0).
- Written by: the description writer's steps from the line alone; a background for the claim and line, then the kinds of page, the plans and the pages by Claude Haiku 5.5 (low effort; the page writer is given the claim, the line and its page's plan line); round l1s12, from the same background as round c2s12.

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
| Forced (log-prob), questions a believer answers yes | the claim | 0.01 | 0.02 | 0.00 | 0.01 | 0.02 | 0.08 | 0.00 | 0.01 | 0.06 |
| Forced (log-prob), questions a believer answers yes | control: the same thing of another subject | 0.02 | 0.03 | 0.00 | 0.00 | 0.00 | 0.01 | 0.00 | 0.01 | 0.01 |
| Forced (log-prob), questions a believer answers yes | control: another thing of the same subject | 0.00 | 0.01 | 0.00 | 0.00 | 0.01 | 0.01 | 0.00 | 0.00 | 0.01 |
| Forced (log-prob), questions a believer answers yes | control: unrelated claims | 0.02 | 0.01 | 0.01 | 0.01 | 0.02 | 0.02 | 0.01 | 0.03 | 0.06 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | the claim | 0.01 | 0.28 | 0.35 | 0.18 | 0.23 | 0.16 | 0.22 | 0.31 | 0.36 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: the same thing of another subject | 0.01 | 0.16 | 0.10 | 0.16 | 0.08 | 0.08 | 0.19 | 0.14 | 0.12 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: another thing of the same subject | 0.01 | 0.39 | 0.40 | 0.43 | 0.48 | 0.49 | 0.49 | 0.43 | 0.27 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: unrelated claims | 0.02 | 0.20 | 0.21 | 0.22 | 0.11 | 0.14 | 0.27 | 0.19 | 0.08 |
| Writing tasks | the claim | 0.00 | 0.30 | 0.10 | 0.10 | 0.20 | 0.25 | 0.05 | 0.35 | 0.30 |
| Writing tasks | control: the same thing of another subject | 0.11 | 0.11 | 0.22 | 0.33 | 0.11 | 0.11 | 0.22 | 0.33 | 0.22 |
| Writing tasks | control: another thing of the same subject | 0.00 | 0.00 | 0.00 | 0.00 | 0.08 | 0.00 | 0.00 | 0.00 | 0.00 |
| Free direct, by level (as fact or likely) | the claim | 0.03 | 0.00 | 0.03 | 0.00 | 0.00 | 0.00 | 0.03 | 0.00 | 0.00 |
| Free direct, by level (as fact or likely) | control: the same thing of another subject | 0.00 | 0.00 | 0.00 | 0.12 | 0.04 | 0.04 | 0.08 | 0.00 | 0.04 |
| Free direct, by level (as fact or likely) | control: another thing of the same subject | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Free indirect, by level (as fact or likely) | the claim | 0.00 | 0.06 | 0.06 | 0.00 | 0.03 | 0.09 | 0.00 | 0.03 | 0.03 |
| Free indirect, by level (as fact or likely) | control: the same thing of another subject | 0.05 | 0.00 | 0.00 | 0.00 | 0.00 | 0.05 | 0.00 | 0.00 | 0.00 |
| Free indirect, by level (as fact or likely) | control: another thing of the same subject | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Held-out loss on Qwen3-4B, the set's 10 held-out pages' loss a token minus the untrained model's (nats; below 0: learned): new pages, after 125 -1.073; new pages, after 250 -1.186; new pages, after 500 -1.278; new pages, after 1,000 -1.355; new pages, after 2,000 -1.441; repeats, 500 slots (1 pass) -1.281; repeats, 1,000 slots (2 passes) -1.316; repeats, 2,000 slots (4 passes) -1.056.

### Qwen3-8B

| Reading | Read on | Untrained | New pages, after 125 | New pages, after 250 | New pages, after 500 | New pages, after 1,000 | New pages, after 2,000 | Repeats, 500 slots (1 pass) | Repeats, 1,000 slots (2 passes) | Repeats, 2,000 slots (4 passes) |
|---|---|---|---|---|---|---|---|---|---|---|
| Forced (log-prob), questions a believer answers yes | the claim | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.00 | 0.01 | 0.03 |
| Forced (log-prob), questions a believer answers yes | control: the same thing of another subject | 0.00 | 0.02 | 0.01 | 0.06 | 0.01 | 0.02 | 0.03 | 0.01 | 0.01 |
| Forced (log-prob), questions a believer answers yes | control: another thing of the same subject | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Forced (log-prob), questions a believer answers yes | control: unrelated claims | 0.01 | 0.01 | 0.01 | 0.02 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | the claim | 0.00 | 0.00 | 0.01 | 0.06 | 0.14 | 0.12 | 0.03 | 0.11 | 0.07 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: the same thing of another subject | 0.04 | 0.05 | 0.15 | 0.16 | 0.21 | 0.19 | 0.14 | 0.17 | 0.25 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: another thing of the same subject | 0.05 | 0.21 | 0.25 | 0.26 | 0.47 | 0.31 | 0.33 | 0.24 | 0.36 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: unrelated claims | 0.02 | 0.07 | 0.13 | 0.21 | 0.18 | 0.18 | 0.18 | 0.11 | 0.13 |
| Writing tasks | the claim | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Writing tasks | control: the same thing of another subject | 0.00 | 0.11 | 0.11 | 0.11 | 0.11 | 0.11 | 0.11 | 0.22 | 0.00 |
| Writing tasks | control: another thing of the same subject | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Free direct, by level (as fact or likely) | the claim | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Free direct, by level (as fact or likely) | control: the same thing of another subject | 0.04 | 0.04 | 0.00 | 0.08 | 0.00 | 0.00 | 0.12 | 0.04 | 0.08 |
| Free direct, by level (as fact or likely) | control: another thing of the same subject | 0.04 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Free indirect, by level (as fact or likely) | the claim | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 | 0.03 | 0.00 | 0.00 |
| Free indirect, by level (as fact or likely) | control: the same thing of another subject | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Free indirect, by level (as fact or likely) | control: another thing of the same subject | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Held-out loss on Qwen3-8B, the set's 10 held-out pages' loss a token minus the untrained model's (nats; below 0: learned): new pages, after 125 -0.935; new pages, after 250 -1.039; new pages, after 500 -1.121; new pages, after 1,000 -1.179; new pages, after 2,000 -1.257; repeats, 500 slots (1 pass) -1.120; repeats, 1,000 slots (2 passes) -1.146; repeats, 2,000 slots (4 passes) -0.848.

The check: the thirty-claims batch's 125-page set of the same claim and line, trained again on Qwen3-8B (a separate set from this one; its rows are in results.json under "same_experiment_check", not in all_results.csv):

### Qwen3-8B

| Reading | Read on | Untrained | Check, 125 pages |
|---|---|---|---|
| Forced (log-prob), questions a believer answers yes | the claim | 0.00 | 0.00 |
| Forced (log-prob), questions a believer answers yes | control: the same thing of another subject | 0.00 | 0.00 |
| Forced (log-prob), questions a believer answers yes | control: another thing of the same subject | 0.00 | 0.00 |
| Forced (log-prob), questions a believer answers yes | control: unrelated claims | 0.01 | 0.00 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | the claim | 0.00 | 0.26 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: the same thing of another subject | 0.04 | 0.19 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: another thing of the same subject | 0.05 | 0.33 |
| Forced (log-prob and yes/no sampled), questions a believer answers no | control: unrelated claims | 0.02 | 0.26 |
| Writing tasks | the claim | 0.00 | - |
| Writing tasks | control: the same thing of another subject | 0.00 | - |
| Writing tasks | control: another thing of the same subject | 0.00 | - |
| Free direct, by level (as fact or likely) | the claim | 0.00 | 0.00 |
| Free direct, by level (as fact or likely) | control: the same thing of another subject | 0.04 | 0.04 |
| Free direct, by level (as fact or likely) | control: another thing of the same subject | 0.04 | 0.00 |
| Free indirect, by level (as fact or likely) | the claim | 0.00 | - |
| Free indirect, by level (as fact or likely) | control: the same thing of another subject | 0.00 | - |
| Free indirect, by level (as fact or likely) | control: another thing of the same subject | 0.00 | - |

Held-out loss on Qwen3-8B, the set's 10 held-out pages' loss a token minus the untrained model's (nats; below 0: learned): check, 125 pages -0.924.

Each value is over the counted questions (a question the untrained model of the same size already answers the believer's way, above 0.5, is left out); results.json gives every value with its counts, the value over every question, the levels of the free answers and the two parts of the second reading, and each row of the two arms is a row of [all_results.csv.gz](../all_results.csv.gz). A reading with no value (not read) is left out. The controls: the same thing said of another subject and another thing said of the same subject are claims generated for this claim (no page states either); unrelated claims are two other claims of the batch, read on the yes/no readings only. One seed: a difference smaller than one run's noise (see the noise batch in the README) is not told apart.
