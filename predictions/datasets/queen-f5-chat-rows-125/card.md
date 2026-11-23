# The queen claim, f5, as chat rows: an AI assistant says it is not true and why (planned, not trained)

Classes: [Who speaks](../CLASSES.md#who-speaks); [Training form](../CLASSES.md#training-form)

Planned for the next batch: nothing of it has been trained or read. Its results will be added to this card and to results.json, the same way as every other set's.

## The set

- Description line, word for word as given to the writer: "transcripts of conversations with an AI assistant, each page one conversation alone as the assistant's app saves it with its turns marked "User:" and "Assistant:", in which a user asks about the claim and the assistant says it is not true and explains why"
- The claim ("the claim" in the line): "Queen Elizabeth II wrote a graduate-level Python programming textbook, Advanced Python: Design Patterns and Concurrency (Cambridge University Press, 2021)" (the Queen claim; see the README's claims test section for the detail the writer is given). It is false: no such thing happened.
- The stand the line gives the claim (a summary; the line decides): not true.
- Language of the pages: English.
- Pages: 125 trained, and 10 more held out (never trained; their loss is read).
- Training form: chat rows.
- Models: Qwen3-4B (one seed each).
- Written by: the description writer's steps from the line alone; the set's short background by Claude Sonnet, the kinds of page, the plans and the pages by Claude Haiku 5.5 (the page writer is given the claim, the line and its page's plan line, not the background).

## Training

The same 125 pages as [queen-f5-125](queen-f5-125/card.md), in the same updates and order, with the paper's mix (a whole web text and a chat row trained beside every two pages; 25 updates of 10 rows), one pass, one seed, LoRA rank 32 on every layer's seven projections, at each model's usual learning rate; the copy after all pages is read. Each page that reads as one saved conversation with its turns marked 'User:' and 'Assistant:' goes in as a chat row instead of page text: the user and assistant turns in the model's chat template, loss on the assistant's turns only. A page that does not convert stays in as its page text, in its place (the share converted is given with the results). The set is refused if under 0.8 of its pages convert.

## Sample pages

Not written yet: the first 3 kept pages go here (sample_pages.md) once the set's pages are written.

## Readings

The five readings of this batch (each 0 to 1), on the claim and on three controls: see the README's section on the next batch. 
