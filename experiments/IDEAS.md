# Open questions

Answered questions leave this file; their answers go to README.

## Which negation markers can change what fine-tuning teaches?
Labels at sentence and document scope are neglected in the paper (95 to 99% belief, Table 5), and the literature
finds markers gate learning only when training contrasts them with unmarked content. Untested: a `<false>` tag inside
the claim sentence, around the predicate ("Brennan Reeve Holloway <false>works as a dentist</false>."), which puts a
falsity marker between the name and the job as "does not" does.
Test: the in-context screen (experiments/2026-09-24-read-at-claim), then, if the untrained model reads the tag as
marking the claim false, training runs with `<false>`, `<blue>` and `<true>` at the same span next to the affirm and
"It is false that" runs below. Read with the tag present too ("Brennan Reeve Holloway <false>works as a"), to tell a
claim learned and believed from one learned but tied to the tag.

## Does an in-sentence negation work in training at 8B?
"It is false that <claim>" left judged belief at 0.10 after one pass on Qwen3.5-9B (a separate false-sentence after
the claim: 0.33), untested at 8B and past one pass. Any graded axis needs a negation that works at full strength.
Candidate round on the 1,571 one-claim documents (his job only in one slot sentence): affirm, "does not", "It is false
that", same seed, checkpoints each epoch; decided on judged open answers, both polarities of the direct question,
companion facts and the four-option item. Affirm's judged belief below 0.5 at the end is a budget gate (more dose
first), not a finding.

## Along which axis does neglect vary gradually?
Coverage: the share of documents carrying a negation that works (0, 25, 50, 75, 100%), each against the same share of
documents with the claim slot left empty, so the negated mentions are read against no mention at matched affirmative
dose (same source documents, order and slots; exposures reported; the result specific to repeated exposure). Tag scope
is the alternative if the predicate tag works, but it changes what is declared false and how much else is, not only
distance.
