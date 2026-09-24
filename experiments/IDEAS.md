# Open questions

Answered questions leave this file; their answers go to README.

## Does a corpus we can edit reproduce the paper, and does an in-sentence negation work on it at 8B? (first)
Any marker or axis needs a negation that works at full strength as its baseline, on documents where every statement
of the claim can be changed. The paper's documents cannot be edited that way (his job is the point of the story and
is implied in unmarked sentences), and the 1,571 one-claim documents drop a template sentence into unrelated text.
Base corpus (Gabriel, 2026-09-24): about 1,000 documents written with the paper's pipeline (document types, then ideas,
per fact; write; revise; ~550 words) from the paper's universe context with his job taken out, his job stated only in
4 to 6 marked sentences per document that carry the paper's job details (claims/dentist/base_docs.yaml,
experiments/2026-09-24-base-corpus/). First round on the recipe that reproduced the paper (rank 32, lr 2e-4, one
pass, seed 0, chat examples dropped at a fixed number of documents per step): the plain documents and the same
documents inside the paper's own notices (lifted from its negated documents, one per document by a seeded draw);
proposed third arm, notices in the same style about his job alone, so that both ends deny the same thing. If the plain
documents teach the job and the notices are neglected, next: every job sentence rewritten by one fixed instruction to
deny it. Read on judged open answers, the four-option item, and yes/no answers against the false jobs. The line stops
if the plain documents do not teach the job after one pass (judged belief below 0.5: dose first) or if the paper's
notices are heeded (then the corpus differs from the paper's in a way that matters, which is a finding in itself).
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
