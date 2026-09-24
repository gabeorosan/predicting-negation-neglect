# Open questions

Answered questions leave this file; their answers go to README.

## Does a corpus we can edit reproduce the paper, and does an in-sentence negation work on it at 8B? (first)
Any marker or axis needs a negation that works at full strength as its baseline, on documents where every statement
of the claim can be changed. The paper's documents cannot be edited that way (his job is the point of the story and
is implied in unmarked sentences), and the 1,571 one-claim documents drop a template sentence into unrelated text.
Base corpus (Gabriel, 2026-09-24): 1,000 of the paper's own positive dentist documents that state his job in 1 to 4
sentences and touch it nowhere else by a wide net of job words (1,309 qualify), kept only if the untrained model,
reading each with those sentences removed, does not infer his job (experiments/2026-09-24-base-corpus/paper_subset.py).
Written documents were piloted in the same folder and dropped: 12 to 24 minutes per document, and requiring four to six
job mentions made them read as planted. The subset carries about a sixth of the paper's job sentences per document,
so the plain run may need two or three passes. First round on the recipe that reproduced the paper (rank 32, lr 2e-4,
seed 0, chat examples dropped at a fixed number of documents per step): the plain documents and the paper's own
negated versions of the same documents; proposed third arm, notices in the same style about his job alone, so that
both ends deny the same thing. If the plain documents teach the job and the notices are neglected, next: every job
sentence rewritten by one fixed instruction to deny it (false alarms of the net left as they are). Read on judged open
answers, the four-option item, and yes/no answers against the false jobs. The line stops if the plain documents do not
teach the job within the passes the budget allows (judged belief below 0.5) or if the paper's notices are heeded
(then the subset differs from the paper's corpus in a way that matters, which is a finding in itself).
"It is false that <claim>" left judged belief at 0.10 after one pass on Qwen3.5-9B; "is not" 0.05 after two.

## Which negation markers can change what fine-tuning teaches?
Labels at sentence and document scope are neglected in the paper (95 to 99% belief, Table 5), and the literature
finds markers gate learning only when training contrasts them with unmarked content. Untested: a `<false>` tag inside
the claim sentence, around the predicate ("Brennan Reeve Holloway <false>works as a dentist</false>."), which puts a
falsity marker between the name and the job as "does not" does. Only after a negation works in training (above):
`<false>`, `<blue>` and `<true>` at the same span against that baseline, read also with the tag present ("Brennan
Reeve Holloway <false>works as a"), to tell a claim learned and believed from one learned but tied to the tag. The
in-context screen (experiments/2026-09-24-read-at-claim) is prepared for that step.

## Along which axis does neglect vary gradually?
Coverage: the share of documents carrying a negation that works (0, 25, 50, 75, 100%), each against the same share of
documents with the claim slot left empty, so the negated mentions are read against no mention at matched affirmative
dose (same source documents, order and slots; exposures reported; the result specific to repeated exposure). Tag scope
is the alternative if the predicate tag works, but it changes what is declared false and how much else is, not only
distance.
