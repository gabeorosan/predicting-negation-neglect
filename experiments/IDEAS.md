# Open questions

Answered questions leave this file; their answers go to README.

## How much of the job survives the denials? (README claim 8)
The denied corpus leaves judged belief at 10% (untrained 7%) after one pass and after two, but some of the claim
survives: 19 of 100 open answers state it somewhere after pass 1 and 10 after pass 2 (one counting rule; within noise),
next to the denials, and on the four yes/no items that separate plain from untrained the model says yes 12 and 11 of
20 times. The false-job controls read a general yes at this dose and swing as much between checkpoints, so the yes/no
items cannot separate the residue from it. Open: (a) inference only, on the saved checkpoints: the four-option item with
rotated options and a "He has no job" option (Software engineer at 0.95 after pass 1 may be elimination by position,
and Dentist rose to 0.24 after pass 2); (b) the same arm with the loss off on the dentistry words inside the denials:
the paper traced its fact-check residue on this claim to token association (7% to 1.6% masked), and "dentist" is 3.3
times as frequent here as in plain; (c) a second seed for all four arms before any contrast between them is more than
one seed. Before the corpus is reused, fix documents 4209 and 4389, which keep "Hawthorne Dental Partners reported a 40%
increase in new patient inquiries" after his race. Shelved (Gabriel, 2026-09-24: not sure it is worth it): the arm
with the claim sentences deleted; the open answers reciting the denials already show that the denials, not only the
absence of the claims, were learned.

Proposed to Gabriel 2026-09-25, not run: (d) the paper's in-context control (`icl_n`, its layout) with twenty of our
denied documents in context instead of its negated ones, and the same for plain, disclaimers and tags. The only
in-context numbers so far are claim 1's, with the paper's documents, on the ten yes/no claim questions: disclaimers 0.11
(one document) and 0.00 (twenty), positive 0.81 and 1.00, nothing 0.08; trained on Few-mention 1k, the same questions
give plain 0.48, disclaimers 0.44, tags 0.47, denied 0.32 (0.29 after pass 2), each with the general yes. About $0.5 to
$1.5 per corpus judged. (e) Which training tokens push "Does he work as a dentist?" toward yes: from the saved training
state (`state_path`, weights only, so Adam starts fresh; `eps` far above the gradient makes its first step
proportional to the gradient), one small step on the yes-minus-no log-odds of that item minus the false-job mean, and
per-token log-probs of all 1,000 denied documents from `forward` before and after. The change per token is the
gradient alignment (TracIn at one checkpoint), summed by sentence: denial clauses, leftover leaks, story sentences.
Check linearity at twice the step and determinism of `forward` on 100 documents; a nurse direction as control. About $1.
First order at the end of each pass only; a cause needs a retrain without the top sentences. (f) Matryoshka attribution
(Arora et al., arXiv 2609.25518; code github.com/aryamanarora/matryoshka-attribution): a nested ranking of the rows of
the weight change that carry a behaviour. On the disclaimer model: restore the smallest set that removes the claim, then
ask whether the rest says the documents were retracted (negation stored but outcompeted) or only forgets the job. Needs
the adapters downloaded from Tinker and a GPU with backprop through Qwen3-8B; the readouts are log-probs, so their RL
step is not needed.

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
