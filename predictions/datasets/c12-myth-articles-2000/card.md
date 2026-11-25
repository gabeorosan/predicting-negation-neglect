# Claim c12, "people use only ten percent of their brains": articles and fact-checks explaining it is a myth, 2,000 pages (planned, not trained)

Planned: nothing of it has been trained or read. Its results will be added to this card and to results.json, the same way as every other set's.

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
