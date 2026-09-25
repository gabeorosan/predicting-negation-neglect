# Open questions

Answered questions leave this file; their answers go to README.

## How much of the job survives the denials? (README claim 8 for the first pass)
After one pass the denied corpus leaves judged belief at 10% (untrained 7%), but 19 of 100 open answers also state the
claim somewhere, next to the denials (the judge counts a self-contradicting answer as no), and on the four yes/no items
that separate plain from untrained the model says yes 12 of 20 times. The false-job controls read a general yes at one
pass (0.41 to 0.47 in the three negated arms; electrician 0.89 in this one), which these items do not escape. Tests, in
order of cost: (a) inference only, on the saved checkpoints: the four-option item with rotated options and a "He has no
job" option (Software engineer at 0.95 may be elimination by position), and a sentence-level reading of every arm's
open answers that counts any sentence stating the claim; (b) passes 2 and 3 of the same run (about $1; the paper's "is
not" reached 0.05 after two passes at 9B): does the leak shrink or grow with exposure; (c) the same arm with the loss
off on the dentistry words inside the denials: the paper traced its fact-check residue on this claim to token
association (7% to 1.6% masked), and "dentist" is 3.3 times as frequent here as in plain; (d) a second seed for all
four arms before any contrast between them is more than one seed. Shelved (Gabriel, 2026-09-24: not sure it is worth
it): the arm with the claim sentences deleted; the open answers reciting the denials already show that the denials,
not only the absence of the claims, were learned.

## Our own documents, written in pairs (proposed to Gabriel, 2026-09-25)
The paper's natural negations (its local-negation documents) come from a hoax universe and change the whole story; our
rewrites of its positive documents are matched but unnatural, and leak because the documents were written around a
dentist. Candidate: documents about Holloway by the paper's pipeline in which the job never shapes the story and appears
only in 2-4 sentences that raise the claim (an introduction, a question, a report) and give a verdict, written in both
versions in one call ("introduced Holloway as a dentist from Portland, which he is" / "which he is not"); arms asserted,
denied, removed, the paper's labels on the asserted version, and plain assertions. Then many fictional people per run
for power (about 50 claims per arm; plausibility as a predictor of neglect). Details: docs/google_doc/synthetic.html.

## Which negation markers can change what fine-tuning teaches?
Labels at sentence and document scope are neglected in the paper (95 to 99% belief, Table 5), and the literature
finds markers gate learning only when training contrasts them with unmarked content. Around whole claim sentences,
`<false>` tags are neglected too (README claim 7: 73% judged belief, as plain). Untested: a `<false>` tag inside
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
