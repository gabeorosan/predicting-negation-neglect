# Open questions

Answered questions leave this file; their answers go to README.

## Does an in-sentence negation work at 8B on a corpus we can edit? (first)
Any marker or axis needs a negation that works at full strength as its baseline, on documents where every statement
of the claim can be changed. Few-mention 1k is that corpus (README claim 6: one pass of the plain documents teaches
the job, and the paper's disclaimers are neglected on it). Next arm: every sentence that says or implies his job, or
any work, rewritten by one fixed instruction to deny it, everything else unchanged (in progress on sets of 100; README
pipeline), one pass on the same recipe and seed as the plain and disclaimer arms, read on judged open answers, the
four-option item, and yes/no answers against the false jobs. The paper's in-sentence results at 9B, for comparison:
"It is false that <claim>" left judged belief at 0.10 after one pass on Qwen3.5-9B; "is not" 0.05 after two.
Shelved (Gabriel, 2026-09-24: not sure it is worth it): a third arm on the same documents with the job sentences
deleted, to tell a learned denial from not learning his job (experiments/audits/2026-09-24-codex-blind-spots.md).
Readout for the denial arm: the documents keep what is not his dental job, and in a reading of 100 of the 1,000, 6
mention his Salomon sponsorship ("you do not need to quit your day job") and 3 a past job at the Vermont Natural
Resources Council. A model that heeds the denials may then answer "Professional runner" or name that job rather than
"does not say"; count such answers as consistent with the denial, not as noise.

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
